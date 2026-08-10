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



## Build log

### Phase 0: standing up the node (10 August 2026)

Mac mini, Apple Silicon, 230 GB free. Docker Desktop, Bitcoin Core 31.1, pruned to 20 GB. Four things broke before it ran, each a different kind of problem.

**Docker Desktop's disk limit is separate from the disk.** Docker on macOS runs a Linux VM with its own virtual disk and its own cap. The Mac having 230 GB free is irrelevant if that cap is 64 GB. Raised it to 150 GB before starting, which avoided running out of space partway through a multi-day sync.

**A stray quote in a filename.** A quote character crept into the `nano` command, so the file was created as `docker-compose.yml'` rather than `docker-compose.yml`. Compose reported "no configuration file provided", which is accurate but says nothing about why. Found it by reading `ls -la` properly instead of skimming it.

**Read-only mount colliding with the image's startup script.** I mounted `bitcoin.conf` read-only into the container's data directory. The official image's entrypoint runs `chown` across that directory on startup, the chown failed on a read-only file, and the container exited. With `restart: unless-stopped` set, it did that in a loop several hundred times. Fixed by mounting the config to `/config` instead and pointing bitcoind at it with `-conf=/config/bitcoin.conf`, so the startup script never touches it.

**Bitcoin Core refuses to guess between two config files.** The failed run had left a copy of `bitcoin.conf` inside the data volume. Once the correct config was at `/config`, the node saw two and refused to start rather than silently pick one. Removed the stray file with a throwaway Alpine container mounted against the volume, since the node's own container would not stay up long enough to do it from inside.

That refusal is worth noting rather than treating as an obstacle. Silently ignoring a config file is how someone ends up running a node they believe is pruned and is not. A system handling money should decline ambiguity rather than resolve it out of sight, which is the same principle behind treating clustering results as probabilistic in `docs/06-detection.md`.

**bitcoin-cli needed telling where its credentials were.** The node had the config, the CLI did not, so it looked in the default path and found nothing. Adding the same `-conf` flag fixed it. Aliased as `btc` to avoid retyping.

None of these were exotic. Every one was named precisely in the container logs, which is where I should have looked first rather than second.
