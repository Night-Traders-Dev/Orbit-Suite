# block.py

import time
import json
from epc import EPCKeyPair
from hashlib import sha256  # For fallbacks if needed

class Block:
    def __init__(self, index, transactions, previous_hash, validator_pubkey, reputation_snapshot=None, timestamp=None):
        self.index = index
        self.timestamp = timestamp or time.time()
        self.transactions = transactions  # List of dicts (must be signed externally)
        self.previous_hash = previous_hash
        self.validator = validator_pubkey
        self.reputation_snapshot = reputation_snapshot or {}
        self.signature = None
        self.hash = None

    def to_dict(self, include_signature=True):
        data = {
            "index": self.index,
            "timestamp": self.timestamp,
            "transactions": self.transactions,
            "previous_hash": self.previous_hash,
            "validator": self.validator,
            "reputation_snapshot": self.reputation_snapshot
        }
        if include_signature:
            data["signature"] = self.signature
        return data

    def compute_hash(self):
        block_data = json.dumps(self.to_dict(include_signature=False), sort_keys=True)
        # Use EPC-based hashing here
        return EPCKeyPair.hash(block_data)

    def sign_block(self, validator_keypair):
        if validator_keypair.public_key != self.validator:
            raise ValueError("Invalid validator keypair")

        self.hash = self.compute_hash()
        self.signature = validator_keypair.sign(self.hash)

    def verify_signature(self):
        if not self.hash:
            self.hash = self.compute_hash()
        return EPCKeyPair.verify(self.validator, self.hash, self.signature)

    def is_valid(self, previous_block_hash):
        if self.previous_hash != previous_block_hash:
            return False
        if self.compute_hash() != self.hash:
            return False
        if not self.verify_signature():
            return False
        return True

    def __repr__(self):
        return f"<Block #{self.index} | Txns: {len(self.transactions)} | Hash: {self.hash[:12]}...>"
