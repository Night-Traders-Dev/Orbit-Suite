import json
import os
import time
import random
from config.configutil import NodeConfig, OrbitDB
from core.networkutil import send_block_to_node

orbit_db = OrbitDB()
NODES_FILE = orbit_db.nodedb
PENDING_PROPOSALS_FILE = orbit_db.pendpropdb

def log_node_activity(node_id, action, detail=""):
    with open("node_activity.log", "a") as log:
        log.write(f"{time.time()} | Node {node_id} | {action} | {detail}\n")

def load_nodes():
    if not os.path.exists(NODES_FILE):
        return {}
    with open(NODES_FILE, "r") as f:
        nodes = json.load(f)
    return nodes

def save_nodes(nodes):
    with open(NODES_FILE, "w") as f:
        json.dump(nodes, f, indent=2)

def register_node(node_id, quorum_slice, address, port):
    nodes = load_nodes()

    node_config = NodeConfig()
    node_config.address = address
    node_config.port = port
    node_config.quorum_slice = quorum_slice
    node_config.trust_score = 1.0
    node_config.uptime_score = 1.0

    nodes[node_id] = node_config.to_dict()
    save_nodes(nodes)
    log_node_activity(node_id, "register_node", f"Registered with quorum {quorum_slice}")

def update_uptime(node_id, is_online=True):
    nodes = load_nodes()
    if node_id in nodes:
        old_score = nodes[node_id]["uptime_score"]
        nodes[node_id]["uptime_score"] += 0.05 if is_online else -0.1
        nodes[node_id]["uptime_score"] = max(0.0, min(1.0, nodes[node_id]["uptime_score"]))
        save_nodes(nodes)
        log_node_activity(node_id, "update_uptime", f"{old_score:.3f} → {nodes[node_id]['uptime_score']:.3f}")

def update_trust(node_id, success=True):
    nodes = load_nodes()
    if node_id in nodes:
        old_score = nodes[node_id]["trust_score"]
        delta = 0.05 if success else -0.1
        nodes[node_id]["trust_score"] += delta
        nodes[node_id]["trust_score"] = max(0.0, min(1.0, nodes[node_id]["trust_score"]))
        save_nodes(nodes)
        log_node_activity(node_id, "update_trust", f"{old_score:.3f} → {nodes[node_id]['trust_score']:.3f}")

def simulate_quorum_vote(node_id, block_data):
    nodes = load_nodes()
    quorum = nodes.get(node_id, {}).get("quorum_slice", [])
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

def simulate_peer_vote(peer_id, block_data, trust_score):
    approval_chance = trust_score * 0.9 + 0.1
    result = random.random() < approval_chance
    log_node_activity(peer_id, "simulate_peer_vote", f"Trust {trust_score:.2f} → {'approve' if result else 'reject'}")
    return result

def sign_vote(node_id, block_data):
    log_node_activity(node_id, "sign_vote", f"Signed block {block_data}")
    return f"signed({node_id})"

def select_next_validator():
    nodes = load_nodes()
    candidates = [(nid, n["trust_score"] * n["uptime_score"]) for nid, n in nodes.items()]
    candidates.sort(key=lambda x: x[1], reverse=True)
    selected = candidates[0][0] if candidates else None
    if selected:
        log_node_activity(selected, "select_next_validator", "Selected as next validator")
    return selected

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

    log_node_activity(node_id, "relay_pending_proposal", f"Block {block_data} queued")
    print("[Relay] Proposal added to retry queue.")


def relay_pending_proposal_new(node_id, block_data):
    nodes = load_nodes()
    quorum = nodes.get(node_id, {}).get("quorum_slice", [])

    for peer_id in quorum:
        peer_node = nodes.get(peer_id)
        if peer_node:
            address = peer_node.get("address")
            success = send_block_to_node(address, block_data)
            log_node_activity(node_id, "relay", f"Sent block to {peer_id} ({'✓' if success else 'x'})")
