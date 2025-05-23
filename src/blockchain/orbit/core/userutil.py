import json
import os
import hashlib
import rsa
import sys
import time
import threading
from cryptography.fernet import Fernet
from config.configutil import OrbitDB
from blockchain.orbitutil import load_nodes, save_nodes, assign_node_to_user
from core.termutil import clear_screen
from core.networkutil import start_listener

orbit_db = OrbitDB()

KEY_SIZE = 2048  # Use strong RSA key
AES_KEY_FILE = "data/aes.key"

# ===================== AES UTILS =====================
def load_aes_key():
    if not os.path.exists(AES_KEY_FILE):
        key = Fernet.generate_key()
        with open(AES_KEY_FILE, "wb") as f:
            f.write(key)
    with open(AES_KEY_FILE, "rb") as f:
        return f.read()

def encrypt_private_key(plain_text):
    key = load_aes_key()
    fernet = Fernet(key)
    return fernet.encrypt(plain_text.encode()).decode()

def decrypt_private_key(cipher_text):
    key = load_aes_key()
    fernet = Fernet(key)
    return fernet.decrypt(cipher_text.encode()).decode()

# ===================== USER FUNCS =====================
def load_active_sessions():
    if os.path.exists(orbit_db.activesessiondb):
        with open(orbit_db.activesessiondb, "r") as f:
            return json.load(f)
    return {}

def save_active_sessions(sessions):
    with open(orbit_db.activesessiondb, "w") as f:
        json.dump(sessions, f, indent=4)

def load_users():
    if os.path.exists(orbit_db.userdb):
        with open(orbit_db.userdb, "r") as f:
            return json.load(f)
    return {}

def save_users(users):
    with open(orbit_db.userdb, "w") as f:
        json.dump(users, f, indent=4)

def hash_password(password):
    return hashlib.sha256(password.encode()).hexdigest()

def log_event(action, username):
    with open("user_activity.log", "a") as f:
        f.write(f"{time.strftime('%Y-%m-%d %H:%M:%S')} | {action} | {username}\n")

def validate_username(username):
    return username.isalnum() and 3 <= len(username) <= 20

def register():
    clear_screen()
    users = load_users()
    username = input("Choose a username: ").strip()

    if username in users:
        print("Username already exists.")
        return False

    if not validate_username(username):
        print("Username must be alphanumeric and 3–20 characters.")
        return False

    password = input("Choose a password: ").strip()
    if len(password) < 6:
        print("Password must be at least 6 characters.")
        return False

    hashed_pw = hash_password(password)
    pubkey, privkey = rsa.newkeys(KEY_SIZE)
    encrypted_private_key = encrypt_private_key(privkey.save_pkcs1().decode())

    users[username] = {
        "password": hashed_pw,
        "public_key": pubkey.save_pkcs1().decode(),
        "private_key": encrypted_private_key,
        "balance": 0,
        "locked": [],
        "security_circle": [],
        "referrals": [],
        "mining_start_time": time.time() - 3600
    }

    save_users(users)
    log_event("REGISTER", username)
    print("Registration successful!")
    return True

def login():
    clear_screen()
    users = load_users()
    username = input("Username: ").strip()

    if username not in users:
        print("Username not found.")
        return None

    password = input("Password: ").strip()
    if users[username]["password"] != hash_password(password):
        print("Incorrect password.")
        return None

    sessions = load_active_sessions()
    if username in sessions:
        print(f"{username} is already logged in on node {sessions[username]}.")
        return username

    node_id = assign_node_to_user(username, sessions)
    if not node_id:
        print("No available nodes at the moment. Try again later.")
        sys.exit()
    threading.Thread(target=start_listener, args=(node_id,), daemon=True).start()
    log_event("LOGIN", username)
    return username, node_id

def logout(user_id):
    if not os.path.exists(orbit_db.activesessiondb):
        return

    with open(orbit_db.activesessiondb, "r") as f:
        sessions = json.load(f)

    if user_id in sessions:
        del sessions[user_id]
        with open(orbit_db.activesessiondb, "w") as f:
            json.dump(sessions, f, indent=4)
        log_event("LOGOUT", user_id)
    else:
        print(f"User {user_id} was not in active sessions.")



def web_register(username=None, password=None):
    if username is None or password is None:
        clear_screen()
        users = load_users()
        username = input("Choose a username: ").strip()
        if username in users:
            print("Username already exists.")
            return False

        if not validate_username(username):
            print("Username must be alphanumeric and 3–20 characters.")
            return False

        password = input("Choose a password: ").strip()
        if len(password) < 6:
            print("Password must be at least 6 characters.")
            return False
    else:
        users = load_users()
        if username in users:
            return False
        if not validate_username(username) or len(password) < 6:
            return False

    hashed_pw = hash_password(password)
    pubkey, privkey = rsa.newkeys(KEY_SIZE)
    encrypted_private_key = encrypt_private_key(privkey.save_pkcs1().decode())

    users[username] = {
        "password": hashed_pw,
        "public_key": pubkey.save_pkcs1().decode(),
        "private_key": encrypted_private_key,
        "balance": 0,
        "locked": [],
        "security_circle": [],
        "referrals": [],
        "mining_start_time": time.time()
    }

    save_users(users)
    log_event("REGISTER", username)
    print("Registration successful!")
    return True

def web_login(username=None, password=None):
    users = load_users()

    if username is None or password is None:
        clear_screen()
        username = input("Username: ").strip()
        if username not in users:
            print("Username not found.")
            return None

        password = input("Password: ").strip()
        if users[username]["password"] != hash_password(password):
            print("Incorrect password.")
            return None
    else:
        if username not in users or users[username]["password"] != hash_password(password):
            return None

    sessions = load_active_sessions()
    if username in sessions:
        print(f"{username} is already logged in on node {sessions[username]}.")
        return username

    node_id = assign_node_to_user(username)
    if not node_id:
        print("No available nodes at the moment. Try again later.")
        sys.exit()

    log_event("LOGIN", username)
    return username, node_id

def web_logout(user_id):
    if not os.path.exists(orbit_db.activesessiondb):
        return

    with open(orbit_db.activesessiondb, "r") as f:
        sessions = json.load(f)

    if user_id in sessions:
        del sessions[user_id]
        with open(orbit_db.activesessiondb, "w") as f:
            json.dump(sessions, f, indent=4)
        log_event("LOGOUT", user_id)
    else:
        print(f"User {user_id} was not in active sessions.")
