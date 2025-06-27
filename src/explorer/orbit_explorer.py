from flask import Flask, render_template, request, jsonify, redirect, url_for, g, Response
import json, os, datetime, math, time, asyncio
from os import listdir
from os.path import isfile, join

from collections import defaultdict

from blockchain.stakeutil import get_user_lockups, lock_tokens, claim_lockup_rewards, check_claim
from blockchain.tokenutil import send_orbit
from blockchain.miningutil import start_mining, check_mining

from config.configutil import OrbitDB

from core.ioutil import load_chain, load_nodes
from core.orderutil import token_stats, BASE_PRICE, all_tokens_stats
from core.walletutil import load_balance
from core.cacheutil import get_cached, set_cached, clear_cache
from core.hashutil import create_2fa_secret, verify_2fa_token, generate_orbit_address
from core.authutil import update_login, is_logged_in, cleanup_expired_sessions
from core.tokenmeta import get_token_meta
from core.userutil import register, login

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
node_validation_proofs = {}
active_node_registry = {}


@app.before_request
def load_chain_once():
    g.chain = load_chain()

@app.template_filter('ts')
def format_timestamp(value):
    try:
        return datetime.datetime.fromtimestamp(value).strftime('%Y-%m-%d %H:%M:%S')
    except:
        return str(value)

@app.template_filter('commas')
def format_commas(value):
    return "{:,.0f}".format(value)

def is_thousand_milestone(chain_length):
    return chain_length % 1000 == 0 and chain_length != 0


def human_readable_age(delta):
    days = delta.days
    seconds = delta.seconds
    if days > 0:
        return f"{days} day{'s' if days != 1 else ''} ago"
    elif seconds >= 3600:
        return f"{seconds // 3600} hour{'s' if seconds // 3600 != 1 else ''} ago"
    elif seconds >= 60:
        return f"{seconds // 60} minute{'s' if seconds // 60 != 1 else ''} ago"
    return "just now"

# ===================== General UI Routes =====================


@app.route("/")
def get_home():
    query = request.args.get("q")
    if query:
        return search_chain(query)
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

@app.route("/locked")
def route_locked():
    html, locks, totals, sort = locked()
    return render_template(html, locks=locks, totals=totals, sort=sort)

@app.route("/top-wallets")
def get_top_wallets():
    html, wallet_data = top_wallets(g.chain)
    return render_template(html, wallets=wallet_data)


@app.route("/cache/clear")
def clear_explorer_cache():
    clear_cache()
    return "Explorer cache cleared", 200

@app.route("/mining")
def mining_stats():
    from blockchain.miningutil import get_dynamic_mining_rate
    from config.configutil import MiningConfig

    # Get dynamic rate and breakdown
    rate, breakdown = get_dynamic_mining_rate()

    # Estimate reward for 1 hour (3600s)
    estimated_reward = round(rate * 3600, 6)

    return render_template("mining.html",
                           rate=rate,
                           breakdown=breakdown,
                           reward=estimated_reward,
                           duration=3600)

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


@app.route("/node/<node_id>")
def load_node(node_id):
    node_data = load_nodes()
    chain = g.chain  # Assumes g.chain has already been set

    node_blocks = [block for block in chain if block.get("validator") == node_id]

    if node_id not in node_data:
        if not node_blocks:
            return render_template("node_not_found.html", node_id=node_id), 404


        # Add placeholder node data if only found via chain
        node_data[node_id] = {
            "id": node_id,
            "trust": 0.0,
            "uptime": 0.0,
            "address": "Unknown",
            "host": "Unknown",
            "port": "N/A",
            "last_seen": None,
            "users": []
        }

    # Pull flattened node info
    node = node_data.get(node_id, {})
    trust = round(node.get("trust", 0.0), 3)
    uptime = round(node.get("uptime", 0.0), 3)
    total_blocks = len(node_blocks)

    total_orbit = 0.0
    for block in node_blocks:
        for tx in block.get("transactions", []):
            note = tx.get("note", {})
            if note and "type" in note:
                gas_info = note["type"].get("gas")
                if gas_info:
                    total_orbit += gas_info.get("fee", 0.0)
                lock_info = note["type"].get("lockup")
                if lock_info:
                    total_orbit += lock_info.get("amount", 0.0)

                if tx.get("sender") == "mining":
                    mining_info = tx.get("amount")
                    if mining_info:
                        total_orbit += mining_info
            else:
                total_orbit += tx.get("amount", 0.0)

    # Average block size (tx count per block)
    avg_block_size = round(
        sum(len(block.get("transactions", [])) for block in node_blocks) / total_blocks,
        2
    ) if total_blocks else 0.0

    return render_template(
        "node_profile.html",
        node_id=node_id,
        blocks=node_blocks,
        trust=trust,
        uptime=uptime,
        total_blocks=total_blocks,
        total_orbit=total_orbit,
        avg_block_size=avg_block_size
    )



@app.route("/tokens")
def all_tokens():
    from datetime import datetime, timedelta, UTC
    from collections import defaultdict
    now = datetime.now(UTC)

    chain = load_chain()
    tokens = {}
    total_transfers = 0
    transfers_24h = 0
    new_tokens_24h = 0

    def parse_ts(ts_raw):
        if isinstance(ts_raw, str):
            return datetime.fromisoformat(ts_raw).replace(tzinfo=UTC)
        elif isinstance(ts_raw, (int, float)):
            return datetime.fromtimestamp(ts_raw, tz=UTC)
        return None

    for block in chain:
        for tx in block.get("transactions", []):
            note = tx.get("note")
            if not isinstance(note, dict):
                continue
            tx_type = note.get("type", {})
            ts = parse_ts(tx.get("timestamp"))

            # Token creation
            if "create_token" in tx_type:
                d = tx_type["create_token"]
                name = d.get("name")
                symbol = d.get("symbol")
                supply = float(d.get("supply", 0))
                creator = d.get("creator")
                timestamp = d.get("timestamp")

                if name and symbol:
                    tokens[symbol] = {
                        "symbol": symbol,
                        "name": name,
                        "supply": supply,
                        "creator": creator,
                        "created_at": timestamp,
                        "age": "",
                        "transfers": 0,
                        "holders": set()
                    }
                    ts_created = parse_ts(timestamp)
                    if ts_created and (now - ts_created <= timedelta(days=1)):
                        new_tokens_24h += 1

            # Transfer types: update holders and transfers
            for typ in ["buy_token", "sell_token", "token_transfer"]:
                if typ in tx_type:
                    d = tx_type[typ]
                    symbol = d.get("symbol") or d.get("token_symbol")
                    sender = d.get("sender")
                    receiver = d.get("receiver")

                    if symbol in tokens:
                        tokens[symbol]["transfers"] += 1
                        if sender:
                            tokens[symbol]["holders"].add(sender)
                        if receiver:
                            tokens[symbol]["holders"].add(receiver)

                    total_transfers += 1
                    if ts and (now - ts <= timedelta(days=1)):
                        transfers_24h += 1

    # Final formatting
    token_list = []
    for token in tokens.values():
        created_at = parse_ts(token["created_at"])
        if created_at:
            age = now - created_at
            days = age.days
            token["age"] = f"{days} day{'s' if days != 1 else ''}"
        else:
            token["age"] = "Unknown"
        token["holders"] = len(token["holders"])
        token_list.append(token)

    token_list = sorted(token_list, key=lambda x: x["symbol"].lower())

    metrics = {
        "total_transfers": total_transfers,
        "transfers_24h": transfers_24h,
        "total_tokens": len(tokens),
        "new_tokens_24h": new_tokens_24h
    }

    return render_template("tokens.html", tokens=token_list, metrics=metrics)


@app.route("/token/<symbol>")
def token_metrics(symbol):
    symbol_key = symbol.upper()
    cached = get_cached("token_stats", symbol_key)
    if cached:
        tokens, wallets, metrics = cached
    else:
        tokens, wallets, metrics = asyncio.run(all_tokens_stats(symbol_key))
        set_cached("token_stats", (tokens, wallets, metrics), symbol_key)
    token_sym = symbol.upper()
    icon_files = [f.split('.')[0] for f in listdir('static/token_icons') if isfile(join('static/token_icons', f))]
    try:
        token_meta = asyncio.run(get_token_meta(token_sym))


        return render_template("token_metrics.html", token=token_meta) #, top_wallets=wallets)

    except Exception as e:
        print(f"Error: {e}")
        return render_template("token_not_found.html", symbol=symbol, token_icon_symbols=icon_files), 404


# ===================== Auth + Identity APIs ==================


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
    registered = register(address, secret)
    if registered:
        return jsonify({"status": "success", "message": secret}), 200
    else:
        return jsonify({"status": "fail", "message": "account creation failed"}), 400

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


# ===================== Mining + Staking APIs =================
@app.route("/api/mine_check", methods=["POST"])
def api_mine_check():
    data = request.get_json()
    address = data.get("address")
    result = check_mining(address)
    return jsonify(result)


@app.route('/api/mine', methods=['POST'])
def api_mine():
    try:
        data = request.get_json()
        address = data.get('address')
        success, message = start_mining(address)
        if success:
            return jsonify({
                "status": "success",
                "rate": message["rate"],
                "mined": message["mined"],
                "payout": message["payout"]
            }), 200
        else:
            return jsonify({"status": "fail", "message": message}), 400

    except Exception as e:
        print(f"error: {str(e)}")
        return jsonify({"error": str(e)}), 500

@app.route('/api/lock', methods=['POST'])
def api_lock():
    try:
        data = request.get_json()
        address = data.get('address')
        amount = data.get('amount')
        duration = data.get('duration')
        success, message = lock_tokens(address, amount, duration)
        if success:
            return jsonify({
                "status": "success",
                "lockup_times": message["lockup_times"],
                "lockup_amount": message["lockup_amount"]
            }), 200
        else:
            return jsonify({"status": "fail", "message": message}), 400

    except Exception as e:
        return jsonify({"error": str(e)}), 500



@app.route("/api/claim", methods=["POST"])
def api_claim():
    data = request.get_json()
    address = data.get("address")
    relock_duration = data.get("relock_duration")  # Optional
    result = claim_lockup_rewards(address, relock_duration)
    return jsonify(result)

@app.route("/api/claim_check", methods=["POST"])
def api_claim_check():
    data = request.get_json()
    address = data.get("address")
    result = check_claim(address) or {"message": "N/A"}
    return jsonify(result)

# ===================== Token Operations APIs =================


@app.route('/api/send', methods=['POST'])
def api_send():
    try:
        data = request.get_json()

        # Validate input
        sender = data.get('sender')
        recipient = data.get('recipient')
        amount = data.get('amount')
        order = data.get('order')

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
        success, message = send_orbit(sender, recipient, amount, order)

        if success:
            return jsonify({"status": "success", "message": message}), 200
        else:
            return jsonify({"status": "fail", "message": message}), 400

    except Exception as e:
        return jsonify({"error": str(e)}), 500

@app.route('/api/balance/<address>', methods=['GET'])
def api_balance(address):
    try:
        amount, locked = load_balance(address)
        return jsonify({
            "total_balance": amount + locked,
            "available_balance": amount,
            "locked_balance": locked
        })
    except Exception as e:
        return jsonify({"error": "Failed to load balance", "details": str(e)}), 500

# ===================== Blockchain Data APIs ==================

@app.route("/api/latest-block")
def api_latest_block():
    result = latest_block(g.chain)
    return jsonify(result)

@app.route("/api/latest-transactions")
def api_latest_transactions():
    result = latest_txs(g.chain)
    return jsonify(result)

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



@app.route("/validators")
def validators():
    stats = get_validator_stats()
    return render_template("validators.html", validator_data=stats)


@app.route("/api/docs")
def api_docs():
    return render_template("api_docs.html")

@app.route("/api/chain")
def api_chain():
    if is_thousand_milestone(len(g.chain)):
        #Get active nodes
        active_nodes = active_node_registry
        if active_nodes:
            print(f"Active nodes at {len(g.chain)}: {len(active_nodes)}")
    else:
        active_nodes = active_node_registry
        if active_nodes:
            for node_id, data in active_nodes.items():
                last_seen = data.get("last_seen", 0)
                address = data.get("node", {}).get("address", "Unknown")
                user = data.get("node", {}).get("user", "Unknown")
                print(f"Node {node_id} last seen at {last_seen}, address: {address}, user: {user}")
                nodefeebalance, _ = load_balance("ORB.3C0738F00DE16991DDD5B506")
                print(f"Node Fee Balance: {nodefeebalance}")              
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


@app.route("/node_ping", methods=["POST"])
def node_ping():
    node = request.get_json()
    node_id = node.get("id")
    last_seen = time.time()

    if not node_id:
        return jsonify({"error": "Missing node ID"}), 400

    # Store by node_id directly
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


from flask import request, jsonify
import time

# You should have some persistent storage for proofs (e.g., file, DB)
node_proofs = {}

@app.route("/node_proof", methods=["POST"])
def node_proof():
    data = request.get_json()
    print(node_validation_proofs)

    node_id = data.get("node_id")
    latest_hash = data.get("latest_hash")
    proof_hash = data.get("proof_hash")

    if not node_id or not latest_hash or not proof_hash:
        return jsonify({"status": "error", "message": "Missing fields"}), 400

    node_validation_proofs[node_id] = {
        "timestamp": time.time(),
        "latest_hash": latest_hash,
        "proof_hash": proof_hash
    }

    return jsonify({"status": "success", "message": f"Proof received from {node_id}"}), 200


@app.route("/receive_block", methods=["POST"])
def receive_block():
    block_data = request.json
    # TODO: validate and append to chain if valid
    print(f"Received block proposal: {block_data.get('index')}")
    return "OK", 200

if __name__ == "__main__":
    host = '0.0.0.0'
    app.run(host=host, port=PORT, debug=False)
