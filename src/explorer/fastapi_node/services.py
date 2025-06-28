from typing import Dict, Any, List
from .models import NodeInfo
from core.ioutil import load_chain as _load_chain
from core.ioutil import load_nodes as _load_nodes
from blockchain.tokenutil import send_orbit

def load_chain() -> List[Dict[str, Any]]:
    return _load_chain()

def load_nodes() -> Dict[str, NodeInfo]:
    raw = _load_nodes()
    return {nid: NodeInfo(**info) for nid, info in raw.items()}

def distribute_fees(node_infos: Dict[str, Dict[str, Any]], collector: str):
    """
    90% to node.user, 8% to mining, 2% to burn.
    """
    for nid, entry in node_infos.items():
        node = entry["node"]
        bal = node.nodefeebalance
        if bal <= 0:
            continue
        user_cut  = bal * 0.9
        mine_cut  = bal * 0.08
        burn_cut  = bal * 0.02

        order_meta = {
            "note": {"type": {"reward": {
                "user_reward": user_cut,
                "mining_reward": mine_cut,
                "burn_amount": burn_cut
            }}}
        }
        # Fire‐and‐forget
        send_orbit(collector, node.user,  user_cut,  order_meta)
        send_orbit(collector, "mining",    mine_cut,  order_meta)
        send_orbit(collector, "burn",      burn_cut,  order_meta)