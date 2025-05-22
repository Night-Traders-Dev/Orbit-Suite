import time
from config.configutil import TXConfig, get_node_for_user
from blockchain.blockutil import add_block, load_chain
from blockchain.tokenutil import send_orbit
from core.userutil import load_users, save_users
from core.walletutil import load_balance

LOCK_REWARD_RATE_PER_DAY = 0.05
MIN_LOCK_AMOUNT = 0.0001
MAX_LOCK_DURATION_DAYS = 365 * 5  # 5 years max


def get_user_lockups(username):
    blockchain = load_chain()
    lockups = []
    for block in blockchain:
        for tx_data in block.get("transactions", []):
            tx = TXConfig.Transaction.from_dict(tx_data)
            tx_type = getattr(tx, "type", None)
            if tx.sender == username and tx_type == "lockup":
                lock_data = tx.note.get("lockup")
                if isinstance(lock_data, dict) and "start" in lock_data and "end" in lock_data:
                    duration = int((lock_data["end"] - lock_data["start"]) / 86400)
                    lockups.append({
                        "amount": tx.amount,
                        "duration": duration,
                        "start_time": lock_data["start"]
                    })
    return lockups

def print_lockups(lockups):
    if not lockups:
        print("No active lockups.")
        return
    print("Your Lockups:")
    for i, lock in enumerate(lockups):
        amount = lock["amount"]
        duration = lock["duration"]
        start = lock["start_time"]
        days_remaining = max(0, int((start + duration * 86400 - time.time()) / 86400))
        print(f" {i+1}. {amount:.4f} Orbit locked for {duration} days ({days_remaining} days remaining)")

def view_lockups(username):
    lockups = get_user_lockups(username)
    print_lockups(lockups)

def lock_tokens(username):
    users = load_users()
    balance, _ = load_balance(username)

    try:
        amount = float(input(f"Enter amount of Orbit to lock (available: {balance:.4f}): "))
        if amount < MIN_LOCK_AMOUNT or amount > balance:
            print("Invalid amount.")
            return

        duration = int(input("Enter lockup duration in days (min 1, max 1825): "))
        if duration < 1 or duration > MAX_LOCK_DURATION_DAYS:
            print(f"Duration must be between 1 and {MAX_LOCK_DURATION_DAYS} days.")
            return
        send_orbit(username, "lockup_rewards", amount, {"note": {lock_metadata}})
        print(f"Locked {amount:.4f} Orbit for {duration} days.")

    except ValueError:
        print("Invalid input.")



def withdraw_lockup(username):
    users = load_users()
    user = users[username]
    user_lockups = user.get("locked", [])
    now = time.time()

    matured_total = 0.0
    txs = []
    remaining_locked = []


    for i, lock in enumerate(lockups):
        amount = lock["amount"]
        duration = lock["duration"]
        start = lock["start_time"]
        lock_end = start + duration * 86400

        if now >= lock_end:
            matured_total += amount
        else:
            remaining_locked.append(lock)

    if matured_total == 0:
        print("No matured lockups available to withdraw.")
        return

    node_id = get_node_for_user(username)
    node_fee_rate = 0.02  # 2% withdrawal fee
    fee = round(matured_total * node_fee_rate, 6)
    payout = round(matured_total - fee, 6)

    print(f"Matured Amount: {matured_total:.6f} Orbit")
    print(f"Node Fee (2%): {fee:.6f} Orbit")
    print(f"Net Payout: {payout:.6f} Orbit")

    confirm = input("Proceed with withdrawal? (y/n): ").strip().lower()
    if confirm != 'y':
        print("Withdrawal cancelled.")
        return

    now = time.time()

    # Main withdrawal transaction
    txs.append(TXConfig.Transaction(
        sender="lockup_rewards",
        recipient=username,
        amount=payout,
        note={"type": "withdrawal", "total_locked": matured_total},
        timestamp=now
    ).to_dict())

    # Node fee transaction
    txs.append(TXConfig.Transaction(
        sender=username,
        recipient="nodefeecollector",
        amount=fee,
        note={"type": f"Lockup Withdrawal Fee: {fee}", "node": node_id},
        timestamp=now
    ).to_dict())

    # Write to chain
    add_block(txs, node_id)

    # Update user state
    user["locked"] = remaining_locked
    user["balance"] += payout
    save_users(users)

    print(f"{matured_total:.6f} Orbit withdrawn from matured lockups.")
    print(f"Node Fee: {fee:.6f} Orbit → Node {node_id}")
    print(f"{payout:.6f} Orbit added to your balance.")


def claim_lockup_rewards(username):
    users = load_users()
    user = users[username]
    user_lockups = user.get("locked", [])
    now = time.time()
    chain = load_chain()

    # Step 1: Extract most recent claim_until per lock_start from chain
    claim_map = {}
    for block in chain:
        for tx in block.get("transactions", []):
            if tx.get("recipient") == username and tx.get("sender") == "lockup_rewards":
                note = tx.get("note", {})
                if isinstance(note, dict) and "lock_start" in note and "claim_until" in note:
                    lock_start = str(note["lock_start"])
                    prev_claim = claim_map.get(lock_start, 0)
                    claim_map[lock_start] = max(prev_claim, note["claim_until"])

    matured_total = 0.0
    total_reward = 0.0
    reward_txs = []
    still_locked = []

    for lock in user_lockups:
        lock_start = lock["start_time"]
        duration = lock["duration"]
        amount = lock["amount"]
        lock_end = lock_start + duration * 86400
        last_claim = claim_map.get(str(lock_start), lock_start)
        claim_until = min(now, lock_end)

        # Unlock matured principal if reward has been claimed through or past lock_end
        if now >= lock_end and last_claim >= lock_end:
            matured_total += amount
        else:
            still_locked.append(lock)  # still in progress

        # Calculate eligible reward
        if last_claim < claim_until:
            seconds_eligible = claim_until - last_claim
            reward = (amount * LOCK_REWARD_RATE_PER_DAY / 86400) * seconds_eligible
            reward = round(reward, 6)

            if reward > 0:
                total_reward += reward
                reward_txs.append(TXConfig.Transaction(
                    sender="lockup_rewards",
                    recipient=username,
                    amount=reward,
                    note={},
                    timestamp=now
                ).to_dict())

    if total_reward == 0 and matured_total == 0:
        print("No new rewards or matured lockups available.")
        return

    node_id = get_node_for_user(username)
    node_fee = round(total_reward * 0.03, 6)
    net_reward = round(total_reward - node_fee, 6)

    if total_reward > 0:
        reward_txs.append(TXConfig.Transaction(
            sender=username,
            recipient="nodefeecollector",
            amount=node_fee,
            note={"type": f"Node Fee: {node_fee}", "node": node_id},
            timestamp=now
        ).to_dict())
        add_block(reward_txs, node_id)

    if matured_total > 0:
        user["balance"] += round(matured_total, 6)
        print(f"{matured_total:.6f} Orbit unlocked from matured lockups.")

    user["locked"] = still_locked
    save_users(users)

    if net_reward > 0:
        print(f"Claimed {total_reward:.6f} Orbit in lockup rewards.")
        print(f"Node Fee: {node_fee:.6f} Orbit → Node {node_id}")
        print(f"Net credited: {net_reward:.6f} Orbit")

        choice = input("Re-lock rewards for compounding? (y/n): ").strip().lower()
        if choice == 'y':
            try:
                duration = int(input("Enter new lockup duration in days (1 - 1825): "))
                if duration < 1 or duration > MAX_LOCK_DURATION_DAYS:
                    print("Invalid duration.")
                    return
                relock_tx = TXConfig.Transaction(
                    sender=username,
                    recipient="lockup_rewards",
                    amount=net_reward,
                    note={"duration": duration},
                    timestamp=time.time()
                )
                add_block([relock_tx.to_dict()], node_id)
                print(f"Re-locked {net_reward:.6f} Orbit for {duration} days.")
            except ValueError:
                print("Invalid duration.")
        else:
            users = load_users()
            users[username]["balance"] += net_reward
            save_users(users)
            print(f"{net_reward:.6f} Orbit added to your balance.")
