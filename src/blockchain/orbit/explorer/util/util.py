import json, os, datetime, math
from config.configutil import OrbitDB
from blockchain.stakeutil import get_user_lockups, get_all_lockups
from core.walletutil import load_balance
from blockchain.blockutil import load_chain
from blockchain.orbitutil import load_nodes
import time
from collections import defaultdict
from core.tx_types import TXTypes

def search_chain(query):
    query = query.lower()
    if query.isdigit():
        return redirect(url_for('block_detail', index=int(query)))
    if len(query) >= 50:
        return redirect(url_for('tx_detail', txid=query))
    return redirect(url_for('address_detail', address=query))


def last_transactions(address, limit=10):
    txs = []
    for block in reversed(load_chain()):
        for tx in block.get("transactions", []):
            if tx["sender"] == address or tx["recipient"] == address:
                txs.append(tx)
                if len(txs) >= limit:
                    return txs
    return txs



def get_validator_stats():
    nodes = load_nodes()
    chain = load_chain()

    block_counts = {}
    for block in chain:
        val = block.get("validator")
        if val:
            block_counts[val] = block_counts.get(val, 0) + 1

    total_blocks = sum(block_counts.values())

    stats = []
    for node in nodes:
        node_info = node.get("node", {})
        validator = node_info.get("id")
        if not validator:
            continue

        blocks = block_counts.get(validator, 0)
        percent = round(100 * blocks / total_blocks, 2) if total_blocks else 0
        trust = round(node_info.get("trust_score", 0.0), 3)
        uptime = round(node_info.get("uptime_score", 0.0), 3)

        stats.append({
            "validator": validator,
            "blocks": blocks,
            "percent": percent,
            "trust": trust,
            "uptime": uptime
        })

    stats.sort(key=lambda x: x["blocks"], reverse=True)
    return stats


def get_chain_summary():
    chain = load_chain()
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
