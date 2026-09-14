#!/usr/bin/env bash
# Runs the actual ingestor (ingestor/main.py) against the regtest nodes,
# watches an address, funds TEN separate fresh addresses, has each of them
# independently pay the watched address, and asserts
# detection/fan_in_consolidation.py writes a shadow alert with the source
# set visible -- the reproducible, on-demand proof that rule 3 fires, since
# no naturally-occurring high-diversity fan-in address was found in the
# live archive when this was built (see docs/08-build-plan.md, phase 4d).
#
# Ten separate source addresses are used, each funded and each spending
# from its own distinct, confirmed UTXO, rather than ten sendtoaddress
# calls from the wallet's general balance -- the latter does not guarantee
# ten DISTINCT resolved input addresses (bitcoind's coin selection could
# reuse the same UTXO's address across sends), and the whole point of this
# test is proving the distinct-source count, not just the transaction count.
#
# Uses the same disposable clickhouse-regtest container as the other
# regtest/*-test.sh scripts, for the same reason: synthetic regtest
# addresses must never land in the real chainwatch database.
set -euo pipefail

ROOT="$HOME/chainwatch"
COMPOSE="docker compose -f $ROOT/docker-compose.regtest.yml"
INGESTOR_DIR="$ROOT/ingestor"
DETECTION_DIR="$ROOT/detection"
LOGFILE="$(mktemp -t detection-fan-in-test.XXXXXX.log)"
N_SOURCES=10

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

count_in_flows() {
  ch_select "SELECT count(DISTINCT address) AS n FROM flows WHERE direction='in' AND txid IN ($1) AND address != ''" \
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

echo "=== funding $N_SOURCES separate source addresses ==="
declare -a SRC_ADDR SRC_FUND_TXID
for i in $(seq 1 "$N_SOURCES"); do
  SRC_ADDR[$i]=$(b1 getnewaddress)
  SRC_FUND_TXID[$i]=$(b1 sendtoaddress "${SRC_ADDR[$i]}" 0.001)
done
echo "funded ${N_SOURCES} source addresses"

echo "mining the funding transactions so each source's UTXO is resolvable via gettxout..."
b1 generatetoaddress 1 "$(b1 getnewaddress)" > /dev/null

echo "=== each source address independently pays the watched address ==="
declare -a DEST_TXID
for i in $(seq 1 "$N_SOURCES"); do
  VOUT=$(b1 gettransaction "${SRC_FUND_TXID[$i]}" | find_vout_for_address "${SRC_ADDR[$i]}")
  RAW=$(b1 createrawtransaction "[{\"txid\":\"${SRC_FUND_TXID[$i]}\",\"vout\":$VOUT}]" "{\"$WATCHED\":0.00099000}")
  SIGNED=$(b1 signrawtransactionwithwallet "$RAW" | jfield "['hex']")
  DEST_TXID[$i]=$(b1 sendrawtransaction "$SIGNED")
done
echo "sent ${N_SOURCES} independent payments to $WATCHED"

b1 generatetoaddress 1 "$(b1 getnewaddress)" > /dev/null

echo "=== waiting for the ingestor to resolve all $N_SOURCES source addresses in flows ==="
TXID_LIST=""
for i in $(seq 1 "$N_SOURCES"); do
  TXID_LIST="$TXID_LIST${TXID_LIST:+,}'${DEST_TXID[$i]}'"
done

for i in $(seq 1 30); do
  N=$(count_in_flows "$TXID_LIST")
  [ "$N" -ge "$N_SOURCES" ] && break
  sleep 1
  [ "$i" = "30" ] && { echo "FAIL - ingestor resolved only $N of $N_SOURCES source addresses"; exit 1; }
done
echo "confirmed: all $N_SOURCES source addresses resolved against $WATCHED's receiving transactions"

echo "=== running detection/fan_in_consolidation.py ==="
(
  cd "$DETECTION_DIR"
  env "${ENV_VARS[@]}" .venv/bin/python fan_in_consolidation.py --once
)

echo "=== querying alerts directly ==="
RESULT=$(ch_select "SELECT alert_id, address, rule, severity, txid, value, confidence, is_shadow, detail FROM alerts WHERE rule='fan_in_consolidation' AND address='$WATCHED'")
if [ -z "$RESULT" ]; then
  echo "FAIL - no fan_in_consolidation alert found for $WATCHED"
  exit 1
fi
echo "$RESULT" | python3 -m json.tool 2>/dev/null || echo "$RESULT"

SEVERITY=$(echo "$RESULT" | python3 -c "import sys,json; print(json.loads(sys.stdin.readline())['severity'])")
CONFIDENCE=$(echo "$RESULT" | python3 -c "import sys,json; print(json.loads(sys.stdin.readline())['confidence'])")
IS_SHADOW=$(echo "$RESULT" | python3 -c "import sys,json; print(json.loads(sys.stdin.readline())['is_shadow'])")
SOURCE_COUNT=$(echo "$RESULT" | python3 -c "
import sys,json
row = json.loads(sys.stdin.readline())
detail = json.loads(row['detail'])
print(detail['source_count'])
")

if [ "$SEVERITY" = "medium" ] && [ "$CONFIDENCE" = "37" ] && [ "$IS_SHADOW" = "1" ] && [ "$SOURCE_COUNT" -ge "$N_SOURCES" ]; then
  echo "PASS - detection-fan-in-test: shadow alert written, severity=medium confidence=37 is_shadow=1 source_count=$SOURCE_COUNT, reasoning visible in detail"
else
  echo "FAIL - alert row present but fields unexpected: severity=$SEVERITY confidence=$CONFIDENCE is_shadow=$IS_SHADOW source_count=$SOURCE_COUNT (expected >= $N_SOURCES)"
  exit 1
fi
