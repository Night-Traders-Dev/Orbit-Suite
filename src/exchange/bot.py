import discord
import asyncio
import uuid
import time
import json
import os

from discord.ext import commands
from core.tx_util.tx_types import TXExchange
from core.tx_util.tx_validator import TXValidator
from config import DISCORD_TOKEN

# Load config
BOT_OPS_CHANNEL_ID = 1379630873174872197
EXCHANGE_ADDR = "orbitxchg123"

intents = discord.Intents.all()
intents.messages = True
intents.guilds = True

bot = commands.Bot(command_prefix="!", intents=intents)

# Helper to parse exchange command from UI bot

def parse_exchange_command(message_content):
    try:
        if message_content.startswith("[ExchangeRequest] BUY"):
            parts = message_content.split()
            symbol = parts[2]
            amount = float(parts[3])
            buyer = parts[4]
            return {
                "action": "buy",
                "symbol": symbol,
                "amount": amount,
                "buyer": buyer
            }
        # Future: support SELL, CANCEL, etc.
        else:
            return None
    except Exception as e:
        print(f"Failed to parse command: {e}")
        return None

# Exchange logic

def create_buy_order(symbol, amount, buyer_addr):
    tx = TXExchange.buy_token(
        order_id=str(uuid.uuid4()),
        token_id="0001",  # TODO: get_token_id(symbol) dynamically
        symbol=symbol,
        amount=amount,
        buyer_address=buyer_addr,
        exchange_fee=0.01
    )
    validator = TXValidator(tx)
    valid, msg = validator.validate()
    if valid:
        return True, tx
    else:
        return False, msg

@bot.event
async def on_ready():
    print(f"[✓] Orbit Exchange Bot is online as {bot.user.name}")
    channel = bot.get_channel(BOT_OPS_CHANNEL_ID)
    if channel:
        await channel.send("[ExchangeBot] Ready and listening for orders.")

@bot.event
async def on_message(message):
    # Ignore self messages
    if message.author == bot.user:
        return

    # Only listen to messages from bot-ops channel
    if message.channel.id != BOT_OPS_CHANNEL_ID:
        return

    command = parse_exchange_command(message.content)
    if command:
        if command["action"] == "buy":
            success, result = create_buy_order(command["symbol"], command["amount"], command["buyer"])
            if success:
                tx_json = json.dumps(result, indent=2)
                await message.channel.send(f"[ExchangeBot] Buy order created and validated:\n```json\n{tx_json}\n```")
            else:
                await message.channel.send(f"[ExchangeBot] Order failed validation: {result}")
    else:
        await message.channel.send("[ExchangeBot] Unrecognized or malformed command.")

# Run bot
if __name__ == "__main__":
    bot.run(DISCORD_TOKEN)
