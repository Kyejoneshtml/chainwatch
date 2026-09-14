"""Rule 1: watchlist movement (docs/06-detection.md).

Funds move from a watched address -- the address appears as a transaction
input (flows.direction = 'in'), i.e. it is spending. Fires on mempool
arrival in intent; in practice this runs as a scheduled poll
(docs/02-architecture.md: detection is deliberately separate from the
ingestor, which must never block on analysis), so "fires on mempool
arrival" describes when in a transaction's life the underlying event is
normally first visible, not a hard requirement that status still read
'pending' at the moment this script happens to run. A transaction that
confirmed between arrival and this poll still fires -- excluding it because
it is no longer literally pending would silently drop a real detection.

Type: observation, not inference (docs/06-detection.md, "Observation rules
vs inference rules"). The watched address either appears as an input or it
does not; there is no heuristic between the chain data and the alert, and
therefore no error rate to compute a confidence figure from. confidence is
stored as 0 -- not a claimed 0% confidence, but the documented sentinel for
"no figure applies," with the reason carried in `detail` rather than left to
a comment. See docs/06-detection.md for why 0 rather than some other magic
number: naive code that averages or ranges over confidence should fail
obviously (a wrong low number), not subtly (a poisoned high one).

Every alert this rule writes has is_shadow = 1. Nothing is delivered.
"""
import argparse
import json
import re
import time
import uuid
from dataclasses import dataclass, field
from datetime import datetime, timezone

import config
from ch_client import CHClient

RULE_NAME = "watchlist_movement"
SEVERITY = "high"
NOT_AN_INFERENCE = 0  # see module docstring and docs/06-detection.md

ALERT_TXID_CHUNK = 1000  # same defensive chunk size as ingestor/confirm.py's
# KNOWN_TXIDS_CHUNK, for the same reason: ClickHouse's max_query_size is a
# hard SQL-parser limit on a single IN (...) clause, independent of table size.

_ADDRESS_RE = re.compile(r"^[a-zA-Z0-9]{20,90}$")  # same shape as
# ingestor/watchlist_cli.py's validator -- duplicated, not imported, for the
# same decoupling reason as ch_client.py and config.py.
_TXID_RE = re.compile(r"^[0-9a-f]{64}$")


def _validated_address(address):
    if not _ADDRESS_RE.match(address):
        raise ValueError(f"'{address}' doesn't look like a Bitcoin address")
    return address


def now_dt():
    return datetime.now(timezone.utc)


def dt_str(dt):
    # Same DateTime64(3) string shape ingestor/persist.py's now_str() uses --
    # a bare JSON float is rejected by ClickHouse's JSONEachRow parser.
    return dt.strftime("%Y-%m-%d %H:%M:%S.%f")[:-3]


def parse_ch_datetime(s):
    # ClickHouse returns DateTime64(3) values as "YYYY-MM-DD HH:MM:SS.mmm"
    # strings under JSONEachRow -- the same format dt_str() produces, so
    # round-tripping through here is exact.
    return datetime.strptime(s, "%Y-%m-%d %H:%M:%S.%f").replace(tzinfo=timezone.utc)


@dataclass
class Stats:
    """Structured shutdown summary, same philosophy as ingestor/main.py's
    Stats -- this is a separate process's own counters, not the ingestor's."""

    started_at: float = field(default_factory=time.monotonic)
    runs: int = 0
    candidates_evaluated: int = 0
    alerts_written: int = 0
    skipped_below_threshold: int = 0
    db_errors: int = 0

    def summary(self):
        return {
            "elapsed_seconds": round(time.monotonic() - self.started_at, 1),
            "runs": self.runs,
            "candidates_evaluated": self.candidates_evaluated,
            "alerts_written": self.alerts_written,
            "skipped_below_threshold": self.skipped_below_threshold,
            "db_errors": self.db_errors,
        }


def load_watchlist(ch):
    rows = ch.select("""
        SELECT address, watch_id, min_value, created_at
        FROM watchlist FINAL
        WHERE active = 1
    """)
    for r in rows:
        r["created_at"] = parse_ch_datetime(r["created_at"])
    return rows


def read_detector_watermark(ch):
    rows = ch.select("""
        SELECT last_run_at FROM checkpoints
        WHERE component = 'detector'
        ORDER BY last_run_at DESC LIMIT 1 BY component
    """)
    return parse_ch_datetime(rows[0]["last_run_at"]) if rows else None


def write_detector_checkpoint(ch, run_started_at):
    # last_block_hash/last_block_height are unused by this component --
    # '' and 0 are the same "not applicable" sentinels the schema already
    # uses elsewhere (e.g. transactions.block_hash while pending).
    ch.insert_rows("checkpoints", [{
        "component": "detector",
        "last_block_hash": "",
        "last_block_height": 0,
        "last_run_at": dt_str(run_started_at),
    }])


def find_candidates(ch, address, since_dt):
    """Transactions where `address` is an input (spending) with a first
    sighting after since_dt. DISTINCT on (txid, position, value) collapses
    the pending-arrival and post-confirmation duplicate flow rows for the
    same input -- same value, different block_height/seen_at, neither of
    which is selected here.
    """
    address = _validated_address(address)
    rows = ch.select(f"""
        SELECT DISTINCT txid, position, value
        FROM flows
        WHERE direction = 'in'
          AND address = '{address}'
          AND seen_at > toDateTime64('{dt_str(since_dt)}', 3)
        ORDER BY txid
    """)
    by_txid = {}
    for r in rows:
        entry = by_txid.setdefault(r["txid"], {"value": 0, "positions": []})
        entry["value"] += int(r["value"])
        entry["positions"].append(r["position"])
    return by_txid


def already_alerted(ch, watch_id, txids):
    """(watch_id, txid) pairs already alerted for this rule -- makes
    reprocessing the same candidates across runs safe."""
    if not txids:
        return set()
    bad = [t for t in txids if not _TXID_RE.match(t)]
    if bad:
        raise ValueError(f"txid did not match expected 64-char hex format: {bad[:3]}")

    seen = set()
    txids = list(txids)
    for i in range(0, len(txids), ALERT_TXID_CHUNK):
        chunk = txids[i:i + ALERT_TXID_CHUNK]
        id_list = ",".join(f"'{t}'" for t in chunk)
        rows = ch.select(f"""
            SELECT DISTINCT txid FROM alerts
            WHERE rule = '{RULE_NAME}' AND watch_id = '{watch_id}' AND txid IN ({id_list})
        """)
        seen.update(r["txid"] for r in rows)
    return seen


def transaction_status(ch, txid):
    if not _TXID_RE.match(txid):
        raise ValueError(f"txid did not match expected 64-char hex format: {txid}")
    rows = ch.select(f"""
        SELECT status, block_hash FROM transactions FINAL WHERE txid = '{txid}'
    """)
    return (rows[0]["status"], rows[0]["block_hash"]) if rows else ("pending", "")


def build_alert(watch, txid, entry, status, block_hash):
    detail = {
        "observation": "watched address is a transaction input (fund source)",
        "matched_positions": entry["positions"],
        "value_from_address_sats": entry["value"],
        "min_value_threshold_sats": watch["min_value"],
        "watch_id": watch["watch_id"],
        "tx_status_at_detection": status,
        "confidence_basis": (
            "observation rule -- no confidence figure applies; "
            "see docs/06-detection.md, 'Observation rules vs inference rules'"
        ),
    }
    return {
        "alert_id": str(uuid.uuid4()),
        "watch_id": watch["watch_id"],
        "address": watch["address"],
        "rule": RULE_NAME,
        "severity": SEVERITY,
        "txid": txid,
        "block_hash": block_hash,
        "value": entry["value"],
        "detail": json.dumps(detail),
        "confidence": NOT_AN_INFERENCE,
        "is_shadow": 1,
        "created_at": dt_str(now_dt()),
        "acknowledged": 0,
        "invalidated": 0,
    }


def run_once(ch, stats):
    run_started_at = now_dt()  # captured before querying -- see module docs
    # on the checkpoint race: the NEXT run's watermark must be THIS run's
    # start time, not its completion time, or a row landing mid-run could
    # be silently skipped forever rather than merely re-scanned once (safe,
    # since (watch_id, txid) dedup makes re-scanning idempotent).

    watches = load_watchlist(ch)
    global_watermark = read_detector_watermark(ch)

    alert_batch = []
    for watch in watches:
        effective_start = max(global_watermark, watch["created_at"]) if global_watermark else watch["created_at"]
        candidates = find_candidates(ch, watch["address"], effective_start)
        stats.candidates_evaluated += len(candidates)
        if not candidates:
            continue

        already = already_alerted(ch, watch["watch_id"], list(candidates.keys()))
        for txid, entry in candidates.items():
            if txid in already:
                continue
            if entry["value"] < watch["min_value"]:
                stats.skipped_below_threshold += 1
                continue
            status, block_hash = transaction_status(ch, txid)
            alert_batch.append(build_alert(watch, txid, entry, status, block_hash))

    if alert_batch:
        ch.insert_rows("alerts", alert_batch)
        stats.alerts_written += len(alert_batch)

    write_detector_checkpoint(ch, run_started_at)
    stats.runs += 1
    print(
        f"[detector] run complete: watches={len(watches)} "
        f"candidates={stats.candidates_evaluated} alerts_written={len(alert_batch)} "
        f"skipped_below_threshold={stats.skipped_below_threshold}"
    )


def main():
    parser = argparse.ArgumentParser(description=f"Detection rule: {RULE_NAME} (shadow mode)")
    parser.add_argument("--once", action="store_true", help="run a single pass and exit")
    args = parser.parse_args()

    ch = CHClient()
    stats = Stats()

    try:
        while True:
            try:
                run_once(ch, stats)
            except Exception as exc:
                stats.db_errors += 1
                print(f"[detector] run failed: {exc}")
            if args.once:
                break
            time.sleep(config.DETECTION_INTERVAL_SECONDS)
    except KeyboardInterrupt:
        pass
    finally:
        print(f"[detector] shutdown: {stats.summary()}")


if __name__ == "__main__":
    main()
