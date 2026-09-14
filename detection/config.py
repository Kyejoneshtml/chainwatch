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
DETECTION_INTERVAL_SECONDS = int(os.environ.get("DETECTION_INTERVAL_SECONDS", "15"))
