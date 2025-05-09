'''
    Orbit Market
    Stock.py
'''
from Ledger import Ledger
import random
import time

class Stock:
    def __init__(self, name: str, initial_price: float, supply: int, ledger):
        self.name = name
        self.initial_price = initial_price
        self.supply = supply
        self.ledger = ledger

    def get_market_price(self):
        best_buy = self.ledger.order_book["buy"][0].price if self.ledger.order_book["buy"] else None
        best_sell = self.ledger.order_book["sell"][0].price if self.ledger.order_book["sell"] else None
        return best_buy, best_sell

    def get_volume(self, since_seconds_ago=None):
        now = time.time()
        buy_volume = 0
        sell_volume = 0
        total_volume = 0

        for trade in self.ledger.trade_history:
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
        buy_str = f"${buy:,.4f}" if buy else "N/A"
        sell_str = f"${sell:,.4f}" if sell else "N/A"
        return (
            f"{self.name} | Price: ${self.ledger.last_price:,.4f} | "
            f"Supply: {self.supply:,} | Buy: {buy_str} | Sell: {sell_str}"
        )

    def tick(self):
        if not self.ledger.order_book["buy"] and not self.ledger.order_book["sell"]:
            return  # No market activity, skip drift

        base_drift = random.uniform(-0.01, 0.01)  # +/- 1% base drift
        pressure = len(self.ledger.order_book["buy"]) - len(self.ledger.order_book["sell"])

        pressure_drift = 0
        if pressure > 2:
            pressure_drift = 0.005  # 0.5% up
        elif pressure < -2:
            pressure_drift = -0.005  # 0.5% down

        total_drift = base_drift + pressure_drift
        max_drift = 0.03  # Max 3% change per tick

        total_drift = max(-max_drift, min(max_drift, total_drift))

        self.ledger.last_price *= (1 + total_drift)
        self.ledger.last_price = round(max(0.0001, min(self.ledger.last_price, 100000)), 4)

    def show_trade_history(self, limit=10):
        print(f"\n--- Last {limit} Trades for {self.name} ---")
        for trade in self.ledger.trade_history[-limit:]:
            t = time.strftime('%Y-%m-%d %H:%M:%S', time.localtime(trade["timestamp"]))
            print(f"[{t}] {trade['buyer']} bought {trade['quantity']:,} from {trade['seller']} @ ${trade['price']:,.4f}")
