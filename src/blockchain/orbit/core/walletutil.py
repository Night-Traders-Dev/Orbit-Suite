import time, datetime
from blockchain.blockutil import load_chain
from config.configutil import TXConfig

def load_balance(username):
    blockchain = load_chain(username)
    balance = 0
    locked_from_ledger = []
    total_sent = 0
    total_received = 0

    for block in blockchain:
        for tx_data in block.get("transactions", []):
            tx = TXConfig.Transaction.from_dict(tx_data)
            note = (tx.note or "")
            is_sender = tx.sender == username
            is_recipient = tx.recipient == username

            # Tally totals
            if is_sender:
                total_sent += tx.amount
            if is_recipient:
                total_received += tx.amount

            # Transfer logic (default if note is empty or includes "transfer")
            if not note or "transfer" in note:
                if is_sender:
                    balance -= tx.amount
                if is_recipient:
                    balance += tx.amount

            # Mining reward
            elif "mining reward" in note:
                if is_recipient:
                    balance += tx.amount

            # Lockup transaction
            elif "lockup" in note:
                if is_sender:
                    locked_from_ledger.append({
                        "amount": tx.amount,
                        "start": tx.timestamp,
                        "days": tx.lock_duration,
                        "locked": tx.claim_until or (tx.timestamp + tx.lock_duration * 86400),
                    })
                    balance -= tx.amount

            # Claimed reward
            elif "claimed reward" in note:
                if is_recipient:
                    balance += tx.amount

    # Calculate currently locked amount from ledger
    current_time = time.time()
    active_locked = sum(
        lock["amount"]
        for lock in locked_from_ledger
        if current_time < lock["start"] + lock["days"] * 86400
    )

    return round(balance, 6), round(active_locked, 6)
