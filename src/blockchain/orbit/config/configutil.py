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
        self.NodeRegistry = {}
        self.explorer = 'http://127.0.0.1:7000'

class MiningConfig:
    def __init__(self):
        self.mode: str = "mainnet"
        self.base: float = 0.1
        self.decay: float = 0.0001


class NodeConfig:
    def __init__(self, id, address, host, port, quorum_slice=None, trust=0.5, uptime=0.5, users=None):
        self.id = id
        self.address = address
        self.host = host
        self.port = port
        self.quorum_slice = quorum_slice or []
        self.trust = trust
        self.uptime = uptime
        self.users = users or []

    def to_dict(self):
        return {
            "id": self.id,
            "address": self.address,
            "host": self.host,
            "port": self.port,
            "quorum_slice": self.quorum_slice,
            "trust": self.trust,
            "uptime": self.uptime,
            "last_seen": time.time(),
            "users": self.users
        }

    @staticmethod
    def from_dict(data):
        return NodeConfig(
            id=data.get("id"),
            address=data.get("address"),
            host=data.get("host"),
            port=data.get("port"),
            quorum_slice=data.get("quorum_slice", []),
            trust=data.get("trust", 0.5),
            uptime=data.get("uptime", 0.5),
            users=data.get("users", [])
        )

    def add_user(self, address):
        if address not in self.users:
            self.users.append(address)

    def remove_user(self, address):
        if address in self.users:
            self.users.remove(address)

    def has_user(self, address):
        return address in self.users


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
    from core.ioutil import load_nodes, save_nodes
    try:
        nodes = load_nodes()  # Returns a dict of {node_id: {node: {...}, last_seen: ...}}

        for node_id, data in nodes.items():
            node_config = data.get("node", {})
            if node_config.get("user") == user_id:
                return node_id

        for node_id, data in nodes.items():
            node_config = data.get("node", {})
            if not node_config.get("user"):
                node_config["user"] = user_id
                data["node"] = node_config
                nodes[node_id] = data
                save_nodes(nodes)  # Persist updated mapping
                return node_id
    except Exception as e:
        print(f"[get_node_for_user] Error: {e}")
    return None


