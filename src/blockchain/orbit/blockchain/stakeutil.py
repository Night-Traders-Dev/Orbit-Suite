import time
from config.configutil import TXConfig, get_node_for_user
from blockchain.blockutil import add_block, load_chain
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
            if tx.recipient == username and isinstance(tx.note, dict) and "duration_days" in tx.note:
                lockups.append({
                    "amount": tx.amount,
                    "duration": tx.note["duration_days"],
                    "start_time": getattr(tx, "timestamp", time.time())
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

        users[username]["balance"] -= amount
        save_users(users)

        lock_tx = TXConfig.Transaction(
            sender="system",
            recipient=username,
            amount=amount,
            note={"duration_days": duration},
            timestamp=time.time()
        )
        add_block([lock_tx.to_dict()])
        print(f"Locked {amount:.4f} Orbit for {duration} days.")

    except ValueError:
        print("Invalid input.")


def claim_lockup_rewards(username):
    users = load_users()
    claimed = users[username].get("claimed_rewards", {})
    lockups = get_user_lockups(username)
    total_reward = 0
    reward_txs = []
    now = time.time()

    for lock in lockups:
        lock_start = lock["start_time"]
        duration_secs = lock["duration"] * 86400
        lock_end = lock_start + duration_secs
        last_claim = claimed.get(str(lock_start), lock_start)
        claim_until = min(now, lock_end)

        if last_claim >= claim_until:
            continue

        seconds_eligible = claim_until - last_claim
        reward = (lock["amount"] * LOCK_REWARD_RATE_PER_DAY / 86400) * seconds_eligible
        reward = round(reward, 6)

        if reward > 0:
            total_reward += reward
            claimed[str(lock_start)] = claim_until
            reward_txs.append(TXConfig.Transaction(
                sender="lockup_reward",
                recipient=username,
                amount=reward,
                note={"lock_start": lock_start, "claim_until": claim_until},
                timestamp=now
            ).to_dict())

    if total_reward == 0:
        print("No new rewards available to claim.")
        return

    # Calculate node fee (e.g., 3%) and adjust payout
    node_id = get_node_for_user(username)
    node_fee_rate = 0.03
    node_fee = round(total_reward * node_fee_rate, 6)
    net_reward = round(total_reward - node_fee, 6)

    # Add node fee transaction
    reward_txs.append(TXConfig.Transaction(
        sender=username,
        recipient="nodefeecollector",
        amount=node_fee,
        note={"type": f"Node Fee: {node_fee}", "node": node_id},
        timestamp=now
    ).to_dict())

    # Write reward transactions to the chain
    add_block(reward_txs, node_id)

    # Save claimed state
    users[username]["claimed_rewards"] = claimed
    save_users(users)

    print(f"Claimed {total_reward:.6f} Orbit in lockup rewards.")
    print(f"Node Fee: {node_fee:.6f} Orbit → Node {node_id}")
    print(f"Net credited: {net_reward:.6f} Orbit")

    # Ask user to re-lock or receive balance
    choice = input("Re-lock rewards for compounding? (y/n): ").strip().lower()
    if choice == 'y':
        try:
            duration = int(input("Enter new lockup duration in days (1 - 1825): "))
            if duration < 1 or duration > MAX_LOCK_DURATION_DAYS:
                print("Invalid duration.")
                return
            relock_tx = TXConfig.Transaction(
                sender="system",
                recipient=username,
                amount=net_reward,
                note={"duration_days": duration},
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
