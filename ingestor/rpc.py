import itertools

import requests

import config


class RPCError(Exception):
    pass


class RPCClient:
    def __init__(self, host=config.RPC_HOST, port=config.RPC_PORT,
                 user=config.RPC_USER, password=config.RPC_PASSWORD):
        self._url = f"http://{host}:{port}/"
        self._auth = (user, password)
        self._ids = itertools.count(1)
        self._session = requests.Session()

    def call(self, method, params=None):
        payload = {
            "jsonrpc": "1.0",
            "id": next(self._ids),
            "method": method,
            "params": params or [],
        }
        resp = self._session.post(self._url, json=payload, auth=self._auth, timeout=30)
        # bitcoind returns HTTP 500 for ordinary RPC errors (bad txid, etc),
        # not just for genuine server failures, and still puts a real JSON
        # body on the response -- so the body is parsed before checking
        # status, rather than raise_for_status() discarding it.
        try:
            body = resp.json()
        except ValueError:
            resp.raise_for_status()
            raise
        if body.get("error") is not None:
            raise RPCError(f"{method}{params or []} -> {body['error']}")
        resp.raise_for_status()
        return body["result"]

    def getblockchaininfo(self):
        return self.call("getblockchaininfo")

    def getrawtransaction(self, txid, verbose=True):
        return self.call("getrawtransaction", [txid, verbose])

    def gettxout(self, txid, vout):
        # include_mempool is hardcoded false. With the default (true), an
        # output being spent by a pending transaction counts as already
        # spent and gettxout returns null -- silently, exit 0, no stderr.
        # That is exactly the case this ingestor resolves inputs in.
        # See docs/04-ingestion.md, "include_mempool must be false".
        return self.call("gettxout", [txid, vout, False])
