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

# Configs
BOT_OPS_CHANNEL_ID = 1379630873174872197
EXCHANGE_ADDR = "orbitxchg123"
TX_LOG_PATH = "exchange_tx_log.json"

intents = discord.Intents.all()
intents.messages = True
intents.guilds = True

bot = commands.Bot(command_prefix="!", intents=intents)

# --- Command Parser ---
def parse_exchange_command(message_content):
    try:
        parts = message_content.strip().split()
        if parts[0] != "[ExchangeRequest]":
            return None

        action = parts[1].lower()
        symbol = parts[2]
        amount = float(parts[3])
        addr = parts[4]

        return {
            "action": action,
            "symbol": symbol,
            "amount": amount,
            "address": addr
        }
    except Exception as e:
        print(f"Failed to parse command: {e}")
        return None

# --- Exchange Logic ---
def create_buy_order(symbol, amount, buyer_addr):
    tx = TXExchange.buy_token(
        order_id=str(uuid.uuid4()),
        token_id="0001",  # TODO: dynamic token ID lookup
        symbol=symbol,
        amount=amount,
        buyer_address=buyer_addr,
        exchange_fee=0.01
    )
    return validate_and_log(tx)

def create_sell_order(symbol, amount, seller_addr):
    tx = TXExchange.sell_token(
        order_id=str(uuid.uuid4()),
        token_id="0001",  # TODO: dynamic token ID lookup
        symbol=symbol,
        amount=amount,
        seller_address=seller_addr,
        exchange_fee=0.01
    )
    return validate_and_log(tx)

def create_cancel_order(order_id, sender_addr):
    tx = TXExchange.cancel_order(
        order_id=order_id,
        sender_address=sender_addr
    )
    return validate_and_log(tx)

def validate_and_log(tx):
    validator = TXValidator(tx)
    valid, msg = validator.validate()
    if valid:
        # Log to file
        log_transaction(tx)
        # Broadcast (stub)
        broadcast_transaction(tx)
        return True, tx
    else:
        return False, msg

def log_transaction(tx):
    if not os.path.exists(TX_LOG_PATH):
        with open(TX_LOG_PATH, "w") as f:
            json.dump([], f)

    with open(TX_LOG_PATH, "r+") as f:
        data = json.load(f)
        data.append(tx)
        f.seek(0)
        json.dump(data, f, indent=2)

def broadcast_transaction(tx):
    # TODO: Replace this with actual Orbit Blockchain broadcast logic
    print("[✓] Broadcasting transaction to Orbit network:")
    print(json.dumps(tx, indent=2))

# --- Discord Events ---
@bot.event
async def on_ready():
    print(f"[✓] Orbit Exchange Bot is online as {bot.user.name}")
    channel = bot.get_channel(BOT_OPS_CHANNEL_ID)
    if channel:
        await channel.send("[ExchangeBot] Ready and listening for orders.")

@bot.event
async def on_message(message):
    if message.author == bot.user:
        return

    if message.channel.id != BOT_OPS_CHANNEL_ID:
        return

    command = parse_exchange_command(message.content)
    if not command:
        await message.channel.send("[ExchangeBot] Unrecognized or malformed command.")
        return

    action = command["action"]
    symbol = command["symbol"]
    amount = command["amount"]
    address = command["address"]

    if action == "buy":
        success, result = create_buy_order(symbol, amount, address)
    elif action == "sell":
        success, result = create_sell_order(symbol, amount, address)
    elif action == "cancel":
        success, result = create_cancel_order(symbol, address)  # symbol holds order_id in this case
    else:
        await message.channel.send("[ExchangeBot] Unknown action.")
        return

    if success:
        await message.channel.send(f"[ExchangeBot] Order processed:\n```json\n{json.dumps(result, indent=2)}\n```")
    else:
        await message.channel.send(f"[ExchangeBot] Order failed validation: {result}")

# --- Start Bot ---
if __name__ == "__main__":
    bot.run(DISCORD_TOKEN)
