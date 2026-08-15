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

**Incomplete.** `reorg.sh` mines orphaned blocks with `generatetoaddress`, so the orphaned blocks contain only coinbase transactions. The test proves the node reorgs; it proves nothing about how transactions in an orphaned block are handled, which is what the ingestor actually needs.

Of Lopp's five failure modes in `11-prior-art.md`, only reorganizations are covered. Double spends, spending of unconfirmed outputs, chaining of unconfirmed outputs, and transactions that never confirm are all untested.

Extending the harness to cover these is a prerequisite for 3c.

### 3b. ClickHouse and schema

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

### 3d. Reorg handling

- Block hash stored per confirmed row
- Detection by hash comparison and by the sequence topic
- Rollback in reverse order, alert invalidation, reprocessing
- **Tested against the regtest harness**, not hoped for

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
