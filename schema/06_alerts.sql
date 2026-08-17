-- Append-only, with two flags flipped after insert: `acknowledged` by user
-- action, `invalidated` on reorg. Both are rare, targeted changes, not a
-- high-churn update workload, so a plain MergeTree with lightweight
-- ALTER TABLE ... UPDATE mutations is the right fit -- a version column
-- (as in transactions) would be overkill for this access pattern.
--
-- is_shadow: true = recorded, not delivered. Lets a detection rule run
-- silently against live traffic before its false positive rate is known.
--
-- block_hash + invalidated: alerts derived from an orphaned block must be
-- withdrawn. A user told that funds moved must be told if that block was
-- discarded.
USE chainwatch;

CREATE TABLE IF NOT EXISTS alerts
(
    alert_id     UUID,
    watch_id     UUID,
    address      String,
    rule         LowCardinality(String),
    severity     Enum8('low' = 1, 'medium' = 2, 'high' = 3, 'critical' = 4),
    txid         String,
    block_hash   String,           -- for invalidation on reorg
    value        UInt64,           -- satoshis
    detail       String,           -- JSON, includes contributing factors
    confidence   UInt8,            -- 0-100
    is_shadow    UInt8,            -- true = recorded, not delivered
    created_at   DateTime64(3),
    acknowledged UInt8,
    invalidated  UInt8             -- set on reorg
)
ENGINE = MergeTree
ORDER BY (address, created_at, alert_id);
