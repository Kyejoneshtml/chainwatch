-- Watched addresses the in-memory matcher (ingestor/watchlist.py) checks
-- every transaction against (docs/02-architecture.md, docs/06-detection.md
-- rule 1). New in phase 4a. Additive: no existing table is touched.
--
-- ReplacingMergeTree keyed by address, not a generated id, with an explicit
-- version column -- the same pattern `transactions` uses for status
-- transitions. "Removing" a watch means inserting a new row for the same
-- address with active=0, never deleting or mutating in place, so the CLI
-- needs only INSERT (already granted to `ingestor` via chainwatch.*, no
-- new grant). Keying on address means a FINAL read always yields exactly
-- one row per address, with no separate "latest per address" logic needed.
--
-- FINAL is required on any read where current state matters -- same reason
-- as `transactions`.
USE chainwatch;

CREATE TABLE IF NOT EXISTS watchlist
(
    address       String,
    watch_id      UUID,             -- fresh UUID each time a watch is (re)added;
                                     -- referenced by alerts.watch_id once phase 4b writes alerts
    created_at    DateTime64(3),
    updated_at    DateTime64(3),    -- version column
    min_value     UInt64,           -- satoshis; 0 = any movement. Not enforced
                                     -- by the matcher itself -- that's rule 1's
                                     -- job in phase 4b. Stored here so it
                                     -- exists when that rule is built.
    trace_depth   UInt8,            -- hop depth for later graph expansion
                                     -- (phase 5); unused by the matcher itself
    active        UInt8
)
ENGINE = ReplacingMergeTree(updated_at)
ORDER BY (address);
