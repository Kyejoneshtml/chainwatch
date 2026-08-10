# 02. Architecture

## Data flow

```
Bitcoin P2P network
        |
        v
[ bitcoind ]  pruned full node
        |
        |  ZeroMQ publishes: rawtx (unconfirmed), rawblock (confirmed)
        |  JSON-RPC answers: gettxout, getblock, getblockchaininfo
        v
[ ingestor ]  Python service
        |     - decodes raw transactions
        |     - resolves input addresses (see doc 04, this is the hard part)
        |     - normalises into flat rows
        |
        +-----------------------------> [ ClickHouse ]  everything, forever
        |                                     |
        |                                     |  aggregate queries
        v                                     v
[ watchlist matcher ]                   [ detection jobs ]
        |                                     |
        |  address is watched?                |  signal fired?
        v                                     v
[ Neo4j ]  subgraph only            [ alerts table in ClickHouse ]
        |                                     |
        +------------------+------------------+
                           |
                           v
                     [ API layer ]  FastAPI
                           |
                           v
                     [ web UI ]  React, D3 for the graph
```

## Components

### bitcoind

Bitcoin Core in pruned mode. Validates the full chain, keeps only recent blocks on disk, maintains the complete UTXO set. Publishes new transactions and blocks over ZeroMQ.

Covered in detail in doc 03.

### ingestor

A Python service. Subscribes to the node's ZeroMQ sockets, decodes each raw transaction, resolves the addresses on both sides, and writes rows.

This is the only genuinely difficult component and doc 04 is entirely about it. Everything else is configuration and query writing.

### ClickHouse

The archive. Every transaction, every input, every output, from the moment you switch the ingestor on. Append only. This is where all aggregate analysis happens.

Note that you are building history forward from day one, not backfilling. On a pruned node you cannot recover the past. Accept this. Two weeks of live data is enough to demonstrate everything, and "we index forward from ingestion start" is a perfectly respectable architectural statement.

### watchlist matcher

Cheap in-memory check. Every transaction the ingestor sees, is either side of it an address currently on a watchlist, or within N hops of one? If yes, the transaction also goes to Neo4j and may trigger an alert.

Keep the watchlist in Redis or just a Python set refreshed every few seconds. Do not query a database per transaction.

### Neo4j

The working set. Addresses and the value flows between them, but only for subgraphs that someone is actually watching.

### detection jobs

Scheduled queries against ClickHouse that look for the patterns in doc 06. Run them on a short interval, one to five minutes. They write into an alerts table.

Deliberately separate from the ingestor. The ingestor must never block, because if it falls behind the mempool it starts missing the input resolution window described in doc 04.

### API layer

FastAPI. Thin. Queries ClickHouse for numbers and time series, queries Neo4j for graphs, serves both to the UI as JSON.

### web UI

React. D3 for the network graph, as Michael suggested. Everything else is standard components.

Built design-first in Claude Design, exported, then wired up. See doc 07.

## Everything runs in Docker Compose

Per Michael's advice. One `docker-compose.yml`, five services, `docker compose up` and it works. Portable to a bigger machine by copying the directory.

Services: `bitcoind`, `clickhouse`, `neo4j`, `ingestor`, `api`. Add `redis` if the watchlist grows past what a Python set handles comfortably.

Named volumes for the persistent data. One important exception: put the bitcoind data directory on a bind mount to a path you choose explicitly, so you can see the disk usage with `du` and move it to an external drive without wrestling Docker.

## Deliberate simplifications

Written down so you can answer "why didn't you use X" honestly rather than looking like you did not know about X.

**No message queue between ingestor and databases.** A production system would put Kafka or Redis Streams in the middle so that a database restart does not lose transactions. For a single-machine portfolio build it is a component to operate for little benefit. If asked, the answer is that you would add Redis Streams as the first change under real load, and you know exactly where it would go.

**Single ingestor process.** No horizontal scaling. Bitcoin produces a few hundred thousand transactions a day, which is roughly five per second average. Python handles that comfortably. Say so with the number, because the number is what shows you thought about it.

**No historical backfill.** Discussed above. Forward-only from ingestion start.

**No address labelling data.** You have no exchange deposit address list. You can partially work around this with clustering heuristics and by hand-labelling a few well-known addresses from public sources. Be explicit that this is the biggest functional gap versus a commercial tool.
