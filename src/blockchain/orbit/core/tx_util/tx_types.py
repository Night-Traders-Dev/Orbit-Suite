import time
import json
import uuid
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


    class NFTTypes:
        def __init__(self, nft_id=None, owner=None, metadata=None, timestamp=None):
            self.nft_id = nft_id or str(uuid.uuid4())
            self.owner = owner or "unknown"
            self.metadata = metadata or {}
            self.timestamp = timestamp or time.time()

        def create_nft(self):
            return {
                "type": {
                    "nft": {
                        "id": self.nft_id,
                        "owner": self.owner,
                        "metadata": self.metadata,
                        "timestamp": self.timestamp
                    }
                }
            }
    def transfer_nft(self, new_owner):
        return {
            "type": {
                "transfer_nft": {
                    "nft_id": self.nft_id,
                    "from": self.owner,
                    "to": new_owner,
                    "timestamp": time.time()
                }
            }
        }
    def update_nft_metadata(self, new_metadata):
        self.metadata.update(new_metadata)
        return {
            "type": {
                "update_nft_metadata": {
                    "nft_id": self.nft_id,
                    "owner": self.owner,
                    "metadata": self.metadata,
                    "timestamp": time.time()
                }
            }
        }
    def get_nft_metadata(self):
        return {
            "type": {
                "get_nft_metadata": {
                    "nft_id": self.nft_id,
                    "owner": self.owner,
                    "metadata": self.metadata,
                    "timestamp": time.time()
                }
            }
        }
    def delete_nft(self):
        return {
            "type": {
                "delete_nft": {
                    "nft_id": self.nft_id,
                    "owner": self.owner,
                    "timestamp": time.time()
                }
            }
        }
    def get_nft_id(self):
        return self.nft_id
    def get_nft_owner(self):
        return self.owner
    def get_nft_metadata(self):
        return self.metadata
    def get_nft_timestamp(self):
        return self.timestamp



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


class TXExchange:

    # --- Exchange Metadata Utilities ---

    @staticmethod
    def create_token(name, symbol, supply, creator, listing_fee=250, token_id=None):
        return {
            "type": {
                "create_token": {
                    "token_id": token_id or str(uuid.uuid4()),
                    "name": name,
                    "symbol": symbol.upper(),
                    "supply": float(supply),
                    "creator": creator,
                    "listing_fee": listing_fee,
                    "timestamp": time.time()
                }
            }
        }


    @staticmethod
    def list_token(symbol, price, lister_address, token_id=None, exchange_fee=0.0):
        return {
            "type": {
                "list_token": {
                    "token_id": token_id or symbol.upper(),
                    "symbol": symbol.upper(),
                    "price": float(price),
                    "lister": lister_address,
                    "exchange_fee": float(exchange_fee),
                    "timestamp": time.time()
                }
            }
        }

    @staticmethod
    def buy_token(symbol, price,  amount, buyer_address, order_id=None, token_id=None, status=None, exchange_fee=0.0):
        return {
            "type": {
                "buy_token": {
                    "order_id": order_id or str(uuid.uuid4()),
                    "token_id": token_id or symbol.upper(),
                    "symbol": symbol.upper(),
                    "price": float(price),
                    "amount": float(amount),
                    "buyer": buyer_address,
                    "exchange_fee": float(exchange_fee),
                    "status": status,
                    "timestamp": time.time()
                }
            }
        }




    @staticmethod
    def tx_token(
        type,
        symbol,
        price,
        amount,
        address,
        order_id=None,
        token_id=None,
        status=None,
        exchange_fee=0.0
    ):
        if type == "buy":
            addr_key = "buyer"
        else:
            addr_key = "seller"

        return {
            "type": {
                f"{type}_token": {
                    "order_id": order_id or str(uuid.uuid4()),
                    "token_id": token_id or symbol.upper(),
                    "symbol": symbol.upper(),
                    "price": float(price),
                    "amount": float(amount),
                    addr_key: address,
                    "exchange_fee": float(exchange_fee),
                    "status": status,
                    "timestamp": time.time()
                }
            }
        }

    @staticmethod
    def sell_token(symbol, price, amount, seller_address, order_id=None, token_id=None, status=None, exchange_fee=0.0):
        return {
            "type": {
                "sell_token": {
                    "order_id": order_id or str(uuid.uuid4()),
                    "token_id": token_id or symbol.upper(),
                    "symbol": symbol.upper(),
                    "price": float(price),
                    "amount": float(amount),
                    "seller": seller_address,
                    "exchange_fee": float(exchange_fee),
                    "status": status,
                    "timestamp": time.time()
                }
            }
        }

    @staticmethod
    def cancel_order(order_id, canceller_address, symbol=None):
        return {
            "type": {
                "cancel_order": {
                    "order_id": order_id,
                    "symbol": symbol.upper() if symbol else None,
                    "canceller": canceller_address,
                    "timestamp": time.time()
                }
            }
        }

    @staticmethod
    def create_token_transfer_tx(sender, receiver, amount, token_symbol, note="", signature=""):
        return {
            "type": {
                "token_transfer": {
                    "sender": sender,
                    "receiver": receiver,
                    "amount": amount,
                    "token_symbol": token_symbol,
                    "note": note,
                    "timestamp": time.time(),
                    "signature": signature
                }
            }
        }
