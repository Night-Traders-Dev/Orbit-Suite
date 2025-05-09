'''
    Orbit Market
    Stock.py
'''
from Ledger import Ledger
import random
import time

class Stock:
    def __init__(self, name: str, initial_price: float, supply: int, ledger: Ledger):
        self.name = name
        self.initial_price = initial_price
        self.supply = supply
        self.ledger = ledger

        # Initialize tracking data inside the ledger
        self.ledger.stocks[self.name] = {
            "last_price": initial_price,
            "supply": supply
        }

    def get_market_price(self):
        buy_orders = self.ledger.order_book[self.name]["buy"]
        sell_orders = self.ledger.order_book[self.name]["sell"]
        best_buy = buy_orders[0].price if buy_orders else None
        best_sell = sell_orders[0].price if sell_orders else None
        return best_buy, best_sell

    def get_volume(self, since_seconds_ago=None):
        now = time.time()
        buy_volume = 0
        sell_volume = 0
        total_volume = 0

        for trade in self.ledger.trade_history:
            if trade["stock"] != self.name:
                continue
            if since_seconds_ago is None or now - trade["timestamp"] <= since_seconds_ago:
                qty = trade["quantity"]
                if trade["buyer"] != "N/A":
                    buy_volume += qty
                if trade["seller"] != "N/A":
                    sell_volume += qty
                total_volume += qty

        return {
            "buy_volume": buy_volume,
            "sell_volume": sell_volume,
            "total_volume": total_volume
        }

    def __str__(self):
        buy, sell = self.get_market_price()
        last_price = self.ledger.stocks[self.name]["last_price"]
        buy_str = f"${buy:,.4f}" if buy else "N/A"
        sell_str = f"${sell:,.4f}" if sell else "N/A"
        return (
            f"{self.name} | Price: ${last_price:,.4f} | "
            f"Supply: {self.supply:,} | Buy: {buy_str} | Sell: {sell_str}"
        )

    def tick(self):
        if not self.ledger.order_book[self.name]["buy"] and not self.ledger.order_book[self.name]["sell"]:
            return

        base_drift = random.uniform(-0.01, 0.01)  # +/- 1%
        pressure = len(self.ledger.order_book[self.name]["buy"]) - len(self.ledger.order_book[self.name]["sell"])

        pressure_drift = 0
        if pressure > 2:
            pressure_drift = 0.005
        elif pressure < -2:
            pressure_drift = -0.005

        total_drift = base_drift + pressure_drift
        total_drift = max(-0.03, min(0.03, total_drift))  # Clamp to ±3%

        last_price = self.ledger.stocks[self.name]["last_price"]
        new_price = last_price * (1 + total_drift)
        self.ledger.stocks[self.name]["last_price"] = round(max(0.0001, min(new_price, 100000)), 4)

    def show_trade_history(self, limit=10):
        print(f"\n--- Last {limit} Trades for {self.name} ---")
        trades = [t for t in self.ledger.trade_history if t["stock"] == self.name][-limit:]
        for trade in trades:
            t = time.strftime('%Y-%m-%d %H:%M:%S', time.localtime(trade["timestamp"]))
            print(f"[{t}] {trade['buyer']} bought {trade['quantity']:,} from {trade['seller']} @ ${trade['price']:,.4f}")