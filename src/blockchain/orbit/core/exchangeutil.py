# exchangeutil.py
import json
import os
import time
from blockchain.tokenutil import send_orbit
EXCHANGE_DB = "data/exchange_data.json"

# Load or initialize exchange state
def load_exchange():
    if os.path.exists(EXCHANGE_DB):
        with open(EXCHANGE_DB, 'r') as f:
            return json.load(f)
    return {"orders": []}

def save_exchange(data):
    with open(EXCHANGE_DB, 'w') as f:
        json.dump(data, f, indent=2)

def append_order(order):
    data = load_exchange()
    data.setdefault("orders", [])
    data["orders"].append(order)
    save_exchange(data)

def place_order(user, side, amount, price, wallet):
    data = load_exchange()
    recipient = "exchange01"
    order = {
        "id": f"{user}-{int(time.time() * 1000)}",
        "user": user,
        "side": side,
        "amount": amount,
        "price": price,
        "timestamp": time.time(),
    }
    if side == "buy":
        total_value = (amount * price)
        if wallet < total_value:
            return False, "Insufficient USD"
        send_orbit(user, recipient, total_value)
    elif side == "sell":
        if wallet < amount:
            return False, "Insufficient ORBIT"
 #       update_balance(data, user, delta_orbit=-amount)
    else:
        return False, "Invalid side"

    append_order(order)
    return True, order["id"]

def cancel_order(user, order_id):
    data = load_exchange()
    for order in data["orders"]:
        if order["id"] == order_id and order["user"] == user:
            if order["side"] == "buy":
                refund = order["amount"] * order["price"]
                send_orbit("exchange01", user, refund)
                data["orders"].remove(order)
                save_exchange(data)
                return True
    return False


def match_orders(data):
    buys = sorted([o for o in data["orders"] if o["side"] == "buy"], key=lambda o: (-o["price"], o["timestamp"]))
    sells = sorted([o for o in data["orders"] if o["side"] == "sell"], key=lambda o: (o["price"], o["timestamp"]))
    matched = []

    for buy in buys:
        for sell in sells:
            if buy["price"] >= sell["price"] and buy["amount"] > 0 and sell["amount"] > 0:
                trade_amount = min(buy["amount"], sell["amount"])
                trade_price = sell["price"]

                update_balance(data, buy["user"], delta_orbit=trade_amount)
                update_balance(data, sell["user"], delta_usd=trade_amount * trade_price)

                buy["amount"] -= trade_amount
                sell["amount"] -= trade_amount

                data["trades"].append({
                    "buyer": buy["user"],
                    "seller": sell["user"],
                    "amount": trade_amount,
                    "price": trade_price,
                    "timestamp": time.time()
                })

                matched.append((buy["id"], sell["id"]))

    data["orders"] = [o for o in data["orders"] if o["amount"] > 0]
    return matched

def get_order_book():
    data = load_exchange()
    data.setdefault("orders", [])
    buys = sorted(
        [o for o in data["orders"] if o.get("side") == "buy"],
        key=lambda o: (-o.get("price", 0), o.get("timestamp", 0))
    )
    sells = sorted(
        [o for o in data["orders"] if o.get("side") == "sell"],
        key=lambda o: (o.get("price", 0), o.get("timestamp", 0))
    )
    return buys, sells

def get_recent_trades(data, limit=10):
    return data["trades"][-limit:]
