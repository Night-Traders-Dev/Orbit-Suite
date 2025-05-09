'''
    Orbit Market
    main.py
'''
from Market import Market
from AdminPanel import AdminPanel
from Order import Order
from Stock import Stock
from AITrader import AITrader,AIinit
from InitToken import InitToken
from Ledger import Ledger



def main():
    print("Orbit Market")
    market = Market()
    ledger = Ledger(market)
    init_token = InitToken(market, ledger)
    init_token.create_init_token()
    ai_init = AIinit(market, ledger)
    ai_traders = ai_init.ai_traders
    admin = AdminPanel(market, ai_traders, ledger)
    for ai in ai_traders:
        market.add_player(ai)


    while True:
        print("\nMain Menu")
        print("1. Admin Panel")
        print("2. Exit")
        choice = input("Choice: ")

        if choice == "1":
            admin.menu()
        elif choice == "2":
            print("Exiting...")
            sys.exit()
        else:
            print("Invalid choice.")

if __name__ == "__main__":
    main()
