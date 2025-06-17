import asyncio
from core.orderutil import all_tokens_stats
from core.cacheutil import get_cached, set_cached, clear_cache


cached = get_cached("all_tokens_stats")
if cached:
    tokens, metrics = cached
else:
    tokens, wallets, metrics = asyncio.run(all_tokens_stats("FUEL"))
for address in wallets:
    if wallets[address]["amount"] >= 0:
        print(f"{address}: {wallets[address]['amount']:,}")
