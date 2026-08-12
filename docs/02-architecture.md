# 02. Architecture

## Data flow

```
Bitcoin P2P network
        |
        v
[ bitcoind ]  pruned full node
        |
        |  ZeroMQ: rawtx, rawblock, sequence  -- NOTIFICATION ONLY
        |  JSON-RPC: gettxout, getblock, getrawtransaction  -- SOURCE OF TRUTH
        v
[ ingestor ]  Python service
        |     - ZMQ notification triggers RPC fetch
        |     - decodes transactions
        |     - resolves input addresses (see doc 04)
        |     - detects reorgs via stored block hash
        |     - periodic mempool reconciliation
        |
        +--> [ checkpoint store ]  last processed block hash, last reconciliation
        +--> [ dead letter store ]  repeatedly failing transactions
        |
        +-----------------------------> [ ClickHouse ]  everything, forever
        |                                     |
        v                                     v
[ watchlist matcher ]                   [ detection jobs ]
        |                                     |  shadow mode first
        v                                     v
[ Neo4j ]  watched subgraphs only      [ alerts table ]
        |                                     |
        +------------------+------------------+
                           |
                           v
                     [ API layer ]  FastAPI
                           |
                     +-----+-----+
                     v           v
              [ victim view ]  [ report generator ]
```

## Components

### bitcoind

Bitcoin Core, pruned, with four ZeroMQ topics published. Detail in `03-bitcoin-node.md`.

### ingestor

The only genuinely difficult component. Detail in `04-ingestion.md`.

Three properties govern its design:

**It never silently fails.** Every failure is recorded and counted. This follows from Lopp's observation that a single missed UTXO update can cascade until the index is unusable.

**It never blocks.** ClickHouse writes are batched, Neo4j writes are queued to a separate thread. If the mempool subscriber falls behind, input resolution starts failing as transactions confirm before they are processed.

**It is restartable.** A checkpoint records the last processed block hash and the last mempool reconciliation timestamp, so a restart resumes rather than restarting.

### ClickHouse

The archive. Every transaction, input and output from ingestion start. Append-only, with a version column for status transitions. All aggregate analysis happens here.

History is built forward, not backfilled. On a pruned node the past cannot be recovered, and full historical indexing is not feasible on this hardware regardless — electrs indexes require 250GB to 1.3TB. "We index forward from ingestion start" is the architectural position.

### watchlist matcher

An in-memory check on every transaction: is either side within N hops of a watched address? Kept as a Python set refreshed on a short interval. No database query per transaction.

### Neo4j

Materialised subgraphs around watched addresses only. Provisional, pending the benchmark described in `13-engineering-practice.md`.

### detection jobs

Scheduled queries against ClickHouse, running on a short interval, writing to an alerts table.

**Every rule runs in shadow mode first**, recording what it would have alerted on without producing user-facing alerts, until its false positive rate is measured. See `06-detection.md`.

Deliberately separate from the ingestor, which must never block on analysis.

### checkpoint store

Last processed block hash, last mempool reconciliation timestamp, last successful ClickHouse flush. Small, durable, read on startup.

### dead letter store

Transactions that fail processing repeatedly. Not retried indefinitely, not dropped. Inspected manually.

### API layer

FastAPI. Queries ClickHouse for aggregates, Neo4j for graphs, serves both as JSON.

### victim view and report generator

Two distinct outputs. The victim view answers one question at a time in plain language. The report generator produces the police-ready document with full evidence and provenance.

This split follows from `15-user-and-regulation.md`: the same data serves a distressed person and an investigator, and those are different readers.

## Everything runs in Docker Compose

One file, services: `bitcoind`, `clickhouse`, `neo4j`, `ingestor`, `api`. Named volumes for persistence, except the bitcoind data directory which uses an explicit bind mount so disk usage is visible.

A separate compose file provides the **regtest harness** — a private Bitcoin network for testing reorg handling deliberately. Detail in `08-build-plan.md`.

## Deliberate simplifications

Written down so the reasoning survives.

**No message queue.** A production system would put Kafka or Redis Streams between ingestor and databases so a database restart loses nothing. The streaming literature is clear that this is often unnecessary: "a well-monitored at-least-once pipeline with idempotent sinks is often sufficient." Idempotency comes from the txid as natural key. Redis Streams would be the first addition under real load.

**Single ingestor process.** Bitcoin produces roughly 5 to 7 transactions per second. Python handles that comfortably.

**No historical backfill.** Discussed above.

**No address labelling data.** The largest functional gap. OFAC sanctioned addresses are ingestible and cover a small fraction.

**At-least-once, not exactly-once.** Duplicates are prevented by the natural key rather than by delivery guarantees. A continuous duplicate-detection query runs in production; if it ever returns rows, the idempotency contract is broken.
