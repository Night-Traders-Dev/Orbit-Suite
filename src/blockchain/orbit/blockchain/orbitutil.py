import json
import os
import time
import random
from config.configutil import NodeConfig, OrbitDB
from core.ioutil import load_nodes, save_nodes, session_util
from core.logutil import log_node_activity
from core.networkutil import send_block_to_node

orbit_db = OrbitDB()
PENDING_PROPOSALS_FILE = orbit_db.pendpropdb

TRUST_BLACKLIST_THRESHOLD = 0.2

def assign_node_to_user(username, sessions):
    sessions = session_util("load")  # Load the current user:node mapping
    nodes = load_nodes()  # Format: { "Node1": {node data}, ... }

    if username in sessions:
        return sessions[username]

    if nodes:
        available_node_ids = list(nodes.keys())
        chosen_node = random.choice(available_node_ids)
        sessions[username] = chosen_node
        session_util("save", sessions)
        return chosen_node

    return None  # No nodes available

def revoke_node_from_user(username):
    sessions = session_util("load")
    if username in sessions:
        del sessions[username]
        session_util("save", sessions)

def get_node_for_user(username):
    sessions = session_util("load")
    return sessions.get(username)

def register_node(node_id, quorum_slice, address, port):
#    nodes = load_nodes()
    node_config = NodeConfig()
    node_config.address = address
    node_config.port = port
    node_config.quorum_slice = quorum_slice
    node_config.trust_score = 1.0
    node_config.uptime_score = 1.0
    nodes[node_id] = node_config.to_dict()
#    save_nodes(nodes)
    log_node_activity(node_id, "register_node", f"Registered with quorum {quorum_slice}")
    return nodes

def update_uptime(node_id, is_online=True):
    nodes = load_nodes()
    if node_id in nodes:
        old_score = nodes[node_id]["uptime_score"]
        delta = 0.05 if is_online else -0.1
        nodes[node_id]["uptime_score"] = max(0.0, min(1.0, old_score + delta))
        save_nodes(nodes)
        log_node_activity(node_id, "update_uptime", f"{old_score:.3f} → {nodes[node_id]['uptime_score']:.3f}")

def update_trust(node_id, success=True):
    nodes = load_nodes()
    if node_id in nodes:
        old_score = nodes[node_id]["trust_score"]
        delta = 0.05 if success else -0.1
        new_score = max(0.0, min(1.0, old_score + delta))
        nodes[node_id]["trust_score"] = new_score

        # Blacklist logic
        if new_score <= TRUST_BLACKLIST_THRESHOLD:
            log_node_activity(node_id, "blacklist", f"Trust score too low: {new_score:.2f}")
            del nodes[node_id]
        else:
            log_node_activity(node_id, "update_trust", f"{old_score:.3f} → {new_score:.3f}")

        save_nodes(nodes)

def simulate_peer_vote(peer_id, block_data, trust_score):
    approval_chance = trust_score * 0.9 + 0.1
    result = random.random() < approval_chance
    log_node_activity(peer_id, "simulate_peer_vote", f"Trust {trust_score:.2f} → {'approve' if result else 'reject'}")
    return result

def simulate_quorum_vote(node_id, block_data):
    nodes = load_nodes()
    quorum = nodes.get(node_id, {}).get("quorum_slice", [])
    if not quorum:
        log_node_activity(node_id, "simulate_quorum_vote", "No quorum slice defined")
        return False

    votes = 0
    for peer in quorum:
        trust = nodes.get(peer, {}).get("trust_score", 0.5)
        result = simulate_peer_vote(peer, block_data, trust)
        update_uptime(peer, result)
        update_trust(peer, result)
        if result:
            votes += 1
    log_node_activity(node_id, "simulate_quorum_vote", f"{votes}/{len(quorum)} approvals")
    return votes >= max(1, len(quorum) // 2)

def sign_vote(node_id, block_data):
    log_node_activity(node_id, "sign_vote", f"Signed block {block_data}")
    return f"signed({node_id})"

def select_next_validator():
    nodes = load_nodes()
    candidates = [(nid, n["trust_score"] * n["uptime_score"]) for nid, n in nodes.items()]
    candidates.sort(key=lambda x: x[1], reverse=True)
    if not candidates:
        log_node_activity("system", "select_next_validator", "No eligible candidates")
        return None
    selected = candidates[0][0]
    log_node_activity(selected, "select_next_validator", "Selected as next validator")
    return selected

def save_pending_proposal(node_id, block_data):
    proposals = {}
    if os.path.exists(PENDING_PROPOSALS_FILE):
        with open(PENDING_PROPOSALS_FILE, "r") as f:
            proposals = json.load(f)
    proposals[block_data["hash"]] = {"sender": node_id, "block": block_data}
    with open(PENDING_PROPOSALS_FILE, "w") as f:
        json.dump(proposals, f, indent=2)

def relay_pending_proposal(node_id, block_data):
    nodes = load_nodes()
    quorum = nodes.get(node_id, {}).get("quorum_slice", [])
    save_pending_proposal(node_id, block_data)

    for peer_id in quorum:
        peer_node = nodes.get(peer_id)
        if not peer_node:
            continue

        address = peer_node.get("address")
        success = False
        attempt = 0
        max_attempts = 3

        while not success and attempt < max_attempts:
            success = send_block_to_node(address, block_data)
            attempt += 1
            if not success:
                time.sleep(2 ** attempt)  # exponential backoff

        log_node_activity(
            node_id,
            "relay",
            f"Sent block to {peer_id} ({'✓' if success else 'x'}) after {attempt} attempt(s)"
        )
