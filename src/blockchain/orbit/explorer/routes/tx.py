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
                    if other_tx["recipient"] == "nodefeecollector":
                        tx_fee = other_tx['note']['type']['gas']['fee']
                        tx_node = other_tx['note']['type']['gas']['node']
                        fee_applied = {
                            "amount": tx_fee,
                            "node": tx_node,
                            "type": "gas"
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
