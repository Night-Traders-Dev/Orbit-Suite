import json
import os
from datetime import datetime

BLOCKCHAIN_FILE = "data/orbit_chain.json"

def load_blockchain():
    if not os.path.exists(BLOCKCHAIN_FILE):
        return []
    with open(BLOCKCHAIN_FILE, "r") as f:
        return json.load(f)

def format_transaction(tx):
    try:
        if isinstance(tx, dict) and "timestamp" in tx:
            ts = datetime.fromtimestamp(tx["timestamp"]).strftime("%Y-%m-%d %H:%M:%S")
            return (
                f"[{ts}] {tx.get('from')} -> {tx.get('to')} | "
                f"{tx['amount']} Orbit | Note: {tx.get('note', 'N/A')}"
            )
        else:
            raise ValueError("Invalid transaction format.")
    except Exception as e:
        print(f"Error formatting transaction: {e}")
        return "Invalid transaction data"

def view_all_transactions():
    blockchain = load_blockchain()
    print("\n=== Full Orbit Ledger ===")
    for block in blockchain:
        for tx in block.get("transactions", []):
            print(format_transaction(tx))

def view_user_transactions(username):
    blockchain = load_blockchain()
    print(f"\n=== Transactions for {username} ===")
    found = False
    for block in blockchain:
        for tx in block.get("transactions", []):
            if tx.get("from") == username or tx.get("to") == username:
                print(format_transaction(tx))
                found = True
    if not found:
        print("No transactions found for this user.")

def view_mining_rewards(username):
    blockchain = load_blockchain()
    print(f"\n=== Mining Rewards for {username} ===")
    found = False
    for block in blockchain:
        for tx in block.get("transactions", []):
            if tx.get("from") == "mining" and tx.get("to") == username:
                print(format_transaction(tx))
                found = True
    if not found:
        print("No mining rewards found.")

def view_transfers(username):
    blockchain = load_blockchain()
    print(f"\n=== Transfers by/to {username} ===")
    found = False
    for block in blockchain:
        for tx in block.get("transactions", []):
            if tx.get("note") != "Mining Reward" and (
                tx.get("from") == username or tx.get("to") == username
            ):
                print(format_transaction(tx))
                found = True
    if not found:
        print("No transfer records found.")
