import ipaddress
import time

# ===== Default Constants =====
DEFAULT_CHAIN_PATH = "data/orbit_chain.json"
DEFAULT_NODE_DB = "data/nodes.json"
DEFAULT_PORT = 5000
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
        def __init__(self, sender: str, recipient: str, amount: float):
            if amount < 0:
                raise ValueError("Transaction amount must be non-negative")
            self.sender = sender
            self.recipient = recipient
            self.amount = amount

        def to_dict(self):
            return {
                "sender": self.sender,
                "recipient": self.recipient,
                "amount": self.amount
            }

        @staticmethod
        def from_dict(data):
            return TXConfig.Transaction(
                sender=data["sender"],
                recipient=data["recipient"],
                amount=data["amount"]
            )

        def __repr__(self):
            return f"Transaction({self.sender} -> {self.recipient}: {self.amount})"

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
