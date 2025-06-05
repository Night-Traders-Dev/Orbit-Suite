
import json
import time
import requests
from web3 import Web3
from eth_account import Account
from eth_account.messages import encode_defunct

# ------------------------
# CONFIGURATION
# ------------------------
ORBIT_BRIDGE_ADDRESS = ""
POLYGON_RPC = ""
PRIVATE_KEY = ""
WRAPPED_ORBIT_CONTRACT = ""
BRIDGE_GAS_LIMIT = 150000
BRIDGE_GAS_PRICE_GWEI = 50

ORBIT_LEDGER_PATH = fetch_chain
PROCESSED_TX_PATH = fetch_processed

with open("wrapped_orbit_abi.json") as f:
    WRAPPED_ORBIT_ABI = json.load(f)

# ------------------------
# HELPERS
# ------------------------

def load_orbit_ledger():
    with open(ORBIT_LEDGER_PATH, "r") as f:
        return json.load(f)

def load_processed():
    try:
        with open(PROCESSED_TX_PATH, "r") as f:
            return set(json.load(f))
    except:
        return set()

def save_processed(tx_ids):
    with open(PROCESSED_TX_PATH, "w") as f:
        json.dump(list(tx_ids), f)

def connect_polygon():
    w3 = Web3(Web3.HTTPProvider(POLYGON_RPC))
    acct = Account.from_key(PRIVATE_KEY)
    contract = w3.eth.contract(address=WRAPPED_ORBIT_CONTRACT, abi=WRAPPED_ORBIT_ABI)
    return w3, acct, contract

# ------------------------
# ORBIT -> POLYGON (Mint)
# ------------------------

def handle_orbit_deposits():
    chain = load_orbit_ledger()
    processed = load_processed()
    w3, acct, contract = connect_polygon()

    for block in chain:
        for tx in block.get("transactions", []):
            if tx["receiver"] != ORBIT_BRIDGE_ADDRESS:
                continue
            if tx["id"] in processed:
                continue

            amount = tx.get("amount")
            note = tx.get("note")
            if not isinstance(note, dict):
                continue

            target = note.get("bridge_to")
            if not Web3.is_address(target):
                print(f"Invalid Ethereum address: {target}")
                continue

            # Mint wORBIT
            nonce = w3.eth.get_transaction_count(acct.address)
            tx_data = contract.functions.mint(target, int(amount * 1e18)).build_transaction({
                'chainId': 80001,
                'gas': BRIDGE_GAS_LIMIT,
                'gasPrice': w3.to_wei(BRIDGE_GAS_PRICE_GWEI, 'gwei'),
                'nonce': nonce
            })

            signed = w3.eth.account.sign_transaction(tx_data, private_key=PRIVATE_KEY)
            tx_hash = w3.eth.send_raw_transaction(signed.rawTransaction)
            print(f"Minted {amount} wORBIT to {target}, tx: {tx_hash.hex()}")
            processed.add(tx["id"])

    save_processed(processed)

# ------------------------
# POLYGON -> ORBIT (Burn)
# ------------------------

def handle_polygon_burns():
    w3, acct, contract = connect_polygon()
    latest_block = w3.eth.block_number
    processed = load_processed()

    burn_events = contract.events.Transfer().create_filter(
        fromBlock=latest_block - 5000,
        toBlock='latest',
        argument_filters={'to': '0x0000000000000000000000000000000000000000'}
    ).get_all_entries()

    for event in burn_events:
        tx_hash = event["transactionHash"].hex()
        if tx_hash in processed:
            continue

        from_address = event["args"]["from"]
        amount = event["args"]["value"] / 1e18
        print(f"Burn event: {amount} wORBIT from {from_address}")

        # Submit Orbit transaction
        payload = {
            "sender": "orbit_bridge_wallet_address_here",
            "receiver": from_address,
            "amount": amount,
            "note": {
                "bridge_from": from_address,
                "type": "bridge_withdraw"
            }
        }

        try:
            r = requests.post("http://localhost:8000/send_orbit", json=payload)
            if r.status_code == 200:
                print("Bridge withdrawal successful")
                processed.add(tx_hash)
            else:
                print(f"Failed to submit Orbit TX: {r.text}")
        except Exception as e:
            print(f"Error posting to Orbit API: {e}")

    save_processed(processed)

# ------------------------
# MAIN LOOP
# ------------------------

def run_bridge():
    print("🔗 Orbit ↔ Polygon Bridge running...")
    while True:
        handle_orbit_deposits()
        handle_polygon_burns()
        time.sleep(10)

if __name__ == "__main__":
    run_bridge()
