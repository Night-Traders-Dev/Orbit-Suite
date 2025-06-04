explorer = "http://127.0.0.1:7000"

with open("secret", "r") as file:
    DISCORD_TOKEN = file.read().strip()
