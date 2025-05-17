import time
from config.configutil import TXConfig
from blockchain.blockutil import add_block, load_chain
from core.userutil import load_users, save_users
from core.walletutil import load_balance

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
        print(f" {i+1}. {amount} Orbit locked for {duration} days ({days_remaining} days remaining)")

def view_lockups(username):
    lockups = get_user_lockups(username)
    print_lockups(lockups)

def lock_tokens(username):
    users = load_users()
    balance, _ = load_balance(username)

    try:
        amount = float(input(f"Enter amount of Orbit to lock (available: {balance}): "))
        if amount <= 0 or amount > balance:
            print("Invalid amount.")
            return

        duration = int(input("Enter lockup duration in days (min 1): "))
        if duration < 1:
            print("Duration must be at least 1 day.")
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

        print(f"Locked {amount} Orbit for {duration} days.")

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
        rate_per_day = 0.05
        rate_per_sec = (lock["amount"] * rate_per_day) / 86400

        reward = seconds_eligible * rate_per_sec
        if reward > 0:
            total_reward += reward
            claimed[str(lock_start)] = claim_until

            reward_tx = TXConfig.Transaction(
                sender="lockup_reward",
                recipient=username,
                amount=reward,
                note={"lock_start": lock_start, "claim_until": claim_until},
                timestamp=now
            )
            reward_txs.append(reward_tx.to_dict())

    if reward_txs:
        add_block(reward_txs)

    users[username]["claimed_rewards"] = claimed
    save_users(users)

    if total_reward > 0:
        print(f"Claimed {total_reward:.6f} Orbit in lockup rewards.")
        choice = input("Would you like to re-lock your claimed rewards (compound)? (y/n): ").lower()
        if choice == 'y':
            try:
                duration = int(input("Enter new lockup duration in days: "))
                if duration < 1:
                    print("Duration must be at least 1 day.")
                    return

                relock_tx = TXConfig.Transaction(
                    sender="system",
                    recipient=username,
                    amount=total_reward,
                    note={"duration_days": duration},
                    timestamp=time.time()
                )
                add_block([relock_tx.to_dict()])
                print(f"Re-locked {total_reward:.6f} Orbit for {duration} days.")
            except ValueError:
                print("Invalid duration input.")
        else:
            users = load_users()
            users[username]["balance"] += total_reward
            save_users(users)
            print(f"{total_reward:.6f} Orbit added to your balance.")
    else:
        print("No new rewards available to claim.")
