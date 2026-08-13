# Regtest harness

A private Bitcoin network for testing behaviour that cannot be triggered on mainnet on demand — principally chain reorganizations.

Separate from the mainnet node in every respect: different compose file, different volumes, different network. Neither can see the other.

## Why this exists

`04-ingestion.md` requires reorg detection and rollback. Roughly one reorganization occurs per day on mainnet, at an unpredictable time, and reproducing one deliberately is impossible.

Lopp used the same approach when building BitGo's indexer, describing a local simulator generating "random transactions, blocks, forks and problematic behaviour" as an invaluable QA mechanism.

Reorg handling that cannot be tested cannot be trusted.

## Credentials

`regtest/bitcoin-regtest.conf` contains a hardcoded weak RPC password and permissive `rpcallowip`. This is deliberate and safe to commit:

- The network exists only on this machine
- It contains no real bitcoin, and cannot
- It has no connection to mainnet or to any public network

Nothing in this directory should ever be copied into the mainnet configuration.

## Layout

Two nodes, `btc1` and `btc2`, on a private Docker network.

| Node | RPC port on host | P2P port in network |
|---|---|---|
| btc1 | 18443 | 18444 |
| btc2 | 18453 | 18444 |

Note the config places all network-specific settings inside the `[regtest]` section. Bitcoin Core refuses to start otherwise, since a setting like `rpcbind` at the top level is ambiguous about which network it applies to.

## Aliases

```bash
alias btc1='docker compose -f ~/chainwatch/docker-compose.regtest.yml exec btc1 bitcoin-cli -conf=/config/bitcoin.conf'
alias btc2='docker compose -f ~/chainwatch/docker-compose.regtest.yml exec btc2 bitcoin-cli -conf=/config/bitcoin.conf'
```

## Scripts

| Script | Purpose |
|---|---|
| `regtest/up.sh` | Start both nodes, create wallets, mine to a spendable state, connect them |
| `regtest/reorg.sh` | Split the network, mine competing chains, reconnect, report the result |
| `regtest/reset.sh` | Destroy both chains and start from genesis |

## The reorg procedure

`reorg.sh` performs the following, and each step is observable:

1. **Split.** `setnetworkactive false` on btc1. Both nodes report zero connections and each believes its chain is canonical.

2. **Diverge.** btc1 mines 2 blocks, btc2 mines 5. They now disagree about history from the split height onward.

3. **Record.** btc1's tip hash is captured before reconnection. This block is about to be orphaned.

4. **Reconnect.** `setnetworkactive true` restores networking but does **not** restore the peer connection — the peer was dropped when networking went down. `addnode ... onetry` is required to re-establish it. This is easy to miss and looks like a failed reorg.

5. **Converge.** btc1 sees the longer chain, discards its own blocks, and adopts btc2's.

6. **Verify.** `getblock <recorded_hash>` reports `confirmations: -1`.

## What -1 means

The block still exists in the node's database and can be fetched by hash. It is no longer on the active chain.

**This is the signal the ingestor detects.** Every confirmed row stores `block_hash` alongside `block_height`. Periodically, or on a `sequence` topic disconnect event, the ingestor verifies the block at a recorded height still has the recorded hash. If it does not, every row derived from that block is invalid and the rollback path in `04-ingestion.md` executes.

Height alone is never sufficient. Height is reused across a reorg; the hash is not.

This mirrors electrs, which stores the block hash alongside the height for exactly this purpose.

## First verified run

13 August 2026. Chain split at height 111. btc1 mined to 113, btc2 to 116. On reconnection btc1 adopted btc2's chain and its former tip `50ce276753f9deb561051d80cb71917b6d5590b90e94f484a4b87489f51bd0f8` at height 113 reported `confirmations: -1`.

Elapsed time from split to confirmed reorg: under two minutes.

## Repeating

The nodes are left disconnected after a reorg run, so the exercise can be repeated without resetting. `reset.sh` destroys both chains and returns to genesis if a clean state is needed.
