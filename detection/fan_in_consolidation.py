"""Rule 3: fan-in consolidation (docs/06-detection.md).

Many addresses paying one, within a window: the watched address receives
from at least min_sources distinct source addresses inside a trailing
window ending at each new receiving transaction.

Type: inference, not observation (docs/06-detection.md, "Observation rules
vs inference rules"). Confidence leans on common-input-ownership -- not
because the transactions that fund the watched address are assumed to
share a common input owner, but because distinguishing "many genuinely
unrelated depositors" from "one entity's own several addresses, secretly
clustered, consolidating its own funds" is exactly the question that
heuristic addresses and cannot resolve reliably. Computed once, in integer
basis points, from that heuristic's published error rate (63.46%), and
identical on every alert this rule writes.

Fires on every qualifying arrival, not just the first crossing of
min_sources within a burst. Suppressing repeat fires within one ongoing
burst as "the same event already reported" is exactly the kind of
judgment a suppression list makes -- not built yet, deliberately (see
below) -- so it is not baked into this query as an unstated threshold
tweak.

NOT BUILDING SUPPRESSION YET -- there is no data to populate it with.
Instead, every alert's `detail` carries the full source-address set, the
contributing transaction ids, and a `source_set_fingerprint` (a hash of
the sorted source list) so a future reviewer -- or a future suppression-
list-building query -- can group alerts by recurring source sets (an
exchange's batch of depositors, a mining pool's payout run) without
re-deriving the set from scratch each time. That is the concrete
difference between building the list now and making it buildable later.

THE WINDOW LIMITATION, stated where it belongs rather than only inside a
query (docs/06-detection.md, "What this report does not claim"): the
window's lower edge is bounded by watch.created_at, the same floor rules
1 and 2 already use, so a watch less than one window-length old sees a
proportionally truncated window, not a full one. This closes on its own
once the watch has run longer than the window -- unlike rule 2's holdings-
visibility gap, which never closes -- but during that early period this
rule is structurally weaker than it will shortly become, which is exactly
when a newly-added watch (a victim who just discovered a theft) is most
likely to need it working at full strength. Every alert's `detail` carries
`window_seconds_used` alongside the configured value for this reason.

Every alert this rule writes has is_shadow = 1. Nothing is delivered.
"""
import argparse
import hashlib
import json
import time
import uuid
from dataclasses import dataclass, field
from datetime import timedelta

import common
import config
from ch_client import CHClient

RULE_NAME = "fan_in_consolidation"
SEVERITY = "medium"
CHECKPOINT_COMPONENT = "detector_fan_in_consolidation"  # distinct from
# rule 1's 'detector' and rule 2's 'detector_wallet_drain' -- see those
# modules for why a shared value would clobber watermarks across rules.

# Confidence, computed once, in integer basis points -- no floats anywhere.
# docs/06-detection.md assumptions register: common-input-ownership
# published error rate is 63.46% (6346 basis points out of 10000).
COMMON_INPUT_OWNERSHIP_ERROR_RATE_BP = 6346
CONFIDENCE_PCT = (10000 - COMMON_INPUT_OWNERSHIP_ERROR_RATE_BP + 50) // 100  # = 37,
# rounded half-up from 36.54%. Not chosen, not inflated.


@dataclass
class Stats:
    started_at: float = field(default_factory=time.monotonic)
    runs: int = 0
    candidates_evaluated: int = 0
    alerts_written: int = 0
    skipped_below_min_sources: int = 0
    db_errors: int = 0

    def summary(self):
        return {
            "elapsed_seconds": round(time.monotonic() - self.started_at, 1),
            "runs": self.runs,
            "candidates_evaluated": self.candidates_evaluated,
            "alerts_written": self.alerts_written,
            "skipped_below_min_sources": self.skipped_below_min_sources,
            "db_errors": self.db_errors,
        }


def sources_within_window(ch, address, window_start, window_end):
    """Every distinct source address (flows.direction='in') across every
    transaction where `address` received something (direction='out')
    within [window_start, window_end]. Returns (sorted source addresses,
    the receiving txids they came through).
    """
    address = common.validated_address(address)
    receiving_rows = ch.select(f"""
        SELECT DISTINCT txid FROM flows
        WHERE direction = 'out' AND address = '{address}'
          AND seen_at BETWEEN toDateTime64('{common.dt_str(window_start)}', 3)
                          AND toDateTime64('{common.dt_str(window_end)}', 3)
    """)
    receiving_txids = [r["txid"] for r in receiving_rows]
    if not receiving_txids:
        return [], []

    sources = set()
    for i in range(0, len(receiving_txids), common.ALERT_TXID_CHUNK):
        chunk = receiving_txids[i:i + common.ALERT_TXID_CHUNK]
        id_list = ",".join(f"'{common.validated_txid(t)}'" for t in chunk)
        rows = ch.select(f"""
            SELECT DISTINCT address FROM flows
            WHERE direction = 'in' AND address != '' AND txid IN ({id_list})
        """)
        sources.update(r["address"] for r in rows)
    return sorted(sources), receiving_txids


def window_value_received(ch, address, receiving_txids):
    """Total value the watched address received across receiving_txids,
    deduped at the SQL level on (txid, position, value) -- same reasoning
    as wallet_drain.py's address_totals, collapsing the pending-arrival and
    post-confirmation duplicate rows for the same output.
    """
    if not receiving_txids:
        return 0
    address = common.validated_address(address)
    total = 0
    for i in range(0, len(receiving_txids), common.ALERT_TXID_CHUNK):
        chunk = receiving_txids[i:i + common.ALERT_TXID_CHUNK]
        id_list = ",".join(f"'{common.validated_txid(t)}'" for t in chunk)
        rows = ch.select(f"""
            SELECT sum(v) AS total FROM (
                SELECT DISTINCT txid, position, value AS v FROM flows
                WHERE direction = 'out' AND address = '{address}' AND txid IN ({id_list})
            )
        """)
        if rows and rows[0]["total"] is not None:
            total += int(rows[0]["total"])
    return total


def seconds_between(earlier_dt, later_dt):
    # Whole seconds only -- timedelta.total_seconds() returns a float.
    delta = later_dt - earlier_dt
    return delta.days * 86400 + delta.seconds


def source_set_fingerprint(sources):
    return hashlib.sha256(",".join(sources).encode()).hexdigest()


def build_alert(watch, txid, sources, receiving_txids, status, block_hash,
                 window_start, window_end, window_seconds_used, value_received):
    detail = {
        "observation": (
            f"at least {config.FAN_IN_MIN_SOURCES} distinct addresses paid the watched "
            f"address within the configured window"
        ),
        "min_sources_threshold": config.FAN_IN_MIN_SOURCES,
        "source_count": len(sources),
        "source_addresses": sources[:200],
        "source_addresses_truncated": len(sources) > 200,
        "receiving_txids": receiving_txids[:200],
        "receiving_txids_truncated": len(receiving_txids) > 200,
        "source_set_fingerprint": source_set_fingerprint(sources),
        "value_received_in_window_sats": value_received,
        "window_seconds_configured": config.FAN_IN_WINDOW_SECONDS,
        "window_seconds_used": window_seconds_used,
        "window_start": common.dt_str(window_start),
        "window_end": common.dt_str(window_end),
        "watch_id": watch["watch_id"],
        "tx_status_at_detection": status,
        "confidence_basis": (
            f"inference rule -- confidence computed solely from the common-input-ownership "
            f"heuristic's published error rate (63.46%, docs/06-detection.md assumptions "
            f"register): base confidence = 1 - 0.6346 = 36.54%, rounded to {CONFIDENCE_PCT}. "
            f"Not chosen, not inflated."
        ),
        "suppression_note": (
            "no suppression list exists yet -- exchange deposit addresses, payment "
            "processors and mining pool payouts produce this same shape and are expected "
            "to fire this rule constantly (docs/06-detection.md, 'Suppression'). "
            "source_set_fingerprint is provided so recurring source groups can be "
            "identified for a future suppression list, not built here."
        ),
        "window_truncation_note": (
            "window_seconds_used is less than window_seconds_configured when the watch "
            "is younger than the configured window -- see docs/06-detection.md, 'What "
            "this report does not claim'."
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
        "value": value_received,
        "detail": json.dumps(detail),
        "confidence": CONFIDENCE_PCT,
        "is_shadow": 1,
        "created_at": common.dt_str(common.now_dt()),
        "acknowledged": 0,
        "invalidated": 0,
    }


def run_once(ch, stats):
    run_started_at = common.now_dt()  # same checkpoint-race reasoning as
    # the other two rules: next run's watermark is THIS run's start time.

    watches = common.load_watchlist(ch)
    global_watermark = common.read_checkpoint(ch, CHECKPOINT_COMPONENT)

    alert_batch = []
    for watch in watches:
        effective_start = max(global_watermark, watch["created_at"]) if global_watermark else watch["created_at"]
        candidates = common.find_receiving_txids(ch, watch["address"], effective_start)
        stats.candidates_evaluated += len(candidates)
        if not candidates:
            continue

        already = common.already_alerted(ch, RULE_NAME, watch["watch_id"], list(candidates.keys()))
        for txid, first_seen in candidates.items():
            if txid in already:
                continue

            window_start = max(
                first_seen - timedelta(seconds=config.FAN_IN_WINDOW_SECONDS),
                watch["created_at"],
            )
            window_seconds_used = seconds_between(window_start, first_seen)

            sources, receiving_txids = sources_within_window(ch, watch["address"], window_start, first_seen)
            if len(sources) < config.FAN_IN_MIN_SOURCES:
                stats.skipped_below_min_sources += 1
                continue

            status, block_hash = common.transaction_status(ch, txid)
            value_received = window_value_received(ch, watch["address"], receiving_txids)
            alert_batch.append(build_alert(
                watch, txid, sources, receiving_txids, status, block_hash,
                window_start, first_seen, window_seconds_used, value_received,
            ))

    if alert_batch:
        ch.insert_rows("alerts", alert_batch)
        stats.alerts_written += len(alert_batch)

    common.write_checkpoint(ch, CHECKPOINT_COMPONENT, run_started_at)
    stats.runs += 1
    print(
        f"[detector] run complete: watches={len(watches)} "
        f"candidates={stats.candidates_evaluated} alerts_written={len(alert_batch)} "
        f"skipped_below_min_sources={stats.skipped_below_min_sources}"
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
