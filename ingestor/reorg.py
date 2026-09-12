import re

import confirm
from persist import EPOCH, now_str

REORG_CHECK_SECONDS = 15.0  # periodic hash-comparison cadence. The ZMQ
# sequence 'D' (block disconnected) event triggers the same check
# immediately for faster detection -- this timer is the fallback, since
# docs/04-ingestion.md is explicit that ZMQ "does not guarantee you're not
# missing anything."

_HASH_RE = re.compile(r"^[0-9a-f]{64}$")


class ReorgExceedsWindow(Exception):
    """Every height this ingestor has tracked since its last restart
    mismatched the node's current view. The true fork point is below what's
    in memory -- rolling back to a guessed height risks reverting or
    reprocessing the wrong range, so this is raised rather than acted on.
    """

    def __init__(self, orphaned):
        self.orphaned = orphaned
        super().__init__(
            f"reorg deeper than the tracked window ({len(orphaned)} heights "
            "checked, all mismatched) -- fork point unknown, not rolling "
            "back automatically"
        )


def find_divergence(rpc, recent_confirmed):
    """Compare recorded (height, hash) pairs -- tip first -- against the
    node's current view. Height is never trusted alone (docs/04-ingestion.md):
    every comparison is height AND its recorded hash together.

    Returns None if nothing has changed, or (fork_height, fork_hash,
    orphaned) where fork_height/fork_hash is the highest still-matching
    entry and orphaned is the mismatched entries, highest height first --
    the order rollback reverts in.
    """
    ordered = sorted(recent_confirmed, key=lambda pair: pair[0], reverse=True)
    orphaned = []
    for height, recorded_hash in ordered:
        current_hash = rpc.getblockhash(height)
        if current_hash == recorded_hash:
            return (height, current_hash, orphaned) if orphaned else None
        orphaned.append((height, recorded_hash))

    if orphaned:
        raise ReorgExceedsWindow(orphaned)
    return None


def _validated(values):
    bad = [v for v in values if not _HASH_RE.match(v)]
    if bad:
        raise ValueError(f"expected 64-char hex hash/txid, got: {bad[:3]}")
    return values


def _revert_transactions(ch, persistence, stats, orphaned_hashes):
    """Revert every confirmed row whose block_hash is no longer canonical.
    Non-coinbase transactions go back to 'pending' -- they usually return to
    the mempool (regtest/scenarios.sh's reorg-with-transactions proves this).
    Coinbase transactions go to 'orphaned': a coinbase output only ever
    exists inside the block that creates it, so it cannot return to the
    mempool and will not be reprocessed -- 'pending' would misrepresent it.

    Reverted in reverse order of position on the orphaned chain (highest
    block first), mirroring how the rows themselves are identified.

    Only the `transactions` table is touched. `flows` has no status column
    and is already append-only across the pending -> confirmed transition
    (old rows are never rewritten); reorg rollback follows that same
    established pattern rather than inventing revert semantics for a table
    that doesn't model "current state" at all.
    """
    if not orphaned_hashes:
        return []
    hash_list = ",".join(f"'{h}'" for h in _validated(orphaned_hashes))
    rows = ch.select(f"""
        SELECT * FROM transactions FINAL
        WHERE status = 'confirmed' AND block_hash IN ({hash_list})
        ORDER BY block_height DESC
    """)
    reverted_txids = []
    for row in rows:
        _validated([row["txid"], row["block_hash"]])
        new_row = dict(row)
        new_row.update(
            status="orphaned" if row["is_coinbase"] else "pending",
            block_height=0,
            block_hash="",
            block_time=EPOCH,
            seen_at=now_str(),
        )
        persistence.revert_transaction(new_row)
        reverted_txids.append(row["txid"])
        stats.tx_reverted += 1
    return reverted_txids


def _invalidate_alerts(ch, orphaned_hashes):
    """Queue invalidation for alerts derived from orphaned blocks. Returns
    the number of alerts targeted (matched before the mutation was issued).

    ALTER TABLE ... UPDATE is an async mutation in ClickHouse -- queuing it
    is fast, applying it is not guaranteed to be immediate. Not waited on
    here: docs/04-ingestion.md's constraint is that the ingestor never
    blocks, and a synchronous wait on a ClickHouse mutation inside the main
    loop is exactly the kind of unbounded wait that constraint rules out.
    A caller needing to observe completion polls the table, the same way
    regtest/ingestor-rollback-test.sh does.

    Requires ALTER UPDATE on chainwatch.alerts -- see
    schema/ingestor-user.sql.example.
    """
    if not orphaned_hashes:
        return 0
    hash_list = ",".join(f"'{h}'" for h in _validated(orphaned_hashes))
    before = ch.select(f"""
        SELECT count() AS n FROM alerts
        WHERE block_hash IN ({hash_list}) AND invalidated = 0
    """)[0]["n"]
    if before == 0:
        return 0
    ch.execute(f"ALTER TABLE alerts UPDATE invalidated = 1 WHERE block_hash IN ({hash_list})")
    return before


def check_and_handle(rpc, ch, persistence, stats):
    """Entry point for both triggers: the periodic timer in main.py's loop,
    and the ZMQ sequence 'D' event. Detects, rolls back, and reprocesses --
    the whole of docs/04-ingestion.md's five rollback steps.
    """
    try:
        result = find_divergence(rpc, persistence.recent_confirmed)
    except ReorgExceedsWindow as exc:
        stats.reorg_check_failures += 1
        print(f"[reorg] CRITICAL: {exc}")
        return

    if result is None:
        return

    fork_height, fork_hash, orphaned = result
    orphaned_heights = [h for h, _ in orphaned]
    orphaned_hashes = [h for _, h in orphaned]

    print(
        f"[reorg] DETECTED: fork_height={fork_height} fork_hash={fork_hash} "
        f"orphaned_heights={orphaned_heights}"
    )

    reverted_txids = _revert_transactions(ch, persistence, stats, orphaned_hashes)
    invalidated = _invalidate_alerts(ch, orphaned_hashes)
    stats.alerts_invalidated += invalidated
    stats.reorgs_detected += 1

    # Rewind the checkpoint and the in-memory history to the last known-good
    # block. fork_height/fork_hash is already present in recent_confirmed
    # (it's the matching entry find_divergence stopped on), so this is a
    # rewind, not a fresh confirmation -- mark_block_confirmed is not used
    # here, to avoid re-appending a duplicate entry for the same height.
    persistence.rewind_to(fork_height, fork_hash)
    persistence.flush()  # durability before reprocessing: the reverted
    # rows and the rewound checkpoint must land first

    print(
        f"[reorg] rolled back {len(reverted_txids)} transaction(s), "
        f"invalidation requested for {invalidated} alert(s), "
        f"resuming from height={fork_height}"
    )

    try:
        confirm.catch_up_to_tip(rpc, ch, persistence, stats)
    except Exception as exc:
        stats.rpc_failures += 1
        print(f"[reorg] reprocessing after rollback failed: {exc}")
