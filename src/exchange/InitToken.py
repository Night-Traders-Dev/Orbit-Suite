'''
    Orbit Market
    InitToken.py
'''
from Stock import Stock

class InitToken:
    def __init__(self, market, ledger):
        self.market = market
        self.ledger = ledger
        self.init_token = []

        self.init_token.extend([
            {"name": "Orbit", "initial_price": 0.0021, "supply": 100_000_000_000},
#            {"name": "Sheep", "initial_price": 0.045, "supply": 50_000_000_000},
#            {"name": "Nova", "initial_price": 0.0083, "supply": 75_000_000_000},
#            {"name": "Zenith", "initial_price": 0.031, "supply": 20_000_000_000},
#            {"name": "Flare", "initial_price": 0.0155, "supply": 60_000_000_000},
#            {"name": "Terra", "initial_price": 0.0042, "supply": 90_000_000_000},
#            {"name": "Pulse", "initial_price": 0.012, "supply": 30_000_000_000},
#            {"name": "Echo", "initial_price": 0.0019, "supply": 120_000_000_000},
#            {"name": "Neon", "initial_price": 0.022, "supply": 40_000_000_000},
#            {"name": "Void", "initial_price": 0.0007, "supply": 150_000_000_000}
        ])

    def create_init_token(self):
        for token in self.init_token:
            name = token['name']
            initial_price = token['initial_price']
            supply = token['supply']
            self.market.stocks[name.upper()] = Stock(name, initial_price, supply, self.ledger)
            self.ledger.initialize_stock(name, initial_price, supply)
          
