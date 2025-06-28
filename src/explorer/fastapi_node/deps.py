import time
from functools import lru_cache
from cachetools import TTLCache, cached
from fastapi import Depends

from .config import settings
from .services import load_chain, load_nodes

# In-memory TTL cache for active nodes
heartbeat_cache = TTLCache(maxsize=10000, ttl=settings.heartbeat_ttl)

def get_chain():
    return load_chain()

def get_node_registry():
    return load_nodes()

@cached(heartbeat_cache)
def record_heartbeat(node_id: str, payload: dict):
    """
    Store or refresh a node's heartbeat.
    """
    timestamp = time.time()
    return {"node": payload, "last_seen": timestamp}

def get_active_nodes():
    """
    Return fresh heartbeats.
    """
    now = time.time()
    cutoff = now - settings.heartbeat_ttl
    return {
        nid: info
        for nid, info in heartbeat_cache.items()
        if info["last_seen"] > cutoff
    }

def is_milestone(chain_length: int):
    return chain_length % settings.milestone_interval == 0 and chain_length != 0