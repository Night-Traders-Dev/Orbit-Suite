# cli_exchange.py

import sys
import core.exchangeutil as exchange
from core.walletutil import load_balance


def main_menu():
    print("\n--- Orbit CLI Exchange ---")
    print("1. View Balance")
    print("2. Place Buy Order")
    print("3. Place Sell Order")
    print("4. View My Orders")
    print("5. Cancel Order")
    print("6. View Order Book")
    print("7. View Trade History")
    print("8. Exit")

def prompt_amount_price():
    try:
        amount = float(input("Amount (Orbit): "))
        price = float(input("Price (per Orbit): "))
        return amount, price
    except ValueError:
        print("Invalid input.")
        return None, None

def cli():
    address = input("Enter your wallet address: ").strip()
    wallet, active_locked = load_balance(address)
    if not wallet:
        print("Wallet not found.")
        return

    print(f"Welcome, {address}!")

    while True:
        main_menu()
        choice = input("Select option: ").strip()

        if choice == "1":
            balance = wallet
            print(f"Balance: {balance:.2f} Orbit")

        elif choice == "2":
            amount, price = prompt_amount_price()
            if amount and price:
                success = exchange.place_order(address, "buy", amount, price, wallet)
                print("Buy order placed." if success else "Failed to place buy order.")

        elif choice == "3":
            amount, price = prompt_amount_price()
            if amount and price:
                success = exchange.place_order(address, "sell", amount, price, wallet)
                print("Sell order placed." if success else "Failed to place sell order.")

        elif choice == "4":
            orders = exchange.get_orders_by_address(address)
            if not orders:
                print("No active orders.")
            for o in orders:
                print(f"Order #{o['id']}: {o['type'].upper()} {o['amount']} @ {o['price']}")

        elif choice == "5":
            order_id = input("Enter order ID to cancel: ").strip()
            success = exchange.cancel_order(address, order_id)
            print("Order cancelled." if success else "Failed to cancel order.")

        elif choice == "6":
            buys, sells = exchange.get_order_book()
            print("\nBuy Orders:")
            for b in buys:
                print(f"{b['amount']} Orbit @ {b['price']} by {b['user']}")
            print("\nSell Orders:")
            for s in sells:
                print(f"{s['amount']} Orbit @ {s['price']} by {s['user']}")

        elif choice == "7":
            history = exchange.get_trade_history()
            if not history:
                print("No trades yet.")
            for t in history:
                print(f"Trade: {t['amount']} Orbit @ {t['price']} between {t['buy_address']} and {t['sell_address']}")

        elif choice == "8":
            print("Exiting.")
            break
        else:
            print("Invalid option.")

if __name__ == "__main__":
    cli()
