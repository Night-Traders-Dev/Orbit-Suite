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

def simulate_peer_vote(peer_id, block_data, trust_score):
    approval_chance = trust_score * 0.9 + 0.1
    return random.random() < approval_chance

def sign_vote(node_id, block_data):
    return f"signed({node_id})"

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

def propose_block(node_id, block_data, timeout=5):
    nodes = load_nodes()

    if node_id not in nodes:
        print(f"Node {node_id} is not registered.")
        return False

    proposer_config = NodeConfig.from_dict(nodes[node_id])
    quorum_slice = proposer_config.quorum_slice

    print(f"[Propose] Node {node_id} proposing block to quorum: {quorum_slice}")

    votes = {node_id}
    signatures = {node_id: sign_vote(node_id, block_data)}
    start_time = time.time()

    for peer_id in quorum_slice:
        if time.time() - start_time > timeout:
            print("[Propose] Timeout during quorum vote collection.")
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
            if simulate_peer_vote(peer_id, block_data, trust_score):
                votes.add(peer_id)
                signatures[peer_id] = sign_vote(peer_id, block_data)
                print(f"[Propose] Vote received from {peer_id} (trust: {trust_score:.2f})")
                peer_data["trust_score"] = min(peer_data.get("trust_score", 0.5) + ADJUST_RATE, 1.0)
                peer_data["uptime_score"] = min(peer_data.get("uptime_score", 0.5) + ADJUST_RATE, 1.0)
            else:
                print(f"[Propose] {peer_id} voted NO (trust: {trust_score:.2f})")

                peer_data["trust_score"] = max(peer_data.get("trust_score", 0.5) - ADJUST_RATE, 0.0)
        else:
            print(f"[Propose] {peer_id} unavailable (uptime: {uptime_score:.2f})")

            peer_data["uptime_score"] = max(peer_data.get("uptime_score", 0.5) - ADJUST_RATE, 0.0)

        nodes[peer_id] = peer_data

    required_votes = (len(quorum_slice) // 2) + 1

    if len(votes) >= required_votes:
        print(f"[Propose] Consensus achieved: {len(votes)} votes (required {required_votes}).")
        print(f"[Signatures] {signatures}")
        save_nodes(nodes)
        return True
    else:
        print(f"[Propose] Consensus failed: {len(votes)} votes (required {required_votes}).")
        relay_pending_proposal(node_id, block_data)
        save_nodes(nodes)
        return False
