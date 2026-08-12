# 14. Tracing methodology and adversarial conditions

Findings on questions the earlier documents did not ask. One of these is a fundamental methodological gap: the system claims to trace stolen funds but never defines what "the stolen funds" means once they mix with other money.

Compiled 11 August 2026.

---

## A. The trace feature has no defined methodology

This is the largest gap found so far.

`01-thesis.md` promises to show "where the money went". `05-data-models.md` specifies graph traversal to find paths. Neither addresses the question that makes tracing hard.

**When 1 stolen BTC is combined with 9 clean BTC and then split into outputs of 6 and 4, which output contains the stolen money?**

Bitcoin's protocol does not answer this. It records that ten coins went in and ten came out. The mapping is not stored anywhere because it does not exist at the protocol level. Any answer is a rule imposed from outside.

There are three established rules, and they give different answers.

### The three methods

**Poison.** Any transaction with a tainted input produces entirely tainted outputs. In the example, both outputs are fully stolen.

**Haircut.** Taint is distributed proportionally. 1/10 of the inputs were tainted, so the 6 BTC output carries 0.6 tainted and the 4 BTC output carries 0.4.

**FIFO.** First in, first out. Inputs fund outputs in order until depleted. The first output receives the first coins in, so taint attaches to specific satoshis rather than being spread as a percentage.

### Why poison and haircut fail

Cambridge researchers ran both against real thefts from 2014 and found that **by 2017 more than 90% of wallets active on the network were tainted.**

Their conclusion on what that means practically:

> "This diffusion prevents any sensible recourse for victims – if we were to recover the 9% of stolen bitcoin and refund the victims, we might as well levy a 9% tax on all users. That is politically and technically impractical."

A method that eventually marks almost everything is not a method. It is noise.

### Why FIFO matters specifically for a UK product

FIFO is not an arbitrary technical preference. It is the rule English law already uses for exactly this problem.

Anderson et al. proceed from **Clayton's Case (1816)**, in which the High Court had to decide how to track money through the accounts of a failed bank. The ruling: funds whose ownership is disputed are tracked first-in, first-out. The first penny in satisfies the first withdrawal.

The precedent is described as in force throughout the UK, Canada and many other Commonwealth countries.

Its technical properties are also better. FIFO is **lossless**, so unlike haircut a coin can be traced backwards as well as forwards, all the way to the block in which its component satoshis were created.

Summarised by one of the authors: "It's not just good law; it's good computer science too."

### The industry does something else

Most chain analysis firms use haircut, aligning with risk-based AML frameworks where the goal is risk assessment rather than absolute attribution.

That is a defensible choice for a compliance product asking "how risky is this counterparty". It is the wrong choice for an evidence product asking "where did this specific victim's money go", and this system is now the second kind, per `12-market-process.md`.

### Change

**Adopt FIFO as the tracing methodology, and state the reasoning.**

This is arguably the single strongest decision available to this project:

- It is the method with UK legal precedent behind it, in a product designed to produce reports for UK police
- It is technically superior, being lossless and reversible
- It differs from what most commercial tools do, and the difference can be justified from first principles
- It suits an evidence product rather than a risk-scoring product

Implementation is non-trivial. The Cambridge write-up notes the difficulty: "The tricky bit is the handling of transaction fees but once that's done, we can track the provenance of any satoshi."

There are also honest criticisms to record. Commentary on the original work notes that tracing rules exist because property is not uniquely identifiable, that FIFO ordering is itself arbitrary, and that taint tracking sits uneasily with fungibility, since cash is not treated as tainted by its history. A published survey adds that FIFO "cannot handle the accuracy problem since the order may be inaccurate in some cases."

Variants exist. The same literature describes LIFO and TIHO (Taint In Highest Out) methods, and finds that combining tainting with address profiling improves accuracy.

**Change:** add `docs/15-taint-methodology.md` specifying FIFO, the legal basis, the fee handling problem, and the stated limitations.

---

## B. The system can be attacked

None of the earlier documents consider that an adversary might manipulate the data the system reads. Both major techniques are documented and active.

### Dusting attacks

An attacker sends tiny amounts to many addresses. If a recipient later spends that dust alongside their own funds, the multi-input heuristic links those addresses together. The attacker learns which addresses share an owner.

Scale is real. Samourai Wallet alerted users to a campaign sending 546 satoshi transactions, exactly at the dust limit, to thousands of Bitcoin addresses in bulk, and responded by adding a "Do Not Spend" feature. A single campaign hit over 294,000 Litecoin addresses in one day.

Economics govern frequency. Lopp notes this kind of spray-and-pray dusting "is only economically feasible during low fee environments... It can make sense at 1 sat/vb fees but at 100 sat/vb it becomes egregiously expensive."

**Why this matters here.** Chainwatch's clustering can be poisoned. An attacker who dusts a victim's address, then arranges for that dust to be spent alongside other coins, causes the system to draw a false link. The consequence is a trace that leads somewhere wrong, in a report intended for police.

**Changes:**
1. Flag dust-value inputs, at or near the 546 satoshi limit, and exclude them from clustering by default
2. Where a cluster link depends on a dust input, mark the link low confidence and say so
3. Surface dust inputs to users watching an address, with the advice not to spend them

The third turns a defensive measure into a user-facing feature, and it is genuinely useful safety advice.

### Address poisoning

Different attack, similar family. The attacker generates a vanity address closely resembling one the victim uses, typically matching four or five characters at each end, then sends a zero or near-zero value transaction so the lookalike appears in the victim's history. The hope is that the victim later copies the wrong address.

Lopp documented a real success: address `bc1qr9wuw4zkjflet80lr9cr5ec8620c4fg52wua0h` fooled `bc1qr9xkxanfstzqpfd5ce0t3evwc45pnmsr2wua0h` into sending 0.1 BTC.

Look at those two strings. They share the first ten characters and the last six.

**This is a direct validation of a design decision already taken.** `10-design-system.md` specifies that addresses truncate in the *middle*, never at the end, because both ends matter for visual verification. Address poisoning is precisely the attack that exploits truncation. The decision was correct and now has a documented threat behind it.

**Changes:**
1. Detect near-identical addresses in a watched address's history and warn explicitly
2. Never truncate in a way that hides the differing portion of two similar addresses
3. Where two addresses in one view are visually similar, highlight the differing characters

---

## C. The reputational risk is real and documented

**Source:** coverage of Arkham Intelligence, 2023.

Arkham launched a platform to deanonymise blockchain addresses, including a marketplace paying bounties for identifying information. The reaction is instructive for anyone building in this space.

Criticism included that "incorrect labeling in Arkham's public database could lead to false accusations of money laundering and other crimes," and a claim from a privacy technologist that the platform "almost certainly violates the European Union's General Data Protection Regulation." One critic called the project "utterly disgraceful" and said it "should be publicly disowned by the entire crypto community."

Arkham's defence was scale: over 350 million labels, and users who "already trust us to provide correct labels."

**What this project should take from it.**

The GDPR concern is the same one identified in `11-prior-art.md` from ICO guidance. Independent confirmation that this is a live risk, not a hypothetical.

More importantly, the reputational failure mode is specific: **publishing identity labels, and paying for them, is what drew the reaction.** This project's existing non-goal of attribution in `01-thesis.md` avoids it directly.

**Change:** state explicitly that Chainwatch produces no public database of address labels, pays nobody for identifying information, and makes no identity claims. Traces are generated privately for the person who requested them.

---

## D. The literature admits its own weakness

**Source:** "SoK: Assumptions Underlying Cryptocurrency Deanonymizations", 2022.

A systematisation-of-knowledge paper examining the assumptions behind deanonymisation techniques. Two useful observations.

On CoinJoin, it confirms the position taken in `06-detection.md`: for CoinJoin transactions the multi-input assumption "is false as such transactions combine the inputs of multiple entities by design. Consequently, applying the multi-input heuristic to CoinJoin transactions would lead to false positives which is problematic."

More striking is its criticism of the field. Of papers using the multi-input heuristic, it observes that "the discussion of how reasonable the assumption is differs greatly. There are papers that completely forgo any discussion of whether the assumption is reasonable."

A body of published work uses a heuristic with a documented 63% error rate without examining whether it holds.

**What this offers.** Documenting assumptions and their error rates is a low bar that much of the field does not clear. `06-detection.md` already commits to it. This finding says that commitment is worth more than it appeared.

**Change:** add an explicit assumptions register to `06-detection.md`. Each heuristic states its assumption, the conditions under which it fails, and its published error rate where one exists.

---

## Changes required

| # | Change | Affects |
|---|---|---|
| 29 | Adopt FIFO taint tracking, per Clayton's Case (1816) | `01`, `05`, new `15` |
| 30 | Document the fee-handling problem in FIFO implementation | new `15` |
| 31 | Record honest criticisms of taint analysis and fungibility | new `15` |
| 32 | Exclude dust-value inputs from clustering by default | `06` |
| 33 | Mark cluster links depending on dust as low confidence | `06` |
| 34 | Surface dust inputs to users with do-not-spend advice | `07` |
| 35 | Detect and warn on near-identical addresses in history | `06`, `07` |
| 36 | Highlight differing characters between visually similar addresses | `10` |
| 37 | State explicitly: no public label database, no paid identification, no identity claims | `01` |
| 38 | Add an assumptions register with failure conditions and error rates | `06` |

---

## Assessment

Thirty-eight changes now identified before implementation.

**Item 29 is the most consequential finding in any of the research documents.** The system claimed to trace stolen funds without defining what tracing means when funds mix. FIFO answers it, and answers it with a piece of English common law from 1816 that is still in force. For a product whose output is a report for UK police, adopting the tracing rule that English law already uses for mixed funds is a much stronger position than adopting the one most commercial tools use.

Item 32 closes a genuine attack surface. An adversary can currently poison the system's clustering with dust for a few pounds in fees.

Items 35 and 36 formalise a threat the design system had already defended against by instinct. The middle-truncation rule was chosen for legibility; it turns out to be a control against address poisoning.

Research ends here. The remaining unknowns require running code.
