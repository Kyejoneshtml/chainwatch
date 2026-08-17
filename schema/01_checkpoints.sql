-- Restart position for ingestor, reconciler and detector. Read on startup.
--
-- Plain MergeTree, not ReplacingMergeTree. Deduplication on a Replacing
-- engine happens during background merges on ClickHouse's own schedule, so
-- between merges both the old and new row for a component are visible to a
-- query. That is unacceptable at startup, which is precisely when an
-- unambiguous answer is required. `LIMIT 1 BY component` on the read side
-- is deterministic regardless of merge state; FINAL would be correct too
-- but at read cost, and it disables PREWHERE.
--
-- Read pattern:
--   SELECT * FROM checkpoints ORDER BY last_run_at DESC LIMIT 1 BY component
--
-- CLICKHOUSE_DB creates the database but the docker-entrypoint-initdb.d
-- runner does not pass --database, so each file must select it explicitly.
USE chainwatch;

CREATE TABLE IF NOT EXISTS checkpoints
(
    component         String,           -- 'ingestor', 'reconciler', 'detector'
    last_block_hash   String,
    last_block_height UInt32,
    last_run_at       DateTime64(3)
)
ENGINE = MergeTree
ORDER BY (component, last_run_at);
