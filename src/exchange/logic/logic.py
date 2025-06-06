# logic/logic.py

import uuid, time
from core.exchangeutil import get_token_id, get_user_token_balance
from core.tx_util.tx_types import TXExchange
from core.tx_util.tx_validator import TXValidator
try:
    from bot.api import get_user_address, send_orbit_api
except Exception as e:
    from api import get_user_address, send_orbit_api
try:
    from configure import EXCHANGE_ADDRESS
except Exception as e:
    pass

async def create_order(type, symbol, price, amount, address, status="open", order_id=None):
    token_id = get_token_id(symbol.upper())

    if order_id == None:
        order_id=str(uuid.uuid4())
    else:
        order_id=order_id
    tx = TXExchange.tx_token(
        type=type,
        order_id=order_id,
        token_id=token_id,
        symbol=symbol,
        price=price,
        amount=amount,
        address=address,
        exchange_fee=0.01,
        status=status
    )

    validator = TXValidator(tx)
    valid, msg = validator.validate()

    sent = await send_orbit_api(
        sender=address,
        recipient=EXCHANGE_ADDRESS,
        amount=0.01,
        order=tx
    )

    return (True, tx) if valid else (False, msg)


async def cancel_order(order_id, canceller_address, symbol=None):
    tx = TXExchange.cancel_order(
        order_id=order_id,
        canceller_address=canceller_address,
        symbol=symbol
    )

    validator = TXValidator(tx)
    valid, msg = validator.validate()
    if not valid:
        return False, msg

    cancel_fee = 0.01

    sent = await send_orbit_api(
        sender=canceller_address,
        recipient=EXCHANGE_ADDRESS,
        amount=cancel_fee,
        order=tx
    )

    if not sent:
        return False, "Transaction submission failed."

    return True, f"Cancel request for order {order_id} submitted successfully."

def quote_symbol(symbol):
    return True, {
        "symbol": symbol,
        "price": 1.23,
        "volume": 10000,
        "updated": "Just now"
    }

async def create_token(name, symbol, supply, creator):
    if get_token_id(symbol):
        msg = "Token already exists"
        return (False, msg)
    tx = TXExchange.create_token(
        token_id=str(uuid.uuid4()),
        name=name,
        symbol=symbol,
        supply=supply,
        creator=creator,
        listing_fee=250  # Could be pulled from config
    )

    unsigned_tx = TXExchange.create_token_transfer_tx(
        sender="system",
        receiver=EXCHANGE_ADDRESS,
        amount=supply,
        token_symbol=symbol,
        note="Token Mint",
        signature=""
    )

    tx_type = list(unsigned_tx["type"].keys())[0]
    tx_data = unsigned_tx["type"][tx_type]
    unsigned_tx["type"][tx_type] = tx_data



    validator = TXValidator(tx)
    valid, msg = validator.validate()
    if valid:
        creator = tx['type']['create_token']['creator']
        listing_fee = tx['type']['create_token']['listing_fee']
        mint_token = await send_orbit_api(creator, EXCHANGE_ADDRESS, 250, order=tx)
        tranfer_token = await send_orbit_api(creator, "system", 2.5, order=unsigned_tx)
    return (True, tx) if valid else (False, msg)



EXCHANGE_PRICE = 0.1

async def buy_token_from_exchange(symbol, amount, buyer_address):
    token_id = get_token_id(symbol.upper())
    if not token_id:
        return False, f"Token '{symbol.upper()}' not found."

    exchange_balance = get_user_token_balance(EXCHANGE_ADDRESS, symbol.upper())
    if exchange_balance < amount:
        return False, "Exchange does not have enough token supply available."

    total_cost = round(amount * EXCHANGE_PRICE, 6)


    token_tx = TXExchange.create_token_transfer_tx(
        sender=EXCHANGE_ADDRESS,
        receiver=buyer_address,
        amount=amount,
        token_symbol=symbol.upper(),
        note="Token purchased from exchange"
    )

    sent = await send_orbit_api(buyer_address, EXCHANGE_ADDRESS, total_cost, order=token_tx)
    if not sent:
        return False, "Token delivery failed."

    return True, {
        "orbit_spent": total_cost,
        "tokens_received": amount,
        "symbol": symbol.upper()
    }
