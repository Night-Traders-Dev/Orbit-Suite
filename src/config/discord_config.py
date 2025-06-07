explorer = "http://127.0.0.1:7000"
BOT_OPS_CHANNEL_ID = 1379630873174872197
TOKEN_CREATION_FEE = 250  # ORBIT
EXCHANGE_ADDRESS="ORB.A6C19210F2B823246BA1DCA7"

try:
    with open("secret", "r") as file:
        DISCORD_TOKEN = file.read().strip()
except Exception as e:
    pass
