import os

REQUIRED = [
    "CH_HOST",
    "CH_PORT",
    "CH_USER",
    "CH_PASSWORD",
    "CH_DATABASE",
]


def _load_dotenv(path=".env"):
    if not os.path.exists(path):
        return
    with open(path) as f:
        for line in f:
            line = line.strip()
            if not line or line.startswith("#") or "=" not in line:
                continue
            key, _, value = line.partition("=")
            os.environ.setdefault(key.strip(), value.strip())


_load_dotenv()

# Presence, not truthiness -- CH_PASSWORD may legitimately be empty. Same
# reasoning as ingestor/config.py. Deliberately no RPC_* or ZMQ_* here:
# detection is a separate component from the ingestor (docs/02-architecture.md)
# and must not need bitcoind connectivity just to run.
missing = [name for name in REQUIRED if name not in os.environ]
if missing:
    raise RuntimeError(
        f"Missing required environment variables: {', '.join(missing)}. "
        "Copy .env.example to .env and fill in real values -- same "
        "ClickHouse credentials as ingestor/.env, since this reuses the "
        "same 'ingestor' CH user (see docs/08-build-plan.md, phase 4b: "
        "no new grant needed)."
    )

CH_HOST = os.environ["CH_HOST"]
CH_PORT = int(os.environ["CH_PORT"])
CH_USER = os.environ["CH_USER"]
CH_PASSWORD = os.environ["CH_PASSWORD"]
CH_DATABASE = os.environ["CH_DATABASE"]

# docs/06-detection.md: "on a short interval." Matches the reorg-check
# cadence already established in the ingestor -- fast enough to be timely
# for a severity-high rule without hammering ClickHouse on a table this size.
# Shared by every rule in this component; split into per-rule intervals
# later if one rule's query cost ever actually calls for a different cadence.
DETECTION_INTERVAL_SECONDS = int(os.environ.get("DETECTION_INTERVAL_SECONDS", "15"))

# Rule 2 (wallet drain), docs/06-detection.md defaults. Global, not per-watch
# -- the watchlist schema has no columns for these and none are being added.
# 0.0001 BTC converted once, here, to the satoshi integer everything else in
# this codebase uses -- no floats anywhere past this comment.
RESIDUAL_THRESHOLD_SATS = int(os.environ.get("RESIDUAL_THRESHOLD_SATS", "10000"))
REQUIRE_NO_CHANGE = os.environ.get("REQUIRE_NO_CHANGE", "true").strip().lower() not in ("false", "0", "")
# wallet_drain.address_summary's GROUP BY spills to disk past this many
# bytes of aggregation state instead of growing until the server-wide cap
# picks it as the query to kill (docs/08-build-plan.md, known issues).
# A backstop, not the main fix: the largest active watch held 162,571
# flows rows on 2026-10-05, tens of MB of state, so this rarely triggers
# at current watch sizes. Collapsing three full-history scans into one is
# what actually cuts the failure exposure.
WALLET_DRAIN_SPILL_BYTES = int(os.environ.get("WALLET_DRAIN_SPILL_BYTES", str(100_000_000)))
# Same pattern as FAN_IN_SCAN_MAX_THREADS below. The merged query still
# failed 120 times in the 39 hours to 2026-10-07T09:35Z, every one the
# server-wide (total) cap with OvercommitTracker choosing this query's
# AggregatingTransform. At the server default (8 threads) each thread holds
# its own aggregation state; fewer threads means a smaller footprint and so
# a less likely OvercommitTracker victim. Lowers the odds, does not remove
# the server-wide cause.
WALLET_DRAIN_MAX_THREADS = int(os.environ.get("WALLET_DRAIN_MAX_THREADS", "2"))

# Rule 3 (fan-in consolidation), docs/06-detection.md defaults. Global, not
# per-watch, same reasoning as rule 2's thresholds above.
FAN_IN_MIN_SOURCES = int(os.environ.get("FAN_IN_MIN_SOURCES", "10"))
FAN_IN_WINDOW_SECONDS = int(os.environ.get("FAN_IN_WINDOW_SECONDS", str(60 * 60)))  # 1 hour
# fan_in_consolidation.sources_by_txid is a full scan of flows.txid (4.08
# GiB compressed on 2026-10-05) -- txid is not a prefix of flows's ORDER BY,
# so nothing prunes it. Fewer threads means fewer concurrent 65k-row read
# blocks (~4.5 MiB each for txid, matching the allocation sizes in the
# 26 Sep soak's MEMORY_LIMIT_EXCEEDED errors) held at once, in exchange for
# a slower scan; the timeout is sized for that slower scan, not the
# 30-second default every other query uses.
FAN_IN_SCAN_MAX_THREADS = int(os.environ.get("FAN_IN_SCAN_MAX_THREADS", "2"))
FAN_IN_SCAN_TIMEOUT_SECONDS = int(os.environ.get("FAN_IN_SCAN_TIMEOUT_SECONDS", "300"))

# Shared by all three rules, see common.cap_candidates. Bounds one
# run_once() call to at most this many candidates, gathered across every
# watch combined, rather than processing an entire, potentially unbounded
# backlog in one shot (docs/08-build-plan.md: watchlist_movement's first
# post-recalculation run took 48 minutes doing exactly that).
CANDIDATE_CAP = int(os.environ.get("CANDIDATE_CAP", "2000"))
