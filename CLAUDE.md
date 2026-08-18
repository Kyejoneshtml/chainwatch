# Context for AI coding assistants

Read this before making changes to this repository.

## What this project is

Chainwatch: a real-time Bitcoin fraud analytics platform. A user watches a wallet address, is alerted the moment funds move, and can trace where the money went through a network graph.

Full context is in `docs/`. Read `docs/01-thesis.md` and `docs/02-architecture.md` before proposing changes.

## Hard constraints

**Pruned node.** No `txindex`. No historical backfill. Input resolution uses `gettxout` against the UTXO set during the mempool window. Read `docs/04-ingestion.md` in full before touching ingestion. A proposal to call `getrawtransaction` on an arbitrary historical txid indicates that document has not been read.

**Satoshis as integers.** Never floating point for monetary amounts, anywhere, including test fixtures.

**The ingestor never blocks.** ClickHouse inserts are batched. Neo4j writes go to a separate queue. If the mempool subscriber falls behind, input resolution begins to fail and data is lost permanently.

**Heuristics are labelled as heuristics.** Change identification, address clustering and risk scores are probabilistic. They must carry confidence levels through the data model and into the interface. An inference is never presented as a fact.

**Phase order is enforced.** `docs/08-build-plan.md` defines seven phases, each with a definition of done. Implementation code does not begin before Phase 3.

## Stack

- Bitcoin Core, pruned, ZeroMQ enabled
- ClickHouse, full archive
- Neo4j Community, watched subgraphs only
- Python ingestor
- FastAPI
- React with a force-directed graph component
- Docker Compose

## Environment

Single machine. Disk is a genuine constraint; the budget is in `docs/03-bitcoin-node.md`. Proposals assuming cloud infrastructure or spare terabytes are out of scope.

## Protected paths

Never modify these without stopping first and stating plainly what the change is and why:

- `bitcoin.conf` — live mainnet node configuration, contains RPC credentials
- `schema/` — applied to a running database with data behind it
- `regtest/` — the test harness everything downstream is validated against
- `docker-compose.yml` — running services, including a node with five days of sync state

## Destructive commands

Never run these without explicit confirmation in the same message, quoting the exact command:

- `docker compose down -v`, or any command removing volumes
- `rm -rf`, or `rm` on anything outside a temporary working directory
- `git reset --hard`, `git clean`, `git push --force`
- Any `DROP` or `TRUNCATE` against ClickHouse
- `docker volume rm`

**STOP AND CONFIRM** — state this as its own visible line before running one of the above, not a passing mention buried in output.

The node holds five days of validated chain state that takes a full day to rebuild, and the regtest harness is the only thing proving reorg handling works. Both are cheap to protect and expensive to lose.

## Working preferences

- Be specific. If something needs changing, name the file and the change
- Push back on decisions that look wrong rather than implementing them
- Verify factual claims about API behaviour by testing rather than asserting
