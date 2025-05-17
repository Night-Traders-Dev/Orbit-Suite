import json
import os
import time
import random
from config.configutil import NodeConfig, OrbitDB

orbit_db = OrbitDB()
NODES_FILE = orbit_db.nodedb
PENDING_PROPOSALS_FILE = orbit_db.pendpropdb

def load_nodes():
    if not os.path.exists(NODES_FILE):
        return {}
    with open(NODES_FILE, "r") as f:
        return json.load(f)

def save_nodes(nodes):
    with open(NODES_FILE, "w") as f:
        json.dump(nodes, f, indent=2)

def register_node(node_id, quorum_slice, address):
    nodes = load_nodes()

    node_config = NodeConfig()
    node_config.address = address
    node_config.quorum_slice = quorum_slice
    node_config.trust_score = 1.0
    node_config.uptime_score = 1.0

    nodes[node_id] = node_config.to_dict()
    save_nodes(nodes)

def update_uptime(node_id, is_online=True):
    nodes = load_nodes()
    if node_id in nodes:
        nodes[node_id]["uptime_score"] += 0.05 if is_online else -0.1
        nodes[node_id]["uptime_score"] = max(0.0, min(1.0, nodes[node_id]["uptime_score"]))
        save_nodes(nodes)

def update_trust(node_id, success=True):
    nodes = load_nodes()
    if node_id in nodes:
        delta = 0.05 if success else -0.1
        nodes[node_id]["trust_score"] += delta
        nodes[node_id]["trust_score"] = max(0.0, min(1.0, nodes[node_id]["trust_score"]))
        save_nodes(nodes)

def simulate_quorum_vote(node_id, block_data):
    nodes = load_nodes()
    quorum = nodes.get(node_id, {}).get("quorum_slice", [])
    votes = 0
    for peer in quorum:
        trust = nodes.get(peer, {}).get("trust_score", 0.5)
        result = simulate_peer_vote(peer, block_data, trust)
        update_uptime(peer, result)  # always update uptime
        if result:
            update_trust(peer, +0.01)
            votes += 1
        else:
            update_trust(peer, -0.01)
    return votes >= max(1, len(quorum) // 2)


def simulate_peer_vote(peer_id, block_data, trust_score):
    approval_chance = trust_score * 0.9 + 0.1
    return random.random() < approval_chance

def sign_vote(node_id, block_data):
    return f"signed({node_id})"

def select_next_validator():
    nodes = load_nodes()
    candidates = [(nid, n["trust_score"] * n["uptime_score"]) for nid, n in nodes.items()]
    candidates.sort(key=lambda x: x[1], reverse=True)
    return candidates[0][0] if candidates else None

def relay_pending_proposal(node_id, block_data):
    if not os.path.exists(PENDING_PROPOSALS_FILE):
        proposals = []
    else:
        with open(PENDING_PROPOSALS_FILE, "r") as f:
            proposals = json.load(f)

    proposals.append({
        "node_id": node_id,
        "block_data": block_data,
        "timestamp": time.time()
    })

    with open(PENDING_PROPOSALS_FILE, "w") as f:
        json.dump(proposals, f, indent=2)
    print("[Relay] Proposal added to retry queue.")

def log_node_activity(node_id, action, detail=""):
    with open("node_activity.log", "a") as log:
        log.write(f"{time.time()} | Node {node_id} | {action} | {detail}\n")
