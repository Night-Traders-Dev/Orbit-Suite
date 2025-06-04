@app.route("/api/tx/<txid>")
def api_tx(txid):
    chain = load_chain()
    for block in chain:
        for tx in block.get("transactions", []):
            current_id = f"{tx.get('sender')}-{tx.get('recipient')}-{tx.get('timestamp')}"
            if current_id == txid:
                return jsonify(tx)
    return jsonify({"error": "Transaction not found"}), 404
