def get_wallet_balance(username):
    return {
        "address": username,
        "available": 0.0,
        "locked": 0.0,
        "total": 0.0,
        "transactions": [],
        "validators": {},
        "security_circle": []
    }

def lock_orbit(username, amount, duration):
    return True

def claim_rewards(username):
    return True
