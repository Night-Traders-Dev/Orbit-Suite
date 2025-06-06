import asyncio
from logic.logic import create_order
from core.ioutil import fetch_chain
from core.logutil import log_node_activity
from api import send_orbit_api
from core.tx_util.tx_types import TXExchange

async def match_orders(node_id):
    buy_orders = []
    sell_orders = []
    filled_order_ids = set()
    chain = fetch_chain()

    # Parse orders from chain
    for block in reversed(chain):
        for tx in block.get("transactions", []):
            note = tx.get("note")
            if not isinstance(note, dict):
                continue

            note_type = note.get("type")
            if not isinstance(note_type, dict):
                continue

            if "buy_token" in note_type:
                order = note_type["buy_token"]
                status = order.get("status")
                order_id = order.get("order_id")

                if status == "filled":
                    filled_order_ids.add(order_id)
                elif status == "open" and order_id not in filled_order_ids:
                    buy_orders.append(order)

            elif "sell_token" in note_type:
                order = note_type["sell_token"]
                status = order.get("status")
                order_id = order.get("order_id")

                if status == "filled":
                    filled_order_ids.add(order_id)
                elif status == "open" and order_id not in filled_order_ids:
                    sell_orders.append(order)

    # Match orders
    matched_pairs = []
    unmatched_buys = []
    unmatched_sells = sell_orders.copy()

    for buy in buy_orders:
        match = None
        for sell in unmatched_sells:
            if (
                buy["price"] == sell["price"]
                and buy["amount"] == sell["amount"]
                and buy["symbol"].upper() == sell["symbol"].upper()
                and buy["buyer"] != sell["seller"]  # Prevent self-trading
            ):
                match = sell
                break

        if match:
            unmatched_sells.remove(match)
            matched_pairs.append((buy, match))
        else:
            unmatched_buys.append(buy)

    # Process matched pairs
    for buy, sell in matched_pairs:
        print("\nMatching Buy/Sell Orders Found:")
        print("Buy:", buy)
        print("Sell:", sell)

        buyer = buy["buyer"]
        seller = sell["seller"]
        symbol = buy["symbol"].upper()
        amount = float(buy["amount"])
        price = float(buy["price"])
        total_orbit = round(amount * price, 6)

        # Create filled orders
        buy_result = await create_order(
            type="buy",
            symbol=symbol,
            price=price,
            amount=amount,
            address=buyer,
            order_id=buy["order_id"],
            status="filled"
        )

        sell_result = await create_order(
            type="sell",
            symbol=symbol,
            price=price,
            amount=amount,
            address=seller,
            order_id=sell["order_id"],
            status="filled"
        )




        # Transfer Token from Seller to Buyer
        if symbol != "ORBIT":
            token_tx = TXExchange.create_token_transfer_tx(
                sender=seller,
                receiver=buyer,
                amount=amount,
                token_symbol=symbol,
                note=f"Exchange: {symbol} to {buyer}"
            )
            token_success = await send_orbit_api(seller, buyer, 0.5, sell_result)  # Token tx + fee
        else:
            token_tx = ""
            token_success = True  # No extra transfer for ORBIT

        # Transfer ORBIT from Buyer to Seller
        orbit_success = await send_orbit_api(buyer, seller, total_orbit, buy_result)
        if token_success and orbit_success:
            log_node_activity(node_id, "[ORDERBOOK]", f"\n✅ Token {symbol} sent from {seller} to {buyer}")
            log_node_activity(node_id, "[ORDERBOOK]", f"✅ {total_orbit} ORBIT sent from {buyer} to {seller}")
        else:
            log_node_activity(node_id, "[ORDERBOOK]", "\n⛔️ One or both transfers failed. Skipping order fill.")
            continue  # Skip creating filled orders if payment failed





