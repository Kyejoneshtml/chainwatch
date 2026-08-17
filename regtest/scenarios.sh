#!/usr/bin/env bash
set -euo pipefail
COMPOSE="docker compose -f $HOME/chainwatch/docker-compose.regtest.yml"
b1() { $COMPOSE exec -T btc1 bitcoin-cli -conf=/config/bitcoin.conf "$@"; }
b2() { $COMPOSE exec -T btc2 bitcoin-cli -conf=/config/bitcoin.conf "$@"; }

b1 loadwallet "test" > /dev/null 2>&1 || b1 createwallet "test" > /dev/null 2>&1 || true
b2 loadwallet "test2" > /dev/null 2>&1 || b2 createwallet "test2" > /dev/null 2>&1 || true

jfield() { python3 -c "import sys,json; print(json.load(sys.stdin)$1)"; }

find_vout_for_address() {
  python3 -c "
import sys, json
d = json.load(sys.stdin)
addr = sys.argv[1]
for det in d['details']:
    if det.get('address') == addr and det.get('category') == 'receive':
        print(det['vout'])
        sys.exit(0)
sys.exit('no matching receive output for ' + addr)
" "$1"
}

amount_for_vout() {
  python3 -c "
import sys, json
d = json.load(sys.stdin)
vout = int(sys.argv[1])
for det in d['details']:
    if det.get('vout') == vout and det.get('category') == 'receive':
        print(det['amount'])
        sys.exit(0)
sys.exit('no matching receive amount for vout ' + str(vout))
" "$1"
}

# Reconnects and waits for equal height, regardless of what state the last
# scenario (or reorg.sh) left the harness in. Every scenario calls this
# first so none of them depend on a specific prior exit state.
sync_up() {
  b1 setnetworkactive true > /dev/null 2>&1 || true
  sleep 1
  b1 addnode "btc2:18444" "onetry" > /dev/null 2>&1 || true
  sleep 5
  local h1 h2 tries=0
  h1=$(b1 getblockcount)
  h2=$(b2 getblockcount)
  while [ "$h1" != "$h2" ] && [ "$tries" -lt 10 ]; do
    sleep 2
    h1=$(b1 getblockcount)
    h2=$(b2 getblockcount)
    tries=$((tries+1))
  done
  if [ "$h1" != "$h2" ]; then
    echo "FAIL - could not sync btc1 and btc2 before scenario (btc1=$h1 btc2=$h2)"
    exit 1
  fi
}

scenario_reorg_with_transactions() {
  sync_up

  local A1 A2 ADDR TXID DOOMED CONF_PRE CONF_DOOMED CONF_POST in_mempool=0

  A1=$(b1 getnewaddress)
  A2=$(b2 getnewaddress)
  ADDR=$(b1 getnewaddress)

  b1 setnetworkactive false > /dev/null
  sleep 2

  TXID=$(b1 sendtoaddress "$ADDR" 1)
  b1 generatetoaddress 1 "$A1" > /dev/null
  DOOMED=$(b1 getbestblockhash)

  CONF_PRE=$(b1 gettransaction "$TXID" | jfield "['confirmations']")
  echo "pre-reorg  txid=$TXID confirmations=$CONF_PRE"

  b2 generatetoaddress 3 "$A2" > /dev/null

  b1 setnetworkactive true > /dev/null
  sleep 2
  b1 addnode "btc2:18444" "onetry" > /dev/null 2>&1 || true
  sleep 8

  CONF_DOOMED=$(b1 getblock "$DOOMED" | jfield "['confirmations']")
  CONF_POST=$(b1 gettransaction "$TXID" | jfield "['confirmations']")
  echo "post-reorg doomed_block_confirmations=$CONF_DOOMED  txid_confirmations=$CONF_POST"

  b1 getmempoolentry "$TXID" > /dev/null 2>&1 && in_mempool=1

  if [ "$CONF_PRE" -gt 0 ] && [ "$CONF_DOOMED" = "-1" ] && [ "$CONF_POST" = "0" ] && [ "$in_mempool" = "1" ]; then
    echo "PASS - reorg-with-transactions: tx confirmed then returned to mempool with 0 confirmations after orphaning"
  else
    echo "FAIL - reorg-with-transactions: expected confirmations>0 then -1 (block) then 0 (tx) plus mempool membership; got pre=$CONF_PRE doomed=$CONF_DOOMED post=$CONF_POST in_mempool=$in_mempool"
    exit 1
  fi
}

scenario_chained_unconfirmed() {
  sync_up

  local ADDRA ADDRB TXA VOUTA AMTA FEE SENDAMT RAW SIGNED TXB gt txout_a ok=1

  ADDRA=$(b1 getnewaddress)
  ADDRB=$(b1 getnewaddress)

  TXA=$(b1 sendtoaddress "$ADDRA" 1)
  gt=$(b1 gettransaction "$TXA")
  VOUTA=$(echo "$gt" | find_vout_for_address "$ADDRA")
  AMTA=$(echo "$gt" | amount_for_vout "$VOUTA")

  FEE="0.0001"
  SENDAMT=$(python3 -c "print(f'{$AMTA - $FEE:.8f}')")
  RAW=$(b1 createrawtransaction "[{\"txid\":\"$TXA\",\"vout\":$VOUTA}]" "{\"$ADDRB\":$SENDAMT}")
  SIGNED=$(b1 signrawtransactionwithwallet "$RAW" | jfield "['hex']")
  TXB=$(b1 sendrawtransaction "$SIGNED")

  echo "TXA=$TXA (vout $VOUTA, unconfirmed)  TXB=$TXB (spends TXA:$VOUTA)"

  txout_a=$(b1 gettxout "$TXA" "$VOUTA" false)
  if [ -n "$txout_a" ]; then
    echo "FAIL - chained-unconfirmed: gettxout(A, include_mempool=false) returned a value, expected null"
    ok=0
  fi

  if b1 getmempoolentry "$TXA" > /dev/null 2>&1; then
    :
  else
    echo "FAIL - chained-unconfirmed: parent TXA missing from mempool, cannot classify as parent-pending"
    ok=0
  fi

  if b1 getmempoolentry "$TXB" > /dev/null 2>&1; then
    :
  else
    echo "FAIL - chained-unconfirmed: child TXB was not accepted into the mempool"
    ok=0
  fi

  if [ "$ok" = "1" ]; then
    echo "PASS - chained-unconfirmed: A's output invisible to gettxout(include_mempool=false) while A is pending; A's own mempool membership distinguishes this from a genuinely unresolvable input"
  else
    exit 1
  fi
}

scenario_rbf_replacement() {
  sync_up

  local ADDR TXID BUMPED NEWTXID A1 orig_conf new_conf

  ADDR=$(b1 getnewaddress)
  TXID=$(b1 -named send outputs="{\"$ADDR\":1}" options='{"replaceable":true,"fee_rate":1}' | jfield "['txid']")
  echo "original txid=$TXID"

  BUMPED=$(b1 bumpfee "$TXID")
  NEWTXID=$(echo "$BUMPED" | jfield "['txid']")
  echo "replacement txid=$NEWTXID"

  if b1 getmempoolentry "$TXID" > /dev/null 2>&1; then
    echo "FAIL - rbf-replacement: original txid still in mempool after bumpfee"
    exit 1
  fi

  A1=$(b1 getnewaddress)
  b1 generatetoaddress 2 "$A1" > /dev/null

  orig_conf=$(b1 gettransaction "$TXID" | jfield "['confirmations']")
  new_conf=$(b1 gettransaction "$NEWTXID" | jfield "['confirmations']")
  echo "after mining 2 blocks: original confirmations=$orig_conf  replacement confirmations=$new_conf"

  # A replaced tx never gets positive confirmations. Once the replacement
  # confirms, Core's wallet reports the original as negative (conflicted at
  # that depth), not exactly 0 - so "never confirms" is confirmations <= 0.
  if [ "$orig_conf" -le 0 ] && [ "$new_conf" -gt 0 ]; then
    echo "PASS - rbf-replacement: original left the mempool and never confirmed, replacement did"
  else
    echo "FAIL - rbf-replacement: expected original confirmations<=0 and replacement confirmations>0; got orig_conf=$orig_conf new_conf=$new_conf"
    exit 1
  fi
}

scenario_stale_transaction() {
  sync_up

  local ADDR MINE TXID i ok=1 conf

  ADDR=$(b1 getnewaddress)
  MINE=$(b1 getnewaddress)

  TXID=$(b1 -named send outputs="{\"$ADDR\":1}" options='{"fee_rate":1}' | jfield "['txid']")
  echo "stale candidate txid=$TXID"

  if ! b1 getmempoolentry "$TXID" > /dev/null 2>&1; then
    echo "FAIL - stale-transaction: tx not accepted into mempool"
    exit 1
  fi

  # generateblock with an explicit empty tx list deliberately excludes the
  # mempool. Regtest has no fee-market pressure, so generatetoaddress would
  # otherwise sweep this tx into the very next block regardless of fee.
  for i in 1 2 3; do
    b1 generateblock "$MINE" "[]" > /dev/null
    if ! b1 getmempoolentry "$TXID" > /dev/null 2>&1; then
      echo "FAIL - stale-transaction: tx left the mempool after block $i (should have been deliberately excluded)"
      ok=0
      break
    fi
  done

  conf=$(b1 gettransaction "$TXID" | jfield "['confirmations']")
  echo "after 3 excluded blocks: mempool membership held, confirmations=$conf"

  if [ "$ok" = "1" ] && [ "$conf" = "0" ]; then
    echo "PASS - stale-transaction: tx remained unconfirmed in the mempool across 3 mined blocks"
  else
    echo "FAIL - stale-transaction: expected confirmations=0 throughout; got $conf"
    exit 1
  fi
}

FAILED=0

run_scenario() {
  local name="$1" fn="$2"
  echo "=== $name ==="
  if ( set -euo pipefail; "$fn" ); then
    :
  else
    echo "FAIL - $name (unexpected error - see output above)"
    FAILED=1
  fi
  echo
}

case "${1:-all}" in
  reorg-with-transactions) run_scenario "reorg-with-transactions" scenario_reorg_with_transactions ;;
  chained-unconfirmed)     run_scenario "chained-unconfirmed" scenario_chained_unconfirmed ;;
  rbf-replacement)         run_scenario "rbf-replacement" scenario_rbf_replacement ;;
  stale-transaction)       run_scenario "stale-transaction" scenario_stale_transaction ;;
  all)
    run_scenario "reorg-with-transactions" scenario_reorg_with_transactions
    run_scenario "chained-unconfirmed" scenario_chained_unconfirmed
    run_scenario "rbf-replacement" scenario_rbf_replacement
    run_scenario "stale-transaction" scenario_stale_transaction
    ;;
  *)
    echo "usage: $0 [reorg-with-transactions|chained-unconfirmed|rbf-replacement|stale-transaction]"
    exit 2
    ;;
esac

exit $FAILED
