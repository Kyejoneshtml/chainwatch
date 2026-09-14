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

# Rule 3 (fan-in consolidation), docs/06-detection.md defaults. Global, not
# per-watch, same reasoning as rule 2's thresholds above.
FAN_IN_MIN_SOURCES = int(os.environ.get("FAN_IN_MIN_SOURCES", "10"))
FAN_IN_WINDOW_SECONDS = int(os.environ.get("FAN_IN_WINDOW_SECONDS", str(60 * 60)))  # 1 hour
