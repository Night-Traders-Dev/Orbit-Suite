import time
import json
from core.hashutil import generate_lock_id

class TXTypes:
    def __init__(self, tx_class=None, tx_type=None, tx_data=None, tx_value=None):
        self.tx_class = tx_class
        self.tx_type = tx_type
        self.tx_data = tx_data
        self.tx_value = tx_value
        self.metadata = {}

    def get_value(self, tx_key):
        self.tx_key = tx_key
        if self.tx_class and self.tx_data:
            return self.tx_data.get("type", {}).get(self.tx_class, {}).get(self.tx_key)
        return None

    def tx_types(self):
        if not self.tx_class or not self.tx_type or not self.tx_data:
            return None
        if self.tx_value == "string":
            return json.dumps(self.tx_data, indent=2)
        elif self.tx_value == "dict":
            return self.tx_data
        return None

    # --- Mining ---
    class MiningTypes:
        def __init__(self, mined=0.0, base=0.0, security=0.0, lockup=0.0, referral=0.0, now=None):
            self.mined = mined
            self.rate = {
                "base": base,
                "security": security,
                "lockup": lockup,
                "referral": referral
            }
            self.now = now or time.time()
            self.metadata = {}

        def rate_dict(self):
            self.metadata = {
                "rate": self.mined,
                "formula": self.rate
            }
            return self.metadata

        @staticmethod
        def mining_metadata(node_fee, rate_metadata):
            return {
                "type": {
                    "mining": {
                        "fee": node_fee,
                        "bonuses": rate_metadata
                    }
                }
            }

    # --- Staking ---
    class StakingTypes:
        from core.hashutil import generate_lock_id
        def __init__(self, duration=None, amount=None):
            duration = duration or {}
            amount = amount or {}

            self.init_days = duration.get("init_days", 0)
            self.start = duration.get("start", time.time())
            self.end = duration.get("end", self.start + self.init_days * 86400)
            self.now = duration.get("now", time.time())
            self.days = (self.end - self.now) / 86400
            self.claim = amount.get("claim", 0.0)
            self.lock = amount.get("lock", 0.0)
            self.metadata = {}


        def tx_build(self, build="claim"):
            if build == "lockup":
                self.metadata = {
                    "type": {
                        "lockup": {
                            "amount": self.lock,
                            "start": self.start,
                            "end": self.end,
                            "days": self.days,
                            "uuid": generate_lock_id(self.start, self.lock, self.end)
                        }
                    }
                }
                return self.metadata
            elif build == "claim":
                self.metadata = {
                    "type": {
                        "claim": {
                            "amount": self.claim,
                            "start": self.start,
                            "end": self.end,
                            "days": self.days,
                            "locked": self.lock,
                            "last_claim": time.time() 
                        }
                    }
                }
                return self.metadata
            elif build == "withdraw":
                self.metadata = {
                    "type": {
                        "withdraw": {
                            "amount": self.claim,
                            "start": self.start,
                            "end": self.end,
                            "days": self.days,
                            "locked": self.lock,
                            "uuid": generate_lock_id(time.time(), self.claim, self.end)
                        }
                    }
                }
                return self.metadata
            return {}

        @staticmethod
        def from_dict(data):
            lockup = data.get("type", {}).get("lockup", {})
            return (
                lockup.get("start"),
                lockup.get("end"),
                lockup.get("days"),
                lockup.get("amount")
            )

    # --- Gas ---
    class GasTypes:
        def __init__(self, node_fee, node_id, sender, recipient):
            self.node_fee = node_fee
            self.node_id = node_id
            self.sender = sender
            self.recipient = recipient
            self.metadata = {}

        def gas_tx(self):
            self.metadata = {
                "type": {
                    "gas": {
                        "fee": self.node_fee,
                        "node": self.node_id,
                        "tx": f"{self.sender}->{self.recipient}",
                        "timestamp": time.time()
                    }
                }
            }
            return self.metadata

    # --- Basic Metadata Utilities ---
    @staticmethod
    def transfer_metadata(purpose="standard"):
        return {
            "type": {
                "transfer": {
                    "purpose": purpose,
                    "timestamp": time.time()
                }
            }
        }

    @staticmethod
    def reward_metadata(reason="contribution", bonus=0.0):
        return {
            "type": {
                "reward": {
                    "reason": reason,
                    "amount": bonus,
                    "timestamp": time.time()
                }
            }
        }

    @staticmethod
    def airdrop_metadata(source="foundation", campaign=None):
        return {
            "type": {
                "airdrop": {
                    "source": source,
                    "campaign": campaign,
                    "timestamp": time.time()
                }
            }
        }

    @staticmethod
    def penalty_metadata(reason="misconduct", penalty=0.0):
        return {
            "type": {
                "penalty": {
                    "reason": reason,
                    "amount": penalty,
                    "timestamp": time.time()
                }
            }
        }

    @staticmethod
    def delegation_metadata(delegate_to, amount=0.0):
        return {
            "type": {
                "delegation": {
                    "to": delegate_to,
                    "amount": amount,
                    "timestamp": time.time()
                }
            }
        }
