import time
from userutil import load_users, save_users
from ledgerutil import load_blockchain
from blockutil import add_block
from configutil import TXConfig  # Ensure TXConfig is properly imported

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
        for tx_data in block.get("transactions", []):
            tx = TXConfig.Transaction.from_dict(tx_data)

            # Determine transaction type
            tx_type = tx_data.get("type")
            if not tx_type:
                if tx.sender == "mining":
                    tx_type = "mining"
                elif isinstance(tx.note, dict) and "duration_days" in tx.note:
                    tx_type = "lockup"
                else:
                    tx_type = "transfer"

            if tx_type == "transfer":
                if tx.sender == sender:
                    balance -= tx.amount
                if tx.recipient == sender:
                    balance += tx.amount

            elif tx_type == "lockup" and tx.recipient == sender:
                duration = tx.note.get("duration_days", 0)
                start_time = tx.timestamp or current_time
                amount = tx.amount
                locked_entries.append({
                    "amount": amount,
                    "duration_days": duration,
                    "start_time": start_time
                })
                balance -= amount

            elif tx_type == "mining" and tx.recipient == sender:
                balance += tx.amount

    # Calculate locked and available balance
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

        tx = TXConfig.Transaction(
            sender=sender,
            recipient=recipient,
            amount=amount,
            timestamp=current_time
        )

        add_block([tx.to_dict()])

        print(f"Successfully sent {amount} Orbit to {recipient}.")

    except ValueError:
        print("Invalid input.")
