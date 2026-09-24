# Chainwatch operations runbook

For whoever is looking at this after being away for a while and remembers
nothing about how any of this was started. Read top to bottom the first
time; after that, jump to whichever section matches what you're trying to
do.

## What's actually running

Four long-running processes, started under `nohup` so they survive a
closed terminal or a disconnected SSH session:

- `ingestor/main.py` — the ingestor. Watches the live Bitcoin node via
  ZeroMQ, resolves inputs, writes `transactions` and `flows` to
  ClickHouse.
- `detection/watchlist_movement.py` — rule 1 (watchlist movement).
- `detection/wallet_drain.py` — rule 2 (wallet drain).
- `detection/fan_in_consolidation.py` — rule 3 (fan-in consolidation).

All four are separate OS processes, started independently. None of them
depend on this terminal, this SSH session, or Claude Code being open.
Stopping one does not stop the others.

None of these run inside Docker. `bitcoind` and `clickhouse` run inside
Docker (`docker compose ps` from the repo root shows them); the ingestor
and the three detectors run directly on the host, as plain Python
processes under their own virtualenvs (`ingestor/.venv`,
`detection/.venv`).

## Is it alive right now?

```
ps aux | grep -E "main\.py|watchlist_movement\.py|wallet_drain\.py|fan_in_consolidation\.py" | grep -v grep
```

You should see four Python processes (plus their `bash -c` wrapper
parents, which just exist to add timestamps to the log — harmless, leave
them). If a process is missing, it has died or was stopped; see
"Something looks wrong" below.

A process being alive is not the same as it making progress. Check the
row count is actually growing:

```
docker exec clickhouse clickhouse-client --database chainwatch --query "SELECT count() FROM flows"
```

Run it twice, a minute or two apart, while the ingestor is alive. If the
number isn't moving and new mainnet blocks/transactions are happening
(check any block explorer), something is stuck even though the process
is technically still running — see "Something looks wrong."

## Where the logs are

`chainwatch/logs/`, one file per process:

- `logs/ingestor.log`
- `logs/detector_watchlist_movement.log`
- `logs/detector_wallet_drain.log`
- `logs/detector_fan_in_consolidation.log`

Every line is prefixed with a UTC timestamp (`2026-09-24T19:00:21Z ...`),
added by the shell wrapper the processes were started under — the Python
code itself doesn't timestamp its own output.

These files are **not rotated or truncated automatically.** They will
grow forever as long as the processes run. If disk space ever becomes a
concern, check their size (`ls -lh logs/`) before assuming something else
is wrong.

Quick tail of all four at once:

```
tail -f chainwatch/logs/ingestor.log chainwatch/logs/detector_*.log
```

## How to stop it cleanly

Find the PID of the Python process (not the `bash -c` wrapper) and send
it `SIGINT` (Ctrl-C's signal), not `SIGKILL`. All four scripts have a
`try/except KeyboardInterrupt/finally` shutdown path that flushes buffered
rows and prints a shutdown summary — killing with `-9` skips that and can
lose whatever was buffered but not yet flushed (up to ~2 seconds of data
for the ingestor, or a partial detection run).

```
pkill -INT -f "ingestor/main.py"
pkill -INT -f "detection/watchlist_movement.py"
pkill -INT -f "detection/wallet_drain.py"
pkill -INT -f "detection/fan_in_consolidation.py"
```

Give each a few seconds, then confirm it's gone:

```
ps aux | grep -E "main\.py|watchlist_movement\.py|wallet_drain\.py|fan_in_consolidation\.py" | grep -v grep
```

If a process is still alive after ~10 seconds, `SIGINT` didn't land or
didn't get handled — check the log file for a `shutdown:` summary line
first (it may just be slow to flush a large buffer); only escalate to
`pkill -9 -f "<script>"` if it's genuinely hung, and note in the log or
here that you had to force it, since that's the one path that can lose
unflushed data.

Stopping the ingestor does not stop `bitcoind` or `clickhouse` (the Docker
containers) — those keep running independently. To stop those too:
`docker compose down` from the repo root (never `docker compose down -v`
— that deletes the data volumes, including five days of node sync state
and all of `flows`/`transactions`).

## Starting it again

From the repo root:

```
cd ingestor
nohup env PYTHONUNBUFFERED=1 .venv/bin/python main.py 2>&1 | \
  while IFS= read -r line; do printf '%s %s\n' "$(date -u +%Y-%m-%dT%H:%M:%SZ)" "$line"; done \
  > ../logs/ingestor.log 2>&1 &
disown
```

Same pattern for each detector, from `detection/`:

```
cd detection
nohup env PYTHONUNBUFFERED=1 .venv/bin/python watchlist_movement.py 2>&1 | \
  while IFS= read -r line; do printf '%s %s\n' "$(date -u +%Y-%m-%dT%H:%M:%SZ)" "$line"; done \
  > ../logs/detector_watchlist_movement.log 2>&1 &
disown
```

(replace `watchlist_movement.py` with `wallet_drain.py` or
`fan_in_consolidation.py` for the other two.)

The ingestor resumes from wherever its `checkpoints` row last left off —
it does not backfill from scratch and does not need to be told where to
start. If the node has moved on a lot of blocks since the last run
(e.g. after being stopped for hours or days), the first new block
confirmation after startup will trigger `catch_up_to_tip`, which walks
forward through every block since the checkpoint in one go, synchronously
— this can take a while for a large gap and will block new mempool
processing while it runs. That's expected, documented behaviour
(`docs/04-ingestion.md`), not a hang, as long as it's still making
progress — check the log for `[block] height=...` lines advancing.

**Before starting the ingestor after any schema change**, it will refuse
to start on its own if `flows` doesn't match what the code writes
(`ingestor/schema_check.py`, checked automatically at startup) — if it
exits immediately with a `SchemaMismatch` error, that's it working
correctly, not a bug. Don't work around it; find out why the schema and
the code disagree first.

## Something looks wrong — what to check first

1. **Is the process actually still running?** (`ps aux | grep ...` above.)
   If it's gone, check the tail of its log file for the last thing it
   printed — especially a Python traceback, or a `SchemaMismatch` line.

2. **Is ClickHouse or bitcoind down?**
   ```
   docker compose ps
   ```
   Both `clickhouse` and `bitcoind` should show `Up`. If either is down
   or restarting, every process above will be failing to connect —
   that's the root cause, not something wrong with the ingestor/detectors
   themselves.

3. **Is it a memory problem?**
   ```
   docker exec clickhouse clickhouse-client --query "SELECT formatReadableSize(value) FROM system.metrics WHERE metric='MemoryTracking'"
   ```
   The server-wide cap is 2,000,000,000 bytes (~1.86 GiB) — if this is
   sitting close to that, or if the ingestor/detector logs show
   `MEMORY_LIMIT_EXCEEDED`, that's ClickHouse's memory cap doing its job
   (see `docs/08-build-plan.md`'s OOM section for why this cap exists and
   what it's protecting against) — not a bug, but worth knowing about
   rather than just retrying blindly.

4. **Are the row counts actually moving?**
   ```
   docker exec clickhouse clickhouse-client --database chainwatch --query "SELECT count() FROM flows"
   docker exec clickhouse clickhouse-client --database chainwatch --query "SELECT rule, count() FROM alerts GROUP BY rule"
   ```
   Run each twice a couple of minutes apart. `flows` should grow whenever
   the ingestor is alive and mainnet is producing transactions. `alerts`
   grows more slowly and unevenly — a quiet period there is not
   necessarily a problem (see the note on rule 1 below).

5. **Grep every log for errors at once:**
   ```
   grep -iE "error|exception|traceback" logs/*.log
   ```
   A `NotOpenSSLWarning` line from `urllib3` at the very start of every
   log is expected noise, not a real error — ignore it. Anything else is
   worth reading in full before deciding what to do.

6. **Rule 1 (watchlist movement) can legitimately produce a lot of
   alerts, fast, on a high-volume address** — this is a known, expected
   property of the rule as currently specified
   (`docs/08-build-plan.md`, phase 4b), not a sign of malfunction. A
   sudden spike in `alerts` for `rule='watchlist_movement'` specifically
   is the measurement this phase of the project is trying to take, not
   necessarily an incident. Check `docs/08-build-plan.md`'s phase 4b
   section before treating a large rule-1 count as a bug.

7. **If nothing above explains it**, stop the affected process cleanly
   (see above), read `docs/08-build-plan.md` end to end for the relevant
   phase — most operational quirks this project has hit before are
   recorded there with the actual cause, not just the symptom — and don't
   restart until you understand what happened.

## Things that are deliberate, not bugs

- `address_stats` no longer updates. This was deliberate
  (`docs/08-build-plan.md`, flows redesign section) — the materialized
  view that fed it was dropped, not fixed, because reattaching it would
  have kept adding correct numbers on top of an already-wrong total
  forever. Nothing in `detection/` reads `address_stats`. Don't recreate
  the view without reading why it was dropped first.
- `flows_old` still exists in the database (67,144,753 rows, the
  pre-migration table). It is intentionally not dropped — a safety net,
  not leftover clutter. Don't delete it without a specific reason to.
- Every alert currently written has `is_shadow = 1`. Nothing is delivered
  to anyone yet — this is still shadow mode (`docs/08-build-plan.md`,
  phase 4's own definition of done). A growing `alerts` table is the
  point, not a leak.
