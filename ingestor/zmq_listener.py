import zmq

import config

POLL_TIMEOUT_MS = 500


def listen():
    """Yields (topic: str, payload: bytes) for rawtx and sequence notifications,
    or (None, None) on each poll timeout with nothing received.

    ZMQ is notification only -- the caller decides what, if anything, to do
    with payload. This function does not interpret it.

    A Poller with a timeout is used rather than a plain blocking recv so the
    caller regains control on a bound (POLL_TIMEOUT_MS) even when the
    mempool is quiet -- needed for a time-based batch flush (1,000 rows or
    2 seconds, whichever first) to actually honour its 2-second half, not
    just the fortunate case where a message happens to arrive within it.
    """
    ctx = zmq.Context()
    sock = ctx.socket(zmq.SUB)
    sock.connect(f"tcp://{config.ZMQ_HOST}:{config.ZMQ_RAWTX_PORT}")
    sock.connect(f"tcp://{config.ZMQ_HOST}:{config.ZMQ_SEQUENCE_PORT}")
    sock.setsockopt(zmq.SUBSCRIBE, b"rawtx")
    sock.setsockopt(zmq.SUBSCRIBE, b"sequence")
    poller = zmq.Poller()
    poller.register(sock, zmq.POLLIN)

    try:
        while True:
            events = dict(poller.poll(POLL_TIMEOUT_MS))
            if sock not in events:
                yield None, None
                continue
            topic, payload, _seq = sock.recv_multipart()
            topic = topic.decode("ascii")
            print(f"[zmq] notification arrived: topic={topic} bytes={len(payload)}")
            yield topic, payload
    finally:
        sock.close()
        ctx.term()
