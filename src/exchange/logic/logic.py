# logic/logic.py

import uuid, time
from core.exchangeutil import get_token_id, get_user_token_balance
from core.ioutil import get_address_from_label
from core.tx_util.tx_types import TXExchange
from core.tx_util.tx_validator import TXValidator
from core.orderutil import token_stats
from core.walletutil import get_wallet_stats
from core.tx_util.tx_types import TXExchange

try:
    from bot.api import get_user_address, send_orbit_api, get_user_tokens
except Exception as e:
    from api import get_user_address, send_orbit_api, get_user_tokens
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
    tx = TXExchange.create_token(
        token_id=str(uuid.uuid4()),
        name=name,
        symbol=symbol,
        supply=supply,
        creator=creator,
        listing_fee=250  # Could be pulled from config
    )

    unsigned_tx = TXExchange.create_token_transfer_tx(
        sender=get_address_from_label("system"),
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
        tranfer_token = await send_orbit_api(creator, get_address_from_label("system"), 2.5, order=unsigned_tx)
    return (True, tx) if valid else (False, msg)


async def deposit(symbol, amount, receiver, sender):
    result = await send_orbit_api(sender, receiver, amount, order={"Deposit": {"sender": sender, "receiver": receiver, "amount": amount}})
    return(True, {"Orbit Deposit": {"sender": sender, "receiver": receiver, "amount": amount}})

async def withdrawal(amount, receiver, sender):
    import re
    symbol = "CORAL"
    response = await get_wallet_stats(symbol)
    for wallet in response:
        if sender in wallet:
            match = re.search(r': ([\d,\.]+)\(([\d,\.]+) Orbit\)', wallet)
            if match:
                quantity_str = match.group(1).replace(",", "")
                orbit_value_str = match.group(2).replace(",", "")
                quantity = float(quantity_str)
                orbit_value = float(orbit_value_str)
                current_price = (orbit_value / quantity)
                transfer_amount = (current_price * amount)
    token_tx = TXExchange.create_token_transfer_tx(
    sender=sender,
    receiver=receiver,
    amount=transfer_amount,
    token_symbol=symbol,
    note={"Withdrawal": {"sender": sender, "receiver": receiver, "symbol": symbol, "amount": transfer_amount}}
    )
    orbit_amount = 5
    txt = f"{symbol} Withdrawal"
    result = await send_orbit_api(receiver, sender, orbit_amount, order=token_tx)
    return(True, {txt: {"sender": sender, "receiver": receiver, "amount": transfer_amount}})

async def swap_token(from_token, to_token, amount, receiver, sender):
    user = receiver
    receiver = sender
    import re
#    tokens_to_swap = [from_token, to_token]
    if from_token != "ORBIT" and to_token == "ORBIT":
        token_res = await get_wallet_stats(from_token)
    else:
        to_token != "ORBIT" and from_token == "ORBIT":
            token_res = await get_wallet_stats(to_token)
    for wallet in token_res:
        if sender in wallet:
            match = re.search(r': ([\d,\.]+)\(([\d,\.]+) Orbit\)', wallet)
            if match:
                quantity_str = match.group(1).replace(",", "")
                orbit_value_str = match.group(2).replace(",", "")
                quantity = float(quantity_str)
                orbit_value = float(orbit_value_str)
                current_price = (orbit_value / quantity)
                transfer_amount = (current_price * amount)
    token_tx = TXExchange.create_token_transfer_tx(
    sender=sender,
    receiver=receiver,
    amount=transfer_amount,
    token_symbol=to_token,
    note={"Swap": {"sender": sender, "receiver": user, "from_token": from_token, "to_token": to_token, "amount": transfer_amount, "price": current_price}}
    )
    orbit_amount = transfer_amount * 0.015 # 1.5% orbit fee for swap
    txt = f"{to_token}/{from_token} Swap"
    result = await send_orbit_api("ORB.52234E31F8C4351E2040E6C7", sender, orbit_amount, order=token_tx)
    return(True, {txt: {"sender": sender, "receiver": user,  "from_token": from_token, "to_token": to_token, "amount": transfer_amount, "price": current_price}})


EXCHANGE_PRICE = 0.1



async def buy_token_from_exchange(symbol, amount, buyer_address):
    token_id = get_token_id(symbol.upper())
    filled, open_orders, metadata, tx_cnt, history_data, price_history_dates, price_history_values, open_book = await token_stats(symbol.upper())
    if not token_id:
        return False, f"Token '{symbol.upper()}' not found."

    filled_dict = {stat["token"]: stat for stat in filled if isinstance(stat, dict)}
    open_dict = {stat["token"]: stat for stat in open_orders if isinstance(stat, dict)}
    meta_dict = {stat["symbol"]: stat for stat in metadata if isinstance(stat, dict)}
    cnt_dict = {stat["token"]: stat for stat in tx_cnt if isinstance(stat, dict)}

    all_tokens = sorted(set(filled_dict.keys()) | set(open_dict.keys()) | set(meta_dict.keys()) | set(cnt_dict.keys()))
    f_stat = filled_dict.get(symbol, {})
    m_stat = meta_dict.get(symbol, {})
    current_price = f_stat.get("current_price") or EXCHANGE_PRICE
    owner = m_stat.get("owner", "")
    exchange_balance = get_user_token_balance(EXCHANGE_ADDRESS, symbol.upper())
    if exchange_balance < amount:
        return False, "Exchange does not have enough token supply available."

    total_cost = round(amount * current_price, 6)


    token_tx = TXExchange.create_token_transfer_tx(
        sender=EXCHANGE_ADDRESS,
        receiver=buyer_address,
        amount=amount,
        token_symbol=symbol.upper(),
        note="Token purchased from exchange"
    )

    shre = round(total_cost * 0.01, 6)
    sent = await send_orbit_api(buyer_address, EXCHANGE_ADDRESS, total_cost, order=token_tx)
    if True in sent:
        fee = await send_orbit_api(EXCHANGE_ADDRESS, owner, shre, order="")
    if False in sent or False in fee:
        return False, "Token delivery failed."

    return True, {
        "orbit_spent": total_cost,
        "tokens_received": amount,
        "symbol": symbol.upper()
    }


async def trade_token_on_exchange(
    symbol: str,
    amount: float,
    user_address: str,
    action: str = "BUY",
):
    """
    Buy or sell a token on the exchange.

    action: "buy" to purchase from exchange,
            "sell" to sell back into exchange
    """
    symbol = symbol.upper()
    token_id = get_token_id(symbol)
    if not token_id:
        return False, f"Token '{symbol}' not found."

    # fetch stats
    filled, open_orders, metadata, tx_cnt, _, _, _, _ = await token_stats(symbol)
    f_stat = {s["token"]: s for s in filled if isinstance(s, dict)}.get(symbol, {})
    m_stat = {s["symbol"]: s for s in metadata if isinstance(s, dict)}.get(symbol, {})
    current_price = f_stat.get("current_price") or EXCHANGE_PRICE
    owner_address = m_stat.get("owner", "")

    # determine price & check balances
    if action == "BUY":
        unit_price = (current_price  * 1.025)  # buyer pays 2.5% premium
        # ensure exchange has tokens
        if get_user_token_balance(EXCHANGE_ADDRESS, symbol) < amount:
            return False, "Exchange does not have enough token supply."
        total = round(amount * unit_price, 6)
        # create token transfer: exchange → buyer
        token_tx = TXExchange.create_token_transfer_tx(
            sender=EXCHANGE_ADDRESS,
            receiver=user_address,
            amount=amount,
            token_symbol=symbol,
            note="Token purchased from exchange"
        )
        # buyer pays exchange
        orbit_sent = await send_orbit_api(user_address, EXCHANGE_ADDRESS, total, order=token_tx)

        # pay owner 1% fee from the incoming orbit
        fee = round(total * 0.01, 6)
        owner_paid = await send_orbit_api(EXCHANGE_ADDRESS, owner_address, fee, order="")
        if False in orbit_sent or False in owner_paid:
            return False, "Buy transaction failed."

        return True, {
            "action": "BUY",
            "symbol": symbol,
            "tokens_received": amount,
            "orbit_spent": total,
            "owner_fee": fee
        }

    elif action == "SELL":
        # seller pays 2.5% discount
        unit_price = round(current_price * 0.975, 6)
        # ensure seller has tokens
        if get_user_token_balance(user_address, symbol) < amount:
            return False, "User does not have enough tokens to sell."
        total = round(amount * unit_price, 6)

        # create token transfer: seller → exchange
        token_tx = TXExchange.create_token_transfer_tx(
            sender=user_address,
            receiver=EXCHANGE_ADDRESS,
            amount=amount,
            token_symbol=symbol,
            note="Token sold to exchange"
        )
        #token_sent = await send_orbit_api(user_address, EXCHANGE_ADDRESS, 0.5, order=token_tx)
        # exchange pays seller in orbit
        orbit_sent = await send_orbit_api(EXCHANGE_ADDRESS, user_address, total, order=token_tx)

        # pay owner 1% fee from the proceeds
        fee = round(total * 0.01, 6)
        owner_paid = await send_orbit_api(EXCHANGE_ADDRESS, owner_address, fee, order="")
        if False in orbit_sent or False in owner_paid:
            return False, "Sell transaction failed."

        return True, {
            "action": "SELL",
            "symbol": symbol,
            "tokens_sold": amount,
            "orbit_received": total - fee,
            "owner_fee": fee
        }

    else:
        return False, f"Invalid action '{action}'. Use 'BUY' or 'SELL'."