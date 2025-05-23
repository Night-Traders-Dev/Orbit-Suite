import time, datetime
from blockchain.blockutil import load_chain
from config.configutil import TXConfig

chain = load_chain()
for block in chain:
    for tx in block.get("transactions", {}):
        if tx["sender"] == "blmvxer" and tx["recipient"] == "lockup_rewards":
            print(tx["note"]["type"]["lockup"]["amount"])

def load_balance(username):
    blockchain = load_chain(username)
    balance = 0
    locked_from_ledger = []
    total_sent = 0
    total_received = 0
    total_locked = 0

    for block in blockchain:
        for tx_data in block.get("transactions", []):
            tx = TXConfig.Transaction.from_dict(tx_data)
            note = (tx.note or "")
            is_sender = tx.sender == username
            is_recipient = tx.recipient == username
            for txdata in block.get("transactions", {}):
                if txdata["sender"] == username and txdata["recipient"] == "lockup_rewards":
                    total_locked += int((txdata["note"]["type"]["lockup"]["amount"]))


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
                        "end": tx.lock_duration,
                        "days": tx.claim_until,
                    })
                    balance -= tx.amount
                    total_locked += tx.amount

            # Claimed reward
            elif "claimed reward" in note:
                if is_recipient:
                    balance += tx.amount

    # Calculate currently locked amount from ledger
    balance = abs(total_received - total_sent)

    return round(balance, 6), round(total_locked, 6)
