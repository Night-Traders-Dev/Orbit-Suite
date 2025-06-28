# fastapi_node.py

import time
from typing import Any, Dict, Optional

from fastapi import FastAPI, HTTPException
from pydantic import BaseModel, Field

from core.ioutil import load_chain, load_nodes
from blockchain.tokenutil import send_orbit

app = FastAPI(title="Orbit Explorer – Node APIs")

# In-memory stores (just like your Flask globals)
active_node_registry: Dict[str, Dict[str, Any]] = {}
node_validation_proofs: Dict[str, Dict[str, Any]] = {}


def is_thousand_milestone(chain_length: int) -> bool:
    return chain_length % 1000 == 0 and chain_length != 0



class NodeProfileOut(BaseModel):
    node_id: str
    trust: float
    uptime: float
    total_blocks: int
    total_orbit: float
    avg_block_size: float


@app.get("/node/{node_id}", response_model=NodeProfileOut)
def get_node_profile(node_id: str):
    chain = load_chain()
    node_data = load_nodes()
    node_blocks = [blk for blk in chain if blk.get("validator") == node_id]

    if not node_blocks and node_id not in node_data:
        raise HTTPException(404, f"Node {node_id} not found")

    # Fill placeholder if never registered in NodeRegistry
    if node_id not in node_data:
        node_data[node_id] = {
            "id": node_id, "trust": 0.0, "uptime": 0.0,
            "address": "Unknown", "host": "Unknown", "port": "N/A",
            "last_seen": None, "users": []
        }

    info = node_data[node_id]
    total_blocks = len(node_blocks)

    # Sum all orbit fees from gas, lockups, mining payouts
    total_orbit = 0.0
    for blk in node_blocks:
        for tx in blk.get("transactions", []):
            note = tx.get("note", {}).get("type", {})
            if note.get("gas"):
                total_orbit += note["gas"].get("fee", 0.0)
            if note.get("lockup"):
                total_orbit += note["lockup"].get("amount", 0.0)
            if tx.get("sender") == "mining":
                total_orbit += tx.get("amount", 0.0)
            # fallback
            if not note:
                total_orbit += tx.get("amount", 0.0)

    avg_block_size = (
        sum(len(blk.get("transactions", [])) for blk in node_blocks) / total_blocks
        if total_blocks else 0.0
    )

    return NodeProfileOut(
        node_id=node_id,
        trust=round(info.get("trust", 0.0), 3),
        uptime=round(info.get("uptime", 0.0), 3),
        total_blocks=total_blocks,
        total_orbit=round(total_orbit, 6),
        avg_block_size=round(avg_block_size, 2),
    )



class NodePingRequest(BaseModel):
    id: str
    address: Optional[str]         = None
    user: Optional[str]            = None
    nodefeebalance: float = Field(0.0, ge=0.0)

@app.post("/node_ping")
def node_ping(req: NodePingRequest):
    """
    Register heartbeat from a node.
    On every 1000th block, auto–distribute node fees.
    """
    now = time.time()
    active_node_registry[req.id] = {
        "node": req.dict(), "last_seen": now
    }

    chain_len = len(load_chain())
    if is_thousand_milestone(chain_len):
        # Distribute 90% to user, 8% mining, 2% burn
        for nid, data in active_node_registry.items():
            node = data["node"]
            bal = node.get("nodefeebalance", 0.0)
            user_cut = bal * 0.9
            mine_cut = bal * 0.08
            burn_cut = bal * 0.02

            order = {
                "sender": "ORB.3C0738F00DE16991DDD5B506",
                "note": {"type": {"reward": {
                    "user_reward": user_cut,
                    "mining_reward": mine_cut,
                    "burn_amount": burn_cut
                }}}
            }
            # send_orbit(sender, recipient, amount, order)
            send_orbit(order["sender"], node["user"], user_cut, order)
            send_orbit(order["sender"], "burn",       burn_cut, order)
            send_orbit(order["sender"], "mining",     mine_cut, order)

    return {"status": "registered", "node": req}



@app.get("/active_nodes")
def active_nodes():
    """
    List nodes seen in the last 120s.
    """
    cutoff = time.time() - 120
    fresh = {
        nid: info
        for nid, info in active_node_registry.items()
        if info["last_seen"] > cutoff
    }
    return fresh



class NodeProofRequest(BaseModel):
    node_id: str
    latest_hash: str
    proof_hash: str

@app.post("/node_proof")
def node_proof(req: NodeProofRequest):
    node_validation_proofs[req.node_id] = {
        "timestamp": time.time(),
        "latest_hash": req.latest_hash,
        "proof_hash": req.proof_hash
    }
    return {
        "status": "success",
        "message": f"Proof received from {req.node_id}"
    }



@app.post("/receive_block")
def receive_block(block: Dict[str, Any]):
    # TODO: hook into your validation/append logic
    print(f"Received block proposal: {block.get('index')}")
    return {"status": "ok"}