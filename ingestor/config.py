import os

REQUIRED = [
    "RPC_HOST",
    "RPC_PORT",
    "RPC_USER",
    "RPC_PASSWORD",
    "ZMQ_HOST",
    "ZMQ_RAWTX_PORT",
    "ZMQ_SEQUENCE_PORT",
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

missing = [name for name in REQUIRED if not os.environ.get(name)]
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
