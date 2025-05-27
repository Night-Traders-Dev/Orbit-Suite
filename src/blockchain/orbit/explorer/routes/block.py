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
