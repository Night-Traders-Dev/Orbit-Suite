from flask import request

def latest_block(chain):
    if chain:
        return chain[-1]
    return {"error": "No blocks found"}, 404


def latest_txs(chain):
    limit = int(request.args.get("limit", 5))
    txs = []
    for block in reversed(chain):
        for tx in reversed(block.get("transactions", [])):
            tx["block"] = block["index"]
            txs.append(tx)
            if len(txs) >= limit:
                return txs
    return txs
