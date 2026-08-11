# 04. Ingestion

The central technical problem in the system. Everything else is configuration and query writing.

## Bitcoin has no accounts

There are no balances and no accounts. There are only **unspent transaction outputs**.

A transaction consumes existing outputs and creates new ones:

```
Inputs:                          Outputs:
  (txid_A, vout 1)  ---------->    0.4 BTC to address bc1q...xyz
  (txid_B, vout 0)  ---------->    0.6 BTC to address bc1q...abc
```

Outputs are straightforward. Each states its value and its locking script, and an address derives from that script.

**Inputs are the problem.** An input is a pointer: transaction ID plus output index. It carries no address and no amount. Determining the sender requires looking up the output being spent.

This is why tracing funds on Bitcoin is harder than it appears from the outside.

## Why this collides with pruning

Resolving an input requires the previous transaction. An archival node with `txindex=1` answers this with `getrawtransaction`. A pruned node may have deleted that transaction years ago, and `txindex` is incompatible with pruning.

## The resolution

**A pruned node retains the complete UTXO set.**

An input to an unconfirmed transaction is, by definition, currently unspent. That is what makes the spending transaction valid. So the output sits in the UTXO set, and `gettxout` returns it with its value and address, regardless of when it was created.

```
gettxout(txid, vout, include_mempool) -> { value, scriptPubKey: { address, type }, ... }
```

This holds on a pruned node for any unspent output, including one created in 2013.

### The third argument is not optional in practice

`include_mempool` defaults to `true`. With it enabled, an output that a **pending** transaction is spending is treated as already spent and excluded from the result.

That is precisely the case the ingestor operates in. It processes transactions the moment they arrive in the mempool, so every input it resolves is by definition being spent by a pending transaction. Called with the default, `gettxout` returns null every time.

**The ingestor must pass `include_mempool=false`**, which queries the UTXO set as of the confirmed chain tip, where those outputs remain unspent.

The failure mode matters more than the fix. `gettxout` with the default returns exit code 0, writes nothing to stderr, and produces an empty result. No exception, no error log, no crash. An ingestor built without this flag runs indefinitely, reports success, and resolves zero percent of inputs.

Verified against a live node on 11 August 2026: input resolution returned a P2WSH address and a value of 7.32669980 BTC for an output that returned null under the default behaviour.

## The window

Once a transaction is confirmed, its inputs are spent and leave the UTXO set permanently. `gettxout` then returns null under any flag.

So there is a window. A transaction's inputs are resolvable while it sits in the mempool. After it is mined, they are not.

This is a constraint that produces the correct design rather than a problem to work around.

## Mempool-first ingestion

```
ZMQ rawtx fires (transaction enters mempool)
    |
    v
Decode the raw transaction
    |
    v
For each input: gettxout(prev_txid, prev_vout, include_mempool=false)
    |            -> returns sender address and amount
    |            -> the window is open now and closes on confirmation
    v
Write row to ClickHouse with status = 'pending'
    |
    v
Cache every output this transaction creates, locally
    |
    v
... roughly 10 minutes on average ...
    |
    v
ZMQ rawblock fires (transaction confirmed)
    |
    v
Look the transaction up by txid in local data. Already present,
fully resolved, from the mempool stage.
    |
    v
Update status = 'confirmed', set block height and timestamp
```

This is how a real-time monitoring product should work regardless. A suspicious movement is worth knowing about when it is broadcast, not ten minutes later when it is mined. The pruning constraint forces the architecture that the product requires anyway.

## Handling the misses

Transactions will be missed. The ingestor restarts, a container fails, and some transactions are mined without ever passing through the local mempool view.

Three fallbacks, in order:

1. **The local outputs table.** Every output ever ingested is stored with its address and value. Check locally before calling the node. Once the system has been running a while this is a cache hit most of the time and costs nothing.

2. **`getblock` with verbosity 3.** For recent blocks this returns prevout information including addresses, because the node retains undo data for blocks it still holds. On a pruned node this covers blocks inside the prune window, roughly the last two to three months at 20 GB. **Verify on the node before relying on it:** run `getblock <recent_hash> 3` and confirm the input objects contain a `prevout` field with an address.

3. **Mark it unresolved.** Store the transaction with a null input address and a flag. Never silently drop it and never guess. Track the unresolved rate as a metric and surface it in the interface. A tool that quietly loses data is worse than one that reports its own coverage.

## Address types

| Type | Prefix | Notes |
|---|---|---|
| P2PKH | `1...` | Original format |
| P2SH | `3...` | Script hash, often multisig |
| P2WPKH | `bc1q...` (42 chars) | SegWit v0 |
| P2WSH | `bc1q...` (62 chars) | SegWit v0 script |
| P2TR | `bc1p...` | Taproot |
| P2PK | none | Very early outputs. Raw public key, no address |
| OP_RETURN | none | Data carrier, unspendable, zero value |

Decoders are not written by hand. `gettxout` and `getblock` verbosity 3 both return `scriptPubKey.address` already computed by Bitcoin Core, which is more reliable than any reimplementation. Where script parsing is genuinely needed, `python-bitcoinlib` handles it.

Some outputs are non-standard scripts with no address at all. Null must be handled rather than assumed away.

## Multi-input transactions and the ownership heuristic

A transaction with several inputs carries information. Signing it requires control of the private keys for all of them, so those input addresses are probably controlled by one entity.

This is the **common-input-ownership heuristic**, the foundation of address clustering.

It has a known failure mode. CoinJoin transactions are constructed so that many unrelated parties contribute inputs to one transaction, specifically to defeat it. Applied blindly to a CoinJoin, it merges dozens of unrelated users into one false cluster.

Detection is covered in `06-detection.md`. Cluster logic excludes transactions flagged as CoinJoin.

## Performance

- Bitcoin averages roughly 400,000 to 600,000 transactions a day, around 5 to 7 per second
- Roughly 2 inputs per transaction on average, so 10 to 15 `gettxout` calls per second
- `gettxout` against a local node over the Docker network is sub-millisecond

Comfortably within a single Python process.

Two things that will cause trouble:

**Batch the ClickHouse inserts.** Single-row inserts each create a data part and the merge process falls behind. Buffer in memory and flush at 1,000 rows or 2 seconds, whichever comes first.

**Never block the ingestor on Neo4j.** Graph writes are far slower than columnar writes. A synchronous Neo4j write stalls the mempool subscriber, the ingestor falls behind, and input resolution starts failing as transactions confirm before they are processed. Neo4j writes go to a separate queue and thread.
