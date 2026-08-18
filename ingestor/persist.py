import time
from datetime import datetime, timezone

FLUSH_ROWS = 1000
FLUSH_SECONDS = 2.0

EPOCH = "1970-01-01 00:00:00"  # sentinel for block_time on unconfirmed rows,
# the same idea as the schema's existing block_height=0 / block_hash=''


def now_str():
    # DateTime64(3) via JSONEachRow needs a quoted string, not a bare JSON
    # float -- verified directly against the running container: the float
    # form that toDateTime64() accepts as a SQL argument is rejected here.
    return datetime.now(timezone.utc).strftime("%Y-%m-%d %H:%M:%S.%f")[:-3]


def build_transaction_row(summary, vsize, seen_at):
    resolved_value = sum(i["value"] for i in summary["inputs"] if i["state"] == "resolved")
    return {
        "txid": summary["txid"],
        "status": "pending",
        "seen_at": seen_at,
        "block_height": 0,
        "block_hash": "",
        "block_time": EPOCH,
        "input_count": len(summary["inputs"]),
        "output_count": len(summary["outputs"]),
        "input_value": resolved_value,  # sum of resolved inputs only -- see
        # README: not the true total unless inputs_pending and
        # inputs_unresolved are both 0
        "output_value": summary["output_value"],
        "fee": summary["fee"] if summary["fee"] is not None else 0,
        "vsize": vsize,
        "is_coinbase": 1 if summary["is_coinbase"] else 0,
        "is_coinjoin": 0,  # no detection logic exists yet (phase 4); 0 means
        # "not evaluated", not "checked and clean"
        "inputs_resolved": summary["resolved"],
        "inputs_pending": summary["parent_pending"],
        "inputs_unresolved": summary["unresolved"],
    }


def build_flow_rows(summary, seen_at):
    rows = []
    for position, inp in enumerate(summary["inputs"]):
        rows.append({
            "txid": summary["txid"],
            "direction": "in",
            "position": position,
            "address": inp["address"] or "",
            "value": inp["value"] if inp["value"] is not None else 0,
            "address_type": inp["script_type"] or "",
            "block_height": 0,
            "block_hash": "",
            "block_time": EPOCH,
            "seen_at": seen_at,
            "is_change": 0,
            "change_confidence": 0,
            "is_dust": 1 if inp["is_dust"] else 0,
            "resolution_state": inp["state"],
        })
    for out in summary["outputs"]:
        rows.append({
            "txid": summary["txid"],
            "direction": "out",
            "position": out["position"],
            "address": out["address"] or "",
            "value": out["value"],
            "address_type": out["script_type"] or "",
            "block_height": 0,
            "block_hash": "",
            "block_time": EPOCH,
            "seen_at": seen_at,
            "is_change": 0,
            "change_confidence": 0,
            "is_dust": 0,  # dust flagging is inputs-only scope (stage 2)
            "resolution_state": "resolved",  # outputs are decoded directly
            # from the transaction body, not looked up -- always fully known
        })
    return rows


class Persistence:
    def __init__(self, ch, stats):
        self.ch = ch
        self.stats = stats
        self.tx_buffer = []
        self.flow_buffer = []
        self.last_flush = time.monotonic()

    def add(self, summary, vsize):
        seen_at = now_str()
        self.tx_buffer.append(build_transaction_row(summary, vsize, seen_at))
        self.flow_buffer.extend(build_flow_rows(summary, seen_at))

    def should_flush(self):
        return (
            len(self.tx_buffer) + len(self.flow_buffer) >= FLUSH_ROWS
            or time.monotonic() - self.last_flush >= FLUSH_SECONDS
        )

    def flush(self):
        if not self.tx_buffer and not self.flow_buffer:
            self.last_flush = time.monotonic()
            return

        n_tx, n_flow = len(self.tx_buffer), len(self.flow_buffer)
        try:
            self.ch.insert_rows("transactions", self.tx_buffer)
            self.ch.insert_rows("flows", self.flow_buffer)
        except Exception as exc:
            self.stats.insert_failures += 1
            # Buffer is kept, not cleared -- a failed flush must not lose
            # data. last_flush still advances so retries follow the normal
            # 2-second cadence instead of hammering every poll tick while
            # ClickHouse is unavailable.
            self.last_flush = time.monotonic()
            print(f"[ch] flush failed, {n_tx} transaction rows and {n_flow} flow rows retained: {exc}")
            return

        self.tx_buffer = []
        self.flow_buffer = []
        self.last_flush = time.monotonic()
        self.stats.rows_written_transactions += n_tx
        self.stats.rows_written_flows += n_flow
        self.stats.batches_flushed += 1
        print(f"[ch] flushed batch: {n_tx} transaction rows, {n_flow} flow rows")

        try:
            self.ch.insert_rows("checkpoints", [{
                "component": "ingestor",
                # Stage 3 does not track confirmed blocks -- that starts in
                # stage 4. Writing the current chain tip here would put a
                # plausible-looking but false value in a field later code
                # reads as "processed up to here", which is exactly the
                # class of silent error docs/04-ingestion.md warns about.
                # Empty/0 is honest; a guessed block position is not.
                "last_block_hash": "",
                "last_block_height": 0,
                "last_run_at": now_str(),
            }])
        except Exception as exc:
            self.stats.insert_failures += 1
            print(f"[ch] checkpoint write failed: {exc}")


def read_checkpoint(ch, component="ingestor"):
    rows = ch.select(f"""
        SELECT last_block_hash, last_block_height, last_run_at
        FROM checkpoints
        WHERE component = '{component}'
        ORDER BY last_run_at DESC
        LIMIT 1 BY component
    """)
    return rows[0] if rows else None


def count_duplicate_transactions(ch):
    # FINAL forces at most one row per ORDER BY key (txid) at read time, by
    # construction, regardless of how many un-merged versions exist on
    # disk. This should therefore always return zero rows; a nonzero result
    # would point to an engine/version behaviour problem, not an ordinary
    # duplicate insert, which FINAL exists specifically to collapse. Kept
    # exactly as docs/05-data-models.md specifies anyway -- it is cheap,
    # and that is exactly the kind of assumption worth verifying rather
    # than asserting.
    rows = ch.select("""
        SELECT txid, count() AS n
        FROM transactions FINAL
        GROUP BY txid
        HAVING n > 1
        LIMIT 10
    """)
    return len(rows)
