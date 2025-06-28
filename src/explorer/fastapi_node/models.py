from typing import Any, Dict, List, Optional
from pydantic import BaseModel, Field

class NodeInfo(BaseModel):
    id: str
    user: Optional[str]
    address: Optional[str]
    nodefeebalance: float = Field(0.0, ge=0.0)
    # ... any other registration fields

class NodeProfileOut(BaseModel):
    node_id: str
    trust: float
    uptime: float
    total_blocks: int
    total_orbit: float
    avg_block_size: float

class NodePingIn(BaseModel):
    id: str
    user: Optional[str]
    address: Optional[str]
    nodefeebalance: float = Field(0.0, ge=0.0)

class NodeProofIn(BaseModel):
    node_id: str
    latest_hash: str
    proof_hash: str

class BlockProposal(BaseModel):
    index: int
    previous_hash: str
    transactions: List[Dict[str, Any]]
    # ... your block schema