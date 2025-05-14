import ipaddress
import time
import socket
import hashlib
import os
import json

# ===== Default Constants =====
DEFAULT_CHAIN_PATH = "data/orbit_chain.json"
DEFAULT_NODE_DB = "data/nodes.json"
DEFAULT_PORT = 5000
DEFAULT_ADDRESS = "0.0.0.0"
DEFAULT_USER_DB = USERS_FILE = "data/users.json"
ACTIVE_SESSIONS_FILE = "data/active_sessions.json"

# ===== Session Assignment (Global Active Sessions) =====


def load_active_sessions():
    if os.path.exists(ACTIVE_SESSIONS_FILE):
        with open(ACTIVE_SESSIONS_FILE, "r") as f:
            return json.load(f)
    return {}

def save_active_sessions(sessions):
    with open(ACTIVE_SESSIONS_FILE, "w") as f:
        json.dump(sessions, f, indent=4)

def load_nodes():
    if os.path.exists(DEFAULT_NODE_DB):
        with open(DEFAULT_NODE_DB, "r") as f:
            return json.load(f)
    return []

def assign_node_to_user(username):
    sessions = load_active_sessions()
    nodes = load_nodes()
    assigned_nodes = set(sessions.values())

    for node in nodes:
        if node not in assigned_nodes:
            sessions[username] = node
            save_active_sessions(sessions)
            return node
    return None  # No unassigned node available

def revoke_node_from_user(username):
    sessions = load_active_sessions()
    if username in sessions:
        del sessions[username]
        save_active_sessions(sessions)

def get_node_for_user(username):
    sessions = load_active_sessions()
    return sessions.get(username)

# ===== Node Configuration =====
class NodeConfig:
    def __init__(self):
        self.port: int = self.find_available_port(DEFAULT_PORT)
        self.address = ipaddress.IPv4Address(DEFAULT_ADDRESS)
        self.nodedb: str = DEFAULT_NODE_DB
        self.quorum_slice = []
        self.trust_score = 0.5  # Initial trust
        self.uptime_score = 0.5  # Initial uptime

    @staticmethod
    def port_is_available(port):
        with socket.socket(socket.AF_INET, socket.SOCK_STREAM) as s:
            try:
                s.bind((DEFAULT_ADDRESS, port))
                return True
            except OSError:
                return False

    def find_available_port(self, start_port):
        port = start_port
        while not self.port_is_available(port):
            port += 1
        return port

    def to_dict(self):
        return {
            "port": self.port,
            "address": str(self.address),
            "nodedb": self.nodedb,
            "quorum_slice": self.quorum_slice,
            "trust_score": self.trust_score,
            "uptime_score": self.uptime_score
        }

    @classmethod
    def from_dict(cls, data):
        node_config = cls()
        addr_port = data.get("address", DEFAULT_ADDRESS)

        if ":" in addr_port:
            ip_str, port_str = addr_port.split(":")
            node_config.address = ipaddress.IPv4Address(ip_str)
            node_config.port = int(port_str)
        else:
            node_config.address = ipaddress.IPv4Address(addr_port)
            requested_port = data.get("port", DEFAULT_PORT)
            node_config.port = node_config.find_available_port(requested_port)

        node_config.nodedb = data.get("nodedb", DEFAULT_NODE_DB)
        node_config.quorum_slice = data.get("quorum_slice", [])
        node_config.trust_score = data.get("trust_score", 0.5)
        node_config.uptime_score = data.get("uptime_score", 0.5)
        return node_config

    def __repr__(self):
        return (
            f"NodeConfig(port={self.port}, address={self.address}, nodedb={self.nodedb}, "
            f"quorum_slice={self.quorum_slice}, trust_score={self.trust_score:.2f}, uptime_score={self.uptime_score:.2f})"
        )

# ===== Mining Configuration =====
class MiningConfig:
    def __init__(self):
        self.mode: str = "simulation"
        self.base: float = 0.1
        self.decay: float = 0.0001


# ===== Ledger Configuration =====
class LedgerConfig:
    def __init__(self):
        self.blockchaindb: str = DEFAULT_CHAIN_PATH

# ===== User Configuration =====
class UserConfig:
    def __init__(self):
        self.userdb: str = DEFAULT_USER_DB



# ===== Transaction and Block Templates =====
class TXConfig:
    class Transaction:
        def __init__(self, sender: str, recipient: str, amount: float, note: dict = None, timestamp: float = None):
            if amount < 0:
                raise ValueError("Transaction amount must be non-negative")
            self.sender = sender
            self.recipient = recipient
            self.amount = amount
            self.note = note if note is not None else {}
            self.timestamp = timestamp if timestamp is not None else time.time()

        def to_dict(self):
            return {
                "sender": self.sender,
                "recipient": self.recipient,
                "amount": self.amount,
                "note": self.note,
                "timestamp": self.timestamp
            }

        @staticmethod
        def from_dict(data):
            sender = data["from"] if "from" in data else data["sender"]
            recipient = data["to"] if "to" in data else data["recipient"]
            amount = data["amount"]
            note = data.get("note", {})
            timestamp = data.get("timestamp", time.time())

            return TXConfig.Transaction(
                sender=sender,
                recipient=recipient,
                amount=amount,
                note=note,
                timestamp=timestamp
            )

        def __repr__(self):
            return f"Transaction({self.sender} -> {self.recipient}: {self.amount}, Timestamp: {self.timestamp}, Note: {self.note})"

    class Block:
        def __init__(
            self,
            index: int,
            timestamp: float,
            transactions: list["TXConfig.Transaction"],
            previous_hash: str,
            hash: str,
            validator: str = "",
            signatures: dict = None,
            merkle_root: str = "",
            nonce: int = 0,
            metadata: dict = None
        ):
            self.index = index
            self.timestamp = timestamp
            self.transactions = transactions
            self.previous_hash = previous_hash
            self.hash = hash
            self.validator = validator
            self.signatures = signatures if signatures else {}
            self.merkle_root = merkle_root or self.compute_merkle_root()
            self.nonce = nonce
            self.metadata = metadata if metadata else {}

        def to_dict(self):
            return {
                "index": self.index,
                "timestamp": self.timestamp,
                "transactions": [tx.to_dict() for tx in self.transactions],
                "previous_hash": self.previous_hash,
                "hash": self.hash,
                "validator": self.validator,
                "signatures": self.signatures,
                "merkle_root": self.merkle_root,
                "nonce": self.nonce,
                "metadata": self.metadata
            }

        @staticmethod
        def from_dict(data):
            return TXConfig.Block(
                index=data["index"],
                timestamp=data["timestamp"],
                transactions=[
                    TXConfig.Transaction.from_dict(tx)
                    for tx in data["transactions"]
                ],
                previous_hash=data["previous_hash"],
                hash=data["hash"],
                validator=data.get("validator", ""),
                signatures=data.get("signatures", {}),
                merkle_root=data.get("merkle_root", ""),
                nonce=data.get("nonce", 0),
                metadata=data.get("metadata", {})
            )

        def compute_merkle_root(self):
            tx_hashes = [self.hash_transaction(tx) for tx in self.transactions]
            while len(tx_hashes) > 1:
                if len(tx_hashes) % 2 != 0:
                    tx_hashes.append(tx_hashes[-1])  # duplicate last if odd
                tx_hashes = [
                    hashlib.sha256((tx_hashes[i] + tx_hashes[i + 1]).encode()).hexdigest()
                    for i in range(0, len(tx_hashes), 2)
                ]
            return tx_hashes[0] if tx_hashes else ""

        def hash_transaction(self, tx):
            raw = f"{tx.sender}->{tx.recipient}:{tx.amount}:{tx.timestamp}"
            return hashlib.sha256(raw.encode()).hexdigest()

        def __repr__(self):
            return f"Block(Index: {self.index}, TXs: {len(self.transactions)}, Validator: {self.validator})"
