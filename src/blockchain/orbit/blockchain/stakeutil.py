import time
from config.configutil import TXConfig, get_node_for_user
from blockchain.blockutil import add_block
from blockchain.tokenutil import send_orbit
from core.ioutil import fetch_chain, load_users, save_users
from core.tx_types import TXTypes
from core.walletutil import load_balance
import json

LOCK_REWARD_RATE_PER_DAY = 0.05
MIN_LOCK_AMOUNT = 0.0001
MAX_LOCK_DURATION_DAYS = 365 * 5  # 5 years max


def get_all_lockups():
    chain = fetch_chain()
    lockups = []
    stakes = 0
    for block in chain:
        for tx in block['transactions']:
            if tx["recipient"] == "lockup_rewards":
                stakes += 1
                lockups.append({
                    "amount": tx["note"]["type"]["lockup"]["amount"],
                    "days": tx["note"]["type"]["lockup"]["days"],
                    "stakes": stakes
                 })
    return lockups

def get_user_lockups(username: str = "all"):
    chain = fetch_chain()
    lockups = []

    for block in chain:
        for tx in block.get("transactions", []):
            if tx.get("recipient") != "lockup_rewards":
                continue

            sender = tx.get("sender")

            if username != "all" and sender != username:
                continue

            try:
                note = tx.get("note", {})
                lock = note.get("type", {}).get("lockup", {})
                lockups.append({
                    "amount": lock.get("amount"),
                    "start": lock.get("start"),
                    "end": lock.get("end"),
                    "days": lock.get("days"),
                    "uuid": lock.get("uuid"),
                    "user": sender  # useful when "all" is selected
                })
            except Exception:
                continue

    return lockups


def print_lockups(lockups):
    if not lockups:
        print("No active lockups.")
        return

    print("Your Lockups:")
    for i, lock in enumerate(lockups):
        locked = lock["amount"]
        end = lock["end"]
        start = lock["start"]
        now = time.time()
        init_days = int((end - start) / 86400)

        duration = {"start": start, "end": end, "init_days": init_days, "now": now}
        amount = {"lock": locked}
        staking = TXTypes.StakingTypes(duration, amount)
        lockup_tx = TXTypes(
            tx_class="staking",
            tx_type="lockup",
            tx_data=staking.tx_build("lockup"),
            tx_value="dict"
        )
        order_tx = lockup_tx.tx_types()
        days_remaining = order_tx.get("type", {}).get("lockup", {}).get("days", 0)
        print(f" {i+1}. {locked:.4f} Orbit locked — {days_remaining:.1f} days remaining")

def view_lockups(username):
    lockups = get_user_lockups(username)
    print_lockups(lockups)

def lock_tokens(username, duration, amount):
    users = load_users()
    balance, _ = load_balance(username)

    try:
        if amount < MIN_LOCK_AMOUNT or amount > balance:
            print("Invalid amount.")
            return

        if duration < 1 or duration > MAX_LOCK_DURATION_DAYS:
            return
        lockup_times = {"init_days": duration}
        lockup_amount = {"lock": amount}
        staking = TXTypes.StakingTypes(lockup_times, lockup_amount)
        lock_metadata = TXTypes(
            tx_class="staking",
            tx_type="lockup",
            tx_data=staking.tx_build("lockup"),
            tx_value="dict"
        )
        send_orbit(username, "lockup_rewards", amount, order=lock_metadata.tx_types())
        return True, {
            "lockup_times": lockup_times,
            "lockup_amount": lockup_amount
        }

    except ValueError:
        print("Invalid input.")



def withdraw_lockup(username):
    from core.hashutil import generate_lock_id
    users = load_users()
    user = users[username]
    lockups = get_user_lockups(username)
    now = int(time.time())

    matured_total = 0.0
    txs = []
    remaining_locked = []


    for i, lock in enumerate(lockups):
        amount = lock["amount"]
        duration = lock["days"]
        start = lock["start"]
        uuid =  lock["uuid"]
        lock_end = start + duration * 86400
        tuid = generate_lock_id(start, lock, lock_end)

        if now >= lock_end:
            matured_total += amount
        else:
            remaining_locked.append(lock)

    if uuid == tuid:
        print(f"lockup: {uuid} already claimed.")
        return

    if matured_total == 0:
        print("No matured lockups available to withdraw.")
        return

    node_id = get_node_for_user(username)
    node_fee_rate = 0.02  # 2% withdrawal fee
    fee = round(matured_total * node_fee_rate, 6)
    payout = round(matured_total - fee, 6)

    print(f"Matured Amount: {matured_total:.6f} Orbit")
    print(f"Node Fee (2%): {fee:.6f} Orbit")
    print(f"Net Payout: {payout:.6f} Orbit")

    confirm = input("Proceed with withdrawal? (y/n): ").strip().lower()
    if confirm != 'y':
        print("Withdrawal cancelled.")
        return

    now = time.time()
    lockup_times = {"init_days": duration, "start": start, "end": lock_end}
    lockup_amount = {"lock": amount}
    staking = TXTypes.StakingTypes(lockup_times, lockup_amount)

    # Main withdrawal transaction
    txs.append(TXConfig.Transaction(
        sender="lockup_rewards",
        recipient=username,
        amount=payout,
        note=staking.tx_build("withdraw"),
        timestamp=now
    ).to_dict())

    # Node fee transaction
    txs.append(TXConfig.Transaction(
        sender=username,
        recipient="nodefeecollector",
        amount=fee,
        note={"type": f"Lockup Withdrawal Fee: {fee}", "node": node_id},
        timestamp=now
    ).to_dict())

    # Write to chain
    add_block(txs, node_id)

    # Update user state
    user["locked"] = remaining_locked
    user["balance"] += payout
    save_users(users)

    print(f"{matured_total:.6f} Orbit withdrawn from matured lockups.")
    print(f"Node Fee: {fee:.6f} Orbit → Node {node_id}")
    print(f"{payout:.6f} Orbit added to your balance.")


def claim_lockup_rewards(username):
    users = load_users()
    user = users[username]
    user_lockups = get_user_lockups(username)
    now = int(time.time())
    chain = fetch_chain()
    node_id = get_node_for_user(username)

    # Step 1: Extract most recent claim_until per lock_start from chain
    claim_map = {}
    for block in chain:
        for tx in block.get("transactions", []):
            if tx.get("recipient") == username and tx.get("sender") == "lockup_rewards":
                note = tx.get("note", {})
                if isinstance(note, dict) and "start" in note and "end" in note:
                    lock_start = str(note["start"])
                    prev_claim = claim_map.get(lock_start, 0)
                    claim_map[lock_start] = max(prev_claim, note["end"])

    matured_total = 0.0
    total_reward = 0.0
    reward_txs = []
    still_locked = []
    claimed = 0
    lock_count = 0

    for lock in user_lockups:
        lock_count += 1
        lock_start = lock["start"]
        duration = lock["days"]
        amount = lock["amount"]
        lock_end = lock_start + duration * 86400
        last_claim = int(claim_map.get(str(lock_start), lock_start))
        claim_until = min(now, lock_end)

        # Unlock matured principal if reward has been claimed through or past lock_end
        if now >= lock_end and last_claim >= lock_end:
            matured_total += amount
        else:
            still_locked.append(lock)  # still in progress

        if now < last_claim + 86400:

            remaining = int((last_claim + 86400) - now)
            hours = remaining // 3600
            minutes = (remaining % 3600) // 60
            print(f"Next claim in {hours}h {minutes}m")
            claimed += 1
            continue

            if claimed == lock_count:
                return

        # Calculate eligible reward
        if last_claim < claim_until:
            seconds_eligible = claim_until - last_claim
            reward = (amount * LOCK_REWARD_RATE_PER_DAY / 86400) * seconds_eligible
            reward = round(reward, 6)
            lockup_times = {"start": lock_start, "end": lock["end"], "days": duration, "last_claim": last_claim}
            lockup_amount = {"amount": reward,"lock": amount, "claim": reward}
            staking = TXTypes.StakingTypes(lockup_times, lockup_amount)
            lock_metadata = TXTypes(
                tx_class="staking",
                tx_type="claim",
                tx_data=staking.tx_build("lockup"),
                tx_value="dict"
            )
            if reward > 0:
                total_reward += reward
                reward_txs.append(TXConfig.Transaction(
                    sender="lockup_rewards",
                    recipient=username,
                    amount=reward,
                    note=staking.tx_build("claim"),
                    timestamp=now
                ).to_dict())

    if total_reward == 0 and matured_total == 0:
        print("No new rewards or matured lockups available.")
        return

    node_fee = round(total_reward * 0.03, 6)
    net_reward = round(total_reward - node_fee, 6)

    if total_reward > 0:
        tx_fee = TXTypes.GasTypes(node_fee, node_id, username, "nodefeecollector")
        reward_txs.append(TXConfig.Transaction(
            sender=username,
            recipient="nodefeecollector",
            amount=node_fee,
            note=tx_fee.gas_tx(),
            timestamp=now
        ).to_dict())
        add_block(reward_txs, node_id)

    if matured_total > 0:
        user["balance"] += round(matured_total, 6)
        print(f"{matured_total:.6f} Orbit unlocked from matured lockups.")

    user["locked"] = still_locked
    save_users(users)

    if net_reward > 0:
        print(f"Claimed {total_reward:.6f} Orbit in lockup rewards.")
        print(f"Node Fee: {node_fee:.6f} Orbit → Node {node_id}")
        print(f"Net credited: {net_reward:.6f} Orbit")

        choice = input("Re-lock rewards for compounding? (y/n): ").strip().lower()
        if choice == 'y':
            try:
                duration = int(input("Enter new lockup duration in days (1 - 1825): "))
                if duration < 1 or duration > MAX_LOCK_DURATION_DAYS:
                    print("Invalid duration.")
                    return
                relock_tx = TXConfig.Transaction(
                    sender=username,
                    recipient="lockup_rewards",
                    amount=net_reward,
                    note={"duration": duration},
                    timestamp=time.time()
                )
                add_block([relock_tx.to_dict()])
                print(f"Re-locked {net_reward:.6f} Orbit for {duration} days.")
            except ValueError:
                print("Invalid duration.")
        else:
            users = load_users()
            users[username]["balance"] += net_reward
            save_users(users)
            print(f"{net_reward:.6f} Orbit added to your balance.")
