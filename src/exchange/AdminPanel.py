'''
    Orbit Market
    AdminPanel.py
'''
import matplotlib.pyplot as plt
import pandas as pd
import os

class AdminPanel:
    def __init__(self, market, ai_traders, ledger):
        self.market = market
        self.ai_traders = ai_traders
        self.ledger = ledger

    def menu(self):
        while True:
            print("\nAdmin Panel")
            print("1. Create Stock")
            print("2. Rename Stock")
            print("3. Delete Stock")
            print("4. Ledger")
            print("5. Portfolios and Balances")
            print("6. Simulate Ticks")
            print("7. Save Stock Price Chart")
            print("8. Save Market Chart")
            print("9. Exit Admin Panel")
            choice = input("Choice: ")

            if choice == "1":
                self.create_stock()
            elif choice == "2":
                self.rename_stock()
            elif choice == "3":
                self.delete_stock()
            elif choice == "4":
                self.view_ledger()
            elif choice == "5":
                self.view_players_portfolios()
            elif choice == "6":
                self.simulate_ticks()
            elif choice == "7":
                self.save_stock_chart()
            elif choice == "8":
                self.save_market_chart()
            elif choice == "9":
                break
            else:
                print("Invalid choice.")

    def create_stock(self):
        name = input("Stock name: ").upper()
        if name not in self.market.stocks:
            try:
                initial_price = float(input("Initial price: "))
                supply = int(input("Total supply: "))
                if initial_price <= 0 or supply <= 0:
                    print("Price and supply must be greater than zero.")
                    return
            except ValueError:
                print("Invalid input for price or supply. Please enter numerical values.")
                return
            self.market.stocks[name] = Stock(name, initial_price, supply)
            print(f"Created stock {name}")
        else:
            print("Stock already exists.")

    def rename_stock(self):
        old_name = input("Old stock name: ").upper()
        if old_name in self.market.stocks:
            new_name = input("New stock name: ").upper()
            if new_name not in self.market.stocks:
                self.market.stocks[new_name] = self.market.stocks.pop(old_name)
                self.market.stocks[new_name].name = new_name
                print(f"Renamed {old_name} to {new_name}")
            else:
                print(f"Error: Stock with the name {new_name} already exists.")
        else:
            print(f"Error: Stock with the name {old_name} not found.")

    def delete_stock(self):
        name = input("Stock to delete: ").upper()
        if name in self.market.stocks:
            stock = self.market.stocks[name]
            if not stock.order_book["buy"] and not stock.order_book["sell"]:
                del self.market.stocks[name]
                print(f"Deleted {name}")
            else:
                print(f"Error: Cannot delete stock {name} as there are active orders.")
        else:
            print("Stock not found.")

    def view_ledger(self):
        print("\n--- Market Ledger ---")
        for stock in self.market.stocks.values():
            print(f"\n{stock}")
            stock.show_trade_history()

    def view_players_portfolios(self):
        print("\n--- Players' Portfolios and Balances ---")
        for player in self.market.players:
            print(f"\n{player.name}'s Portfolio and Balance:")
            print(f"Balance: ${player.balance:,.4f}")
            for stock, quantity in player.portfolio.items():
                print(f"{stock}: {quantity:,} shares")

    def simulate_ticks(self):
        try:
            ticks = int(input("Enter number of ticks to simulate: "))
            for _ in range(ticks):
                for stock in self.market.stocks.values():
                    stock.tick()
                for ai in self.ai_traders:
                    ai.act(self.market)
            print(f"Simulated {ticks} tick(s).")
        except ValueError:
            print("Invalid number of ticks.")

    def save_stock_chart(self):
        name = input("Enter stock symbol to chart: ").upper()
        stock = self.market.stocks.get(name)

        if not stock:
            print("Stock not found.")
            return

        trades = stock.trade_history
        if not trades:
            print("No trades yet to chart.")
            return

        # Get volume summary
        volume_summary = stock.get_volume()
        print(
            f"Volume Summary for {name} — "
            f"Buy: {volume_summary['buy_volume']:,}, "
            f"Sell: {volume_summary['sell_volume']:,}, "
            f"Total: {volume_summary['total_volume']:,}"
        )

        # Create DataFrame from trade history
        df = pd.DataFrame(trades)
        df['timestamp'] = pd.to_datetime(df['timestamp'], unit='s')
        df.set_index('timestamp', inplace=True)

        df['price'] = df['price'].astype(float)
        df['volume'] = df['quantity'].astype(float)

        # Calculate RSI
        delta = df['price'].diff()
        gain = delta.clip(lower=0).rolling(window=14).mean()
        loss = -delta.clip(upper=0).rolling(window=14).mean()
        rs = gain / (loss + 1e-6)
        df['RSI'] = 100 - (100 / (1 + rs))

        df['MA7'] = df['price'].rolling(window=7).mean()

        # Plotting
        plt.figure(figsize=(12, 10))

        # Price chart
        plt.subplot(3, 1, 1)
        plt.plot(df.index, df['price'], label='Price', color='blue')
        plt.plot(df.index, df['MA7'], label='MA (7)', color='orange', linestyle='--')
        plt.title(f"{name} Price")
        plt.ylabel("Price")
        plt.legend()

        # Volume chart
        plt.subplot(3, 1, 2)
        plt.bar(df.index, df['volume'], label='Volume', color='gray')
        plt.title("Trade Volume")
        plt.ylabel("Volume")
        plt.ylim(0, df['volume'].max() * 1.1)
        plt.legend()

        # RSI chart
        plt.subplot(3, 1, 3)
        plt.plot(df.index, df['RSI'], label='RSI', color='purple')
        plt.axhline(70, color='red', linestyle='--', label='Overbought (70)')
        plt.axhline(30, color='green', linestyle='--', label='Oversold (30)')
        plt.title("Relative Strength Index (RSI)")
        plt.ylabel("RSI")
        plt.xlabel("Time")
        plt.legend()

        # Save chart
        os.makedirs("charts", exist_ok=True)
        filename = f"charts/{name}_chart.png"
        plt.tight_layout()
        plt.savefig(filename)
        plt.close()

        print(f"Chart saved to {filename}")

    def save_market_chart(self):
        all_trades = []

        for stock in self.market.stocks.values():
            for trade in self.ledger.trade_history:
                trade_entry = trade.copy()
                trade_entry['symbol'] = stock.name
                all_trades.append(trade_entry)

        if not all_trades:
            print("No trades available to chart.")
            return

        df = pd.DataFrame(all_trades)
        df['timestamp'] = pd.to_datetime(df['timestamp'], unit='s')
        df.set_index('timestamp', inplace=True)

        df['price'] = df['price'].astype(float)
        df['volume'] = df['quantity'].astype(float)

        # Market index as sum of prices per timestamp
        df_grouped = df.groupby(['timestamp', 'symbol'])['price'].mean().unstack()
        df_grouped['market_index'] = df_grouped.sum(axis=1)

        # RSI for market index
        delta = df_grouped['market_index'].diff()
        gain = delta.clip(lower=0).rolling(window=14).mean()
        loss = -delta.clip(upper=0).rolling(window=14).mean()
        rs = gain / (loss + 1e-6)
        df_grouped['RSI'] = 100 - (100 / (1 + rs))

        df_grouped['MA7'] = df_grouped['market_index'].rolling(window=7).mean()

        # Total volume per timestamp
        df_volume = df.groupby('timestamp')['volume'].sum()

        # Overall market volume summary
        total_buy = 0
        total_sell = 0
        for stock in self.market.stocks.values():
            v = stock.get_volume()
            total_buy += v['buy_volume']
            total_sell += v['sell_volume']
        total_volume = total_buy + total_sell

        print(
            f"Market Volume Summary — "
            f"Buy: {total_buy:,}, Sell: {total_sell:,}, Total: {total_volume:,}"
        )

        # Plotting
        plt.figure(figsize=(12, 10))

        # Market index chart
        plt.subplot(3, 1, 1)
        plt.plot(df_grouped.index, df_grouped['market_index'], label='Market Index', color='blue')
        plt.plot(df_grouped.index, df_grouped['MA7'], label='MA (7)', color='orange', linestyle='--')
        plt.title("Market Index Price")
        plt.ylabel("Price")
        plt.legend()

        # Volume chart
        plt.subplot(3, 1, 2)
        plt.bar(df_volume.index, df_volume.values, label='Total Volume', color='gray')
        plt.title("Total Market Trade Volume")
        plt.ylabel("Volume")
        max_volume = df_volume.max()
        plt.ylim(0, max_volume * 1.1 if max_volume > 0 else 1)
        plt.grid(True, axis='y', linestyle='--', alpha=0.5)
        plt.legend()

        # RSI chart
        plt.subplot(3, 1, 3)
        plt.plot(df_grouped.index, df_grouped['RSI'], label='RSI', color='purple')
        plt.axhline(70, color='red', linestyle='--', label='Overbought (70)')
        plt.axhline(30, color='green', linestyle='--', label='Oversold (30)')
        plt.title("Market Index RSI")
        plt.ylabel("RSI")
        plt.xlabel("Time")
        plt.legend()

        os.makedirs("charts", exist_ok=True)
        filename = "charts/market_index_chart.png"
        plt.tight_layout()
        plt.savefig(filename)
        plt.close()

        print(f"Market index chart saved to {filename}")
