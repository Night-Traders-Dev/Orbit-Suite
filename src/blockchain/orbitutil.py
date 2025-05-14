import json
import os
from configutil import NodeConfig

NODES_FILE = "data/nodes.json"

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

    # Create a NodeConfig instance for structured data
    node_config = NodeConfig(
        quorum_slice=quorum_slice,
        address=address
    )

    nodes[node_id] = node_config.to_dict()  # Save the node configuration as a dictionary
    save_nodes(nodes)

def propose_block(node_id, block_data):
    nodes = load_nodes()

    if node_id not in nodes:
        print(f"Node {node_id} is not registered.")
        return False

    node_config = NodeConfig.from_dict(nodes[node_id])

    quorum_slice = node_config.quorum_slice
    votes = {node_id}

    for peer in quorum_slice:
        if peer in nodes:
            votes.add(peer)

    required_votes = (len(quorum_slice) // 2) + 1
    if len(votes) >= required_votes:
        print("Consensus reached. Block accepted.")
        return True
    else:
        print(f"Consensus failed. Required: {required_votes}, Got: {len(votes)}.")
        return False
