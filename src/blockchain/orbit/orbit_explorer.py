from flask import Flask, render_template, request, jsonify, redirect, url_for, g
import json, os, datetime, math, time

from config.configutil import OrbitDB
from core.ioutil import load_chain, load_nodes
from core.walletutil import load_balance
from blockchain.stakeutil import get_user_lockups
from blockchain.tokenutil import send_orbit
from blockchain.miningutil import start_mining
from core.hashutil import create_2fa_secret, verify_2fa_token, generate_orbit_address
from core.authutil import update_login, is_logged_in, cleanup_expired_sessions

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
NodeRegistry = orbit_db.NodeRegistry

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

@app.route('/api/get_orbit_address', methods=['POST'])
def api_get_address():
    data = request.get_json()
    uid = data.get('uid')
    address = generate_orbit_address(uid)
    return jsonify({"status": "success", "address": address}), 200

@app.route('/api/create_2fa', methods=['POST'])
def api_create_2fa():
    data = request.get_json()
    address = data.get('address')
    secret = create_2fa_secret(address)
    return jsonify({"status": "success", "message": secret}), 200

@app.route('/api/verify_2fa', methods=['POST'])
def api_verift_2fa():
    data = request.get_json()
    address = data.get('address')
    totp = data.get('totp')
    print(f"{address}:{totp}")
    result = verify_2fa_token(address, int(totp))
    if result:
        update_login(address)
        return jsonify({"status": "success"}), 200
    else:
        return jsonify({"status": "fail"}), 400

@app.route('/api/mine', methods=['POST'])
def api_mine():
    try:
        data = request.get_json()
        user = data.get('user')
        success, rate, mined, reward = start_mining(user)
        message = [rate, mined, reward]
        if success:
            return jsonify({"status": "success", "message": message}), 200
        else:
            return jsonify({"status": "fail", "message": message}), 400

    except Exception as e:
        return jsonify({"error": str(e)}), 500


@app.route('/api/send', methods=['POST'])
def api_send():
    try:
        data = request.get_json()

        # Validate input
        sender = data.get('sender')
        recipient = data.get('recipient')
        amount = data.get('amount')

        if not sender or not recipient or amount is None:
            return jsonify({"error": "Missing required fields"}), 400

        # Convert and validate amount
        try:
            amount = float(amount)
            if amount <= 0:
                return jsonify({"error": "Amount must be greater than 0"}), 400
        except ValueError:
            return jsonify({"error": "Invalid amount format"}), 400

        # Call core logic
        success, message = send_orbit(sender, recipient, amount)

        if success:
            return jsonify({"status": "success", "message": message}), 200
        else:
            return jsonify({"status": "fail", "message": message}), 400

    except Exception as e:
        return jsonify({"error": str(e)}), 500

@app.route('/api/balance/<username>', methods=['GET'])
def api_balance(username):
    try:
        amount, locked = load_balance(username)
        return jsonify({
            "total_balance": amount + locked,
            "available_balance": amount,
            "locked_balance": locked
        })
    except Exception as e:
        return jsonify({"error": "Failed to load balance", "details": str(e)}), 500

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
    node_data = load_nodes()

    if node_id in node_data:
        # Node is found in registered nodes
        node_blocks = [block for block in g.chain if block.get("validator") == node_id]
    else:
        # Try to find node by scanning the chain
        node_blocks = [block for block in g.chain if block.get("validator") == node_id]

        # If still no blocks, return not found
        if not node_blocks:
            return render_template("node_not_found.html", node_id=node_id), 404

        # If found only via blocks, add minimal data
        node_data[node_id] = {
            "uptime": None,
            "trust": None
        }

    html, blocks, trust, uptime, total_blocks, total_orbit, avg_block_size = node_profile(
        node_id, node_data, g.chain
    )

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

active_node_registry = {}

@app.route("/node_ping", methods=["POST"])
def node_ping():
    data = request.get_json()
    node = data.get("node", {})
    node_id = node.get("id")
    last_seen = time.time()

    if not node_id:
        return jsonify({"error": "Missing node ID"}), 400

    # Store by node_id
    active_node_registry[node_id] = {
        "node": node,
        "last_seen": last_seen
    }

    return jsonify({"status": "registered", "node": node}), 200


@app.route("/active_nodes", methods=["GET"])
def active_nodes():
    now = time.time()
    cutoff = now - 120  # Only return nodes seen in the last 2 minutes
    fresh_nodes = {
        node_id: data for node_id, data in active_node_registry.items()
        if data.get("last_seen", 0) > cutoff
    }
    return jsonify(fresh_nodes), 200


@app.route("/receive_block", methods=["POST"])
def receive_block():
    block_data = request.json
    # TODO: validate and append to chain if valid
    print(f"Received block proposal: {block_data.get('index')}")
    return "OK", 200

if __name__ == "__main__":
    host = '0.0.0.0'
    app.run(host=host, port=PORT, debug=True)
