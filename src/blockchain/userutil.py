# userutil.py
import time
import json
import os
import hashlib
import rsa
import threading
from blockutil import add_block, start_listener
from ledgerutil import load_blockchain

USERS_FILE = "data/users.json"

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
        print(f"Welcome, {username}!")
        listener_thread = threading.Thread(target=start_listener, daemon=True)
        listener_thread.start()
        return username
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
    blockchain = load_blockchain()
    lockups = []

    for block in blockchain:
        for tx in block.get("transactions", []):
            if tx.get("to") == username:
                note = tx.get("note")
                if isinstance(note, dict) and "duration_days" in note:
                    amount = tx["amount"]
                    duration = note["duration_days"]
                    start_time = tx.get("timestamp", time.time())
                    lockups.append({
                        "amount": amount,
                        "duration": duration,
                        "start_time": start_time
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

        lock_tx = {
            "from": None,
            "to": username,
            "amount": amount,
            "timestamp": time.time(),
            "note": {"duration_days": duration}
        }
        add_block([lock_tx])

        print(f"Locked {amount} Orbit for {duration} days.")

    except ValueError:
        print("Invalid input.")
