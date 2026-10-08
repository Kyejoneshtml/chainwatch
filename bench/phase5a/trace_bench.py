#!/usr/bin/env python3
"""Phase 5a: 6-hop FIFO trace, ClickHouse vs Neo4j.

Method and winner condition are pre-registered in docs/08-build-plan.md,
Phase 5a. This file implements that method and nothing else. Every engine
applies exactly the same rules:

  link       a tainted output (txid, vout, address, value) is spent by the
             `in` row with the same address and exact value in a different
             transaction. flows stores no previous outpoint, so this is the
             only link the schema allows (05-data-models.md's FUNDED {value}
             is the same link). 0 candidates -> 'unspent', >1 -> 'ambiguous';
             both are terminal and never guessed.
  FIFO       Clayton's Case: inputs laid end to end in vin order, outputs in
             vout order; satoshi n of the input side is satoshi n of the
             output side; satoshis past the total output value are the fee
             ('fee', terminal). Taint is a satoshi range [lo, hi) within a
             specific output, never a proportion.
  complete   a spending transaction is only propagated through if its observed
             input/output row counts equal transactions.input_count /
             output_count; otherwise 'incomplete', terminal.
  noaddr     an output with an empty address is terminal (harness-side, same
             for every engine).

Each hop is one query, FIFO computed inside the engine. Hop 1 starts from
seeds (the watched address's own inputs to the source transaction, fully
tainted). Hops 2..6 start from the previous hop's tainted ranges.

No address strings live in this file. Results, which contain addresses and
txids, are written only to the --out directory (keep it outside the repo).
"""
import argparse
import json
import os
import re
import statistics
import subprocess
import sys
import time

import requests

HEX64 = re.compile(r"^[0-9a-f]{64}$")
ADDR = re.compile(r"^[A-Za-z0-9]{14,90}$")
HOPS = 6

# --------------------------------------------------------------------------
# ClickHouse


class CH:
    def __init__(self, url, user, password, database="chainwatch"):
        self.url, self.auth, self.db = url, (user, password), database
        self.s = requests.Session()

    def q(self, sql, query_id=None, timeout=1800):
        params = {"database": self.db, "output_format_json_quote_64bit_integers": "0",
                  "max_execution_time": "1700"}
        if query_id:
            params["query_id"] = query_id
        r = self.s.post(self.url, params=params, data=(sql + "\nFORMAT JSONEachRow").encode(),
                        auth=self.auth, timeout=timeout)
        if r.status_code != 200:
            raise RuntimeError(r.text[:3000])
        rows = [json.loads(l) for l in r.text.splitlines() if l]
        for row in rows:
            if "exception" in row:
                raise RuntimeError(row["exception"][:3000])
        return rows


def _s(txid):
    assert HEX64.match(txid), txid
    return f"'{txid}'"


def _a(addr):
    assert addr == "" or ADDR.match(addr), addr
    return f"'{addr}'"


CH_TABLES = {
    # variant: (link table, txid-access table, transactions table)
    "CH-A": ("flows", "flows", "transactions"),
    "CH-B": ("flows", "bench_flows_by_txid", "transactions"),
    "CH-S": ("bench_sub_flows", "bench_sub_flows_by_txid", "bench_sub_tx"),
}

_CH_COLS = "kind, txid, pos, address, value, lo, hi, n"


CH_FORMULATION = "v2"


def _ch_propagate(txid_table, tx_table):
    """CTEs + SELECTs that turn CTE `linked(t, vin, lo, hi)` into result rows.

    v1 emitted ranges, fees and incompletes as three UNION ALL branches over
    `seg`. ClickHouse inlines CTEs, so each branch re-ran the whole link +
    propagate chain: measured ~270 ms of fixed overhead per hop even on the
    121-row subgraph. v2 computes `seg` once and emits all three kinds from
    one branch via ARRAY JOIN. Same rows, same order-independent result.
    """
    if CH_FORMULATION == "v2":
        return _ch_propagate_v2(txid_table, tx_table)
    return _ch_propagate_v1(txid_table, tx_table)


def _ch_propagate_v2(txid_table, tx_table):
    return _ch_propagate_v1(txid_table, tx_table).split("\nSELECT 'range'")[0] + """
SELECT r.1 AS kind, r.2 AS txid, r.3 AS pos, r.4 AS address, r.5 AS value, r.6 AS lo, r.7 AS hi, r.8 AS n
FROM seg
ARRAY JOIN arrayConcat(
  if(complete,
     arrayMap(z -> ('range', t, toUInt32(z.1), z.2, toUInt64(z.3), toUInt64(z.4 - z.6), toUInt64(z.5 - z.6), toUInt64(0)),
       arrayFilter(z -> z.4 < z.5,
         arrayMap((o, e) -> (o.1, o.3, o.2, greatest(a, e - o.2), least(b, e), e - o.2), outs, oend))),
     []),
  if(complete AND b > tot, [('fee', t, toUInt32(vin), '', toUInt64(0), toUInt64(greatest(a, tot)), toUInt64(b), toUInt64(0))], []),
  if(NOT complete, [('incomplete', t, toUInt32(vin), '', toUInt64(0), toUInt64(a), toUInt64(b), toUInt64(0))], [])
) AS r"""


def _ch_propagate_v1(txid_table, tx_table):
    return f"""
txs AS (SELECT DISTINCT t FROM linked),
rws AS (
  SELECT txid,
         arraySort(x -> x.1, groupArrayIf((position, value), direction = 'in')) AS ins,
         arraySort(x -> x.1, groupArrayIf((position, value, address), direction = 'out')) AS outs
  FROM (SELECT DISTINCT txid, direction, position, address, value
        FROM {txid_table} WHERE txid IN (SELECT t FROM txs))
  GROUP BY txid
),
tc AS (SELECT txid, input_count, output_count FROM {tx_table} FINAL WHERE txid IN (SELECT t FROM txs)),
info AS (
  SELECT tx.t AS t, rws.ins AS ins, rws.outs AS outs,
         (length(rws.ins) = tc.input_count AND length(rws.outs) = tc.output_count
          AND tc.input_count > 0) AS complete
  FROM txs AS tx LEFT JOIN rws ON rws.txid = tx.t LEFT JOIN tc ON tc.txid = tx.t
),
seg AS (
  SELECT l.t AS t, l.vin AS vin, info.complete AS complete, info.outs AS outs,
         toUInt64(arraySum(arrayMap(x -> x.2, arrayFilter(x -> x.1 < l.vin, info.ins)))) + l.lo AS a,
         toUInt64(arraySum(arrayMap(x -> x.2, arrayFilter(x -> x.1 < l.vin, info.ins)))) + l.hi AS b,
         arrayCumSum(arrayMap(x -> toUInt64(x.2), info.outs)) AS oend,
         toUInt64(arraySum(arrayMap(x -> x.2, info.outs))) AS tot
  FROM linked AS l INNER JOIN info ON info.t = l.t
)
SELECT 'range' AS kind, t AS txid, toUInt32(o.1) AS pos, o.3 AS address, toUInt64(o.2) AS value,
       toUInt64(greatest(a, e - o.2) - (e - o.2)) AS lo, toUInt64(least(b, e) - (e - o.2)) AS hi,
       toUInt64(0) AS n
FROM seg ARRAY JOIN outs AS o, oend AS e
WHERE complete AND greatest(a, e - o.2) < least(b, e)
UNION ALL
SELECT 'fee', t, toUInt32(vin), '', toUInt64(0), toUInt64(greatest(a, tot)), toUInt64(b), toUInt64(0)
FROM seg WHERE complete AND b > tot
UNION ALL
SELECT 'incomplete', t, toUInt32(vin), '', toUInt64(0), toUInt64(a), toUInt64(b), toUInt64(0)
FROM seg WHERE NOT complete"""


def ch_hop_sql(variant, frontier=None, seeds=None):
    link_t, txid_t, tx_t = CH_TABLES[variant]
    if seeds is not None:
        lits = ",".join(f"({_s(s['txid'])},{int(s['vin'])},{int(s['lo'])},{int(s['hi'])})" for s in seeds)
        return f"""WITH
linked AS (SELECT x.1 AS t, x.2 AS vin, x.3 AS lo, x.4 AS hi FROM
  (SELECT arrayJoin(CAST([{lits}], 'Array(Tuple(String, UInt16, UInt64, UInt64))')) AS x)),
{_ch_propagate(txid_t, tx_t)}"""
    lits = ",".join(
        f"({_s(f['txid'])},{int(f['pos'])},{_a(f['address'])},{int(f['value'])},{int(f['lo'])},{int(f['hi'])})"
        for f in frontier)
    return f"""WITH
f AS (SELECT x.1 AS ptxid, x.2 AS pvout, x.3 AS addr, x.4 AS val, x.5 AS lo, x.6 AS hi FROM
  (SELECT arrayJoin(CAST([{lits}], 'Array(Tuple(String, UInt16, String, UInt64, UInt64, UInt64))')) AS x)),
cand AS (
  SELECT DISTINCT txid AS t, position AS vin, address AS caddr, value AS cval FROM {link_t}
  WHERE direction = 'in' AND address IN (SELECT addr FROM f) AND (address, value) IN (SELECT addr, val FROM f)
),
lk AS (
  SELECT f.ptxid AS ptxid, f.pvout AS pvout, f.lo AS lo, f.hi AS hi, c.t AS t, c.vin AS vin
  FROM f INNER JOIN cand AS c ON c.caddr = f.addr AND c.cval = f.val WHERE c.t != f.ptxid
),
cnt AS (SELECT ptxid, pvout, count() AS n FROM lk GROUP BY ptxid, pvout),
linked AS (SELECT t, vin, lo, hi FROM lk WHERE (ptxid, pvout) IN (SELECT ptxid, pvout FROM cnt WHERE n = 1)),
{_ch_propagate(txid_t, tx_t)}
UNION ALL
SELECT if(c.n = 0, 'unspent', 'ambiguous'), f.ptxid, toUInt32(f.pvout), f.addr, toUInt64(f.val),
       toUInt64(f.lo), toUInt64(f.hi), toUInt64(c.n)
FROM f LEFT JOIN cnt AS c ON c.ptxid = f.ptxid AND c.pvout = f.pvout WHERE c.n != 1"""


# --------------------------------------------------------------------------
# Neo4j (05-data-models.md model: Address -FUNDED{value,vin}-> Transaction
# -PAID{value,vout}-> Address)

_NEO_PROPAGATE = """
  MATCH (t:Transaction {txid: ttxid})
  CALL { WITH t MATCH (:Address)-[i:FUNDED]->(t) WITH i ORDER BY i.vin RETURN collect([i.vin, i.value]) AS ins }
  CALL { WITH t MATCH (t)-[o:PAID]->(y:Address) WITH o, y ORDER BY o.vout
         RETURN collect([o.vout, o.value, y.address]) AS outs }
  WITH t, ttxid, vin, lo, hi, ins, outs,
       reduce(s = 0, x IN ins | s + CASE WHEN x[0] < vin THEN x[1] ELSE 0 END) AS base,
       reduce(acc = [0], x IN outs | acc + [acc[size(acc) - 1] + x[1]]) AS cum
  WITH ttxid, vin, outs, cum, base + lo AS a, base + hi AS b,
       (size(ins) = coalesce(t.input_count, 0) AND size(outs) = coalesce(t.output_count, 0)
        AND coalesce(t.input_count, 0) > 0) AS complete
  WITH ttxid, vin, outs, cum, a, b, complete, cum[size(cum) - 1] AS tot
  RETURN CASE WHEN NOT complete
    THEN [{kind: 'incomplete', txid: ttxid, pos: vin, address: '', value: 0, lo: a, hi: b, n: 0}]
    ELSE [i IN range(0, size(outs) - 1)
           WHERE (CASE WHEN a > cum[i] THEN a ELSE cum[i] END) < (CASE WHEN b < cum[i + 1] THEN b ELSE cum[i + 1] END)
           | {kind: 'range', txid: ttxid, pos: outs[i][0], address: outs[i][2], value: outs[i][1],
              lo: (CASE WHEN a > cum[i] THEN a ELSE cum[i] END) - cum[i],
              hi: (CASE WHEN b < cum[i + 1] THEN b ELSE cum[i + 1] END) - cum[i], n: 0}]
         + CASE WHEN b > tot
             THEN [{kind: 'fee', txid: ttxid, pos: vin, address: '', value: 0,
                    lo: CASE WHEN a > tot THEN a ELSE tot END, hi: b, n: 0}]
             ELSE [] END
  END AS out"""

NEO_SEED_Q = """
UNWIND $seeds AS s
CALL {
  WITH s
  WITH s.txid AS ttxid, s.vin AS vin, s.lo AS lo, s.hi AS hi
""" + _NEO_PROPAGATE + """
}
UNWIND out AS r
RETURN r.kind AS kind, r.txid AS txid, r.pos AS pos, r.address AS address, r.value AS value,
       r.lo AS lo, r.hi AS hi, r.n AS n"""

NEO_HOP_Q = """
UNWIND $frontier AS f
CALL {
  WITH f
  OPTIONAL MATCH (:Address {address: f.address})-[sp:FUNDED]->(t:Transaction)
  WHERE sp.value = f.value AND t.txid <> f.txid
  RETURN collect(CASE WHEN t IS NULL THEN null ELSE {t: t.txid, vin: sp.vin} END) AS cands
}
CALL {
  WITH f, cands
  WITH f, cands WHERE size(cands) <> 1
  RETURN [{kind: CASE WHEN size(cands) = 0 THEN 'unspent' ELSE 'ambiguous' END, txid: f.txid,
           pos: f.pos, address: f.address, value: f.value, lo: f.lo, hi: f.hi, n: size(cands)}] AS out
  UNION ALL
  WITH f, cands
  WITH f, cands WHERE size(cands) = 1
  WITH cands[0].t AS ttxid, cands[0].vin AS vin, f.lo AS lo, f.hi AS hi
""" + _NEO_PROPAGATE + """
}
UNWIND out AS r
RETURN r.kind AS kind, r.txid AS txid, r.pos AS pos, r.address AS address, r.value AS value,
       r.lo AS lo, r.hi AS hi, r.n AS n"""


class Neo:
    def __init__(self, uri, user, password):
        from neo4j import GraphDatabase
        self.driver = GraphDatabase.driver(uri, auth=(user, password))

    def hop(self, frontier=None, seeds=None):
        q, params = (NEO_SEED_Q, {"seeds": seeds}) if seeds is not None else (NEO_HOP_Q, {"frontier": frontier})
        with self.driver.session(database="neo4j") as s:
            res = s.run(q, params)
            rows = [r.data() for r in res]
            summ = res.consume()
        engine_ms = (summ.result_available_after or 0) + (summ.result_consumed_after or 0)
        return rows, engine_ms


# --------------------------------------------------------------------------
# Trace driver, identical for every engine


def norm(rows):
    out = []
    for r in rows:
        out.append((r["kind"], r["txid"], int(r["pos"]), r["address"], int(r["value"]),
                    int(r["lo"]), int(r["hi"]), int(r["n"])))
    return sorted(out)


def run_trace(engine, variant, seeds, tag, ch=None):
    """Returns (per-hop normalised results, per-hop engine ms, query ids, wall s)."""
    hops, engine_ms, qids = [], [], []
    frontier = None
    t0 = time.perf_counter()
    for h in range(1, HOPS + 1):
        if engine == "neo":
            rows, ms = engine_obj_neo.hop(seeds=seeds) if h == 1 else engine_obj_neo.hop(frontier=frontier)
            engine_ms.append(ms)
        else:
            qid = f"p5a-{tag}-h{h}"
            sql = ch_hop_sql(variant, seeds=seeds) if h == 1 else ch_hop_sql(variant, frontier=frontier)
            rows = ch.q(sql, query_id=qid)
            qids.append(qid)
        n = norm(rows)
        hops.append(n)
        frontier = [dict(txid=r[1], pos=r[2], address=r[3], value=r[4], lo=r[5], hi=r[6])
                    for r in n if r[0] == "range" and r[3] != ""]
        if not frontier and h < HOPS:
            for _ in range(h + 1, HOPS + 1):
                hops.append([])
            break
    wall = time.perf_counter() - t0
    return hops, engine_ms, qids, wall


engine_obj_neo = None


def ch_admin(sql):
    """DDL/admin as the container's default user (the ingestor user is read-only)."""
    return subprocess.run(["docker", "exec", "clickhouse", "clickhouse-client", "--database", "chainwatch",
                           "--query", sql], capture_output=True, text=True, check=True).stdout


def query_log(qids):
    ch_admin("SYSTEM FLUSH LOGS")
    ids = ",".join(f"'{q}'" for q in qids)
    out = ch_admin(f"""SELECT query_id, type, query_duration_ms, memory_usage, read_rows, read_bytes,
        exception_code FROM system.query_log WHERE query_id IN ({ids}) AND type != 'QueryStart'
        FORMAT JSONEachRow""")
    return {r["query_id"]: r for r in (json.loads(l) for l in out.splitlines() if l)}


def summarise(values):
    v = sorted(values)
    return {"median": statistics.median(v), "min": v[0], "max": v[-1], "n": len(v), "all": values}


def main():
    ap = argparse.ArgumentParser()
    ap.add_argument("variant", choices=["CH-A", "CH-B", "CH-S", "NEO"])
    ap.add_argument("--source", required=True, help="JSON file: {seeds: [...]} from select_source.py")
    ap.add_argument("--runs", type=int, default=7)
    ap.add_argument("--out", required=True)
    ap.add_argument("--reference", help="JSON results file every run must equal")
    ap.add_argument("--ch-formulation", choices=["v1", "v2"], default="v2")
    args = ap.parse_args()
    global CH_FORMULATION
    CH_FORMULATION = args.ch_formulation

    seeds = json.load(open(args.source))["seeds"]
    ch = CH(f"http://{os.environ['CH_HOST']}:{os.environ['CH_PORT']}/", os.environ["CH_USER"],
            os.environ["CH_PASSWORD"])
    global engine_obj_neo
    if args.variant == "NEO":
        engine_obj_neo = Neo(os.environ["NEO4J_URI"], "neo4j", os.environ["NEO4J_PASSWORD"])

    ref = json.load(open(args.reference))["hops"] if args.reference else None
    stamp = time.strftime("%Y%m%d%H%M%S")
    runs = []
    for i in range(1, args.runs + 1):
        tag = f"{args.variant}-{stamp}-r{i}"
        try:
            hops, eng_ms, qids, wall = run_trace("neo" if args.variant == "NEO" else "ch",
                                                args.variant, seeds, tag, ch=ch)
            err = None
        except Exception as exc:  # a failure is a result, recorded, not hidden
            hops, eng_ms, qids, wall, err = None, [], [], None, str(exc)[:2000]
        hop_json = [[list(r) for r in h] for h in hops] if hops else None
        same = (hop_json == ref) if (ref is not None and hop_json is not None) else None
        runs.append({"run": i, "wall_s": wall, "engine_ms_neo": eng_ms, "qids": qids, "error": err,
                     "equal_to_reference": same, "hops": hop_json})
        print(f"{args.variant} run {i}: wall={wall if wall is None else round(wall, 3)}s "
              f"err={'yes' if err else 'no'} equal_ref={same}", flush=True)

    if args.variant != "NEO":
        all_ids = [q for r in runs for q in r["qids"]]
        log = query_log(all_ids) if all_ids else {}
        for r in runs:
            per = [log.get(q, {}) for q in r["qids"]]
            r["engine_ms_ch"] = [p.get("query_duration_ms") for p in per]
            r["memory_bytes_per_hop"] = [p.get("memory_usage") for p in per]
            r["read_rows_per_hop"] = [p.get("read_rows") for p in per]
            r["read_bytes_per_hop"] = [p.get("read_bytes") for p in per]
            r["exception_codes"] = [p.get("exception_code") for p in per]

    warm = [r for r in runs[1:] if r["error"] is None]
    summary = {"variant": args.variant, "runs": len(runs), "failed_runs": sum(1 for r in runs if r["error"]),
               "warm_runs_used": len(warm)}
    if warm:
        summary["wall_s"] = summarise([r["wall_s"] for r in warm])
        if args.variant == "NEO":
            summary["engine_s"] = summarise([sum(r["engine_ms_neo"]) / 1000 for r in warm])
        else:
            summary["engine_s"] = summarise([sum(x or 0 for x in r["engine_ms_ch"]) / 1000 for r in warm])
            mems = [max(x or 0 for x in r["memory_bytes_per_hop"]) for r in runs if r["error"] is None]
            summary["peak_query_memory_bytes_all_runs"] = max(mems) if mems else None
            summary["read_bytes_per_trace_warm"] = summarise([sum(x or 0 for x in r["read_bytes_per_hop"]) for r in warm])
        summary["all_equal_to_reference"] = all(r["equal_to_reference"] for r in runs if r["error"] is None) \
            if ref is not None else None
    summary["frontier_sizes"] = [len(h) for h in runs[0]["hops"]] if runs[0]["hops"] else None
    json.dump({"summary": summary, "runs": runs, "hops": runs[0]["hops"]}, open(args.out, "w"), indent=1)
    print(json.dumps(summary, indent=1, default=str))


if __name__ == "__main__":
    main()
