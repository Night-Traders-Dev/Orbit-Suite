from flask import Flask, render_template, request, jsonify, redirect, url_for, g
import json, os, datetime, math, time

from config.configutil import OrbitDB
from core.ioutil import load_chain, load_nodes

from explorer.api.latest import latest_block, latest_txs
from explorer.api.volume import tx_volume_14d, block_volume_14d, orbit_volume_14d
from explorer.routes.address import address_detail
from explorer.routes.block import block_detail
from explorer.routes.locked import locked
from explorer.routes.home import home
from explorer.routes.node import node_profile
from explorer.routes.orbitstats import orbit_stats
from explorer.routes.topwallets import top_wallets
from explorer.routes.tx import tx_detail
from explorer.util.util import search_chain, last_transactions, get_validator_stats, get_chain_summary

orbit_db = OrbitDB()
app = Flask(__name__)

CHAIN_PATH = orbit_db.blockchaindb
PORT = 7000


@app.before_request
def load_chain_once():
    g.chain = load_chain()

@app.before_request
def load_nodes_once():
    g.nodes = load_nodes()

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
def get_top_wallets():
    html, wallet_data = top_wallets(g.chain)
    return render_template(html, wallets=wallet_data)

@app.route("/block/<int:index>")
def get_block(index):
    result = block_detail(index, g.chain)
    if result == "404":
        return "Transaction not found", 404
    else:
        (
            html,
            block,
            txs,
            fee_txs
        ) = result
        return render_template(
            html,
            block=block,
            txs=txs,
            fee_txs=fee_txs
        )



@app.route("/address/<address>")
def get_address_detail(address):
    html, data = address_detail(address, g.chain)
    if request.args.get("json") == "1":
        return jsonify(data)

    return render_template(html, address_data=data)

@app.route("/validators")
def validators():
    stats = get_validator_stats()
    return render_template("validators.html", validator_data=stats)

@app.route("/node/<node_id>")
def load_node(node_id):
    (
        html,
        blocks,
        trust,
        uptime,
        total_blocks,
        total_orbit,
        avg_block_size
    ) = node_profile(node_id, g.nodes, g.chain)

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
