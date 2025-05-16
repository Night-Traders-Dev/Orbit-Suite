import time
import json
import os
import hashlib
import rsa
import threading
from blockchain.blockutil import add_block, start_listener, load_chain
from config.configutil import TXConfig, assign_node_to_user, load_active_sessions, OrbitDB
from blockchain.orbitutil import load_nodes
from core.termutil import clear_screen

orbit_db = OrbitDB()

USERS_FILE = orbit_db.userdb

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

    if username not in users:
        clear_screen()
        print("Username not found.")
        return None

    password = input("Password: ").strip()
    if users[username]["password"] != hash_password(password):
        clear_screen()
        print("Incorrect password.")
        return None

    sessions = load_active_sessions()
    if username in sessions:
        clear_screen()
        print(f"{username} is already logged in on node {sessions[username]}.")
        return username

    node_id = assign_node_to_user(username)
    if not node_id:
        print("No available nodes at the moment. Try again later.")
        sys.exit()

    return username, node_id

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


