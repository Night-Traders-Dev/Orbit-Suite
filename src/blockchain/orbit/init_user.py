import json
import os
import time
import rsa
import hashlib
from cryptography.fernet import Fernet
from config.configutil import OrbitDB

orbit_db = OrbitDB()
USERS_FILE = orbit_db.userdb
AES_KEY_FILE = "aes.key"
KEY_SIZE = 2048

# ===== AES Setup =====
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

# ===== User Functions =====
def hash_password(password):
    return hashlib.sha256(password.encode()).hexdigest()

def generate_user(username, balance):
    pubkey, privkey = rsa.newkeys(KEY_SIZE)
    encrypted_priv = encrypt_private_key(privkey.save_pkcs1().decode())
    return {
        "password": hash_password("orbit_system"),  # dummy password
        "public_key": pubkey.save_pkcs1().decode(),
        "private_key": encrypted_priv,
        "balance": balance,
        "locked": [],
        "security_circle": [],
        "referrals": [],
        "mining_start_time": time.time()
    }

def init_users():
    users = {}
    users["system"] = generate_user("system", 98900000.0)
    users["lockup_rewards"] = generate_user("lockup_rewards", 100000.0)
    users["mining"] = generate_user("mining", 1000000.0)
    users["nodefeecollector"] = generate_user("nodefeecollector", 0.0)

    with open(USERS_FILE, "w") as f:
        json.dump(users, f, indent=4)

    print("Initialized users with system balances.")

if __name__ == "__main__":
    init_users()
