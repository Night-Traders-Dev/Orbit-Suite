import os
import json
import time
import hashlib

DATA_DIR = "data"
if not os.path.exists(DATA_DIR):
    os.makedirs(DATA_DIR)

class OrbitDB:
    def __init__(self):
        self.activesessiondb = os.path.join(DATA_DIR, "active_sessions.json")
        self.blockchaindb = os.path.join(DATA_DIR, "orbit_chain.json")
        self.nodedb = os.path.join(DATA_DIR, "nodes.json")
        self.userdb = os.path.join(DATA_DIR, "users.json")
        self.peerlog = os.path.join(DATA_DIR, "peers.log")
        self.pendpropdb: str = os.path.join(DATA_DIR, "pending_proposals.json")
        self.stakefile = os.path.join(DATA_DIR, "stake.json")

class MiningConfig:
    def __init__(self):
        self.mode: str = "mainnet"
        self.base: float = 0.1
        self.decay: float = 0.0001


class NodeConfig:
    def __init__(self, node_id, address, port, quorum_slice=None, trust_score=0.5, uptime_score=0.5, user=None):
        self.node_id = node_id
        self.address = address
        self.port = port
        self.quorum_slice = quorum_slice or []
        self.trust_score = trust_score
        self.uptime_score = uptime_score
        self.user = user  # Optional field to link node to a user

    def to_dict(self):
        return {
            "node_id": self.node_id,
            "address": self.address,
            "port": self.port,
            "quorum_slice": self.quorum_slice,
            "trust_score": self.trust_score,
            "uptime_score": self.uptime_score,
            "user": self.user
        }

    @staticmethod
    def from_dict(data):
        return NodeConfig(
            node_id=data.get("node_id"),
            address=data.get("address"),
            port=data.get("port"),
            quorum_slice=data.get("quorum_slice", []),
            trust_score=data.get("trust_score", 0.5),
            uptime_score=data.get("uptime_score", 0.5),
            user=data.get("user")
        )

class TXConfig:
    class Transaction:
        def __init__(self, sender, recipient, amount, timestamp=None, note="", **kwargs):
            self.sender = sender
            self.recipient = recipient
            self.amount = amount
            self.timestamp = timestamp or time.time()
            self.note = note if note is not None else {}
            self.extra = kwargs  # Any additional fields

        def to_dict(self):
            tx = {
                "sender": self.sender,
                "recipient": self.recipient,
                "amount": self.amount,
                "timestamp": self.timestamp,
                "note": self.note
            }
            tx.update(self.extra)
            return tx

        @staticmethod
        def from_dict(data):
            return TXConfig.Transaction(
                sender=data.get("sender", ""),
                recipient=data.get("recipient", ""),
                amount=data.get("amount", 0),
                timestamp=data.get("timestamp", time.time()),
                note=data.get("note", ""),
                **{k: v for k, v in data.items() if k not in {"sender", "recipient", "amount", "tx_type", "timestamp", "note"}}
            )

    class Block:
        def __init__(self, index, timestamp, transactions, previous_hash, hash, validator, signatures, merkle_root, nonce, metadata=None):
            self.index = index
            self.timestamp = timestamp
            self.transactions = transactions
            self.previous_hash = previous_hash
            self.hash = hash
            self.validator = validator
            self.signatures = signatures
            self.merkle_root = merkle_root
            self.nonce = nonce
            self.metadata = metadata or {}

        def to_dict(self):
            return {
                "index": self.index,
                "timestamp": self.timestamp,
                "transactions": [tx.to_dict() if hasattr(tx, "to_dict") else tx for tx in self.transactions],
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
            txs = data.get("transactions", [])
            tx_objs = [TXConfig.Transaction.from_dict(tx) for tx in txs]
            return TXConfig.Block(
                index=data.get("index"),
                timestamp=data.get("timestamp"),
                transactions=tx_objs,
                previous_hash=data.get("previous_hash"),
                hash=data.get("hash"),
                validator=data.get("validator", ""),
                signatures=data.get("signatures", {}),
                merkle_root=data.get("merkle_root", ""),
                nonce=data.get("nonce", 0),
                metadata=data.get("metadata", {})
            )

        def generate_merkle_root(self):
            tx_hashes = [hashlib.sha256(json.dumps(tx.to_dict(), sort_keys=True).encode()).hexdigest()
                         for tx in self.transactions]
            while len(tx_hashes) > 1:
                if len(tx_hashes) % 2 == 1:
                    tx_hashes.append(tx_hashes[-1])
                tx_hashes = [hashlib.sha256((tx_hashes[i] + tx_hashes[i + 1]).encode()).hexdigest()
                             for i in range(0, len(tx_hashes), 2)]
            return tx_hashes[0] if tx_hashes else ""

def get_node_for_user(user_id):
    path = os.path.join(DATA_DIR, "nodes.json")
    if not os.path.exists(path):
        return None
    try:
        with open(path, "r") as f:
            nodes = json.load(f)
        for node_id, config in nodes.items():
            if config.get("user") == user_id:
                return node_id
        # Otherwise, find an unused node
        for node_id, config in nodes.items():
            if not config.get("user"):
                config["user"] = user_id
                nodes[node_id] = config
                with open(path, "w") as f:
                    json.dump(nodes, f, indent=4)
                return node_id
    except Exception as e:
        print(f"[get_node_for_user] Error: {e}")
    return None
