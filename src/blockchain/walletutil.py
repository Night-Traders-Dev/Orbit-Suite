import time
from userutil import load_users, save_users
from ledgerutil import load_blockchain

def show_balance(username):
    users = load_users()
    user_data = users.get(username, {"balance": 0, "locked": []})

    blockchain = load_blockchain()
    balance_from_ledger = 0
    locked_from_ledger = []

    for block in blockchain:
        for tx in block.get("transactions", []):
            tx_type = tx.get("type")

            # Infer transaction type if not explicitly given
            if not tx_type:
                if tx.get("from") == "mining":
                    tx_type = "mining"
                elif isinstance(tx.get("note"), dict) and "duration_days" in tx["note"]:
                    tx_type = "lockup"
                else:
                    tx_type = "transfer"

            # Process transfer
            if tx_type == "transfer":
                if tx.get("from") == username:
                    balance_from_ledger -= tx.get("amount", 0)
                if tx.get("to") == username:
                    balance_from_ledger += tx.get("amount", 0)

            # Process lockup
            elif tx_type == "lockup" and tx.get("to") == username:
                note = tx.get("note", {})
                duration = note.get("duration_days", 0)
                lock = {
                    "amount": tx.get("amount", 0),
                    "duration_days": duration,
                    "start_time": tx.get("timestamp", time.time())
                }
                locked_from_ledger.append(lock)
                balance_from_ledger -= lock["amount"]

            # Process mining reward
            elif tx_type == "mining" and tx.get("to") == username:
                balance_from_ledger += tx.get("amount", 0)

    current_time = time.time()
    active_locked = sum(
        lock["amount"]
        for lock in locked_from_ledger
        if current_time < lock["start_time"] + lock["duration_days"] * 86400
    )
    available = balance_from_ledger

    # Compare ledger-derived data with user.json
    user_balance = user_data.get("balance", 0)
    user_locked = user_data.get("locked", [])

    if abs(user_balance - available) > 1e-6 or user_locked != locked_from_ledger:
        print("Ledger mismatch detected. Updating user data to match ledger.")
        user_data["balance"] = round(available, 6)
        user_data["locked"] = locked_from_ledger
        users[username] = user_data
        save_users(users)

    print(f"Total Balance: {available + active_locked:.4f} Orbit")
    print(f"Locked: {active_locked:.4f} Orbit")
    print(f"Available: {available:.4f} Orbit")
