# 11. Prior art and design corrections

Findings from published accounts of building comparable systems, and the changes they require. Recorded with sources so the reasoning can be checked rather than taken on trust.

Compiled 11 August 2026, before implementation began.

---

## A. Real-time indexing has five failure modes this design did not handle

**Source:** Jameson Lopp, "The Challenges of Blockchain Indexing", 29 May 2015. Written while enhancing BitGo's blockchain indexing service.

Lopp's central point is that processing a static chain and processing a live chain are different problems, and the second is much harder. He lists five events that break naive real-time indexers:

1. Reorganizations
2. Double spends
3. Spending of unconfirmed unspent outputs
4. Chaining of multiple unconfirmed outputs
5. Transactions that never get confirmed

The original ingestion design in `04-ingestion.md` handled none of these.

### A1. Reorganizations

A block that was mined can be discarded and replaced when a competing chain becomes longer. Every transaction in the orphaned block must be rolled back, in reverse order, and the transactions on the new chain processed instead.

Lopp reports roughly one reorganization per day on mainnet, and observed reorganizations orphaning chains over 100 blocks long during testnet block storms. He notes those storms broke over half of the public testnet block explorers, because they were not built to handle the volume of events.

**Consequence for this system:** without rollback, the database retains transactions that no longer exist on the canonical chain. An alert could fire for a theft that did not happen, or a trace could follow a path that was never real. For a tool whose output is used to make judgements about criminal activity, silently retaining invalidated data is the most serious defect available.

**Change:** the ingestor requires a rollback path keyed on block hash, not block height, since height is reused across a reorg.

### A2. Stale unconfirmed transactions

Some transactions are never mined. Lopp's recommendation is to periodically check for unconfirmed transactions pending for several days and revert them, noting that if they are later confirmed they will arrive in a block and be reprocessed.

**Change:** an expiry job. Transactions pending beyond a configurable threshold are reverted rather than left in `pending` indefinitely.

### A3. Chained unconfirmed spends

Mempool transactions frequently spend outputs created by other mempool transactions. Those outputs are not in the UTXO set under any flag, because they do not yet exist on the confirmed chain.

This was observed directly during Phase 0 verification. Forty consecutive resolution attempts returned null. Part of the cause was the `include_mempool` default documented in `04-ingestion.md`; the remainder is this.

**Change:** input resolution must distinguish three outcomes rather than two. Resolved; unresolved because the parent is itself pending, which is recoverable once the parent confirms; and unresolved for any other reason, which is a genuine gap. Conflating the second and third overstates the coverage problem and hides the real one.

### A4. The design principle

Lopp: "The interconnectedness of block chain data requires that your indexer be bulletproof and never silently fail. Think of the UTXO set as an unending series of fan-out operations; if you miss a single update then the resulting series of errors can cascade such that your index is eventually corrupted to the point of unusability."

This is independent confirmation of the lesson from the `include_mempool` discovery, reached ten years earlier at a custody firm. It is now the governing principle for the ingestor.

He also recommends a data store supporting transactions, so that a partial write does not leave a corrupt index. ClickHouse does not offer multi-statement transactions. This is a real trade-off and is mitigated by idempotent writes keyed on txid rather than by rollback.

### A5. Testing method

Lopp built a network simulator using tools from Bitcoin Core's test suite, spinning up several nodes locally in **regtest** mode and generating random transactions, blocks, forks and problematic behaviour. He describes it as an invaluable QA mechanism that let him reproduce rare events locally rather than waiting for them to occur.

Regtest is a private Bitcoin network on a single machine where blocks are mined on command. It permits deliberately triggering a reorg, a double spend, or a chained unconfirmed spend.

**Change:** a regtest harness is added to the build plan as a prerequisite for the reorg handling work. Reorg rollback cannot be verified against mainnet without waiting for an unpredictable event, so it will be tested against a chain we control.

---

## B. ZeroMQ is a notification mechanism, not a data source

**Source:** Bitcoin Core issue #11848, developer response.

The original design treated the ZMQ `rawtx` feed as the ingestion source. Bitcoin Core's own developers state otherwise: ZMQ "is not a reliable transport — it does not guarantee you're not missing anything. That means that if you really want to see all transactions, you must additionally rely on RPC anyway." It is described as "more useful as a notification mechanism 'there are things you may want to look at' than an authoritative source of information."

**Change, three parts:**

1. ZMQ triggers work; RPC confirms it. The notification says a transaction exists, the RPC call retrieves it authoritatively.

2. Add the `sequence` notification topic, which Bitcoin Core provides for ordered mempool additions, removals, and block connections and disconnections. Block **disconnection** is the reorg signal. This was not in the original configuration and `bitcoin.conf` requires `zmqpubsequence`.

3. Add a periodic mempool reconciliation. A published study of Bitcoin transaction fees describes exactly this pattern in practice: a monitor subscribing to the ZMQ rawtx feed while separately recording the node's full mempool state every 25 seconds. Push for latency, poll for correctness.

---

## C. Clustering error rates are far higher than the original doc implied

**Sources:** Meiklejohn, Pomarole, Jordan, Levchenko, McCoy, Voelker and Savage, "A Fistful of Bitcoins", UCSD, 2013 (later in Communications of the ACM, 2016). Subsequent error-rate analysis published in 2022.

The two heuristics in `06-detection.md` originate with this paper. The multi-input heuristic collapsed over 12 million addresses to about four million.

Two corrections follow.

### C1. The original authors were more cautious than we were

Meiklejohn et al. noted that earlier assumptions about change addresses "may have held at the time of their work, but no longer hold at present," and that they "therefore focused on designing the safest heuristic possible, even at the expense of losing some utility."

Meiklejohn has since stated publicly that changes in Bitcoin have made both heuristics less safe than when the research was conducted.

### C2. Published error rates

A 2022 analysis found average error rates of **63.46% for the multi-input heuristic** and **92.66% for the one-time change heuristic**, with the lowest error achieved by applying both together.

`06-detection.md` presented change identification as a ranked list of signals combined into a confidence score. That structure is sound, but the tone implied far more reliability than the literature supports.

**Change:** cite the published error rates directly in the detection doc. For a system whose stated principle is that a heuristic is never presented as a fact, publishing the error rate of the heuristic it depends on is consistent rather than embarrassing.

### C3. The admissibility gap

The same 2022 paper states: "none of the heuristic-based address clustering algorithms have been successfully admitted in court proceedings because they are heuristic in nature. According to the Daubert standard, for an algorithm to be admissible, it should have a known error rate... no address clustering algorithm is able to report an error rate."

This is a documented gap in the commercial category, not a marketing position. A system that reports its own error rates addresses something the incumbents demonstrably do not.

---

## D. The ClickHouse schema has a correctness problem

**Sources:** ClickHouse official documentation on ReplacingMergeTree; Altinity engineering blog; multiple production write-ups.

`05-data-models.md` specifies `ReplacingMergeTree` for the transactions table, so that a confirmed row supersedes the pending row for the same txid. The mechanism does not work the way the doc assumed.

ReplacingMergeTree deduplicates **during background merges**, on ClickHouse's own schedule, not at insert time. Until a merge runs, both rows coexist and queries return both. Reported delays range from seconds to hours.

**Consequence:** a query for a transaction's status could return both `pending` and `confirmed`. For a system that alerts on state changes, that is a correctness failure, not a performance one.

**Changes:**

1. Use a **version column** explicitly. Without one, replacement follows merge order, which is unsafe for update-style workloads. `seen_at` serves this purpose and must be declared.

2. Use `FINAL` on any query where correctness matters. It forces deduplication at read time. It is expensive, and it disables the `PREWHERE` optimisation by default, so it is applied to status queries rather than sprinkled across all analytics.

3. Note the trade-off: ReplacingMergeTree discards previous versions on merge, so historical states are not preserved. If an audit trail of status transitions is ever required, that needs a separate append-only table.

4. Watch for `TOO_MANY_PARTS`. This is the failure mode caused by unbatched inserts, and it is the reason the doc already specifies buffering to 1,000 rows or 2 seconds.

---

## E. The graph model will hit supernodes

**Sources:** Neo4j developer documentation on supernodes; OpenCredo engineering write-up; practitioner reports.

A supernode is a node with very high relationship count, typically 100,000 or more. Bitcoin produces these naturally: exchange hot wallets, mining pool payout addresses, large custodial services.

Reported consequences:

- Traversal through a supernode requires evaluating all its relationships, degrading query performance sharply. One report describes traversals through 10 supernodes approaching a minute each.
- `MERGE` on a relationship locks both source and target nodes for the transaction. On a heavily-connected address receiving continuous writes, this creates contention.
- Community detection algorithms, including the Louvain call specified in `05-data-models.md`, degrade badly on graphs containing supernodes.
- Unbounded variable-length traversal on dense subgraphs "can literally run for hours".

**Changes:**

1. All variable-length Cypher patterns are bounded. `05-data-models.md` already specifies `*1..6`, which is correct and now has a stated reason.

2. Label supernodes separately once identified, so traversals can exclude them explicitly. The standard recommendation is that segregating high-degree nodes by label lets queries opt in or out.

3. Cap by node count as well as hop depth during subgraph materialisation. Already specified; the supernode literature is the justification.

4. A supernode at the *end* of a path is harmless; the cost is in traversing *through* one. Trace queries terminating at an exchange address are therefore acceptable, which happens to be the common case for this product.

---

## F. Wallet addresses may be personal data under UK GDPR

**Sources:** ICO consultation on distributed ledger technologies guidance, 2025; ICO guidance on anonymisation and pseudonymisation, May 2025.

This was not considered at all in the original documents and it affects what the system may lawfully do.

The ICO's position is that online identifiers including wallet addresses and transaction identifiers **may be personal data** under UK GDPR, and that the assessment turns on whether the identifier could be combined with other data to identify an individual.

Critically: **pseudonymous data remains personal data** and stays within scope of the legislation. Only genuinely anonymous data falls outside it. A Bitcoin address is pseudonymous, not anonymous.

The ICO also flags that transferring personal data to recipients outside the UK carries obligations, relevant because blockchain nodes are globally distributed.

**Consequences and changes:**

1. The system's clustering function exists precisely to combine identifiers so as to increase identifiability. That is the activity the ICO describes as bringing data into scope.

2. This strengthens rather than weakens the existing non-goal of attribution in `01-thesis.md`. It now has a legal basis and not only an epistemic one.

3. Before any public deployment, the following are required: a lawful basis for processing, a retention policy, and consideration of whether a Data Protection Impact Assessment is needed. A DPIA is likely given large-scale processing and the risk profile.

4. The watchlist feature stores an email address alongside a wallet address, which is unambiguously personal data regardless of how the wallet address is classified.

**This does not block the build.** It blocks public deployment, which is Phase 7. Recorded now so it is designed for rather than discovered late.

---

## G. What the large platforms do differently

**Sources:** AWS reference architecture for blockchain indexers, 2025; Coinbase engineering on ChainStack.

Worth recording for contrast rather than imitation.

AWS's reference architecture assumes an **archive node**, noting that a full node would require verifying it holds the necessary data. This system runs a pruned node, which is why the `include_mempool` finding was necessary and why the approach is unusual.

They separate **backfill** (historical, parallel, genesis to tip) from **forward-fill** (live, on discovery), and note that reorganizations need no consideration during backfill because historical data is immutable.

This system has forward-fill only. The implication is worth stating plainly: reorganizations are always a live concern here, and none of the simplifications available to backfill apply.

Lopp explains why parallel backfill is difficult regardless: indexing resists parallelisation because of dependencies between inputs and outputs across blocks and within a single block, and workers stall on transactions spending outputs from parents not yet processed.

---

## Summary of changes required before implementation

| # | Change | Affects |
|---|---|---|
| 1 | Reorg detection and rollback, keyed on block hash | `04`, `08` |
| 2 | ZMQ as notification, RPC as source of truth | `04` |
| 3 | Add `zmqpubsequence` topic and reconcile mempool periodically | `03`, `04` |
| 4 | Three-way input resolution outcome | `04` |
| 5 | Stale pending transaction expiry | `04` |
| 6 | Explicit version column and `FINAL` on status queries | `05` |
| 7 | Supernode labelling and bounded traversal rationale | `05` |
| 8 | Publish clustering error rates from the literature | `06` |
| 9 | Regtest harness as prerequisite for reorg work | `08` |
| 10 | GDPR position, DPIA before deployment | `01`, new doc |

Items 1, 2 and 6 are correctness defects. Items 3, 4, 5 and 9 are completeness gaps. Items 7 and 8 are accuracy improvements. Item 10 is a legal prerequisite for deployment.
