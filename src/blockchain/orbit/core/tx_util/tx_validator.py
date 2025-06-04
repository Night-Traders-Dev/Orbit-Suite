import time
import uuid

class TXValidator:
    def __init__(self, metadata):
        self.metadata = metadata
        self.errors = []
        self.corrections = []

        # Registry of validation rules
        self.rules = {
            "create_token": {
                "required": ["token_id", "name", "symbol", "supply", "creator", "timestamp"],
                "checks": {
                    "supply": self._is_positive_number,
                    "timestamp": self._is_recent_timestamp
                },
                "autofix": {
                    "token_id": lambda d: self._autofix(d, "token_id", str(uuid.uuid4())),
                    "timestamp": lambda d: self._autofix(d, "timestamp", time.time())
                }
            },
            "list_token": {
                "required": ["token_id", "symbol", "price", "lister", "exchange_fee", "timestamp"],
                "checks": {
                    "price": self._is_positive_number,
                    "exchange_fee": self._is_non_negative_number,
                    "timestamp": self._is_recent_timestamp
                },
                "autofix": {
                    "exchange_fee": lambda d: self._autofix(d, "exchange_fee", 0.01),
                    "timestamp": lambda d: self._autofix(d, "timestamp", time.time())
                }
            },
            "buy_token": {
                "required": ["order_id", "token_id", "symbol", "amount", "buyer", "exchange_fee", "timestamp"],
                "checks": {
                    "amount": self._is_positive_number,
                    "exchange_fee": self._is_non_negative_number,
                    "timestamp": self._is_recent_timestamp
                },
                "autofix": {
                    "order_id": lambda d: self._autofix(d, "order_id", str(uuid.uuid4())),
                    "exchange_fee": lambda d: self._autofix(d, "exchange_fee", 0.01),
                    "timestamp": lambda d: self._autofix(d, "timestamp", time.time())
                }
            },
            "sell_token": {
                "required": ["order_id", "token_id", "symbol", "amount", "seller", "exchange_fee", "timestamp"],
                "checks": {
                    "amount": self._is_positive_number,
                    "exchange_fee": self._is_non_negative_number,
                    "timestamp": self._is_recent_timestamp
                },
                "autofix": {
                    "order_id": lambda d: self._autofix(d, "order_id", str(uuid.uuid4())),
                    "exchange_fee": lambda d: self._autofix(d, "exchange_fee", 0.01),
                    "timestamp": lambda d: self._autofix(d, "timestamp", time.time())
                }
            },
            "token_transfer": {
                "required": ["sender", "receiver", "amount", "token_symbol", "timestamp", "signature"],
                "checks": {
                    "amount": self._is_positive_number,
                    "timestamp": self._is_recent_timestamp
                },
                "autofix": {
                    "timestamp": lambda d: self._autofix(d, "timestamp", time.time())
                }
            }
        }

    def validate(self):
        tx_type_dict = self.metadata.get("type", {})
        if not tx_type_dict:
            return False, "Missing 'type' in transaction metadata"

        for tx_name, tx_data in tx_type_dict.items():
            rule = self.rules.get(tx_name)
            if not rule:
                return False, f"Unknown transaction type: {tx_name}"

            valid, msg = self._validate_fields(
                tx_data,
                rule["required"],
                rule.get("checks", {}),
                rule.get("autofix", {})
            )
            if valid and self.corrections:
                return True, f"Valid with corrections: {', '.join(self.corrections)}"
            return valid, msg

        return False, "No transaction type found"

    def _validate_fields(self, data, required_fields, custom_checks={}, autofix={}):
        for field in required_fields:
            if field not in data:
                if field in autofix:
                    autofix[field](data)  # Pass data dict to the autofix function
                else:
                    return False, f"Missing required field: {field}"

        for field, check in custom_checks.items():
            try:
                if isinstance(data[field], str) and data[field].replace('.', '', 1).isdigit():
                    data[field] = float(data[field]) if '.' in data[field] else int(data[field])
                if not check(data[field]):
                    if field in autofix:
                        autofix[field](data)
                        if not check(data[field]):
                            return False, f"Invalid value for field: {field}"
                    else:
                        return False, f"Invalid value for field: {field}"
            except Exception as e:
                return False, f"Error validating field '{field}': {str(e)}"

        return True, "Valid transaction metadata"

    def _is_recent_timestamp(self, ts):
        now = time.time()
        return now - 300 < ts < now + 300  # ±5 minutes

    def _is_positive_number(self, val):
        try:
            return float(val) > 0
        except:
            return False

    def _is_non_negative_number(self, val):
        try:
            return float(val) >= 0
        except:
            return False

    def _autofix(self, data, key, default_value):
        data[key] = default_value
        self.corrections.append(f"Auto-filled '{key}'")
