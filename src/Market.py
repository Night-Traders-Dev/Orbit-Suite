'''
    Orbit Market
    Market.py
'''
from Stock import Stock

class Market:
    def __init__(self):
        self.stocks = {}
        self.players = []

    def display_market(self):
        print("\n--- Market ---")
        for stock in self.stocks.values():
            print(stock)

    def add_player(self, player):
        if player not in self.players:
            self.players.append(player)

    def get_stock(self, name):
        return self.stocks.get(name)

    def list_stocks(self):
        return list(self.stocks.keys())
