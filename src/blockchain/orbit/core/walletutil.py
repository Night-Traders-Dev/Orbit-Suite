import time
from core.userutil import load_users, save_users
from blockchain.blockutil import load_chain
from config.configutil import TXConfig

def load_balance(username):
    users = load_users()
    user_data = users.get(username, {"balance": 0, "locked": []})

    blockchain = load_chain(username)
    balance_from_ledger = 0
    locked_from_ledger = []

    for block in blockchain:
        for tx_data in block.get("transactions", []):
            tx = TXConfig.Transaction.from_dict(tx_data)
            tx_type = getattr(tx, "type", None)

            # Infer transaction type if not explicitly given
            if not tx_type:
                if tx.sender == "mining":
                    tx_type = "mining"
                else:
                    tx_type = "transfer"

            # Process transfer
            if tx_type == "transfer":
                if tx.sender == username:
                    balance_from_ledger -= tx.amount
                if tx.recipient == username:
                    balance_from_ledger += tx.amount

            elif tx_type == "mining":
                if tx.recipient == username:
                    balance_from_ledger += tx.amount
                if tx.sender == username:
                    balance_from_ledger -= tx.amount

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

    return available, active_locked

