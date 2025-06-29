import time, math
from core.tx_util.tx_types import TXTypes, TXExchange
from core.ioutil import load_users, save_users, fetch_chain, get_address_from_label
from core.walletutil import load_balance
from config.configutil import MiningConfig
from blockchain.tokenutil import send_orbit

# Load configuration
mining_address = get_address_from_label("mining")
mining_config = MiningConfig()
MODE = "mainnet"

# Updated total supply to match genesis allocation (100B)
TOTAL_MINING_SUPPLY = 1_000_000_000

def get_chain_summary():
    chain = fetch_chain()
    tx_count = sum(len(b.get("transactions", [])) for b in chain)
    account_set = set()
    circulating = 0.0

    for b in chain:
        for tx in b.get("transactions", []):
            account_set.add(tx["sender"])
            account_set.add(tx["recipient"])
            circulating += tx["amount"]

    return {
        "blocks": len(chain),
        "transactions": tx_count,
        "accounts": len(account_set),
        "circulating": circulating
    }

def get_node_score(node_id):
    nodes = []
    for node in nodes:
        node = nodes.get(node_id, {})
        return node.get("trust_score", 1.0)

def calculate_mining_rate(U, S, B, Score,
                          R_base=0.082,
                          U_target=10_000,
                          S_max=TOTAL_MINING_SUPPLY,
                          B_halflife=100_000):
    user_factor = (U_target / max(U, U_target)) ** 0.5
    supply_factor = (S / S_max)
    time_decay = 0.5 ** (B / B_halflife)
    node_boost = 1 + min(Score, 0.10)
    rate = (R_base * user_factor * supply_factor * time_decay * node_boost)
    rate_dict = {
        "base": R_base,
        "user": user_factor,
        "supply": supply_factor,
        "time": time_decay,
        "node": node_boost
    }

    return rate, rate_dict

def get_dynamic_mining_rate():
    data = get_chain_summary()
    U = data["accounts"]
    S, _ = load_balance(mining_address)
    B = data["blocks"]
    Score = 1.0  # Placeholder; replace with actual node trust score if needed
    rate, rate_dict = calculate_mining_rate(U, S, B, Score)
    return rate, rate_dict

def format_duration(seconds):
    seconds = int(seconds)
    days, seconds = divmod(seconds, 86400)
    hours, seconds = divmod(seconds, 3600)
    minutes, seconds = divmod(seconds, 60)

    parts = []
    if days > 0:
        parts.append(f"{days}d")
    if hours > 0 or days > 0:
        parts.append(f"{hours}h")
    if minutes > 0 or hours > 0 or days > 0:
        parts.append(f"{minutes}m")
    parts.append(f"{seconds}s")

    return " ".join(parts)

def check_mining(address):
    users = load_users()
    if address not in users:
        return

    user_data = users[address]
    now = time.time()
    start_time = user_data.get("mining_start_time", now)

    if not start_time:
        user_data["mining_start_time"] = now
        return False, "Mining timer initialized."

    remaining = 3600 - (now - start_time)
    if remaining > 0:
        return False, f"Mining available again in {format_duration(remaining)}"
    return True, "Mining ready"

def start_mining(address):
    users = load_users()
    if address not in users:
        return

    user_data = users[address]
    now = time.time()
    start_time = user_data.get("mining_start_time", now)

    if now - start_time < 3600:
        return False, f"Mining available again in {format_duration(3600 - (now - start_time))}"

    user_data["mining_start_time"] = now
    users[address] = user_data
    save_users(users)

    rate, rate_dict = get_dynamic_mining_rate()
    mined = round(rate * 3600, 6)

    node_fee_rate = 0.03
    node_fee = round(mined * node_fee_rate, 6)
    user_payout = round(mined - node_fee, 6)

    if MODE == "mainnet":
        tx_metadata = TXTypes.MiningTypes(
            mined,
            rate_dict["base"],
            rate_dict["user"],
            rate_dict["supply"],
            rate_dict["time"],
            time.time()
        )
        tx_order = TXTypes.MiningTypes.mining_metadata(node_fee, tx_metadata.rate_dict())
        token_tx = TXExchange.create_token_transfer_tx(
            sender="ORB.A6C19210F2B823246BA1DCA7",
            receiver=address,
            amount=user_payout,
            token_symbol="FUEL",
            note="Mining reward",
        )
        orbit_amount = 0.5
        send_orbit(mining_address, address, user_payout, order=tx_order)
        send_orbit("ORB.A6C19210F2B823246BA1DCA7", address, orbit_amount, order=token_tx)

        return True, {
            "rate": rate,
            "mined": mined,
            "payout": user_payout
        }
