# 08. Build plan

Seven phases, each with a definition of done. No phase begins before the previous one meets it. The failure mode this guards against is several components half-built and nothing demonstrable.

Time estimates assume focused days.

---

## Phase 0: Node sync

Everything is blocked behind this, and it runs unattended for days, so it starts first.

- Docker and Docker Compose installed
- `docker-compose.yml` with the `bitcoind` service only
- Configuration per `03-bitcoin-node.md`

**Done when:** `getblockchaininfo` reports `initialblockdownload: false` and the height matches a public explorer.

**Time:** about an hour of work, then one to four days of syncing.

Phases 1 and 2 require no node and run in parallel.

---

## Phase 1: Documentation

Architecture written down before any implementation code exists.

The substantive work here is the typology mapping: establishing which money laundering patterns from traditional payments transfer to a UTXO ledger and which do not. Layering maps almost directly. Structuring depends on a reporting threshold with no Bitcoin equivalent. That distinction shapes which detection rules in `06-detection.md` are worth building and which are included only to make the comparison explicit.

**Done when:** the full architecture can be explained to a non-technical reader in five minutes without reference to the documents.

**Time:** 1 to 2 days.

---

## Phase 2: Design system and screens

Runs in parallel with the sync.

- Design system per `07-ui-spec.md`
- Wireframes for all six screens
- High-fidelity mockups
- Exported assets into the repository

**Done when:** mockups exist for every screen and are internally consistent.

**Time:** 1 to 2 days.

---

## Phase 3: Ingestion

The hardest phase.

- ClickHouse added to the compose file, schema from `05-data-models.md` applied
- Ingestor service: ZeroMQ subscriber, transaction decoder, input resolution per `04-ingestion.md`
- Batched inserts, flushing at 1,000 rows or 2 seconds
- Metrics from the outset: transactions per second, resolution rate, lag

Verification is manual before proceeding. At least five transactions stored by the ingestor are checked against a public block explorer, confirming every input address, output address and amount. The sample includes a multi-input transaction and a SegWit transaction.

**Done when:** 24 hours of unattended operation, input resolution above 95%, and hand-verification passes.

**Time:** 3 to 5 days. Address decoding consistently takes longer than expected.

---

## Phase 4: Detection

- Watchlist matcher
- Tier 1 rules from `06-detection.md`: watchlist movement, wallet drain, fan-in consolidation, dormancy break
- Alerts table and write path
- Manual review of 100 real alerts to establish a measured false positive rate

Tier 2 and tier 3 rules are deferred. Behavioural profile shift and velocity anomaly require 30 days of accumulated history. Peel chain requires the graph layer. Fan-out and proximity to labelled addresses require an exchange address set that is not available.

**Done when:** alerts fire against live traffic and a measured false positive rate is recorded.

**Time:** 2 to 3 days.

---

## Phase 5: Graph

- Neo4j added to the compose file, constraints from `05-data-models.md` applied before any data load
- Subgraph materialisation on watch creation
- Live graph writes on a separate thread, never blocking the ingestor
- Rule 2, peel chain detection
- Trace and shortest-path queries

**Done when:** a watch on a live active address produces a correct graph within a minute.

**Time:** 2 to 3 days.

---

## Phase 6: API and interface

- FastAPI over both stores
- React frontend built from the Phase 2 mockups
- Force-directed trace graph. The hardest frontend component; budgeted accordingly
- Email alerting through a transactional provider

**Done when:** end to end. An address is submitted, funds move, an email arrives, and the link opens a graph showing the movement.

**Time:** 4 to 6 days.

---

## Phase 7: Documentation and write-up

- README with screenshots
- Technical write-up of the design decisions. The pruning constraint forcing mempool-first ingestion, described in `04-ingestion.md`, is the most substantive of these: a real constraint, a non-obvious solution, and a consequence that turned out to be architecturally correct
- Short demonstration recording

**Time:** 1 to 2 days.

---

## Total

Roughly 15 to 25 working days beyond node sync time.

## Scope reduction

If time requires cutting, the order is:

1. Rules 2, 5, 7 and 8 from `06-detection.md`
2. Screen 3, with watch configuration hardcoded
3. Neo4j, with traces implemented as recursive ClickHouse queries

The third is significant but survivable. A documented decision explaining the two-store design, why ClickHouse was built first, and exactly how the graph layer slots in demonstrates more than a half-working graph implementation would.

Ingestion quality and the false positive measurement are not cut. Those are what the rest of the system's credibility rests on.
