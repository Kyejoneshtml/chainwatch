"""Refuses to start against a `flows` table that doesn't match what this
code writes.

Verified directly against the live database, not assumed: an INSERT shaped
exactly like persist.build_flow_rows's output (schema/08_flows_redesign.sql
design -- no block_height/block_hash/block_time) against the OLD
03_flows.sql schema does not fail. ClickHouse's JSONEachRow insert silently
fills the omitted columns with their type's default -- block_height=0,
block_hash='', block_time=1970-01-01 -- which is exactly this project's own
"pending" sentinel (schema/02_transactions.sql, persist.py's EPOCH), for
every row, including fully confirmed transactions. That is silent
corruption, not a crash: the code has no other way to notice the mismatch
on its own, which is why this check exists.

Also refuses to start if any materialized view depends on flows that isn't
explicitly expected here. Found by testing on regtest, not assumed: a
materialized view resolves its source table by name at each push, not by a
fixed reference captured when the view was created -- RENAME TABLE flows TO
flows_old, flows_new TO flows leaves any MV still named as depending on
"flows" pointed at the *new* table, not the renamed-away old one. Confirmed
live against production immediately before address_stats_mv was dropped
(schema/10_drop_address_stats_mv.sql): its stored query still referenced
flows.block_time, so it would have started failing every insert into the
redesigned flows the moment a future rename made it the live "flows" --
the same flush-failure-forever shape already found once this session, this
time against real traffic. EXPECTED_FLOWS_DEPENDENTS is empty because that
MV is now dropped, not fixed -- see docs/08-build-plan.md for why.
"""

# Exactly the columns persist.build_flow_rows produces today. Kept as an
# explicit set here, not derived from the code at import time, so a future
# change to build_flow_rows's shape has to touch this file too -- the
# whole point is a check that doesn't silently drift with the writer.
EXPECTED_FLOWS_COLUMNS = {
    "txid", "direction", "position", "address", "value", "address_type",
    "seen_at", "is_change", "change_confidence", "is_dust", "resolution_state",
}
EXPECTED_FLOWS_ENGINE = "ReplacingMergeTree"

# Materialized views (or anything else) allowed to depend on flows. Empty:
# address_stats_mv, the only one that ever existed, is dropped
# (schema/10_drop_address_stats_mv.sql), not fixed -- see this module's
# docstring. Any future view attached here has to be added explicitly, the
# same discipline EXPECTED_FLOWS_COLUMNS already applies to the writer.
EXPECTED_FLOWS_DEPENDENTS = set()


class SchemaMismatch(Exception):
    pass


def verify_flows_schema(ch):
    rows = ch.select("""
        SELECT engine FROM system.tables
        WHERE database = currentDatabase() AND name = 'flows'
    """)
    if not rows:
        raise SchemaMismatch(
            "flows table does not exist in this database -- has schema/ been applied at all?"
        )
    engine = rows[0]["engine"]
    if engine != EXPECTED_FLOWS_ENGINE:
        raise SchemaMismatch(
            f"flows engine is {engine!r}, this code writes the redesigned schema "
            f"(schema/08_flows_redesign.sql) which expects {EXPECTED_FLOWS_ENGINE!r}. "
            "The production migration has not been applied to this database -- "
            "do not proceed; see docs/08-build-plan.md's flows redesign section."
        )

    col_rows = ch.select("""
        SELECT name FROM system.columns
        WHERE database = currentDatabase() AND table = 'flows'
    """)
    actual = {r["name"] for r in col_rows}
    if actual != EXPECTED_FLOWS_COLUMNS:
        missing = sorted(EXPECTED_FLOWS_COLUMNS - actual)
        extra = sorted(actual - EXPECTED_FLOWS_COLUMNS)
        raise SchemaMismatch(
            f"flows columns do not match what this code writes -- "
            f"missing={missing} extra={extra}. Inserting anyway would silently "
            "succeed with the missing columns defaulted (verified live: "
            "block_height=0, block_hash='', block_time=1970-01-01 on every row, "
            "indistinguishable from this project's own 'pending' sentinel, on "
            "fully confirmed transactions too). Do not proceed."
        )

    dep_rows = ch.select("""
        SELECT dependencies_table FROM system.tables
        WHERE database = currentDatabase() AND name = 'flows'
    """)
    dependents = set(dep_rows[0]["dependencies_table"]) if dep_rows else set()
    unexpected = dependents - EXPECTED_FLOWS_DEPENDENTS
    if unexpected:
        raise SchemaMismatch(
            f"unexpected object(s) depending on flows: {sorted(unexpected)}. "
            "A materialized view resolves its source by name at push time, not "
            "a fixed reference -- if this ever holds a stale view expecting the "
            "old columns (address_stats_mv did, until it was dropped rather "
            "than fixed -- schema/10_drop_address_stats_mv.sql), every insert "
            "into flows would silently succeed at the base table while the "
            "view push fails, and this process would report every flush as "
            "failed and retry forever without ever advancing its checkpoint. "
            "Do not proceed until this is explained and EXPECTED_FLOWS_DEPENDENTS "
            "is updated deliberately."
        )
