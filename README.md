# Chainwatch

Real-time Bitcoin fraud analytics. Watch a wallet, get told the moment money moves, then follow it through the network.

Built by Kye McFarlane-Jones, Edinburgh.

## The problem

Bitcoin is public but illegible. Every transaction that has ever happened is visible to anyone, yet when a wallet is drained the victim has no practical way to read it. There are no names, no account numbers, no balances, just hex strings pointing at other hex strings.

Commercial tools solve this for institutions at institutional prices. Chainwatch is an attempt at the individual version: paste an address, get alerted the moment funds move, and see where they went.

## What this repository is right now

Planning documents. No implementation code yet, which is deliberate.

The order of work is architecture first, written down until it is boring and obvious, then design system and mockups, then ingestion, then the interface. Skipping the first step produces a working Bitcoin node, a database full of hex strings, and no clear question to ask of it.

## Documents

| File | What it covers |
|---|---|
| `docs/01-thesis.md` | Why this project exists and the case for the approach |
| `docs/02-architecture.md` | Components and how data flows between them |
| `docs/03-bitcoin-node.md` | Pruning, disk budget, bandwidth, node configuration |
| `docs/04-ingestion.md` | The central technical problem and how it is solved |
| `docs/05-data-models.md` | ClickHouse schema, Neo4j schema, and why both |
| `docs/06-detection.md` | Fraud typologies and the detection logic |
| `docs/07-ui-spec.md` | Interface specification |
| `docs/08-build-plan.md` | Phased build plan |
| `docs/09-glossary.md` | Every term used here, defined |

## Stack

Bitcoin Core running pruned, publishing over ZeroMQ. A Python ingestor resolving transactions in real time. ClickHouse as the full archive, Neo4j for watched subgraphs. FastAPI and a React frontend with D3 for graph rendering. All of it in Docker Compose.

## Status

Node synced and verified at block 962,053, publishing on four ZeroMQ topics. Fifteen planning and research documents complete, recording 46 design corrections identified before implementation. Design system built. Ingestion is next. The commit history and doc revisions are part of the record, not just the finished build.

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

### Phase 0 verification: input resolution (11 August 2026)

Node synced at block 962,053. Pruned, out of initial block download, ZeroMQ publishing on all three sockets.

The check that mattered was resolving a sender address on a pruned node. It failed forty times in a row before I understood why.

`gettxout` takes an optional third argument, `include_mempool`, which defaults to true. With it enabled, an output that a pending transaction is spending counts as already spent and is excluded. That is exactly the case the ingestor operates in, since it processes transactions the moment they enter the mempool. Called with the default, it returns null every single time.

What makes this worth recording is the failure mode rather than the fix. Exit code 0, nothing on stderr, empty result. An ingestor written without the flag would run indefinitely, report success throughout, and resolve zero percent of inputs. Nothing would alert anyone until someone queried the database and found it empty.

Resolution confirmed against live data: a P2WSH output of 7.32669980 BTC, retrieved for an input that returned null under the default. `docs/04-ingestion.md` now specifies the flag and explains why.

The general lesson transfers beyond this project. The dangerous failures in a monitoring system are the ones that return success.
