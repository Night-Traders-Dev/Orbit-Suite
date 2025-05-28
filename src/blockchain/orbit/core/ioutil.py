import os
import fcntl
import time
import json
import platform
import requests
from functools import wraps
from config.configutil import OrbitDB

orbit_db = OrbitDB()
CHAIN_FILE = orbit_db.blockchaindb
LOCK_FILE = CHAIN_FILE + ".lock"
NODES_FILE = orbit_db.nodedb
PENDING_PROPOSALS_FILE = orbit_db.pendpropdb

# ===================== USER FUNCS =====================

def load_active_sessions():
    if os.path.exists(orbit_db.activesessiondb):
        with open(orbit_db.activesessiondb, "r") as f:
            return json.load(f)
    return {}

def save_active_sessions(sessions):
    with open(orbit_db.activesessiondb, "w") as f:
        json.dump(sessions, f, indent=4)

def load_users():
    if os.path.exists(orbit_db.userdb):
        with open(orbit_db.userdb, "r") as f:
            return json.load(f)
    return {}

def save_users(users):
    with open(orbit_db.userdb, "w") as f:
        json.dump(users, f, indent=4)

# ===================== NODE FUNCS =====================

EXPLORER_API = "http://localhost:7000"

def load_nodes():
    try:
        response = requests.get(f"{EXPLORER_API}/active_nodes", timeout=5)
        if response.status_code == 200:
            return response.json()
        else:
            print(f"[load_nodes] Failed with status {response.status_code}")
            return {}
    except requests.Timeout as e:
        print(f"[load_nodes] Timeout")
    except Exception as e:
        print(f"[load_nodes] Explorer unreachable: {e}")
        return {}

def save_nodes(nodes, exclude_id=None):
    for node in nodes:
#        if exclude_id:
#            if node["node"]["id"] == exclude_id:
#                continue
        try:
            requests.post(
                f"{EXPLORER_API}/node_ping",
                json=node,
                timeout=3
            )
        except requests.Timeout as e:
            print(f"[save_nodes] Timeout")
        except Exception as e:
            print(f"[save_nodes] Failed to ping explorer for node {node_id}: {e}")



def session_util(option, sessions=None):
    if option == "load":
        return load_active_sessions()
    elif option == "save":
        if sessions is not None:
            save_active_sessions(sessions)
    else:
        return None

# ===================== CHAIN FUNCS =====================

def acquire_soft_lock(owner_id, timeout=5):
    start = time.time()

    while os.path.exists(LOCK_FILE):
        try:
            with open(LOCK_FILE, "r") as f:
                current_owner = f.read().strip()
        except (OSError, IOError) as e:
            print(f"[Soft Lock] Warning: Failed to read lock file: {e}")
            time.sleep(0.1)
            continue

        if time.time() - start > timeout:
            print(f"[Soft Lock] Timeout waiting for lock held by {current_owner}")
            return False
        time.sleep(0.1)

    try:
        f = open(LOCK_FILE, "w")
        if FILE_LOCK_SUPPORTED:
            try:
                fcntl.flock(f, fcntl.LOCK_EX | fcntl.LOCK_NB)
            except BlockingIOError:
                f.close()
                print("[Soft Lock] Could not acquire file lock via fcntl.")
                return False

        f.write(owner_id)
        f.close()
        return True
    except (OSError, IOError) as e:
        print(f"[Soft Lock] Failed to create or lock file: {e}")
        return False

def release_soft_lock(owner_id):
    if os.path.exists(LOCK_FILE):
        with open(LOCK_FILE, "r") as f:
            current_owner = f.read().strip()
        if current_owner == owner_id:
            os.remove(LOCK_FILE)

if platform.system() == 'Windows':
    import msvcrt
else:
    try:
        import fcntl
        FILE_LOCK_SUPPORTED = True
    except ImportError:
        FILE_LOCK_SUPPORTED = False

def fetch_chain(url="localhost", port="7000"):
    chainurl=(f"http://{url}:{port}/api/chain")
    try:
        response = requests.get(chainurl, timeout=5)
        if response.status_code == 200:
            return response.json()
        else:
            print(f"Failed to fetch chain. Status code: {response.status_code}")
            return []
    except Exception as e:
        print(f"Error fetching chain: {e}")
        return []

def load_chain(owner_id="explorer", wait_time=5):
    start = time.time()
    while os.path.exists(LOCK_FILE):
        try:
            with open(LOCK_FILE, "r") as f:
                lock_holder = f.read().strip()
        except:
            lock_holder = "unknown"

        if time.time() - start > wait_time:
            print(f"[Soft Lock] Timeout: chain locked by {lock_holder}. Returning fallback empty chain.")
            return []  # <-- instead of None
        time.sleep(0.1)

    try:
        with open(LOCK_FILE, "w") as f:
            f.write(owner_id)

        if not os.path.exists(CHAIN_FILE):
            return [create_genesis_block()]

        with open(CHAIN_FILE, "r") as f:
            return json.load(f)

    except Exception as e:
        print(f"[load_chain] Failed: {e}")
        return []

    finally:
        if os.path.exists(LOCK_FILE):
            try:
                with open(LOCK_FILE, "r") as f:
                    current = f.read().strip()
                if current == owner_id:
                    os.remove(LOCK_FILE)
            except:
                pass


def save_chain(chain, owner_id="default", chain_file=CHAIN_FILE):
    if not acquire_soft_lock(owner_id):
        return False
    try:
        with open(chain_file, "w") as f:
            json.dump(chain, f, indent=4)
        return True
    finally:
        release_soft_lock(owner_id)

# ===================== DECORATORS =====================

def with_chain(func):
    @wraps(func)
    def wrapper(*args, **kwargs):
        chain = load_chain()
        return func(chain, *args, **kwargs)
    return wrapper


def with_nodes(func):
    @wraps(func)
    def wrapper(*args, **kwargs):
        nodes = load_nodes()
        return func(nodes, *args, **kwargs)
    return wrapper

def with_users(func):
    @wraps(func)
    def wrapper(*args, **kwargs):
        users = load_users()
        return func(users, *args, **kwargs)
    return wrapper
