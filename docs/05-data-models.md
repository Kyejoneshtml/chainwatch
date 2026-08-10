# 05. Data models

Michael's question, "what's the difference between modelling it in Neo versus modelling it in ClickHouse", is the interview question. Here is the answer in concrete form.

The same real-world fact, "0.5 BTC moved from address A to address B", gets stored twice, in two shapes, because two different kinds of question are being asked of it.

## ClickHouse

Wide, flat, denormalised, append-only. Joins are avoided. Storage is traded for query speed.

### `transactions`

One row per transaction.

```
txid              String
status            Enum8('pending' = 1, 'confirmed' = 2, 'orphaned' = 3)
seen_at           DateTime64(3)     -- when your ingestor saw it
block_height      UInt32            -- 0 while pending
block_time        DateTime          -- 0 while pending
input_count       UInt16
output_count      UInt16
input_value       UInt64            -- satoshis, never floats
output_value      UInt64
fee               UInt64
vsize             UInt32
is_coinbase       UInt8
inputs_resolved   UInt8             -- coverage flag from doc 04
```

Engine: `ReplacingMergeTree(seen_at)` ordered by `(txid)`. Replacing lets the confirmed row supersede the pending row on the same txid.

### `flows`

The one that does the work. One row per input and per output, flattened.

```
txid              String
direction         Enum8('in' = 1, 'out' = 2)
position          UInt16            -- vin or vout index
address           String            -- '' if unresolvable
value             UInt64            -- satoshis
address_type      LowCardinality(String)   -- p2pkh, p2wpkh, p2tr, ...
block_height      UInt32
block_time        DateTime
seen_at           DateTime64(3)
is_change         UInt8             -- heuristic, see doc 06
```

Engine: `MergeTree` ordered by `(address, block_time, txid)`.

That ordering key is the important decision. Ordering by address first means every query of the form "everything this address ever did" reads a contiguous run of disk. That is the most common query in the product, so optimise for it.

Add a skip index on `block_time` for the time-range aggregations.

### Why satoshis as UInt64

Never store Bitcoin amounts as floats. 0.1 + 0.2 does not equal 0.3 in binary floating point, and in a financial tool that is unacceptable. One BTC is 100,000,000 satoshis. Store integers, divide at display time only.

This is a small thing that people who have worked with financial data notice immediately.

### `address_stats`

A materialised view maintained incrementally by ClickHouse, so you never scan `flows` to answer "what is this address's balance and history".

```
address           String
first_seen        SimpleAggregateFunction(min, DateTime)
last_seen         SimpleAggregateFunction(max, DateTime)
total_received    SimpleAggregateFunction(sum, UInt64)
total_sent        SimpleAggregateFunction(sum, UInt64)
tx_count          SimpleAggregateFunction(sum, UInt64)
```

Engine: `AggregatingMergeTree` ordered by `(address)`.

Materialised views in ClickHouse are insert triggers, not cached queries. They update as rows arrive. This is a genuinely different mental model from a Postgres materialised view and worth understanding.

### `alerts`

```
alert_id          UUID
watch_id          UUID
address           String
rule              LowCardinality(String)
severity          Enum8('low'=1,'medium'=2,'high'=3,'critical'=4)
txid              String
value             UInt64
detail            String            -- JSON
created_at        DateTime64(3)
acknowledged      UInt8
```

### Queries ClickHouse is for

- Total value received by an address today versus its 90 day average
- Every output between 0.99 and 1.01 BTC in the last hour (round-amount structuring)
- Top 500 addresses by inflow in the last 15 minutes
- Transaction velocity distribution across the whole network
- How many transactions per second is the ingestor handling

All aggregations over large row counts. All fast in a columnar store.

## Neo4j

Narrow, connected, sparse. Only what is being watched.

### Nodes

```
(:Address {
    address: String,        -- unique constraint
    first_seen: DateTime,
    last_seen: DateTime,
    total_received: Long,   -- satoshis
    total_sent: Long,
    tx_count: Integer,
    label: String,          -- 'exchange', 'mixer', 'victim', null
    risk_score: Float,
    cluster_id: String      -- from common-input-ownership
})

(:Transaction {
    txid: String,           -- unique constraint
    block_height: Integer,
    block_time: DateTime,
    fee: Long,
    input_count: Integer,
    output_count: Integer,
    is_coinjoin: Boolean
})

(:Watch {
    watch_id: String,
    address: String,
    created_at: DateTime,
    hop_depth: Integer,
    notify_email: String
})
```

### Relationships

Model it both ways. This is a real design decision, not indecision.

**Detailed, for accuracy:**
```
(:Address)-[:FUNDED {value, vin}]->(:Transaction)
(:Transaction)-[:PAID {value, vout, is_change}]->(:Address)
```

**Collapsed, for traversal speed:**
```
(:Address)-[:SENT_TO {value, txid, block_time, hops}]->(:Address)
```

The detailed form is correct: Bitcoin transactions genuinely are many-to-many, and a transaction with 3 inputs and 5 outputs does not decompose cleanly into address-to-address pairs, because you cannot know which input paid which output.

The collapsed form is what makes path queries fast, because a six-hop trace through the detailed model is actually twelve hops.

Build both. Use `SENT_TO` for tracing and drop into the detailed model when the user opens a specific transaction. Be ready to explain that `SENT_TO` value is an apportionment, not a fact, because in a multi-input multi-output transaction the true input-to-output mapping is unknowable. That caveat is the kind of thing that marks out someone who has actually thought about it.

### Constraints and indexes

```cypher
CREATE CONSTRAINT address_unique IF NOT EXISTS
FOR (a:Address) REQUIRE a.address IS UNIQUE;

CREATE CONSTRAINT tx_unique IF NOT EXISTS
FOR (t:Transaction) REQUIRE t.txid IS UNIQUE;

CREATE INDEX addr_label IF NOT EXISTS
FOR (a:Address) ON (a.label);

CREATE INDEX sent_time IF NOT EXISTS
FOR ()-[r:SENT_TO]-() ON (r.block_time);
```

Create the uniqueness constraints before loading any data. They also create the backing index, and without them `MERGE` on address does a full scan, which will be catastrophically slow.

### Queries Neo4j is for

Trace outbound flow from a victim address, up to six hops, forward in time only:

```cypher
MATCH path = (start:Address {address: $address})
             -[:SENT_TO*1..6]->(dest:Address)
WHERE ALL(r IN relationships(path) WHERE r.block_time >= $theft_time)
  AND reduce(t = $theft_time, r IN relationships(path) |
             CASE WHEN r.block_time >= t THEN r.block_time ELSE t END) IS NOT NULL
RETURN path
ORDER BY length(path)
LIMIT 200
```

Find where stolen funds reached a known exchange:

```cypher
MATCH path = shortestPath(
    (v:Address {address: $victim})-[:SENT_TO*1..10]->(e:Address)
)
WHERE e.label = 'exchange'
RETURN path, e.address
```

Find clusters, which is Michael's "network rings" point:

```cypher
CALL gds.louvain.stream('address-graph')
YIELD nodeId, communityId
RETURN communityId, count(*) AS size,
       collect(gds.util.asNode(nodeId).address)[0..10] AS sample
ORDER BY size DESC
LIMIT 20
```

The Louvain call needs the Graph Data Science plugin. Available in Neo4j Community, but check the licence terms for the specific GDS version you use, since the licensing has changed across versions.

The time-ordering constraint in the first query matters and is easy to miss. Money cannot flow backwards through time. Without it you will trace paths that are chronologically impossible and produce confident nonsense.

## The bridge between them

The rule from doc 02: ClickHouse holds everything, Neo4j holds the working set.

When someone adds a watch on an address:

1. Insert the `Watch` node in Neo4j
2. Query ClickHouse for all `flows` rows involving that address
3. Expand outward to the configured hop depth, still in ClickHouse
4. Bulk-load that subgraph into Neo4j
5. Register the address, and everything within the hop radius, in the live matcher set
6. From then on, matching transactions are written to Neo4j in real time as they arrive

Step 3 is where you decide the hop depth. Bitcoin fans out fast. Depth 2 might be 500 addresses, depth 4 might be 50,000, depth 6 might be millions. Cap it and cap it by node count, not just by depth. Something like "expand until you hit 10,000 nodes or depth 6, whichever comes first".

This cap is the most important number in the system and you should be able to say why.
