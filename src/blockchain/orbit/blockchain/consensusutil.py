import time
from core.ioutil import fetch_chain, save_chain, load_nodes
from core.logutil import log_node_activity
from blockchain.voteutil import record_vote, get_votes, has_quorum
from config.configutil import OrbitDB

db = OrbitDB()
CONSENSUS_STATES = ["nominate", "vote", "accept", "confirm"]

def nominate_block(node_id, block_data):
    block_hash = block_data["hash"]
    log_node_activity(node_id, "nominate", f"Nominating block {block_hash}")
    return record_vote(node_id, block_hash, "nominate")

def vote_block(node_id, block_data):
    block_hash = block_data["hash"]
    log_node_activity(node_id, "vote", f"Voting for block {block_hash}")
    return record_vote(node_id, block_hash, "vote")

def accept_block(node_id, block_data):
    block_hash = block_data["hash"]
    log_node_activity(node_id, "accept", f"Accepting block {block_hash}")
    return record_vote(node_id, block_hash, "accept")

def confirm_block(node_id, block_data):
    block_hash = block_data["hash"]
    log_node_activity(node_id, "confirm", f"Confirming block {block_hash}")
    return record_vote(node_id, block_hash, "confirm")

def consensus_progression(node_id, block_data):
    nodes = load_nodes()
    quorum = nodes.get(node_id, {}).get("quorum_slice", [])
    block_hash = block_data["hash"]

    if not has_quorum(block_hash, quorum, "nominate"):
        nominate_block(node_id, block_data)
        return "nominated"

    if not has_quorum(block_hash, quorum, "vote"):
        vote_block(node_id, block_data)
        return "voted"

    if not has_quorum(block_hash, quorum, "accept"):
        accept_block(node_id, block_data)
        return "accepted"

    if not has_quorum(block_hash, quorum, "confirm"):
        confirm_block(node_id, block_data)
        return "confirmed"

    # Final confirmation: add block to chain if not already added
    chain = fetch_chain()
    if not any(b["hash"] == block_hash for b in chain):
        chain.append(block_data)
        save_chain(chain)
        log_node_activity(node_id, "finalize", f"Block {block_hash} added to chain")
        return "finalized"

    return "already_finalized"

def get_consensus_state(block_hash, quorum_slice):
    for state in reversed(CONSENSUS_STATES):
        if has_quorum(block_hash, quorum_slice, state):
            return state
    return "pending"
