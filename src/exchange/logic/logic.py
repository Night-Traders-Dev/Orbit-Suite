import uuid
from core.tx_util.tx_types import TXExchange
from core.tx_util.tx_validator import TXValidator

EXCHANGE_ADDR = "orbitxchg123"

# --- Exchange Logic ---
def create_buy_order(symbol, amount, buyer_addr):
    tx = TXExchange.buy_token(
        order_id=str(uuid.uuid4()),
        token_id="0001",  # TODO: dynamic token ID lookup
        symbol=symbol,
        amount=amount,
        buyer_address=buyer_addr,
        exchange_fee=0.01
    )
    return validate_and_log(tx)

def create_sell_order(symbol, amount, seller_addr):
    tx = TXExchange.sell_token(
        order_id=str(uuid.uuid4()),
        token_id="0001",  # TODO: dynamic token ID lookup
        symbol=symbol,
        amount=amount,
        seller_address=seller_addr,
        exchange_fee=0.01
    )
    return validate_and_log(tx)

def create_cancel_order(order_id, sender_addr):
    tx = TXExchange.cancel_order(
        order_id=order_id,
        sender_address=sender_addr
    )
    return validate_and_log(tx)

def validate_and_log(tx):
    validator = TXValidator(tx)
    valid, msg = validator.validate()
    if valid:
        # Log to file
        log_transaction(tx)
        # Broadcast (stub)
        broadcast_transaction(tx)
        return True, tx
    else:
        return False, msg

def log_transaction(tx):
    if not os.path.exists(TX_LOG_PATH):
        with open(TX_LOG_PATH, "w") as f:
            json.dump([], f)

    with open(TX_LOG_PATH, "r+") as f:
        data = json.load(f)
        data.append(tx)
        f.seek(0)
        json.dump(data, f, indent=2)

def broadcast_transaction(tx):
    # TODO: Replace this with actual Orbit Blockchain broadcast logic
    print("[✓] Broadcasting transaction to Orbit network:")
    print(json.dumps(tx, indent=2))
