-- Redesigns `flows` to fix the duplication defect found investigating why
-- ClickHouse OOM'd searching it (docs/08-build-plan.md, phase 4): a plain
-- MergeTree with no dedup, replayed by repeated confirm.catch_up_to_tip
-- passes over overlapping block ranges. 15,051,201 duplicate keys measured
-- live, 97.95% pure replay (never seen pending at all), 1.46% the
-- legitimate pending+confirmed structural pair, 0.59% a structural pair
-- also hit by replay.
--
-- Runs after 03_flows.sql in file order, so it corrects that table rather
-- than replacing its own definition -- 03_flows.sql is not edited
-- (schema/ is protected; it is applied to a running database with real
-- ingested data behind it on the live instance). On a fresh container
-- (this file's only current use -- clickhouse-regtest, no persistent
-- volume, wiped and reapplied every test run) this simply supersedes
-- 03_flows.sql's definition before any data exists.
USE chainwatch;

DROP TABLE IF EXISTS flows;

-- Three changes from 03_flows.sql, in order of how the investigation found them:
--
-- 1. block_height, block_hash, block_time removed. Confirmed by grepping
--    every consumer (detection/*.py): nothing reads them from `flows` --
--    confirmation status is already fetched exclusively via
--    common.transaction_status() against `transactions FINAL`. These three
--    columns were exactly the ones that differed between a pending capture,
--    a confirmed capture, and repeated replay of the same confirmation --
--    removing them means a flow's remaining columns are stable once
--    written, for every case except #2 below.
--
-- 2. ReplacingMergeTree(seen_at), ORDER BY (address, direction, position,
--    txid) -- not (txid, direction, position). Measured live: a
--    txid-first ordering with a bloom_filter index on address to recover
--    per-address lookups read the ENTIRE table (8,388,564 of 8,388,564
--    rows on a 1/8 slice) -- the bloom filter gave no real pruning,
--    since a given address's rows are scattered pseudo-randomly across
--    txid-ordered granules. Address-first ordering read 360,448 rows for
--    the same query -- about 23x fewer. Every rule 1-3 query filters on
--    an exact address first; losing that pruning would turn every
--    15-second detection poll, for every watch, into a near-full-table
--    scan -- the same shape of query that caused the OOM in the first
--    place, just running continuously instead of once. txid is appended
--    only to make the tuple unique.
--
-- 3. Because address is part of the ORDER BY / dedup identity, it must
--    never change after a flow's first write, or ReplacingMergeTree will
--    never merge the two versions (an input written parent_pending with
--    address='' and later rewritten resolved with its real address would
--    otherwise persist as two permanently-separate rows forever --
--    confirmed to occur in the live data: 44,502 input keys show more
--    than one distinct address or resolution_state). Enforced at the
--    write layer, not here: ingestor/persist.py's Persistence.add() no
--    longer writes a flows row for an input in parent_pending or
--    unresolved state at all -- it waits for resolution, which always
--    arrives at the latest by confirmation (getblock verbosity 3 embeds
--    prevout directly, so confirm.py's resolve_confirmed_input succeeds
--    in every case except the pruned node's undo-data window being
--    exceeded, a genuinely terminal 'unresolved', not a pending state).
--    Proven on regtest: regtest/flows-dedup-test.sh.
--
--    Cost of this, stated plainly: a watched address's own outgoing
--    transaction, if it itself spends a still-unconfirmed parent (a
--    rapid, chained hop -- notably also the shape of an attacker
--    deliberately relaying funds quickly to evade single-hop tracing),
--    is not visible to rule 1 (watchlist_movement, "fires on mempool
--    arrival in intent") until that transaction confirms, not when it
--    enters the mempool. Ordinary movements -- spending an
--    already-confirmed output, the large majority of real traffic --
--    are completely unaffected; resolution still succeeds immediately at
--    mempool time and the flows row is written exactly as before. The
--    alternative (excluding address from the ordering key and only
--    recovering per-address reads via a secondary index) was measured
--    and rejected above.
CREATE TABLE IF NOT EXISTS flows
(
    txid              String,
    direction         Enum8('in' = 1, 'out' = 2),
    position          UInt16,
    address           String,           -- '' if unresolvable (outputs only,
                                         -- post-#3 above -- an input with an
                                         -- empty address is never written)
    value             UInt64,           -- satoshis
    address_type      LowCardinality(String),
    seen_at           DateTime64(3),    -- version column
    is_change         UInt8,            -- heuristic
    change_confidence UInt8,            -- 0-100
    is_dust           UInt8,            -- at or near 546 sat
    resolution_state  Enum8('resolved' = 1, 'parent_pending' = 2, 'unresolved' = 3)
)
ENGINE = ReplacingMergeTree(seen_at)
ORDER BY (address, direction, position, txid);
