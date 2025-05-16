import math
import time
from core.userutil import load_users, save_users
from blockchain.blockutil import add_block
from config.configutil import MiningConfig, TXConfig, get_node_for_user

# Load configuration
mining_config = MiningConfig()

# Simulation or Mainnet mode toggle
MODE = "simulation"  # Toggle to "mainnet" when ready

def get_base_rate(start_time):
    current_time = time.time()
    t = current_time - start_time
    return mining_config.base * math.exp(-mining_config.decay * t)

def get_security_circle_bonus(user_data):
    return 0.05 * min(len(user_data.get("security_circle", [])), 5)

def get_lockup_reward(user_data):
    locked = user_data.get("locked", [])
    Lb = user_data.get("balance", 1)

    current_time = time.time()
    active_lockups = [
        lock for lock in locked
        if current_time < lock["start_time"] + lock["duration_days"] * 86400
    ]

    n = len(active_lockups)
    if n == 0 or Lb == 0:
        return 0

    total = 0
    for lock in active_lockups:
        Lc = lock["amount"]
        Lt = lock["duration_days"]
        total += (Lc / Lb) * Lt * math.log(n + 1)

    return total

def get_referral_bonus(user_data):
    return 0.01 * len(user_data.get("referrals", []))

def calculate_total_rate(user_data, start_time):
    B = get_base_rate(start_time)
    S = get_security_circle_bonus(user_data)
    L = get_lockup_reward(user_data)
    R = get_referral_bonus(user_data)
    I = B * (1 + S + L + R)
    return I

def simulate_mining(username, duration=10):
    users = load_users()
    node_id = get_node_for_user(username)
    if username not in users:
        print("User not found.")
        return

    user_data = users[username]
    start_time = user_data.get("mining_start_time", time.time())
    user_data["mining_start_time"] = start_time

    print(f"Simulating mining for {duration} seconds...")
    rate = calculate_total_rate(user_data, start_time)
    mined = rate * duration
    user_data["balance"] += mined
    print(f"Mining rate: {rate:.6f} Orbit/sec")
    print(f"Mined: {mined:.6f} Orbit")

    # Blockchain record of mining reward
    if MODE == "simulation":
        mining_tx = TXConfig.Transaction(
            sender="mining",
            recipient=username,
            amount=round(mined, 6),
            note="Mining Reward",
            timestamp=time.time()
        )
        add_block([mining_tx.to_dict()], node_id)

    users[username] = user_data
    save_users(users)
