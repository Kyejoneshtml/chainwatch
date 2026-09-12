import time
from dataclasses import dataclass, field

import config
import confirm
import decode
import persist
import reorg
import zmq_listener
from ch_client import CHClient
from rpc import RPCClient

LABELS = {
    "C": "block connected",
    "D": "block disconnected",
    "R": "removed from mempool",
    "A": "added to mempool",
}


@dataclass
class Stats:
    """Structured shutdown summary -- the start of docs/04-ingestion.md's metrics discipline, not just a goodbye message."""

    started_at: float = field(default_factory=time.monotonic)
    fetched: int = 0
    rpc_failures: int = 0
    resolved: int = 0
    parent_pending: int = 0
    unresolved: int = 0
    rows_written_transactions: int = 0
    rows_written_flows: int = 0
    batches_flushed: int = 0
    insert_failures: int = 0
    duplicate_count: int = 0
    blocks_processed: int = 0
    tx_confirmed: int = 0
    tx_confirmed_new: int = 0  # confirmed but never seen pending -- a signal
    # about how much the mempool subscriber is missing, not a coverage bug
    max_block_seconds: float = 0.0
    reorgs_detected: int = 0
    tx_reverted: int = 0
    alerts_invalidated: int = 0
    reorg_check_failures: int = 0  # includes ReorgExceedsWindow -- a genuine
    # emergency, not routine failure, but counted here so it's never silent

    def summary(self):
        # coverage_rate is what docs/08-build-plan.md's 95% target measures:
        # 1 - (genuine gaps / total). parent_pending is a correct
        # classification, not a miss -- it resolves once its parent
        # confirms -- so it belongs in pending_rate, not the failure count.
        total_inputs = self.resolved + self.parent_pending + self.unresolved
        coverage_rate = round(1 - (self.unresolved / total_inputs), 4) if total_inputs else None
        pending_rate = round(self.parent_pending / total_inputs, 4) if total_inputs else None
        return {
            "elapsed_seconds": round(time.monotonic() - self.started_at, 1),
            "fetched": self.fetched,
            "rpc_failures": self.rpc_failures,
            "resolved": self.resolved,
            "parent_pending": self.parent_pending,
            "unresolved": self.unresolved,
            "coverage_rate": coverage_rate,
            "pending_rate": pending_rate,
            "rows_written_transactions": self.rows_written_transactions,
            "rows_written_flows": self.rows_written_flows,
            "batches_flushed": self.batches_flushed,
            "insert_failures": self.insert_failures,
            "duplicate_count": self.duplicate_count,
            "blocks_processed": self.blocks_processed,
            "tx_confirmed": self.tx_confirmed,
            "tx_confirmed_new": self.tx_confirmed_new,
            "max_block_seconds": round(self.max_block_seconds, 2),
            "reorgs_detected": self.reorgs_detected,
            "tx_reverted": self.tx_reverted,
            "alerts_invalidated": self.alerts_invalidated,
            "reorg_check_failures": self.reorg_check_failures,
        }


def txid_from_sequence(payload):
    # sequence's 32-byte hash is already in RPC display order (verified
    # against live mempool contents -- unlike hashing the rawtx payload,
    # which yields the wtxid for any SegWit transaction and so can't be
    # used as a getrawtransaction lookup key at all).
    return payload[:32].hex()


def fee_display(summary):
    if summary["is_coinbase"]:
        return "coinbase"
    if summary["fee"] is None:
        return "incomplete"
    return summary["fee"]


def process_and_log(rpc, txid, source, stats, persistence):
    tx = rpc.getrawtransaction(txid, verbose=True)
    summary = decode.process_transaction(rpc, tx)

    stats.resolved += summary["resolved"]
    stats.parent_pending += summary["parent_pending"]
    stats.unresolved += summary["unresolved"]
    persistence.add(summary, tx["vsize"])

    print(
        f"[tx] source={source} txid={summary['txid']} "
        f"inputs(resolved={summary['resolved']} pending={summary['parent_pending']} "
        f"unresolved={summary['unresolved']}) outputs={len(summary['outputs'])} "
        f"value={summary['output_value']} fee={fee_display(summary)} dust={summary['dust_count']}"
    )


def main():
    rpc = RPCClient()
    ch = CHClient()

    info = rpc.getblockchaininfo()
    print(f"[main] RPC connected: chain={info['chain']} blocks={info['blocks']}")

    checkpoint = persist.read_checkpoint(ch)
    if checkpoint and checkpoint["last_block_height"] > 0:
        print(f"[main] resuming: last checkpoint {checkpoint}")
        last_block_height = checkpoint["last_block_height"]
        last_block_hash = checkpoint["last_block_hash"]
    else:
        # No prior block checkpoint (fresh install, or only the stage-3
        # sentinel exists). Baseline is the current tip, not genesis --
        # CLAUDE.md: no historical backfill. Only blocks connecting from
        # here on are processed.
        print(
            f"[main] no prior block checkpoint, starting confirmation baseline "
            f"at current tip height={info['blocks']} (no historical backfill)"
        )
        last_block_height = info["blocks"]
        last_block_hash = info["bestblockhash"]

    stats = Stats()
    persistence = persist.Persistence(
        ch, stats, last_block_height=last_block_height, last_block_hash=last_block_hash,
    )
    last_reorg_check = time.monotonic()

    try:
        for topic, payload in zmq_listener.listen():
            if topic == "rawtx":
                pass  # arrival already logged by zmq_listener; no reliable
                # txid can be derived from this payload without decoding it
                # (hashing it yields the wtxid for SegWit transactions, not
                # the txid getrawtransaction needs) -- sequence's 'A' event
                # for the same transaction drives the RPC fetch instead.

            elif topic == "sequence":
                label = chr(payload[32])
                label_name = LABELS.get(label, f"unknown({label})")
                if label == "A":
                    txid = txid_from_sequence(payload)
                    try:
                        process_and_log(rpc, txid, "sequence", stats, persistence)
                        stats.fetched += 1
                    except Exception as exc:
                        stats.rpc_failures += 1
                        print(f"[main] sequence txid={txid} fetch failed: {exc}")
                elif label == "C":
                    # The payload's own hash/height bytes are never read --
                    # 'C' is a wake-up signal only. The authoritative tip
                    # comes from RPC; catch_up_to_tip walks forward one
                    # block at a time from the last confirmed height so
                    # nothing in between is skipped.
                    try:
                        confirm.catch_up_to_tip(rpc, ch, persistence, stats)
                    except Exception as exc:
                        stats.rpc_failures += 1
                        print(f"[main] block confirmation failed at height={persistence.last_block_height + 1}: {exc}")
                elif label == "D":
                    # Also a wake-up signal only, same reasoning as 'C' --
                    # the disconnected block's own hash isn't read. Triggers
                    # an immediate reorg check rather than waiting for the
                    # periodic timer, for faster detection.
                    print(f"[main] sequence event: {label_name} -- checking for reorg")
                    try:
                        reorg.check_and_handle(rpc, ch, persistence, stats)
                    except Exception as exc:
                        stats.reorg_check_failures += 1
                        print(f"[main] reorg check (triggered by 'D') failed: {exc}")
                else:
                    print(f"[main] sequence event: {label_name}")

            # topic is None on a poll timeout tick (mempool quiet). Falls
            # through to here regardless of branch above, which is the
            # point: both the flush check and the periodic reorg check must
            # run on a timer, not only when a message happens to arrive.
            if persistence.should_flush():
                persistence.flush()
            if time.monotonic() - last_reorg_check >= reorg.REORG_CHECK_SECONDS:
                last_reorg_check = time.monotonic()
                try:
                    reorg.check_and_handle(rpc, ch, persistence, stats)
                except Exception as exc:
                    stats.reorg_check_failures += 1
                    print(f"[main] periodic reorg check failed: {exc}")
    except KeyboardInterrupt:
        pass
    finally:
        persistence.flush()
        stats.duplicate_count = persist.count_duplicate_transactions(ch)
        print(f"[main] shutdown: {stats.summary()}")


if __name__ == "__main__":
    main()
