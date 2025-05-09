# Orbit Market - AITrader.py

import random
import statistics
from collections import deque
import time
from Order import Order, OrderUtil

class AIinit:
    def __init__(self, market, ledger):
        self.market = market
        self.ai_traders = []
        self.trader_specs = [
            ("MM", "maker", 15, (5_000, 10_000)),
            ("Trend", "trend", 30, (7_500, 15_000)),
            ("Swing", "swing", 40, (10_000, 20_000)),
            ("Whale", "whale", 10, (50_000, 100_000)),
            ("Trader", "risky", 80, (2_000, 7_500)),
        ]
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
    def __init__(self, name, role, balance, market, ledger):
        self.name = name
        self.role = role
        self.balance = balance
        self.ledger = ledger
        self.order_util = OrderUtil(self.ledger)
        self.portfolio = {}
        self.price_memory = {}
        self.avg_buy_price = {}
        self.trade_history = self.ledger.trade_history
        self.stats = {"buys": 0, "sells": 0, "buy_total": 0.0, "sell_total": 0.0, "profit": 0.0}

        self.role_cap = random.randint(20, 300) if role == "risky" else {
            "maker": 20, "trend": 30, "swing": 40, "whale": 100
        }.get(role, 25)

    def act(self, market):
        for stock in market.stocks.values():
            self.update_memory(stock)
            decision = self.analyze(stock)

            book = self.ledger.order_book[stock.name]
            if self.role == "swing" and not book["buy"]:
                print(f"{self.name} ({self.role}) sees an opportunity to BUY {stock.name} as no buy orders exist.")
                self.buy_market(stock)
                self.place_initial_sell_order(stock)

            if decision == "buy" and book["sell"]:
                best_offer = book["sell"][0]
                print(f"{self.name} ({self.role}) decided to BUY {min(best_offer.quantity, 25)} of {stock.name} @ ${best_offer.price:.4f}")
            elif decision == "sell" and book["buy"]:
                best_bid = book["buy"][0]
                print(f"{self.name} ({self.role}) decided to SELL {min(best_bid.quantity, self.portfolio.get(stock.name, 0))} of {stock.name} @ ${best_bid.price:.4f}")
            else:
                print(f"{self.name} ({self.role}) decided to {decision.upper()} on {stock.name}")

            getattr(self, f"{decision}_market", lambda s: None)(stock) if decision in {"buy", "sell"} else \
                getattr(self, decision, lambda s: None)(stock) if hasattr(self, decision) else None

    def update_memory(self, stock):
        mem = self.price_memory.setdefault(stock.name, deque(maxlen=10))
        mem.append(self.ledger.stocks[stock.name]["last_price"])

    def analyze(self, stock):
        memory = list(self.price_memory.get(stock.name, []))
        if len(memory) < 2:
            return "hold"

        current_price, prev_price = memory[-1], memory[-2]
        avg_price = sum(memory) / len(memory)
        avg_buy = self.avg_buy_price.get(stock.name, avg_price)
        vol, volm, r = self.volatility_factor(stock), self.volume_factor(stock), random.random()

        if self.role == "trend":
            if current_price > prev_price and r < 0.7 * volm * (1 - vol): return "buy"
            if current_price < prev_price and r < 0.3 * volm * (1 - vol): return "sell"
            if current_price > avg_price * 1.1 and r < 0.2: return "sell"
            if current_price < avg_price * 0.9 and r < 0.3: return "buy"

        elif self.role == "swing":
            swing_range = avg_price * 0.05
            if current_price < avg_price - swing_range and r < 0.7 * vol * volm: return "buy"
            if current_price > avg_buy * 1.15 and r < 0.6 * vol * volm: return "sell"

        elif self.role == "maker":
            return "make_market" if r < 0.85 else "hold"

        elif self.role == "whale":
            if current_price < prev_price and r < 0.6 * (1 - volm): return "buy"
            if current_price > prev_price and r < 0.3 * volm: return "sell"
            if current_price < avg_buy * 0.8 and vol > 0.05 and volm > 0.5: return "big_dump"

        elif self.role == "risky":
            if current_price < avg_price * 0.85 and r < 0.6 * vol:
                print(f"{self.name} is PANICKING and selling {stock.name}!")
                return "sell"
            if current_price > avg_price * 1.1 and r < 0.6 * volm:
                print(f"{self.name} has FOMO and is buying {stock.name}!")
                return "buy"
            if r < 0.15:
                action = random.choice(["buy", "sell", "hold"])
                print(f"{self.name} acts ERRATICALLY and chose to {action.upper()} {stock.name}")
                return action

        return "hold"

    def volatility_factor(self, stock):
        prices = list(self.price_memory.get(stock.name, []))
        return min(statistics.stdev(prices) / prices[-1], 0.1) if len(prices) >= 2 else 0

    def volume_factor(self, stock):
        trades = self.trade_history[-20:]
        if not trades: return 0.0
        avg_volume = sum(t["quantity"] for t in trades if t["stock"] == stock.name) / len(trades)
        return min(avg_volume / self.role_cap, 1.0)

    def buy_market(self, stock):
        sell_orders = self.ledger.order_book[stock.name]["sell"]
        if not sell_orders: return

        best_offer = sell_orders[0]
        cap = int(self.role_cap * random.uniform(0.5, 1.5))
        quantity = min(cap, best_offer.quantity)
        if quantity <= 0: return

        price = round(best_offer.price, 4)
        cost = round(price * quantity, 4)

        if self.balance >= cost:
            self.order_util.add_order(stock.name, "buy", Order(self, quantity, price), self.name)
            self.record_trade("buy", stock, quantity, price)
            self.update_avg_buy(stock.name, price, quantity)

    def sell_market(self, stock):
        shares = self.portfolio.get(stock.name, 0)
        if shares <= self.min_holdings_threshold(stock.name): return

        buy_orders = self.ledger.order_book[stock.name]["buy"]
        if not buy_orders: return

        best_bid = buy_orders[0]
        cap = int(self.role_cap * random.uniform(0.5, 1.5))
        max_q = min(cap, shares - self.min_holdings_threshold(stock.name), best_bid.quantity)
        quantity = random.randint(1, max_q) if max_q > 0 else 0
        if quantity <= 0: return

        price = round(best_bid.price, 4)
        self.order_util.add_order("sell", Order(self, quantity, price), self.name)
        self.record_trade("sell", stock, quantity, price)

    def big_dump(self, stock):
        shares = self.portfolio.get(stock.name, 0)
        if shares <= 10: return
        buy_orders = self.ledger.order_book[stock.name]["buy"]
        if not buy_orders: return

        best_bid = buy_orders[0]
        quantity = min(int(shares * random.uniform(0.7, 0.95)), best_bid.quantity)
        if quantity <= 0: return

        price = round(max(0.0001, best_bid.price * random.uniform(0.9, 1.0)), 4)
        self.order_util.add_order("sell", Order(self, quantity, price), self.name)
        self.record_trade("sell", stock, quantity, price)

    def make_market(self, stock):
        price = round(self.ledger.stocks[stock.name]["last_price"], 4)
        spread = min(price * 0.01 * (1 + self.volatility_factor(stock) * 5 + self.volume_factor(stock) * 2), price * 0.1)
        buy_price = round(max(0.0001, price - spread), 4)
        sell_price = round(price + spread, 4)
        quantity = random.randint(5, 20)

        if self.balance >= buy_price * quantity:
            self.order_util.add_order("buy", Order(self, quantity, buy_price), self.name)

        shares = self.portfolio.get(stock.name, 0)
        if shares > self.min_holdings_threshold(stock.name):
            sell_q = min(quantity, shares - self.min_holdings_threshold(stock.name))
            self.order_util.add_order("sell", Order(self, sell_q, sell_price), self.name)

    def place_initial_sell_order(self, stock):
        shares = self.portfolio.get(stock.name, 0)
        if shares > 0:
            price = round(self.ledger.stocks[stock.name]["last_price"] * 1.10, 4)
            self.order_util.add_order(stock.name, "sell", Order(self, min(shares, 10), price), self.name)

    def update_avg_buy(self, stock_name, price, quantity):
        total_shares = self.portfolio.get(stock_name, 0)
        current_avg = self.avg_buy_price.get(stock_name, 0)
        new_avg = ((current_avg * total_shares) + (price * quantity)) / (total_shares + quantity)
        self.avg_buy_price[stock_name] = new_avg

    def min_holdings_threshold(self, stock_name):
        return max(1, random.randint(1, 5))

    def record_trade(self, action, stock, quantity, price):
        if action == "buy":
            self.stats["buys"] += quantity
            self.stats["buy_total"] += price * quantity
        elif action == "sell":
            self.stats["sells"] += quantity
            self.stats["sell_total"] += price * quantity
            avg = self.avg_buy_price.get(stock.name, price)
            self.stats["profit"] += (price - avg) * quantity

        self.trade_history.append({
            "timestamp": time.time(),
            "stock": stock.name,
            "quantity": quantity,
            "price": round(price, 4),
            "action": action,
            "buyer": self.name if action == "buy" else "N/A",
            "seller": self.name if action == "sell" else "N/A"
        })

    def __str__(self):
        return f"{self.name} ({self.role}) | Balance: ${self.balance:,.4f} | Holdings: {self.portfolio}"

    def get_stats(self):
        buys, sells = self.stats["buys"], self.stats["sells"]
        return {
            "role": self.role,
            "buys": buys,
            "sells": sells,
            "avg_buy": self.stats["buy_total"] / buys if buys else 0,
            "avg_sell": self.stats["sell_total"] / sells if sells else 0,
            "profit": self.stats["profit"]
        }