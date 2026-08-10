# 04. Ingestion

This is the hard part of the project. It is also the part that will make you sound credible, because it is a problem you only discover by building.

## Bitcoin has no accounts

If you have only worked with bank data this is the mental adjustment. There are no balances and no accounts. There are only **unspent transaction outputs**.

A transaction consumes some existing outputs and creates new ones. A transaction looks like:

```
Inputs:                          Outputs:
  (txid_A, vout 1)  ---------->    0.4 BTC to address bc1q...xyz
  (txid_B, vout 0)  ---------->    0.6 BTC to address bc1q...abc
```

Outputs are easy. Each output states its value and its locking script, and you derive an address from that script. It is all right there.

**Inputs are the problem.** An input is a pointer: transaction ID plus output index. It does not contain an address or an amount. To know who is sending, you must go and look up the output being spent.

This is why "follow the money" is genuinely harder on Bitcoin than it sounds, and it is worth being able to say that out loud.

## Why this collides with pruning

To resolve an input you need the previous transaction. On an archival node with `txindex=1` you would just call `getrawtransaction` on it. On a pruned node that transaction may have been deleted years ago and `txindex` is not available.

At first glance this looks fatal. It is not, and the reason is the single best technical detail in this build.

## The resolution

**The pruned node keeps the complete UTXO set.**

An input to an unconfirmed transaction is, by definition, currently unspent. That is what makes the transaction valid. So it is in the UTXO set. So `gettxout` returns it, including its value and its address, regardless of how old it is.

```
gettxout(txid, vout) -> { value, scriptPubKey: { address, type }, ... }
```

This works on a pruned node for any unspent output, including one created in 2013.

## The catch, and it dictates the architecture

The moment a transaction is **confirmed** in a block, its inputs are spent, and they leave the UTXO set. `gettxout` then returns null.

So there is a window. You can resolve a transaction's inputs while it sits in the mempool. Once it is mined, you cannot.

This is not a bug to work around. It is a constraint that produces the right design.

## Mempool-first ingestion

```
ZMQ rawtx fires (transaction enters mempool)
    |
    v
Decode the raw transaction
    |
    v
For each input: gettxout(prev_txid, prev_vout)
    |            -> gives you sender address and amount
    |            -> DO THIS NOW. The window is open.
    v
Write row to ClickHouse with status = 'pending'
    |
    v
Cache every output this transaction creates, in your own store
    |
    v
... time passes, roughly 10 minutes on average ...
    |
    v
ZMQ rawblock fires (transaction confirmed)
    |
    v
Look the transaction up by txid in your own data. You already have it,
fully resolved, from the mempool stage.
    |
    v
Update status = 'confirmed', set block height and timestamp
```

Notice this is exactly how a real-time monitoring product ought to work anyway. You want to know about a suspicious movement when it is broadcast, not ten minutes later when it is mined. The pruning constraint pushed you toward the correct architecture. That is a good story and it is true, which is better.

## Handling the misses

You will miss transactions. The ingestor will restart, a container will hiccup, and some transactions get mined without ever passing through your mempool view.

Three fallbacks, in order:

1. **Your own outputs table.** Every output you have ever ingested is stored with its address and value. Before calling the node, look locally. This is a cache hit most of the time once you have been running a while, and it costs nothing.

2. **`getblock` with verbosity 3.** For recent blocks, this returns prevout information including addresses, because the node retains undo data for blocks it still holds. On a pruned node this works for blocks inside the prune window, which is your last 20 GB, roughly the last two to three months. **Verify this on your node before relying on it.** Run `bitcoin-cli getblock <recent_hash> 3` and confirm the input objects contain a `prevout` field with an address. If they do not, this fallback is unavailable and you drop to option 3.

3. **Mark it unresolved.** Store the transaction with the input address as null and a flag. Do not silently drop it and do not guess. An analytics tool that quietly loses data is worse than one that admits a gap. Track the unresolved rate as a metric and put it on the dashboard, because knowing your own coverage is exactly the sort of thing that separates a real tool from a demo.

## Address types you will encounter

Bitcoin has accumulated several address formats over the years. Your decoder must handle all of them or your data has holes.

| Type | Prefix | Notes |
|---|---|---|
| P2PKH | `1...` | Original format |
| P2SH | `3...` | Script hash, often multisig |
| P2WPKH | `bc1q...` (42 chars) | SegWit v0 |
| P2WSH | `bc1q...` (62 chars) | SegWit v0 script |
| P2TR | `bc1p...` | Taproot |
| P2PK | none | Very early outputs. Raw public key, no address. Derive one or mark as such |
| OP_RETURN | none | Data carrier, unspendable, zero value |

Do not write the decoders yourself. Use a library. `python-bitcoinlib` or `bitcoinlib` handle script parsing. Even better, note that `gettxout` and `getblock` verbosity 3 give you `scriptPubKey.address` already computed by Bitcoin Core, which is more reliable than anything you would write. Take the address the node gives you.

One thing that will bite you: some outputs are non-standard scripts with no address at all. Handle null. Do not assume every output has an address.

## Multi-input transactions and the ownership heuristic

When you see a transaction with several inputs, you have just learned something valuable. To sign a transaction spending multiple outputs, the sender must control the private keys for all of them. So all those input addresses are probably controlled by one entity.

This is the **common-input-ownership heuristic** and it is the foundation of every address clustering system in the industry.

It has exceptions. CoinJoin transactions are deliberately built so that many unrelated parties contribute inputs to one transaction, specifically to break this heuristic. If you apply it blindly to a CoinJoin you will merge dozens of unrelated users into one false cluster.

Detecting CoinJoins is covered in doc 06. Build the cluster logic so that transactions flagged as CoinJoin are excluded from clustering. Getting this right is a genuinely good thing to be able to talk about, because it shows you understand that these are heuristics with failure modes rather than facts.

## Performance

Rough numbers so you can size things sensibly.

- Bitcoin averages roughly 400,000 to 600,000 transactions a day, so around 5 to 7 per second
- Each transaction has maybe 2 inputs on average, so 10 to 15 `gettxout` calls per second
- `gettxout` on a local node over the Docker network is sub-millisecond

This is comfortably within a single Python process. Do not over-engineer it.

Two things that will actually cause you trouble:

**Batch your ClickHouse inserts.** ClickHouse hates single-row inserts, each one creates a data part and the merge process falls behind. Buffer in memory and flush every 1,000 rows or every 2 seconds, whichever comes first. This is the single most common way people make ClickHouse look slow.

**Never let the ingestor block on Neo4j.** Neo4j writes are much slower than ClickHouse writes. If the watchlist matcher fires and you write synchronously to Neo4j, a slow write stalls your mempool subscriber, you fall behind, and you start missing the input resolution window. Push Neo4j writes onto a separate queue and thread.
