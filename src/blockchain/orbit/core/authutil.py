import json, os, time
from core.hashutil import generate_orbit_address

LOGIN_FILE = "data/login.now"
SESSION_TIMEOUT = 300  # 5 minutes in seconds

def load_login_sessions():
    if not os.path.exists(LOGIN_FILE):
        return {}
    with open(LOGIN_FILE, "r") as f:
        return json.load(f)

def save_login_sessions(data):
    with open(LOGIN_FILE, "w") as f:
        json.dump(data, f)

def update_login(discord_id):
    address = generate_orbit_address(discord_id)
    data = load_login_sessions()
    current_time = int(time.time())
    data[address] = {
        "login_time": data.get(address, {}).get("login_time", current_time),
        "last_interaction": current_time
    }
    save_login_sessions(data)

def is_logged_in(discord_id):
    address = generate_orbit_address(discord_id)
    data = load_login_sessions()
    session = data.get(address)
    if not session:
        return False
    if int(time.time()) - session['last_interaction'] > SESSION_TIMEOUT:
        del data[address]
        save_login_sessions(data)
        return False
    return True

def cleanup_expired_sessions():
    data = load_login_sessions()
    now = int(time.time())
    to_delete = [address for address, sess in data.items() if now - sess['last_interaction'] > SESSION_TIMEOUT]
    for user in to_delete:
        del data[address]
    save_login_sessions(data)
