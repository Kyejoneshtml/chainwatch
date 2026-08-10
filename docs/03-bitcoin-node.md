# 03. The Bitcoin node

## The disk situation, corrected

Michael said 400 to 600 GB. That figure is a year or two out of date. As of early August 2026 the Bitcoin blockchain is roughly 760 GB of block data, and it grows by about 8 to 10 GB a month. Add a transaction index and you are over 800 GB.

You are not storing that on a laptop. So you prune.

## What pruning actually does

This is worth understanding properly because it is counterintuitive and it is a good thing to be able to explain.

A pruned node still downloads and validates every single block from genesis. It verifies the entire chain. It is a full node in the security sense. The difference is that once a block has been validated and its effects committed, the node deletes the raw block file from disk.

What it keeps is the **chainstate**, also called the UTXO set: the complete list of every unspent transaction output in existence. This is not pruned. A pruned node holds the full UTXO set, currently around 15 GB.

That distinction is the single most important technical fact in this project, and doc 04 explains why.

What you lose:
- You cannot look up an arbitrary historical transaction by its ID
- You cannot run `txindex`, Bitcoin Core rejects the combination
- You cannot serve old blocks to other nodes
- You cannot backfill history into your database

What you keep:
- Full validation and full consensus security
- The complete UTXO set, queryable by outpoint
- Live mempool transactions
- Live blocks as they arrive

For a forward-looking real-time monitoring product, you lose nothing that matters.

## Disk budget

| Item | Size |
|---|---|
| Pruned block storage, `prune=20000` | 20 GB |
| Chainstate (UTXO set) | ~15 GB, growing |
| Block index | ~1.5 GB |
| ClickHouse, roughly per month of ingestion | 1 to 3 GB |
| Neo4j, subgraphs only | 1 to 5 GB |
| Docker images | ~3 GB |
| **Steady state total** | **~45 to 55 GB** |

Check what you have before starting:

```bash
df -h
```

If you have 100 GB free you are comfortable. If you have 60 GB it will work but keep an eye on it. Below 50 GB, buy an external SSD. A 1 TB USB-C SSD is about £60 and removes the constraint entirely, which is a better use of an evening than fighting disk pressure for three weeks.

Note the chainstate grows steadily. Budget for it.

## Bandwidth is the real cost, not disk

Pruning saves disk. It does not save download. Your node still pulls all 760 GB during initial block download, because it must validate every block before discarding it.

Practical implications:
- Expect 1 to 4 days of syncing depending on connection and CPU
- If you are on a metered or capped connection, check the cap first
- Set `maxuploadtarget` so you do not also serve hundreds of GB back out

## Shortening the sync: assumeutxo

Worth knowing about. Bitcoin Core supports loading a UTXO set snapshot, which gets a node to a usable state in hours rather than days while it validates the historical chain in the background. Pruned nodes can use it.

Two caveats. The snapshot is checked against a hash hardcoded in Bitcoin Core, but you are still trusting whoever hosts the file to give you the right bytes, and there is no single canonical source. And during background sync you temporarily hold two chainstate directories, so peak disk usage is higher than steady state.

Recommendation: start a normal sync tonight and let it run. If after two days it is still crawling, look at assumeutxo. Do not add a moving part on day one.

## Config

`bitcoin.conf`:

```
server=1
daemon=0
rpcuser=chainwatch
rpcpassword=CHANGE_THIS
rpcbind=0.0.0.0
rpcallowip=172.16.0.0/12

# Pruning. 20000 MiB of recent blocks.
# Minimum permitted is 550. Do not use txindex with this.
prune=20000

# Speed up initial sync. Set to roughly a quarter of your RAM.
dbcache=4000

# Do not upload more than 1 GB a day to peers
maxuploadtarget=1000

# ZeroMQ. This is how the ingestor gets live data.
zmqpubrawtx=tcp://0.0.0.0:28332
zmqpubrawblock=tcp://0.0.0.0:28333
zmqpubhashblock=tcp://0.0.0.0:28334
```

`rpcallowip=172.16.0.0/12` covers the default Docker bridge network range so other containers can reach the RPC. Do not expose RPC beyond the Docker network, and do not port-forward it.

## Verify before building anything on top

Once synced, run these three checks. If any fails, stop and fix it, because the entire ingestion design in doc 04 depends on all three working.

```bash
# 1. Fully synced and pruned as expected
bitcoin-cli getblockchaininfo
# check: "pruned": true, "initialblockdownload": false,
#        "blocks" matches current height on a public explorer

# 2. UTXO lookups work. Take any txid from the current mempool.
bitcoin-cli getrawmempool | head
bitcoin-cli getrawtransaction <txid> true
# take one of its inputs, then:
bitcoin-cli gettxout <input_txid> <input_vout>
# must return an object with scriptPubKey.address. This is the whole
# ballgame. If this returns null for an unconfirmed transaction's
# input, re-read doc 04 before continuing.

# 3. ZeroMQ is publishing
bitcoin-cli getzmqnotifications
# should list the three sockets configured above
```

Do check number 2 by hand before writing a line of ingestion code.
