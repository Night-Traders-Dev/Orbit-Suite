import time
from config.configutil import OrbitDB
from core.logutil import log_node_activity
from core.ioutil import load_chain, save_chain

db = OrbitDB()
VOTE_TYPES = ["nominate", "vote", "accept", "confirm"]

def record_vote(node_id, block_hash, state):
    if state not in VOTE_TYPES:
        return False

    vote_tx = {
        "type": "vote",
        "block_hash": block_hash,
        "state": state,
        "voter": node_id,
        "timestamp": int(time.time())
    }

    chain = load_chain()
    if not chain:
        return False

    # Append to the most recent block’s votes or create a new vote block
    latest_block = chain[-1]
    if "transactions" not in latest_block:
        latest_block["transactions"] = []

    latest_block["transactions"].append(vote_tx)
    save_chain(chain)
    log_node_activity(node_id, state, f"{state.title()} vote for block {block_hash}")
    return True

def get_votes(block_hash, state=None):
    chain = load_chain()
    result = []
    for block in chain:
        for tx in block.get("transactions", []):
            if tx.get("type") == "vote" and tx.get("block_hash") == block_hash:
                if state is None or tx.get("state") == state:
                    result.append(tx)
    return result

def has_quorum(block_hash, quorum_slice, state):
    votes = get_votes(block_hash, state)
    voting_nodes = {tx["voter"] for tx in votes}
    approvals = sum(1 for node in quorum_slice if node in voting_nodes)
    return approvals >= (len(quorum_slice) // 2 + 1)
