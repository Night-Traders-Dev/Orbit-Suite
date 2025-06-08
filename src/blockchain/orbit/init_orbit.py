import os
import json
import hashlib
import time
import rsa
from cryptography.fernet import Fernet
from config.configutil import OrbitDB

# ======== Setup ========
orbit_db = OrbitDB()
GENESIS_PATH = orbit_db.blockchaindb
USERS_FILE = orbit_db.userdb
AES_KEY_FILE = "data/aes.key"
KEY_SIZE = 2048

WALLET_ALLOCATIONS = {
    "system": 98_900_000_000.0000,
    "lockup_rewards": 100000000.0000,
    "mining": 1000000000.0000,
    "nodefeecollector": 0.0000,
    "community": 3000000000.0000,
    "team": 5000000000.0000,
    "airdrop": 1000000000.0000,
    "foundation": 2000000000.0000,
    "partnerships": 1000000000.0000,
    "reserve": 5000000000.0000
}

# ======== AES Setup ========
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

# ======== User/Wallet Functions ========
def hash_password(password):
    return hashlib.sha256(password.encode()).hexdigest()

def derive_orbit_address(public_key):
    hash_bytes = hashlib.sha256(public_key.encode()).digest()
    return "ORBIT" + hash_bytes.hex()[:36].upper()

def generate_user(username, balance):
    pubkey, privkey = rsa.newkeys(KEY_SIZE)
    pub_pem = pubkey.save_pkcs1().decode()
    encrypted_priv = encrypt_private_key(privkey.save_pkcs1().decode())
    address = derive_orbit_address(pub_pem)
    return username, {
        "password": hash_password("orbit_system"),
        "public_key": pub_pem,
        "private_key": encrypted_priv,
        "address": address,
        "balance": balance,
        "locked": [],
        "security_circle": [],
        "referrals": [],
        "mining_start_time": time.time()
    }

# ======== Genesis Functions ========
def calculate_merkle_root(transactions):
    if not transactions:
        return ""
    hashes = [hashlib.sha256(json.dumps(tx, sort_keys=True).encode()).hexdigest() for tx in transactions]
    while len(hashes) > 1:
        hashes = [hashlib.sha256((hashes[i] + hashes[i+1]).encode()).hexdigest()
                  for i in range(0, len(hashes)-1, 2)] + (hashes[-1:] if len(hashes) % 2 else [])
    return hashes[0]

def calculate_genesis_hash(block):
    block_copy = block.copy()
    block_copy["hash"] = ""
    block_string = json.dumps(block_copy, sort_keys=True)
    return hashlib.sha256(block_string.encode()).hexdigest()

def create_genesis_block(user_map):
    transactions = []
    for username, user in user_map.items():
        transactions.append({
            "sender": "genesis",
            "recipient": user["address"],
            "amount": round(user["balance"], 4),
            "timestamp": int(time.time()),
            "note": f"Initial allocation for {username}"
        })

    block = {
        "index": 0,
        "timestamp": int(time.time()),
        "transactions": transactions,
        "previous_hash": "0" * 64,
        "hash": "",  # to be filled in
        "validator": "genesis",
        "signatures": {},
        "merkle_root": "",
        "nonce": 0,
        "metadata": {
            "version": "1.0",
            "note": "Genesis Block for Orbit Chain"
        }
    }

    block["merkle_root"] = calculate_merkle_root(transactions)
    block["hash"] = calculate_genesis_hash(block)
    return block

# ======== Initialization Entry Point ========
def init_chain():
    if not os.path.exists("data"):
        os.makedirs("data")

    # Create all users
    users = {}
    address_mapping = {}
    for name, amount in WALLET_ALLOCATIONS.items():
        uname, user_data = generate_user(name, amount)
        users[uname] = user_data
        address_mapping[uname] = user_data["address"]

    # Write users to file
    with open(USERS_FILE, "w") as f:
        json.dump(users, f, indent=4)

    print("Users initialized.")

    # Create genesis block
    if not os.path.exists(GENESIS_PATH):
        genesis_block = create_genesis_block(users)
        with open(GENESIS_PATH, "w") as f:
            json.dump([genesis_block], f, indent=4)
        print("Genesis block created.")
    else:
        print("Genesis block already exists.")

    # Write explorer-friendly mapping
    with open("data/wallet_mapping.json", "w") as f:
        json.dump(address_mapping, f, indent=4)
    print("Explorer wallet name mapping saved.")

if __name__ == "__main__":
    init_chain()
