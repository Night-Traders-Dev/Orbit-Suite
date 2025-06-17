import time

# In-memory cache storage
CACHE = {
    "all_tokens": {"data": None, "ts": 0},
    "token_stats": {},  # symbol -> {data, ts}
}

CACHE_TTL = 30  # seconds


def get_cached(key, subkey=None):
    now = time.time()
    if subkey:
        entry = CACHE.get(key, {}).get(subkey)
    else:
        entry = CACHE.get(key)

    if entry and entry["data"] and (now - entry["ts"] < CACHE_TTL):
        return entry["data"]
    return None


def set_cached(key, data, subkey=None):
    now = time.time()
    entry = {"data": data, "ts": now}
    if subkey:
        if key not in CACHE:
            CACHE[key] = {}
        CACHE[key][subkey] = entry
    else:
        CACHE[key] = entry


def clear_cache():
    for key in CACHE:
        if isinstance(CACHE[key], dict):
            for sub in CACHE[key]:
                CACHE[key][sub] = {"data": None, "ts": 0}
        else:
            CACHE[key] = {"data": None, "ts": 0}
