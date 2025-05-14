import ipaddress

class NodeConfig:
    def __init__(self):
        self.port: int = 5000
        self.address: IPv4Address = "0.0.0.0"
        self.nodedb: str = "data/nodes.json"

class MiningConfig:
    def __init__(self):
        self.mode: str = "simulation"
        self.base: float = 0.1
        self.decay: float = 0.0001

class LedgerConfig:
    def __init__(self):
        self.blockchaindb: str = "data/orbit_chain.json"

class TXConfig:
    class Transaction:
        def __init__(self, sender: str, recipient: str, amount: float):
            self.sender = sender
            self.recipient = recipient
            self.amount = amount

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
