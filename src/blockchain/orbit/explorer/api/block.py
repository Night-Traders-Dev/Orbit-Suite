@app.route("/api/block/<int:index>")
def api_block(index):
    chain = load_chain()
    for block in chain:
        if block["index"] == index:
            return jsonify(block)
    return jsonify({"error": "Block not found"}), 404
