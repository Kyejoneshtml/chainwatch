#!/usr/bin/env bash
# Proves confirm.catch_up_to_tip's bounded-chunk + main.py's periodic
# self-retry (docs/08-build-plan.md, first mainnet soak run): mines more
# blocks than MAX_BLOCKS_PER_CALL in one go, starts the ingestor from a
# stale checkpoint, and asserts the first pass stops exactly at the bound
# (not the tip) and logs that backlog remains, then the periodic retry
# timer -- not a new block event -- picks up the rest on its own.
set -euo pipefail

ROOT="$HOME/chainwatch"
COMPOSE="docker compose -f $ROOT/docker-compose.regtest.yml"
INGESTOR_DIR="$ROOT/ingestor"
LOGFILE="/private/tmp/claude-501/-Users-kyejones-chainwatch/a2b4b1d4-028b-41de-87fb-e5cdcf024a61/scratchpad/catch-up-bounded-test.log"
: > "$LOGFILE"

b1() { $COMPOSE exec -T btc1 bitcoin-cli -conf=/config/bitcoin.conf "$@"; }
ch_regtest() { $COMPOSE exec -T clickhouse-regtest clickhouse-client --database chainwatch --query "$1"; }

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

echo "=== bringing up regtest nodes and a fresh disposable ClickHouse ==="
$COMPOSE up -d btc1 btc2 > /dev/null
$COMPOSE rm -sf clickhouse-regtest > /dev/null 2>&1 || true
$COMPOSE up -d clickhouse-regtest > /dev/null
for i in $(seq 1 30); do
  curl -s -o /dev/null "http://127.0.0.1:18123/ping" && break
  sleep 1
done
$COMPOSE exec -T clickhouse-regtest clickhouse-client --multiquery < "$ROOT/regtest/clickhouse-regtest-user.sql"

b1 loadwallet "test" > /dev/null 2>&1 || b1 createwallet "test" > /dev/null 2>&1 || true
b1 setnetworkactive true > /dev/null 2>&1 || true
sleep 1
b1 addnode "btc2:18444" "onetry" > /dev/null 2>&1 || true
sleep 3
BAL=$(b1 getbalance)
if python3 -c "exit(0 if $BAL < 1 else 1)"; then
  FUND_ADDR=$(b1 getnewaddress)
  b1 generatetoaddress 111 "$FUND_ADDR" > /dev/null
  sleep 2
fi

START_HEIGHT=$(b1 getblockcount)
START_HASH=$(b1 getblockhash "$START_HEIGHT")
echo "=== mining 55 blocks in one go (bound is 50) ==="
b1 generatetoaddress 55 "$(b1 getnewaddress)" > /dev/null
TIP_HEIGHT=$(b1 getblockcount)
echo "start_height=$START_HEIGHT tip_height=$TIP_HEIGHT (55 new blocks)"

echo "=== seeding the checkpoint at start_height, so the ingestor resumes 55 blocks behind ==="
docker compose -f "$ROOT/docker-compose.regtest.yml" exec -T clickhouse-regtest clickhouse-client --database chainwatch --query "
  INSERT INTO checkpoints (component, last_block_hash, last_block_height, last_run_at)
  FORMAT JSONEachRow
  {\"component\": \"ingestor\", \"last_block_hash\": \"$START_HASH\", \"last_block_height\": $START_HEIGHT, \"last_run_at\": \"$(date -u +%Y-%m-%dT%H:%M:%S.000)\"}
"

ENV_VARS=(
  RPC_HOST=127.0.0.1 RPC_PORT=18443 RPC_USER=chainwatch RPC_PASSWORD=regtestonly
  ZMQ_HOST=127.0.0.1 ZMQ_RAWTX_PORT=18532 ZMQ_SEQUENCE_PORT=18535
  CH_HOST=127.0.0.1 CH_PORT=18123 CH_USER=ingestor CH_PASSWORD=regtestonly CH_DATABASE=chainwatch
  CATCH_UP_RETRY_SECONDS=20
)

echo "=== starting the ingestor with a checkpoint already at start_height (55 blocks behind) ==="
(
  cd "$INGESTOR_DIR"
  exec env PYTHONUNBUFFERED=1 "${ENV_VARS[@]}" .venv/bin/python main.py
) > "$LOGFILE" 2>&1 &
INGESTOR_PID=$!

for i in $(seq 1 20); do
  grep -q "RPC connected" "$LOGFILE" 2>/dev/null && break
  kill -0 "$INGESTOR_PID" 2>/dev/null || { echo "FAIL - ingestor exited early, see log"; exit 1; }
  sleep 1
done

echo "waiting for the first catch-up pass to bound at 50 blocks (up to 60s -- the periodic timer fires every 20s)..."
for i in $(seq 1 60); do
  grep -qE "catch-up (.*) bounded at height=|block\] height=$TIP_HEIGHT " "$LOGFILE" && break
  sleep 1
  [ "$i" = "60" ] && { echo "FAIL - never saw the bounded-catch-up log line nor reached tip within 60s"; echo "--- full log so far ---"; cat "$LOGFILE"; exit 1; }
done
BOUND_LINE=$(grep "catch-up (.*) bounded at height=" "$LOGFILE" | head -1)
echo "$BOUND_LINE"
BOUND_HEIGHT=$(echo "$BOUND_LINE" | grep -oE "height=[0-9]+" | head -1 | cut -d= -f2)
EXPECTED_BOUND=$((START_HEIGHT + 50))
if [ "$BOUND_HEIGHT" != "$EXPECTED_BOUND" ]; then
  echo "FAIL - expected bound at height=$EXPECTED_BOUND, got $BOUND_HEIGHT"
  exit 1
fi
echo "PASS - first pass stopped at exactly the 50-block bound ($BOUND_HEIGHT), not the tip ($TIP_HEIGHT)"

echo "=== waiting for the periodic retry (CATCH_UP_RETRY_SECONDS=20) to finish the remaining 5 blocks, with no new block event ==="
for i in $(seq 1 40); do
  CUR=$(ch_regtest "SELECT last_block_height FROM checkpoints WHERE component='ingestor' ORDER BY last_run_at DESC LIMIT 1")
  if [ "$CUR" = "$TIP_HEIGHT" ]; then
    echo "PASS - periodic retry reached tip on its own: checkpoint now at height=$CUR"
    exit 0
  fi
  sleep 1
done
echo "FAIL - periodic retry never reached tip ($TIP_HEIGHT); checkpoint stuck at $CUR"
exit 1
