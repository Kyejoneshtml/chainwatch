import json
from decimal import Decimal

import requests

import config

# Duplicated from ingestor/ch_client.py rather than imported, deliberately --
# detection is a separate component (docs/02-architecture.md) and importing
# across would couple its runtime to ingestor/config.py's RPC_*/ZMQ_*
# requirements, which detection has no need of at all.


class CHError(Exception):
    pass


class CHClient:
    def __init__(self, host=config.CH_HOST, port=config.CH_PORT,
                 user=config.CH_USER, password=config.CH_PASSWORD,
                 database=config.CH_DATABASE):
        self._url = f"http://{host}:{port}/"
        self._auth = (user, password)
        self._database = database
        self._session = requests.Session()

    def _execute(self, query, body=None):
        if body is None:
            # Query-only call (select()). The query goes in the POST body,
            # not the `query` URL param -- ClickHouse's HTTP form parser
            # rejects a `query` param past roughly 100KB with "Field value
            # too long" (verified against this container in the ingestor).
            params = {"database": self._database}
            data = query
        else:
            params = {"database": self._database, "query": query}
            data = body
        resp = self._session.post(self._url, params=params, data=data, auth=self._auth, timeout=30)
        if resp.status_code != 200:
            raise CHError(f"query={query!r} -> HTTP {resp.status_code}: {resp.text}")
        return resp.text

    def insert_rows(self, table, rows):
        # JSONEachRow: DateTime/DateTime64 columns must be quoted strings,
        # not bare JSON floats -- verified against this container in the
        # ingestor; the bare-float form toDateTime64() accepts as a SQL
        # argument is rejected here with a parse error.
        if not rows:
            return
        body = "\n".join(json.dumps(row) for row in rows)
        self._execute(f"INSERT INTO {table} FORMAT JSONEachRow", body=body)

    def select(self, query):
        text = self._execute(f"{query} FORMAT JSONEachRow")
        return [json.loads(line, parse_float=Decimal) for line in text.splitlines() if line]
