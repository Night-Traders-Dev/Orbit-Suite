import time
import json
import os
import hashlib
import rsa
import threading
from blockutil import add_block, start_listener, load_chain
from configutil import TXConfig, assign_node_to_user, load_active_sessions
from orbitutil import load_nodes

USERS_FILE = "data/users.json"
NODES_FILE = "data/nodes.json"

def load_users():
    if os.path.exists(USERS_FILE):
        with open(USERS_FILE, "r") as f:
            return json.load(f)
    return {}

def save_users(users):
    with open(USERS_FILE, "w") as f:
        json.dump(users, f, indent=4)

def hash_password(password):
    return hashlib.sha256(password.encode()).hexdigest()

def register():
    users = load_users()
    username = input("Choose a username: ").strip()
    if username in users:
        print("Username already exists.")
        return

    password = input("Choose a password: ").strip()
    hashed_pw = hash_password(password)

    (pubkey, privkey) = rsa.newkeys(512)
    users[username] = {
        "password": hashed_pw,
        "public_key": pubkey.save_pkcs1().decode(),
        "private_key": privkey.save_pkcs1().decode(),
        "balance": 0,
        "locked": [],
        "security_circle": [],
        "referrals": []
    }
    save_users(users)
    print("Registration successful!")


def login():
    users = load_users()
    username = input("Username: ").strip()
    password = input("Password: ").strip()

    if username in users and users[username]["password"] == hash_password(password):
        sessions = load_active_sessions()

        if username in sessions:
            print(f"{username} is already logged in on node {sessions[username]}.")
            return username

        node_id = assign_node_to_user(username)
        if not node_id:
            print("No available nodes at the moment. Try again later.")
            sys.exit()

        return username, node_id
    else:
        print("Invalid credentials.")
        return None


def view_security_circle(username):
    users = load_users()
    circle = users[username].get("security_circle", [])
    if not circle:
        print("Your Security Circle is empty.")
    else:
        print("Your Security Circle:")
        for user in circle:
            print(f" - {user}")

def add_to_security_circle(username):
    users = load_users()
    new_trust = input("Enter username to add to Security Circle: ").strip()
    if new_trust not in users:
        print("User does not exist.")
        return
    if new_trust == username:
        print("You cannot add yourself.")
        return

    if new_trust in users[username].get("security_circle", []):
        print("User already in your Security Circle.")
        return

    users[username]["security_circle"].append(new_trust)
    save_users(users)
    print(f"{new_trust} added to your Security Circle.")

def remove_from_security_circle(username):
    users = load_users()
    circle = users[username].get("security_circle", [])
    if not circle:
        print("Your Security Circle is already empty.")
        return

    remove_user = input("Enter username to remove: ").strip()
    if remove_user not in circle:
        print("User is not in your Security Circle.")
        return

    users[username]["security_circle"].remove(remove_user)
    save_users(users)
    print(f"{remove_user} removed from your Security Circle.")

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

        # Deduct from balance immediately
        user_data["balance"] -= amount
        users[username] = user_data
        save_users(users)

        lock_tx = TXConfig.Transaction(
            sender="system",  # Explicit sender for clarity
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
                continue  # Already fully claimed

            seconds_eligible = claim_until - last_claim
            rate_per_day = 0.05  # 5% daily reward
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

                # Create a new lockup transaction for the compounded reward
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
            # Add reward to balance if not re-locked
            users = load_users()
            users[username]["balance"] += total_reward
            save_users(users)
            print(f"{total_reward:.6f} Orbit added to your balance.")
    else:
        print("No new rewards available to claim.")
