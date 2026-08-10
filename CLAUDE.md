# Context for Claude Code

Read this before doing anything in this repository.

## What this project is

Chainwatch: a real-time Bitcoin fraud analytics platform. A user watches a wallet address and is alerted the moment funds move, then can trace where the money went through a network graph.

Full context is in `docs/`. Read `docs/01-thesis.md` and `docs/02-architecture.md` before proposing anything.

## Who you are working with

Kye. Business Administration graduate, not a professional developer. Higher in Computing Science, originally enrolled in Computer Science before switching. Codes occasionally. Learns fast.

This means:

- Explain what you are doing and why, not just what to run
- Do not assume familiarity with Docker internals, database administration, or deployment
- Do not skip steps because they seem obvious
- When suggesting a command, say what it does and what a successful result looks like
- When something fails, explain the actual cause rather than just producing a fix

Domain knowledge is the opposite way round. He knows financial crime, AML, KYC and fraud typologies well, from an FCA-regulated bank role and a dissertation on AI adoption in APP fraud prevention that scored 85%. Do not explain what layering is. Do explain what a MergeTree ordering key is.

## Working style

- Be specific and direct. If something needs changing, say exactly what and exactly where. Do not hedge or circle around it
- Push back when a decision looks wrong. Do not just implement what was asked if it is a mistake
- Verify factual claims. If unsure whether an API behaves a certain way, say so and test it rather than asserting it

## Hard constraints

**Do not write code until Phase 3 in `docs/08-build-plan.md`.** Phases 0 to 2 are node sync, documentation and design. Writing implementation code early is the specific failure mode this plan exists to avoid.

**Pruned node.** No `txindex`. No historical backfill. Input resolution uses `gettxout` against the UTXO set during the mempool window. Read `docs/04-ingestion.md` fully before touching ingestion. If you propose `getrawtransaction` on an arbitrary historical txid, you have not read it.

**Satoshis as integers.** Never floats for monetary amounts, anywhere, including in test fixtures.

**Never block the ingestor.** ClickHouse inserts are batched. Neo4j writes go to a separate queue. If the mempool subscriber falls behind, input resolution starts failing.

**Heuristics are labelled as heuristics.** Change identification, clustering and risk scores are probabilistic. They must be surfaced with confidence levels in both the data model and the UI. Never present an inference as a fact.

## Stack

- Bitcoin Core, pruned, ZMQ enabled
- ClickHouse, full archive
- Neo4j Community, watched subgraphs only
- Python ingestor
- FastAPI
- React with D3 for graph rendering
- Docker Compose for all of it

## Environment

Single normal machine. Disk is a real constraint, see the budget in `docs/03-bitcoin-node.md`. Do not propose anything that assumes cloud infrastructure or spare terabytes.

## Definition of done for any phase

It is in `docs/08-build-plan.md`. Each phase has one. Do not move on until it is met.
