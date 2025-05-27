import json

def block_detail(index, chain):
    for block in chain:
        if block["index"] == index:
            txs = block.get("transactions", [])
            fee_txs = [tx for tx in txs if isinstance(tx.get("note"), dict) and "burn" in json.dumps(tx["note"])]
            return (
                "block_detail.html",
                block,
                txs,
                fee_txs
            )
    return "404"
