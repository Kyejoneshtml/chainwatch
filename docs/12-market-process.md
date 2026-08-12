# 12. Market and process research

Findings on what already exists, how stolen funds are actually recovered in the UK, how comparable systems handle the hard problems, and which data sources are usable.

Compiled 11 August 2026.

This document contains the most consequential finding in the project so far. It is in section B.

---

## A. The alerting product already exists, repeatedly, and free

The original premise in `01-thesis.md` was that nobody serves the individual victim. That premise is wrong as stated.

Existing services offering Bitcoin address monitoring with alerts:

| Service | Notes |
|---|---|
| Blockonomics | Watch any BTC address, email on activity. Free |
| Bitcoinwhoswho | Email notifications on transactions to or from any address. Free with signup |
| Cryptocurrency Alerting | Nine notification methods including email, SMS, webhook, Telegram, Discord, automated phone calls. Free tier, paid from $19.99/month |
| WalletWhitePages | Free for up to 5 wallets. Alerts on new identity links, scam reports, sanctions and risk signals |
| Check Crypto Address | Real-time monitoring, incoming and outgoing, balance changes |

Cryptocurrency Alerting in particular is a mature commercial product with a REST API, webhook support, bulk address import and multi-chain coverage.

**The bare alerting feature is not a differentiator.** It is a commodity, available free, from several established providers.

This does not invalidate the project, but it does invalidate the pitch. What none of these offer, as far as their published material shows:

- Tracing where funds went after they moved, as opposed to notifying that they moved
- Laundering pattern detection: peel chains, fan-in consolidation, dormancy breaks
- Explained risk scoring with contributing factors and stated error rates
- Anything oriented toward what the victim should do next

The differentiator is what happens *after* the alert. Section B explains why that matters more than expected.

---

## B. How stolen crypto is actually recovered in the UK

**Sources:** Proceeds of Crime Act 2002 practitioner guidance; UK law firms specialising in crypto asset recovery; Action Fraud reporting guidance.

This changes the product.

### The mechanism that actually freezes funds

Law enforcement holds powers under the **Proceeds of Crime Act 2002** to obtain **Crypto Wallet Freezing Orders**, which require exchanges to freeze deposit addresses identified as receiving misappropriated assets. A victim can then apply for release of the funds back to them.

So funds are frozen by a court order obtained by police, not by an exchange acting on a victim's email. The original assumption in `01-thesis.md` — that exchanges can freeze deposits if notified fast enough — is at best incomplete.

### The bottleneck is not detection speed

Practitioner guidance states the position plainly: while law enforcement capability is increasing, "it is simply impossible for them to investigate every instance that is referred to them, such is the scale of this problem."

The recommended response is the important part:

> "it can be of assistance for a victim to conduct their own investigations, including tracing the stolen assets, identifying the owners of the deposit addresses that received the stolen funds... At this stage, a victim can then 'package up' their investigation and provide it to the police to assist them in their ability to commence their own investigation, with a view to obtaining a Crypto Wallet Freezing Order."

A victim who arrives at Action Fraud with a completed trace is materially more likely to get action than one who arrives with a wallet address and a story.

### What that means for this product

The output of the system should not only be an alert. It should be **a report the victim can hand to police**.

That is a different deliverable with the same infrastructure underneath:

- A timeline of movements with timestamps and transaction IDs
- The trace path with each hop evidenced
- Destination addresses, flagged where they appear to be exchange deposits
- Confidence levels on every inference, stated explicitly
- Formatted for someone who is not a blockchain analyst

This is also **more defensible commercially**. Nobody in section A produces this. And it aligns with the explainability thesis: a report that shows its working is precisely what an investigator or a court needs, and precisely what the clustering literature says the incumbents cannot provide.

### Supporting observations

- Commercial tracing reports already exist as a paid service from UK law firms, with one firm claiming to have traced over £100 million and describing tracing 107 BTC through more than 40 wallets to a Binance destination. That establishes both the value of the output and the price point being charged.
- Case law supports the approach. *Ion Science Ltd v Persons Unknown* [2020] saw the High Court grant proprietary and worldwide freezing injunctions over stolen Bitcoin, with commentary noting courts respond "particularly when victims act quickly and with legal precision."
- Exchanges hold KYC records on account holders, which is why disclosure orders against exchanges are a standard step.

### The safeguarding point, reinforced

Multiple sources independently confirm that **victims of crypto fraud are specifically targeted a second time** by criminals posing as recovery specialists, law enforcement, or regulatory officials, who charge fees or extract sensitive information.

This validates the earlier decision to put no payment mechanism on the site, and makes the anti-recovery-scam warning a required feature rather than a nice addition.

---

## C. How production indexers handle reorganizations

**Source:** electrs, the index engine behind Blockstream's Esplora and mempool.space.

Their documented approach:

> "The index with T prefix mapping txids to block heights now also includes the block hash. This allows for quick reorg-aware transaction confirmation status lookups, by verifying the current block at the recorded height still matches the recorded block hash."

This is independent confirmation of the approach proposed in `11-prior-art.md`. Store the block hash alongside the height; on each check, verify the block at that height still has the expected hash. If it does not, a reorg has occurred and the affected rows are invalid.

Simple, cheap, and it requires no reorg notification to work, though the ZMQ `sequence` topic makes detection faster.

Two further observations from electrs:

**They poll rather than rely on push.** Their design "no longer queries bitcoind to serve user requests and is only polled periodically for new blocks and for syncing the mempool." Consistent with the finding in `11-prior-art.md` that ZMQ is a notification mechanism rather than a data source.

**Full indexing is enormous.** electrs indexes require 250GB to 300GB in Blockstream's build, and 1.3TB in the mempool.space fork as of October 2023, with roughly double that needed during index compaction.

This validates the decision in `01-thesis.md` to index forward from ingestion start rather than backfill history, and to materialise only watched subgraphs into Neo4j. Full historical indexing is not feasible on the available hardware and was never the plan.

**They offer a prevout toggle.** electrs has a `--disable-prevout` option that skips attaching previous output information to inputs, described as significantly reducing transaction lookups and IO, CPU and memory usage, at the cost of not knowing input amounts and previous addresses.

That confirms input resolution is the expensive part of indexing. It is also exactly the data this system cannot do without, so the cost is unavoidable here.

---

## D. The OFAC sanctions list is usable

**Sources:** OFAC FAQ 563 and 594; open source extraction tools.

`06-detection.md` rule 9 depends on labelled address data and flags OFAC as a partial source. Verified as workable.

**Format is documented and stable.** Per OFAC FAQ 563, each digital currency address on the SDN List has its own field, always beginning with "Digital Currency Address", followed by a dash and the currency symbol, then the address. Bitcoin is `XBT`.

**Machine-readable download exists.** `sdn_advanced.xml`, roughly 80MB.

**Extraction is a solved problem.** The repository `0xB10C/ofac-sanctioned-digital-currency-addresses` extracts addresses per asset and publishes automatically updated lists regenerated nightly at 00:00 UTC by a scheduled workflow.

**Practical route:** consume the pre-extracted list rather than parsing the XML. Verify against the official source periodically rather than trusting a third party blindly.

**Scale caveat.** The list is small. It covers sanctioned entities, not the general population of exchange or mixer addresses. It closes a fraction of the labelling gap described in `06-detection.md` and does not change the overall position.

---

## Changes required

| # | Change | Affects |
|---|---|---|
| 11 | Correct the premise: free alerting services already exist. Differentiator is trace, detection and report | `01` |
| 12 | Add the police-ready report as a primary output, not a secondary feature | `01`, `07` |
| 13 | Correct the freezing mechanism: Crypto Wallet Freezing Orders under PoCA 2002, obtained by police | `01` |
| 14 | Anti-recovery-scam warning becomes a required feature | `07` |
| 15 | Reorg detection via stored block hash, per electrs | `04`, `05` |
| 16 | OFAC ingestion via the nightly-updated extracted list | `06` |

Item 12 is the significant one. It changes what the product is for: not "you have been robbed, here is an alert," but "you have been robbed, here is the evidence pack to take to Action Fraud."

---

## Open questions this raises

Recorded rather than answered.

1. Would Action Fraud or a UK police force actually accept a report generated by an automated tool, and in what format?
2. Does producing tracing reports for others carry any regulated-activity implications?
3. If the report becomes the product, does the real user become the solicitor or investigator rather than the victim?
4. What is the minimum evidentiary standard for a Crypto Wallet Freezing Order application?

Question 1 is answerable by asking. That is a customer discovery task, not a research task.
