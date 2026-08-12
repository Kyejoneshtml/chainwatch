# 04. Ingestion

The central technical problem. Everything else is configuration and query writing.

## Governing principle

> "The interconnectedness of block chain data requires that your indexer be bulletproof and never silently fail. Think of the UTXO set as an unending series of fan-out operations; if you miss a single update then the resulting series of errors can cascade such that your index is eventually corrupted to the point of unusability."
>
> — Jameson Lopp, on building BitGo's indexer, 2015

Every failure is recorded and counted. Nothing is dropped quietly.

## Bitcoin has no accounts

There are no balances. There are only **unspent transaction outputs**.

```
Inputs:                          Outputs:
  (txid_A, vout 1)  ---------->    0.4 BTC to bc1q...xyz
  (txid_B, vout 0)  ---------->    0.6 BTC to bc1q...abc
```

Outputs state their value and locking script; an address derives from the script.

**Inputs are pointers.** Transaction ID plus output index, carrying no address and no amount. Determining the sender requires looking up the output being spent.

## Resolution on a pruned node

A pruned node retains the complete UTXO set. An input to an unconfirmed transaction is by definition unspent — that is what makes the spending transaction valid — so `gettxout` returns it with value and address, regardless of when it was created.

### include_mempool must be false

`gettxout` takes a third argument, `include_mempool`, defaulting to `true`. With it enabled, an output that a **pending** transaction is spending counts as already spent and is excluded.

That is precisely the case the ingestor operates in. Called with the default, resolution returns null every time, with exit code 0 and nothing on stderr.

**An ingestor built without this flag runs indefinitely, reports success, and resolves zero percent of inputs.**

Verified against a live node on 11 August 2026.

## The window

Once a transaction is confirmed, its inputs are spent and leave the UTXO set permanently. Resolution is possible while a transaction sits in the mempool, and not afterwards.

This constraint produces the correct architecture. A monitoring product wants to know about a movement when it is broadcast, not ten minutes later.

## ZeroMQ is a notification, not a source

Bitcoin Core's developers, on the ZMQ interface:

> "ZMQ is not a reliable transport — it does not guarantee you're not missing anything. That means that if you really want to see all transactions, you must additionally rely on RPC anyway."

It is "more useful as a notification mechanism 'there are things you may want to look at' than an authoritative source of information."

**The pattern is push for latency, poll for correctness:**

1. ZMQ notification triggers work
2. RPC retrieves the transaction authoritatively
3. A periodic reconciliation compares the node's full mempool against local state, on a short interval, catching anything the notification stream dropped

This mirrors production practice. electrs, behind Blockstream's Esplora and mempool.space, "is only polled periodically for new blocks and for syncing the mempool."

## Ingestion flow

```
ZMQ rawtx or sequence notification
    |
    v
RPC: getrawtransaction  <- authoritative
    |
    v
Decode. For each input:
    gettxout(prev_txid, prev_vout, include_mempool=false)
    |
    +-- resolved      -> address and value
    +-- parent pending -> recoverable, retry on parent confirmation
    +-- unresolved     -> genuine gap, counted and flagged
    |
    v
Write to ClickHouse, status = 'pending', with block hash = null
    |
    v
Cache all outputs this transaction creates
    |
    v
... ZMQ rawblock / sequence: block connected ...
    |
    v
Update status = 'confirmed', set block height AND block hash
    |
    v
Checkpoint: record last processed block hash
```

## Three-way input resolution

Earlier versions treated resolution as binary. It is not.

**Resolved.** Address and value obtained.

**Parent pending.** The input's parent transaction is itself in the mempool, so the output does not yet exist on the confirmed chain and is absent from the UTXO set under any flag. This is recoverable: once the parent confirms, resolution succeeds. Lopp lists "chaining of multiple unconfirmed outputs" as a distinct failure mode for exactly this reason.

**Unresolved.** Neither of the above. A genuine coverage gap.

Conflating the second and third overstates the problem and hides the real one. They are counted separately and both are surfaced on the status screen.

## Reorganizations

A mined block can be discarded and replaced when a competing chain becomes longer. Lopp reports roughly one reorganization per day on mainnet, and observed testnet reorganizations orphaning chains over 100 blocks long — events that "broke over half of the public block explorers."

Without rollback, the database retains transactions the network has discarded. For a system whose output is evidence about criminal activity, that is the most serious available defect: an alert could fire on a theft that did not happen, and a trace could follow a path that was never real.

### Detection

Two mechanisms, used together.

**Block hash comparison.** Every confirmed row stores the block hash alongside the height. Periodically, verify that the block at the recorded height still has the recorded hash. If it does not, a reorg has occurred.

This is exactly how electrs does it:

> "The index with T prefix mapping txids to block heights now also includes the block hash. This allows for quick reorg-aware transaction confirmation status lookups, by verifying the current block at the recorded height still matches the recorded block hash."

**ZMQ sequence topic.** Publishes block disconnection events directly, giving faster detection. Requires `zmqpubsequence` in the node config.

**Height is never trusted alone.** Height is reused across a reorg; the hash is not.

### Rollback

On detection:

1. Identify all rows with block hashes no longer on the canonical chain
2. Revert those transactions to `pending` or remove them, in reverse order of their position on the orphaned chain
3. Invalidate any alerts derived from them
4. Reprocess transactions from the new canonical chain
5. Update the checkpoint

Alert invalidation matters. If a user was told funds moved and that block was orphaned, they must be told.

### Testing

Reorg handling that cannot be tested cannot be trusted, and waiting for a mainnet reorg is not a test strategy.

A **regtest harness** provides a private Bitcoin network where blocks are mined on command and reorgs can be forced deliberately. Lopp used the same approach, describing a local simulator generating "random transactions, blocks, forks and problematic behaviour" as an invaluable QA mechanism.

Prerequisite for the reorg work. See `08-build-plan.md`.

## Stale transactions

Some transactions are never mined. Lopp's recommendation: periodically check for transactions pending several days and revert them. If later confirmed, they arrive in a block and are reprocessed.

Without this, `pending` rows accumulate indefinitely and any count derived from them drifts.

```
stale_threshold    default 14 days
```

## Dead letter store

Transactions that repeatedly fail processing go to a separate store rather than being retried forever or dropped. Consistent with never failing silently. Reviewed manually; a growing dead letter count is itself a signal.

## Fallbacks for missed transactions

In order:

1. **Local outputs table.** Every ingested output is stored with address and value. Check locally first — a cache hit most of the time once running, at no cost.

2. **`getblock` verbosity 3.** Returns prevout information including addresses for blocks the node still holds, roughly the last two to three months at 20 GB pruning. **Verify on the node before relying on it.**

3. **Mark unresolved.** Store with a null address and a flag. Track the rate as a metric and display it.

## Address types

| Type | Prefix | Notes |
|---|---|---|
| P2PKH | `1...` | Original |
| P2SH | `3...` | Script hash, often multisig |
| P2WPKH | `bc1q...` (42) | SegWit v0 |
| P2WSH | `bc1q...` (62) | SegWit v0 script |
| P2TR | `bc1p...` | Taproot |
| P2PK | none | Early outputs, raw public key |
| OP_RETURN | none | Data carrier, unspendable |

Decoders are not written by hand. `gettxout` and `getblock` verbosity 3 return `scriptPubKey.address` already computed by Bitcoin Core.

Some outputs are non-standard with no address. Null is handled explicitly.

## Dust

Inputs at or near the 546 satoshi dust limit are flagged and excluded from clustering by default.

Dusting attacks send tiny amounts to many addresses; when a recipient spends that dust alongside their own funds, the multi-input heuristic links those addresses. Campaigns have hit hundreds of thousands of addresses. An adversary can poison this system's clustering for a few pounds in fees.

Detail in `14-tracing-adversarial.md`.

## Multi-input transactions

Several inputs in one transaction implies one controlling entity, since signing requires the keys for all of them. This is the **common-input-ownership heuristic**.

Its published error rate is 63.46%. CoinJoin transactions defeat it by design. Transactions flagged as CoinJoin are excluded from clustering, as are dust inputs.

## Performance and reliability

- Roughly 5 to 7 transactions per second network-wide
- Roughly 2 inputs each, so 10 to 15 `gettxout` calls per second
- `gettxout` over the local Docker network is sub-millisecond

Within a single Python process.

**Batch ClickHouse inserts.** 1,000 rows or 2 seconds, whichever first. Single-row inserts create a data part each and trigger `TOO_MANY_PARTS`.

**Never block on Neo4j.** Graph writes are far slower. A synchronous write stalls the mempool subscriber and resolution begins failing.

**Idempotency via natural key.** The txid is the natural key. Retries overwrite rather than duplicate.

**Checkpoint on every flush.** Last processed block hash and last reconciliation timestamp, stored durably.

**Kill-and-restart testing.** The ingestor is killed at random points during processing and the output checked for correctness after recovery. This "exercises checkpoint recovery, offset replay, and partial batch handling simultaneously" and is the most realistic available test.
