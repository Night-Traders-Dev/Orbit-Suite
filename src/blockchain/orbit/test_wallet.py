import asyncio
from core.orderutil import all_tokens_stats

tokens, wallets = asyncio.run(all_tokens_stats())
for address in wallets:
    if wallets[address]["amount"] >= 0:
        print(f"{address}: {wallets[address]['amount']:,}")
