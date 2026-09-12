import time

REFRESH_SECONDS_DEFAULT = 30  # docs/02-architecture.md: an in-memory check
# on every transaction, refreshed on a short interval, never a query per
# transaction (5-7 tx/s, several inputs and outputs each, would not keep
# up). Watch additions are a deliberate, infrequent user action, not a
# latency-sensitive path -- 30s means a newly added watch takes effect
# quickly enough to test or demo, without adding needless ClickHouse
# chatter for a table this small. Configurable via WATCHLIST_REFRESH_SECONDS
# (config.py), not required -- existing deployments don't need to set it.


class WatchlistMatcher:
    """Holds active watched addresses as a Python dict (address -> watch
    metadata), refreshed on a timer rather than queried per transaction.

    check() is called from both the mempool path (main.py, on sequence's
    'A' event) and the confirmed-block path (confirm.py) -- "every
    transaction" per docs/02-architecture.md, not just mempool arrivals,
    since a mempool-only check would silently miss transactions that first
    appear directly in a block (the same coverage gap tx_confirmed_new
    already tracks elsewhere).
    """

    def __init__(self, ch, refresh_seconds=None):
        self.ch = ch
        self.refresh_seconds = refresh_seconds or REFRESH_SECONDS_DEFAULT
        self._watches = {}
        self._last_refresh = 0.0  # 0 forces a load on the first maybe_refresh()

    def load(self):
        rows = self.ch.select("""
            SELECT address, watch_id, min_value, trace_depth
            FROM watchlist FINAL
            WHERE active = 1
        """)
        self._watches = {r["address"]: r for r in rows}
        self._last_refresh = time.monotonic()
        # Printed on every load, not just the first -- otherwise there is no
        # visible signal that a watch added after startup was ever picked up
        # by the periodic refresh rather than sitting unloaded.
        print(f"[watchlist] loaded {len(self._watches)} active address(es)")
        return len(self._watches)

    def maybe_refresh(self):
        if time.monotonic() - self._last_refresh >= self.refresh_seconds:
            self.load()

    def check(self, summary, source, stats):
        """summary is the same shape decode.py and confirm.py both produce:
        inputs/outputs lists, each with an 'address' key that is falsy
        (None or '') when unresolved -- checked and skipped before the set
        lookup, never matched, per docs/06-detection.md.
        """
        matches = []
        for position, inp in enumerate(summary["inputs"]):
            address = inp.get("address")
            if address and address in self._watches:
                matches.append(("input", position, address, inp.get("value")))
        for out in summary["outputs"]:
            address = out.get("address")
            if address and address in self._watches:
                matches.append(("output", out["position"], address, out.get("value")))

        for side, position, address, value in matches:
            watch = self._watches[address]
            print(
                f"[watchlist] MATCH source={source} txid={summary['txid']} side={side} "
                f"position={position} address={address} value={value} "
                f"min_value={watch['min_value']} watch_id={watch['watch_id']}"
            )
        stats.watchlist_matches += len(matches)
        return matches
