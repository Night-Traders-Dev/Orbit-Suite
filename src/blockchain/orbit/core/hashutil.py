import hashlib
import json
import rsa
import os
import time
from cryptography.fernet import Fernet
import pyotp

KEY_SIZE = 2048  # Use strong RSA key
AES_KEY_FILE = "data/aes.key"
totp_db = "data/totp_db.json"

# ===================== ADDRESS UTILS =====================

def generate_orbit_address(discord_id):
    """
    Generates a unique Orbit address using a Discord user ID.
    Returns a short base58-like address starting with 'ORB'.
    """
    if not isinstance(discord_id, (int, str)):
        raise ValueError("Discord ID must be an int or string.")

    uid_str = str(discord_id)
    hash_obj = hashlib.sha256(uid_str.encode())
    hex_digest = hash_obj.hexdigest()

    # Take first 24 characters for a short readable address
    short_hash = hex_digest[:24].upper()

    # Prefix to indicate Orbit address
    return f"ORB.{short_hash}"

# ===================== 2FA UTILS =====================

def create_2fa_secret(discord_id):
    secret = pyotp.random_base32()
    encrypted = encrypt_private_key(secret)
    address = generate_orbit_address(discord_id)

    if os.path.exists(totp_db):
        with open(totp_db, "r") as f:
            data = json.load(f)
    else:
        data = {}

    if data.get(address):
        return False


    data[address] = encrypted
    with open(totp_db, "w") as f:
        json.dump(data, f)

    return secret

def verify_2fa_token(discord_id, user_token):
    address = generate_orbit_address(discord_id)
    with open(totp_db, "r") as f:
        data = json.load(f)

    encrypted = data.get(address)
    if not encrypted:
        return False

    secret = decrypt_private_key(encrypted)
    totp = pyotp.TOTP(secret)
    return totp.verify(user_token)


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

def create_account(username, password, users):
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
    return users

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


# ===================== STAKE UTILS =====================

def generate_lock_id(start, amount, days):
    return hashlib.sha256(f"{start}:{amount}:{days}".encode()).hexdigest()
