#!/usr/bin/env bash
# Proves the flows redesign (schema/08_flows_redesign.sql,
# ingestor/persist.py) against a real chained-unconfirmed spend, the same
# shape regtest/scenarios.sh's chained-unconfirmed scenario already proves
# at the RPC level -- this proves it end to end through the actual
# ingestor's writes to `flows`, not just bitcoind's own view.
#
# TXA (parent) enters the mempool unconfirmed. TXB (child) spends TXA's
# output while TXA is still unconfirmed -- resolve_input classifies TXB's
# input as parent_pending, and under the new design that means NO flows
# row is written yet (asserted directly). TXA and TXB are then mined
# together in one block (regtest's generatetoaddress includes the whole
# eligible mempool, and TXB became fully eligible the moment TXA entered
# the mempool). confirm.process_block resolves TXB's input via getblock
# verbosity 3's embedded prevout and writes exactly one flows row --
# asserted via FINAL, with its address/value checked against the real
# resolved values, not placeholders.
#
# Same disposable clickhouse-regtest container as ingestor-watchlist-test.sh
# and ingestor-rollback-test.sh, for the same reason: synthetic regtest
# data must never land in the real chainwatch database. No persistent
# volume on clickhouse-regtest, so removing and recreating it applies
# schema/*.sql fresh, including 08_flows_redesign.sql.
set -euo pipefail

ROOT="$HOME/chainwatch"
COMPOSE="docker compose -f $ROOT/docker-compose.regtest.yml"
INGESTOR_DIR="$ROOT/ingestor"
LOGFILE="$(mktemp -t flows-dedup-test.XXXXXX.log)"

b1() { $COMPOSE exec -T btc1 bitcoin-cli -conf=/config/bitcoin.conf "$@"; }
ch_regtest() { $COMPOSE exec -T clickhouse-regtest clickhouse-client --database chainwatch "$@"; }
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

echo "=== bringing up regtest nodes and a fresh disposable ClickHouse (applies schema/*.sql, including 08_flows_redesign.sql) ==="
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

echo "=== confirming flows has the new engine/ordering, no block_height column ==="
ENGINE=$(ch_regtest --query "SELECT engine FROM system.tables WHERE database='chainwatch' AND name='flows'")
SORTKEY=$(ch_regtest --query "SELECT sorting_key FROM system.tables WHERE database='chainwatch' AND name='flows'")
echo "flows engine=$ENGINE sorting_key=$SORTKEY"
[ "$ENGINE" = "ReplacingMergeTree" ] || { echo "FAIL - expected ReplacingMergeTree, got $ENGINE"; exit 1; }
echo "$SORTKEY" | grep -q "^address, direction, position, txid$" || { echo "FAIL - unexpected sorting key: $SORTKEY"; exit 1; }
if ch_regtest --query "DESCRIBE flows" | grep -q "block_height"; then
  echo "FAIL - block_height column still present on flows"; exit 1
fi
echo "confirmed: ReplacingMergeTree(seen_at), ORDER BY (address, direction, position, txid), no block_height column"

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

echo "=== creating the chained unconfirmed spend: TXA (parent, unconfirmed) -> TXB (child, spends TXA) ==="
ADDRA=$(b1 getnewaddress)
ADDRB=$(b1 getnewaddress)

TXA=$(b1 sendtoaddress "$ADDRA" 1)
gt=$(b1 gettransaction "$TXA")
VOUTA=$(echo "$gt" | find_vout_for_address "$ADDRA")
AMTA=$(echo "$gt" | amount_for_vout "$VOUTA")

FEE="0.0001"
SENDAMT=$(python3 -c "print(f'{$AMTA - $FEE:.8f}')")
RAW=$(b1 createrawtransaction "[{\"txid\":\"$TXA\",\"vout\":$VOUTA}]" "{\"$ADDRB\":$SENDAMT}")
SIGNED=$(b1 signrawtransactionwithwallet "$RAW" | jfield "['hex']")
TXB=$(b1 sendrawtransaction "$SIGNED")

echo "TXA=$TXA (vout $VOUTA, unconfirmed)  TXB=$TXB (spends TXA:$VOUTA, chained unconfirmed)"

echo "waiting for the ingestor to see both TXA and TXB arrive in the mempool..."
for i in $(seq 1 20); do
  grep -q "txid=$TXA" "$LOGFILE" && grep -q "txid=$TXB" "$LOGFILE" && break
  sleep 1
  [ "$i" = "20" ] && { echo "FAIL - ingestor never logged both TXA and TXB"; exit 1; }
done
grep "txid=$TXB" "$LOGFILE" | grep -q "pending=1" && echo "confirmed: ingestor classified TXB's input as parent_pending (TXA still unconfirmed)"

echo "=== asserting no flows row exists yet for TXB's input (deferred, not a placeholder) ==="
sleep 3  # let a flush cycle pass
PRE_COUNT=$(ch_regtest --query "SELECT count() FROM flows WHERE txid = '$TXB' AND direction = 'in' AND position = 0")
if [ "$PRE_COUNT" != "0" ]; then
  echo "FAIL - expected 0 flows rows for TXB's still-unresolved input, found $PRE_COUNT"
  exit 1
fi
echo "PASS - no flows row written for TXB's input while parent_pending (count=0)"

echo "=== mining: TXA and TXB confirm together (TXB was already mempool-eligible as TXA's descendant) ==="
MINE_ADDR=$(b1 getnewaddress)
b1 generatetoaddress 1 "$MINE_ADDR" > /dev/null

CONF_A=$(b1 gettransaction "$TXA" | jfield "['confirmations']")
CONF_B=$(b1 gettransaction "$TXB" | jfield "['confirmations']")
echo "TXA confirmations=$CONF_A  TXB confirmations=$CONF_B"
if [ "$CONF_A" -lt 1 ] || [ "$CONF_B" -lt 1 ]; then
  echo "FAIL - expected both TXA and TXB to confirm in the same block, got confirmations A=$CONF_A B=$CONF_B"
  exit 1
fi

echo "waiting for the ingestor to process the confirming block..."
for i in $(seq 1 20); do
  grep -q "\[block\] height=" "$LOGFILE" && break
  sleep 1
  [ "$i" = "20" ] && { echo "FAIL - ingestor never logged block confirmation"; exit 1; }
done
sleep 3  # let the flush cycle land the confirm-path rows

echo "=== asserting exactly one flows row for TXB's input, via FINAL ==="
ROW=$(ch_regtest --query "
  SELECT address, value, resolution_state, count() OVER () AS n
  FROM flows FINAL
  WHERE txid = '$TXB' AND direction = 'in' AND position = 0
  FORMAT TSV
")
echo "row: $ROW"
N=$(echo "$ROW" | cut -f4)
ADDR=$(echo "$ROW" | cut -f1)
VALUE=$(echo "$ROW" | cut -f2)
STATE=$(echo "$ROW" | cut -f3)

if [ "$N" != "1" ]; then
  echo "FAIL - expected exactly 1 row via FINAL, found $N"
  exit 1
fi
if [ "$ADDR" != "$ADDRA" ]; then
  echo "FAIL - expected resolved address $ADDRA, got '$ADDR'"
  exit 1
fi
if [ "$STATE" != "resolved" ]; then
  echo "FAIL - expected resolution_state=resolved, got '$STATE'"
  exit 1
fi
EXPECTED_SATS=$(python3 -c "print(round($AMTA * 100_000_000))")
if [ "$VALUE" != "$EXPECTED_SATS" ]; then
  echo "FAIL - expected value=$EXPECTED_SATS sats, got $VALUE"
  exit 1
fi
echo "PASS - exactly one flows row for TXB's input: address=$ADDR value=$VALUE sats resolution_state=$STATE"

echo "=== extended duplicate check (persist.count_duplicate_flows) ==="
DUP_COUNT=$(ch_regtest --query "
  SELECT count() FROM (
    SELECT txid, direction, position, count() AS n
    FROM flows FINAL GROUP BY txid, direction, position HAVING n > 1
  )
")
if [ "$DUP_COUNT" != "0" ]; then
  echo "FAIL - count_duplicate_flows shape found $DUP_COUNT duplicate (txid,direction,position) groups"
  exit 1
fi
echo "PASS - flows-dedup-test: no placeholder written while parent_pending, exactly one correctly-resolved row once confirmed, zero duplicates by the extended check"
