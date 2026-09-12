import argparse
import re
import sys
import uuid

from ch_client import CHClient
from persist import now_str

# Bitcoin addresses (base58 or bech32) never contain quotes, semicolons, or
# backslashes -- this is validated before any value is interpolated into a
# SQL string below, the same defensive-regex-before-interpolation pattern
# confirm.py and reorg.py already use for txids and block hashes.
_ADDRESS_RE = re.compile(r"^[a-zA-Z0-9]{20,90}$")


def _validated(address):
    if not _ADDRESS_RE.match(address):
        sys.exit(f"'{address}' doesn't look like a Bitcoin address (expected 20-90 alphanumeric characters)")
    return address


def add_watch(ch, address, min_value, trace_depth):
    address = _validated(address)
    existing = ch.select(f"SELECT watch_id FROM watchlist FINAL WHERE address = '{address}' AND active = 1")
    if existing:
        print(f"already watching {address} (watch_id={existing[0]['watch_id']}); remove it first to change settings")
        return
    watch_id = str(uuid.uuid4())
    now = now_str()
    ch.insert_rows("watchlist", [{
        "address": address, "watch_id": watch_id, "created_at": now, "updated_at": now,
        "min_value": min_value, "trace_depth": trace_depth, "active": 1,
    }])
    print(f"watching {address} (watch_id={watch_id}, min_value={min_value}, trace_depth={trace_depth})")


def remove_watch(ch, address):
    address = _validated(address)
    existing = ch.select(
        f"SELECT watch_id, created_at, min_value, trace_depth FROM watchlist FINAL "
        f"WHERE address = '{address}' AND active = 1"
    )
    if not existing:
        print(f"{address} is not currently watched")
        return
    row = existing[0]
    ch.insert_rows("watchlist", [{
        "address": address, "watch_id": row["watch_id"], "created_at": row["created_at"],
        "updated_at": now_str(), "min_value": row["min_value"], "trace_depth": row["trace_depth"],
        "active": 0,
    }])
    print(f"stopped watching {address} (watch_id={row['watch_id']})")


def list_watches(ch):
    rows = ch.select("""
        SELECT address, watch_id, min_value, trace_depth, created_at
        FROM watchlist FINAL
        WHERE active = 1
        ORDER BY created_at
    """)
    if not rows:
        print("no active watches")
        return
    for r in rows:
        print(
            f"{r['address']}  watch_id={r['watch_id']}  min_value={r['min_value']}  "
            f"trace_depth={r['trace_depth']}  since={r['created_at']}"
        )


def main():
    parser = argparse.ArgumentParser(description="Manage chainwatch's watched addresses")
    sub = parser.add_subparsers(dest="command", required=True)

    p_add = sub.add_parser("add", help="start watching an address")
    p_add.add_argument("address")
    p_add.add_argument("--min-value", type=int, default=0,
                        help="satoshis; 0 = alert on any movement (default: 0). "
                             "Not enforced by the matcher yet -- see phase 4b")
    p_add.add_argument("--trace-depth", type=int, default=1,
                        help="hop depth for later graph expansion (default: 1)")

    p_remove = sub.add_parser("remove", help="stop watching an address")
    p_remove.add_argument("address")

    sub.add_parser("list", help="list currently watched addresses")

    args = parser.parse_args()
    ch = CHClient()

    if args.command == "add":
        if args.min_value < 0:
            sys.exit("--min-value must not be negative")
        if not (0 <= args.trace_depth <= 255):
            sys.exit("--trace-depth must fit in UInt8 (0-255)")
        add_watch(ch, args.address, args.min_value, args.trace_depth)
    elif args.command == "remove":
        remove_watch(ch, args.address)
    elif args.command == "list":
        list_watches(ch)


if __name__ == "__main__":
    main()
