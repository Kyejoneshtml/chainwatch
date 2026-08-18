import time
from dataclasses import dataclass, field

import config
import zmq_listener
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

    def summary(self):
        return {
            "elapsed_seconds": round(time.monotonic() - self.started_at, 1),
            "fetched": self.fetched,
            "rpc_failures": self.rpc_failures,
        }


def txid_from_sequence(payload):
    # sequence's 32-byte hash is already in RPC display order (verified
    # against live mempool contents -- unlike hashing the rawtx payload,
    # which yields the wtxid for any SegWit transaction and so can't be
    # used as a getrawtransaction lookup key at all).
    return payload[:32].hex()


def fetch_and_log(rpc, txid, source):
    tx = rpc.getrawtransaction(txid, verbose=True)
    print(f"[main] source={source} txid={txid} inputs={len(tx['vin'])}")


def main():
    rpc = RPCClient()

    info = rpc.getblockchaininfo()
    print(f"[main] RPC connected: chain={info['chain']} blocks={info['blocks']}")

    stats = Stats()
    try:
        for topic, payload in zmq_listener.listen():
            if topic == "rawtx":
                continue  # arrival already logged by zmq_listener; no reliable
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
                        fetch_and_log(rpc, txid, "sequence")
                        stats.fetched += 1
                    except Exception as exc:
                        stats.rpc_failures += 1
                        print(f"[main] sequence txid={txid} fetch failed: {exc}")
                else:
                    print(f"[main] sequence event: {label_name}")
    except KeyboardInterrupt:
        pass
    finally:
        print(f"[main] shutdown: {stats.summary()}")


if __name__ == "__main__":
    main()
