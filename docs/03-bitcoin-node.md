# 03. The Bitcoin node

## Disk

The chain was roughly 760 GB in August 2026, growing 8 to 10 GB per month. Bitcoin Core v30 removed the 80-byte OP_RETURN cap, so growth may exceed that. Pruning is not optional on ordinary hardware.

### What pruning does

A pruned node downloads and validates every block from genesis. It is a full node in the security sense. Once a block is validated and committed, the raw block file is deleted.

What it keeps is the **chainstate** — the complete UTXO set, every unspent output in existence, roughly 15 GB. This is not pruned.

That distinction is the reason this project works. See `04-ingestion.md`.

Lost: arbitrary historical transaction lookup, `txindex`, serving old blocks to peers, backfilling history.

Kept: full validation, the complete UTXO set, live mempool, live blocks.

### Budget

| Item | Size |
|---|---|
| Pruned blocks, `prune=20000` | 20 GB |
| Chainstate (UTXO set) | ~15 GB, growing |
| Block index | ~1.5 GB |
| ClickHouse, per month ingested | 1 to 3 GB |
| Neo4j, subgraphs only | 1 to 5 GB |
| Docker images | ~3 GB |
| **Steady state** | **~45 to 55 GB** |

**Monitor UTXO set growth separately from block growth.** Pruning absorbs block growth; it cannot absorb chainstate growth. The OP_RETURN change increases on-chain data volume, and the chainstate is the component with no ceiling.

On macOS, Docker Desktop's disk limit is separate from the host disk and defaults low. Raise it before starting.

### Bandwidth

Pruning saves disk, not download. The node pulls all 760 GB during initial sync because it must validate every block before discarding it. Expect one to four days. Set `maxuploadtarget` to avoid serving hundreds of GB back out.

## Configuration

`bitcoin.conf`:

```
server=1
printtoconsole=1

rpcuser=chainwatch
rpcpassword=CHANGEME
rpcbind=0.0.0.0
rpcallowip=172.16.0.0/12

# Pruning. 20000 MiB of recent blocks. Incompatible with txindex.
prune=20000

# Roughly a quarter of available RAM.
dbcache=4000

maxuploadtarget=1000

# ZeroMQ. Notification only, never treated as the data source.
zmqpubrawtx=tcp://0.0.0.0:28332
zmqpubrawblock=tcp://0.0.0.0:28333
zmqpubhashblock=tcp://0.0.0.0:28334
zmqpubsequence=tcp://0.0.0.0:28335
```

### The sequence topic

`zmqpubsequence` was added after the original configuration and is required.

It provides ordered events for mempool additions, mempool removals, and block **connections and disconnections**, with guaranteed ordering.

Block disconnection is the reorganization signal. Without it, reorgs are detected only by the block hash check described in `04-ingestion.md`, which works but is slower.

The config file mounts at `/config/bitcoin.conf` rather than into the data directory, because the official image's entrypoint runs `chown` across the data directory on startup and fails on a read-only mount. bitcoind is pointed at it with `-conf=/config/bitcoin.conf`.

## Verification

Once synced, three checks. All three must pass before ingestion work begins.

```bash
# 1. Synced and pruned
bitcoin-cli getblockchaininfo | grep -E '"pruned"|"initialblockdownload"|"blocks"'
# want: pruned true, initialblockdownload false, blocks matching a public explorer
```

```bash
# 2. Input resolution — the check that validates the architecture
bitcoin-cli getrawmempool | head -3
bitcoin-cli getrawtransaction <txid> true
# take the first input's txid and vout, then:
bitcoin-cli gettxout <input_txid> <input_vout> false
```

**The third argument matters.** `include_mempool` defaults to `true`, and with it enabled an output being spent by a pending transaction is treated as already spent and excluded. That is exactly the case the ingestor operates in. Called with the default, this returns null and reports success.

Must return an object containing `scriptPubKey.address` and `value`.

Verified 11 August 2026: returned a P2WSH address and 7.32669980 BTC for an input that returned null under the default.

```bash
# 3. ZeroMQ publishing
bitcoin-cli getzmqnotifications
# want four entries: rawtx, rawblock, hashblock, sequence
```

## Operational notes

**Prevent sleep.** On macOS, System Settings → Energy, or `caffeinate -dimsu`. Verify with `pmset -g | grep sleep`, which should read `0`. A sleeping machine mid-sync risks chainstate corruption and a full re-sync.

**Shut down cleanly.** `stop_grace_period: 10m` in compose. Bitcoin Core writes substantial state on shutdown.

**Chain splits happen.** On 8 August 2026 nodes running BIP-110 split from the majority chain, with roughly 2.53% of blocks signalling support. Bitcoin Core nodes follow the majority chain. This is recorded as evidence that chain-level disagreement is not hypothetical, which is the justification for the reorg handling in `04-ingestion.md`.
