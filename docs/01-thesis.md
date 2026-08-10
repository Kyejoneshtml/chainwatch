# 01. Thesis

## The problem

If a bank account is compromised, there is an institution to call, a chargeback mechanism, and a regulated firm with a duty to reimburse. If a Bitcoin wallet is drained, there is nothing. The transaction is final, the ledger is public, and the victim has no practical way to read it.

That last part is the gap. The data is fully public. The illegibility is a tooling problem, not an information problem.

Chainalysis, Elliptic and TRM Labs solve this for institutions at institutional prices. The individual victim is not served, and neither is anyone who wants to see how the analysis was reached rather than take it on trust.

## The product

A watchlist and alerting service for Bitcoin addresses.

1. A user enters a wallet address they care about, typically one that has just been drained
2. The moment funds move from that address, an alert fires. Seconds, not the next day
3. The alert links to a graph showing where the money went and what happened next
4. As funds hop, the trace extends automatically to a configured depth

The closest existing analogy is Have I Been Pwned, but for wallet movement rather than credential leaks.

## Why real time rather than batch

This is the design decision that carries the project.

Laundering happens on a clock. Funds stolen from a hot wallet are typically split, hopped and moved toward an exchange or a mixer within minutes to hours. A batch pipeline that runs nightly reports where the money was, which is a historical record. A streaming pipeline reports where the money is, which is actionable, because exchanges can freeze deposits if they are notified fast enough.

The gap between those two is the value of the product. Batch processing is an archive. Streaming is an intervention.

## The technical position

The system uses both a columnar store and a graph database. The reasoning matters more than the choice.

**ClickHouse answers questions about volume.** It is a columnar store. It scans hundreds of millions of rows and aggregates them quickly. Questions like "which addresses received the most value in the last hour", "what is the transaction velocity of this address against its 30 day baseline", "show every output between 0.99 and 1.01 BTC today" are aggregation questions. They are cheap in a columnar store and expensive in a graph.

**Neo4j answers questions about connection.** Questions like "find every path from this address to a known exchange deposit address within six hops", "which addresses form a tightly connected cluster", "did these two apparently unrelated wallets ever share a common ancestor" are traversal questions. They are natural in Cypher and painful in SQL, because each hop is another join and the query plan degrades badly past three or four.

**The interesting part is the split between them.** ClickHouse determines what is worth looking at. Neo4j explains why. An alert originates from an aggregate signal computed over the full stream in ClickHouse, and when an analyst opens that alert they land in a graph view served from Neo4j showing the specific subgraph.

The consequence is a deliberate asymmetry: **the whole blockchain does not go into Neo4j.** Roughly 500,000 transactions a day produces well over a million address-to-address edges a day. Neo4j can hold that, but it is the wrong use of it. Only the subgraph around watched addresses is materialised, expanded to a configured hop depth. ClickHouse holds everything; Neo4j holds the working set.

The trade-off is real. Arbitrary historical graph queries against addresses nobody has ever watched are not possible without a backfill step. The mitigation is that any subgraph can be reconstructed from ClickHouse on demand, since ClickHouse holds the full edge list. Storage is cheap in the columnar store and expensive in the graph, so the archive lives in the cheap one and the working set in the expensive one.

## Scope

Deliberately excluded:

- No custody. This system never holds funds and has no wallet functionality
- No attribution. Addresses are not linked to real identities. Clustering groups addresses by probable common control, which is a statistically weaker and different claim
- Bitcoin only, initially. Ethereum's account model is a fundamentally different data problem and would double the ingestion work
- No commercial-grade address labelling. Chainalysis and equivalents hold years of proprietary labelled address data that is not publicly available. This is the largest functional gap against a commercial tool and is stated plainly rather than worked around

## Open questions

Recorded here to be answered as the build progresses:

- Which money laundering typologies from traditional payments transfer cleanly to a UTXO ledger, and which do not? Structuring, for instance, depends on a reporting threshold that has no Bitcoin equivalent, while layering maps almost directly
- What false positive rate do the detection rules produce against unlabelled live traffic, and which rules are usable without an exchange address whitelist?
- At what hop depth does subgraph expansion stop being informative and start being noise?
