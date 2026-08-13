# 16. Security posture

Written before public deployment rather than after an incident. Covers what the system exposes, what it must never expose, and the risks specific to operating it as a named individual rather than a firm.

Compiled 12 August 2026.

---

## A. Current exposure

**The node is outbound-only.** Port 8333 has never been forwarded, so the node initiates connections to peers but nothing on the internet can initiate a connection to it. `getnetworkinfo` has consistently reported `in 0, out 10`.

This is the lowest-exposure configuration and is deliberate. A node that does not accept inbound connections is still a fully validating node; accepting them is a contribution to the network, not a requirement.

**Nothing else is publicly reachable.** No web service, no API, no database port. The entire system currently exists on one machine behind NAT.

**Assessment: low risk in the current state.** The remainder of this document concerns what changes on deployment.

---

## B. Port discipline

### 8333 — Bitcoin P2P

If ever opened, the exposure is limited: "Opening port 8333 exposes only the Bitcoin P2P protocol. Your node does not hold funds and there is nothing to steal through this port. The risk profile is comparable to running any well-maintained network service."

It does reveal the host IP address to peers, which matters for the hosting decision in section D.

It is also a frequently scanned port. Opening it invites background noise and some DDoS exposure.

**Position: leave closed.** The node gains nothing this project needs from inbound peers.

### 8332 — JSON-RPC

**This port must never reach the internet.** It is the administrative interface: "If an attacker can reach and authenticate to the API, they may be able to inspect wallet data, issue wallet commands."

Current configuration binds it inside the Docker network with `rpcallowip=172.16.0.0/12`. Correct and unchanged.

Named risks are "weak RPC credentials, overly broad rpcallowip settings, accidental WAN exposure, and old node software."

Controls:
- RPC credentials generated randomly, stored only in a password manager, never printed to a terminal or committed
- `bitcoin.conf` is gitignored; `bitcoin.conf.example` carries `CHANGEME`
- `rpcallowip` never widened
- Bitcoin Core kept current

### Database ports

ClickHouse and Neo4j bind to the Docker network only. Never published to the host, never to the internet. If the web layer needs data it asks the API; the API talks to the databases.

### The rule

**Nothing external ever talks to the node or the databases directly.** The API is the only public surface, and it exposes read operations on data the system has already computed.

---

## C. Publication policy

The most significant risk in this project is not a technical compromise. It is publishing accusations.

### Traces are private

**A trace is generated for the person who requested it and shown only to them.**

No public case database. No public address pages. No address is ever named as belonging to a thief on a page a stranger can load.

Three reasons, each sufficient alone.

**Attribution is already out of scope.** `01-thesis.md` commits to no identity claims. Publishing "this address stole funds" is an identity claim about whoever controls it.

**Incorrect labelling is a documented failure mode.** Arkham Intelligence's public label database drew criticism that incorrect labelling "could lead to false accusations of money laundering and other crimes." A firm can absorb a defamation claim. A recent graduate cannot.

**Correct labelling carries its own risk.** Doxxing research finds "the primary target of doxing, particularly when it involves a physical extortion component, is for finance." Publicly naming addresses controlled by people who steal for a living, as a named individual at a known location with no institutional backing, is an asymmetric position.

### What is published

The tool itself, the source code, the methodology, the measured error rates, and aggregate statistics about the system's own operation. None of that names anyone.

---

## D. Hosting

**The web layer does not run from home.**

If deployed, the API and frontend go on a rented server. The node, databases and ingestor stay where they are.

Reasons:

- The home IP never appears in DNS or in any traceroute from a user
- A denial-of-service attempt hits rented infrastructure rather than domestic internet
- Compromise of the web layer does not put a personal machine on the same network as the attacker

The link between the two is outbound-initiated from home, so the home machine is never a listening service on the public internet.

**Not the family business server.** An earlier option was to host on a domain belonging to a relative's business. Rejected: a fault, a traffic spike or an incident would affect a working commercial site, and the association attaches this project's risk to a business that has not accepted it.

---

## E. Operating as an individual

Currently public in the repository: full name, email address in every commit, city, and the fact that the system runs on a Mac mini at home.

None of that is a problem for a portfolio project. It becomes relevant only in combination with section C, which is the reason section C exists.

**If this becomes a business, incorporate before it goes public.** A limited company places a legal entity between the operator and any claim, which is much of what incorporation is for. It also bears on the open question in `12-market-process.md` about whether producing tracing reports for others carries regulated-activity implications.

Until then it remains a portfolio project running locally with no users, and the risk is correspondingly low.

---

## F. Standard hygiene

- Operating system patched; automatic security updates enabled
- Two-factor authentication on GitHub
- The personal access token scoped to `repo` only, with an expiry, stored in a password manager
- Credentials never pasted into a chat interface, a screenshot, or a file that could be committed
- `.gitignore` verified with `git status` before every commit
- Docker images pinned to explicit versions rather than `latest`, so an upstream change cannot alter the running system silently

---

## G. What would change this assessment

Recorded so the posture is revisited rather than assumed permanent.

1. Accepting public users, which introduces personal data and the GDPR obligations in `15-user-and-regulation.md`
2. Publishing anything that names an address, which section C currently prohibits
3. Opening port 8333, which is not planned
4. Operating commercially, which requires incorporation first
5. Storing user email addresses at scale, which is unambiguously personal data and requires a retention policy

---

## Assessment

The current risk is low and the controls are already in place, largely by accident rather than design — the node was never made reachable because there was no reason to.

The material decision is section C. A tool that traces stolen funds and publishes the results is a different proposition from one that traces stolen funds and shows the result to the person who was robbed. The second is the product described throughout these documents. The first would be a considerably more exposed thing to operate from a flat in Edinburgh.
