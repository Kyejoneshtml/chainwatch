"""Shared helpers for detection rules. Extracted from watchlist_movement.py
when wallet_drain.py was added -- both rules live in the same "detection
jobs" component (docs/02-architecture.md) with identical dependencies
(ClickHouse only, no RPC/ZMQ), so sharing code within detection/ carries
none of the coupling risk that kept detection/ and ingestor/ deliberately
separate from each other. Duplicating this logic per-rule would just risk
the two copies drifting.
"""
import re
import time
from datetime import datetime, timezone

ALERT_TXID_CHUNK = 1000  # ClickHouse's max_query_size is a hard SQL-parser
# limit on a single IN (...) clause, independent of table size (see
# ingestor/ch_client.py's _execute for the measured ~100KB failure point) --
# chunking keeps each query safely under it regardless of how many
# candidates a run produces.

_ADDRESS_RE = re.compile(r"^[a-zA-Z0-9]{20,90}$")  # same shape as
# ingestor/watchlist_cli.py's validator -- duplicated there, not imported,
# since ingestor/ and detection/ are the components kept decoupled.
_TXID_RE = re.compile(r"^[0-9a-f]{64}$")


def validated_address(address):
    if not _ADDRESS_RE.match(address):
        raise ValueError(f"'{address}' doesn't look like a Bitcoin address")
    return address


def validated_txid(txid):
    if not _TXID_RE.match(txid):
        raise ValueError(f"txid did not match expected 64-char hex format: {txid}")
    return txid


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


def load_watchlist(ch):
    rows = ch.select("""
        SELECT address, watch_id, min_value, created_at
        FROM watchlist FINAL
        WHERE active = 1
    """)
    for r in rows:
        r["created_at"] = parse_ch_datetime(r["created_at"])
    return rows


def read_checkpoint(ch, component):
    """component is a plain, unconstrained String column -- each rule uses
    its own distinct value (e.g. 'detector' for watchlist_movement,
    'detector_wallet_drain' for wallet_drain) so their watermarks never
    clobber each other under `ORDER BY last_run_at DESC LIMIT 1 BY component`.
    """
    rows = ch.select(f"""
        SELECT last_run_at FROM checkpoints
        WHERE component = '{component}'
        ORDER BY last_run_at DESC LIMIT 1 BY component
    """)
    return parse_ch_datetime(rows[0]["last_run_at"]) if rows else None


def write_checkpoint(ch, component, run_started_at):
    # last_block_hash/last_block_height are unused by detection components --
    # '' and 0 are the same "not applicable" sentinels the schema already
    # uses elsewhere (e.g. transactions.block_hash while pending).
    ch.insert_rows("checkpoints", [{
        "component": component,
        "last_block_hash": "",
        "last_block_height": 0,
        "last_run_at": dt_str(run_started_at),
    }])


def find_input_side_candidates(ch, address, since_dt):
    """Transactions where `address` is an input (spending) with a first
    sighting after since_dt. Each entry also carries "first_seen" -- the
    earliest seen_at across that input's own pending-arrival and
    post-confirmation duplicate flow rows (used by wallet_drain.py's
    observation-window figure; ignored by watchlist_movement.py).

    Deliberately NOT a SQL-level DISTINCT: the pending-arrival and
    post-confirmation duplicate rows for the same (txid, position) share
    value but differ in seen_at, so a DISTINCT across all four columns
    would not collapse them (unlike the plain (txid, position, value)
    DISTINCT this function used before seen_at was needed here too).
    Deduped in Python instead: one entry per (txid, position), value taken
    as-is (must agree across duplicate copies), seen_at as the minimum
    across them (the true first sighting, not a later reprocessing).
    """
    address = validated_address(address)
    rows = ch.select(f"""
        SELECT txid, position, value, seen_at
        FROM flows
        WHERE direction = 'in'
          AND address = '{address}'
          AND seen_at > toDateTime64('{dt_str(since_dt)}', 3)
        ORDER BY txid
    """)
    positions = {}  # (txid, position) -> (value, earliest_seen_at)
    for r in rows:
        key = (r["txid"], r["position"])
        seen = parse_ch_datetime(r["seen_at"])
        value = int(r["value"])
        if key not in positions or seen < positions[key][1]:
            positions[key] = (value, seen)

    by_txid = {}
    for (txid, position), (value, seen) in positions.items():
        entry = by_txid.setdefault(txid, {"value": 0, "positions": [], "first_seen": None})
        entry["value"] += value
        entry["positions"].append(position)
        if entry["first_seen"] is None or seen < entry["first_seen"]:
            entry["first_seen"] = seen
    return by_txid


def find_receiving_txids(ch, address, since_dt):
    """Transactions where `address` received an output (direction='out'),
    with first sighting after since_dt. Returns {txid: first_seen_dt}.

    Deduped in Python, not via a SQL DISTINCT, for the same reason as
    find_input_side_candidates: the pending-arrival and post-confirmation
    duplicate rows for the same output can carry different seen_at, and
    only the earliest matters here. No value/position tracking -- unlike
    find_input_side_candidates, callers of this one (fan_in_consolidation.py)
    only need to know a receiving transaction happened and when it was
    first seen, not how much or at which position.
    """
    address = validated_address(address)
    rows = ch.select(f"""
        SELECT txid, seen_at
        FROM flows
        WHERE direction = 'out'
          AND address = '{address}'
          AND seen_at > toDateTime64('{dt_str(since_dt)}', 3)
    """)
    first_seen = {}
    for r in rows:
        txid = r["txid"]
        seen = parse_ch_datetime(r["seen_at"])
        if txid not in first_seen or seen < first_seen[txid]:
            first_seen[txid] = seen
    return first_seen


def already_alerted(ch, rule, watch_id, txids):
    """(watch_id, txid) pairs already alerted for this specific rule --
    makes reprocessing the same candidates across runs safe."""
    if not txids:
        return set()
    txids = list(txids)
    for t in txids:
        validated_txid(t)

    seen = set()
    for i in range(0, len(txids), ALERT_TXID_CHUNK):
        chunk = txids[i:i + ALERT_TXID_CHUNK]
        id_list = ",".join(f"'{t}'" for t in chunk)
        rows = ch.select(f"""
            SELECT DISTINCT txid FROM alerts
            WHERE rule = '{rule}' AND watch_id = '{watch_id}' AND txid IN ({id_list})
        """)
        seen.update(r["txid"] for r in rows)
    return seen


DEFAULT_CANDIDATE_CAP = 2000  # see config.CANDIDATE_CAP -- bounds one
# run_once() call to at most this many candidates, gathered across every
# watch combined, so one run's work (and one run's failure) is bounded
# instead of processing a potentially unbounded backlog in one shot.
# docs/08-build-plan.md: watchlist_movement's first post-recalculation run
# took 48 minutes processing ~281,000 candidates unbounded, one at a time.

ALERT_INSERT_CHUNK = 500  # never one unbounded INSERT for a run's whole
# alert batch, same "bound the payload size, not just the read side"
# reasoning as ALERT_TXID_CHUNK above.


def cap_candidates(entries, cap):
    """entries: a flat list of tuples whose first element is a seen_at
    datetime, gathered across every watch in the current run -- gather
    first, cap once globally, rather than per watch, so one run_once()
    call's total work is bounded regardless of how many watches
    contributed candidates.

    Sorted by seen_at ascending and cut at `cap`, but EXTENDED through any
    tie at the cutoff seen_at: if the cap falls in the middle of a group of
    candidates sharing the exact same seen_at (DateTime64(3) millisecond
    ties are real under bursty replay/backlog conditions), the whole tied
    group is included rather than split. This is what makes "advance the
    checkpoint to the max seen_at actually processed" safe: the checkpoint
    value can never be shared with a candidate left for next run, so
    nothing between the old and new checkpoint is silently skipped -- err
    toward rescanning, never toward skipping, since (watch_id, txid) dedup
    already makes rescanning idempotent.

    Returns (batch, batch_max_seen_at). batch_max_seen_at is None only when
    entries is empty -- callers should not advance the checkpoint in that
    case (nothing was observed to advance it to).
    """
    if not entries:
        return [], None
    ordered = sorted(entries, key=lambda e: e[0])
    if len(ordered) <= cap:
        return ordered, ordered[-1][0]
    cutoff = ordered[cap - 1][0]
    end = cap
    while end < len(ordered) and ordered[end][0] == cutoff:
        end += 1
    batch = ordered[:end]
    return batch, batch[-1][0]


def transaction_statuses(ch, txids):
    """Batched form of transaction_status: one query per ALERT_TXID_CHUNK
    txids instead of one round trip per candidate -- the single biggest
    cost driver behind watchlist_movement's 48-minute run
    (docs/08-build-plan.md): 421,225 individual calls project-wide during
    that window, ~3.85ms DB time each but a full serial HTTP round trip per
    call, unbatched. `ORDER BY seen_at DESC LIMIT 1 BY txid` is the batched
    form of transaction_status's own per-txid `ORDER BY seen_at DESC LIMIT
    1` -- LIMIT n BY, not FINAL, same reasoning as transaction_status
    itself, just grouped.

    Returns {txid: (status, block_hash)}; a txid with no `transactions`
    row at all is ("pending", ""), matching transaction_status's own
    default for that case.
    """
    if not txids:
        return {}
    txids = list(dict.fromkeys(txids))  # de-dup, preserve order -- the
    # same txid can appear twice in one run (two different watches, same
    # transaction touching both as an input), and status doesn't depend on
    # which watch is asking.
    for t in txids:
        validated_txid(t)
    result = {}
    for i in range(0, len(txids), ALERT_TXID_CHUNK):
        chunk = txids[i:i + ALERT_TXID_CHUNK]
        id_list = ",".join(f"'{t}'" for t in chunk)
        rows = ch.select(f"""
            SELECT txid, status, block_hash FROM transactions
            WHERE txid IN ({id_list})
            ORDER BY seen_at DESC
            LIMIT 1 BY txid
        """)
        for r in rows:
            result[r["txid"]] = (r["status"], r["block_hash"])
    for t in txids:
        result.setdefault(t, ("pending", ""))
    return result


def insert_alerts_chunked(ch, alerts):
    """Never one unbounded INSERT for a run's whole alert batch -- chunks
    of ALERT_INSERT_CHUNK rows regardless of how many alerts one capped
    candidate batch produces."""
    for i in range(0, len(alerts), ALERT_INSERT_CHUNK):
        ch.insert_rows("alerts", alerts[i:i + ALERT_INSERT_CHUNK])

