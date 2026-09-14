#!/usr/bin/env bash
# Runs the actual ingestor (ingestor/main.py) against the regtest nodes,
# watches an address, funds it with THREE separate confirmed UTXOs, then
# spends all three in one transaction to a different address with no
# change returned, and asserts detection/wallet_drain.py writes a shadow
# alert with the reasoning visible -- the reproducible, on-demand proof
# that rule 2 fires, for the case docs/06-detection.md itself expects to be
# rare on live mainnet (see docs/08-build-plan.md, phase 4c).
#
# Funding outputs are mined BEFORE the drain transaction is constructed,
# same reasoning as regtest/ingestor-watchlist-test.sh: gettxout(...,
# include_mempool=false) cannot resolve an unconfirmed parent's output, so
# spending it while still pending would leave the drain transaction's own
# inputs unresolved (address='') in `flows`, and wallet_drain.py would never
# see the watched address as an input at all.
#
# Uses the same disposable clickhouse-regtest container as the other
# regtest/*-test.sh scripts, for the same reason: synthetic regtest
# addresses must never land in the real chainwatch database.
set -euo pipefail

ROOT="$HOME/chainwatch"
COMPOSE="docker compose -f $ROOT/docker-compose.regtest.yml"
INGESTOR_DIR="$ROOT/ingestor"
DETECTION_DIR="$ROOT/detection"
LOGFILE="$(mktemp -t detection-wallet-drain-test.XXXXXX.log)"

b1() { $COMPOSE exec -T btc1 bitcoin-cli -conf=/config/bitcoin.conf "$@"; }
jfield() { python3 -c "import sys,json; print(json.load(sys.stdin)$1)"; }

find_vout_for_address() {
  python3 -c "
import sys, json
d = json.load(sys.stdin)
addr = sys.argv[1]
for det in d['details']:
    if det.get('address') == addr and det.get('category') == 'receive':
        print(det['vout'])
        sys.exit(0)
sys.exit('no matching receive output for ' + addr)
" "$1"
}

CH_URL="http://127.0.0.1:18123/?database=chainwatch"
CH_AUTH="ingestor:regtestonly"
ch_select() { curl -s -u "$CH_AUTH" "$CH_URL" --data-binary "$1 FORMAT JSONEachRow"; }

flows_seen() {
  ch_select "SELECT count() AS n FROM flows WHERE direction='in' AND txid='$1' AND address='$2'" \
    | python3 -c "import sys,json; l=sys.stdin.readline(); print(json.loads(l)['n'] if l.strip() else 0)"
}

INGESTOR_PID=""
cleanup() {
  if [ -n "$INGESTOR_PID" ] && kill -0 "$INGESTOR_PID" 2>/dev/null; then
    kill -INT "$INGESTOR_PID" 2>/dev/null || true
    for _ in 1 2 3 4 5; do kill -0 "$INGESTOR_PID" 2>/dev/null || break; sleep 1; done
    kill -9 "$INGESTOR_PID" 2>/dev/null || true
  fi
  echo "--- ingestor log: $LOGFILE ---"
  tail -n 30 "$LOGFILE" 2>/dev/null || true
  $COMPOSE rm -sf clickhouse-regtest > /dev/null 2>&1 || true
}
trap cleanup EXIT

echo "=== bringing up regtest nodes and disposable ClickHouse ==="
$COMPOSE up -d btc1 btc2 > /dev/null
$COMPOSE rm -sf clickhouse-regtest > /dev/null 2>&1 || true
$COMPOSE up -d clickhouse-regtest > /dev/null

echo "waiting for clickhouse-regtest to accept connections..."
for i in $(seq 1 30); do
  curl -s -o /dev/null "http://127.0.0.1:18123/ping" && break
  sleep 1
  [ "$i" = "30" ] && { echo "FAIL - clickhouse-regtest did not come up"; exit 1; }
done

echo "applying regtest ingestor user..."
$COMPOSE exec -T clickhouse-regtest clickhouse-client --multiquery < "$ROOT/regtest/clickhouse-regtest-user.sql"

echo "=== ensuring btc1 is funded ==="
b1 loadwallet "test" > /dev/null 2>&1 || b1 createwallet "test" > /dev/null 2>&1 || true
b1 setnetworkactive true > /dev/null 2>&1 || true
sleep 1
b1 addnode "btc2:18444" "onetry" > /dev/null 2>&1 || true
sleep 3

BAL=$(b1 getbalance)
if python3 -c "exit(0 if $BAL < 1 else 1)"; then
  echo "funding btc1 wallet..."
  FUND_ADDR=$(b1 getnewaddress)
  b1 generatetoaddress 111 "$FUND_ADDR" > /dev/null
  sleep 2
fi

ENV_VARS=(
  RPC_HOST=127.0.0.1 RPC_PORT=18443 RPC_USER=chainwatch RPC_PASSWORD=regtestonly
  ZMQ_HOST=127.0.0.1 ZMQ_RAWTX_PORT=18532 ZMQ_SEQUENCE_PORT=18535
  CH_HOST=127.0.0.1 CH_PORT=18123 CH_USER=ingestor CH_PASSWORD=regtestonly CH_DATABASE=chainwatch
)

echo "=== starting the ingestor against btc1 ==="
(
  cd "$INGESTOR_DIR"
  exec env PYTHONUNBUFFERED=1 "${ENV_VARS[@]}" .venv/bin/python main.py
) > "$LOGFILE" 2>&1 &
INGESTOR_PID=$!

for i in $(seq 1 20); do
  grep -q "RPC connected" "$LOGFILE" 2>/dev/null && break
  kill -0 "$INGESTOR_PID" 2>/dev/null || { echo "FAIL - ingestor exited early, see log"; exit 1; }
  sleep 1
  [ "$i" = "20" ] && { echo "FAIL - ingestor did not report RPC connected"; exit 1; }
done
echo "ingestor running, pid=$INGESTOR_PID"

echo "=== watching a fresh address ==="
WATCHED=$(b1 getnewaddress)
env "${ENV_VARS[@]}" "$INGESTOR_DIR/.venv/bin/python" "$INGESTOR_DIR/watchlist_cli.py" add "$WATCHED" --min-value 0 --trace-depth 1

echo "=== funding it with three separate UTXOs, 0.001 BTC each ==="
FUND_TXID_1=$(b1 sendtoaddress "$WATCHED" 0.001)
FUND_TXID_2=$(b1 sendtoaddress "$WATCHED" 0.001)
FUND_TXID_3=$(b1 sendtoaddress "$WATCHED" 0.001)
echo "funding txids: $FUND_TXID_1 $FUND_TXID_2 $FUND_TXID_3"

echo "mining the funding transactions so their outputs are resolvable via gettxout..."
b1 generatetoaddress 1 "$(b1 getnewaddress)" > /dev/null

VOUT_1=$(b1 gettransaction "$FUND_TXID_1" | find_vout_for_address "$WATCHED")
VOUT_2=$(b1 gettransaction "$FUND_TXID_2" | find_vout_for_address "$WATCHED")
VOUT_3=$(b1 gettransaction "$FUND_TXID_3" | find_vout_for_address "$WATCHED")
echo "vouts: $VOUT_1 $VOUT_2 $VOUT_3"

echo "waiting for the ingestor to observe and confirm the funding transactions..."
for i in $(seq 1 30); do
  N=$(curl -s -u ingestor:regtestonly "$CH_URL" --data-binary \
      "SELECT count() AS n FROM flows WHERE direction='out' AND address='$WATCHED' FORMAT JSONEachRow" \
      | python3 -c "import sys,json; l=sys.stdin.readline(); print(json.loads(l)['n'] if l.strip() else 0)")
  [ "$N" -ge 3 ] && break
  sleep 1
  [ "$i" = "30" ] && { echo "FAIL - ingestor never observed all three funding outputs (saw $N)"; exit 1; }
done
echo "confirmed: ingestor observed all three funding outputs"

echo "=== draining: all three inputs, one output, no change back to WATCHED ==="
OTHER=$(b1 getnewaddress)
# 3 x 0.001 BTC = 300,000 sats in, minus a 1,000 sat fee, all to OTHER --
# nothing back to WATCHED at all.
INPUTS="[{\"txid\":\"$FUND_TXID_1\",\"vout\":$VOUT_1},{\"txid\":\"$FUND_TXID_2\",\"vout\":$VOUT_2},{\"txid\":\"$FUND_TXID_3\",\"vout\":$VOUT_3}]"
RAW=$(b1 createrawtransaction "$INPUTS" "{\"$OTHER\":0.00299000}")
SIGNED=$(b1 signrawtransactionwithwallet "$RAW" | jfield "['hex']")
DRAIN_TXID=$(b1 sendrawtransaction "$SIGNED")
echo "drain_txid=$DRAIN_TXID"

b1 generatetoaddress 1 "$(b1 getnewaddress)" > /dev/null

echo "waiting for the ingestor to observe the drain transaction's inputs..."
for i in $(seq 1 30); do
  N=$(flows_seen "$DRAIN_TXID" "$WATCHED")
  [ "$N" -ge 3 ] && break
  sleep 1
  [ "$i" = "30" ] && { echo "FAIL - ingestor never resolved the drain tx's inputs against $WATCHED (saw $N of 3)"; exit 1; }
done
echo "confirmed: drain transaction's three inputs resolved against $WATCHED"

echo "=== running detection/wallet_drain.py ==="
(
  cd "$DETECTION_DIR"
  env "${ENV_VARS[@]}" .venv/bin/python wallet_drain.py --once
)

echo "=== querying alerts directly ==="
RESULT=$(ch_select "SELECT alert_id, address, rule, severity, txid, value, confidence, is_shadow, detail FROM alerts WHERE rule='wallet_drain' AND address='$WATCHED'")
if [ -z "$RESULT" ]; then
  echo "FAIL - no wallet_drain alert found for $WATCHED"
  exit 1
fi
echo "$RESULT" | python3 -m json.tool 2>/dev/null || echo "$RESULT"

SEVERITY=$(echo "$RESULT" | python3 -c "import sys,json; print(json.loads(sys.stdin.readline())['severity'])")
CONFIDENCE=$(echo "$RESULT" | python3 -c "import sys,json; print(json.loads(sys.stdin.readline())['confidence'])")
IS_SHADOW=$(echo "$RESULT" | python3 -c "import sys,json; print(json.loads(sys.stdin.readline())['is_shadow'])")
ALERT_TXID=$(echo "$RESULT" | python3 -c "import sys,json; print(json.loads(sys.stdin.readline())['txid'])")

if [ "$SEVERITY" = "critical" ] && [ "$CONFIDENCE" = "7" ] && [ "$IS_SHADOW" = "1" ] && [ "$ALERT_TXID" = "$DRAIN_TXID" ]; then
  echo "PASS - detection-wallet-drain-test: shadow alert written for the drain transaction, severity=critical confidence=7 is_shadow=1, reasoning visible in detail"
else
  echo "FAIL - alert row present but fields unexpected: severity=$SEVERITY confidence=$CONFIDENCE is_shadow=$IS_SHADOW txid=$ALERT_TXID (expected txid=$DRAIN_TXID)"
  exit 1
fi
