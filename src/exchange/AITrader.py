'''
    Orbit Market
    AITrader.py
'''
import random
import statistics
from Order import Order, OrderUtil
from collections import deque
import time

class AIinit:
    def __init__(self, market, ledger):
        self.market = market
        self.ai_traders = []
        self.trader_specs = []
        self.trader_specs.extend([
            ("MM", "maker", 15, (5_000, 10_000)),
            ("Trend", "trend", 30, (7_500, 15_000)),
            ("Swing", "swing", 40, (10_000, 20_000)),
            ("Whale", "whale", 10, (50_000, 100_000)),
            ("Trader", "risky", 80, (2_000, 7_500)),
        ])
        for prefix, role, count, balance_range in self.trader_specs:
            for i in range(1, count + 1):
                starting_balance = random.randint(*balance_range)
                agent = AITrader(f"{prefix}{i}", role, starting_balance, market, ledger)
                self.ai_traders.append(agent)
                for stock in market.stocks.values():
                    max_airdrop = int(stock.supply * 0.01)
                    quantity = random.randint(0, max_airdrop)
                    if quantity > 0:
                        agent.portfolio[stock.name] = quantity

class AITrader:
    def __init__(self, name: str, role, balance, market, ledger):
        self.name = name
        self.role = role
        self.balance = balance
        self.ledger = ledger
        self.order_util = OrderUtil(self.ledger)
        self.portfolio = {}
        self.price_memory = {}
        self.trade_history = self.ledger.trade_history
        self.avg_buy_price = {}
        self.stats = {
            "buys": 0,
            "sells": 0,
            "buy_total": 0.0,
            "sell_total": 0.0,
            "profit": 0.0
        }

        if self.role == "risky":
            self.role_cap = random.randint(20, 300)
        else:
            self.role_cap = {
                "maker": 20,
                "trend": 30,
                "swing": 40,
                "whale": 100
            }.get(self.role, 25)

    def act(self, market):
        for stock in market.stocks.values():
            self.update_memory(stock)
            decision = self.analyze(stock)

            if self.role == "swing" and not self.ledger.order_book["buy"]:
                print(f"{self.name} ({self.role}) sees an opportunity to BUY {stock.name} as no buy orders are available.")
                self.buy_market(stock)
                self.place_initial_sell_order(stock)

            if decision == "buy" and self.ledger.order_book["sell"]:
                best_offer = self.ledger.order_book["sell"][0]
                potential_quantity = min(best_offer.quantity, 25)
                print(f"{self.name} ({self.role}) decided to BUY {potential_quantity} of {stock.name} @ ${best_offer.price:.4f}")
            elif decision == "sell" and self.ledger.order_book["buy"]:
                best_bid = self.ledger.order_book["buy"][0]
                shares_owned = self.portfolio.get(stock.name, 0)
                potential_quantity = min(best_bid.quantity, shares_owned)
                print(f"{self.name} ({self.role}) decided to SELL {potential_quantity} of {stock.name} @ ${best_bid.price:.4f}")
            else:
                print(f"{self.name} ({self.role}) decided to {decision.upper()} on {stock.name}")

            if decision == "buy":
                self.buy_market(stock)
            elif decision == "sell":
                self.sell_market(stock)
            elif decision == "make_market":
                self.make_market(stock)
            elif decision == "big_dump":
                self.big_dump(stock)

    def update_memory(self, stock):
        if stock.name not in self.price_memory:
            self.price_memory[stock.name] = deque(maxlen=10)
        self.price_memory[stock.name].append(self.ledger.stocks[stock.name]["last_price"])

    def analyze(self, stock):
        memory = self.price_memory.get(stock.name, [])
        if len(memory) < 2:
            return "hold"

        recent = list(memory)
        current_price = recent[-1]
        average_price = sum(recent) / len(recent)
        avg_buy = self.avg_buy_price.get(stock.name, average_price)
        prev_price = recent[-2]
        r = random.random()
        vol = self.volatility_factor(stock)
        volm = self.volume_factor(stock)

        uptrend = current_price > prev_price
        downtrend = current_price < prev_price
        far_above_avg = current_price > average_price * 1.1
        far_below_avg = current_price < average_price * 0.9

        if self.role == "trend":
            if uptrend and r < 0.7 * volm * (1 - vol):
                return "buy"
            elif downtrend and r < 0.3 * volm * (1 - vol):
                return "sell"
            elif far_above_avg and r < 0.2:
                return "sell"
            elif far_below_avg and r < 0.3:
                return "buy"
            else:
                return "hold"

        elif self.role == "swing":
            swing_range = average_price * 0.05
            if current_price < average_price - swing_range and r < 0.7 * vol * volm:
                return "buy"
            elif current_price > avg_buy * 1.15 and r < 0.6 * vol * volm:
                return "sell"

        elif self.role == "maker":
            return "make_market" if r < 0.85 else "hold"

        elif self.role == "whale":
            if downtrend and r < 0.6 * (1 - volm):
                return "buy"
            elif uptrend and r < 0.3 * volm:
                return "sell"
            elif current_price < avg_buy * 0.8 and vol > 0.05 and volm > 0.5:
                return "big_dump"

        elif self.role == "risky":
            panic_sell = current_price < average_price * 0.85 and r < 0.6 * vol
            fomo_buy = current_price > average_price * 1.1 and r < 0.6 * volm
            erratic = r < 0.15

            if panic_sell:
                print(f"{self.name} ({self.role}) is PANICKING and selling {stock.name}!")
                return "sell"
            elif fomo_buy:
                print(f"{self.name} ({self.role}) has FOMO and is buying {stock.name}!")
                return "buy"
            elif erratic:
                choice = random.choice(["buy", "sell", "hold"])
                print(f"{self.name} ({self.role}) is acting ERRATICALLY and randomly chose to {choice.upper()} {stock.name}")
                return choice

        return "hold"

    def volatility_factor(self, stock):
        prices = list(self.price_memory.get(stock.name, []))
        if len(prices) < 2:
            return 0
        return min(statistics.stdev(prices) / prices[-1], 0.1)

    def volume_factor(self, stock):
        recent_trades = self.trade_history[-20:]
        if not recent_trades:
            return 0.0
        avg_volume = sum(t["quantity"] for t in recent_trades) / len(recent_trades)
        base_volume = self.role_cap
        return min(avg_volume / base_volume, 1.0)

    def min_holdings_threshold(self, stock_name):
        return max(1, random.randint(1, 5))

    def buy_market(self, stock):
        sell_orders = self.ledger.order_book["sell"]
        if not sell_orders:
            print(f"{self.name} ({self.role}) couldn't buy because no sell orders are available.")
            return

        best_offer = sell_orders[0]
        base_cap = self.role_cap
        cap = int(base_cap * random.uniform(0.5, 1.5))
        quantity = min(cap, best_offer.quantity)

        if quantity <= 0:
            total_qty = sum(order.quantity for order in sell_orders)
            if total_qty <= 0:
                return
            quantity = random.randint(1, total_qty)

        price = round(best_offer.price, 4)
        cost = round(price * quantity, 4)

        if self.balance >= cost:
            self.order_util.add_order("buy", Order(self, quantity, price), self.name)
            self.record_trade("buy", stock, quantity, price)
            self.update_avg_buy(stock.name, price, quantity)

    def sell_market(self, stock):
        shares_owned = self.portfolio.get(stock.name, 0)
        min_threshold = self.min_holdings_threshold(stock.name)
        if shares_owned <= min_threshold:
            return

        buy_orders = self.ledger.order_book["buy"]
        if not buy_orders:
            return

        best_bid = buy_orders[0]
        base_cap = self.role_cap
        cap = int(base_cap * random.uniform(0.5, 1.5))
        max_quantity = min(cap, shares_owned - min_threshold, best_bid.quantity)

        if max_quantity <= 0:
            total_buy_qty = sum(order.quantity for order in buy_orders)
            fallback_qty = min(shares_owned - min_threshold, total_buy_qty)
            if fallback_qty <= 0:
                return
            quantity = random.randint(1, fallback_qty)
        else:
            quantity = random.randint(1, max_quantity)

        price = round(best_bid.price, 4)
        self.order_util.add_order("sell", Order(self, quantity, price), self.name)
        self.record_trade("sell", stock, quantity, price)

    def big_dump(self, stock):
        shares_owned = self.portfolio.get(stock.name, 0)
        if shares_owned <= 10:
            return
        buy_orders = self.ledger.order_book["buy"]
        if not buy_orders:
            return
        best_bid = buy_orders[0]
        quantity = int(shares_owned * random.uniform(0.7, 0.95))
        quantity = min(quantity, best_bid.quantity)
        if quantity <= 0:
            return
        price = round(best_bid.price * random.uniform(0.9, 1.0), 4)
        price = max(0.0001, price)
        self.order_util.add_order("sell", Order(self, quantity, price), self.name)
        self.record_trade("sell", stock, quantity, price)

    def make_market(self, stock):
        price = round(self.ledger.stocks[stock.name]["last_price"], 4)
        base_spread = 0.01
        spread_multiplier = 1 + self.volatility_factor(stock) * 5 + self.volume_factor(stock) * 2

        if random.random() < 0.1 + self.volatility_factor(stock) + self.volume_factor(stock) * 0.2:
            spread_multiplier *= random.uniform(1.5, 3.0)

        spread = round(min(price * base_spread * spread_multiplier, price * 0.1), 4)
        buy_price = round(max(0.0001, price - spread), 4)
        sell_price = round(min(100000, price + spread), 4)

        quantity = random.randint(5, 20)

        if self.balance >= buy_price * quantity:
            self.order_util.add_order("buy", Order(self, quantity, buy_price), self.name)

        owned = self.portfolio.get(stock.name, 0)
        min_threshold = self.min_holdings_threshold(stock.name)
        sell_quantity = min(quantity, owned - min_threshold) if owned > min_threshold else 0
        if sell_quantity > 0:
            self.order_util.add_order("sell", Order(self, sell_quantity, sell_price), self.name)

    def place_initial_sell_order(self, stock):
        shares_owned = self.portfolio.get(stock.name, 0)
        if shares_owned > 0:
            sell_price = self.ledger.stocks[stock.name]["last_price"] * 1.10
            quantity = min(shares_owned, 10)
            self.order_util.add_order("sell", Order(self, quantity, round(sell_price, 4)), self.name)

    def update_avg_buy(self, stock_name, price, quantity):
        current_avg = self.avg_buy_price.get(stock_name, 0)
        total_shares = self.portfolio.get(stock_name, 0)
        new_avg = ((current_avg * total_shares) + (price * quantity)) / (total_shares + quantity)
        self.avg_buy_price[stock_name] = new_avg

    def record_trade(self, action, stock, quantity, price):
        if action == "buy":
            self.stats["buys"] += quantity
            self.stats["buy_total"] += price * quantity
        elif action == "sell":
            self.stats["sells"] += quantity
            self.stats["sell_total"] += price * quantity
            avg_buy = self.avg_buy_price.get(stock.name, price)
            self.stats["profit"] += (price - avg_buy) * quantity
        trade_record = {
            "timestamp": time.time(),
            "stock": stock.name,
            "quantity": quantity,
            "price": round(price, 4),
            "action": action,
            "buyer": self.name if action == "buy" else "N/A",
            "seller": self.name if action == "sell" else "N/A"
        }
        self.trade_history.append(trade_record)

    def show_trade_history(self, limit=10):
        print(f"\n--- {self.name} Trade History (Last {limit}) ---")
        for trade in self.trade_history[-limit:]:
            t = time.strftime('%Y-%m-%d %H:%M:%S', time.localtime(trade["timestamp"]))
            print(f"[{t}] {trade['action']} {trade['quantity']:,} of {trade['stock']} @ ${trade['price']:,.4f}")

    def __str__(self):
        return f"{self.name} ({self.role}) | Balance: ${self.balance:,.4f} | Holdings: {self.portfolio}"

    def get_stats(self):
        avg_buy = self.stats["buy_total"] / self.stats["buys"] if self.stats["buys"] else 0
        avg_sell = self.stats["sell_total"] / self.stats["sells"] if self.stats["sells"] else 0
        return {
            "role": self.role,
            "buys": self.stats["buys"],
            "sells": self.stats["sells"],
            "avg_buy": avg_buy,
            "avg_sell": avg_sell,
            "profit": self.stats["profit"]
        }