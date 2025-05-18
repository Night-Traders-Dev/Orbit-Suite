import math
import time
from core.userutil import load_users, save_users
from blockchain.blockutil import add_block
from config.configutil import MiningConfig, TXConfig, get_node_for_user
from blockchain.tokenutil import send_orbit

# Load configuration
mining_config = MiningConfig()
MODE = "simulation"  # Toggle to "mainnet" when ready

MAX_MINING_RATE = 5.0  # max Orbit/sec allowed per user
MAX_MINING_DURATION = 60 * 60  # 1 hour max per mining session

def get_base_rate(start_time):
    current_time = time.time()
    t = current_time - start_time
    return mining_config.base * math.exp(-mining_config.decay * t)

def get_security_circle_bonus(user_data):
    circle = user_data.get("security_circle", [])
    if not isinstance(circle, list): return 0
    return min(0.25, 0.05 * min(len(circle), 5))

def get_lockup_reward(user_data):
    locked = user_data.get("locked", [])
    Lb = user_data.get("balance", 1)
    current_time = time.time()

    if not isinstance(locked, list) or Lb <= 0:
        return 0

    active_lockups = [
        lock for lock in locked
        if isinstance(lock, dict)
        and "amount" in lock and "duration_days" in lock and "start_time" in lock
        and current_time < lock["start_time"] + lock["duration_days"] * 86400
    ]

    n = len(active_lockups)
    if n == 0:
        return 0

    total = 0
    for lock in active_lockups:
        Lc = lock["amount"]
        Lt = lock["duration_days"]
        if Lc > 0 and Lt > 0:
            total += (Lc / Lb) * Lt * math.log(n + 1)

    return min(total, 0.5)  # cap lockup bonus

def get_referral_bonus(user_data):
    refs = user_data.get("referrals", [])
    if not isinstance(refs, list): return 0
    return min(0.1, 0.01 * len(refs))

def calculate_total_rate(user_data, start_time):
    B = get_base_rate(start_time)
    S = get_security_circle_bonus(user_data)
    L = get_lockup_reward(user_data)
    R = get_referral_bonus(user_data)
    I = B * (1 + S + L + R)
    return min(I, MAX_MINING_RATE)

def simulate_mining(username, duration=10):
    users = load_users()
    if username not in users:
        print("User not found.")
        return

    user_data = users[username]
    node_id = get_node_for_user(username)
    now = time.time()

    start_time = user_data.get("mining_start_time", now)
    if not start_time:
        user_data["mining_start_time"] = now
        start_time = now
    else:
        if now - start_time < 1:
            print("Mining session already active or too recent.")
            return

    duration = min(duration, MAX_MINING_DURATION)
    user_data["mining_start_time"] = now

    print(f"Simulating mining for {duration} seconds...")
    rate = calculate_total_rate(user_data, start_time)
    mined = round(rate * duration, 6)

    # Calculate dynamic node fee (e.g., 3% of mined)
    node_fee_rate = 0.03
    node_fee = round(mined * node_fee_rate, 6)
    user_payout = round(mined - node_fee, 6)

    print(f"Mining rate: {rate:.6f} Orbit/sec")
    print(f"Total mined: {mined:.6f} Orbit")
    print(f"Node Fee: {node_fee:.6f} Orbit → Node {node_id}")
    print(f"User reward: {user_payout:.6f} Orbit")

    if MODE == "simulation":
        send_orbit("mining", username, user_payout, "Mining Reward")

    users[username] = user_data
    save_users(users)
