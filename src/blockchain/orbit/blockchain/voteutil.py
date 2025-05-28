import time
from config.configutil import OrbitDB
from core.logutil import log_node_activity
from core.ioutil import fetch_chain, save_chain

db = OrbitDB()
VOTE_TYPES = ["nominate", "vote", "accept", "confirm"]

def record_vote(node_id, block_hash, state):
    from blockchain.tokenutil import send_orbit

    if state not in VOTE_TYPES:
        return False

    vote_tx = {
        "type": {
            "vote": {
                "block_hash": block_hash,
                "state": state,
                "voter": node_id,
                "timestamp": int(time.time())
            }
        }
    }

    # This transaction will be stored as a zero-value reward, only logged.
    send_orbit("nodefeecollector", "lockup_rewards", 0.1, vote_tx)
    log_node_activity(node_id, state, f"{state.title()} vote for block {block_hash}")
    return True

def get_votes(block_hash, state=None):
    chain = fetch_chain()
    result = []

    for block in chain:
        for tx in block.get("transactions", []):
            vote = tx.get("type", {}).get("vote")
            if vote and vote.get("block_hash") == block_hash:
                if state is None or vote.get("state") == state:
                    result.append(vote)

    return result

def has_quorum(block_hash, quorum_slice, state):
    votes = get_votes(block_hash, state)
    voting_nodes = {vote["voter"] for vote in votes}
    approvals = sum(1 for node in quorum_slice if node in voting_nodes)
    return approvals >= (len(quorum_slice) // 2 + 1)
