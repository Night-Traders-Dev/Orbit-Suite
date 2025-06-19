import time, datetime
from core.ioutil import fetch_chain
from config.configutil import TXConfig

async def get_wallet_stats(symbol):
    from core.tokenmeta import get_token_meta
    from core.orderutil import all_tokens_stats
    from core.cacheutil import get_cached, set_cached, clear_cache
    current_price = 0.0
    wallet_stats = []

    response = await get_token_meta(symbol.upper())
    for i in response:
        if "current_price" in i:
            current_price = response.get("current_price")
    cached = get_cached("all_tokens_stats")
    if cached:
        tokens, metrics = cached
    else:
        tokens, wallets, metrics = await all_tokens_stats(symbol.upper())
    for address in wallets:
        if wallets[address]["amount"] >= 0:
            token_value = wallets[address]["amount"] * current_price
            wallet_stats.append(f"{address}: {wallets[address]['amount']:,}({token_value:,} Orbit)")
    return wallet_stats

def load_balance(username):
    blockchain = fetch_chain() #load_chain(username)
    balance = 0
    locked_from_ledger = []
    total_sent = 0
    total_received = 0
    total_locked = 0

    for block in blockchain:
        for tx_data in block.get("transactions", []):
            tx = TXConfig.Transaction.from_dict(tx_data)
            note = (tx.note or "")
            is_sender = tx.sender == username
            is_recipient = tx.recipient == username
            for txdata in block.get("transactions", {}):
                if txdata["sender"] == username and txdata["recipient"] == "lockup_rewards":
                    try:
                        total_locked += int((txdata["note"]["type"]["lockup"]["amount"]))
                    except Exception:
                        continue

            # Tally totals
            if is_sender:
                total_sent += tx.amount
            if is_recipient:
                total_received += tx.amount

            # Transfer logic (default if note is empty or includes "transfer")
            if not note or "transfer" in note:
                if is_sender:
                    balance -= tx.amount
                if is_recipient:
                    balance += tx.amount

            # Mining reward
            elif "mining reward" in note:
                if is_recipient:
                    balance += tx.amount

            # Lockup transaction
            elif "lockup" in note:
                if is_sender:
                    locked_from_ledger.append({
                        "amount": tx.amount,
                        "start": tx.timestamp,
                        "end": tx.lock_duration,
                        "days": tx.claim_until,
                    })
                    balance -= tx.amount
                    total_locked += tx.amount

            # Claimed reward
            elif "claimed reward" in note:
                if is_recipient:
                    balance += tx.amount

    # Calculate currently locked amount from ledger
    balance = abs(total_received - total_sent)

    return round(balance, 6), round(total_locked, 6)
