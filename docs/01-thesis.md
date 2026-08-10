# 01. Thesis

## The problem

If your bank account is compromised, there is an institution to call, a chargeback mechanism, and a regulated firm with a duty to reimburse. If your Bitcoin wallet is drained, there is nothing. The transaction is final, the ledger is public, and you personally have no practical way to read it.

That last part is the gap. The data is fully public. The illegibility is a tooling problem, not an information problem.

Chainalysis, Elliptic and TRM Labs solve this for institutions at institutional prices. Nobody solves it for the individual victim, and nobody solves it in a way that shows their working.

## The product

A watchlist and alerting service for Bitcoin addresses.

1. A user enters a wallet address they care about, typically one that has just been drained
2. The moment funds move from that address, an alert fires. Seconds, not the next day
3. The alert links to a graph showing where the money went and what happened next
4. As funds hop, the trace extends automatically to a configured depth

Michael's framing was "Have I Been Pwned, but for crypto wallets." That is the right analogy and worth using directly. It communicates the whole product in five words.

## Why real time rather than batch

This is the design decision that carries the project, so be able to defend it.

Laundering happens on a clock. Funds stolen from a hot wallet are typically split, hopped and moved toward an exchange or a mixer within minutes to hours. A batch pipeline that runs nightly tells you where the money was, which is a historical record. A streaming pipeline tells you where the money is, which is actionable, because exchanges can freeze deposits if they are told fast enough.

The gap between those two is the entire value of the product. Batch processing is an archive. Streaming is an intervention.

## The technical opinion

Michael's specific advice was to run both ClickHouse and Neo4j and build something that blends them. The opinion worth articulating is *why* rather than just *that*.

**ClickHouse answers questions about volume.** It is a columnar store. It scans hundreds of millions of rows and aggregates them fast. Questions like "which addresses received the most value in the last hour", "what is the transaction velocity of this address versus its 30 day baseline", "show me every output between 0.99 and 1.01 BTC today" are aggregation questions. They are cheap in ClickHouse and expensive in a graph.

**Neo4j answers questions about connection.** Questions like "find every path from this address to a known exchange deposit address within six hops", "which addresses form a tightly connected cluster", "did these two supposedly unrelated wallets ever share a common ancestor" are traversal questions. They are natural in Cypher and painful in SQL, because each hop is another join and the query plan degrades badly past three or four.

**The blend is the interesting part.** ClickHouse decides what is worth looking at. Neo4j explains why. An alert originates from an aggregate signal computed over the full stream in ClickHouse, and when the analyst clicks the alert, they land in a graph view served from Neo4j showing the specific subgraph.

The consequence, and this is the design decision people will push on: **do not put the whole blockchain in Neo4j.** Roughly 500,000 transactions a day means well over a million address-to-address edges a day. Neo4j can hold that but it is the wrong use of it. Materialise into Neo4j only the subgraph around watched addresses, expanded to a configured hop depth. ClickHouse holds everything, Neo4j holds what matters.

If someone challenges this in an interview, the honest answer is that it is a trade-off: you lose the ability to run arbitrary historical graph queries on addresses nobody has ever watched. The counter is that you can backfill any subgraph from ClickHouse on demand, because ClickHouse has the full edge list. Storage is cheap in ClickHouse and expensive in Neo4j, so put the archive in the cheap store and the working set in the expensive one.

## What this is really for

Two things, in this order.

**Demonstrable competence.** A dissertation proves you can analyse. This proves you can build. Michael was blunt about the difference and he is right. The interview conversations this unlocks, about UTXO modelling, about why a graph database and a columnar store answer different questions, about the mempool race condition in section 04, are conversations you cannot have from reading alone.

**A public artefact.** The repository, the doc revisions and a short write-up series are the evidence. Someone can look at the commit history and see how you thought.

Do not over-claim. This is a portfolio project, not a product with users. Say so. Overstating it is the fastest way to lose credibility with anyone who actually works in this space, and understating a genuinely good build costs you nothing.

## Non-goals

Worth writing down so you do not drift.

- Not building an exchange, wallet, or anything that custodies funds
- Not doing attribution. You will not name real people. Address clustering is a statistical heuristic, not an identification
- Not covering other chains initially. Bitcoin only. Ethereum's account model is a completely different data problem and adding it early will sink the schedule
- Not achieving Chainalysis coverage. They have years of labelled address data you do not have and cannot get
