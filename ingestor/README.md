# Ingestor

## Setup

```
python3 -m venv .venv
.venv/bin/pip install -r requirements.txt
cp .env.example .env   # then fill in real RPC credentials from bitcoin.conf,
                        # and a real ClickHouse password -- see below
.venv/bin/python main.py
```

## ClickHouse: the 'default' user does not work from the host, by design

`/etc/clickhouse-server/users.d/default-user.xml` restricts the `default` user's `<networks>` to `::1` and `127.0.0.1` — connections must originate from true localhost as ClickHouse itself sees them. `docker exec clickhouse clickhouse-client` satisfies that: it runs inside the container and connects to its own loopback. A request to the published host port does not, even when the client believes it is talking to `127.0.0.1` — **Docker Desktop's port forwarding does not preserve `127.0.0.1` as the source IP once the connection crosses into the container**, so ClickHouse's network check rejects it before the password is ever examined.

The failure this produces is genuinely misleading: HTTP 401, `Code: 194`, `"Authentication failed: password is incorrect, or there is no user with such name"` — indistinguishable, from the client side, from an actually wrong password. It is not a password problem. `curl -u default: http://127.0.0.1:8123/` fails identically with an empty password, a correct empty password (verified against `system.users`, `auth_type = 'plaintext_password'` with no value set), or no `Authorization` header at all — the network check runs first regardless. Confirmed by comparing `docker exec` (works) against every host-side auth variant (all fail the same way) before concluding it was the network restriction and not the credential.

The fix is not to widen `default`'s network — that restriction is a real, working security control and stays as-is. Instead, the ingestor authenticates as a dedicated `ingestor` ClickHouse user: `SELECT` and `INSERT` on `chainwatch` only, `HOST IP` scoped to `172.16.0.0/12` (the Docker bridge range, the same one `bitcoin.conf`'s `rpcallowip` already uses), created via `CREATE USER` against the running instance rather than a config file.

**That means it is not persisted the way the applied schema is.** `CREATE USER` writes to ClickHouse's own access-entity storage under `/var/lib/clickhouse/access/`, inside the `clickhouse-data` volume — it survives an ordinary container restart or recreate, but is gone if that volume is ever removed or recreated (`docker compose down -v`, `docker volume rm`). If that happens: re-run `schema/ingestor-user.sql.example` (with a real password substituted for `CHANGEME`) and update `CH_PASSWORD` in `.env` to match. Nothing about this is automatic; it is exactly the kind of undocumented local state that becomes unreproducible if it isn't written down, which is why it's written down here.

## Known constraint: Python version

This machine has only `/usr/bin/python3` (Apple's Command Line Tools Python, 3.9.6) — no Homebrew, pyenv, uv, or python.org install present. 3.9 reached end of life in October 2025.

The venv is built from this Python because there is nothing newer to pin it to. In practice this surfaces as a `NotOpenSSLWarning` from `urllib3` on every run (this system's `ssl` module is built against LibreSSL, which `urllib3` v2 doesn't recognise as new enough) — harmless for RPC calls over `127.0.0.1`, but worth knowing the source of rather than treating as unexplained noise.

If a newer Python becomes available on this machine, rebuild the venv against it instead:

```
rm -rf .venv
python3.12 -m venv .venv   # or whatever version is installed
.venv/bin/pip install -r requirements.txt
```
