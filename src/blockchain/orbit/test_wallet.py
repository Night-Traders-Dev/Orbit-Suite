import asyncio
from core.orderutil import all_tokens_stats

# All tokens
#tokens, wallets, metrics = asyncio.run(all_tokens_stats())

# Specific token
tokens, wallets, metrics = asyncio.run(all_tokens_stats("FUEL"))
for address in wallets:
    if wallets[address]["amount"] >= 0:
        print(f"{address}: {wallets[address]['amount']:,}")
# Multiple specific tokens
#tokens, wallets, metrics = asyncio.run(all_tokens_stats(["CORAL", "FIG"]))
