-- Fixes address_stats_mv, broken by 08_flows_redesign.sql removing
-- flows.block_time. Discovered running regtest/flows-dedup-test.sh: every
-- single insert into flows failed with "Unknown expression or function
-- identifier `block_time`... while pushing to view
-- chainwatch.address_stats_mv" -- not a cosmetic issue, a hard block on
-- the ingestor ever flushing cleanly once 08 is applied. Runs after
-- 08_flows_redesign.sql in file order.
--
-- Minimal fix only: first_seen/last_seen now come from flows.seen_at
-- (still present) instead of the removed block_time. This does NOT fix
-- address_stats's separate, pre-existing correctness gap -- it is still a
-- raw sum()/count() with no deduplication, and materialized views compute
-- against each insert batch before any merge or FINAL ever runs, so no
-- storage-engine change to flows can reach it (docs/08-build-plan.md's
-- flows redesign section covers this). That remains explicitly separate,
-- undecided follow-on work.
USE chainwatch;

DROP TABLE IF EXISTS address_stats_mv;
DROP TABLE IF EXISTS address_stats;

CREATE TABLE IF NOT EXISTS address_stats
(
    address        String,
    first_seen     SimpleAggregateFunction(min, DateTime64(3)),
    last_seen      SimpleAggregateFunction(max, DateTime64(3)),
    total_received SimpleAggregateFunction(sum, UInt64),
    total_sent     SimpleAggregateFunction(sum, UInt64),
    tx_count       SimpleAggregateFunction(sum, UInt64)
)
ENGINE = AggregatingMergeTree
ORDER BY (address);

CREATE MATERIALIZED VIEW IF NOT EXISTS address_stats_mv TO address_stats AS
SELECT
    address,
    min(seen_at)                    AS first_seen,
    max(seen_at)                    AS last_seen,
    sumIf(value, direction = 'out') AS total_received,
    sumIf(value, direction = 'in')  AS total_sent,
    count()                         AS tx_count
FROM flows
WHERE address != ''
GROUP BY address;
