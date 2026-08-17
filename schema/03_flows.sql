-- One row per input and per output, flattened. The table that does the
-- work for address-centric queries.
--
-- Ordered by (address, block_time, txid) so "everything this address ever
-- did" reads contiguous disk -- the most common query shape.
USE chainwatch;

CREATE TABLE IF NOT EXISTS flows
(
    txid              String,
    direction         Enum8('in' = 1, 'out' = 2),
    position          UInt16,
    address           String,           -- '' if unresolvable
    value             UInt64,           -- satoshis
    address_type      LowCardinality(String),
    block_height      UInt32,
    block_hash        String,
    block_time        DateTime,
    seen_at           DateTime64(3),
    is_change         UInt8,            -- heuristic
    change_confidence UInt8,            -- 0-100
    is_dust           UInt8,            -- at or near 546 sat
    resolution_state  Enum8('resolved' = 1, 'parent_pending' = 2, 'unresolved' = 3)
)
ENGINE = MergeTree
ORDER BY (address, block_time, txid);
