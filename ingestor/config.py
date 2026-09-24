import os

REQUIRED = [
    "RPC_HOST",
    "RPC_PORT",
    "RPC_USER",
    "RPC_PASSWORD",
    "ZMQ_HOST",
    "ZMQ_RAWTX_PORT",
    "ZMQ_SEQUENCE_PORT",
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

# Presence, not truthiness: CH_PASSWORD is legitimately empty (the
# ClickHouse container has no password configured), and an empty string
# set on purpose is not the same failure as a variable never set at all.
missing = [name for name in REQUIRED if name not in os.environ]
if missing:
    raise RuntimeError(
        f"Missing required environment variables: {', '.join(missing)}. "
        "Copy .env.example to .env and fill in real values."
    )

RPC_HOST = os.environ["RPC_HOST"]
RPC_PORT = int(os.environ["RPC_PORT"])
RPC_USER = os.environ["RPC_USER"]
RPC_PASSWORD = os.environ["RPC_PASSWORD"]

ZMQ_HOST = os.environ["ZMQ_HOST"]
ZMQ_RAWTX_PORT = int(os.environ["ZMQ_RAWTX_PORT"])
ZMQ_SEQUENCE_PORT = int(os.environ["ZMQ_SEQUENCE_PORT"])

CH_HOST = os.environ["CH_HOST"]
CH_PORT = int(os.environ["CH_PORT"])
CH_USER = os.environ["CH_USER"]
CH_PASSWORD = os.environ["CH_PASSWORD"]
CH_DATABASE = os.environ["CH_DATABASE"]

# Optional, not in REQUIRED -- existing deployments don't need to set this.
# See watchlist.py for why 30s.
WATCHLIST_REFRESH_SECONDS = int(os.environ.get("WATCHLIST_REFRESH_SECONDS", "30"))

# How often main.py retries confirm.catch_up_to_tip on its own, rather than
# only in response to a live 'C' event or a detected reorg. See
# confirm.MAX_BLOCKS_PER_CALL and docs/08-build-plan.md's first mainnet
# soak run -- without this, a bounded call left mid-backlog (or one that
# failed outright) waits for the next real block, which could be ~10
# minutes away. 30s matches the reorg-check cadence already established.
CATCH_UP_RETRY_SECONDS = int(os.environ.get("CATCH_UP_RETRY_SECONDS", "30"))
