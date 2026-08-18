import zmq

import config


def listen():
    """Yields (topic: str, payload: bytes) for rawtx and sequence notifications.

    ZMQ is notification only -- the caller decides what, if anything, to do
    with payload. This function does not interpret it.
    """
    ctx = zmq.Context()
    sock = ctx.socket(zmq.SUB)
    sock.connect(f"tcp://{config.ZMQ_HOST}:{config.ZMQ_RAWTX_PORT}")
    sock.connect(f"tcp://{config.ZMQ_HOST}:{config.ZMQ_SEQUENCE_PORT}")
    sock.setsockopt(zmq.SUBSCRIBE, b"rawtx")
    sock.setsockopt(zmq.SUBSCRIBE, b"sequence")

    try:
        while True:
            topic, payload, _seq = sock.recv_multipart()
            topic = topic.decode("ascii")
            print(f"[zmq] notification arrived: topic={topic} bytes={len(payload)}")
            yield topic, payload
    finally:
        sock.close()
        ctx.term()
