def tx_detail(txid, chain):
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

                return (
                    "tx_detail.html",
                    tx,
                    note_type,
                    confirmations,
                    "Success" if tx.get("valid", True) else "Fail",
                    tx.get("fee", 0),
                    tx.get("signature", "N/A"),
                    block["index"],
                    fee_applied
                )
    return "404"
