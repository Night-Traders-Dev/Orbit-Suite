'''
    Orbit Market
    Order.py
'''

import time

class Order:
    def __init__(self, player, quantity, price):
        self.player = player
        self.quantity = quantity
        self.price = price

class OrderUtil:
    def __init__(self, ledger):
        self.ledger = ledger

    def add_order(self, stock_name, order_type, order, trader_name):
        # Initialize stock entry if missing
        if stock_name not in self.ledger.order_book:
            self.ledger.order_book[stock_name] = {"buy": [], "sell": []}

        self.ledger.order_book[stock_name][order_type].append(order)
        self.ledger.order_book[stock_name][order_type].sort(
            key=lambda o: o.price, reverse=(order_type == "buy")
        )
        self.match_orders(stock_name)

    def match_orders(self, stock_name):
        book = self.ledger.order_book.get(stock_name)
        if not book:
            return

        buy_orders = book["buy"]
        sell_orders = book["sell"]

        while buy_orders and sell_orders and buy_orders[0].price >= sell_orders[0].price:
            buyer = buy_orders[0]
            seller = sell_orders[0]
            trade_price = seller.price
            quantity = min(buyer.quantity, seller.quantity)

            total_cost = quantity * trade_price
            if buyer.player.balance < total_cost:
                buy_orders.pop(0)
                continue

            if seller.player.portfolio.get(stock_name, 0) < quantity:
                sell_orders.pop(0)
                continue

            buyer.player.balance -= total_cost
            seller.player.balance += total_cost

            buyer.player.portfolio[stock_name] = buyer.player.portfolio.get(stock_name, 0) + quantity
            seller.player.portfolio[stock_name] -= quantity

            print(f"Trade executed: {quantity:,} x {stock_name} @ ${trade_price:,.4f}")

            trade_record = {
                "timestamp": time.time(),
                "stock": stock_name,
                "quantity": quantity,
                "price": trade_price,
                "buyer": buyer.player.name,
                "seller": seller.player.name
            }

            self.ledger.trade_history.append(trade_record)
            if hasattr(buyer.player, "trade_history"):
                buyer.player.trade_history.append(trade_record)
            if hasattr(seller.player, "trade_history"):
                seller.player.trade_history.append(trade_record)

            # Price adjustment logic
            stock_info = self.ledger.stocks.get(stock_name, {})
            supply = stock_info.get("supply", 1)
            last_price = stock_info.get("last_price", trade_price)

            delta = (quantity / supply) * trade_price * 0.1
            max_delta = last_price * 0.05
            delta = min(delta, max_delta)

            new_price = last_price + delta if buyer.quantity > seller.quantity else last_price - delta
            new_price = round(max(0.0001, min(new_price, 100000)), 4)

            self.ledger.stocks[stock_name]["last_price"] = new_price

            buyer.quantity -= quantity
            seller.quantity -= quantity

            if buyer.quantity == 0:
                buy_orders.pop(0)
            if seller.quantity == 0:
                sell_orders.pop(0)