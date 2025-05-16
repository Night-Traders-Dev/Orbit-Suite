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

