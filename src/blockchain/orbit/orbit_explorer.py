from flask import Flask, render_template_string, request, jsonify
import json, os, datetime, math
from config.configutil import OrbitDB
from blockchain.stakeutil import get_user_lockups
from templates.explorer_template import HTML_TEMPLATE

orbit_db = OrbitDB()
app = Flask(__name__)

CHAIN_PATH = orbit_db.blockchaindb
PAGE_SIZE = 5
PORT = 7000

def load_chain():
    if os.path.exists(CHAIN_PATH):
        with open(CHAIN_PATH, 'r') as f:
            return json.load(f)
    return []

def search_chain(query):
    query = query.lower()
    matches = []
    for block in load_chain():
        for tx in block.get("transactions", []):
            tx_id = f"{tx.get('sender')}-{tx.get('recipient')}-{tx.get('timestamp')}"
            if (query in tx.get("sender", "").lower() or
                query in tx.get("recipient", "").lower() or
                query in json.dumps(tx).lower() or
                query in tx_id.lower()):
                matches.append({"block": block["index"], "tx": tx})
    return matches

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

@app.template_filter('ts')
def format_timestamp(value):
    try:
        return datetime.datetime.fromtimestamp(value).strftime('%Y-%m-%d %H:%M:%S')
    except:
        return str(value)

@app.route("/")
def home():
    query = request.args.get("q", "").strip()
    page = int(request.args.get("page", 1))
    chain = load_chain()
    results = search_chain(query) if query else []
    total_pages = max(1, math.ceil(len(chain) / PAGE_SIZE))
    start = (page - 1) * PAGE_SIZE
    end = start + PAGE_SIZE
    blocks = chain[::-1][start:end] if not query else []
    return render_template_string(HTML_TEMPLATE,
                                  chain=chain,
                                  results=results,
                                  query=query,
                                  page=page,
                                  total_pages=total_pages,
                                  blocks=blocks)

@app.route("/tx/<txid>")
def tx_detail(txid):
    chain = load_chain()
    for block in chain:
        for tx in block.get("transactions", []):
            current_id = f"{tx.get('sender')}-{tx.get('recipient')}-{tx.get('timestamp')}"
            if current_id == txid:
                note = tx.get("note", {})
                note_type = note.get("type", "N/A")
                return f'''
                <h1>Transaction Details</h1>
                <p><strong>Sender:</strong> {tx["sender"]}</p>
                <p><strong>Recipient:</strong> {tx["recipient"]}</p>
                <p><strong>Amount:</strong> {tx["amount"]} Orbit</p>
                <p><strong>Note Type:</strong> {note_type}</p>
                <p><strong>Note Content:</strong> <pre>{json.dumps(note, indent=2)}</pre></p>
                <p><strong>Timestamp:</strong> {format_timestamp(tx["timestamp"])}</p>
                <a href="/">Back</a>
                '''
    return "Transaction not found", 404

@app.route("/block/<int:index>")
def block_detail(index):
    chain = load_chain()
    for block in chain:
        if block["index"] == index:
            txs = block.get("transactions", [])
            fee_txs = [tx for tx in txs if isinstance(tx.get("note"), dict) and "burn" in json.dumps(tx["note"])]
            return f'''
            <h1>Block #{block["index"]}</h1>
            <p><strong>Timestamp:</strong> {format_timestamp(block["timestamp"])}</p>
            <p><strong>Hash:</strong> {block["hash"]}</p>
            <p><strong>Prev Hash:</strong> {block["previous_hash"]}</p>
            <p><strong>Validator:</strong> {block["validator"]}</p>
            <p><strong>Merkle Root:</strong> {block["merkle_root"]}</p>
            <p><strong>Nonce:</strong> {block["nonce"]}</p>
            <p><strong>Size:</strong> {len(txs)} txs</p>
            <p><strong>Fee Transactions:</strong> {len(fee_txs)}</p>
            <p><strong>Signatures:</strong> <pre>{json.dumps(block["signatures"], indent=2)}</pre></p>
            <h3>Transactions:</h3>
            <ul>
                {''.join(f"<li>{tx['sender']} → {tx['recipient']} ({tx['amount']} Orbit)" +
                         (f" [{tx['note'].get('type')}]" if isinstance(tx.get("note"), dict) and 'type' in tx['note'] else "") +
                         "</li>" for tx in txs)}
            </ul>
            <a href="/">Back</a>
            '''
    return "Block not found", 404

@app.route("/address/<address>")
def address_detail(address):
    balance = calculate_balance(address)
    locks = get_user_lockups(address)
    last10 = last_transactions(address)
    return f'''
    <h1>Address: {address}</h1>
    <p><strong>Current Balance:</strong> {balance} Orbit</p>
    <h3>Locked Balances:</h3>
    <ul>
        {''.join(f"<li>{l['amount']} Orbit locked until {format_timestamp(l['duration'])}</li>" for l in locks)}
    </ul>
    <h3>Last 10 Transactions:</h3>
    <ul>
        {''.join(f"<li>{tx['sender']} → {tx['recipient']} ({tx['amount']} Orbit) [{format_timestamp(tx['timestamp'])}]</li>" for tx in last10)}
    </ul>
    <a href="/">Back</a>
    '''

@app.route("/validators")
def validator_stats():
    stats = get_validator_stats()
    rows = "".join(f"<li>{s['validator']}: {s['blocks']} blocks ({s['percent']}%)</li>" for s in stats)
    return f"<h1>Validator Stats</h1><ul>{rows}</ul><a href='/'>Back</a>"

# New API Endpoints
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

if __name__ == "__main__":
    app.run(port=PORT, debug=True)
