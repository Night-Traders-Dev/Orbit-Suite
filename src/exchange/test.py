from logic.logic import create_order
from core.ioutil import fetch_chain
import asyncio

async def main():
    buy_orders = []
    sell_orders = []
    filled_order_ids = set()
    chain = fetch_chain()

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
            if (buy["price"] == sell["price"] and
                buy["amount"] == sell["amount"] and
                buy["symbol"].upper() == sell["symbol"].upper() and
                buy["buyer"] != sell["seller"]):  # ✅ Avoid self-trading
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

        # Create filled orders
        buy_result = await create_order(
            type="buy_token",
            symbol=buy["symbol"],
            price=buy["price"],
            amount=buy["amount"],
            address=buy["buyer"],
            order_id=buy["order_id"],
            status="filled"
        )
        print("\nBuy Fill Result:", buy_result)

        sell_result = await create_order(
            type="sell_token",
            symbol=sell["symbol"],
            price=sell["price"],
            amount=sell["amount"],
            address=sell["seller"],
            order_id=sell["order_id"],
            status="filled"
        )
        print("\nSell Fill Result:", sell_result)

    # Optional: Show remaining unmatched
    print("\nUnmatched Buy Orders:", unmatched_buys)
    print("\nUnmatched Sell Orders:", unmatched_sells)


if __name__ == "__main__":
    asyncio.run(main())
