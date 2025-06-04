import time, math
from core.tx_util.tx_types import TXTypes
from core.ioutil import load_users, save_users, fetch_chain
from core.walletutil import load_balance
from blockchain.blockutil import add_block
from config.configutil import MiningConfig, TXConfig, get_node_for_user
from blockchain.tokenutil import send_orbit

# Load configuration
mining_config = MiningConfig()
MODE = "mainnet"

def get_chain_summary():
    chain = fetch_chain()
    tx_count = sum(len(b.get("transactions", [])) for b in chain)
    account_set = set()
    total_orbit = 100000000
    circulating = (0 - total_orbit)
    for b in chain:
        for tx in b.get("transactions", []):
            account_set.add(tx["sender"])
            account_set.add(tx["recipient"])
            circulating += tx["amount"]
    return {
        "blocks": len(chain),
        "transactions": tx_count,
        "accounts": len(account_set),
        "circulating": circulating,
        "total_orbit": total_orbit
    }


def get_node_score(node_id):
    nodes = load_nodes()
    for node in nodes:
        node = nodes.get(node_id, {})
        return node.get("trust_score", 1.0)

def calculate_mining_rate(U, S, B, Score,
                          R_base=0.082,
                          U_target=10000,
                          S_max=100000,
                          B_halflife=100000):
    user_factor = (U_target / max(U, U_target)) ** 0.5
    supply_factor = max(0, 1 - (S / S_max))
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
    S = data["circulating"]
    B = data["blocks"]
    Score = 1.0 #get_node_score(node_id)
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
    node_id = get_node_for_user(address)
    now = time.time()

    start_time = user_data.get("mining_start_time", now)
    if not start_time:
        user_data["mining_start_time"] = now
        start_time = now
    else:
        if now - start_time < 3600:
            return False, f"{format_duration(3600 - (now - start_time))}"

def start_mining(address):
    users = load_users()
    if address not in users:
        return

    user_data = users[address]
    node_id = get_node_for_user(address)
    now = time.time()

    start_time = user_data.get("mining_start_time", now)
    if not start_time:
        user_data["mining_start_time"] = now
        start_time = now
    else:
        if now - start_time < 3600:
            return False, f"Mining available again in {format_duration(3600 - (now - start_time))}"

    user_data["mining_start_time"] = now

    rate, rate_dict = get_dynamic_mining_rate()
    mined = round(rate * 3600, 6)

    # Calculate dynamic node fee (e.g., 3% of mined)
    node_fee_rate = 0.03
    node_fee = round(mined * node_fee_rate, 6)
    user_payout = round(mined - node_fee, 6)

    if MODE == "mainnet":
        users[address] = user_data
        save_users(users)
        tx_metadata = TXTypes.MiningTypes(
            mined,
            rate_dict["base"],
            rate_dict["user"],
            rate_dict["supply"],
            rate_dict["time"],
            time.time()
        )
        rate_data = tx_metadata.rate_dict()
        tx_order = TXTypes.MiningTypes.mining_metadata(node_fee, rate_data)
        send_orbit("mining", address, user_payout, order=tx_order)

        return True, {
            "rate": rate,
            "mined": mined,
            "payout": user_payout
        }
