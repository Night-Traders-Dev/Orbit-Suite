'''
    Orbit Market
    Order.py
'''


class Order:
    def __init__(self, player, quantity, price):
        self.player = player
        self.quantity = quantity
        self.price = price

class OrderUtil:
    def __init__(self, ledger):
        self.ledger = ledger


    def add_order(self, order_type, order, name):
        self.ledger.order_book[order_type].append(order)
        self.ledger.order_book[order_type].sort(key=lambda o: o.price, reverse=(order_type == "buy"))
        self.match_orders(name)

    def match_orders(self, name):
        buy_orders = self.ledger.order_book["buy"]
        sell_orders = self.ledger.order_book["sell"]
        self.name = name

        while buy_orders and sell_orders and buy_orders[0].price >= sell_orders[0].price:
            buyer = buy_orders[0]
            seller = sell_orders[0]
            trade_price = seller.price
            quantity = min(buyer.quantity, seller.quantity)

            total_cost = quantity * trade_price
            if buyer.player.balance < total_cost:
                buy_orders.pop(0)
                continue

            # Prevent seller from selling more than they own
            if seller.player.portfolio.get(self.name, 0) < quantity:
                sell_orders.pop(0)
                continue

            buyer.player.balance -= total_cost
            seller.player.balance += total_cost

            buyer.player.portfolio[self.name] = buyer.player.portfolio.get(self.name, 0) + quantity
            seller.player.portfolio[self.name] -= quantity

            print(f"Trade executed: {quantity:,} x {self.name} @ ${trade_price:,.4f}")

            trade_record = {
                "timestamp": time.time(),
                "stock": self.name,
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

            # Price adjustment logic with cap
            delta = (quantity / self.supply) * trade_price * 0.1
            max_delta = self.last_price * 0.05  # Cap price movement per trade to 5%
            delta = min(delta, max_delta)

            if buyer.quantity > seller.quantity:
                self.last_price += delta
            else:
                self.last_price -= delta

            # Clamp and round price properly
            self.last_price = round(max(0.0001, min(self.last_price, 100000)), 4)

            buyer.quantity -= quantity
            seller.quantity -= quantity

            if buyer.quantity == 0:
                buy_orders.pop(0)
            if seller.quantity == 0:
                sell_orders.pop(0)
