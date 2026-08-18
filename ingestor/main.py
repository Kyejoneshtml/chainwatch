import time
from dataclasses import dataclass, field

import config
import decode
import persist
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
    if checkpoint:
        print(f"[main] resuming: last checkpoint {checkpoint}")
    else:
        print("[main] no checkpoint found, starting fresh")

    stats = Stats()
    persistence = persist.Persistence(ch, stats)

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
                else:
                    print(f"[main] sequence event: {label_name}")

            # topic is None on a poll timeout tick (mempool quiet). Falls
            # through to here regardless of branch above, which is the
            # point: the flush check must run on a timer, not only when a
            # message happens to arrive.
            if persistence.should_flush():
                persistence.flush()
    except KeyboardInterrupt:
        pass
    finally:
        persistence.flush()
        stats.duplicate_count = persist.count_duplicate_transactions(ch)
        print(f"[main] shutdown: {stats.summary()}")


if __name__ == "__main__":
    main()
