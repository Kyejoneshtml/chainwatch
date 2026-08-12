# 01. Thesis

## The problem

If a bank account is compromised, there is an institution to call, a chargeback mechanism, and a regulated firm with a duty to reimburse. If a Bitcoin wallet is drained, there is none of that. The transaction is final, the ledger is public, and the victim has no practical way to read it.

The data is entirely public. The illegibility is a tooling problem.

## What already exists, and what does not

An earlier version of this document claimed nobody serves the individual victim. That was wrong and is corrected here.

Free Bitcoin address monitoring with email alerts is available from several established providers, including Blockonomics, Bitcoinwhoswho, WalletWhitePages and Cryptocurrency Alerting. The last is a mature commercial product with a REST API, webhooks and multi-chain coverage. **Basic alerting is a commodity.**

What none of them provide:

- Tracing where funds went after they moved, rather than only notifying that they moved
- Laundering pattern detection
- Explained risk assessment with stated error rates
- Any output oriented toward what the victim should do next

At the other end, Chainalysis, Elliptic and TRM Labs serve institutions at institutional prices, and their methods are closed.

## What actually recovers stolen funds in the UK

This determines the product, so it is stated precisely.

Funds are frozen by **Crypto Wallet Freezing Orders** under the Proceeds of Crime Act 2002, obtained by law enforcement, requiring exchanges to freeze deposit addresses identified as receiving misappropriated assets. A victim may then apply for release of the funds.

The constraint is not detection speed. Practitioner guidance is blunt that law enforcement cannot investigate every referral, "such is the scale of this problem." The recommended response is that a victim conducts their own tracing, then packages the investigation and provides it to police to support an application for a freezing order.

Compounding this: only **2% to 15% of fraud victims report at all**. The barriers are psychological rather than practical — shame, self-blame, secondary victimisation by family and community, and a belief that authorities will not act. Some victims feel they do not deserve to recover their money.

## The product

**A tool that produces evidence a victim can act on.**

1. A watched address is monitored continuously
2. Movement produces an alert within seconds
3. Funds are traced through subsequent hops using a defined methodology
4. The output is a report formatted for submission to police

The report is the product. The alerting is how the evidence is gathered.

This addresses the real constraint. A person arriving at Action Fraud with a completed trace is not narrating their own mistake; they are presenting documented evidence of a crime. That is a materially different encounter, and it may be what makes reporting possible at all.

## Tracing methodology

The system uses **FIFO** — first in, first out — to determine which outputs carry stolen funds when they mix with clean funds.

This is not a technical preference. It is the rule English law already applies to mixed funds, established in **Clayton's Case (1816)** and still in force across the UK and much of the Commonwealth. For a product whose output is intended for UK police, using the tracing rule English law itself uses is the strongest available position.

It is also technically superior. FIFO is lossless, so provenance can be traced backwards as well as forwards. The alternatives fail badly: Cambridge researchers applying poison and haircut methods to real 2014 thefts found that by 2017 more than 90% of active wallets were tainted, which makes the result meaningless.

Most commercial tools use haircut, which suits risk scoring. This system produces evidence, which is a different job.

Full treatment, including the transaction fee problem and honest criticisms, in `14-tracing-adversarial.md`.

## Why real time

Laundering runs on a clock. Stolen funds are typically split, hopped and moved toward an exchange within minutes to hours. A nightly batch produces a historical record; a live stream produces something actionable while the trail is still warm.

## Technical position

The system uses a columnar store for aggregate analysis and a graph database for traversal.

**ClickHouse** answers questions about volume: totals, rates, distributions, baselines. **Neo4j** answers questions about connection: paths, clusters, common ancestors. ClickHouse determines what merits attention; the graph explains why.

The graph holds only materialised subgraphs around watched addresses, capped by node count and hop depth. ClickHouse holds everything.

**This choice is provisional.** The BlockSci paper from Princeton argues that an in-memory analytical database is "orders of magnitudes faster than using general-purpose graph databases" for blockchain analysis. That criticism targets whole-chain workloads rather than bounded subgraph traversal, but the difference will be measured rather than assumed. See `13-engineering-practice.md`.

## Scope

Excluded deliberately:

- **No custody.** The system never holds funds
- **No attribution.** No identity claims, no public database of address labels, no payment for identifying information. Clustering groups addresses by probable common control, which is a weaker and different claim
- **Bitcoin only initially.** Ethereum's account model is a different data problem
- **No commercial-grade labelling.** Years of proprietary labelled address data are not obtainable. This is the largest functional gap and is stated rather than obscured

The attribution exclusion has three justifications. It is epistemically honest. It is legally safer, since the ICO's position is that wallet addresses may constitute personal data and pseudonymous data remains in scope of UK GDPR. And it avoids a documented reputational failure: Arkham Intelligence's paid deanonymisation marketplace drew criticism that incorrect labelling "could lead to false accusations of money laundering."

## Obligations to the accused

A system that produces evidence about a person has obligations toward that person, including when it is wrong.

The forensic standards literature identifies two interests: that tools produce court-admissible evidence or reasonable suspicion, and that outcomes "comply with general legal standards and in particular preserve the fair trial rights of the accused."

Practically this means every inference carries a stated confidence level, heuristics are never presented as facts, published error rates are cited, and reports record what they were derived from and when.

## Regulatory position

Provisionally, no FCA registration is required. The Money Laundering Regulations registration regime covers exchange, custody and similar activities under Regulation 14A; analytics and tracing are not listed. This is not legal advice and requires confirmation before commercial operation.

The Financial Services and Markets Act 2000 (Cryptoassets) Regulations 2026 were made on 4 February 2026, with the new regime expected in force on 25 October 2027. Scope should be rechecked before then.

## Open questions

1. Which money laundering typologies transfer from traditional payments to a UTXO ledger, and which do not? Layering maps directly; structuring does not, because there is no reporting threshold to structure below
2. What false positive rate do the detection rules produce against unlabelled live traffic?
3. At what hop depth does subgraph expansion stop being informative?
4. **Who is the primary user — the victim, or the person recovering funds on their behalf?** This determines the shape of the interface and is unresolved
5. Would Action Fraud or a UK police force accept a report generated by an automated tool, and in what format?
