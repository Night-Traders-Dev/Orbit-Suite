import time
import json

class TXTypes:
    def __init__(self, tx_class=None, tx_type=None, tx_data=None, tx_value=None):
        self.tx_class = tx_class
        self.tx_type = tx_type
        self.tx_data = tx_data
        self.tx_value = tx_value
        self.metadata = {}

    def get_value(self, tx_key):
        self.tx_key = tx_key
        if self.tx_class == "staking":
            metadata = self.tx_data or {}
            key = metadata.get("type", {}).get(self.tx_type, {})
            if self.tx_key in key:
                return key[self.tx_key]
        return None

    def tx_types(self):
        if self.tx_class == "staking":
            if not self.tx_value or not self.tx_type or not self.tx_data:
                return None
            if self.tx_value == "string":
                return json.dumps(self.tx_data, indent=2)
            elif self.tx_value == "dict":
                return self.tx_data
        return None

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

    class StakingTypes:
        def __init__(self, duration=None, amount=None):
            duration = duration or {}
            amount = amount or {}

            self.init_days = duration.get("init_days", 0)
            self.start = duration.get("start", time.time())
            self.end = duration.get("end", (self.start + self.init_days * 86400))
            self.now = duration.get("now", time.time())
            self.days = ((self.end - self.now) / 86400)
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
                            "days": self.days
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
                            "locked": self.lock
                        }
                    }
                }
                return self.metadata

    class MiscTypes:
        def __init__(self):
            self.metadata = {}


        def gas_tx(self, node_fee, node_id, tx_id):
            self.metadata = {
                "type": {
                    "gas": {
                         "fee": node_fee,
                         "node": node_id,
                         "tx": tx_id
                    }
                }
            }
            return self.metadata
