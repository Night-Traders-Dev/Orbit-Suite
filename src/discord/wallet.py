from api import lock_orbit_api

def get_wallet_balance(address):
    return {
        "address": address,
        "available": 0.0,
        "locked": 0.0,
        "total": 0.0,
        "transactions": [],
        "validators": {},
        "security_circle": []
    }

async def lock_orbit(username, amount, duration):
    result, message = await lock_orbit_api(username, amount, duration)
    if result == "success":
        return True

def claim_rewards(username):
    return True
