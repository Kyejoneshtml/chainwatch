-- Incrementally maintained per-address rollup. AggregatingMergeTree target
-- table plus a materialized view as the insert trigger -- in ClickHouse a
-- materialized view is not a cached query, it fires on every insert into
-- its source table (flows).
USE chainwatch;

CREATE TABLE IF NOT EXISTS address_stats
(
    address        String,
    first_seen     SimpleAggregateFunction(min, DateTime),
    last_seen      SimpleAggregateFunction(max, DateTime),
    total_received SimpleAggregateFunction(sum, UInt64),
    total_sent     SimpleAggregateFunction(sum, UInt64),
    tx_count       SimpleAggregateFunction(sum, UInt64)
)
ENGINE = AggregatingMergeTree
ORDER BY (address);

-- Inference beyond 05-data-models.md: the doc does not mention filtering
-- unresolvable flow rows out of this rollup. `address = ''` marks an
-- unresolvable input/output in `flows`; without this WHERE clause, every
-- such row would be aggregated into a single fake "address" (''), mixing
-- unrelated unresolved flows together and reporting activity for an
-- address that does not exist. Excluding it keeps address_stats meaningful
-- only for real, resolved addresses.
CREATE MATERIALIZED VIEW IF NOT EXISTS address_stats_mv TO address_stats AS
SELECT
    address,
    min(block_time)                 AS first_seen,
    max(block_time)                 AS last_seen,
    sumIf(value, direction = 'out') AS total_received,
    sumIf(value, direction = 'in')  AS total_sent,
    count()                         AS tx_count
FROM flows
WHERE address != ''
GROUP BY address;
