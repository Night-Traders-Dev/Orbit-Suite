import hashlib
import json
import time
import os
import random
import socket
import threading
import platform

from blockchain.orbitutil import update_trust, update_uptime, save_nodes, load_nodes, simulate_peer_vote, sign_vote, relay_pending_proposal, simulate_quorum_vote, select_next_validator
from config.configutil import OrbitDB, NodeConfig, TXConfig, get_node_for_user
from core.userutil import load_users, save_users

orbit_db = OrbitDB()

CHAIN_FILE = orbit_db.blockchaindb

def start_listener(node_id):
    node_data = load_nodes().get(node_id)
    if not node_data:
        print(f"No config found for node {node_id}")
        return

    address = node_data["address"]
    port = node_data["port"]
    server = socket.socket(socket.AF_INET, socket.SOCK_STREAM)
    server.setsockopt(socket.SOL_SOCKET, socket.SO_REUSEADDR, 1)
    server.bind((address, port))
    server.listen()
    print(f"[Listener] {node_id} listening on {address}:{port}...")

    while True:
        conn, addr = server.accept()
        threading.Thread(target=handle_connection, args=(conn, addr, node_id), daemon=True).start()

def handle_connection(conn, addr, node_id):
    try:
        data = conn.recv(4096)
        if not data:
            return
        msg = json.loads(data.decode())

        if msg.get("type") == "block":
            block_data = msg["data"]
            chain = load_chain()

            # Skip if block already exists
            if any(b["hash"] == block_data["hash"] for b in chain):
                update_trust(node_id, success=False)
                update_uptime(node_id, is_online=True)
                return

            # First-time use: accept block if chain is empty and index is 0
            if not chain and block_data["index"] == 0:
                save_chain([block_data])
                return

            # Normal validation
            if chain and block_data["previous_hash"] == chain[-1]["hash"]:
                chain.append(block_data)
                save_chain(chain)
                update_trust(node_id, success=True)
                update_uptime(node_id, is_online=True)

    except Exception as e:
        print(f"[{node_id}] Error handling connection from {addr}: {e}")
    finally:
        conn.close()



def generate_merkle_root(transaction_dicts):
    def hash_pair(a, b):
        return hashlib.sha256((a + b).encode()).hexdigest()

    tx_hashes = [hashlib.sha256(json.dumps(tx, sort_keys=True).encode()).hexdigest() for tx in transaction_dicts]
    while len(tx_hashes) > 1:
        if len(tx_hashes) % 2 == 1:
            tx_hashes.append(tx_hashes[-1])  # duplicate last hash if odd
        tx_hashes = [hash_pair(tx_hashes[i], tx_hashes[i+1]) for i in range(0, len(tx_hashes), 2)]
    return tx_hashes[0] if tx_hashes else ""

def calculate_hash(index, previous_hash, timestamp, transactions, validator="", merkle_root="", nonce=0, metadata=None):
    block_content = {
        "index": index,
        "previous_hash": previous_hash,
        "timestamp": timestamp,
        "transactions": transactions,
        "validator": validator,
        "merkle_root": merkle_root,
        "nonce": nonce,
        "metadata": metadata or {}
    }
    block_string = json.dumps(block_content, sort_keys=True)
    return hashlib.sha256(block_string.encode()).hexdigest()

def create_genesis_block():
    genesis_block = TXConfig.Block(
        index=0,
        timestamp=time.time(),
        transactions=[],
        previous_hash="0",
        hash="",
        validator="genesis",
        signatures={},
        merkle_root="",
        nonce=0,
        metadata={"note": "genesis block"}
    )
    genesis_block.hash = calculate_hash(
        genesis_block.index,
        genesis_block.previous_hash,
        genesis_block.timestamp,
        [],
        genesis_block.validator,
        genesis_block.merkle_root,
        genesis_block.nonce,
        genesis_block.metadata
    )
    return genesis_block.to_dict()

LOCK_FILE = CHAIN_FILE + ".lock"

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
        with open(LOCK_FILE, "w") as f:
            f.write(owner_id)
        return True
    except (OSError, IOError) as e:
        print(f"[Soft Lock] Failed to create lock file: {e}")
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


def save_chain(chain, owner_id="default"):
    if not acquire_soft_lock(owner_id):
        return False
    try:
        with open(CHAIN_FILE, "w") as f:
            json.dump(chain, f, indent=4)
        return True
    finally:
        release_soft_lock(owner_id)


def get_last_block():
    chain = load_chain()
    return chain[-1]

def propose_block(node_id, block_data, timeout=5):
    nodes = load_nodes()

    if node_id not in nodes:
        print(f"Node {node_id} is not registered.")
        return False

    node_id = select_next_validator()
    proposer_config = NodeConfig.from_dict(nodes[node_id])
    quorum_slice = proposer_config.quorum_slice

    votes = {node_id}
    signatures = {node_id: sign_vote(node_id, block_data)}
    start_time = time.time()

    for peer_id in quorum_slice:
        if time.time() - start_time > timeout:
            break

        peer_data = nodes.get(peer_id)
        if not peer_data:
            print(f"[Propose] Peer {peer_id} not found in registry.")
            continue

        peer_config = NodeConfig.from_dict(peer_data)
        trust_score = peer_config.trust_score
        uptime_score = peer_config.uptime_score
        online = random.random() < uptime_score  # simulate uptime

        ADJUST_RATE = 0.05

        if online:
            if simulate_quorum_vote(peer_id, block_data):
                votes.add(peer_id)
                signatures[peer_id] = sign_vote(peer_id, block_data)
                peer_data["trust_score"] = min(peer_data.get("trust_score", 0.5) + ADJUST_RATE, 1.0)
                peer_data["uptime_score"] = min(peer_data.get("uptime_score", 0.5) + ADJUST_RATE, 1.0)
            else:

                peer_data["trust_score"] = max(peer_data.get("trust_score", 0.5) - ADJUST_RATE, 0.0)
        else:

            peer_data["uptime_score"] = max(peer_data.get("uptime_score", 0.5) - ADJUST_RATE, 0.0)

        nodes[peer_id] = peer_data

    required_votes = (len(quorum_slice) // 2) + 1

    if len(votes) >= required_votes:
        save_nodes(nodes)
        return True
    else:
        print(f"[Propose] Consensus failed: {len(votes)} votes (required {required_votes}).")
        relay_pending_proposal(node_id, block_data)
        save_nodes(nodes)
        return False

def receive_block(block):
    chain = load_chain()
    last_block = chain[-1]

    if block["index"] != last_block["index"] + 1:
        print("Rejected block: invalid index.")
        return False

    if block["previous_hash"] != last_block["hash"]:
        print("Rejected block: previous hash mismatch.")
        print(f"Expected: {last_block['hash']}, got: {block['previous_hash']}")
        return False

    recalculated_hash = calculate_hash(
        block["index"],
        block["previous_hash"],
        block["timestamp"],
        block["transactions"],
        block.get("validator", ""),
        block.get("merkle_root", ""),
        block.get("nonce", 0),
        block.get("metadata", {})
    )

    if recalculated_hash != block["hash"]:
        print("Rejected block: invalid hash.")
        return False

    chain.append(block)
    save_chain(chain)
    return True

def send_block(peer_address, block):
    host, port = peer_address.split(":")
    port = int(port)

    with socket.socket(socket.AF_INET, socket.SOCK_STREAM) as s:
        s.connect((host, port))
        data = json.dumps({"type": "block", "data": block.to_dict()})
        s.sendall(data.encode())

def broadcast_block(block, sender_id=None):
    nodes = load_nodes()
    for node_id, info in nodes.items():
        if node_id == sender_id:
            continue
        address = info.get("address")
        port = info.get("port")
        if address and port:
            full_address = f"{address}:{port}"
            try:
                send_block(full_address, block)
            except Exception as e:
                print(f"Failed to send block to {node_id} at {full_address}: {e}")

def add_block(transactions, node_id="Node1"):
    chain = load_chain()
    last_block = chain[-1]
    node_id = select_next_validator()

    tx_objs = [TXConfig.Transaction.from_dict(tx) for tx in transactions]

    # Calculate Merkle root from transaction dicts
    merkle_root = generate_merkle_root([tx.to_dict() for tx in tx_objs])

    new_block = TXConfig.Block(
        index=len(chain),
        timestamp=time.time(),
        transactions=tx_objs,
        previous_hash=last_block["hash"],
        hash="",
        validator=node_id,
        signatures={},
        merkle_root=merkle_root,
        nonce=0,
        metadata={"lockup_rewards": [], "version": "1.0"}
    )

    # Calculate hash for the new block
    new_block.hash = calculate_hash(
        new_block.index,
        new_block.previous_hash,
        new_block.timestamp,
        [tx.to_dict() for tx in new_block.transactions],
        new_block.validator,
        new_block.merkle_root,
        new_block.nonce,
        new_block.metadata
    )

    # Propose block to consensus
    if propose_block(node_id, new_block):
        users = load_users()

        for tx in new_block.transactions:
            tx_dict = tx.to_dict() if hasattr(tx, "to_dict") else tx
            sender = tx_dict.get("sender")
            recipient = tx_dict.get("recipient")
            amount = tx_dict.get("amount", 0)

            # Handle unknown accounts
            if sender not in users:
                print(f"Unknown sender {sender}, skipping transaction.")
                continue
            if recipient not in users:
                print(f"Unknown recipient {recipient}, skipping transaction.")
                continue

            # Perform the transfer if balance is sufficient
            if users[sender]["balance"] >= amount:
                users[sender]["balance"] -= amount
                users[recipient]["balance"] += amount
            else:
                print(f"Insufficient funds for {sender}, skipping transaction.")
                continue

        # Save updated user balances
        save_users(users)

        # Broadcast new block to network
        broadcast_block(new_block, node_id)


def is_chain_valid():
    chain = load_chain()
    for i in range(1, len(chain)):
        current = chain[i]
        previous = chain[i - 1]
        recalculated_hash = calculate_hash(
            current["index"],
            current["previous_hash"],
            current["timestamp"],
            current["transactions"],
            current.get("validator", ""),
            current.get("merkle_root", ""),
            current.get("nonce", 0),
            current.get("metadata", {})
        )
        if current["hash"] != recalculated_hash:
            return False
        if current["previous_hash"] != previous["hash"]:
            return False
    return True
