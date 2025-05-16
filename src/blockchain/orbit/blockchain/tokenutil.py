import time
from core.userutil import load_users, save_users
from blockchain.blockutil import add_block, load_chain
from config.configutil import TXConfig

def send_orbit(sender):
    users = load_users()
    if sender not in users:
        print("Sender not found.")
        return

    blockchain = load_chain()
    balance = 0
    locked_entries = []
    current_time = time.time()

    for block in blockchain:
        for tx_data in block.get("transactions", []):
            tx = TXConfig.Transaction.from_dict(tx_data)

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

        # Calculate dynamic burn fee (e.g., 2%)
        fee_rate = 0.02
        fee = amount * fee_rate
        net_amount = amount - fee

        if net_amount <= 0:
            print("Amount too small after fee deduction.")
            return

        # Transaction to recipient
        tx1 = TXConfig.Transaction(
            sender=sender,
            recipient=recipient,
            amount=net_amount,
            timestamp=current_time
        )

        # Burn transaction
        tx2 = TXConfig.Transaction(
            sender=sender,
            recipient="burn",
            amount=fee,
            note={"type": "burn_fee"},
            timestamp=current_time
        )

        add_block([tx1.to_dict(), tx2.to_dict()])

        print(f"Sent {net_amount:.4f} Orbit to {recipient} with {fee:.4f} Orbit burned as fee.")

    except ValueError:
        print("Invalid input.")
