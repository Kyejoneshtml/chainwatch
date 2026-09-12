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
