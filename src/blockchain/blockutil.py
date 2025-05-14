# blockutil.py

import hashlib
import json
import time
import os
from orbitutil import propose_block

CHAIN_FILE = "data/orbit_chain.json"

def calculate_hash(index, previous_hash, timestamp, transactions):
    block_string = f"{index}{previous_hash}{timestamp}{json.dumps(transactions, sort_keys=True)}"
    return hashlib.sha256(block_string.encode()).hexdigest()

def create_genesis_block():
    genesis_block = {
        "index": 0,
        "timestamp": time.time(),
        "transactions": [],
        "previous_hash": "0",
        "hash": "",
    }
    genesis_block["hash"] = calculate_hash(
        genesis_block["index"],
        genesis_block["previous_hash"],
        genesis_block["timestamp"],
        genesis_block["transactions"]
    )
    return genesis_block

def load_chain():
    if not os.path.exists(CHAIN_FILE):
        return [create_genesis_block()]
    with open(CHAIN_FILE, "r") as f:
        return json.load(f)

def save_chain(chain):
    with open(CHAIN_FILE, "w") as f:
        json.dump(chain, f, indent=4)

def get_last_block():
    chain = load_chain()
    return chain[-1]

def add_block(transactions, node_id="nodeA"):
    chain = load_chain()
    last_block = chain[-1]
    new_block = {
        "index": len(chain),
        "timestamp": time.time(),
        "transactions": transactions,
        "previous_hash": last_block["hash"],
        "hash": ""
    }

    new_block["hash"] = calculate_hash(
        new_block["index"],
        new_block["previous_hash"],
        new_block["timestamp"],
        new_block["transactions"]
    )

    # Check consensus
    if propose_block(node_id, new_block):
        chain.append(new_block)
        save_chain(chain)
        print(f"Block {new_block['index']} added to Orbit chain.")
    else:
        print("Block rejected due to failed consensus.")

def is_chain_valid():
    chain = load_chain()
    for i in range(1, len(chain)):
        current = chain[i]
        previous = chain[i - 1]
        recalculated_hash = calculate_hash(
            current["index"],
            current["previous_hash"],
            current["timestamp"],
            current["transactions"]
        )
        if current["hash"] != recalculated_hash:
            return False
        if current["previous_hash"] != previous["hash"]:
            return False
    return True
