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
import time
import uuid
from dataclasses import dataclass, field

import common
import config
from ch_client import CHClient

RULE_NAME = "watchlist_movement"
SEVERITY = "high"
CHECKPOINT_COMPONENT = "detector"  # unchanged from before the common.py
# extraction -- do not rename; live checkpoint rows already use this value.
NOT_AN_INFERENCE = 0  # see module docstring and docs/06-detection.md


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
        "created_at": common.dt_str(common.now_dt()),
        "acknowledged": 0,
        "invalidated": 0,
    }


def run_once(ch, stats):
    run_started_at = common.now_dt()  # captured before querying -- see
    # module docs on the checkpoint race: the NEXT run's watermark must be
    # THIS run's start time, not its completion time, or a row landing
    # mid-run could be silently skipped forever rather than merely
    # re-scanned once (safe, since (watch_id, txid) dedup makes
    # re-scanning idempotent).

    watches = common.load_watchlist(ch)
    global_watermark = common.read_checkpoint(ch, CHECKPOINT_COMPONENT)

    alert_batch = []
    for watch in watches:
        effective_start = max(global_watermark, watch["created_at"]) if global_watermark else watch["created_at"]
        candidates = common.find_input_side_candidates(ch, watch["address"], effective_start)
        stats.candidates_evaluated += len(candidates)
        if not candidates:
            continue

        already = common.already_alerted(ch, RULE_NAME, watch["watch_id"], list(candidates.keys()))
        for txid, entry in candidates.items():
            if txid in already:
                continue
            if entry["value"] < watch["min_value"]:
                stats.skipped_below_threshold += 1
                continue
            status, block_hash = common.transaction_status(ch, txid)
            alert_batch.append(build_alert(watch, txid, entry, status, block_hash))

    if alert_batch:
        ch.insert_rows("alerts", alert_batch)
        stats.alerts_written += len(alert_batch)

    common.write_checkpoint(ch, CHECKPOINT_COMPONENT, run_started_at)
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
