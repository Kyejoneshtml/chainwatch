# 05. Data models

The same fact — "0.5 BTC moved from A to B" — is stored twice, in two shapes, because two kinds of question are asked of it.

---

## ClickHouse

Wide, flat, denormalised, append-only.

### `transactions`

```
txid              String
status            Enum8('pending'=1, 'confirmed'=2, 'orphaned'=3)
seen_at           DateTime64(3)     -- also the version column
block_height      UInt32            -- 0 while pending
block_hash        String            -- '' while pending. REQUIRED for reorg detection
block_time        DateTime
input_count       UInt16
output_count      UInt16
input_value       UInt64            -- satoshis
output_value      UInt64
fee               UInt64
vsize             UInt32
is_coinbase       UInt8
is_coinjoin       UInt8
inputs_resolved   UInt8             -- count fully resolved
inputs_pending    UInt8             -- parent still in mempool, recoverable
inputs_unresolved UInt8             -- genuine gap
```

Engine: `ReplacingMergeTree(seen_at)` ordered by `(txid)`.

**The version column is declared explicitly.** Without one, replacement follows merge order, which is unsafe for update-style workloads. `seen_at` is the version.

**`block_hash` is not optional.** Height is reused across a reorg; the hash is not. Reorg detection compares the stored hash against the block currently at that height. This is how electrs does it.

**Three separate input counts.** Resolution is not binary. Conflating "parent still pending" with "genuinely unresolvable" overstates the coverage problem and hides the real one.

#### ReplacingMergeTree does not deduplicate on insert

This was misunderstood in an earlier version and is a correctness issue.

Deduplication happens during **background merges**, on ClickHouse's schedule. Until a merge runs, both rows coexist and queries return both. Delays range from seconds to hours.

For a system that alerts on state changes, a query returning both `pending` and `confirmed` for one transaction is a correctness failure.

**Any query where status correctness matters uses `FINAL`.** It forces deduplication at read time. It is expensive and disables `PREWHERE` optimisation by default, so it is applied to status queries rather than to all analytics.

**ReplacingMergeTree discards previous versions on merge.** Historical status transitions are not preserved. If an audit trail is ever required, that needs a separate append-only table.

### `flows`

One row per input and per output, flattened. The table that does the work.

```
txid              String
direction         Enum8('in'=1, 'out'=2)
position          UInt16
address           String            -- '' if unresolvable
value             UInt64            -- satoshis
address_type      LowCardinality(String)
block_height      UInt32
block_hash        String
block_time        DateTime
seen_at           DateTime64(3)
is_change         UInt8             -- heuristic
change_confidence UInt8             -- 0-100
is_dust           UInt8             -- at or near 546 sat
resolution_state  Enum8('resolved'=1, 'parent_pending'=2, 'unresolved'=3)
```

Engine: `MergeTree` ordered by `(address, block_time, txid)`.

Ordering by address first means "everything this address ever did" reads contiguous disk. That is the most common query.

### `taint`

New. Supports the FIFO tracing methodology in `14-tracing-adversarial.md`.

```
txid              String
vout              UInt16
source_txid       String            -- the originating tainted output
source_vout       UInt16
tainted_sats      UInt64            -- how many satoshis of this output trace to source
hop_depth         UInt16
computed_at       DateTime64(3)
```

Engine: `MergeTree` ordered by `(source_txid, source_vout, hop_depth)`.

FIFO attaches taint to specific satoshis rather than distributing it proportionally, so an output can carry taint from multiple sources and each is a separate row. This is what makes FIFO lossless and backward-traceable.

Transaction fee handling is the difficult part and is specified in `14-tracing-adversarial.md`.

### `address_stats`

Materialised view, maintained incrementally.

```
address           String
first_seen        SimpleAggregateFunction(min, DateTime)
last_seen         SimpleAggregateFunction(max, DateTime)
total_received    SimpleAggregateFunction(sum, UInt64)
total_sent        SimpleAggregateFunction(sum, UInt64)
tx_count          SimpleAggregateFunction(sum, UInt64)
```

Engine: `AggregatingMergeTree` ordered by `(address)`.

Materialised views in ClickHouse are insert triggers, not cached queries.

### `alerts`

```
alert_id          UUID
watch_id          UUID
address           String
rule              LowCardinality(String)
severity          Enum8('low'=1,'medium'=2,'high'=3,'critical'=4)
txid              String
block_hash        String            -- for invalidation on reorg
value             UInt64
detail            String            -- JSON, includes contributing factors
confidence        UInt8             -- 0-100
is_shadow         UInt8             -- true = recorded, not delivered
created_at        DateTime64(3)
acknowledged      UInt8
invalidated       UInt8             -- set on reorg
```

**`is_shadow`** supports running a rule silently against live traffic before enabling it. See `06-detection.md`.

**`block_hash` and `invalidated`** allow alerts derived from orphaned blocks to be withdrawn. A user told that funds moved must be told if that block was discarded.

### `checkpoints`

```
component         String            -- 'ingestor', 'reconciler', 'detector'
last_block_hash   String
last_block_height UInt32
last_run_at       DateTime64(3)
```

Read on startup so a restart resumes rather than restarting.

### Continuous verification

A duplicate-detection query runs in production and its result appears on the status screen:

```sql
SELECT txid, count() AS n
FROM transactions FINAL
GROUP BY txid
HAVING n > 1
LIMIT 10
```

If this returns rows, the idempotency contract is broken.

### Satoshis as integers

Never floats for monetary amounts, anywhere, including test fixtures. 0.1 + 0.2 does not equal 0.3 in binary floating point.

---

## Neo4j

Narrow, connected, sparse. Watched subgraphs only.

**Provisional.** The BlockSci paper argues an in-memory analytical database is "orders of magnitudes faster than using general-purpose graph databases" for blockchain analysis. That targets whole-chain workloads rather than bounded traversal, but the difference is measured in Phase 5 rather than assumed. If recursive ClickHouse queries are competitive on 6-hop traces, this component is removed.

### Nodes

```
(:Address {
    address: String,        -- unique constraint
    first_seen: DateTime,
    last_seen: DateTime,
    total_received: Long,
    total_sent: Long,
    tx_count: Integer,
    label: String,          -- 'exchange', 'sanctioned', 'victim', null
    risk_score: Float,
    cluster_id: String,
    cluster_confidence: Integer,
    is_supernode: Boolean
})

(:Transaction {
    txid: String,           -- unique constraint
    block_height: Integer,
    block_hash: String,
    block_time: DateTime,
    fee: Long,
    is_coinjoin: Boolean
})

(:Watch {
    watch_id: String,
    address: String,
    created_at: DateTime,
    hop_depth: Integer,
    notify_email: String    -- personal data, see GDPR position
})
```

### Relationships

```
(:Address)-[:FUNDED {value, vin}]->(:Transaction)
(:Transaction)-[:PAID {value, vout, is_change, change_confidence}]->(:Address)
(:Address)-[:SENT_TO {value, txid, block_time, confidence}]->(:Address)
```

The detailed form is correct: Bitcoin transactions are genuinely many-to-many. The collapsed `SENT_TO` form makes traversal fast, at the cost of apportioning value that cannot truly be apportioned without the FIFO computation.

`SENT_TO.confidence` carries that caveat into the data model rather than leaving it in prose.

### Supernodes

A supernode has very high relationship count, typically 100,000 or more. Bitcoin produces them naturally: exchange hot wallets, mining pool payouts, large custodians.

Consequences: traversal through one requires evaluating all its relationships and degrades sharply; `MERGE` locks both endpoints, creating contention on continuously-written addresses; community detection degrades badly; unbounded traversal on dense subgraphs "can literally run for hours."

**Mitigations:**

1. All variable-length patterns are bounded. `*1..6` maximum
2. Supernodes carry `is_supernode` and can be excluded explicitly. Segregating high-degree nodes by label lets queries opt in or out
3. Materialisation caps by node count as well as depth
4. **A supernode at the end of a path is harmless.** The cost is traversing through one. Traces terminating at an exchange are fine, and that is the common case here

### Constraints

```cypher
CREATE CONSTRAINT address_unique IF NOT EXISTS
FOR (a:Address) REQUIRE a.address IS UNIQUE;

CREATE CONSTRAINT tx_unique IF NOT EXISTS
FOR (t:Transaction) REQUIRE t.txid IS UNIQUE;

CREATE INDEX addr_label IF NOT EXISTS FOR (a:Address) ON (a.label);
CREATE INDEX addr_supernode IF NOT EXISTS FOR (a:Address) ON (a.is_supernode);
CREATE INDEX sent_time IF NOT EXISTS FOR ()-[r:SENT_TO]-() ON (r.block_time);
```

Created before any data load. Without the uniqueness constraints, `MERGE` on address does a full scan.

### Queries

Trace outbound, time-ordered, avoiding traversal through supernodes:

```cypher
MATCH path = (start:Address {address: $address})
             -[:SENT_TO*1..6]->(dest:Address)
WHERE ALL(r IN relationships(path) WHERE r.block_time >= $theft_time)
  AND ALL(n IN nodes(path)[1..-1] WHERE NOT n.is_supernode)
RETURN path
ORDER BY length(path)
LIMIT 200
```

The time constraint is easy to omit and produces confident nonsense. Money cannot flow backwards through time.

The supernode exclusion applies to intermediate nodes only, permitting paths that terminate at an exchange.

Shortest path to a labelled exchange:

```cypher
MATCH path = shortestPath(
    (v:Address {address: $victim})-[:SENT_TO*1..10]->(e:Address)
)
WHERE e.label = 'exchange'
RETURN path, e.address
```

---

## The bridge

ClickHouse holds everything, Neo4j holds the working set.

On watch creation:

1. Insert the `Watch` node
2. Query ClickHouse for all `flows` rows involving the address
3. Expand outward to the configured depth, in ClickHouse
4. Bulk-load the subgraph into Neo4j
5. Register the address and its radius in the live matcher
6. Write matching transactions to Neo4j in real time thereafter

Step 3 caps by node count, not only depth. Bitcoin fans out fast: depth 2 might be 500 addresses, depth 6 millions. "Expand until 10,000 nodes or depth 6, whichever first."

That cap is the most important number in the system.
