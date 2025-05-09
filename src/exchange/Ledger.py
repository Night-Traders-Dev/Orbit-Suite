'''
    Orbit Market
    Ledger.py
'''

class Ledger:
    def __init__(self, market):
        self.market = market
        self.trade_history = []
        self.last_price = 0
        self.order_book = {"buy": [], "sell": []}
