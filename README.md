# Chainwatch

Real-time Bitcoin fraud analytics. Watch a wallet, get told the moment money moves, then follow it through the network.

Built by Kye McFarlane-Jones, Edinburgh. Rename the project if you think of something better. "Chainwatch" is a placeholder.

## What this repository is right now

Planning documents only. No code. That is deliberate.

The order of work is:

1. Write the architecture down in markdown until it is boring and obvious
2. Build a design system in Claude Design
3. Wireframe, then high-fidelity mockups
4. Only then write ingestion code
5. Only then connect the UI to the backend

Skipping step 1 is the standard failure mode. You end up with a working Bitcoin node, a database full of hex strings, and no idea what question you were trying to answer.

## The one-sentence pitch

Bitcoin is public but illegible. Chainwatch makes a specific wallet legible in real time: it tells you when funds move, where they went, and whether the movement pattern looks like laundering.

## Reading order

| File | What it covers |
|---|---|
| `docs/01-thesis.md` | Why this project, what the opinion is, what you say in an interview |
| `docs/02-architecture.md` | The components and how data flows between them |
| `docs/03-bitcoin-node.md` | Pruning, disk budget, bandwidth reality, node config |
| `docs/04-ingestion.md` | The hard technical problem and how it is solved |
| `docs/05-data-models.md` | ClickHouse schema, Neo4j schema, why both |
| `docs/06-detection.md` | The actual fraud logic. This is the part that matters |
| `docs/07-ui-spec.md` | The brief you take into Claude Design |
| `docs/08-build-plan.md` | Phased plan with stop points |
| `docs/09-glossary.md` | Every term used here, defined |
| `CLAUDE.md` | Context file for Claude Code sessions |

## Status

Nothing built yet. Update this section as phases complete so the repo history tells the story. Michael's point about documenting the journey is right: the commit log and the doc revisions are the evidence, not just the finished thing.
