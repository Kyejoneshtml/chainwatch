from rpc import RPCError

DUST_LIMIT_SATS = 546


def sats(btc_amount):
    # btc_amount is a Decimal (see rpc.py's parse_float=Decimal) carrying
    # at most 8 decimal places, so this multiplication is exact.
    return int(btc_amount * 100_000_000)


def is_coinbase(tx):
    return len(tx["vin"]) == 1 and "coinbase" in tx["vin"][0]


def decode_outputs(tx):
    outputs = []
    for vout in tx["vout"]:
        script = vout["scriptPubKey"]
        outputs.append({
            "position": vout["n"],
            "value": sats(vout["value"]),
            "address": script.get("address"),
            "script_type": script.get("type"),
        })
    return outputs


def resolve_input(rpc, vin):
    prev_txid = vin["txid"]
    prev_vout = vin["vout"]

    utxo = rpc.gettxout(prev_txid, prev_vout)
    if utxo is not None:
        value = sats(utxo["value"])
        return {
            "state": "resolved",
            "value": value,
            "address": utxo["scriptPubKey"].get("address"),
            "script_type": utxo["scriptPubKey"].get("type"),
            "is_dust": value <= DUST_LIMIT_SATS,
        }

    # gettxout returned null: the output is either genuinely gone from the
    # UTXO set for reasons other than being confirmed-spent, or its parent
    # transaction is itself still unconfirmed, so the output does not yet
    # exist under include_mempool=false. Distinguish by checking whether
    # the parent is in the mempool -- code -5 means it is not, any other
    # RPCError (or non-RPC exception) is a real failure and propagates.
    try:
        rpc.getmempoolentry(prev_txid)
        return {"state": "parent_pending", "value": None, "address": None,
                "script_type": None, "is_dust": False}
    except RPCError as exc:
        if exc.code == -5:
            return {"state": "unresolved", "value": None, "address": None,
                    "script_type": None, "is_dust": False}
        raise


def process_transaction(rpc, tx):
    outputs = decode_outputs(tx)
    output_value = sum(o["value"] for o in outputs)

    coinbase = is_coinbase(tx)
    inputs = [] if coinbase else [resolve_input(rpc, vin) for vin in tx["vin"]]

    resolved = sum(1 for i in inputs if i["state"] == "resolved")
    parent_pending = sum(1 for i in inputs if i["state"] == "parent_pending")
    unresolved = sum(1 for i in inputs if i["state"] == "unresolved")
    dust_count = sum(1 for i in inputs if i["is_dust"])

    if coinbase:
        fee = None
    elif resolved == len(inputs):
        input_value = sum(i["value"] for i in inputs)
        fee = input_value - output_value
    else:
        fee = None  # incomplete: some inputs pending or unresolved, fee unknown rather than approximated

    return {
        "txid": tx["txid"],
        "is_coinbase": coinbase,
        "outputs": outputs,
        "output_value": output_value,
        "inputs": inputs,
        "resolved": resolved,
        "parent_pending": parent_pending,
        "unresolved": unresolved,
        "dust_count": dust_count,
        "fee": fee,
    }
