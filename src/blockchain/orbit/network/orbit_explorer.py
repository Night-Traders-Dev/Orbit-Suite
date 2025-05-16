from flask import Flask, render_template_string, request
import json
import os
import datetime

app = Flask(__name__)

CHAIN_PATH = "data/orbit_chain.json"
PORT = 7000

# Load the blockchain
def load_chain():
    if os.path.exists(CHAIN_PATH):
        with open(CHAIN_PATH, 'r') as f:
            return json.load(f)
    return []

# Search transactions by address or tx hash
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

HTML_TEMPLATE = '''
<!DOCTYPE html>
<html>
<head>
    <title>Orbit Block Explorer</title>
    <style>
        body { font-family: Arial; margin: 40px; background: #f4f4f4; }
        h1 { color: #333; }
        .block, .tx { background: #fff; padding: 20px; margin-bottom: 20px; border-radius: 8px; box-shadow: 0 0 8px rgba(0,0,0,0.1); overflow-x: auto; }
        .tx { margin-left: 20px; }
        code { background: #eee; padding: 2px 4px; border-radius: 4px; }
        input[type="text"] { width: 400px; padding: 8px; margin-right: 10px; }
        button { padding: 8px 12px; }
    </style>
</head>
<body>
    <h1>Orbit Blockchain Explorer</h1>

    <form method="get">
        <input type="text" name="q" placeholder="Search by address or tx ID..." value="{{ query }}"/>
        <button type="submit">Search</button>
    </form>

    {% if results %}
        <h2>Search Results for "{{ query }}"</h2>
        {% for match in results %}
        <div class="tx">
            <strong>Block:</strong> {{ match.block }}<br>
            <strong>Sender:</strong> {{ match.tx.sender }}<br>
            <strong>Recipient:</strong> {{ match.tx.recipient }}<br>
            <strong>Amount:</strong> {{ match.tx.amount }} Orbit<br>
            <strong>Note:</strong> {{ match.tx.note }}<br>
            <strong>Timestamp:</strong> {{ match.tx.timestamp | ts }}
        </div>
        {% endfor %}
    {% else %}
        {% for block in chain[::-1] %}
        <div class="block">
            <strong>Block #{{ block.index }}</strong><br>
            <strong>Timestamp:</strong> {{ block.timestamp | ts }}<br>
            <strong>Hash:</strong> <code>{{ block.hash }}</code><br>
            <strong>Prev Hash:</strong> <code>{{ block.previous_hash }}</code><br>
            <strong>Validator:</strong> {{ block.validator }}<br>
            <strong>Merkle Root:</strong> <code>{{ block.merkle_root }}</code><br>
            <strong>Nonce:</strong> {{ block.nonce }}<br>
            <strong>Signatures:</strong> <pre>{{ block.signatures }}</pre>
            <hr>
            <strong>Transactions:</strong>
            {% for tx in block.transactions %}
                <div class="tx">
                    <strong>From:</strong> {{ tx.sender }}<br>
                    <strong>To:</strong> {{ tx.recipient }}<br>
                    <strong>Amount:</strong> {{ tx.amount }} Orbit<br>
                    <strong>Note:</strong> {{ tx.note }}<br>
                    <strong>Timestamp:</strong> {{ tx.timestamp | ts }}<br>
                </div>
            {% endfor %}
        </div>
        {% endfor %}
    {% endif %}
</body>
</html>
'''

@app.template_filter('ts')
def format_timestamp(value):
    try:
        return datetime.datetime.fromtimestamp(value).strftime('%Y-%m-%d %H:%M:%S')
    except:
        return str(value)

@app.route("/")
def home():
    query = request.args.get("q", "").strip()
    chain = load_chain()
    results = search_chain(query) if query else []
    return render_template_string(HTML_TEMPLATE, chain=chain, query=query, results=results)

if __name__ == "__main__":
    app.run(port=PORT, debug=True)
