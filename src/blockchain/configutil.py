import ipaddress
import time
import socket

# ===== Default Constants =====
DEFAULT_CHAIN_PATH = "data/orbit_chain.json"
DEFAULT_NODE_DB = "data/nodes.json"
DEFAULT_PORT = 5000
DEFAULT_ADDRESS = "0.0.0.0"
DEFAULT_USER_DB = USERS_FILE = "data/users.json"

# ===== Node Configuration =====
class NodeConfig:
    def __init__(self):
        self.port: int = self.find_available_port(DEFAULT_PORT)
        self.address = ipaddress.IPv4Address(DEFAULT_ADDRESS)
        self.nodedb: str = DEFAULT_NODE_DB
        self.quorum_slice = []

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
            "quorum_slice": self.quorum_slice
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
        return node_config

    def __repr__(self):
        return f"NodeConfig(port={self.port}, address={self.address}, nodedb={self.nodedb}, quorum_slice={self.quorum_slice})"

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
            transaction_dict = {
                "sender": self.sender,
                "recipient": self.recipient,
                "amount": self.amount,
                "note": self.note,
                "timestamp": self.timestamp
            }
            return transaction_dict

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
            hash: str
        ):
            self.index = index
            self.timestamp = timestamp
            self.transactions = transactions
            self.previous_hash = previous_hash
            self.hash = hash

        def to_dict(self):
            return {
                "index": self.index,
                "timestamp": self.timestamp,
                "transactions": [tx.to_dict() for tx in self.transactions],
                "previous_hash": self.previous_hash,
                "hash": self.hash
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
                hash=data["hash"]
            )

        def __repr__(self):
            return f"Block(Index: {self.index}, TXs: {len(self.transactions)})"
