# orbitutil.py

import json
import os

NODES_FILE = "data/nodes.json"

def load_nodes():
    if not os.path.exists(NODES_FILE):
        return {}
    with open(NODES_FILE, "r") as f:
        return json.load(f)

def save_nodes(nodes):
    with open(NODES_FILE, "w") as f:
        json.dump(nodes, f, indent=2)

def register_node(node_id, quorum_slice):
    nodes = load_nodes()
    nodes[node_id] = {
        "quorum_slice": quorum_slice
    }
    save_nodes(nodes)

def propose_block(node_id, block_data):
    nodes = load_nodes()
    if node_id not in nodes:
        print(f"Node {node_id} is not registered.")
        return False

    quorum_slice = nodes[node_id]["quorum_slice"]
    votes = {node_id}

    for peer in quorum_slice:
        if peer in nodes:
            votes.add(peer)

    if len(votes) >= (len(quorum_slice) // 2 + 1):
        print("Consensus reached. Block accepted.")
        return True
    else:
        print("Consensus failed. Not enough trusted nodes agreed.")
        return False
