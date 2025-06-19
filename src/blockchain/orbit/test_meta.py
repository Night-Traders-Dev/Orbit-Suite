import asyncio
from core.walletutil import get_wallet_stats


address = "ORB.B77AC60F52529B834E4DAF21"
tokens = ["CORAL", "FIG", "FUEL"]
for token in tokens:
    response = asyncio.run(get_wallet_stats(token))
    for wallet in response:
        if address in wallet:
            print(f"Token:{token} - {wallet}")
