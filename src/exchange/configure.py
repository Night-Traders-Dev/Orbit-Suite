from core.hashutil import generate_orbit_address
explorer = "http://127.0.0.1:7000"
EXCHANGE_ADDRESS=generate_orbit_address(1379645991782846608)

with open("secret", "r") as file:
    DISCORD_TOKEN = file.read().strip()
