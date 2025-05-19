from blockchain.orbitutil import load_nodes, save_nodes, register_node
from blockchain.blockutil import start_listener
from blockchain.stakeutil import view_lockups, lock_tokens, claim_lockup_rewards
from blockchain.miningutil import simulate_mining
from blockchain.tokenutil import send_orbit
from blockchain.ledgerutil import (
    view_all_transactions, view_user_transactions,
    view_mining_rewards, view_transfers
)
from core.circleutil import view_security_circle, add_to_security_circle, remove_from_security_circle
from core.termutil import clear_screen
from core.walletutil import load_balance
from core.userutil import login, logout, register
import sys
import threading
from colorama import Fore, Style, init

init(autoreset=True)

HEADER = f"{Fore.CYAN + Style.BRIGHT}=== Orbit Terminal ==="
PROMPT = f"{Fore.YELLOW}> {Style.RESET_ALL}"


def pre_login_menu():
    clear_screen()
    while True:
        print(f"\n{HEADER}")
        print("1. Login")
        print("2. Register")
        print("3. Exit")
        choice = input(PROMPT).strip()
        clear_screen()
        if choice == "1":
            result = login()
            if result:
                user, node_id = result
                threading.Thread(target=start_listener, args=(node_id,), daemon=True).start()
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
        print(f"\n{Fore.MAGENTA}=== Node Manager Menu ===")
        print("1. View All Nodes")
        print("2. Register This Node")
        print("3. Edit Quorum Slice")
        print("4. Back")
        choice = input(PROMPT).strip()
        clear_screen()
        if choice == "1":
            nodes = load_nodes()
            print("Registered Nodes:")
            for nid, node in nodes.items():
                quorum = node.get("quorum_slice", [])
                trust = round(node.get("trust_score", 0.0), 2)
                uptime = round(node.get("uptime_score", 0.0), 2)
                print(f"- {nid} | Trust: {trust} | Uptime: {uptime} | Quorum: {quorum}")
        elif choice == "2":
            node_id = input("Enter node ID: ").strip()
            quorum_slice = input("Comma-separated quorum nodes: ").split(',')
            quorum = [q.strip() for q in quorum_slice if q.strip()]
            register_node(node_id, quorum)
            print(f"Node {node_id} registered.")
        elif choice == "3":
            node_id = input("Node ID: ").strip()
            nodes = load_nodes()
            if node_id in nodes:
                quorum_slice = input("New quorum (comma-separated): ").split(',')
                nodes[node_id]["quorum_slice"] = [q.strip() for q in quorum_slice if q.strip()]
                save_nodes(nodes)
                print("Quorum updated.")
            else:
                print("Node not found.")
        elif choice == "4":
            break


def lockup_menu(user):
    clear_screen()
    while True:
        print(f"\n{Fore.BLUE}=== Lockups Menu ===")
        print("1. Lock Orbit")
        print("2. View Lockups")
        print("3. Claim")
        print("4. Back")
        choice = input(PROMPT).strip()
        clear_screen()
        if choice == "1":
            lock_tokens(user)
        elif choice == "2":
            view_lockups(user)
        elif choice == "3":
            claim_lockup_rewards(user)
        elif choice == "4":
            break


def wallet_menu(user):
    clear_screen()
    while True:
        print(f"\n{Fore.GREEN}=== Wallet Menu ===")
        print("1. Show Balance")
        print("2. Send Orbit")
        print("3. Staking")
        print("4. Back")
        choice = input(PROMPT).strip()
        clear_screen()
        if choice == "1":
            available, locked = load_balance(user)
            total = available + locked
            print(f"Total: {total:.4f} | Locked: {locked:.4f} | Available: {available:.4f}")
        elif choice == "2":
            recipient = input("Recipient: ").strip()
            amount = float(input("Amount: ").strip())
            send_orbit(user, recipient, round(amount, 4))
        elif choice == "3":
            lockup_menu(user)
        elif choice == "4":
            break


def security_circle_menu(user):
    clear_screen()
    while True:
        print(f"\n{Fore.YELLOW}=== Security Circle Menu ===")
        print("1. View")
        print("2. Add")
        print("3. Remove")
        print("4. Back")
        choice = input(PROMPT).strip()
        clear_screen()
        if choice == "1":
            view_security_circle(user)
        elif choice == "2":
            add_to_security_circle(user)
        elif choice == "3":
            remove_from_security_circle(user)
        elif choice == "4":
            break


def ledger_menu(user):
    clear_screen()
    while True:
        print(f"\n{Fore.CYAN}=== Ledger Menu ===")
        print("1. All Transactions")
        print("2. My Transactions")
        print("3. Mining Rewards")
        print("4. Transfers")
        print("5. Back")
        choice = input(PROMPT).strip()
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


def post_login_menu(user):
    clear_screen()
    while True:
        print(f"\n{Fore.LIGHTCYAN_EX}=== Welcome to Orbit, {user} ===")
        print("1. Mine Orbit")
        print("2. Wallet")
        print("3. Security Circle")
        print("4. Ledger")
        print("5. Node Management")
        print("6. Logout")
        choice = input(PROMPT).strip()
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
            logout(user)
            print("Logged out.")
            sys.exit()


if __name__ == "__main__":
    clear_screen()
    pre_login_menu()
