from userutil import (
    view_security_circle, add_to_security_circle, remove_from_security_circle,
    view_lockups, lock_tokens, login, register, claim_lockup_rewards
)
from miningutil import simulate_mining
from tokenutil import send_orbit
from ledgerutil import (
    view_all_transactions, view_user_transactions,
    view_mining_rewards, view_transfers
)
from termutil import clear_screen
from walletutil import show_balance
from orbitutil import load_nodes, save_nodes, register_node
import sys

def pre_login_menu():
    clear_screen()
    while True:
        print("\n=== Orbit Terminal ===")
        print("1. Login")
        print("2. Register")
        print("3. Exit")
        choice = input("Choose an option: ").strip()
        clear_screen()
        if choice == "1":
            user = login()
            if user:
                post_login_menu(user)
        elif choice == "2":
            register()
        elif choice == "3":
            print("Goodbye!")
            break
        else:
            print("Invalid option. Try again.")

def quorum_slice_menu(user):
    clear_screen()
    while True:
        print("\n=== Node Manager Menu ===")
        print("1. View All Nodes")
        print("2. Register This Node")
        print("3. Edit Quorum Slice")
        print("4. Back")
        choice = input("Choose an option: ").strip()
        clear_screen()
        if choice == "1":
            nodes = load_nodes()
            if not nodes:
                print("No nodes registered.")
            else:
                print("Registered Nodes:")
                for nid, node in nodes.items():
                    print(f"- {nid} (Quorum Slice: {node.get('quorum_slice', [])})")

        elif choice == "2":
            node_id = input("Enter node ID to register (e.g., Node3): ").strip()
            if node_id:
                nodes = load_nodes()
                quorum_slice = nodes[node_id]["quorum_slice"]
                register_node(node_id, quorum_slice)
                print(f"Node {node_id} registered.")
            else:
                print("Node ID cannot be empty.")

        elif choice == "3":
            node_id = input("Enter your node ID: ").strip()
            nodes = load_nodes()
            if node_id not in nodes:
                print("Node not found.")
                continue

            print("Enter comma-separated IDs of trusted nodes (quorum slice):")
            quorum_input = input("e.g., Node1,Node2: ").strip()
            quorum_slice = [q.strip() for q in quorum_input.split(",") if q.strip()]
            nodes[node_id]["quorum_slice"] = quorum_slice
            save_nodes()
            print(f"Quorum slice for {node_id} updated.")

        elif choice == "4":
            break
        else:
            print("Invalid option. Try again.")

def lockup_menu(user):
    clear_screen()
    while True:
        print("\n=== Lockups Menu ===")
        print("1. Lock Orbit")
        print("2. View Lockups")
        print("3. Claim")
        print("4. Back")
        choice = input("Choose an option: ").strip()
        clear_screen()
        if choice == "1":
            lock_tokens(user)
        elif choice == "2":
            view_lockups(user)
        elif choice == "3":
            claim_lockup_rewards(user)
        elif choice == "4":
            break
        else:
            print("Invalid option. Try again.")

def wallet_menu(user):
    clear_screen()
    while True:
        print("\n=== Wallet Menu ===")
        print("1. Show Balance")
        print("2. Send Orbit")
        print("3. Staking")
        print("4. Back")
        choice = input("Choose an option: ").strip()
        clear_screen()

        if choice == "1":
            show_balance(user)
        elif choice == "2":
            send_orbit(user)
        elif choice == "3":
            lockup_menu(user)
        elif choice == "4":
            break
        else:
            print("Invalid option. Try again.")

def security_circle_menu(user):
    clear_screen()
    while True:
        print("\n=== Security Circle Menu ===")
        print("1. View Security Circle")
        print("2. Add to Security Circle")
        print("3. Remove from Security Circle")
        print("4. Back")
        choice = input("Choose an option: ").strip()
        clear_screen()

        if choice == "1":
            view_security_circle(user)
        elif choice == "2":
            add_to_security_circle(user)
        elif choice == "3":
            remove_from_security_circle(user)
        elif choice == "4":
            break
        else:
            print("Invalid option. Try again.")


def ledger_menu(user):
    clear_screen()
    while True:
        print("\n=== Ledger Menu ===")
        print("1. View All Transactions")
        print("2. View My Transactions")
        print("3. View My Mining Rewards")
        print("4. View My Transfers")
        print("5. Back")
        choice = input("Choose an option: ").strip()
        clear_screen()

        if choice == "1":
            view_all_transactions()
        elif choice == "2":
            view_user_transactions(user)
        elif choice == "3":
            view_mining_rewards(user)
        elif choice == "4":
            view_transfers(user)
        elif choice == "5":
            break
        else:
            print("Invalid option. Try again.")

def post_login_menu(user):
    clear_screen()
    while True:
        print(f"\n=== Welcome to Orbit, {user} ===")
        print("1. Mine Orbit")
        print("2. Wallet")
        print("3. Security Circle")
        print("4. Ledger")
        print("5. Node Management")
        print("6. Logout")

        choice = input("Choose an option: ").strip()
        clear_screen()

        if choice == "1":
            simulate_mining(user, duration=10)
        elif choice == "2":
            wallet_menu(user)
        elif choice == "3":
            security_circle_menu(user)
        elif choice == "4":
            ledger_menu(user)
        elif choice == "5":
            quorum_slice_menu(user)
        elif choice == "6":
            print("Logged out.")
            sys.exit()
        else:
            print("Invalid option. Try again.")

if __name__ == "__main__":
    clear_screen()
    pre_login_menu()
