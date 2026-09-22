# 08. Build plan

Eight phases, each with a definition of done. No phase begins before the previous one meets it.

---

## Phase 0: Node sync — COMPLETE

Node synced and verified at block 962,053 on 11 August 2026. Pruned, out of initial block download, ZeroMQ publishing.

Input resolution verified against live data: a P2WSH address and 7.32669980 BTC, retrieved for an input that returned null under the default `include_mempool` behaviour.

**Outstanding:** `zmqpubsequence` was added to the configuration after initial sync and requires a node restart to take effect.

---

## Phase 1: Documentation — COMPLETE

Fifteen documents. Architecture, ingestion, data models, detection, interface, glossary, design system, and five research documents recording forty-six corrections identified before implementation.

---

## Phase 2: Design system and screens — COMPLETE

Design system published. Address overview and alerts feed at high fidelity.

**Requires revision** against the relief-not-delight principle in `07-ui-spec.md`. The existing screens are analyst-oriented; the victim path does not yet exist.

---

## Phase 3: Ingestion

The hardest phase, and larger than originally scoped because reorg handling has moved into it.

### 3a. Regtest harness — prerequisite

A private Bitcoin network where blocks are mined on command.

- Separate compose file, `docker-compose.regtest.yml`
- Two or three nodes so a fork can be induced
- Scripts to mine blocks, create transactions, and force a reorg on demand

Lopp used the same approach for QA at BitGo, describing a simulator generating "random transactions, blocks, forks and problematic behaviour" as invaluable for reproducing rare events locally.

Reorg handling that cannot be tested cannot be trusted. Waiting for a mainnet reorg is not a test strategy.

**Done when:** a reorg can be triggered on command and observed.

**COMPLETE, 13 August 2026.** Two nodes on a private network. `regtest/reorg.sh` splits them, mines competing chains, reconnects, and asserts `confirmations: -1` on the orphaned tip. Runs in roughly fifteen seconds and passes from any starting height.

One thing the manual run exposed that the documentation would not have: `setnetworkactive true` restores networking but does **not** restore the peer connection. `addnode ... onetry` is required. Without it the reorg silently does not happen and both nodes sit on different chains looking healthy.

**Extended and complete, 16 August 2026.** `regtest/scenarios.sh` covers four cases beyond the bare reorg: a real transaction confirmed then returned to the mempool by orphaning its block; a transaction spending an unconfirmed parent, proving the parent-pending case is distinguishable from a genuine resolution gap; an RBF replacement leaving the mempool and never confirming; and a low-fee transaction persisting unconfirmed across mined blocks. All four pass.

The original gap, now closed: `reorg.sh` mines orphaned blocks with `generatetoaddress`, so the orphaned blocks contain only coinbase transactions. The test proves the node reorgs; it proves nothing about how transactions in an orphaned block are handled, which is what the ingestor actually needs.

Of Lopp's five failure modes in `11-prior-art.md`, four are now covered: reorganizations, spending of unconfirmed outputs, chaining of unconfirmed outputs, and transactions that never confirm. Double spends remain untested, and are partially covered in practice by the RBF scenario since a fee-bumped replacement is the mechanism by which most apparent double spends occur.

**One finding worth recording.** Bitcoin Core reports a replaced transaction's `confirmations` as the negative of the conflicting transaction's depth once the replacement confirms — `-2` when the replacement has 2 confirmations — rather than `0`. The assertion checks `confirmations <= 0` for this reason. The first version of the test asserted `= 0` and failed against correct behaviour.

### 3b. ClickHouse and schema

**COMPLETE, 17 August 2026.** Six tables plus the `address_stats` materialised view, applied automatically on first container start. ClickHouse 25.8 LTS, bound to the Docker network only and confirmed unreachable from the host on both 8123 and 9000.

**One finding worth recording.** The `CLICKHOUSE_DB` environment variable creates the named database but does **not** set it as the default for schema initialisation. The entrypoint runs each `.sql` file through `clickhouse-client` with no `--database` flag, so unqualified `CREATE TABLE` statements land in `default` rather than the intended database. Every statement reports success. `USE chainwatch;` at the top of each schema file is required.

This is the same failure shape as the `include_mempool` default in `04-ingestion.md`: a plausible assumption, no error, and a silently wrong result. It was caught by starting the container and running `SHOW TABLES` rather than by reading the entrypoint script and assuming.

Schema from `05-data-models.md`, including the version column, `block_hash`, the checkpoint table, and the three-way resolution state.

### 3c. Ingestor

- ZMQ subscriber on rawtx, rawblock and sequence — notification only
- RPC fetch as the authoritative source
- Input resolution with `include_mempool=false`, three-way outcome
- Periodic mempool reconciliation
- Batched inserts, 1,000 rows or 2 seconds
- Checkpoint written on every flush
- Dead letter store
- Stale pending expiry
- Metrics from the outset

Built in five stages. **Stage 1 complete, 18 August 2026.** ZMQ subscriber on `rawtx` and `sequence`, RPC client (`getblockchaininfo`, `getrawtransaction`, `gettxout`), and a main loop tying them together. No ClickHouse writes yet, nothing decoded beyond confirming a notification arrived. Ran against the live node for 75 seconds unattended: 485 transactions resolved via RPC, zero fetch failures.

`bitcoind`'s RPC and ZMQ ports were not published to the host (`docker-compose.yml` exposes only `8333`), and Docker Desktop's networking on macOS does not route the host to a container's internal IP directly — confirmed by a hanging connect rather than a refusal. Resolved with `docker-compose.override.yml`, which Compose merges automatically without editing `docker-compose.yml` itself.

**Three findings worth recording, all caught by running the thing rather than by reading the code.**

**The plan approved before writing any code assumed the `rawtx` payload could be hashed to obtain the txid, and that assumption was wrong.** The plan stated it explicitly as a design decision, on the reasoning that hashing an opaque payload without parsing its structure would not count as "decoding" it and would stay within the notification-only rule. Run against live mainnet traffic, every single derived txid failed to resolve. `sha256d` of the full `rawtx` payload is the **wtxid** — the hash of the witness-included serialisation — not the txid, for any SegWit transaction, confirmed by comparing the computed value against the RPC's own `hash` (wtxid) and `txid` fields for the same mempool transaction. Since SegWit transactions are the great majority of current traffic and no RPC method accepts a wtxid in place of a txid, the approach does not degrade gracefully; it fails on almost everything. The fix was to drop the derivation entirely: `rawtx` is now logged on arrival only, exactly as the notification-only rule already required, and the RPC fetch is driven instead by `sequence`'s `A` (added-to-mempool) event, whose hash field is the txid. The approved plan being wrong here, and only being caught by testing against real SegWit traffic rather than by review, is the point worth keeping: a plan reviewed and agreed on is a hypothesis, not a verified fact, exactly as `04-ingestion.md`'s governing principle would predict.

**The `sequence` topic's 32-byte hash needed no byte reversal.** It arrives already in RPC display order. This is the opposite convention from the wtxid computed above, which is produced by hashing and so is in internal byte order and does need reversing to match RPC output. Assuming one convention applied uniformly across both would have been a second, quieter version of the same mistake.

**`bitcoind` returns HTTP 500 for ordinary RPC errors, not only for genuine server failures.** A bad txid, a missing block, any `-5`/`-8`-class error — all come back as HTTP 500 with the real error in a JSON body, rather than HTTP 200 with an `error` field, which is the more common convention. `requests.raise_for_status()` was raising before that body was ever read, so every failure surfaced as a bare "500 Server Error" with the actual cause discarded. Fixed by parsing the JSON body first and only falling back to `raise_for_status()` when there is no parseable body at all. Of the three, this is the one that would have cost the most later: every future RPC failure, of any kind, would have surfaced the same way, and the ingestor's core discipline — record and count every failure rather than dropping it silently — depends on the failure being legible in the first place.

**Stage 2 complete, 18 August 2026.** Output decoding, three-way input resolution, dust flagging, and satoshi-integer fee computation, still entirely in memory — no ClickHouse writes. Ran against live mainnet for 70 seconds: 3,276 transactions processed, zero RPC failures, zero tracebacks.

**A single combined "resolution rate" conflates coverage with mempool timing, and the two must be reported separately.** The first version of the shutdown summary reported one number, `resolved / (resolved + parent_pending + unresolved)`. On the 70-second run it came out at 30%: 1,167 resolved, 2,725 parent_pending, zero unresolved. Read on its own, 30% looks like a coverage failure, well under the 95% target this section sets. It is not one. The run's tail hit a live RBF fee-bump chain — the same output value drifting down by 56 satoshis per replacement, over and over — the mainnet version of exactly what `regtest/scenarios.sh`'s chained-unconfirmed scenario reproduces deliberately. Every one of those `parent_pending` classifications was correct: the spent output's creating transaction was itself still unconfirmed, so the output does not yet exist on the confirmed chain, and resolution succeeds automatically once the parent confirms. Nothing was lost.

The 95% target in this document measures coverage — the failure Lopp warns about, where a missed UTXO update silently corrupts the index. `parent_pending` is not that failure; it is a correct, recoverable classification. Folding it into the same denominator as `unresolved` makes ordinary mempool churn look like data loss. The shutdown summary now reports two rates instead of one:

- `coverage_rate = 1 - (unresolved / total_inputs)` — what the 95% target measures. **100% on the observed run** (zero unresolved).
- `pending_rate = parent_pending / total_inputs` — informative about mempool conditions (RBF activity, chained spends), not about correctness. **70% on the observed run**, entirely attributable to the fee-bump chain above.

Any future reading of a low combined rate should check `pending_rate` before treating it as a coverage problem.

**Stage 4 complete, 5 September 2026.** Confirmation handling: pending transactions move to `confirmed` with `block_height` and `block_hash` populated, sourced by re-fetching from the node (`getblock` verbosity 3) rather than reading back the pending row. Triggered off the `sequence` topic's `'C'` label, already subscribed since stage 1 — its own hash/height bytes are never read, only used as a wake-up signal, with the authoritative tip coming from RPC.

`gettxout` cannot resolve a confirmed transaction's inputs: by the time a transaction confirms, the outputs it spends are already marked spent, so `gettxout(..., include_mempool=false)` returns null for every one of them. `getblock` verbosity 3 embeds `prevout` (value and `scriptPubKey`) directly on each `vin`, verified against the live node before relying on it, and resolves a whole block's inputs in one RPC call rather than one `gettxout` per input.

**The mempool-subscriber-blocking concern was worth measuring rather than assuming, and the measurement came out small.** `docs/04-ingestion.md`'s constraint is that a stalled mempool subscriber doesn't just add latency, it starts losing input resolution permanently. Block processing time is now recorded per block (`max_block_seconds` in the shutdown summary) with a 5-second warning threshold. Observed on a live block of 3,892 transactions: 0.67 seconds. The concern was real enough to check; at this transaction volume it isn't costing anything.

**Verified independently against ClickHouse with `FINAL`, not by trusting the ingestor's log.** A txid logged as pending at mempool arrival (`resolved=1 fee=292`) was queried again after the next block landed: `status='confirmed'`, `block_height` and `block_hash` matching the block exactly. This is `docs/05-data-models.md`'s ReplacingMergeTree behaviour — both rows coexist until a background merge, `FINAL` forces the resolution at read time — working end to end rather than only in the schema document.

**A second latent bug, same shape as the `include_mempool` and `CLICKHOUSE_DB` findings above: plausible, no error, silently wrong, and only caught by running a query large enough to hit it.** `ch_client.py`'s `select()` always placed the SQL text in the URL's `query` parameter. Every prior caller was small enough that this never mattered. Determining which of a block's transactions were already known before confirmation (needed to count "confirmed but never seen pending" separately, as this section requires) queries `transactions` with an `IN (...)` clause over a whole block's txids — several thousand entries, comfortably past 100KB of URL. ClickHouse's HTTP form parser rejects it outright: `HTML Form Exception: Field value too long`, HTTP 500. Confirmed on the live container both broken and, after moving a query-only call's SQL into the POST body instead of the URL (leaving `INSERT`'s short statement-plus-data-body shape unchanged), fixed.

### 3d. Reorg handling

- Block hash stored per confirmed row
- Detection by hash comparison and by the sequence topic
- Rollback in reverse order, alert invalidation, reprocessing
- **Tested against the regtest harness**, not hoped for

**Stage 5 complete, 12 September 2026.** Detection keeps an in-memory `(height, hash)` window (`persist.py`'s `recent_confirmed`, 100 entries) alongside the checkpoint, compared against the node on a timer (15s) and immediately on the `sequence` topic's `'D'` (block disconnected) event — the two mechanisms `04-ingestion.md` specifies. On divergence, `reorg.py` reverts affected rows to `pending` (or `orphaned` for coinbase, which can never return to the mempool — a distinction the task description's "usually return to the mempool" left as a judgment call, and the schema's third status value was sitting unused for exactly this), issues `ALTER TABLE alerts UPDATE invalidated = 1` for alerts referencing the orphaned block hashes, then rewinds the checkpoint to the fork point and lets the ordinary confirmation path (extracted into `confirm.catch_up_to_tip`, now shared with the normal `'C'` handler) walk forward onto the new canonical chain.

**The window must be seeded with the checkpoint tip itself, not just blocks confirmed this run — caught by testing, not by review.** The first version left `recent_confirmed` empty at startup. A reorg striking the very first block confirmed after a restart then had exactly one tracked entry, it mismatched, and `find_divergence` raised `ReorgExceedsWindow` — "reorg deeper than tracked window" — when the true fork point (the checkpoint height itself, never touched by the fork) was known all along, just not in the window. Fixed by seeding the deque with `(last_block_height, last_block_hash)` on construction. Only a regtest run against a freshly-started ingestor surfaced this; the bug is invisible once the ingestor has been running long enough to accumulate its own window.

**Only `ALTER UPDATE` on `alerts` was needed, not the broader `ALTER on transactions/flows` an earlier comment in `schema/ingestor-user.sql.example` had guessed at.** Reverting a transaction is a new `INSERT`, the same pattern the pending → confirmed transition already used — never an in-place mutation — so `transactions` and `flows` needed no new grant at all. `alerts.invalidated` has no such append-only alternative (no version column), so it's the one place `06_alerts.sql`'s own comment already called for `ALTER TABLE ... UPDATE`. Granted on the live instance and verified via `SHOW GRANTS`.

**Testing required extending the regtest harness itself, since the nodes published no ZMQ at all.** `regtest/bitcoin-regtest.conf` gained the same two topics (`zmqpubrawtx`, `zmqpubsequence`) the mainnet node already publishes; `docker-compose.regtest.yml` gained host port publishing for `btc1` (only the node the ingestor watches) and a disposable `clickhouse-regtest` container — schema unmodified, no persistent volume, its own scoped user (`regtest/clickhouse-regtest-user.sql`, mirroring the production grants exactly, so the test exercises the real privilege boundary) — kept separate from the real `chainwatch` ClickHouse so synthetic regtest txids never mix with real fraud-analytics data. New script: `regtest/ingestor-rollback-test.sh`, which runs the actual ingestor (not a stand-in) against `btc1`, confirms a transaction, manually inserts one alert row (nothing generates alerts yet — phase 4), orphans the block, and asserts with `FINAL` that the transaction returned to `pending` and the alert's `invalidated` flipped to `1`.

**A file-mount gotcha cost more debugging time than the actual reorg logic.** Editing `bitcoin-regtest.conf` on the host didn't take effect in the already-running `btc2` container — its bind-mounted config went stale (the edit replaces the underlying file rather than modifying it in place, which breaks a single-file bind mount on Docker Desktop for Mac), producing a flatly misleading `"specified config file could not be opened"` from `bitcoin-cli` that looked like a permissions or path problem. `btc1` didn't show it only because an unrelated port-mapping change happened to force its recreation first. Fixed with `docker compose up -d --force-recreate btc2`; worth remembering for any future edit to a config file bind-mounted into an already-running container.

**The test's own ordering bug looked exactly like a broken reorg and wasn't one.** The first version split the network *after* confirming the test transaction, by which point `btc2` had already synced that block over P2P — so `btc2`'s subsequent "competing" blocks just extended the same chain instead of forking before it, and no reorg was possible at all. `scenarios.sh`'s `reorg-with-transactions` splits first for exactly this reason; the fix was to match it.

### Definition of done

- 24 hours unattended on mainnet without intervention
- Input resolution above 95%, with parent-pending counted separately
- **A forced reorg on regtest is detected, rolled back correctly, and reprocessed**
- **Kill-and-restart testing passes.** The ingestor is killed at random points and the output checked for correctness after recovery. This exercises checkpoint recovery, replay and partial batch handling simultaneously
- **The duplicate-detection query returns zero rows**
- At least five transactions hand-verified against a public block explorer, including a multi-input and a SegWit transaction

**Time:** 5 to 8 days. Longer than originally estimated. Address decoding and reorg rollback both take longer than expected.

---

## Phase 4: Detection

- Watchlist matcher
- Tier 1 rules from `06-detection.md`: watchlist movement, wallet drain, fan-in consolidation, dormancy break
- **All four ship in shadow mode**
- Suppression list for known recurring patterns
- Dust exclusion from clustering
- Address poisoning detection
- OFAC sanctioned address ingestion from the nightly-updated extracted list
- Alerts table with `is_shadow` and reorg invalidation

Tier 2 and tier 3 rules deferred. Behavioural profile shift and velocity anomaly require 30 days of history and run in shadow during that period. Peel chain requires the graph. Fan-out and labelled-address proximity require data not available.

### Catch-up message loss: investigated, not present at tested scale

Before starting on 4b, a concern raised after 4a's watchlist matcher work needed resolving: `confirm.catch_up_to_tip` (used by both the ordinary `'C'` handler and reorg reprocessing) blocks the main loop synchronously while it walks forward through a backlog of blocks. While it runs, nothing calls `zmq_listener.listen()`'s `poller.poll()`, so the ingestor's own ZMQ subscriber socket sits undrained for the whole call. `getzmqnotifications` reports bitcoind's publisher high-water mark at 1,000 messages per topic; a long-stopped-then-restarted ingestor catching up over hundreds of blocks could plausibly exceed that and lose mempool notifications permanently, which is exactly the silent-failure shape `04-ingestion.md`'s governing principle rules out.

**First attempt at measuring this was itself flawed, and is recorded here rather than quietly replaced.** It compared periodic snapshot counts from two independently-running processes: the ingestor's own `[tx] source=sequence` log-line count against a separate always-draining counter process. The gap between them fluctuated across samples (readings in roughly the 59–98 range, non-monotonic) rather than settling on a fixed number. That fluctuation is itself the tell that this approach measures the wrong thing: comparing two processes sampled at different, uncontrolled instants conflates *loss* (permanent, at the socket) with *backlog* (temporary, in the ingestor's own decode/resolve/flush pipeline after `catch_up_to_tip` returns) — a real drop cannot shrink on a later sample, but a backlog does. This method could not distinguish the two and was abandoned rather than trusted.

**Second design isolates the actual question.** A second ZMQ subscriber, opened alongside the ingestor's own, is deliberately left completely undrained for the entire duration of a real (unmodified) `confirm.catch_up_to_tip` call against a deliberately stale checkpoint — reproducing the exact condition under test. A third, always-draining subscriber records every `'A'` (added-to-mempool) txid to a file in real time as independent ground truth for the same window. After `catch_up_to_tip` returns, the deliberately-idle socket is drained once and the two txid *sets* (not counts) are compared — removing all sampling-time noise.

Run four times total, at the same scale (500 blocks, ~380–410s blocked, comparable mempool volume each time so no run measured a materially different load):

| Run | Blocked duration | Blocks | Published (ground truth) | Received (idle socket, drained after) | Missing |
|---|---|---|---|---|---|
| 1 | 380.1s | 500 | 1,940 | 1,949 | **0** |
| 2 | 410.8s | 500 | 1,799 | 1,806 | **0** |
| 3 | 397.7s | 500 | 2,130 | 2,140 | **0** |
| 4 | 404.4s | 500 | 1,764 | 1,765 | **0** |

Zero messages lost, in every run. (Received exceeds published in each case because the idle socket's drain window extends slightly past the ground-truth window's end — expected, not a discrepancy.) Working theory: ZMQ's stated high-water mark governs internal queue depth, but each `sequence` message is roughly 43 bytes, so even ~2,000 of them sit well within an ordinary OS socket receive buffer — the backpressure condition the HWM exists to catch apparently never triggers at this volume.

**Scope of this finding: 500 blocks, not a multi-week gap.** This measurement covers the catch-up shape actually observed in this project's own restart pattern (hours to low thousands of blocks). It has not been tested at 10x this scale or beyond, and the reasoning above (bytes, not message count, is the binding constraint) is inference from these four runs, not independently verified at a larger scale.

**Decision: periodic mempool reconciliation, specified in `04-ingestion.md` as the general-purpose recovery mechanism for exactly this failure mode, is deliberately not built.** It remains the documented fallback if this finding is ever contradicted — by a much larger catch-up gap, a slower node, or a busier mempool — but building it now would be solving a problem this measurement did not find.

### Phase 4a: watchlist matcher — COMPLETE

In-memory Python dict, refreshed on a 30s timer, checked against every transaction on both the mempool path and the confirmed-block path. `ingestor/watchlist_cli.py` manages the list. Verified on live mainnet (718,659 real matches against a genuinely active address across one run) and on regtest with a deliberately deterministic test (`regtest/ingestor-watchlist-test.sh`: watch added to an already-running ingestor, funds sent to it, funds spent from it, both sides matched).

### Phase 4b: rule 1, watchlist movement — shadow mode implemented; the first shadow measurement is itself the finding

`detection/watchlist_movement.py`, a genuinely separate scheduled component (own `config.py` and `ch_client.py`, no RPC or ZMQ dependency), polls every 15s and writes `is_shadow = 1` alerts for funds moving from a watched address, exactly as specified in `06-detection.md`. Confidence is a new concept as of this phase: rule 1 is an **observation** rule (see `06-detection.md`, "Observation rules vs inference rules," added this phase) and stores `confidence = 0` with the reason in `detail`, never a fabricated figure.

**480 shadow alerts, one address, one detection pass.** DoD verification watched `bc1q3zcdunpmqgn8enyxa3smu7fwrfvya35dz3uvjy` — confirmed genuinely active at the time, not assumed — and the first run wrote 480 rows to `alerts`, queried directly and confirmed real (not a log line). A second run against the same state produced zero new candidates and zero duplicates, confirming the watermark and `(watch_id, txid)` dedup both hold.

**The rule is not wrong. This is the finding shadow mode exists to produce.** Every one of the 480 is a genuine movement from the watched address — the rule is behaving exactly as specified. The number itself is the problem: a victim watching one wallet, under this rule as currently specified, would have received 480 notifications from a single pass. That is `06-detection.md`'s own alert-fatigue warning ("the alerts you close too quickly because there are simply too many of them"), measured directly rather than predicted from industry figures.

**Stated plainly: `watchlist_movement` as specified in `06-detection.md` is not deliverable to a real user without either a materially higher minimum-value threshold, aggregation across a time window, or both.** Not fixed here, and the threshold was not tuned to make this number smaller — the honest record is 480 alerts per address per pass, on an address that happened to be active, under the rule exactly as written.

**Two qualifications belong in the same record as the number, not left for someone to discover separately.** First, this address was deliberately chosen *for* being highly active (the same self-chaining address used to prove the phase 4a matcher), specifically so a DoD test would have something to observe without an open-ended wait — that makes 480 closer to a worst case than a typical one. Second, a genuinely dormant victim wallet, which is the more realistic watch target for this product, would produce close to zero alerts under the same rule. Both facts sit next to the number: the rule is not calibrated for its actual target case, and the one data point gathered so far says nothing about what that target case would actually produce.

**Tuning the threshold or adding windowed aggregation is deferred, not decided.** Whatever the fix, it needs measurement against a realistic watch target, not a re-run against the same worst-case address with a bigger threshold typed in.

**Incidental finding, testing methodology rather than the code under test:** `kill -INT` to a backgrounded process in this development environment does not reliably convert to `KeyboardInterrupt` — confirmed with a minimal reproduction (a bare `time.sleep()` under the same signal, same non-delivery). This means every earlier "graceful shutdown" in this project confirmed via `kill -INT` in a background-job test harness (including the ingestor's, several times, in stage 4/5 testing) most likely exercised the `SIGKILL` fallback after its grace-period timeout, not the `try/except KeyboardInterrupt/finally` path itself — visible in retrospect as the "Killed: 9" lines bash printed after those runs, which were read as routine cleanup noise at the time rather than as evidence the graceful path was never actually taken. The `try/except KeyboardInterrupt/finally` shutdown pattern itself is standard, correct CPython behavior independent of this environment quirk, but it has not been positively demonstrated in this project by any test that relied on `kill -INT` to a background job.

### Phase 4c: rule 2, wallet drain — shadow mode implemented, proven on regtest, mainnet result is a legitimate zero

`detection/wallet_drain.py`, alongside a `detection/common.py` extraction of the query/checkpoint logic rule 1 and rule 2 now share (both live in the same "detection jobs" component with identical dependencies, so sharing within `detection/` carries none of the coupling risk that kept `detection/` and `ingestor/` deliberately separate from each other — confirmed behavior-unchanged for rule 1 after the refactor, both by import and by a dry run). Rule 2 uses its own checkpoint component, `detector_wallet_drain`, distinct from rule 1's `detector` — reusing rule 1's value would have let the two rules' watermarks clobber each other under `ORDER BY last_run_at DESC LIMIT 1 BY component`; `checkpoints.component` is a plain, unconstrained `String`, so this needed no schema change.

**Type: inference, unlike rule 1** — the absence of change is inferred, not observed, per the distinction added to `06-detection.md` in phase 4b. Confidence is computed once, in integer basis points (no floats anywhere): the one-time-change heuristic's published error rate, 92.66% (9266 basis points), gives `(10000 - 9266 + 50) // 100 = 7`. Identical on every alert this rule writes, per the confidence-derivation section's own rule that a figure comes from an error rate and nothing else — low, and low is correct, not inflated to look more useful.

**"Every available UTXO consumed" is computed as a balance, not a UTXO set, and the plan for this was checked before any code was written.** There is no capability anywhere in this system to enumerate an address's actual UTXO set — a pruned node with no `txindex` cannot answer that. The rule instead computes total ever received minus total ever spent, from this project's own `flows` data for that address (deduped in Python on (txid, position), not a SQL-level `DISTINCT`, since the field needed for the observation-window figure below — `seen_at` — differs between an input's pending-arrival and post-confirmation duplicate rows even though value doesn't, so a naive `DISTINCT` across all four columns would stop collapsing them). If that balance drops from something meaningful to near zero in one transaction, with no output returning to the address itself, the rule fires.

**This is not the same claim as "every UTXO was consumed," and the gap between them is recorded in three places, not one, so it cannot be read only where it is convenient:** the rule's own section in `06-detection.md`; a new `06-detection.md` closing section, "What this report does not claim" (created this phase, because a similar-sounding limitation was described to this project as already existing and it did not); and every alert's own `detail`, which carries `observation_window_seconds` — how long the address had been observed before the transaction, so a reviewer can weigh the limitation against a specific number rather than a general warning. An address funded before this project started watching it may hold real value in outputs this system has never seen and has no way to discover; a transaction that looks like a complete drain against everything known could leave money behind outside that window, and nothing in this rule's output would show the difference. This is worst for the exact case the product exists to serve: a victim who adds a watched address only after a theft has, by construction, a system that never saw the funds arrive.

**No-change checking is narrower than "the sender's cluster," and this is the other structural limitation stated rather than left inside a query.** No address-clustering exists in this codebase (Neo4j, deferred to phase 5's benchmark), so "no change returning to the sender" is checked as "no output returning to the exact watched address" — nothing broader. Legitimate spending that sends change to a fresh address the same wallet also controls, which is normal, privacy-conscious wallet behaviour, looks identical to a real drain under this check. This is the mechanism behind the "moderate" false-positive rate `06-detection.md` already predicted for this rule, now attributable to a specific, named cause. Every alert's `detail` carries a `plausible_innocent_explanation` field for exactly this reason: a wallet migration or hardware-wallet upgrade produces an identical shape.

**Proven on regtest, twice.** `regtest/detection-wallet-drain-test.sh`: watches a fresh address, funds it with three separate confirmed UTXOs (0.001 BTC each), drains all three in one transaction to a different address with no change, and asserts a shadow alert is written with the expected fields — `severity=critical`, `confidence=7`, `is_shadow=1`, balance 300,000 → 0 sats, `has_change_to_self=false`. Passed on both runs.

**Mainnet result: zero, and zero is the legitimate result the task description anticipated.** Watching the same known-active address used to prove the phase 4a matcher and the 4b flood produced no wallet-drain candidate — that address self-chains continuously and never approaches the residual threshold, so a zero here is expected, not a gap in coverage. A real drain is rare by the rule's own definition; the regtest proof above is what demonstrates the mechanism actually fires, since mainnet cannot be relied on to produce one to order.

**The private-submission figure (docs/06-detection.md, "What this report does not claim") was measured live, not carried forward from an unverified report, and the measurement itself needed a real correction before it could be trusted.** First attempt: track every ZMQ `sequence` `'A'` (added-to-mempool) event with its own arrival time, and on each `'C'` (block connected), check which of that block's transactions were ever seen that way. Run for four blocks, it reported 33.67% absent overall (19,257 confirmed, 6,483 absent) — but the very first block came back at 91.8% absent on its own, an outlier next to the other three (2.7%, 9.3%, 1.4%). The cause: the tracking dict starts empty at process start, so the first block after subscribing always shows every pre-existing mempool transaction as "absent" — not because it bypassed public broadcast, but because this process simply had not been listening yet when it arrived. This is a warm-up artifact of the measurement, not a property of the chain, and it was caught by the same discipline this project has already applied elsewhere: an unexplained outlier next to three consistent readings is a signal to look for what's different about it, not to average it in.

A second run, restarted clean, hit the same warm-up spike on its own first block (91.8% again — confirming it as the warm-up effect and not a one-off) but stayed low across blocks 2 through 4, run with nothing else active on the machine after an earlier version of this same run had produced swinging 45–84% readings across three blocks later traced to concurrent regtest testing competing for the same machine's resources while the probe was supposed to be running undisturbed — a second, distinct contamination source from the same root cause (this measurement is only trustworthy when nothing else is competing for the subscriber's attention), caught the same way, by treating an unexplained swing as a signal rather than noise to average away.

**Measured 14 September 2026, mainnet, excluding the first (warm-up) block of the clean run: 3 blocks (heights 966997–966999), 12,924 confirmed transactions, 668 never observed via this node's own mempool broadcast beforehand — 5.17%.** For transactions that were seen beforehand, median lead time (first sighting to confirmation) was 571.77 seconds across 12,774 of them — context, not the claim under test. **This is materially different from the 12.5% this project was told had been measured** — per instruction, that is the useful result, recorded as what was actually measured rather than adjusted to match what was reported. The sample is three blocks on one day's traffic, not a general constant; `06-detection.md` states the scope this way deliberately rather than repeating a bare percentage.

### Phase 4d: rule 3, fan-in consolidation — shadow mode implemented, proven on regtest, mainnet honest zero, a cross-rule pattern named

`detection/fan_in_consolidation.py`, sharing `detection/common.py` with rules 1 and 2, plus one new shared helper: `find_receiving_txids`, the `direction='out'` sibling of the input-side finder rule 1 and rule 2 already used. Own checkpoint component, `detector_fan_in_consolidation`, distinct from the other two for the same watermark-collision reason recorded in phase 4c.

**Mechanism.** "Many addresses paying one" is a multi-transaction, time-windowed pattern, not a single transaction's own input count — a single transaction's inputs are inherently simultaneous and would need no window at all. For each new transaction where the watched address receives something, the rule looks back `window` (default 1 hour, bounded below by the watch's own creation time) and unions the source addresses across every transaction that paid the watched address in that span. If that union reaches `min_sources` (default 10), it fires — anchored to whichever specific transaction completed the count, not the first one to start it. Confirmed on regtest that this fires on the completing transaction specifically: ten source addresses funded and each independently paying the watched address produced `candidates=10, alerts_written=1, skipped_below_min_sources=9` — only the tenth, which completed the set, crossed the threshold; the first nine were correctly evaluated and correctly held back.

**Point 1, confidence.** Type: inference — computed once, in integer basis points, from common-input-ownership's published 63.46% error rate: `(10000 - 6346 + 50) // 100 = 37`. The connection to that specific heuristic is stated in the rule's own module docstring rather than left implicit: the inference this rule makes is that the source addresses are genuinely unrelated, and distinguishing that from "one entity's own several addresses, secretly clustered" is exactly the question common-input-ownership addresses and cannot resolve reliably — so its error rate is the correct one to derive from, not a borrowed number that happens to be available.

**Point 2, suppression-ready rather than suppressed.** No list is built — `06-detection.md`'s own instruction, and there is no data yet to populate one with. Every alert's `detail` instead carries the full source-address set, the contributing transaction ids, and `source_set_fingerprint` (a hash of the sorted source list), so a future query can `GROUP BY` that fingerprint across many alerts and find a recurring depositor group without re-deriving the set each time. Verified concretely on the regtest run: the alert's `source_addresses` lists all ten, in full.

**Point 3, false positive rate: not measured this phase, because no address exhibiting the pattern was found to measure it against — recorded as a limit on what could be checked, not glossed over as a pass.** A live search for a naturally-occurring fan-in address across the archive was attempted first, before resorting to regtest. A full cross-table join (`flows` output-side joined to input-side, grouped by destination and hour, filtering for ten or more distinct sources) was tried first and killed by the container for excessive memory use against 67 million rows — most of it this project's own repeated stage-5 and phase-4 reprocessing of a handful of test addresses, not organic mainnet volume. A narrower, scoped retry against the four highest-activity addresses in `address_stats` found at most 3 distinct sources in any hour for any of them — all four turned out to be the self-chaining test artifacts already known from earlier phases, paying themselves rather than receiving from genuinely different sources. No naturally-occurring high-fan-in address was available to test against, live or otherwise, so the false-positive question this phase's own point 3 asks about is open, not answered: there is no measured rate to report, high or low, and none should be assumed.

**Live mainnet result: an honest zero, for a different reason than rule 2's zero.** A real, modestly-active address (`bc1qvmw9dmensxtuxu5vw7mxtxqurad2u99pdj9wwa`, previously observed at up to 3 distinct sources per hour — below threshold but genuinely receiving from more than one source) was watched, and the ingestor ran live against it for five minutes. `candidates=0` — no new receiving transaction arrived in that window at all, not even one below the threshold. This is a legitimate result given the address's own low receiving frequency at this timescale, and it is a different kind of zero from rule 2's: rule 2's zero came from evaluating real candidates and finding none crossed the drain condition; this one came from there being nothing new to evaluate in the window tested. Recorded as what it is, not folded into a single "zero" without the distinction.

**Point 4, and the pattern it turned out to be an instance of.** Total ingestion history is ~27 days — far deeper than the 1-hour window needs on its own. The binding constraint is per-watch, not project-wide: the window's lower edge is `max(candidate_time - window, watch.created_at)`, so a watch younger than one window-length sees a proportionally truncated window rather than a full one. Working through this surfaced that it is the same shape as rule 2's holdings-visibility gap — a rule that depends on accumulated observation is weakest exactly when a watch is newest, which is exactly when the product is most likely to be used (a victim adding a watch right after discovering a theft). Recorded once, generally, in `06-detection.md`'s "What this report does not claim," rather than as a rule-3-specific footnote, since a third rule hitting this same shape should not require rediscovering it a third time. That entry also notes the connection to `05-data-models.md`'s bridge section — which already queries ClickHouse's own ingested `flows` for a newly-watched address when building its graph — as the natural place a future backfill-on-watch-creation feature would extend from. Not built now.

**Severity, flagged rather than picked silently.** `06-detection.md` doesn't restate a severity word for rule 3 the way it did for rule 1. Proposed and used: `medium` — below rule 2's `critical`, reflecting the doc's own framing of this rule as a precursor signal ("frequently precedes an exchange deposit") rather than a theft signature in itself.

### ClickHouse OOM during phase 4d's point 3, root-caused

The `clickhouse` container's restart count and log gap (clean activity to 2026-09-14 19:41:59, then a silent jump to a fresh process start at 19:42:07 — no shutdown sequence logged in between) line up exactly with `system.query_log`'s heaviest recorded queries that day: three runs of the unfiltered `flows` output/input self-join described above (point 3), each reading 56–58 million rows and using 3.82 GiB. `max_server_memory_usage` is 6.98 GiB (0.9 of the Docker Desktop VM's 7.75 GiB), but **no per-query `max_memory_usage` cap exists** — it is `0`, unlimited, in the default profile. A few of those queries running close together, on top of ClickHouse's own background merges (independently seen throwing `MEMORY_LIMIT_EXCEEDED` around the same period), pushed total usage past what the VM had left for the three `bitcoind` containers sharing it. That is a VM-level Linux OOM kill, not a ClickHouse-level one — no `mem_limit` is set on the `clickhouse` service in `docker-compose.yml`, so `docker inspect`'s `OOMKilled` flag never fires for it.

The three shadow detectors' own queries all filter on a specific `address = '<watched address>'`, the leading column of `flows`'s `ORDER BY (address, block_time, txid)` — cheap primary-key scans, not table scans, and none reproduce the crashed query's shape. `fan_in_consolidation.py`'s `sources_within_window` resolves source addresses via `txid IN (...)` with no address anchor, which is the same *kind* of unanchored scan, just far smaller (chunked to 1,000 txids, only for actual candidates) — untested at real candidate volume, worth watching once loop mode starts.

**Correction to the first version of this fix: capping the `ingestor` ClickHouse profile alone would not have prevented the incident.** The queries that caused it ran ad hoc, not as `ingestor` — the real exposure is that ClickHouse and all three `bitcoind` containers share one 7.75 GiB VM with no ceiling on ClickHouse's total footprint at all. **Both parts of the fix are now applied and proven, 2026-09-22:**

1. **Per-query `max_memory_usage`, every user, so a single bad query fails cleanly instead of consuming the server budget.**
   - `ingestor` (also used by every `detection/` job — they share this ClickHouse user): `ALTER USER ingestor SETTINGS max_memory_usage = 1000000000` — SQL-driven, `local_directory` storage under `/var/lib/clickhouse/access/` on the mounted `clickhouse-data` volume, survives a container recreate. Documented in `schema/ingestor-query-memory-cap.sql.example`, matching `ingestor-user.sql.example`'s convention.
   - `default` (the user ad hoc/manual queries actually run as, including the one that caused the incident): `default` is `users_xml` storage, read-only from SQL (`ALTER USER default SETTINGS ...` confirmed to fail with `ACCESS_STORAGE_READONLY`), so this went through `docker-compose.yml` instead — a new `clickhouse-config/default-user-memory-limit.xml`, mounted to `/etc/clickhouse-server/users.d/`. First attempt placed this setting in `config.d/` alongside the server-wide one below and it silently had no effect: `config.d/*.xml` merges only into the tree read from `config.xml`, while profiles/users load from the separate `users_config` (`users.xml`) tree via `users.d/*.xml`, confirmed by testing (`SELECT value FROM system.settings WHERE name='max_memory_usage'` stayed `0` until moved).

2. **Server-wide `max_server_memory_usage`, sized against the actual VM budget.**

   VM total: 8,321,798,144 bytes = 7.75 GiB (`docker info`).

   `bitcoind` (mainnet) worst case: `dbcache=4000` MiB ≈ 3.91 GiB (the configured UTXO-cache ceiling — a ceiling it's allowed to grow into, not a fixed allocation) + `maxmempool` 300,000,000 bytes ≈ 0.28 GiB (live default, not set explicitly in `bitcoin.conf`) + an estimated ~0.35 GiB fixed overhead (block/header index, connection buffers, script-verification cache — not separately configurable, so this is a labeled estimate rather than a measurement) ≈ **4.54 GiB**.

   `btc1` + `btc2` (regtest) worst case: neither sets `dbcache`, so both run Bitcoin Core's built-in default of 450 MiB each ≈ **0.88 GiB** combined.

   `bitcoind` total worst case: 4.54 + 0.88 = **5.42 GiB**. Remaining: 7.75 − 5.42 = 2.33 GiB. Reserve ~0.3 GiB (labeled estimate) for the Docker Desktop VM's own kernel/daemon overhead beyond the four containers: **ClickHouse's safe share ≈ 2.03 GiB** — this converges with the roughly-2-GiB estimate that prompted the check. Applied: `max_server_memory_usage = 2000000000` bytes (≈1.86 GiB), rounded down slightly from the arithmetic for margin, via `clickhouse-config/memory-limits.xml` mounted to `/etc/clickhouse-server/config.d/`.

   `docker-compose.yml` changed to mount both files (`clickhouse` service), `docker compose up -d clickhouse` (never a bare `up`, never `down -v`) recreated only that container. **Proof:** row counts identical across the recreate for every table (`flows` 67,144,753, `transactions` 10,088,889, `address_stats` 10,244,591, `alerts` 480, `checkpoints` 86,873, `watchlist` 25, `taint` 0). Both settings confirmed live. The crash-shaped query, rerun as `default`, failed cleanly: `Code: 241 MEMORY_LIMIT_EXCEEDED: would use 1.11 GiB, maximum: 953.67 MiB`.

**`bitcoin.conf`'s `dbcache`, applied: 4000 → 1000 MiB, 2026-09-22.** It was sized for initial sync; the ongoing steady-state benefit of a cache that large is smaller now that the node just validates one new block at a time rather than the historical firehose IBD involves. Frees ~2.93 GiB of worst-case ceiling. Cost: a smaller in-memory UTXO cache means more LevelDB disk reads on cache misses during block validation and more frequent (if smaller) cache flushes — scales with validation load, so it matters most during a future reorg or resync, not ordinary single-block operation. `docker compose restart bitcoind` (full grace period, never killed). Proof: height 968,153 and tip hash `00000000000000000001570d080280349d1fee5991fa6ad74e8a55c9631cc766` identical before and after, `initialblockdownload: false`, `pruned: true` — no resync.

### `flows` redesign: built and proven on regtest, not applied to production

The OOM investigation's live search for a naturally-occurring fan-in address (phase 4d, point 3) led to a second, unrelated defect, found by testing the duplicate-detection query's own premise rather than trusting it: `persist.count_duplicate_transactions` queries `transactions FINAL`, grouped by `txid` — a query that can structurally never return a row, since `FINAL` is exactly what collapses duplicate `txid`s on a `ReplacingMergeTree`. It was checking the one table that cannot show this failure, while `flows` — plain `MergeTree`, no dedup at all — was never checked.

**Measured directly: 15,051,201 duplicate `(txid, direction, position)` keys in `flows`, 41,379,818 excess rows — 61.6% of all 67,144,753 rows.** Broken down by cause (hash-bucket partitioned to fit the new memory cap, sums verified exactly against the ground-truth total):

| Cause | Groups | Share |
|---|---|---|
| Pure confirm-path replay (never seen pending; `catch_up_to_tip` walked the same block range more than once) | 14,742,418 | 97.95% |
| Clean structural pending+confirmed pair (by design, no replay) | 219,756 | 1.46% |
| Structural pair also hit by replay | 89,027 | 0.59% |

Root cause: `confirm.process_block` already computes `known_txids()` but only uses it for a stats counter, never to skip a write — `catch_up_to_tip` walking an overlapping block range (exactly what the phase-4 catch-up-message-loss trials did, four times, at 500-block scale) reinserts every flow row in range, unguarded.

**Downstream impact, precisely scoped by grepping every consumer, not assumed:** `address_stats`/`address_stats_mv` — raw `sum()`/`count()`, no dedup — is materially corrupted by this. Rules 1–3's shadow queries are not: `common.find_input_side_candidates`/`find_receiving_txids` dedupe to `(txid, position)` in Python; `wallet_drain.address_totals`/`fan_in_consolidation.window_value_received` dedupe via SQL `DISTINCT (txid, position, value)`; replay duplicates are identical on exactly those three columns, so they already collapse correctly.

**A second, independent defect found in the same investigation: the parent-pending address trap.** An input resolved via `gettxout` at mempool time can be `parent_pending` (its own parent output still unconfirmed) — written with `address=''`, `value=0` — then resolved for real once its parent confirms, at the *same* `(txid, direction, position)`. Confirmed directly against live data: 44,502 input keys show more than one distinct `address`/`resolution_state`, e.g.
```
txid=5071...b72efd position=0  address=''                                            value=0      parent_pending
txid=5071...b72efd position=0  address='bc1q2kv27d25vmfku6n8zd62hwetwhh5w72kxpw8cd'  value=16627  resolved
```
Worse: `common.find_input_side_candidates` picks the value from whichever copy has the *earliest* `seen_at` — for these 44,502 inputs, that's the placeholder (`value=0`), not the real resolved value. A pre-existing correctness bug in rule 1 and rule 2, surfaced as a side effect of this investigation, not something either rule's own testing had caught.

**Design, and why two earlier versions of it were wrong:**

*First version* proposed `ORDER BY (address, direction, position, txid)` as a `ReplacingMergeTree`, without noticing that `address` is exactly the field the parent-pending trap changes after first write — a row written `parent_pending` with `address=''` and later rewritten `resolved` with a real address would never merge; both would persist forever under that key.

*Two resolutions were weighed; the alternative was measured, not just argued against.* (a) Exclude `address` from the sorting key, recover per-address reads via a secondary index. (b) Guarantee an input's address never changes after first write, by deferring the flows row until resolution. Built two real test tables from an 8.39M-row slice of live `flows`: one `ORDER BY (address, direction, position, txid)`, one `ORDER BY (txid, direction, position)` with a `bloom_filter` index on `address`. Same `WHERE address = 'X'` query against both:

| Ordering | Rows read | Bytes read |
|---|---|---|
| Address-first | 360,448 | 19.90 MiB |
| txid-first + bloom filter | 8,388,564 (the entire table) | 398.67 MiB |

The bloom filter gave no real pruning — a given address's rows are scattered pseudo-randomly across txid-ordered granules, so nearly every granule matched. At production scale that turns every rule 1–3 query, every 15-second poll, every watch, into a near-full-table scan — the same query shape that caused the OOM, now the *default* behaviour of ordinary detection queries rather than an accidental one-off. Option (b) chosen.

*Second version* of (b) proposed a write-path guard in `confirm.py`: skip re-adding a transaction's flows rows if this exact `(txid, block_height)` confirmation was already recorded. Held, not built — wrong on two counts. It contradicts `02-architecture.md`'s explicit design: "duplicates are prevented by the natural key rather than by delivery guarantees" — at-least-once delivery, idempotent sinks, no guard. And it fails in the dangerous direction: `transactions` and `flows` flush as two separate `INSERT`s; a crash between them leaves a `transactions` row with no matching `flows` rows, and a guard reading `transactions` to decide whether to skip would skip that block's `flows` forever — a silent, permanent loss, worse than the duplication it would prevent.

**Final design, built:**

- `block_height`, `block_hash`, `block_time` removed from `flows` entirely. Confirmed by grepping every consumer in `detection/`: nothing reads them — confirmation status already comes exclusively from `transactions FINAL` via `common.transaction_status`.
- `ingestor/persist.py`: `Persistence.add()` (mempool path) no longer writes a `flows` row for an input still `parent_pending`/`unresolved` — it waits for resolution, which arrives at the latest via the confirm path (`resolve_confirmed_input` succeeds in every case except the pruned node's undo-data window being exceeded, a genuine terminal state worth recording once, not deferring). `Persistence.add_confirmed()` writes unconditionally, unchanged in that respect.
- `schema/08_flows_redesign.sql`: `flows` becomes `ReplacingMergeTree(seen_at)`, `ORDER BY (address, direction, position, txid)` — preserving the address-first prefix every rule 1–3 query already depends on. No write-path guard anywhere; deduplication is purely the engine collapsing identical natural keys, exactly matching `02-architecture.md`'s model.
- Cost of deferring, stated plainly: a watched address's own outgoing transaction, if it itself spends a still-unconfirmed parent — a rapid chained hop, notably also the shape of an attacker deliberately relaying funds fast to evade single-hop tracing — is not visible to rule 1 until that transaction confirms, not when it enters the mempool. Ordinary movements (spending an already-confirmed output, the large majority of real traffic) are unaffected.
- `ingestor/persist.py`: added `count_duplicate_flows`, keyed on `(txid, direction, position)` with `FINAL` — deliberately not `flows`'s own `ORDER BY`, since checking the storage key would be exactly as vacuous as `count_duplicate_transactions` checking `transactions FINAL` by `txid`. Wired into `main.py`'s shutdown summary alongside the existing check.

**A build-time-only discovery, fixed in the same pass:** the first regtest run of the new schema showed *every* flush failing and retrying indefinitely — `address_stats_mv` still referenced the now-removed `flows.block_time`. Not a cosmetic issue; it broke the ingestor's own flush success/retry logic outright. `schema/09_address_stats_mv_fix.sql` sources `first_seen`/`last_seen` from `flows.seen_at` instead. Minimal fix only, not a correctness fix — see the known gap below.

**Known gap, recorded rather than decided: `address_stats` will keep inflating on replay regardless of the `flows` redesign.** `address_stats_mv` fires per insert batch, before any merge or `FINAL` ever runs — a replayed flow now collapses correctly in `flows` itself (proven above), but still triggers the materialized view's `sum()`/`count()` a second time, since the MV has already summed and written its own row before ReplacingMergeTree ever gets a chance to deduplicate anything. No storage-engine change to `flows` can reach this; it is a property of how materialized views trigger, not of what they read. Nothing in `detection/` reads `address_stats` today (confirmed by grep, same audit that scoped the `flows` fix) — but the address overview screen (`07-ui-spec.md`, phase 7, not yet built) will. Two options, not chosen here:

- Query `flows FINAL` directly at read time instead of relying on `address_stats`, computing the same aggregates on demand — correct by construction, no separate table to keep in sync, but pays `FINAL`'s read cost on every screen load rather than once at write time.
- Rebuild `address_stats` from a deduplicated source — e.g. a periodic full recomputation against `flows FINAL` rather than the current trigger-on-insert design — keeping the precomputed-aggregate shape but changing when and how it's populated.

**Proven on regtest, twice, with no write-path guard involved in either:**

`regtest/flows-dedup-test.sh` — the parent-pending trap. A real chained-unconfirmed spend (TXA unconfirmed, TXB spends TXA's still-unconfirmed output): asserted zero `flows` rows for TXB's input while `parent_pending` (deferred, not a placeholder), mined together, asserted exactly one row via `FINAL` with the real resolved address and value.

`regtest/flows-replay-dedup-test.sh` — replay, the dominant cause (97.95% of the measured total). Confirmed a real transaction, stopped the ingestor, rewound the checkpoint to just before that block (the same shape a restart after downtime, or the phase-4 catch-up trials, produce), restarted, and mined one more block so a genuine `'C'` ZMQ event forced `catch_up_to_tip` to walk forward from the stale checkpoint through the already-confirmed block on its way to the new tip — reprocessing it, unguarded. Asserted the *raw* table actually held two rows afterward (proving replay genuinely happened, not just that nothing went wrong), with `address`/`direction`/`position`/`txid` identical and only `seen_at` differing, then asserted `FINAL` collapsed them to exactly one, correctly resolved row. Extended duplicate check clean in both tests.

**Checked before committing: is `08_flows_redesign.sql`'s `DROP TABLE IF EXISTS flows` safe on a genuinely fresh, empty database** — the scenario every `schema/*.sql` file runs under automatically via `docker-entrypoint-initdb.d` whenever the `clickhouse-data` volume is created fresh. Verified directly, not just reasoned about: `clickhouse-regtest` has no persistent volume, so every regtest run already *is* exactly this scenario, and both runs bootstrapped all nine files cleanly. Ran one more standalone check of the bootstrap log alone (no ingestor involved): zero errors, final state correct (`flows` is `ReplacingMergeTree` with the right sorting key, `address_stats`/`address_stats_mv` present and consistent). Safe; both files stay in `schema/`.

**Code and production schema are out of step since `db7197d`: checked, and guarded against.** The committed ingestor writes the redesigned `flows` shape; production still has the old table. Verified live, not assumed: inserting the new shape (no `block_height`/`block_hash`/`block_time`) against the old schema does **not** fail — ClickHouse's JSONEachRow insert silently defaults the omitted columns (`block_height=0`, `block_hash=''`, `block_time=1970-01-01`, confirmed against a throwaway copy of the old schema), which is exactly this project's own "pending" sentinel, written on every row including fully confirmed transactions. Silent corruption, not a crash, and the code had no way to notice on its own. `ingestor/schema_check.py`, called at the very start of `main()` before any RPC/ZMQ setup or checkpoint read: compares `flows`'s live engine and column set against what `persist.build_flow_rows` actually writes, raises and refuses to start on any mismatch. Verified both directions live: refuses against the current production database (`flows engine is 'MergeTree' ... do not proceed`) and passes cleanly against the redesigned regtest schema.

**Not built:** the production migration itself (backfill, rename, cutover against the live 67M-row `flows`) — still to be planned, separately, against real data rather than a fresh volume.

### Rule 4 (dormancy): why the watchlist is the wrong instrument for measuring it, and how it's measured instead

Populating the watchlist with genuinely long-dormant addresses so rule 4 could be exercised was considered and rejected. Watching a dormant address is the wrong instrument for measuring rule 4's false-positive rate: by definition it will predictably produce zero alerts over any realistic observation window, which tells us nothing about the rule's real population or how often it should be expected to fire. `dumptxoutset` (the only way to enumerate UTXO creation heights broadly, since the node has no `txindex` and no RPC to list UTXOs by age) was also considered and rejected for this purpose specifically — it suspends the live node's network activity for several minutes to serialize the ~15 GB chainstate, a real operational cost against the live protected node, for a measurement that would not have answered the actual question anyway.

**Rule 4's population is measured across all live traffic instead, not via the watchlist.** `gettxout`, already called during ordinary mempool-window input resolution (`ingestor/decode.py:resolve_input`), returns `confirmations` and `bestblock` in its response today — verified live against the node — but `resolve_input` currently discards both, keeping only `value`, `address` and `script_type`. Every spend the ingestor observes already reveals the age of what it spends: `created_height = height(bestblock) - confirmations + 1`. This needs no snapshot and no historical backfill — it is exactly `06-detection.md`'s point that rule 4's age comes from the UTXO record itself, not accumulated history.

Two gaps stand between that and a measurement, stated plainly rather than fixed silently, since both touch protected territory:

- **`flows` has no column for it.** Approved in principle, **as `Nullable(UInt32)`, not a sentinel default.** The first version of this proposal used `UInt32 DEFAULT 0`, on the (wrong) analogy with `block_hash`/`block_height`'s existing "not applicable" sentinels — but `0` here would read as "created at the genesis block," making every row written before this column existed look maximally dormant and firing rule 4's measurement on all of them. That is the exact sentinel-value mistake this project already avoids everywhere else (`docs/06-detection.md`'s own alert `detail` fields, the checkpoint component-naming rules). `NULL` means unknown, correctly and distinctly, for rows written before this column existed and for `direction='in'` rows that resolved to `parent_pending`/`unresolved` rather than `resolved` — moot for `direction='out'` rows, which under the flows redesign above are the only kind ever written without full resolution being a precondition. Migration: `schema/10_input_creation_height.sql` (file number moved from the original `08` once that number was taken by the flows redesign; a new file regardless, never an edit to `03_flows.sql`), `ALTER TABLE flows ADD COLUMN created_height Nullable(UInt32)`, against the *redesigned* `flows` (`schema/08_flows_redesign.sql`) once that itself is applied to production. **Not applied — the memory cap is now fully in and proven, but `flows` itself is still only proven on regtest, not migrated in production; this waits on that migration, not the other way around.**
- **`decode.py` needs to capture and thread the two fields through.** `resolve_input`'s `"resolved"` branch would carry `confirmations` forward; `created_height` needs the height of `bestblock`, which can come free from `persistence.last_block_height` (already tracked, zero extra RPC calls, off by at most the ~1 block the ingestor might lag the node — irrelevant against a 2-year/~105,120-block dormancy threshold) or exactly via a small `{bestblock_hash: height}` cache backed by one `getblockheader` call per newly-seen block. Not applied without confirmation.

The measurement itself would be a standalone script in `detection/` (not a detection rule, not writing through `alerts`, no watch_id — real or fake): scan `flows WHERE direction='in' AND resolution_state='resolved' AND created_height IS NOT NULL AND created_height <= tip_height - 105120` (two years) across the whole observation window, reporting spends-per-day and their age distribution. That is rule 4's real false-positive population — every dormancy break in live traffic, not one address's silence.

### A real watchlist: selection method and categories

The prior watchlist had only ever contained self-chaining test artifacts (recorded in 4b/4d above), so every measurement to date described one artificial address rather than Bitcoin. Rebuilt with 22 addresses spanning three categories, chosen to exercise rules 1 through 3 (rule 4 is measured project-wide instead, per above, not via the watchlist — see that section):

- **Rule 1, high activity:** addresses transacting frequently and repeatedly, both across the historical ingestion window and in the live mempool at selection time.
- **Rule 3, receiving from many sources:** addresses paid by many *distinct transactions* within a single live snapshot — the actual multi-transaction, time-windowed shape rule 3 measures, not one transaction's own simultaneous input count.
- **High-volume, suppression-precursor:** addresses moving large absolute value in a single transaction or a short burst of them — the shape a future suppression list will need real examples of.

**Sourcing method, and why it changed mid-task.** Ranking `address_stats` by `tx_count` was tried first and abandoned: it surfaces the same handful of addresses across every ingestion session (18 August, 5 September, 12 September, 14 September), every one of them active only within the same narrow dev-session wall-clock windows — the shape of test/dev traffic incidentally captured while the ingestor happened to be running, not a representative sample. This is a wider version of the contamination already known from 4b/4d, not limited to the handful of addresses that were ever formally on `watchlist`.

**Quantified:** `flows` holds 67,144,753 rows total, spread across exactly four ingestion days — 18 August (7,094 rows, 0.01%), 5 September (509,498 rows, 0.76%), 12 September (38,474,227 rows, 57.29%), 14 September (28,153,934 rows, 41.93%). 12 and 14 September — the phase 4b/4c/4d dev-test sessions — together account for 66,628,161 rows, **99.23% of everything ever ingested.** Any ranking over the full history is effectively a ranking over two afternoons of dev testing, not 27 days of mainnet observation.

Candidates were sourced instead directly from the live node's current mempool via RPC — a decoded sample, independent of the ingested ClickHouse history entirely, cross-checked against historical `tx_count` only as corroboration for a couple of candidates. The three previously-watched self-chaining test addresses were confirmed absent from the current live mempool's top activity, consistent with being synthetic rather than real ongoing participants.

**One candidate rejected, and a real data-quality gap found by tracing why.** A high-frequency candidate for the activity category was rejected by `watchlist_cli.py`'s own address-format validation (too short to be a real address). Tracing it: `scriptPubKey.type` for the output in question is `"anchor"` — a fixed, non-unique BIP-118 ephemeral-anchor script template that every Lightning Network commitment transaction using this convention pays identically. It is not a wallet, which is exactly why it had such extreme apparent activity: it aggregates all such Lightning activity network-wide as one address. `address_stats_mv`'s `WHERE address != ''` filter does not exclude non-standard script types like this one, so this same inflation is presumably present, quietly, inside `address_stats` today for this and potentially other shared script templates. Not fixed here — flagged for whoever next relies on `address_stats` for anything resembling "this address's real activity level."

Address strings and full per-address reasoning are in `watchlist.local.md` (gitignored, not committed) per `01-thesis.md`'s no-attribution position — this document records the method and categories only.

### Definition of done

- All four tier 1 rules running in shadow against live traffic
- **A measured false positive rate for each, from manual classification of 100 shadow alerts per rule**
- Rules only enabled after their rate is recorded
- `docs/tuning-log.md` started

**Time:** 3 to 4 days, plus the shadow observation period.

---

## Phase 5: Graph, and the benchmark

### 5a. Benchmark first

**Before building on Neo4j, measure whether it is needed.**

The BlockSci paper argues an in-memory analytical database is "orders of magnitudes faster than using general-purpose graph databases" for blockchain analysis. That targets whole-chain workloads rather than bounded traversal, but the claim is tested rather than argued with.

Benchmark: a 6-hop trace over a materialised subgraph in Neo4j, against the equivalent recursive query in ClickHouse over the same data.

If ClickHouse is competitive, Neo4j is removed and the stack simplifies considerably.

**Time:** half a day.

### 5b. If Neo4j survives

- Constraints applied before any data load
- Subgraph materialisation on watch creation, capped by node count and depth
- Supernode identification and labelling
- Live graph writes on a separate thread, never blocking the ingestor
- Peel chain detection
- Trace and shortest-path queries, time-ordered, avoiding traversal through supernodes

**Done when:** a watch on a live active address produces a correct graph within a minute.

**Time:** 2 to 3 days.

---

## Phase 6: Report generator

**Promoted from a feature to its own phase.** `12-market-process.md` established that the report is the product.

- Plain-language summary
- Timeline with transaction IDs
- FIFO trace path, each hop evidenced
- Confidence on every inference
- Assumptions register with published error rates
- Provenance block: source data, generation time, chain state, hash

**Done when:** a report can be generated for a real traced address and read end to end by someone with no blockchain knowledge.

**Time:** 2 to 3 days.

---

## Phase 7: API and interface

- FastAPI over both stores
- Victim path: three screens, relief-not-delight
- Analyst path: address overview, graph, alerts, configuration
- System status screen with self-reported health
- Anti-recovery-scam warning on landing page and in every email
- Email alerting through a transactional provider

**Done when:** end to end. An address is submitted, funds move, an email arrives, the link opens a plain summary, and a report can be generated.

**Time:** 5 to 7 days.

---

## Phase 8: Publication

- README with screenshots
- Technical write-up. Strongest candidates: the `include_mempool` silent failure, the FIFO methodology decision and its basis in Clayton's Case, and the forty-six corrections found before implementation
- Short demonstration recording

**Before any public deployment:** the GDPR position in `15-user-and-regulation.md` requires a lawful basis, a retention policy, and consideration of a DPIA. Wallet addresses may constitute personal data and pseudonymous data remains in scope.

**Time:** 2 days, plus the data protection work.

---

## Total

Roughly 20 to 30 working days, up from the original estimate. The increase is reorg handling, shadow mode, the report generator, and the regtest harness.

---

## Customer discovery — parallel

Not a phase. Runs alongside, and one question blocks Phase 7.

**Target practitioners, not victims.** A fintech fraud team's warning: "Conventional interviews with users who have been victims may give you incorrect information. Those that have suffered financial losses are not always the most forthcoming." Research found 73.3% of payment-based victims declined to disclose amounts paid.

Practitioners see many cases, have no shame response, and can describe patterns a single victim cannot. Asset recovery solicitors, Action Fraud, bank fraud teams, insolvency practitioners.

Questions to answer:

1. **Would a UK police force accept an automated tracing report, and in what format?** This blocks the report design
2. **Is the primary user the victim or the recovery professional?** This blocks the interface emphasis
3. What is the minimum evidentiary standard for a Crypto Wallet Freezing Order application?
4. Does producing tracing reports for others carry regulated-activity implications?

---

## Scope reduction

If time requires cutting, in order:

1. Tier 2 and tier 3 rules
2. Watch configuration screen, with settings hardcoded
3. The trace graph, which is the largest frontend item and aimed at the audience least likely to benefit
4. Neo4j entirely, with traces as recursive ClickHouse queries

Item 4 is now more likely than previously, pending the Phase 5a benchmark.

**Not cut under any circumstances:** reorg handling, shadow-mode measurement, the report generator, and the anti-recovery-scam warning. The first two are correctness. The third is the product. The fourth is a safeguarding obligation.
