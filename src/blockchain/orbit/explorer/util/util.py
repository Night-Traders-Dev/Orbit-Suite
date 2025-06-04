import json, os, datetime, math
from config.configutil import OrbitDB
from blockchain.stakeutil import get_user_lockups, get_all_lockups
from core.walletutil import load_balance
from core.ioutil import load_nodes, fetch_chain
import time
from collections import defaultdict
from core.tx_util.tx_types import TXTypes

def search_chain(query):
    query = query.lower()
    if query.isdigit():
        return redirect(url_for('block_detail', index=int(query)))
    if len(query) >= 50:
        return redirect(url_for('tx_detail', txid=query))
    return redirect(url_for('address_detail', address=query))


def last_transactions(address, limit=10):
    txs = []
    for block in reversed(fetch_chain()):
        for tx in block.get("transactions", []):
            if tx["sender"] == address or tx["recipient"] == address:
                txs.append(tx)
                if len(txs) >= limit:
                    return txs
    return txs

def get_validator_stats():
    nodes = load_nodes()  # {"Node1": {id, address, host, port, uptime, trust, ...}, ...}
    chain = fetch_chain()

    # Count blocks validated by each node
    block_counts = {}
    for block in chain:
        validator = block.get("validator")
        if validator:
            block_counts[validator] = block_counts.get(validator, 0) + 1

    total_blocks = sum(block_counts.values()) or 1  # Avoid division by zero

    stats = []
    for node_id, node in nodes.items():
        blocks = block_counts.get(node_id, 0)
        percent = round(100 * blocks / total_blocks, 2)

        trust = round(node.get("trust", 0.0), 3)
        uptime = round(node.get("uptime", 0.0), 3)

        stats.append({
            "validator": node_id,
            "blocks": blocks,
            "percent": percent,
            "trust": trust,
            "uptime": uptime,
            "high_trust": trust > 0.9,
            "low_uptime": uptime < 0.5
        })

    stats.sort(key=lambda x: x["blocks"], reverse=True)
    return stats



def get_chain_summary():
    chain = fetch_chain()
    tx_count = sum(len(b.get("transactions", [])) for b in chain)
    account_set = set()
    total_orbit = 100000000
    circulating = (0 - total_orbit)
    for b in chain:
        for tx in b.get("transactions", []):
            account_set.add(tx["sender"])
            account_set.add(tx["recipient"])
            circulating += tx["amount"]
    return {
        "blocks": len(chain),
        "transactions": tx_count,
        "accounts": len(account_set),
        "circulating": circulating,
        "total_orbit": total_orbit
    }
