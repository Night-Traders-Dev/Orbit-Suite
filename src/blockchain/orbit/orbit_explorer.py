from flask import Flask, render_template, request, jsonify, redirect, url_for, g
import json, os, datetime, math
from config.configutil import OrbitDB
from blockchain.stakeutil import get_user_lockups, get_all_lockups
from core.walletutil import load_balance
from blockchain.blockutil import load_chain
from blockchain.orbitutil import load_nodes
import time
from collections import defaultdict
from core.tx_types import TXTypes

from explorer.api.latest import latest_block, latest_txs
from explorer.api.volume import tx_volume_14d, block_volume_14d, orbit_volume_14d
from explorer.routes.locked import locked
from explorer.routes.home import home
from explorer.routes.node import node_profile
from explorer.routes.orbitstats import orbit_stats
from explorer.routes.tx import tx_detail
from explorer.util.util import search_chain, last_transactions, get_validator_stats, get_chain_summary

orbit_db = OrbitDB()
app = Flask(__name__)

CHAIN_PATH = orbit_db.blockchaindb
PORT = 7000


@app.before_request
def load_chain_once():
    g.chain = load_chain()

@app.template_filter('ts')
def format_timestamp(value):
    try:
        return datetime.datetime.fromtimestamp(value).strftime('%Y-%m-%d %H:%M:%S')
    except:
        return str(value)



@app.route("/")
def get_home():
    (
        html,
        chain,
        query,
        page,
        total_pages,
        blocks,
        summary
    ) = home(g.chain)

    return render_template(html,
                           chain=chain,
                           query=query,
                           page=page,
                           total_pages=total_pages,
                           blocks=blocks,
                           summary=summary)



@app.route("/orbit-stats")
def get_orbit_stats():
    html, stats = orbit_stats(g.chain)

    return render_template(html, stats=stats)



@app.route("/api/orbit_volume_14d")
def orbit_volumed():
    result = orbit_volume_14d(g.chain, datetime.datetime.utcnow())
    return jsonify(result)


@app.route("/api/tx_volume_14d")
def tx_volume():
    data = tx_volume_14d(g.chain, int(time.time()))
    return jsonify(data)


@app.route("/api/block_volume_14d")
def block_volume():
    result = block_volume_14d(g.chain, datetime.datetime.utcnow())
    return jsonify(result)

@app.route("/locked")
def route_locked():
    html, locks, totals, sort = locked()
    return render_template(html, locks=locks, totals=totals, sort=sort)


@app.route("/api/latest-block")
def api_latest_block():
    result = latest_block(g.chain)
    return jsonify(result)

@app.route("/api/latest-transactions")
def api_latest_transactions():
    result = latest_txs(g.chain)
    return jsonify(result)
@app.route("/tx/<txid>")
def get_tx(txid):
    result = tx_detail(txid, g.chain)
    if result == "404":
        return "Transaction not found", 404
    else:
        (
            html,
            tx,
            note_type,
            confirmations,
            status,
            fee,
            proof,
            block_index,
            node_fee
        ) = result
        return render_template(html,
            tx=tx,
            note_type=note_type,
            confirmations=confirmations,
            status=status,
            fee=fee,
            proof=proof,
            block_index=block_index,
            node_fee=node_fee
        )

@app.route("/top-wallets")
def top_wallets():
    balances = {}

    for block in g.chain:
        for tx in block.get("transactions", []):
            sender = tx.get("sender")
            recipient = tx.get("recipient")
            amount = tx.get("amount", 0)

            if sender != "genesis":
                balances[sender] = balances.get(sender, 0) - amount
            balances[recipient] = balances.get(recipient, 0) + amount

    top_10 = sorted(balances.items(), key=lambda x: x[1], reverse=True)[:10]
    wallet_data = [{"address": addr, "balance": round(balance, 6)} for addr, balance in top_10]

    return render_template("top_wallets.html", wallets=wallet_data)

@app.route("/block/<int:index>")
def block_detail(index):
    for block in g.chain:
        if block["index"] == index:
            txs = block.get("transactions", [])
            fee_txs = [tx for tx in txs if isinstance(tx.get("note"), dict) and "burn" in json.dumps(tx["note"])]
            return render_template(
                "block_detail.html",
                block=block,
                txs=txs,
                fee_txs=fee_txs
            )
    return "Block not found", 404



@app.route("/address/<address>")
def address_detail(address):
    balance, active_locks = load_balance(address)
    locks = get_user_lockups(address)
    last10 = last_transactions(address)
    pending = [l for l in locks if not l.get("matured")]
    matured = [l for l in locks if l.get("matured")]

    tx_count = 0
    total_sent = 0
    total_received = 0
    volume_by_day = defaultdict(lambda: {"in": 0, "out": 0})

    for block in g.chain:
        for tx in block.get("transactions", []):
            ts = datetime.datetime.fromtimestamp(tx["timestamp"]).strftime("%Y-%m-%d")
            if tx["sender"] == address:
                total_sent += tx["amount"]
                volume_by_day[ts]["out"] += tx["amount"]
                tx_count += 1
            elif tx["recipient"] == address:
                total_received += tx["amount"]
                volume_by_day[ts]["in"] += tx["amount"]
                tx_count += 1

    avg_tx_size = round((total_sent + total_received) / tx_count, 4) if tx_count else 0
    balance = abs(total_received - total_sent)
    chart_data = []
    today = datetime.datetime.now(datetime.UTC)
    for i in range(14):
        day = today - datetime.timedelta(days=i)
        label = day.strftime("%Y-%m-%d")
        chart_data.append({
            "date": label,
            "in": round(volume_by_day[label]["in"], 4),
            "out": round(volume_by_day[label]["out"], 4)
        })
    chart_data.reverse()

    data = {
        "address": address,
        "balance": balance,
        "lockups": locks,
        "pending_lockups": pending,
        "matured_lockups": matured,
        "claimable": sum(l.get("reward", 0) for l in matured),
        "last10": last10,
        "total_sent": total_sent,
        "total_received": total_received,
        "avg_tx_size": avg_tx_size,
        "tx_count": tx_count,
        "chart_data": chart_data
    }

    if request.args.get("json") == "1":
        return jsonify(data)

    return render_template("address.html", address_data=data)

@app.route("/validators")
def validators():
    stats = get_validator_stats()
    return render_template("validators.html", validator_data=stats)

@app.route("/node/<node_id>")
def load_node(node_id):
    nodes = load_nodes()
    (
        html,
        blocks,
        trust,
        uptime,
        total_blocks,
        total_orbit,
        avg_block_size
    ) = node_profile(node_id, nodes, g.chain)

    return render_template(
        html,
        node_id=node_id,
        blocks=blocks,
        trust=trust,
        uptime=uptime,
        total_blocks=total_blocks,
        total_orbit=total_orbit,
        avg_block_size=avg_block_size
    )


@app.route("/api/docs")
def api_docs():
    return render_template("api_docs.html")

@app.route("/api/chain")
def api_chain():
    return jsonify(g.chain)


@app.route("/api/address/<address>")
def api_address(address):
    return jsonify({
        "balance": load_balance(address),
        "locked": get_user_lockups(address),
        "last_10_transactions": last_transactions(address)
    })


@app.route("/api/block/<int:index>")
def api_block(index):
    for block in g.chain:
        if block["index"] == index:
            return jsonify(block)
    return jsonify({"error": "Block not found"}), 404


@app.route("/api/tx/<txid>")
def api_tx(txid):
    for block in g.chain:
        for tx in block.get("transactions", []):
            current_id = f"{tx.get('sender')}-{tx.get('recipient')}-{tx.get('timestamp')}"
            if current_id == txid:
                return jsonify(tx)
    return jsonify({"error": "Transaction not found"}), 404


@app.route("/api/summary")
def api_summary():
    return jsonify(get_chain_summary())

@app.route("/ping")
def ping():
    return "pong", 200

@app.route("/receive_block", methods=["POST"])
def receive_block():
    block_data = request.json
    # TODO: validate and append to chain if valid
    print(f"Received block proposal: {block_data.get('index')}")
    return "OK", 200

if __name__ == "__main__":
    app.run(port=PORT, debug=True)
