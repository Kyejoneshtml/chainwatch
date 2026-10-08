#!/usr/bin/env python3
"""Phase 5a setup steps (docs/08-build-plan.md, Phase 5a pre-registration).

  select-source  apply the pre-registered source rule: active watches in
                 created_at order; for each, its most recent outgoing
                 transaction in flows; the first whose CH-B trace leaves a
                 tainted range at hop 6 is the source. Correctness runs only.
  build-ch       materialise the identical subgraph into ClickHouse
                 (bench_sub_flows, bench_sub_flows_by_txid, bench_sub_tx):
                 exactly the rows the reference trace reads.
  load-neo       load the same rows, read back from bench_sub_*, into Neo4j
                 using 05-data-models.md's model, constraints first.
  verify-links   check every (address, value) link the trace used against the
                 node's own previous-outpoint data (getrawtransaction with
                 blockhash, inside the prune window).

Writes only to --out (keep it outside the repo: contents name addresses).
"""
import argparse
import json
import os
import subprocess
import sys
import time

sys.path.insert(0, os.path.dirname(os.path.abspath(__file__)))
import trace_bench as tb  # noqa: E402


def ch():
    return tb.CH(f"http://{os.environ['CH_HOST']}:{os.environ['CH_PORT']}/", os.environ["CH_USER"],
                 os.environ["CH_PASSWORD"])


def admin_stdin(sql):
    return subprocess.run(["docker", "exec", "-i", "clickhouse", "clickhouse-client", "--database", "chainwatch"],
                          input=sql, capture_output=True, text=True, check=True).stdout


def select_source(args):
    c = ch()
    watches = c.q("SELECT address FROM watchlist FINAL WHERE active = 1 ORDER BY created_at")
    log = []
    for i, w in enumerate(watches, 1):
        addr = w["address"]
        last = c.q(f"""SELECT txid FROM flows WHERE address = {tb._a(addr)} AND direction = 'in'
                       GROUP BY txid ORDER BY max(seen_at) DESC LIMIT 1""")
        if not last:
            log.append({"watch_index": i, "result": "no outgoing transaction"})
            continue
        t0 = last[0]["txid"]
        seeds = [{"txid": t0, "vin": int(r["position"]), "lo": 0, "hi": int(r["value"])}
                 for r in c.q(f"""SELECT DISTINCT position, value FROM flows WHERE address = {tb._a(addr)}
                                  AND direction = 'in' AND txid = {tb._s(t0)} ORDER BY position""")]
        hops, _, _, wall = tb.run_trace("ch", "CH-B", seeds, f"select-{i}-{int(time.time())}", ch=c)
        sizes = [len(h) for h in hops]
        hop6_ranges = sum(1 for r in hops[5] if r[0] == "range") if len(hops) == 6 else 0
        log.append({"watch_index": i, "hop_rows": sizes, "hop6_ranges": hop6_ranges, "wall_s": round(wall, 2)})
        print(f"watch #{i}: hop rows {sizes}, hop-6 ranges {hop6_ranges}", flush=True)
        if hop6_ranges > 0:
            json.dump({"watch_index": i, "address": addr, "source_txid": t0, "seeds": seeds,
                       "selection_log": log}, open(os.path.join(args.out, "source.json"), "w"), indent=1)
            json.dump({"hops": [[list(r) for r in h] for h in hops]},
                      open(os.path.join(args.out, "reference.json"), "w"))
            print(f"selected watch #{i}")
            return
    json.dump({"selection_log": log}, open(os.path.join(args.out, "source.json"), "w"), indent=1)
    print("NO watch qualifies under the pre-registered rule")


def subgraph_keys(args):
    hops = json.load(open(os.path.join(args.out, "reference.json")))["hops"]
    pairs, txs = set(), set()
    for h_i, h in enumerate(hops):
        for kind, txid, pos, address, value, lo, hi, n in h:
            if kind in ("range", "fee", "incomplete"):
                txs.add(txid)
            if kind == "range" and address != "" and h_i < tb.HOPS - 1:
                pairs.add((address, value))
    return sorted(pairs), sorted(txs)


def build_ch(args):
    pairs, txs = subgraph_keys(args)
    plist = ",".join(f"({tb._a(a)},{int(v)})" for a, v in pairs) or "('',0)"
    alist = ",".join(sorted({tb._a(a) for a, _ in pairs})) or "''"
    tlist = ",".join(tb._s(t) for t in txs)
    sel = f"""SELECT DISTINCT txid, direction, position, address, value FROM flows
      WHERE (direction = 'in' AND address IN ({alist}) AND (address, value) IN ({plist}))
         OR txid IN ({tlist})"""
    ddl = f"""
CREATE TABLE IF NOT EXISTS bench_sub_flows (txid String, direction Enum8('in' = 1, 'out' = 2), position UInt16,
  address String, value UInt64) ENGINE = MergeTree ORDER BY (address, direction, position, txid)
  COMMENT 'Phase 5a benchmark: identical subgraph, flows ordering';
CREATE TABLE IF NOT EXISTS bench_sub_flows_by_txid AS bench_sub_flows ENGINE = MergeTree
  ORDER BY (txid, direction, position) COMMENT 'Phase 5a benchmark: identical subgraph, txid ordering';
CREATE TABLE IF NOT EXISTS bench_sub_tx (txid String, input_count UInt16, output_count UInt16, seen_at DateTime64(3))
  ENGINE = ReplacingMergeTree(seen_at) ORDER BY txid COMMENT 'Phase 5a benchmark: identical subgraph, transactions';
INSERT INTO bench_sub_flows {sel};
INSERT INTO bench_sub_flows_by_txid SELECT * FROM bench_sub_flows;
INSERT INTO bench_sub_tx SELECT txid, input_count, output_count, seen_at FROM transactions FINAL WHERE txid IN ({tlist});
"""
    existing = admin_stdin("SELECT count() FROM system.tables WHERE database = 'chainwatch' AND name LIKE 'bench_sub_%'")
    if int(existing.strip()) != 0:
        sys.exit("bench_sub_* tables already exist; refusing to append to them")
    admin_stdin(ddl.replace(";\n", ";\n"))  # clickhouse-client runs multi-statement stdin
    counts = admin_stdin("""SELECT
      (SELECT count() FROM bench_sub_flows), (SELECT count() FROM bench_sub_flows_by_txid),
      (SELECT count() FROM bench_sub_flows WHERE direction = 'in'), (SELECT count() FROM bench_sub_flows WHERE direction = 'out'),
      (SELECT uniqExact(address) FROM bench_sub_flows WHERE address != ''),
      (SELECT uniqExact(txid) FROM bench_sub_flows), (SELECT count() FROM bench_sub_tx FINAL)
      FORMAT JSONEachRow""")
    print(counts)
    json.dump({"pairs": len(pairs), "txs_read": len(txs), "counts": json.loads(counts)},
              open(os.path.join(args.out, "subgraph_ch.json"), "w"), indent=1)


def load_neo(args):
    c = ch()
    flows = c.q("SELECT txid, direction, position, address, value FROM bench_sub_flows")
    txrows = c.q("SELECT txid, input_count, output_count FROM bench_sub_tx FINAL")
    neo = tb.Neo(os.environ["NEO4J_URI"], "neo4j", os.environ["NEO4J_PASSWORD"])
    t0 = time.perf_counter()
    with neo.driver.session(database="neo4j") as s:
        existing = s.run("MATCH (n) RETURN count(n) AS n").single()["n"]
        if existing:
            sys.exit(f"Neo4j already holds {existing} nodes; refusing to load on top")
        for stmt in ["CREATE CONSTRAINT address_unique IF NOT EXISTS FOR (a:Address) REQUIRE a.address IS UNIQUE",
                     "CREATE CONSTRAINT tx_unique IF NOT EXISTS FOR (t:Transaction) REQUIRE t.txid IS UNIQUE"]:
            s.run(stmt).consume()
        s.run("CALL db.awaitIndexes(300)").consume()
        counts = {txr["txid"]: txr for txr in txrows}
        txids = sorted({f["txid"] for f in flows})
        addrs = sorted({f["address"] for f in flows})
        B = 5000

        def batched(items):
            for i in range(0, len(items), B):
                yield items[i:i + B]

        for b in batched([{"txid": t, "ic": int(counts[t]["input_count"]) if t in counts else 0,
                           "oc": int(counts[t]["output_count"]) if t in counts else 0} for t in txids]):
            s.run("UNWIND $b AS r CREATE (:Transaction {txid: r.txid, input_count: r.ic, output_count: r.oc})",
                  b=b).consume()
        for b in batched([{"a": a} for a in addrs]):
            s.run("UNWIND $b AS r CREATE (:Address {address: r.a})", b=b).consume()
        ins = [{"a": f["address"], "t": f["txid"], "v": int(f["value"]), "p": int(f["position"])}
               for f in flows if f["direction"] == "in"]
        outs = [{"a": f["address"], "t": f["txid"], "v": int(f["value"]), "p": int(f["position"])}
                for f in flows if f["direction"] == "out"]
        for b in batched(ins):
            s.run("""UNWIND $b AS r MATCH (a:Address {address: r.a}) MATCH (t:Transaction {txid: r.t})
                     CREATE (a)-[:FUNDED {value: r.v, vin: r.p}]->(t)""", b=b).consume()
        for b in batched(outs):
            s.run("""UNWIND $b AS r MATCH (a:Address {address: r.a}) MATCH (t:Transaction {txid: r.t})
                     CREATE (t)-[:PAID {value: r.v, vout: r.p}]->(a)""", b=b).consume()
        got = {
            "Address": s.run("MATCH (n:Address) RETURN count(n) AS n").single()["n"],
            "Transaction": s.run("MATCH (n:Transaction) RETURN count(n) AS n").single()["n"],
            "FUNDED": s.run("MATCH ()-[r:FUNDED]->() RETURN count(r) AS n").single()["n"],
            "PAID": s.run("MATCH ()-[r:PAID]->() RETURN count(r) AS n").single()["n"],
        }
    want = {"Address": len(addrs), "Transaction": len(txids), "FUNDED": len(ins), "PAID": len(outs)}
    print("loaded", got, "expected", want, f"in {time.perf_counter() - t0:.1f}s")
    assert got == want, "Neo4j load does not match bench_sub_flows"
    json.dump({"neo": got, "load_s": time.perf_counter() - t0},
              open(os.path.join(args.out, "subgraph_neo.json"), "w"), indent=1)


def verify_links(args):
    """For every spending transaction the trace propagated through, compare the
    (address, value) link with the node's real previous outpoint."""
    hops = json.load(open(os.path.join(args.out, "reference.json")))["hops"]
    src = json.load(open(os.path.join(args.out, "source.json")))
    c = ch()

    def bc(*a):
        return subprocess.run(["docker", "exec", "bitcoind", "bitcoin-cli", "-conf=/config/bitcoin.conf", *a],
                              capture_output=True, text=True, check=True).stdout

    # Links: hop k output (txid, vout) -> spending tx at hop k+1, via the linked
    # tx's own input at vin. Reconstruct from frontier -> next hop by rerunning
    # the link step's logic on the reference (address, value) pairs.
    checked = mismatched = 0
    details = []
    for h_i in range(tb.HOPS - 1):
        frontier = [r for r in hops[h_i] if r[0] == "range" and r[3] != ""]
        next_txs = {r[1] for r in hops[h_i + 1] if r[0] in ("range", "fee", "incomplete")}
        for kind, ptxid, pvout, addr, val, lo, hi, n in frontier:
            cands = c.q(f"""SELECT DISTINCT txid, position FROM flows WHERE direction = 'in'
                            AND address = {tb._a(addr)} AND value = {int(val)} AND txid != {tb._s(ptxid)}""")
            if len(cands) != 1:
                continue
            t, vin = cands[0]["txid"], int(cands[0]["position"])
            if t not in next_txs:
                continue
            height = c.q(f"SELECT block_height FROM transactions FINAL WHERE txid = {tb._s(t)}")
            h = int(height[0]["block_height"]) if height else 0
            if h == 0:
                details.append({"spender": t, "status": "unconfirmed or unknown, not checkable"})
                continue
            raw = json.loads(bc("getrawtransaction", t, "1", bc("getblockhash", str(h)).strip()))
            prev = raw["vin"][vin]
            ok = prev.get("txid") == ptxid and prev.get("vout") == pvout
            checked += 1
            mismatched += 0 if ok else 1
            if not ok:
                details.append({"hop": h_i + 1, "status": "MISMATCH"})
    json.dump({"checked": checked, "mismatched": mismatched, "details": details},
              open(os.path.join(args.out, "links.json"), "w"), indent=1)
    print(f"links checked against node: {checked}, mismatched: {mismatched}, notes: {len(details)}")


def main():
    ap = argparse.ArgumentParser()
    ap.add_argument("step", choices=["select-source", "build-ch", "load-neo", "verify-links"])
    ap.add_argument("--out", required=True)
    args = ap.parse_args()
    {"select-source": select_source, "build-ch": build_ch, "load-neo": load_neo,
     "verify-links": verify_links}[args.step](args)


if __name__ == "__main__":
    main()
