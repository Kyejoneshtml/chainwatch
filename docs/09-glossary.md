# 09. Glossary

Every term used across these documents. No assumed knowledge.

## Bitcoin

**UTXO** — Unspent Transaction Output. Bitcoin's unit of value. Not a balance, an unspent output waiting to be consumed.

**Outpoint** — A pointer to a specific output: transaction ID plus output index. What an input contains.

**vin / vout** — Index of an input or output within a transaction. The first output is vout 0.

**Satoshi** — Smallest unit. 100,000,000 to one BTC. Amounts are always stored as integer satoshis.

**Mempool** — Valid transactions broadcast but not yet mined. Where transactions are caught live.

**Confirmation** — Blocks mined on top of the block containing a transaction. Zero means still in the mempool.

**Coinbase transaction** — The first transaction in a block, creating new bitcoin for the miner. No real inputs; a special case in input resolution.

**scriptPubKey** — The locking script on an output. Addresses derive from it. Some scripts have no address.

**Change output** — When a UTXO larger than the payment is spent, the remainder returns to the sender as a new output.

**CoinJoin** — A transaction combining inputs from unrelated parties to defeat clustering. A deliberate privacy technique.

**Peel chain** — Laundering pattern where a large sum repeatedly sheds small amounts while the bulk moves on.

**Dust** — An output so small the fee to spend it approaches or exceeds its value. Bitcoin's dust limit is 546 satoshis for most output types.

**Dusting attack** — Sending dust to many addresses so that when recipients spend it alongside their own funds, the multi-input heuristic falsely links their addresses.

**Address poisoning** — Generating a vanity address resembling one a victim uses, then sending a near-zero transaction so the lookalike appears in their history, hoping they later copy the wrong one.

**Reorganization (reorg)** — A mined block discarded and replaced when a competing chain becomes longer. Roughly one per day on mainnet.

**Orphaned block** — A block no longer on the canonical chain after a reorg.

**Chain split / fork** — When parts of the network follow different rules and diverge onto separate chains. One occurred on 8 August 2026 over BIP-110.

**IBD** — Initial Block Download. First sync from genesis to tip.

**Pruning** — Deleting validated block files after processing while retaining the UTXO set.

**Chainstate** — Bitcoin Core's database of the complete UTXO set. Not pruned. The reason this project works.

**txindex** — Optional index allowing lookup of any transaction by ID. Incompatible with pruning.

**include_mempool** — Third argument to `gettxout`, defaulting to true. When true, outputs being spent by pending transactions are excluded. Must be false for this system's input resolution.

**Regtest** — A private Bitcoin network mode where blocks are mined on command. Used for testing reorg handling deliberately.

**SegWit** — Segregated Witness, 2017 upgrade. Produced the `bc1q` address format.

**Taproot** — 2021 upgrade. Produced the `bc1p` address format.

**RBF** — Replace-By-Fee. Signalling that a transaction may be replaced by a higher-fee version. Part of the behavioural fingerprint in detection rule 5.

**OP_RETURN** — An output type carrying arbitrary data, unspendable. Bitcoin Core v30 removed the 80-byte cap.

**ZeroMQ / ZMQ** — Messaging library Bitcoin Core uses to push notifications. **Not a reliable transport**; a notification mechanism rather than a data source.

**sequence topic** — ZMQ topic publishing ordered mempool additions, removals, and block connections and disconnections. The reorg signal.

**RPC** — Remote Procedure Call. Bitcoin Core's request-response interface. The authoritative source in this system.

## Tracing

**Taint** — The property of an output being traceable to a particular earlier source, typically a theft.

**Poison method** — Any transaction with a tainted input produces entirely tainted outputs. Causes rapid diffusion; unusable.

**Haircut method** — Taint distributed proportionally across outputs. Used by most commercial tools. Also diffuses badly: over 90% of active wallets tainted by 2017 in one study.

**FIFO** — First in, first out. Inputs fund outputs in order. Lossless and backward-traceable. **The method used by this system.**

**Clayton's Case (1816)** — English legal precedent establishing FIFO for tracing mixed funds through an account. Still in force across the UK and much of the Commonwealth.

**LIFO / TIHO** — Last in first out; Taint In Highest Out. Alternative methods described in the literature.

## Databases

**Columnar store** — Stores data by column. Excellent for aggregation across many rows, poor for fetching whole individual records. ClickHouse.

**Graph database** — Stores nodes and relationships with direct pointers. Excellent for traversal, poor for aggregation. Neo4j.

**MergeTree** — ClickHouse's main table engine family.

**ReplacingMergeTree** — Discards older duplicate rows on the sorting key **during background merges**, not on insert. Until a merge runs, both rows are visible.

**FINAL** — ClickHouse query modifier forcing deduplication at read time. Expensive; disables `PREWHERE` optimisation by default.

**Version column** — Explicitly declared column determining which duplicate wins. Without one, replacement follows merge order, which is unsafe.

**TOO_MANY_PARTS** — ClickHouse error caused by unbatched inserts creating too many data parts.

**AggregatingMergeTree** — Combines rows with aggregate functions during merges.

**Ordering key** — Physical sort order on disk. The most important ClickHouse schema decision.

**Materialised view** — In ClickHouse, an insert trigger writing derived rows. Different from a Postgres materialised view.

**Cypher** — Neo4j's query language. Pattern syntax: `(a)-[:SENT_TO]->(b)`.

**MERGE** — Cypher operation meaning create if absent, match if present. Locks both endpoints; requires a uniqueness constraint or it does a full scan.

**Variable-length path** — Cypher's `*1..6` syntax. The core tracing capability. Always bounded.

**Supernode** — A node with very high relationship count, typically 100,000 or more. Exchange hot wallets and mining pools. Traversal *through* one is expensive; terminating *at* one is not.

**Louvain** — Community detection algorithm. Degrades badly on graphs containing supernodes.

## Engineering

**Idempotency** — The property that repeating an operation produces the same result. Achieved here through the txid as natural key.

**Natural key** — A key derived from the data itself rather than generated. The txid. Without one, every retry creates a new row.

**At-least-once delivery** — Guarantees nothing is lost but permits duplicates. Sufficient when paired with idempotent writes.

**Checkpoint** — Durable record of processing position, allowing restart to resume rather than restart.

**Dead letter store** — Where repeatedly failing items go for inspection, rather than infinite retry or silent loss.

**Kill-and-restart test** — Killing a process at random points and verifying correctness after recovery. Exercises checkpoint recovery, replay and partial batch handling at once.

**Shadow rule** — A detection rule running silently against live traffic, recording what it would have alerted on, so its false positive rate can be measured before it is enabled.

**Suppression logic** — Excluding known recurring benign patterns from alerting. Absent suppression is a named cause of high false positive rates.

**Peer group benchmarking** — Comparing an entity against similar entities rather than only against its own history.

## Infrastructure

**Docker** — Runs each service in an isolated container with its own dependencies.

**Docker Compose** — Defines multiple containers in one file. `docker compose up` starts everything.

**Volume** — Persistent storage surviving container restarts.

**Bind mount** — Maps a host directory into a container. Used for bitcoind data so disk usage is visible.

## Financial crime and law

**AML** — Anti-Money Laundering.

**KYC** — Know Your Customer. Largely absent from Bitcoin at the protocol level.

**APP fraud** — Authorised Push Payment fraud. The victim is deceived into sending the payment themselves.

**Typology** — A recognised pattern of criminal behaviour.

**Structuring** — Breaking a transfer into amounts below a reporting threshold. Does not transfer to Bitcoin, which has no such threshold.

**Layering** — Moving funds repeatedly to obscure origin. Transfers directly.

**False positive** — An alert that turns out to be legitimate activity. The dominant operational cost. Industry rates reach 95%.

**Attribution** — Linking an address to a real identity. Explicitly out of scope.

**Clustering** — Grouping addresses by probable common control. A statistical claim, not an identification. Published error rate 63.46% for multi-input.

**PoCA 2002** — Proceeds of Crime Act 2002. The UK statute under which crypto assets are frozen.

**Crypto Wallet Freezing Order** — Court order under PoCA requiring an exchange to freeze a deposit address. Obtained by law enforcement, not by victim request.

**Action Fraud** — The UK's national reporting centre for fraud and cybercrime.

**Daubert standard** — US admissibility test for expert evidence, requiring among other things a known error rate. No address clustering algorithm currently meets it.

**Secondary victimisation** — Blame directed at a victim by family, friends, professionals or the wider community. A major cause of underreporting.

**DPIA** — Data Protection Impact Assessment. Likely required before public deployment.

**Trauma-informed design** — Design practice for interfaces used by people in distress. The governing UI principle here: relief, not delight.
