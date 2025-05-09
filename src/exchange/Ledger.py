'''
    Orbit Market
    Ledger.py
'''

class Ledger:
    def __init__(self, market):
        self.market = market
        self.trade_history = []  # Global list of all trades
        self.order_book = {
            "buy": [],   # List of buy orders across all stocks
            "sell": []   # List of sell orders across all stocks
        }
        self.stocks = {}  # Format: { "Orbit": { "last_price": float, "supply": int } }

    def initialize_stock(self, stock_name, initial_price, supply):
        self.stocks[stock_name] = {
            "last_price": initial_price,
            "supply": supply
        }

    def update_price(self, stock_name, price):
        if stock_name in self.stocks:
            self.stocks[stock_name]["last_price"] = price

    def record_trade(self, stock_name, price, quantity, action, buyer, seller):
        trade = {
            "timestamp": time.time(),
            "stock": stock_name,
            "price": round(price, 4),
            "quantity": quantity,
            "action": action,
            "buyer": buyer,
            "seller": seller
        }
        self.trade_history.append(trade)
        self.update_price(stock_name, price)

    def get_recent_trades(self, stock_name, limit=20):
        return [t for t in self.trade_history if t["stock"] == stock_name][-limit:]