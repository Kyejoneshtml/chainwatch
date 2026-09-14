"""Rule 2: wallet drain (docs/06-detection.md).

Every available UTXO for a watched address consumed in one transaction,
leaving zero or dust, with no change output returning to the sender.
"Available UTXO" is not enumerated as a set anywhere in this code -- see
the balance-based approach below and its stated limitation.

Type: inference, not observation (docs/06-detection.md, "Observation rules
vs inference rules"). The absence of change is the strongest signal and it
is inferred, not read directly off the chain -- it depends on the
one-time-change heuristic's own assumption (change goes to a fresh address
the sender controls), which this code cannot verify or refute without
address clustering (not built; that is Neo4j, phase 5). Confidence is
therefore non-zero, computed once below from the heuristic's published
error rate, and identical on every alert this rule writes -- the
confidence-derivation section is explicit that a figure is computed from
error rates and nothing else, so nothing about a specific transaction
should move it.

THE UTXO-VISIBILITY LIMITATION, stated plainly rather than left inside a
query (docs/06-detection.md, "What this report does not claim"): "every
available UTXO consumed" is checked as "every UTXO this project has itself
observed for this address, via `flows`, consumed" -- not the address's true
on-chain history. A pruned node with no txindex cannot enumerate historical
UTXOs directly (docs/04-ingestion.md), so there is no independent way to
verify that. An address funded before this project started watching it may
hold UTXOs this system has never seen and never will; a transaction that
looks like a full drain against everything WE know about could leave real
money behind in an output outside that window, and nothing here would
reveal the gap. This is at its worst for the exact case this product exists
to serve: a victim who adds a watched address only after a theft has, by
construction, a system that never saw the funds arrive. The one partial
check available -- a negative computed balance -- only catches the opposite
problem (spending more than was ever seen received), not this one.

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

RULE_NAME = "wallet_drain"
SEVERITY = "critical"
CHECKPOINT_COMPONENT = "detector_wallet_drain"  # distinct from rule 1's
# 'detector' -- checkpoints.component is a plain, unconstrained String, but
# reusing rule 1's exact value would let the two rules' watermarks clobber
# each other under `ORDER BY last_run_at DESC LIMIT 1 BY component`.

# Confidence, computed once, in integer basis points -- no floats anywhere.
# docs/06-detection.md assumptions register: one-time-change published error
# rate is 92.66% (9266 basis points out of 10000).
ONE_TIME_CHANGE_ERROR_RATE_BP = 9266
CONFIDENCE_PCT = (10000 - ONE_TIME_CHANGE_ERROR_RATE_BP + 50) // 100  # = 7,
# rounded half-up from 7.34%. Low, and low is correct -- not inflated.


@dataclass
class Stats:
    started_at: float = field(default_factory=time.monotonic)
    runs: int = 0
    candidates_evaluated: int = 0
    alerts_written: int = 0
    skipped_no_meaningful_balance: int = 0
    skipped_residual_remains: int = 0
    skipped_change_detected: int = 0
    skipped_incomplete_history: int = 0
    db_errors: int = 0

    def summary(self):
        return {
            "elapsed_seconds": round(time.monotonic() - self.started_at, 1),
            "runs": self.runs,
            "candidates_evaluated": self.candidates_evaluated,
            "alerts_written": self.alerts_written,
            "skipped_no_meaningful_balance": self.skipped_no_meaningful_balance,
            "skipped_residual_remains": self.skipped_residual_remains,
            "skipped_change_detected": self.skipped_change_detected,
            "skipped_incomplete_history": self.skipped_incomplete_history,
            "db_errors": self.db_errors,
        }


def address_totals(ch, address):
    """Total ever received / ever spent for `address`, deduped at the SQL
    level on (txid, position, value) -- collapses the pending-arrival and
    post-confirmation duplicate flow rows for the same input/output, same
    reasoning as common.find_input_side_candidates. Deliberately unbounded
    by any watch's created_at: this is meant to reflect the address's real
    observed balance, not just movement since it was watched.
    """
    address = common.validated_address(address)
    received = ch.select(f"""
        SELECT sum(v) AS total FROM (
            SELECT DISTINCT txid, position, value AS v FROM flows
            WHERE direction = 'out' AND address = '{address}'
        )
    """)
    spent = ch.select(f"""
        SELECT sum(v) AS total FROM (
            SELECT DISTINCT txid, position, value AS v FROM flows
            WHERE direction = 'in' AND address = '{address}'
        )
    """)
    total_received = int(received[0]["total"]) if received and received[0]["total"] is not None else 0
    total_spent = int(spent[0]["total"]) if spent and spent[0]["total"] is not None else 0
    return total_received, total_spent


def first_seen_for_address(ch, address):
    address = common.validated_address(address)
    rows = ch.select(f"SELECT min(seen_at) AS first_seen FROM flows WHERE address = '{address}'")
    return common.parse_ch_datetime(rows[0]["first_seen"]) if rows and rows[0]["first_seen"] else None


def has_change_to_self(ch, txid, address):
    """Does any output of this transaction pay back to the exact watched
    address? Deliberately narrow -- see module docstring's stated
    limitation on this not covering a fresh change address the same wallet
    also controls, since no address clustering exists in this codebase.
    """
    common.validated_txid(txid)
    address = common.validated_address(address)
    rows = ch.select(f"""
        SELECT count() AS n FROM flows
        WHERE direction = 'out' AND txid = '{txid}' AND address = '{address}'
    """)
    return int(rows[0]["n"]) > 0 if rows else False


def observation_window_seconds(address_first_seen, candidate_first_seen):
    # Whole seconds only -- timedelta.total_seconds() returns a float, so
    # this uses .days/.seconds instead to stay float-free throughout.
    delta = candidate_first_seen - address_first_seen
    return delta.days * 86400 + delta.seconds


def build_alert(watch, txid, entry, status, block_hash, balance_before, balance_after,
                 address_first_seen, has_change):
    detail = {
        "observation": (
            "every balance this project has observed for the watched address consumed "
            "in one transaction, leaving at or below the residual threshold, with no "
            "output returning to the watched address itself"
        ),
        "balance_before_sats": balance_before,
        "balance_after_sats": balance_after,
        "value_from_address_sats": entry["value"],
        "residual_threshold_sats": config.RESIDUAL_THRESHOLD_SATS,
        "require_no_change": config.REQUIRE_NO_CHANGE,
        "has_change_to_self": has_change,
        "watch_id": watch["watch_id"],
        "tx_status_at_detection": status,
        "confidence_basis": (
            f"inference rule -- confidence computed solely from the one-time-change "
            f"heuristic's published error rate (92.66%, docs/06-detection.md assumptions "
            f"register): base confidence = 1 - 0.9266 = 7.34%, rounded to {CONFIDENCE_PCT}. "
            f"Not chosen, not inflated."
        ),
        "no_change_check_limitation": (
            "checks only whether an output pays back to this exact address, not the "
            "sender's wider cluster -- no address clustering exists in this codebase yet. "
            "Legitimate spending that sends change to a fresh address the same wallet "
            "also controls looks identical to a real drain under this check."
        ),
        "utxo_visibility_limitation": (
            "balance computed only from transactions this project has itself observed "
            "for this address, not its full on-chain history -- a pruned node with no "
            "txindex cannot enumerate historical UTXOs directly. See docs/06-detection.md, "
            "'What this report does not claim.'"
        ),
        "address_observed_since": common.dt_str(address_first_seen) if address_first_seen else None,
        "observation_window_seconds": (
            observation_window_seconds(address_first_seen, entry["first_seen"])
            if address_first_seen else None
        ),
        "plausible_innocent_explanation": (
            "wallet migration or a hardware-wallet upgrade produces an identical shape: "
            "moving all funds to a new wallet, with no change expected because none is "
            "being kept back."
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
        "confidence": CONFIDENCE_PCT,
        "is_shadow": 1,
        "created_at": common.dt_str(common.now_dt()),
        "acknowledged": 0,
        "invalidated": 0,
    }


def run_once(ch, stats):
    run_started_at = common.now_dt()  # same checkpoint-race reasoning as
    # watchlist_movement.py: next run's watermark is THIS run's start time.

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
        # Computed once per watch per run, not per candidate: these are
        # address-level aggregates reflecting the CURRENT known balance.
        # If more than one genuine drain candidate landed for the same
        # address in the same run (rare -- drains are rare by definition),
        # each candidate's own "balance before" below would not account for
        # the others' effect within the same batch. Accepted as a stated,
        # minor imprecision rather than engineering a full per-candidate
        # ordering pass for an edge case this unlikely.
        total_received, total_spent = address_totals(ch, watch["address"])
        address_first_seen = first_seen_for_address(ch, watch["address"])
        balance_after = total_received - total_spent

        for txid, entry in candidates.items():
            if txid in already:
                continue

            balance_before = balance_after + entry["value"]
            if balance_after < 0 or balance_before < 0:
                # Spent more than we ever saw received -- our own ingestion
                # history for this address is inconsistent, not a signal of
                # a real drain. Don't fire on a nonsensical number.
                stats.skipped_incomplete_history += 1
                continue
            if balance_before <= config.RESIDUAL_THRESHOLD_SATS:
                # Nothing meaningful was there before this transaction
                # either -- not a drain, just an already-empty address.
                stats.skipped_no_meaningful_balance += 1
                continue
            if balance_after > config.RESIDUAL_THRESHOLD_SATS:
                # Meaningful balance remains -- not a full drain.
                stats.skipped_residual_remains += 1
                continue

            has_change = has_change_to_self(ch, txid, watch["address"]) if config.REQUIRE_NO_CHANGE else False
            if config.REQUIRE_NO_CHANGE and has_change:
                stats.skipped_change_detected += 1
                continue

            status, block_hash = common.transaction_status(ch, txid)
            alert_batch.append(build_alert(
                watch, txid, entry, status, block_hash,
                balance_before, balance_after, address_first_seen, has_change,
            ))

    if alert_batch:
        ch.insert_rows("alerts", alert_batch)
        stats.alerts_written += len(alert_batch)

    common.write_checkpoint(ch, CHECKPOINT_COMPONENT, run_started_at)
    stats.runs += 1
    print(
        f"[detector] run complete: watches={len(watches)} "
        f"candidates={stats.candidates_evaluated} alerts_written={len(alert_batch)} "
        f"skipped(no_balance={stats.skipped_no_meaningful_balance} "
        f"residual_remains={stats.skipped_residual_remains} "
        f"change_detected={stats.skipped_change_detected} "
        f"incomplete_history={stats.skipped_incomplete_history})"
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
