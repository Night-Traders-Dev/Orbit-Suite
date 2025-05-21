from flask import Flask, render_template, request, jsonify, redirect, url_for
import json, os, datetime, math
from config.configutil import OrbitDB
from blockchain.stakeutil import get_user_lockups
from core.walletutil import load_balance
from blockchain.blockutil import load_chain
from blockchain.orbitutil import load_nodes
import time
from collections import defaultdict

orbit_db = OrbitDB()
app = Flask(__name__)

CHAIN_PATH = orbit_db.blockchaindb
PAGE_SIZE = 5
PORT = 7000


def search_chain(query):
    query = query.lower()
    if query.isdigit():
        return redirect(url_for('block_detail', index=int(query)))
    if len(query) >= 50:
        return redirect(url_for('tx_detail', txid=query))
    return redirect(url_for('address_detail', address=query))


def last_transactions(address, limit=10):
    txs = []
    for block in reversed(load_chain()):
        for tx in block.get("transactions", []):
            if tx["sender"] == address or tx["recipient"] == address:
                txs.append(tx)
                if len(txs) >= limit:
                    return txs
    return txs


def get_validator_stats():
    nodes = load_nodes()
    chain = load_chain()

    # Count blocks produced per validator
    block_counts = {}
    for block in chain:
        val = block.get("validator")
        if val:
            block_counts[val] = block_counts.get(val, 0) + 1

    total_blocks = sum(block_counts.values())
    all_validators = set(block_counts.keys()).union(nodes.keys())

    stats = []
    for validator in sorted(all_validators):
        blocks = block_counts.get(validator, 0)
        percent = round(100 * blocks / total_blocks, 2) if total_blocks else 0
        node_info = nodes.get(validator, {})
        trust = round(node_info.get("trust_score", 0.0), 3)
        uptime = round(node_info.get("uptime_score", 0.0), 3)

        stats.append({
            "validator": validator,
            "blocks": blocks,
            "percent": percent,
            "trust": trust,
            "uptime": uptime
        })

    # Optional: Sort by blocks produced
    stats.sort(key=lambda x: x["blocks"], reverse=True)
    return stats

def get_chain_summary():
    chain = load_chain()
    tx_count = sum(len(b.get("transactions", [])) for b in chain)
    account_set = set()
    total_orbit = 100000000
    circulating = (0 - total_orbit)
    for b in chain:
        for tx in b.get("transactions", []):
            account_set.add(tx["sender"])
            account_set.add(tx["recipient"])
            circulating += tx["amount"]
    return {
        "blocks": len(chain),
        "transactions": tx_count,
        "accounts": len(account_set),
        "circulating": circulating,
        "total_orbit": total_orbit
    }



@app.template_filter('ts')
def format_timestamp(value):
    try:
        return datetime.datetime.fromtimestamp(value).strftime('%Y-%m-%d %H:%M:%S')
    except:
        return str(value)






@app.route("/")
def home():
    query = request.args.get("q", "").strip()
    if query:
        return search_chain(query)

    page = int(request.args.get("page", 1))
    chain = load_chain()
    total_pages = max(1, math.ceil(len(chain) / PAGE_SIZE))
    start = (page - 1) * PAGE_SIZE
    end = start + PAGE_SIZE
    blocks = chain[::-1][start:end]
    summary = get_chain_summary()

    return render_template("home.html",
                           chain=chain,
                           query=query,
                           page=page,
                           total_pages=total_pages,
                           blocks=blocks,
                           summary=summary)



@app.route("/api/tx_volume_14d")
def tx_volume_14d():
    from collections import defaultdict
    import time

    chain = load_chain()
    now = int(time.time())
    one_day = 86400

    tx_by_day = defaultdict(int)
    for block in chain:
        for tx in block.get("transactions", []):
            day = (tx.get("timestamp", block["timestamp"])) // one_day
            tx_by_day[day] += 1

    recent_days = [(now // one_day) - i for i in range(13, -1, -1)]
    data = []
    for day in recent_days:
        date_str = datetime.datetime.fromtimestamp(day * one_day).strftime("%b %d")
        data.append({
            "date": date_str,
            "count": tx_by_day.get(day, 0)
        })

    return jsonify(data)



@app.route("/locked")
def locked():
    chain = load_chain()
    now = time.time()
    user_filter = request.args.get("user", "").strip().lower()
    min_amount = float(request.args.get("min_amount", 0))
    min_days = int(request.args.get("min_days", 0))
    sort = request.args.get("sort", "date")

    locks = []
    total_claimed = 0.0

    for block in chain:
        for tx in block.get("transactions", []):
            note = tx.get("note", {})
            # Track claimed rewards
            if tx.get("sender") == "lockup_reward":
                total_claimed += float(tx.get("amount", 0))

            # Track lockups
            if isinstance(note, dict) and "duration_days" in note:
                duration = int(note["duration_days"])
                days_remaining = max(0, int((tx["timestamp"] + duration * 86400 - now) / 86400))
                entry = {
                    "username": tx["recipient"],
                    "amount": float(tx["amount"]),
                    "duration": duration,
                    "days_remaining": days_remaining,
                    "timestamp": tx["timestamp"]
                }
                if (
                    (not user_filter or user_filter in entry["username"].lower())
                    and entry["amount"] >= min_amount
                    and entry["duration"] >= min_days
                ):
                    locks.append(entry)

    if sort == "amount":
        locks.sort(key=lambda x: -x["amount"])
    elif sort == "user":
        locks.sort(key=lambda x: x["username"])
    else:
        locks.sort(key=lambda x: x["timestamp"])

    totals = {
        "total_locked": sum(lock["amount"] for lock in locks),
        "count": len(locks),
        "avg_days": round(sum(lock["duration"] for lock in locks) / len(locks), 1) if locks else 0,
        "total_claimed": round(total_claimed, 4)
    }

    return render_template("locked.html", locks=locks, totals=totals, sort=sort)

@app.route("/api/latest-block")
def api_latest_block():
    chain = load_chain()
    if chain:
        return jsonify(chain[-1])
    return jsonify({"error": "No blocks found"}), 404


@app.route("/api/latest-transactions")
def api_latest_transactions():
    limit = int(request.args.get("limit", 5))
    txs = []
    for block in reversed(load_chain()):
        for tx in reversed(block.get("transactions", [])):
            tx["block"] = block["index"]
            txs.append(tx)
            if len(txs) >= limit:
                return jsonify(txs)
    return jsonify(txs)

@app.route("/tx/<txid>")
def tx_detail(txid):
    chain = load_chain()
    for block in chain:
        txs = block.get("transactions", [])
        for tx in txs:
            current_id = f"{tx.get('sender')}-{tx.get('recipient')}-{tx.get('timestamp')}"
            if current_id == txid:
                # Search this block for a node fee transaction
                fee_applied = None
                for other_tx in txs:
                    note = other_tx.get("note")
                    if (isinstance(note, dict) and 
                        note.get("type", "").startswith("Node Fee") and 
                        other_tx.get("recipient") == "nodefeecollector"):
                        fee_applied = {
                            "amount": other_tx.get("amount"),
                            "node": note.get("node"),
                            "type": note.get("type")
                        }
                        break

                note_type = tx.get("note") or tx.get("metadata", {}).get("note")
                confirmations = len(chain) - block["index"] - 1

                return render_template("tx_detail.html",
                    tx=tx,
                    note_type=note_type,
                    confirmations=confirmations,
                    status="Success" if tx.get("valid", True) else "Fail",
                    fee=tx.get("fee", 0),
                    proof=tx.get("signature", "N/A"),
                    block_index=block["index"],
                    node_fee=fee_applied
                )
    return "Transaction not found", 404


@app.route("/top-wallets")
def top_wallets():
    chain = load_chain()
    balances = {}

    for block in chain:
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
    chain = load_chain()
    for block in chain:
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

    chain = load_chain()
    tx_count = 0
    total_sent = 0
    total_received = 0
    volume_by_day = defaultdict(lambda: {"in": 0, "out": 0})

    for block in chain:
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

    chart_data = []
    today = datetime.datetime.utcnow().date()
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
def node_profile(node_id):
    nodes = load_nodes()
    chain = load_chain()

    node_data = nodes.get(node_id)
    if not node_data:
        return "Node not found", 404

    # Filter blocks validated by this node
    blocks_validated = [b for b in chain if b.get("validator") == node_id]
    total_blocks = len(blocks_validated)
    trust = node_data.get("trust_score", 0)
    uptime = node_data.get("uptime_score", 0)

    total_orbit = 0
    total_tx_count = 0
    for block in blocks_validated:
        txs = block.get("transactions", [])
        total_tx_count += len(txs)
        for tx in txs:
            total_orbit += tx.get("amount", 0)

    avg_block_size = round(total_tx_count / total_blocks, 2) if total_blocks else 0

    return render_template("node_profile.html",
                           node_id=node_id,
                           blocks=blocks_validated,
                           trust=trust,
                           uptime=uptime,
                           total_blocks=total_blocks,
                           total_orbit=round(total_orbit, 4),
                           avg_block_size=avg_block_size)

@app.route("/api/docs")
def api_docs():
    return render_template("api_docs.html")

@app.route("/api/chain")
def api_chain():
    return jsonify(load_chain())


@app.route("/api/address/<address>")
def api_address(address):
    return jsonify({
        "balance": load_balance(address),
        "locked": get_user_lockups(address),
        "last_10_transactions": last_transactions(address)
    })


@app.route("/api/block/<int:index>")
def api_block(index):
    chain = load_chain()
    for block in chain:
        if block["index"] == index:
            return jsonify(block)
    return jsonify({"error": "Block not found"}), 404


@app.route("/api/tx/<txid>")
def api_tx(txid):
    chain = load_chain()
    for block in chain:
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
