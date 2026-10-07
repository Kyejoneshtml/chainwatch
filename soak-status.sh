#!/usr/bin/env bash
# Chainwatch soak status. Read-only. Safe to run any time.
set -uo pipefail
cd "$(dirname "$0")"
CH="docker exec clickhouse clickhouse-client --database chainwatch --query"

echo "=== PROCESSES (expect 4) ==="
ps -eo pid,etime,command | grep -E "[m]ain\.py|[w]atchlist_movement|[w]allet_drain|[f]an_in" \
  | awk '{printf "  %-8s %-12s %s\n", $1, $2, $NF}'
echo

echo "=== NODE vs INGESTOR ==="
TIP=$(docker exec bitcoind bitcoin-cli -conf=/config/bitcoin.conf getblockcount 2>/dev/null)
CKPT=$($CH "SELECT last_block_height FROM checkpoints WHERE component='ingestor' ORDER BY last_run_at DESC LIMIT 1" 2>/dev/null)
echo "  node tip:          ${TIP:-unreachable}"
echo "  ingestor checkpoint: ${CKPT:-unreachable}   (lag: $(( ${TIP:-0} - ${CKPT:-0} )) blocks)"
echo

echo "=== ERRORS SINCE SOAK START ==="
for f in logs/ingestor.log logs/detector_*.log; do
  [ -f "$f" ] || continue
  printf "  %-42s mem=%-5s other=%s\n" "$(basename "$f")" \
    "$(grep -c MEMORY_LIMIT_EXCEEDED "$f")" "$(grep -c 'run failed' "$f")"
done
echo

echo "=== ALERTS BY RULE, THIS SOAK (since 2026-10-05 18:20:29) ==="
$CH "SELECT rule, count() AS alerts, min(created_at) AS first, max(created_at) AS latest
     FROM alerts WHERE created_at >= '2026-10-05 18:20:29'
     GROUP BY rule ORDER BY alerts DESC FORMAT PrettyCompactMonoBlock" 2>/dev/null
echo

echo "=== RULE 2 SKIP BREAKDOWN (latest run) ==="
tail -1 logs/detector_wallet_drain.log 2>/dev/null | cut -c1-200
echo

echo "=== ELAPSED ==="
echo "  soak started 2026-10-05 18:20:29 UTC"
echo "  now          $(date -u +'%Y-%m-%d %H:%M:%S') UTC"
