import hashlib
import json
import rsa
import os
from cryptography.fernet import Fernet

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

def hash_password(password):
    return hashlib.sha256(password.encode()).hexdigest()

# ===================== BLOCK UTILS =====================

def generate_merkle_root(transaction_dicts):
    def hash_pair(a, b):
        return hashlib.sha256((a + b).encode()).hexdigest()

    tx_hashes = [hashlib.sha256(json.dumps(tx, sort_keys=True).encode()).hexdigest() for tx in transaction_dicts]
    while len(tx_hashes) > 1:
        if len(tx_hashes) % 2 == 1:
            tx_hashes.append(tx_hashes[-1])  # duplicate last hash if odd
        tx_hashes = [hash_pair(tx_hashes[i], tx_hashes[i+1]) for i in range(0, len(tx_hashes), 2)]
    return tx_hashes[0] if tx_hashes else ""

def calculate_hash(index, previous_hash, timestamp, transactions, validator="", merkle_root="", nonce=0, metadata=None):
    block_content = {
        "index": index,
        "previous_hash": previous_hash,
        "timestamp": timestamp,
        "transactions": transactions,
        "validator": validator,
        "merkle_root": merkle_root,
        "nonce": nonce,
        "metadata": metadata or {}
    }
    block_string = json.dumps(block_content, sort_keys=True)
    return hashlib.sha256(block_string.encode()).hexdigest()
