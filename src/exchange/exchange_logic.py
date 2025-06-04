from core.tx_util.tx_types import TXExchange
from core.tx_util.tx_validator import TXValidator
import uuid, time

EXCHANGE_ADDR = "orbitxchg123"

def create_buy_order(symbol, amount, buyer_addr):
    tx = TXExchange.buy_token(
        order_id=str(uuid.uuid4()),
        token_id="0001", #get_token_id(symbol),
        symbol=symbol,
        amount=amount,
        buyer_address=buyer_addr,
        exchange_fee=0.01
    )
    validator = TXValidator(tx)
    valid, msg = validator.validate()
    if valid:
        return True, tx
    else:
        return False, msg

status, result = create_buy_order("ORB", 10, "ORB.BDB6B8ED7E609BD9DC42E5B5")
print(f"Status: {status}\nResult: {result}")
