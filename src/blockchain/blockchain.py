# blockchain.py

import time
from block import Block
from poi import ProofOfInsight
from epc import EPCKeyPair

class Blockchain:
    def __init__(self):
        self.chain = []
        self.mempool = []
        self.reputation = {}  # public_key: score
        self.keypair = EPCKeyPair.generate()
        self.create_genesis_block()

    def create_genesis_block(self):
        genesis_block = Block(
            index=0,
            transactions=[],
            previous_hash="0" * 64,
            validator_pubkey=self.keypair.public_key,
            reputation_snapshot=self.reputation.copy()
        )
        genesis_block.sign_block(self.keypair)
        self.chain.append(genesis_block)

    def get_last_block(self):
        return self.chain[-1]

    def add_transaction(self, transaction):
        # Assume transaction is already signed and validated externally
        self.mempool.append(transaction)

    def create_block(self, validator_keypair):
        validator_pubkey = validator_keypair.public_key
        reputation_snapshot = self.reputation.copy()
        block = Block(
            index=len(self.chain),
            transactions=self.mempool[:],
            previous_hash=self.get_last_block().hash,
            validator_pubkey=validator_pubkey,
            reputation_snapshot=reputation_snapshot
        )
        block.sign_block(validator_keypair)
        if block.is_valid(self.get_last_block().hash):
            self.chain.append(block)
            self.mempool.clear()
            PoI.update_reputation(block, self.reputation)
            print(f"Block #{block.index} added by {validator_pubkey[:12]}...")
            return True
        return False

    def validate_chain(self):
        for i in range(1, len(self.chain)):
            if not self.chain[i].is_valid(self.chain[i - 1].hash):
                return False
        return True

    def run_consensus_and_mine(self):
        validator_key = PoI.select_validator(self.reputation)
        if not validator_key:
            print("No eligible validators available.")
            return False
        return self.create_block(validator_key)

    def __repr__(self):
        return f"<OrbitBlockchain | Length: {len(self.chain)} | Pending Txns: {len(self.mempool)}>"
