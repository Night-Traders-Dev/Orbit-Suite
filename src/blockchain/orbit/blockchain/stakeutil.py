import time
from config.configutil import TXConfig
from blockchain.blockutil import add_block, load_chain
from core.termutil import clear_screen
from core.userutil import load_users, save_users

def view_lockups(username):
    blockchain = load_chain()
    lockups = []

    for block in blockchain:
        for tx_data in block.get("transactions", []):
            tx = TXConfig.Transaction.from_dict(tx_data)
            if tx.recipient == username and isinstance(tx.note, dict) and "duration_days" in tx.note:
                duration = tx.note["duration_days"]
                lockups.append({
                    "amount": tx.amount,
                    "duration": duration,
                    "start_time": getattr(tx, "timestamp", time.time())
                })

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

def lock_tokens(username):
    users = load_users()
    user_data = users[username]
    balance = user_data.get("balance", 0)

    try:
        amount = float(input(f"Enter amount of Orbit to lock (available: {balance}): "))
        if amount <= 0 or amount > balance:
            print("Invalid amount.")
            return

        duration = int(input("Enter lockup duration in days (min 1): "))
        if duration < 1:
            print("Duration must be at least 1 day.")
            return

        user_data["balance"] -= amount
        users[username] = user_data
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
    blockchain = load_chain()
    total_reward = 0
    reward_txs = []
    now = time.time()

    for block in blockchain:
        for tx_data in block.get("transactions", []):
            tx = TXConfig.Transaction.from_dict(tx_data)

            if tx.recipient != username:
                continue
            if not isinstance(tx.note, dict) or "duration_days" not in tx.note:
                continue

            lock_start = tx.timestamp
            duration_secs = tx.note["duration_days"] * 86400
            lock_end = lock_start + duration_secs

            last_claim = claimed.get(str(lock_start), lock_start)
            claim_until = min(now, lock_end)

            if last_claim >= claim_until:
                continue

            seconds_eligible = claim_until - last_claim
            rate_per_day = 0.05
            rate_per_sec = (tx.amount * rate_per_day) / 86400

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
