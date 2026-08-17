-- One row per transaction, per status transition. seen_at is the version
-- column, declared explicitly: without one, ReplacingMergeTree replacement
-- follows merge order, which is unsafe for update-style workloads.
--
-- ReplacingMergeTree does not deduplicate on insert. Deduplication happens
-- during background merges, on ClickHouse's schedule, and delays range from
-- seconds to hours. Any query where status correctness matters (i.e. most
-- queries against this table) must use FINAL.
--
-- block_hash is not optional: '' while pending, populated once confirmed.
-- Height is reused across a reorg; the hash is not, and reorg detection
-- compares the stored hash against the block currently at that height.
--
-- Resolution is three-way, not binary: inputs_resolved (fully resolved),
-- inputs_pending (parent still in mempool, recoverable), inputs_unresolved
-- (genuine gap). Conflating the last two overstates the coverage problem.
USE chainwatch;

CREATE TABLE IF NOT EXISTS transactions
(
    txid              String,
    status            Enum8('pending' = 1, 'confirmed' = 2, 'orphaned' = 3),
    seen_at           DateTime64(3),    -- version column
    block_height      UInt32,           -- 0 while pending
    block_hash        String,           -- '' while pending. required for reorg detection
    block_time        DateTime,
    input_count       UInt16,
    output_count      UInt16,
    input_value       UInt64,           -- satoshis
    output_value      UInt64,           -- satoshis
    fee               UInt64,           -- satoshis
    vsize             UInt32,
    is_coinbase       UInt8,
    is_coinjoin       UInt8,
    inputs_resolved   UInt8,
    inputs_pending    UInt8,
    inputs_unresolved UInt8
)
ENGINE = ReplacingMergeTree(seen_at)
ORDER BY (txid);
