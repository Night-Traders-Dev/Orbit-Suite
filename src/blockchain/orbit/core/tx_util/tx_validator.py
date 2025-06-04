import time
import uuid

class TXValidator:
    def __init__(self, metadata):
        self.metadata = metadata
        self.errors = []
        self.corrections = []

    def validate(self):
        tx_type_dict = self.metadata.get("type", {})
        if not tx_type_dict:
            return False, "Missing 'type' in transaction metadata"

        for tx_name, tx_data in tx_type_dict.items():
            method = getattr(self, f"validate_{tx_name}", None)
            if method:
                valid, msg = method(tx_data)
                if valid and self.corrections:
                    return True, f"Valid with corrections: {', '.join(self.corrections)}"
                return valid, msg
            else:
                return False, f"Unknown transaction type: {tx_name}"
        return False, "No transaction type found"

    def validate_create_token(self, data):
        required = ["token_id", "name", "symbol", "supply", "creator", "timestamp"]
        autofix = {
            "token_id": lambda: self._autofix(data, "token_id", str(uuid.uuid4())),
            "timestamp": lambda: self._autofix(data, "timestamp", time.time())
        }
        return self._validate_fields(data, required, {
            "supply": lambda x: x > 0,
            "timestamp": self._is_recent_timestamp
        }, autofix)

    def validate_list_token(self, data):
        required = ["token_id", "symbol", "price", "lister", "exchange_fee", "timestamp"]
        autofix = {
            "timestamp": lambda: self._autofix(data, "timestamp", time.time()),
            "exchange_fee": lambda: self._autofix(data, "exchange_fee", 0.01)
        }
        return self._validate_fields(data, required, {
            "price": lambda x: x > 0,
            "exchange_fee": lambda x: x >= 0,
            "timestamp": self._is_recent_timestamp
        }, autofix)

    def validate_buy_token(self, data):
        required = ["order_id", "token_id", "symbol", "amount", "buyer", "exchange_fee", "timestamp"]
        autofix = {
            "timestamp": lambda: self._autofix(data, "timestamp", time.time()),
            "exchange_fee": lambda: self._autofix(data, "exchange_fee", 0.01),
            "order_id": lambda: self._autofix(data, "order_id", str(uuid.uuid4()))
        }
        return self._validate_fields(data, required, {
            "amount": lambda x: x > 0,
            "exchange_fee": lambda x: x >= 0,
            "timestamp": self._is_recent_timestamp
        }, autofix)

    def validate_sell_token(self, data):
        required = ["order_id", "token_id", "symbol", "amount", "seller", "exchange_fee", "timestamp"]
        autofix = {
            "timestamp": lambda: self._autofix(data, "timestamp", time.time()),
            "exchange_fee": lambda: self._autofix(data, "exchange_fee", 0.01),
            "order_id": lambda: self._autofix(data, "order_id", str(uuid.uuid4()))
        }
        return self._validate_fields(data, required, {
            "amount": lambda x: x > 0,
            "exchange_fee": lambda x: x >= 0,
            "timestamp": self._is_recent_timestamp
        }, autofix)

    # --- Shared utilities ---
    def _validate_fields(self, data, required_fields, custom_checks={}, autofix={}):
        for field in required_fields:
            if field not in data:
                if field in autofix:
                    autofix[field]()  # Auto-fix it
                else:
                    return False, f"Missing required field: {field}"

        for field, check in custom_checks.items():
            try:
                if not check(data[field]):
                    if field in autofix:
                        autofix[field]()  # Auto-fix and recheck
                        if not check(data[field]):
                            return False, f"Invalid value for field: {field}"
                    else:
                        return False, f"Invalid value for field: {field}"
            except Exception as e:
                return False, f"Error validating field '{field}': {str(e)}"

        return True, "Valid transaction metadata"

    def _is_recent_timestamp(self, ts):
        now = time.time()
        return now - 300 < ts < now + 300  # ±5 min

    def _autofix(self, data, key, default_value):
        data[key] = default_value
        self.corrections.append(f"Auto-filled '{key}'")
