# logic/logic.py

import uuid
from core.tx_util.tx_types import TXExchange
from core.tx_util.tx_validator import TXValidator
from bot.api import get_user_address, send_orbit_api


def create_buy_order(symbol, amount, buyer_addr):
    tx = TXExchange.buy_token(
        order_id=str(uuid.uuid4()),
        token_id="0001",  # TODO: get_token_id(symbol)
        symbol=symbol,
        amount=amount,
        buyer_address=buyer_addr,
        exchange_fee=0.01
    )
    validator = TXValidator(tx)
    valid, msg = validator.validate()
    return (True, tx) if valid else (False, msg)

def create_sell_order(symbol, amount, seller_addr):
    tx = TXExchange.sell_token(
        order_id=str(uuid.uuid4()),
        token_id="0001",  # TODO: get_token_id(symbol)
        symbol=symbol,
        amount=amount,
        seller_address=seller_addr,
        exchange_fee=0.01
    )
    validator = TXValidator(tx)
    valid, msg = validator.validate()
    return (True, tx) if valid else (False, msg)

def cancel_order(order_id):
    # Placeholder logic
    return True, f"Order {order_id} canceled (not really, just a stub)."

def quote_symbol(symbol):
    # Placeholder response
    return True, {
        "symbol": symbol,
        "price": 1.23,
        "volume": 10000,
        "updated": "Just now"
    }

async def create_token(name, symbol, supply, creator):
    tx = TXExchange.create_token(
        token_id=str(uuid.uuid4()),
        name=name,
        symbol=symbol,
        supply=supply,
        creator=creator,
        listing_fee=250  # Could be pulled from config
    )
    validator = TXValidator(tx)
    valid, msg = validator.validate()
    if valid:
        exchange="ORB.A6C19210F2B823246BA1DCA7"
        creator = tx['type']['create_token']['creator']
        listing_fee = tx['type']['create_token']['listing_fee']
        success = await send_orbit_api(creator, exchange, 250, order=tx)
    return (True, tx) if valid else (False, msg)
