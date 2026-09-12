#!/usr/bin/env bash
# Runs the actual ingestor (ingestor/main.py) against the regtest nodes,
# confirms a transaction, orphans its block, and asserts the ClickHouse row
# went back to pending -- the docs/08-build-plan.md 3d definition of done:
# "a forced reorg on regtest is detected, rolled back correctly, and
# reprocessed", tested rather than inspected.
#
# Also proves alert invalidation: nothing generates alerts yet (phase 4), so
# this manually inserts one row referencing the doomed block and asserts
# `invalidated` flips to 1 after rollback.
#
# Uses a disposable clickhouse-regtest container (docker-compose.regtest.yml)
# rather than the real chainwatch ClickHouse, so synthetic regtest txids
# never land in real fraud-analytics data.
set -euo pipefail

ROOT="$HOME/chainwatch"
COMPOSE="docker compose -f $ROOT/docker-compose.regtest.yml"
INGESTOR_DIR="$ROOT/ingestor"
LOGFILE="$(mktemp -t ingestor-rollback-test.XXXXXX.log)"

b1() { $COMPOSE exec -T btc1 bitcoin-cli -conf=/config/bitcoin.conf "$@"; }
b2() { $COMPOSE exec -T btc2 bitcoin-cli -conf=/config/bitcoin.conf "$@"; }
jfield() { python3 -c "import sys,json; print(json.load(sys.stdin)$1)"; }

CH_URL="http://127.0.0.1:18123/?database=chainwatch"
CH_AUTH="ingestor:regtestonly"
ch_select() { curl -s -u "$CH_AUTH" "$CH_URL" --data-binary "$1 FORMAT JSONEachRow"; }
ch_insert() { curl -s -u "$CH_AUTH" "$CH_URL" --data-binary "$(printf 'INSERT INTO %s FORMAT JSONEachRow\n%s' "$1" "$2")"; }

tx_status() {
  ch_select "SELECT status FROM transactions FINAL WHERE txid = '$1'" \
    | python3 -c "import sys,json; l=sys.stdin.readline(); print(json.loads(l)['status'] if l.strip() else '')"
}

alert_invalidated() {
  ch_select "SELECT invalidated FROM alerts WHERE alert_id = '$1'" \
    | python3 -c "import sys,json; l=sys.stdin.readline(); print(json.loads(l)['invalidated'] if l.strip() else '')"
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

echo "=== ensuring btc1/btc2 are connected and funded ==="
b1 loadwallet "test" > /dev/null 2>&1 || b1 createwallet "test" > /dev/null 2>&1 || true
b2 loadwallet "test2" > /dev/null 2>&1 || b2 createwallet "test2" > /dev/null 2>&1 || true
b1 setnetworkactive true > /dev/null 2>&1 || true
sleep 1
b1 addnode "btc2:18444" "onetry" > /dev/null 2>&1 || true
sleep 3

BAL=$(b1 getbalance)
if python3 -c "exit(0 if $BAL < 1 else 1)"; then
  echo "funding btc1 wallet..."
  FUND_ADDR=$(b1 getnewaddress)
  b1 generatetoaddress 111 "$FUND_ADDR" > /dev/null
  b1 addnode "btc2:18444" "onetry" > /dev/null 2>&1 || true
  sleep 5
fi

echo "=== starting the ingestor against btc1 ==="
(
  cd "$INGESTOR_DIR"
  exec env PYTHONUNBUFFERED=1 \
    RPC_HOST=127.0.0.1 RPC_PORT=18443 RPC_USER=chainwatch RPC_PASSWORD=regtestonly \
    ZMQ_HOST=127.0.0.1 ZMQ_RAWTX_PORT=18532 ZMQ_SEQUENCE_PORT=18535 \
    CH_HOST=127.0.0.1 CH_PORT=18123 CH_USER=ingestor CH_PASSWORD=regtestonly CH_DATABASE=chainwatch \
    .venv/bin/python main.py
) > "$LOGFILE" 2>&1 &
INGESTOR_PID=$!

for i in $(seq 1 20); do
  grep -q "RPC connected" "$LOGFILE" 2>/dev/null && break
  kill -0 "$INGESTOR_PID" 2>/dev/null || { echo "FAIL - ingestor exited early, see log"; exit 1; }
  sleep 1
  [ "$i" = "20" ] && { echo "FAIL - ingestor did not report RPC connected"; exit 1; }
done
echo "ingestor running, pid=$INGESTOR_PID"

echo "=== splitting the network, then confirming a transaction on the isolated side ==="
# Split BEFORE creating the transaction, not after -- matching
# scenarios.sh's reorg-with-transactions. Splitting afterwards would let
# btc2 sync the doomed block over P2P before the split takes effect, so
# btc2's later "competing" blocks would just extend the same chain rather
# than fork from before it -- no reorg would be possible at all.
A1=$(b1 getnewaddress)
A2=$(b2 getnewaddress)
ADDR=$(b1 getnewaddress)

b1 setnetworkactive false > /dev/null
sleep 2

TXID=$(b1 sendtoaddress "$ADDR" 1)
b1 generatetoaddress 1 "$A1" > /dev/null
DOOMED=$(b1 getbestblockhash)
echo "txid=$TXID  doomed_block=$DOOMED"

echo "waiting for the ingestor to observe confirmation..."
STATUS=""
for i in $(seq 1 30); do
  STATUS=$(tx_status "$TXID")
  [ "$STATUS" = "confirmed" ] && break
  sleep 1
done
if [ "$STATUS" != "confirmed" ]; then
  echo "FAIL - ingestor never confirmed $TXID (last status='$STATUS')"
  exit 1
fi
echo "confirmed: status=$STATUS"

echo "inserting a manual alert row referencing the doomed block..."
ALERT_ID=$(python3 -c "import uuid; print(uuid.uuid4())")
WATCH_ID=$(python3 -c "import uuid; print(uuid.uuid4())")
NOW=$(python3 -c "from datetime import datetime,timezone; print(datetime.now(timezone.utc).strftime('%Y-%m-%d %H:%M:%S.%f')[:-3])")
ALERT_JSON=$(printf '{"alert_id":"%s","watch_id":"%s","address":"%s","rule":"watchlist_movement","severity":"high","txid":"%s","block_hash":"%s","value":100000000,"detail":"{}","confidence":90,"is_shadow":0,"created_at":"%s","acknowledged":0,"invalidated":0}' \
  "$ALERT_ID" "$WATCH_ID" "$ADDR" "$TXID" "$DOOMED" "$NOW")
ch_insert alerts "$ALERT_JSON"
echo "alert_id=$ALERT_ID"

echo "orphaning the doomed block: mining a longer competing chain on btc2, still split..."
b2 generatetoaddress 3 "$A2" > /dev/null
b1 setnetworkactive true > /dev/null
sleep 2
b1 addnode "btc2:18444" "onetry" > /dev/null 2>&1 || true
sleep 8

CONF_DOOMED=$(b1 getblock "$DOOMED" | jfield "['confirmations']")
echo "doomed block confirmations after reconnect: $CONF_DOOMED"
if [ "$CONF_DOOMED" != "-1" ]; then
  echo "FAIL - reorg did not happen on btc1 (doomed block confirmations=$CONF_DOOMED, expected -1)"
  exit 1
fi

echo "=== waiting for the ingestor to detect and roll back ==="
FINAL_STATUS=""
FINAL_INVALIDATED=""
for i in $(seq 1 40); do
  FINAL_STATUS=$(tx_status "$TXID")
  FINAL_INVALIDATED=$(alert_invalidated "$ALERT_ID")
  if [ "$FINAL_STATUS" = "pending" ] && [ "$FINAL_INVALIDATED" = "1" ]; then
    break
  fi
  sleep 2
done

echo "final: tx_status=$FINAL_STATUS alert_invalidated=$FINAL_INVALIDATED"
if [ "$FINAL_STATUS" = "pending" ] && [ "$FINAL_INVALIDATED" = "1" ]; then
  echo "PASS - ingestor-rollback-test: confirmed tx reverted to pending and its alert invalidated after the block it was in was orphaned"
else
  echo "FAIL - ingestor-rollback-test: expected status=pending and invalidated=1; got status='$FINAL_STATUS' invalidated='$FINAL_INVALIDATED'"
  exit 1
fi
