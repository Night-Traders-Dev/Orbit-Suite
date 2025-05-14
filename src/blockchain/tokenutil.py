import time
from userutil import load_users, save_users
from ledgerutil import load_blockchain
from blockutil import add_block

def send_orbit(sender):
    users = load_users()
    if sender not in users:
        print("Sender not found.")
        return

    blockchain = load_blockchain()
    balance = 0
    locked_entries = []
    current_time = time.time()

    # Recalculate balance and lockups from the ledger
    for block in blockchain:
        for tx in block.get("transactions", []):
            tx_type = tx.get("type")

            if not tx_type:
                if tx.get("from") == "mining":
                    tx_type = "mining"
                elif isinstance(tx.get("note"), dict) and "duration_days" in tx["note"]:
                    tx_type = "lockup"
                else:
                    tx_type = "transfer"

            if tx_type == "transfer":
                if tx.get("from") == sender:
                    balance -= tx.get("amount", 0)
                if tx.get("to") == sender:
                    balance += tx.get("amount", 0)

            elif tx_type == "lockup" and tx.get("to") == sender:
                duration = tx.get("note", {}).get("duration_days", 0)
                start_time = tx.get("timestamp", current_time)
                amount = tx.get("amount", 0)
                locked_entries.append({
                    "amount": amount,
                    "duration_days": duration,
                    "start_time": start_time
                })
                balance -= amount

            elif tx_type == "mining" and tx.get("to") == sender:
                balance += tx.get("amount", 0)

    locked_amount = sum(
        l["amount"] for l in locked_entries
        if current_time < l["start_time"] + l["duration_days"] * 86400
    )
    available = balance

    try:
        recipient = input("Enter recipient username: ").strip()
        if recipient not in users:
            print("Recipient not found.")
            return
        if recipient == sender:
            print("You cannot send Orbit to yourself.")
            return

        amount = float(input(f"Enter amount to send (max {available:.4f}): "))
        if amount <= 0 or amount > available:
            print("Invalid amount.")
            return

        tx = {
            "from": sender,
            "to": recipient,
            "amount": amount,
            "timestamp": current_time
        }

        add_block([tx])

        print(f"Successfully sent {amount} Orbit to {recipient}.")

    except ValueError:
        print("Invalid input.")
