#!/usr/bin/env bash
# Runs the actual ingestor (ingestor/main.py) against the regtest nodes,
# watches an address via ingestor/watchlist_cli.py, sends funds to it, then
# spends from it, and asserts a [watchlist] MATCH is logged for both sides --
# the reproducible, on-demand counterpart to a live-mainnet observation.
#
# Deliberately exercises two different code paths:
#   1. The watch is added AFTER the ingestor is already running, with a
#      short refresh interval, to prove the periodic reload actually works
#      and a restart isn't required for a new watch to take effect.
#   2. Funds are sent TO the watched address (output-side match, proven on
#      mempool arrival), the funding tx is mined so its output is resolvable
#      via gettxout(include_mempool=false), then that exact output is spent
#      FROM it via a precisely constructed raw transaction (input-side
#      match) -- docs/02-architecture.md and the phase 4a brief are explicit
#      that both sides matter equally. Spending it before it confirms would
#      only prove the chained-unconfirmed case (address unresolved, correctly
#      skipped), not a real input-side match.
#
# Uses the same disposable clickhouse-regtest container as
# regtest/ingestor-rollback-test.sh, for the same reason: synthetic regtest
# addresses must never land in the real chainwatch database.
set -euo pipefail

ROOT="$HOME/chainwatch"
COMPOSE="docker compose -f $ROOT/docker-compose.regtest.yml"
INGESTOR_DIR="$ROOT/ingestor"
LOGFILE="$(mktemp -t ingestor-watchlist-test.XXXXXX.log)"

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

amount_for_vout() {
  python3 -c "
import sys, json
d = json.load(sys.stdin)
vout = int(sys.argv[1])
for det in d['details']:
    if det.get('vout') == vout and det.get('category') == 'receive':
        print(det['amount'])
        sys.exit(0)
sys.exit('no matching receive amount for vout ' + str(vout))
" "$1"
}

INGESTOR_PID=""
cleanup() {
  if [ -n "$INGESTOR_PID" ] && kill -0 "$INGESTOR_PID" 2>/dev/null; then
    kill -INT "$INGESTOR_PID" 2>/dev/null || true
    for _ in 1 2 3 4 5; do kill -0 "$INGESTOR_PID" 2>/dev/null || break; sleep 1; done
    kill -9 "$INGESTOR_PID" 2>/dev/null || true
  fi
  echo "--- ingestor log: $LOGFILE ---"
  tail -n 40 "$LOGFILE" 2>/dev/null || true
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

echo "=== starting the ingestor against btc1 (no watches yet, 3s refresh interval) ==="
(
  cd "$INGESTOR_DIR"
  exec env PYTHONUNBUFFERED=1 WATCHLIST_REFRESH_SECONDS=3 "${ENV_VARS[@]}" .venv/bin/python main.py
) > "$LOGFILE" 2>&1 &
INGESTOR_PID=$!

for i in $(seq 1 20); do
  grep -q "RPC connected" "$LOGFILE" 2>/dev/null && break
  kill -0 "$INGESTOR_PID" 2>/dev/null || { echo "FAIL - ingestor exited early, see log"; exit 1; }
  sleep 1
  [ "$i" = "20" ] && { echo "FAIL - ingestor did not report RPC connected"; exit 1; }
done
grep -q "\[watchlist\] loaded 0 active" "$LOGFILE" && echo "confirmed: started with zero watches"

echo "=== adding a watch while the ingestor is already running ==="
WATCHED=$(b1 getnewaddress)
env "${ENV_VARS[@]}" "$INGESTOR_DIR/.venv/bin/python" "$INGESTOR_DIR/watchlist_cli.py" add "$WATCHED" --min-value 0 --trace-depth 1

echo "waiting for the periodic refresh (3s interval) to pick it up..."
for i in $(seq 1 10); do
  grep -q "\[watchlist\] loaded 1 active" "$LOGFILE" && break
  sleep 1
  [ "$i" = "10" ] && { echo "FAIL - watchlist refresh never picked up the new watch"; exit 1; }
done
echo "confirmed: refresh picked up the new watch without a restart"

echo "=== sending funds TO the watched address (output-side match) ==="
FUND_TXID=$(b1 sendtoaddress "$WATCHED" 1)
echo "fund_txid=$FUND_TXID"

for i in $(seq 1 20); do
  grep -q "\[watchlist\] MATCH .*txid=$FUND_TXID side=output .*address=$WATCHED" "$LOGFILE" && break
  sleep 1
  [ "$i" = "20" ] && { echo "FAIL - no output-side match logged for $WATCHED"; exit 1; }
done
echo "PASS - output-side match logged"

echo "confirming the funding transaction: an unconfirmed parent's output isn't"
echo "resolvable via gettxout(include_mempool=false) (docs/04-ingestion.md) --"
echo "spending it before it confirms would correctly show address=None (parent"
echo "pending), which the matcher correctly skips. That's not an input-side"
echo "match test, it's the chained-unconfirmed case, so mine it first."
b1 generatetoaddress 1 "$(b1 getnewaddress)" > /dev/null

echo "=== spending FROM the watched address (input-side match) ==="
gt=$(b1 gettransaction "$FUND_TXID")
VOUT=$(echo "$gt" | find_vout_for_address "$WATCHED")
AMT=$(echo "$gt" | amount_for_vout "$VOUT")
FEE="0.0001"
SENDAMT=$(python3 -c "print(f'{$AMT - $FEE:.8f}')")
OTHER=$(b1 getnewaddress)
RAW=$(b1 createrawtransaction "[{\"txid\":\"$FUND_TXID\",\"vout\":$VOUT}]" "{\"$OTHER\":$SENDAMT}")
SIGNED=$(b1 signrawtransactionwithwallet "$RAW" | jfield "['hex']")
SPEND_TXID=$(b1 sendrawtransaction "$SIGNED")
echo "spend_txid=$SPEND_TXID (spends $WATCHED:$VOUT)"

for i in $(seq 1 20); do
  grep -q "\[watchlist\] MATCH .*txid=$SPEND_TXID side=input .*address=$WATCHED" "$LOGFILE" && break
  sleep 1
  [ "$i" = "20" ] && { echo "FAIL - no input-side match logged for $WATCHED"; exit 1; }
done
echo "PASS - ingestor-watchlist-test: matched on both output and input sides of $WATCHED, live-refresh confirmed without restart"
