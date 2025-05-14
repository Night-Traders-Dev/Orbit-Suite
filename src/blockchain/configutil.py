import ipaddress
import time

# ===== Default Constants =====
DEFAULT_CHAIN_PATH = "data/orbit_chain.json"
DEFAULT_NODE_DB = "data/nodes.json"
DEFAULT_PORT = 5001
DEFAULT_ADDRESS = "0.0.0.0"


# ===== Node Configuration =====
class NodeConfig:
    def __init__(self):
        self.port: int = DEFAULT_PORT
        self.address = ipaddress.IPv4Address(DEFAULT_ADDRESS)
        self.nodedb: str = DEFAULT_NODE_DB


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
