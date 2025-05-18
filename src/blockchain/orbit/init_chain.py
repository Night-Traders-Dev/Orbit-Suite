import os
import json
import hashlib
from config.configutil import OrbitDB

orbit_db = OrbitDB()

GENESIS_PATH = orbit_db.blockchaindb

def calculate_genesis_hash(block):
    block_copy = block.copy()
    block_copy["hash"] = ""
    block_string = json.dumps(block_copy, sort_keys=True)
    return hashlib.sha256(block_string.encode()).hexdigest()

def create_genesis_block():
    transactions = [
        {
            "sender": "genesis",
            "recipient": "lockup_reward",
            "amount": 100000.0,
            "timestamp": 0,
            "note": "Initial supply for lockup rewards"
        },
        {
            "sender": "genesis",
            "recipient": "mining",
            "amount": 1000000.0,
            "timestamp": 0,
            "note": "Initial supply for mining rewards"
        },
        {
            "sender": "genesis",
            "recipient": "system",
            "amount": 98900000.0,
            "timestamp": 0,
            "note": "Initial supply for system wallet"
        }
    ]

    block = {
        "index": 0,
        "timestamp": 0,
        "transactions": transactions,
        "previous_hash": "0" * 64,
        "hash": "",  # calculated below
        "validator": "genesis",
        "signatures": {},
        "merkle_root": "",
        "nonce": 0,
        "metadata": {
            "version": "1.0",
            "note": "Genesis Block for Orbit Chain"
        }
    }

    block["hash"] = calculate_genesis_hash(block)
    return block

def ensure_genesis_block():
    if not os.path.exists("data"):
        os.makedirs("data")

    if not os.path.exists(GENESIS_PATH):
        genesis_block = create_genesis_block()
        with open(GENESIS_PATH, "w") as f:
            json.dump([genesis_block], f, indent=4)
        print("Genesis block created at data/orbit_chain.json.")
    else:
        print("Genesis block already exists.")

if __name__ == "__main__":
    ensure_genesis_block()
