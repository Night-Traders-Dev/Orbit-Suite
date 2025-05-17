import time
from core.walletutil import load_balance
from core.userutil import load_users, save_users
from blockchain.blockutil import add_block, load_chain
from config.configutil import TXConfig

def send_orbit(sender, recipient, amount, order: list = None):
    users = load_users()
    if sender not in users:
        print("Sender not found.")
        return

    blockchain = load_chain()
    balance = 0
    locked_entries = []
    current_time = time.time()

    available, active_locked = load_balance(sender)
    try:
        if recipient not in users:
            print("Recipient not found.")
            return
        if recipient == sender:
            print("You cannot send Orbit to yourself.")
            return

        if amount <= 0 or amount > available:
            print("Invalid amount.")
            return

        # Calculate dynamic burn fee (e.g., 2%)
        fee_rate = 0.02
        fee = round(amount * fee_rate, 4)
        net_amount = round(amount + fee, 4)

        if net_amount <= 0.01:
            print("Amount too small after fee deduction.")
            return

        if order is None:

            # Transaction to recipient
            tx1 = TXConfig.Transaction(
                sender=sender,
                recipient=recipient,
                amount=amount,
                timestamp=current_time
            )

        else:


            # Transaction to recipient
            tx1 = TXConfig.Transaction(
                sender=sender,
                recipient=recipient,
                amount=amount,
                note=order,
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

        print(f"Sent {amount:.4f} Orbit to {recipient} with {fee:.4f} Orbit burned as fee.")

    except ValueError:
        print("Invalid input.")
