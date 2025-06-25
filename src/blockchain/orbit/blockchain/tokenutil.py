import time
from core.walletutil import load_balance
from core.ioutil import get_address_from_label
from blockchain.blockutil import add_block
from config.configutil import OrbitDB, TXConfig, get_node_for_user
from core.tx_util.tx_types import TXTypes

MIN_TRANSFER_AMOUNT = 0.000001
FEE_RATE = 0.02
NODE_FEE_ADDRESS = get_address_from_label("nodefeecollector")

def send_orbit(sender, recipient, amount, order=None):

    if recipient is "ORB.BURN":
        recipient = "ORB.00000000000000000000BURN"

    if len(sender) != 28 or len(recipient) != 28:
        return

    if recipient == sender:
        print("You cannot send Orbit to yourself.")
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
        tx_fee = TXTypes.GasTypes(fee, user_node, sender, NODE_FEE_ADDRESS)
        tx2 = TXConfig.Transaction(
            sender=sender,
            recipient=NODE_FEE_ADDRESS,
            amount=round(fee, 6),
            note=tx_fee.gas_tx(),
            timestamp=current_time

        )


        add_block([tx1.to_dict(), tx2.to_dict()], user_node)
        return "success", "dummy"
    except ValueError:
        print("Invalid amount input.")
