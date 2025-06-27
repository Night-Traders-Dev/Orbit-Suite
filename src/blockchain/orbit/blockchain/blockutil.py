import time
import random

from blockchain.orbitutil import (
    update_trust, update_uptime, save_nodes, load_nodes, simulate_peer_vote,
    sign_vote, relay_pending_proposal, simulate_quorum_vote, select_next_validator,
    log_node_activity
)
from blockchain.voteutil import record_vote
from config.configutil import NodeConfig, TXConfig
from core.ioutil import load_chain, save_chain, fetch_chain, load_users, save_users
from core.hashutil import generate_merkle_root, calculate_hash
from core.networkutil import send_block_to_node


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
        genesis_block.index, genesis_block.previous_hash, genesis_block.timestamp,
        [], genesis_block.validator, genesis_block.merkle_root,
        genesis_block.nonce, genesis_block.metadata
    )
    return genesis_block.to_dict()


def get_last_block():
    try:
        chain = fetch_chain()
        if isinstance(chain, list) and len(chain) > 0:
            return chain[-1]
        else:
            print("Chain is empty or invalid format.")
    except Exception as e:
        print(f"Error fetching last block: {e}")
    return None

def propose_block(node_id, block_data, timeout=5):
    if not validate_block(block_data, node_id):
        log_node_activity(node_id, "Propose Block", "Block could not be validated.")
        return False

    nodes = load_nodes()
    if node_id not in nodes:
        log_node_activity(node_id, "Propose Block", "Node is not registered.")
        return False

    proposer = NodeConfig.from_dict(nodes[node_id])
    quorum_slice = proposer.quorum_slice

    votes = {node_id}
    signatures = {node_id: sign_vote(node_id, block_data)}
    start_time = time.time()

    for peer_id in quorum_slice:
        if time.time() - start_time > timeout:
            break

        peer_raw = nodes.get(peer_id)
        if not peer_raw:
            log_node_activity(node_id, "Propose Block", f"Peer {peer_id} not found.")
            continue

        peer = NodeConfig.from_dict(peer_raw)
        ping_success = random.random() < peer.uptime_score

        if ping_success and simulate_quorum_vote(peer_id, block_data):
            votes.add(peer_id)
            signatures[peer_id] = sign_vote(peer_id, block_data)

            # Update uptime with EMA and trust increment
            peer.uptime_score = 0.9 * peer.uptime_score + 0.1 * 1.0
            peer.trust_score = min(peer.trust_score + 0.02, 1.0)

        else:
            # Apply decay for non-participation or failed ping
            peer.uptime_score = 0.98 * peer.uptime_score
            peer.trust_score = max(peer.trust_score - 0.01, 0.0)

        nodes[peer_id] = peer.to_dict()

    save_nodes(nodes)
    required_votes = (len(quorum_slice) // 2) + 1

    if len(votes) >= required_votes:
        log_node_activity(node_id, "Propose Block", f"Consensus passed with {len(votes)} votes.")
        return True
    else:
        log_node_activity(node_id, "Propose Block", f"Consensus failed: {len(votes)} votes (need {required_votes}).")
        relay_pending_proposal(node_id, block_data)
        return False

def receive_block(block):
    chain = fetch_chain()
    if not chain:
        log_node_activity("unknown", "Receive Block", "Chain not loaded")
        return False

    last_block = chain[-1]

    if block["index"] != last_block["index"] + 1:
        log_node_activity(block.get("validator", "unknown"), "Receive Block", "Rejected: Invalid index.")
        return False

    block_obj = TXConfig.Block.from_dict(block)
    if validate_block(block_obj, block.get("validator", "unknown")):
        chain.append(block)
        save_chain(chain)
        log_node_activity(block["validator"], "Receive Block", f"Block {block['index']} accepted.")
        return True
    else:
        log_node_activity(block.get("validator", "unknown"), "Receive Block", "Validation failed.")
        return False


def broadcast_block(block, sender_id=None):
    nodes = load_nodes()
    for node_id, node_data in nodes.items():
        if sender_id != node_id:
            node = NodeConfig.from_dict(node_data)
            if node.address and node.port:
                try:
                    url = f"http://127.0.0.1:{node.port}"
                    send_block_to_node(url, block)
                    log_node_activity(sender_id, "Broadcast Block", f"Block sent to {url}")
                except Exception as e:
                    log_node_activity(sender_id, "Broadcast Block", f"Failed to send to {node_id}: {e}")


def add_block(transactions, node_id):
    chain = fetch_chain()
    last_block = chain[-1]
    tx_objs = [TXConfig.Transaction.from_dict(tx) for tx in transactions]
    tx_dicts = [tx.to_dict() for tx in tx_objs]
    merkle_root = generate_merkle_root(tx_dicts)

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
        metadata={"version": "1.0"}
    )

    new_block.hash = calculate_hash(
        new_block.index, new_block.previous_hash, new_block.timestamp,
        tx_dicts, new_block.validator, new_block.merkle_root,
        new_block.nonce, new_block.metadata
    )

    if propose_block(new_block.validator, new_block):
        users = load_users()
        for tx in new_block.transactions:
            tx_data = tx.to_dict()
            sender, recipient, amount = tx_data["sender"], tx_data["recipient"], tx_data.get("amount", 0)

            if sender not in users or recipient not in users:
                log_node_activity(node_id, "Add Block", f"Skipped: Unknown user {sender} or {recipient}")
                continue

            if users[sender]["balance"] >= amount:
                users[sender]["balance"] -= amount
                users[recipient]["balance"] += amount
            else:
                log_node_activity(node_id, "Add Block", f"Failed: {sender} has insufficient balance.")
                continue

            if sender == recipient:
                tx_data.pop()
                record_vote(new_block.validator, new_block.hash, "nominate")

        save_users(users)
        save_chain(chain + [new_block.to_dict()])
        log_node_activity(node_id, "Add Block", f"Block {new_block.index} added.")
        return True
    else:
        log_node_activity(node_id, "Add Block", "Rejected by consensus.")
        return False


def validate_block(block, node_id):
    chain = fetch_chain()
    if not chain:
        log_node_activity(node_id, "Validate Block", "Blockchain couldn't be loaded")
        return False

    last_block = get_last_block()
    if not last_block:
        return False

    if last_block["index"] == 0:
        return True

    prev_hash = calculate_hash(
        last_block["index"],
        last_block["previous_hash"],
        last_block["timestamp"],
        last_block["transactions"],
        last_block["validator"],
        last_block["merkle_root"],
        last_block["nonce"],
        last_block["metadata"]
    )

    block = block.to_dict()
    if block["previous_hash"] != prev_hash:
        log_node_activity(node_id, "Validate Block", f"Block {block['index']} not valid: incorrect previous_hash")
        return False

    log_node_activity(node_id, "Validate Block", f"Block {block['index']} is valid")
    return True


def is_chain_valid():
    chain = fetch_chain()
    for i in range(1, len(chain)):
        current, previous = chain[i], chain[i - 1]
        recalculated = calculate_hash(
            current["index"], current["previous_hash"], current["timestamp"],
            current["transactions"], current.get("validator", ""),
            current.get("merkle_root", ""), current.get("nonce", 0),
            current.get("metadata", {})
        )
        if current["hash"] != recalculated or current["previous_hash"] != previous["hash"]:
            return False
    return True
