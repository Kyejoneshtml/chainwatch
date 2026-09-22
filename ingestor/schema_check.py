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
