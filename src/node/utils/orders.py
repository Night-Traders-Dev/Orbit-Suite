from core.logutil import log_node_activity
from config.configutil import TXConfig, OrbitDB
from logic.logic import create_order

orbit_db = OrbitDB()

def match_orders(chain):
    # Collect current open orders
    buy_orders = []
    sell_orders = []
    for block in chain:
        for tx in block.get("transactions", []):
            if tx.get("type") == "order":
                order_type = tx.get("data", {}).get("side")
                order_price = tx.get("data", {}).get("price")
                order_amount = tx.get("data", {}).get("amount")
                order_owner = tx.get("sender")
                order_time = tx.get("timestamp")
                order_id = tx.get("txid")

                if all([order_type, order_price, order_amount, order_owner]):
                    order_entry = {
                        "txid": order_id,
                        "owner": order_owner,
                        "price": order_price,
                        "amount": order_amount,
                        "timestamp": order_time,
                        "block_index": block.get("index"),
                        "block_hash": block.get("hash")
                    }
                    if order_type == "buy":
                        buy_orders.append(order_entry)
                    elif order_type == "sell":
                        sell_orders.append(order_entry)

    # Sort buy orders (highest price first, then earliest)
    buy_orders.sort(key=lambda x: (-x["price"], x["timestamp"]))
    # Sort sell orders (lowest price first, then earliest)
    sell_orders.sort(key=lambda x: (x["price"], x["timestamp"]))

    # Try to match orders
    matches = []
    for buy in buy_orders:
        for sell in sell_orders:
            if buy["price"] >= sell["price"] and buy["amount"] > 0 and sell["amount"] > 0:
                matched_amount = min(buy["amount"], sell["amount"])
                match = {
                    "buyer": buy["owner"],
                    "seller": sell["owner"],
                    "price": sell["price"],
                    "amount": matched_amount,
                    "timestamp": time.time()
                }
                matches.append(match)
                # Update order amounts
                buy["amount"] -= matched_amount
                sell["amount"] -= matched_amount

                if buy["amount"] == 0:
                    break  # Move to next buy order

    # Convert matches into transactions and add to mempool or new block
    for match in matches:
        success, result = await create_order("buy", "Orbit", 10.23, 50, "test: address", order_id=order_id, status="filled")

    if matches:
        log_node_activity(self.node_id, "[MATCH]", f"{len(matches)} orders matched and added to mempool.")
