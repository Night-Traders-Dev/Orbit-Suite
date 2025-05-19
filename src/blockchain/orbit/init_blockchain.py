import os
import json
import time
import rsa
import hashlib
from cryptography.fernet import Fernet
from config.configutil import OrbitDB, NodeConfig

orbit_db = OrbitDB()
USERS_FILE = orbit_db.userdb
NODES_FILE = orbit_db.nodedb
GENESIS_PATH = orbit_db.blockchaindb
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
        "password": hash_password("orbit_system"),
        "public_key": pubkey.save_pkcs1().decode(),
        "private_key": encrypted_priv,
        "balance": balance,
        "locked": [],
        "security_circle": [],
        "referrals": [],
        "mining_start_time": time.time()
    }

def init_users():
    users = {
        "system": generate_user("system", 98900000.0),
        "lockup_rewards": generate_user("lockup_rewards", 100000.0),
        "mining": generate_user("mining", 1000000.0),
        "nodefeecollector": generate_user("nodefeecollector", 0.0)
    }
    with open(USERS_FILE, "w") as f:
        json.dump(users, f, indent=4)
    print("Initialized users with balances.")

# ===== Genesis Block =====
def calculate_merkle_root(transactions):
    if not transactions:
        return ""
    hashes = [hashlib.sha256(json.dumps(tx, sort_keys=True).encode()).hexdigest() for tx in transactions]
    while len(hashes) > 1:
        hashes = [hashlib.sha256((hashes[i] + hashes[i + 1]).encode()).hexdigest()
                  for i in range(0, len(hashes) - 1, 2)] + (hashes[-1:] if len(hashes) % 2 else [])
    return hashes[0]

def calculate_genesis_hash(block):
    block_copy = block.copy()
    block_copy["hash"] = ""
    block_string = json.dumps(block_copy, sort_keys=True)
    return hashlib.sha256(block_string.encode()).hexdigest()

def create_genesis_block():
    now = int(time.time())
    transactions = [
        {"sender": "genesis", "recipient": "lockup_rewards", "amount": 100000.0, "timestamp": now, "note": "Initial supply for lockup rewards"},
        {"sender": "genesis", "recipient": "mining", "amount": 1000000.0, "timestamp": now, "note": "Initial supply for mining rewards"},
        {"sender": "genesis", "recipient": "system", "amount": 98900000.0, "timestamp": now, "note": "Initial supply for system wallet"},
        {"sender": "genesis", "recipient": "nodefeecollector", "amount": 0.0, "timestamp": now, "note": "Initial supply for node fee collector"}
    ]
    block = {
        "index": 0,
        "timestamp": now,
        "transactions": transactions,
        "previous_hash": "0" * 64,
        "hash": "",
        "validator": "genesis",
        "signatures": {},
        "merkle_root": calculate_merkle_root(transactions),
        "nonce": 0,
        "metadata": {"version": "1.0", "note": "Genesis Block for Orbit Chain"}
    }
    block["hash"] = calculate_genesis_hash(block)
    return block

def ensure_genesis_block():
    if not os.path.exists("data"):
        os.makedirs("data")
    if not os.path.exists(GENESIS_PATH):
        genesis_block = create_genesis_block()
        with open(GENESIS_PATH, "w") as f:
            json.dump([genesis_block], f, indent=4)
        print("Genesis block created.")
    else:
        print("Genesis block already exists.")

# ===== Initial Node File =====
def init_nodes():
    nodes = {
        "Node1": NodeConfig("127.0.0.1:5000", ["Node1"], 1.0, 1.0).to_dict()
    }
    with open(NODES_FILE, "w") as f:
        json.dump(nodes, f, indent=4)
    print("Initialized data/nodes.json")

if __name__ == "__main__":
    ensure_genesis_block()
    init_users()
    init_nodes()
