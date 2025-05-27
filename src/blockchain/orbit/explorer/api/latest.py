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
