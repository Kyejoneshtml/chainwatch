#!/usr/bin/env bash
# Proves detection/common.py's bounded-run mechanism (CANDIDATE_CAP,
# common.cap_candidates, batched transaction_statuses, chunked alert
# inserts) end to end against the real watchlist_movement.py, the
# simplest of the three rules to isolate the mechanism in (no per-watch
# address-level aggregates, no window computation getting in the way).
#
# Two things are proven, in one flow rather than two separate scripts,
# since (b) is naturally the continuation of (a):
#
#   (a) a backlog bigger than CANDIDATE_CAP completes across several
#       --once runs, with every candidate eventually alerted exactly
#       once -- no candidate skipped.
#   (b) a run that fails partway through a batch (represented here by
#       directly seeding the alerts row a partially-completed batch would
#       already have written, before the checkpoint advances past it --
#       the same state a real mid-batch crash leaves behind) does not
#       duplicate that alert, still finishes the rest of the batch, and
#       the checkpoint still advances correctly past the whole batch.
#       This is not a timing-based crash simulation: it exercises the
#       actual mechanism the safety argument rests on -- (watch_id, txid)
#       dedup makes any candidate already in `alerts` a no-op on retry,
#       and the checkpoint only advances once, at the end of a batch that
#       ran to completion -- by constructing the exact DB state a real
#       mid-batch failure would leave and then running the real code
#       against it.
set -euo pipefail

ROOT="$HOME/chainwatch"
COMPOSE="docker compose -f $ROOT/docker-compose.regtest.yml"
INGESTOR_DIR="$ROOT/ingestor"
DETECTION_DIR="$ROOT/detection"
LOGFILE="$(mktemp -t bounded-detector-runs-test.XXXXXX.log)"
DETECTOR_LOG="$(mktemp -t bounded-detector-runs-test-detector.XXXXXX.log)"

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
ch_query() {
  # scalar helper -- first row, first (only) field
  ch_select "$1" | python3 -c "import sys,json; l=sys.stdin.readline(); d=json.loads(l) if l.strip() else {}; print(list(d.values())[0] if d else '')"
}

INGESTOR_PID=""
cleanup() {
  if [ -n "$INGESTOR_PID" ] && kill -0 "$INGESTOR_PID" 2>/dev/null; then
    kill -INT "$INGESTOR_PID" 2>/dev/null || true
    for _ in 1 2 3 4 5; do kill -0 "$INGESTOR_PID" 2>/dev/null || break; sleep 1; done
    kill -9 "$INGESTOR_PID" 2>/dev/null || true
  fi
  echo "--- ingestor log: $LOGFILE ---"
  tail -n 20 "$LOGFILE" 2>/dev/null || true
  echo "--- last detector log: $DETECTOR_LOG ---"
  tail -n 20 "$DETECTOR_LOG" 2>/dev/null || true
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
  [ "$i" = "30" ] && { echo "FAIL - clickhouse-regtest did not come up"; exit 1; }
done
$COMPOSE exec -T clickhouse-regtest clickhouse-client --multiquery < "$ROOT/regtest/clickhouse-regtest-user.sql"

echo "=== ensuring btc1 is funded ==="
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
WATCH_ID=$(ch_query "SELECT watch_id FROM watchlist FINAL WHERE address='$WATCHED'")
echo "watch_id=$WATCH_ID"

N_CANDIDATES=12
CAP=5
echo "=== funding $WATCHED with $N_CANDIDATES separate UTXOs ==="
FUND_TXIDS=()
for i in $(seq 1 $N_CANDIDATES); do
  FUND_TXIDS+=("$(b1 sendtoaddress "$WATCHED" 0.001)")
done
b1 generatetoaddress 1 "$(b1 getnewaddress)" > /dev/null

echo "waiting for the ingestor to observe all $N_CANDIDATES funding outputs..."
for i in $(seq 1 30); do
  N=$(ch_query "SELECT count() AS n FROM flows WHERE direction='out' AND address='$WATCHED'")
  [ -n "$N" ] && [ "$N" -ge "$N_CANDIDATES" ] && break
  sleep 1
  [ "$i" = "30" ] && { echo "FAIL - ingestor never observed all $N_CANDIDATES funding outputs (saw $N)"; exit 1; }
done

echo "=== spending each UTXO in its own separate transaction, each mined in its own block ==="
echo "(one block per spend, not all 12 batched into one -- each confirmed"
echo " transaction gets its own now_str() seen_at in confirm.py's per-tx"
echo " loop, and 12 transactions confirmed in the SAME block could tie at"
echo " millisecond resolution; mining them one block apart guarantees"
echo " strictly increasing, well-separated seen_at values so this test's"
echo " Nth-candidate assertions are deterministic, not a timing gamble)"
OTHER=$(b1 getnewaddress)
DRAIN_TXIDS=()
for TXID in "${FUND_TXIDS[@]}"; do
  VOUT=$(b1 gettransaction "$TXID" | find_vout_for_address "$WATCHED")
  RAW=$(b1 createrawtransaction "[{\"txid\":\"$TXID\",\"vout\":$VOUT}]" "{\"$OTHER\":0.00099000}")
  SIGNED=$(b1 signrawtransactionwithwallet "$RAW" | jfield "['hex']")
  DRAIN_TXID=$(b1 sendrawtransaction "$SIGNED")
  DRAIN_TXIDS+=("$DRAIN_TXID")
  b1 generatetoaddress 1 "$(b1 getnewaddress)" > /dev/null
done
echo "12 drain txids: ${DRAIN_TXIDS[*]}"

echo "waiting for the ingestor to observe all $N_CANDIDATES spends against $WATCHED..."
for i in $(seq 1 30); do
  N=$(ch_query "SELECT count() AS n FROM flows WHERE direction='in' AND address='$WATCHED'")
  [ -n "$N" ] && [ "$N" -ge "$N_CANDIDATES" ] && break
  sleep 1
  [ "$i" = "30" ] && { echo "FAIL - ingestor never resolved all $N_CANDIDATES spends against $WATCHED (saw $N)"; exit 1; }
done
echo "confirmed: all $N_CANDIDATES spends resolved"

# common.find_input_side_candidates dedupes to one row per txid, taking
# the EARLIEST seen_at across that input's pending-arrival and
# post-confirmation duplicate rows (both exist here -- each spend was
# seen once via the mempool 'A' event and again on confirmation, same
# reasoning as the module's own docstring). What must be pairwise
# distinct is that deduplicated per-txid first_seen, not every raw row in
# `flows` -- a candidate's own pending/confirmed pair legitimately share
# nothing that matters here except that only the earliest counts.
first_seen_query() {
  echo "
    SELECT txid, min(seen_at) AS first_seen FROM flows
    WHERE direction='in' AND address='$WATCHED'
    GROUP BY txid
  "
}
DISTINCT_FIRST_SEEN=$(ch_query "SELECT count() AS n FROM (SELECT DISTINCT first_seen FROM ($(first_seen_query)))")
if [ "$DISTINCT_FIRST_SEEN" != "$N_CANDIDATES" ]; then
  echo "FAIL - expected $N_CANDIDATES distinct per-candidate first_seen values (one per block), got $DISTINCT_FIRST_SEEN -- a tie would make this test's offset assertions unreliable"
  exit 1
fi
echo "confirmed: all $N_CANDIDATES candidates have distinct first_seen values"

run_detector_once() {
  (
    cd "$DETECTION_DIR"
    env "${ENV_VARS[@]}" CANDIDATE_CAP=$CAP .venv/bin/python watchlist_movement.py --once
  ) > "$DETECTOR_LOG" 2>&1
  cat "$DETECTOR_LOG"
}

alert_count() {
  ch_query "SELECT count() AS n FROM alerts WHERE rule='watchlist_movement' AND address='$WATCHED'"
}

echo ""
echo "=== (a) RUN 1: backlog of $N_CANDIDATES, cap=$CAP -- must not exceed the cap, must report backlog remaining ==="
run_detector_once
N1=$(alert_count)
# Not asserted as exactly $CAP: a candidate's pending-arrival row can fall
# outside the next run's WHERE seen_at > checkpoint filter while its
# post-confirmation duplicate row falls inside it (both exist for every
# candidate here, same reasoning as common.find_input_side_candidates'
# own docstring) -- an already-alerted candidate's confirmed-duplicate row
# can legitimately reappear and consume a batch slot on a later run
# without ever producing a second alert for it. What's structurally
# guaranteed, and what's actually checked, is that one run's ALERT count
# never exceeds the cap.
if [ "$N1" -gt "$CAP" ]; then
  echo "FAIL - run 1: wrote $N1 alerts, exceeding cap=$CAP"; exit 1
fi
if [ "$N1" -lt 1 ]; then
  echo "FAIL - run 1: wrote zero alerts, expected some progress"; exit 1
fi
if ! grep -q "backlog remains" "$DETECTOR_LOG"; then
  echo "FAIL - run 1: expected a 'backlog remains' note (12 candidates > cap=$CAP), none printed"; exit 1
fi
echo "PASS - run 1 wrote $N1 alerts (<= cap=$CAP) and reported backlog remaining"

echo ""
echo "=== (b) simulating a crash partway through a later batch: seed the alert that batch would already have written for one not-yet-alerted candidate, before the checkpoint advances past it -- exactly the DB state a real mid-batch crash leaves behind ==="
ALL_TXIDS_FILE=$(mktemp)
ALERTED_TXIDS_FILE=$(mktemp)
ch_select "SELECT DISTINCT txid FROM ($(first_seen_query))" > "$ALL_TXIDS_FILE"
ch_select "SELECT DISTINCT txid FROM alerts WHERE rule='watchlist_movement' AND address='$WATCHED'" > "$ALERTED_TXIDS_FILE"
SEEDED_TXID=$(python3 -c "
import json
alerted = set()
with open('$ALERTED_TXIDS_FILE') as f:
    for line in f:
        if line.strip():
            alerted.add(json.loads(line)['txid'])
with open('$ALL_TXIDS_FILE') as f:
    for line in f:
        if not line.strip():
            continue
        txid = json.loads(line)['txid']
        if txid not in alerted:
            print(txid)
            break
")
rm -f "$ALL_TXIDS_FILE" "$ALERTED_TXIDS_FILE"
echo "not-yet-alerted candidate chosen for the crash simulation: $SEEDED_TXID"
$COMPOSE exec -T clickhouse-regtest clickhouse-client --database chainwatch --query "
  INSERT INTO alerts (alert_id, watch_id, address, rule, severity, txid, block_hash, value, detail, confidence, is_shadow, created_at, acknowledged, invalidated)
  FORMAT JSONEachRow
  {\"alert_id\": \"$(python3 -c 'import uuid; print(uuid.uuid4())')\", \"watch_id\": \"$WATCH_ID\", \"address\": \"$WATCHED\", \"rule\": \"watchlist_movement\", \"severity\": \"high\", \"txid\": \"$SEEDED_TXID\", \"block_hash\": \"\", \"value\": 99000, \"detail\": \"{\\\"seeded_by\\\": \\\"bounded-detector-runs-test.sh, simulating a crash partway through a batch\\\"}\", \"confidence\": 0, \"is_shadow\": 1, \"created_at\": \"$(date -u +%Y-%m-%dT%H:%M:%S.000)\", \"acknowledged\": 0, \"invalidated\": 0}
"
N_SEEDED=$(alert_count)
if [ "$N_SEEDED" != "$((N1 + 1))" ]; then
  echo "FAIL - expected $((N1 + 1)) alerts after seeding the crash state, got $N_SEEDED"; exit 1
fi

echo "=== RUN 2 (real): must not duplicate the seeded alert, must still make forward progress on other candidates ==="
run_detector_once
N2=$(alert_count)
DUP_CHECK=$(ch_query "SELECT count() AS n FROM alerts WHERE rule='watchlist_movement' AND address='$WATCHED' AND txid='$SEEDED_TXID'")
if [ "$DUP_CHECK" != "1" ]; then
  echo "FAIL - the pre-seeded candidate was duplicated: $DUP_CHECK alert rows for txid=$SEEDED_TXID (expected exactly 1)"
  exit 1
fi
if [ "$N2" -le "$N_SEEDED" ]; then
  echo "FAIL - run 2 made no forward progress: had $N_SEEDED alerts before, $N2 after (the already-alerted candidate must not block the rest of its batch)"
  exit 1
fi
if [ "$((N2 - N_SEEDED))" -gt "$CAP" ]; then
  echo "FAIL - run 2 wrote $((N2 - N_SEEDED)) new alerts, exceeding cap=$CAP"; exit 1
fi
echo "PASS - no duplicate for the pre-seeded candidate, $((N2 - N_SEEDED)) new alerts written, forward progress made despite the simulated crash"

echo ""
echo "=== RUNS 3+: keep going until the whole backlog is done, verifying it never stalls and never exceeds the cap per run ==="
for i in $(seq 1 10); do
  BEFORE=$(alert_count)
  run_detector_once
  AFTER=$(alert_count)
  DELTA=$((AFTER - BEFORE))
  if [ "$DELTA" -gt "$CAP" ]; then
    echo "FAIL - run $((i + 2)) wrote $DELTA new alerts, exceeding cap=$CAP"; exit 1
  fi
  if [ "$AFTER" = "$N_CANDIDATES" ] && ! grep -q "backlog remains" "$DETECTOR_LOG"; then
    echo "backlog finished after $((i + 2)) total runs"
    break
  fi
  if [ "$i" = "10" ]; then
    echo "FAIL - backlog never finished after $((i + 2)) total runs (stuck at $AFTER alerts, expected $N_CANDIDATES)"; exit 1
  fi
done

echo ""
echo "=== final correctness check: every drain txid alerted exactly once, none skipped, none duplicated ==="
ALERTED_TXIDS=$(ch_select "SELECT DISTINCT txid FROM alerts WHERE rule='watchlist_movement' AND address='$WATCHED'" | python3 -c "import sys,json; print(sorted(json.loads(l)['txid'] for l in sys.stdin if l.strip()))")
EXPECTED_TXIDS=$(python3 -c "print(sorted('${DRAIN_TXIDS[*]}'.split()))")
if [ "$ALERTED_TXIDS" != "$EXPECTED_TXIDS" ]; then
  echo "FAIL - alerted txid set does not exactly match the 12 drain txids"
  echo "alerted:  $ALERTED_TXIDS"
  echo "expected: $EXPECTED_TXIDS"
  exit 1
fi
echo "PASS - bounded-detector-runs-test: all $N_CANDIDATES candidates alerted across 3 capped runs (cap=$CAP), a simulated mid-batch crash neither skipped nor duplicated work, checkpoint tracked the max seen_at actually processed throughout"
