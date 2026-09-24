-- Drops address_stats_mv, not fixed. schema/09_address_stats_mv_fix.sql
-- corrected the view's block_time reference so it would stop erroring
-- against the redesigned flows -- but address_stats is already inflated
-- by the ~41.38 million duplicate flows rows measured before the
-- redesign, and reattaching a working view would add correct increments
-- on top of wrong totals indefinitely, never converging back to correct.
--
-- Decision: freeze address_stats as a stale snapshot rather than keep it
-- wrong forever. Nothing in detection/ reads it (confirmed by grep).
-- docs/08-build-plan.md records this and why.
--
-- address_stats itself is not dropped and keeps whatever data it holds --
-- this only removes the trigger that feeds it. Verified before running
-- against production: address_stats_mv was created with an explicit
-- `TO address_stats` target, not an implicit inner storage table, so
-- dropping the view cannot delete address_stats's own data.
--
-- Runs after 09_address_stats_mv_fix.sql in file order, so a fresh
-- database bootstrap reaches this same end state -- the view exists
-- briefly during bootstrap (created by 05, fixed by 09) then is dropped
-- here, exactly mirroring what happened to the already-running production
-- instance. Only address_stats_mv is affected; address_stats stays
-- defined so a future redesign has a table to populate, per
-- docs/08-build-plan.md's still-undecided options for it.
USE chainwatch;

DROP TABLE IF EXISTS address_stats_mv;
