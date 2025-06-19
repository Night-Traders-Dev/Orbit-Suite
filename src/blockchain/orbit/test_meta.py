import asyncio
from core.walletutil import get_wallet_stats
import re


address = "ORB.B77AC60F52529B834E4DAF21"
tokens = ["CORAL", "FIG", "FUEL"]
for token in tokens:
    response = asyncio.run(get_wallet_stats(token))
    for wallet in response:
        if address in wallet:
            match = re.search(r': ([\d,\.]+)\(([\d,\.]+) Orbit\)', wallet)
            if match:
                quantity_str = match.group(1).replace(",", "")
                orbit_value_str = match.group(2).replace(",", "")
                quantity = float(quantity_str)
                orbit_value = float(orbit_value_str)
#                print(f"Token:{token} - {wallet}")
                print(f"{quantity}:{orbit_value}")
