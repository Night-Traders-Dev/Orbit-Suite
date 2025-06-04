import time
from core.walletutil import load_balance
from core.ioutil import load_users, save_users
from blockchain.blockutil import add_block
from config.configutil import TXConfig, get_node_for_user
from core.tx_util.tx_types import TXTypes

MIN_TRANSFER_AMOUNT = 0.0001
FEE_RATE = 0.02

def send_orbit(sender, recipient, amount, order=None):
    users = load_users()

    if sender not in users:
        print("Sender not found.")
        return
    if recipient == sender:
        print("You cannot send Orbit to yourself.")
        return
    if recipient not in users:
        print("Recipient not found.")
        return

    try:
        amount = float(amount)
        if amount < MIN_TRANSFER_AMOUNT:
            print(f"Minimum transfer is {MIN_TRANSFER_AMOUNT} Orbit.")
            return

        available, _ = load_balance(sender)
        fee = round(amount * FEE_RATE, 6)
        total = round(amount + fee, 6)

        if total > available:
            print(f"Insufficient balance. Required: {total:.6f}, Available: {available:.6f}")
            return

        current_time = time.time()
        user_node = get_node_for_user(sender)
        # Transactions
        tx_note = order if order else None
        tx1 = TXConfig.Transaction(
            sender=sender,
            recipient=recipient,
            amount=round(amount, 6),
            note=tx_note,
            timestamp=current_time
        )
        tx_fee = TXTypes.GasTypes(fee, user_node, sender, "nodefeecollector")
        tx2 = TXConfig.Transaction(
            sender=sender,
            recipient="nodefeecollector",
            amount=fee,
            note=tx_fee.gas_tx(),
            timestamp=current_time

        )


        add_block([tx1.to_dict(), tx2.to_dict()], user_node)
        return "success", "dummy"
    except ValueError:
        print("Invalid amount input.")
