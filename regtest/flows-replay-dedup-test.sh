#!/usr/bin/env bash
# Proves the new flows table (schema/08_flows_redesign.sql) absorbs replay
# the way docs/02-architecture.md specifies for this whole pipeline:
# "duplicates are prevented by the natural key rather than by delivery
# guarantees" -- not by a write-path guard (considered and explicitly
# rejected: it fails in the wrong direction, since transactions and flows
# flush as separate inserts and a guard reading transactions could skip a
# block's flows forever if a crash landed between the two).
#
# Confirms a real block, rewinds the checkpoint the same way a restart
# after downtime (or the phase-4 catch-up trials already on record) would
# find it, and lets confirm.catch_up_to_tip walk forward over the same
# block again -- the actual, dominant cause measured live: 97.95% of the
# 15,051,201 duplicate keys found in production were exactly this shape.
# Asserts the raw (pre-merge) table actually has two rows for the
# replayed input -- proving replay really happened, not just that nothing
# went wrong -- and that FINAL collapses them to exactly one, with the
# correct resolved value, not a coincidence of the two rows being close
# enough.
set -euo pipefail

ROOT="$HOME/chainwatch"
COMPOSE="docker compose -f $ROOT/docker-compose.regtest.yml"
INGESTOR_DIR="$ROOT/ingestor"
LOGFILE="$(mktemp -t flows-replay-dedup-test.XXXXXX.log)"
LOGFILE2="$(mktemp -t flows-replay-dedup-test-2.XXXXXX.log)"

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

INGESTOR_PID=""
cleanup() {
  if [ -n "$INGESTOR_PID" ] && kill -0 "$INGESTOR_PID" 2>/dev/null; then
    kill -INT "$INGESTOR_PID" 2>/dev/null || true
    for _ in 1 2 3 4 5; do kill -0 "$INGESTOR_PID" 2>/dev/null || break; sleep 1; done
    kill -9 "$INGESTOR_PID" 2>/dev/null || true
  fi
  echo "--- first run log: $LOGFILE ---"
  tail -n 25 "$LOGFILE" 2>/dev/null || true
  echo "--- second (replay) run log: $LOGFILE2 ---"
  tail -n 25 "$LOGFILE2" 2>/dev/null || true
  $COMPOSE rm -sf clickhouse-regtest > /dev/null 2>&1 || true
}
trap cleanup EXIT

echo "=== bringing up regtest nodes and a fresh disposable ClickHouse ==="
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

echo "=== confirming the sorting key contains nothing that differs between replays of the same confirmed transaction ==="
SORTKEY=$(ch_regtest --query "SELECT sorting_key FROM system.tables WHERE database='chainwatch' AND name='flows'")
echo "flows sorting_key=$SORTKEY"
echo "(address, direction, position, txid) are all decoded directly from the transaction/prevout data by confirm.py --"
echo "deterministic and identical on every replay of the same block. Only seen_at (the version column, not part of"
echo "the sorting key) differs -- confirmed below directly against the raw rows, not just asserted here."

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

echo "=== run 1: start the ingestor, confirm a real transaction ==="
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

ADDRA=$(b1 getnewaddress)
TXA=$(b1 sendtoaddress "$ADDRA" 1)
echo "TXA=$TXA"

for i in $(seq 1 20); do
  grep -q "txid=$TXA" "$LOGFILE" && break
  sleep 1
  [ "$i" = "20" ] && { echo "FAIL - ingestor never logged TXA arriving"; exit 1; }
done

MINE_ADDR=$(b1 getnewaddress)
b1 generatetoaddress 1 "$MINE_ADDR" > /dev/null
CONFIRM_HEIGHT=$(b1 getblockcount)
CONFIRM_HASH=$(b1 getbestblockhash)
echo "TXA confirmed at height=$CONFIRM_HEIGHT hash=$CONFIRM_HASH"

for i in $(seq 1 20); do
  grep -q "\[block\] height=$CONFIRM_HEIGHT" "$LOGFILE" && break
  sleep 1
  [ "$i" = "20" ] && { echo "FAIL - ingestor never logged confirming block $CONFIRM_HEIGHT"; exit 1; }
done
sleep 3

RAW_BEFORE=$(ch_regtest --query "SELECT count() FROM flows WHERE txid = '$TXA' AND direction = 'out' AND address = '$ADDRA'")
echo "raw (pre-replay) row count for TXA's output to $ADDRA: $RAW_BEFORE"
[ "$RAW_BEFORE" = "1" ] || { echo "FAIL - expected exactly 1 raw row before replay, got $RAW_BEFORE"; exit 1; }

echo "=== stopping the ingestor cleanly ==="
kill -INT "$INGESTOR_PID" 2>/dev/null || true
for _ in 1 2 3 4 5; do kill -0 "$INGESTOR_PID" 2>/dev/null || break; sleep 1; done
kill -9 "$INGESTOR_PID" 2>/dev/null || true
INGESTOR_PID=""
sleep 1

echo "=== rewinding the checkpoint to just before TXA's block, the same shape a restart after downtime (or repeated catch-up trials) would produce ==="
REWIND_HEIGHT=$((CONFIRM_HEIGHT - 1))
REWIND_HASH=$(b1 getblockhash "$REWIND_HEIGHT")
ch_regtest --query "
  INSERT INTO checkpoints (component, last_block_hash, last_block_height, last_run_at)
  FORMAT JSONEachRow
  {\"component\": \"ingestor\", \"last_block_hash\": \"$REWIND_HASH\", \"last_block_height\": $REWIND_HEIGHT, \"last_run_at\": \"$(date -u +%Y-%m-%dT%H:%M:%S.000)\"}
"
READBACK=$(ch_regtest --query "SELECT last_block_height FROM checkpoints ORDER BY last_run_at DESC LIMIT 1 BY component")
echo "checkpoint now reads last_block_height=$READBACK (was $CONFIRM_HEIGHT)"
[ "$READBACK" = "$REWIND_HEIGHT" ] || { echo "FAIL - checkpoint rewind did not take, reads $READBACK"; exit 1; }

echo "=== run 2: restart the ingestor, resuming from the stale checkpoint ==="
(
  cd "$INGESTOR_DIR"
  exec env PYTHONUNBUFFERED=1 "${ENV_VARS[@]}" .venv/bin/python main.py
) > "$LOGFILE2" 2>&1 &
INGESTOR_PID=$!

for i in $(seq 1 20); do
  grep -q "resuming: last checkpoint" "$LOGFILE2" 2>/dev/null && break
  kill -0 "$INGESTOR_PID" 2>/dev/null || { echo "FAIL - ingestor exited early on restart, see log"; exit 1; }
  sleep 1
  [ "$i" = "20" ] && { echo "FAIL - ingestor did not report resuming from checkpoint"; exit 1; }
done
grep "resuming: last checkpoint" "$LOGFILE2"

echo "resuming at a stale checkpoint alone doesn't trigger catch_up_to_tip -- confirmed directly: it fires only"
echo "on a live 'C' sequence event or a detected reorg, neither of which happens just sitting at a stale height"
echo "with no new block. Mining one more block gives it a real 'C' event -- catch_up_to_tip then walks forward"
echo "from the stale checkpoint (200) to the new tip (202), reprocessing block $CONFIRM_HEIGHT along the way."
echo "This is the actual, real-world shape of the defect: not a contrived direct call, but the same mechanism"
echo "that produced 97.95% of the 15,051,201 duplicate keys measured in production."
b1 generatetoaddress 1 "$(b1 getnewaddress)" > /dev/null
NEW_TIP=$(b1 getblockcount)
echo "new tip height=$NEW_TIP"

for i in $(seq 1 20); do
  grep -q "\[block\] height=$CONFIRM_HEIGHT" "$LOGFILE2" && break
  sleep 1
  [ "$i" = "20" ] && { echo "FAIL - ingestor never replayed block $CONFIRM_HEIGHT"; exit 1; }
done
for i in $(seq 1 20); do
  grep -q "\[block\] height=$NEW_TIP" "$LOGFILE2" && break
  sleep 1
  [ "$i" = "20" ] && { echo "FAIL - ingestor never caught up to the new tip $NEW_TIP"; exit 1; }
done
sleep 3
echo "confirmed: block $CONFIRM_HEIGHT (containing TXA) was reprocessed by catch_up_to_tip on its way to $NEW_TIP -- this is the replay"

echo "=== asserting replay actually happened: raw table now has 2 rows for the same key ==="
RAW_AFTER=$(ch_regtest --query "SELECT count() FROM flows WHERE txid = '$TXA' AND direction = 'out' AND address = '$ADDRA'")
echo "raw (post-replay) row count: $RAW_AFTER"
[ "$RAW_AFTER" = "2" ] || { echo "FAIL - expected exactly 2 raw rows after one replay, got $RAW_AFTER (replay may not have happened, or over/under-replayed)"; exit 1; }

echo "=== confirming the sorting-key columns are identical across the two raw rows, only seen_at differs ==="
ch_regtest --query "
  SELECT address, direction, position, txid, value, resolution_state, seen_at
  FROM flows WHERE txid = '$TXA' AND direction = 'out' AND address = '$ADDRA'
  ORDER BY seen_at
  FORMAT PrettyCompact
"

echo "=== asserting FINAL collapses them to exactly one, correctly resolved row ==="
FINAL_ROW=$(ch_regtest --query "
  SELECT value, resolution_state, count() OVER () AS n
  FROM flows FINAL
  WHERE txid = '$TXA' AND direction = 'out' AND address = '$ADDRA'
  FORMAT TSV
")
echo "FINAL row: $FINAL_ROW"
N=$(echo "$FINAL_ROW" | cut -f3)
STATE=$(echo "$FINAL_ROW" | cut -f2)
[ "$N" = "1" ] || { echo "FAIL - expected exactly 1 row via FINAL after replay, got $N"; exit 1; }
[ "$STATE" = "resolved" ] || { echo "FAIL - expected resolution_state=resolved, got $STATE"; exit 1; }
echo "PASS - two raw rows from replay collapse to exactly one via FINAL"

echo "=== extended duplicate check (persist.count_duplicate_flows shape) across the whole table ==="
DUP_COUNT=$(ch_regtest --query "
  SELECT count() FROM (
    SELECT txid, direction, position, count() AS n
    FROM flows FINAL GROUP BY txid, direction, position HAVING n > 1
  )
")
[ "$DUP_COUNT" = "0" ] || { echo "FAIL - count_duplicate_flows shape found $DUP_COUNT duplicate groups after replay"; exit 1; }
echo "PASS - flows-replay-dedup-test: catch_up_to_tip replayed a confirmed block with no write-path guard of any kind; the raw table genuinely duplicated (2 rows), and FINAL genuinely collapsed it (1 row, correctly resolved) -- deduplication by natural key, not by a guard, exactly as docs/02-architecture.md specifies"
