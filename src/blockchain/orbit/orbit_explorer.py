from flask import Flask, render_template, request, jsonify, redirect, url_for
import json, os, datetime, math
from config.configutil import OrbitDB
from blockchain.stakeutil import get_user_lockups
from templates.explorer_template import HTML_TEMPLATE

orbit_db = OrbitDB()
app = Flask(__name__)

CHAIN_PATH = orbit_db.blockchaindb
PAGE_SIZE = 5
PORT = 7000

LABELS = {
    "abcd1234": "Validator Node #1",
    "efgh5678": "Whale Wallet",
}


def load_chain():
    if os.path.exists(CHAIN_PATH):
        with open(CHAIN_PATH, 'r') as f:
            return json.load(f)
    return []


def search_chain(query):
    query = query.lower()
    if query.isdigit():
        return redirect(url_for('block_detail', index=int(query)))
    if len(query) >= 50:
        return redirect(url_for('tx_detail', txid=query))
    return redirect(url_for('address_detail', address=query))


def calculate_balance(address):
    balance = 0
    chain = load_chain()
    for block in chain:
        for tx in block.get("transactions", []):
            if tx["recipient"] == address:
                balance += tx["amount"]
            if tx["sender"] == address:
                balance -= tx["amount"]
    return balance


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
    stats = {}
    chain = load_chain()
    for block in chain:
        val = block.get("validator")
        if val:
            stats[val] = stats.get(val, 0) + 1
    total = sum(stats.values())
    return [{"validator": v, "blocks": c, "percent": round(100 * c / total, 2)} for v, c in sorted(stats.items(), key=lambda x: x[1], reverse=True)]


def get_chain_summary():
    chain = load_chain()
    tx_count = sum(len(b.get("transactions", [])) for b in chain)
    account_set = set()
    total_orbit = 0
    for b in chain:
        for tx in b.get("transactions", []):
            account_set.add(tx["sender"])
            account_set.add(tx["recipient"])
            total_orbit += tx["amount"]
    return {
        "blocks": len(chain),
        "transactions": tx_count,
        "accounts": len(account_set),
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

@app.route("/tx/<txid>")
def tx_detail(txid):
    chain = load_chain()
    for block in chain:
        for tx in block.get("transactions", []):
            current_id = f"{tx.get('sender')}-{tx.get('recipient')}-{tx.get('timestamp')}"
            if current_id == txid:
                note = tx.get("note", {})
                note_type = note.get("type", "N/A")
                confirmations = len(chain) - block["index"] - 1
                return {
                    "tx": tx,
                    "note_type": note_type,
                    "confirmations": confirmations,
                    "status": "Success" if tx.get("valid", True) else "Fail",
                    "fee": tx.get("fee", 0),
                    "proof": tx.get("signature", "N/A"),
                    "json": tx
                }
    return "Transaction not found", 404


@app.route("/block/<int:index>")
def block_detail(index):
    chain = load_chain()
    for block in chain:
        if block["index"] == index:
            txs = block.get("transactions", [])
            fee_txs = [tx for tx in txs if isinstance(tx.get("note"), dict) and "burn" in json.dumps(tx["note"])]
            return {
                "block": block,
                "fee_txs": len(fee_txs),
                "json": block
            }
    return "Block not found", 404


@app.route("/address/<address>")
def address_detail(address):
    balance = calculate_balance(address)
    locks = get_user_lockups(address)
    last10 = last_transactions(address)
    pending = [l for l in locks if not l.get("matured")]
    matured = [l for l in locks if l.get("matured")]
    label = LABELS.get(address, "")
    return {
        "address": address,
        "balance": balance,
        "lockups": locks,
        "pending_lockups": pending,
        "matured_lockups": matured,
        "claimable": sum(l.get("reward", 0) for l in matured),
        "last10": last10,
        "label": label
    }


@app.route("/validators")
def validator_stats():
    stats = get_validator_stats()
    return {"validators": stats}


@app.route("/api/docs")
def api_docs():
    return {
        "endpoints": [
            {"url": "/api/chain", "desc": "Full chain data"},
            {"url": "/api/block/<index>", "desc": "Block data by index"},
            {"url": "/api/tx/<txid>", "desc": "Transaction details by txid"},
            {"url": "/api/address/<address>", "desc": "Address profile"},
            {"url": "/api/summary", "desc": "Chain summary stats"}
        ]
    }


@app.route("/api/chain")
def api_chain():
    return jsonify(load_chain())


@app.route("/api/address/<address>")
def api_address(address):
    return jsonify({
        "balance": calculate_balance(address),
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


if __name__ == "__main__":
    app.run(port=PORT, debug=True)
