import json
from parser.parser import parse_exchange_command
from logic.logic import (
    cancel_order,
    create_token,
    deposit,
    withdrawal,
    swap_token,
    buy_token_from_exchange,
    trade_token_on_exchange
)
from bot.api import get_user_address

EXCHANGE_UID = 1379645991782846608
BOT_OPS_CHANNEL_ID = [1379630873174872197]  # Add more channel IDs as needed

def register_events(bot):
    @bot.event
    async def on_ready():
        address = await get_user_address(bot.user.id)
        print(f"[✓] Orbit Exchange Bot is online as {address}")
        for channel_id in BOT_OPS_CHANNEL_ID:
            channel = bot.get_channel(channel_id)
            if channel:
                await channel.send("[ExchangeBot] Ready and listening for orders.")
            else:
                print(f"[!] Could not find channel with ID: {channel_id}")

    @bot.event
    async def on_message(message):
        # Ignore messages from the bot itself
        if message.author == bot.user:
            return

        # Check if the message is from one of the allowed channels
        if message.channel.id not in BOT_OPS_CHANNEL_ID:
            return

        command = await parse_exchange_command(message.content)
        if not command:
            return

        action = command["action"]

        if action == "buy_token_from_exchange":
            success, result = await buy_token_from_exchange(command["symbol"], command["amount"], command["buyer"])
        elif action == "swap_token":
            receiver = "ORB.3358818231E648618486921F"
            success, result = await swap_token(command["amount"], command["buyer"], receiver)
        elif action == "BUY" or action == "SELL":
            success, result = await trade_token_on_exchange(
                symbol=command["symbol"],
                amount=command["amount"],
                user_address=command["owner"],
                action=command["action"]
            )
        elif action == "cancel":
            success, result = await cancel_order(command["order_id"])
        elif action == "deposit":
            receiver = "ORB.3358818231E648618486921F"
            success, result = await deposit(command["symbol"], command["amount"], receiver, command["address"])
        elif action == "withdrawal":
            sender = "ORB.3358818231E648618486921F"
            success, result = await withdrawal(command["amount"], command["address"], sender)
        elif action == "create":
            success, result = await create_token(
                name=command["name"],
                symbol=command["symbol"],
                supply=command["supply"],
                creator=command["creator"]
            )
        else:
            success, result = False, f"Unknown action::{action}"

        # Respond based on success/failure
        if success:
            await message.delete()
            if isinstance(result, dict):
                msg = json.dumps(result, indent=2)
                await message.channel.send(f"[ExchangeBot] Success:\n```json\n{msg}\n```")
            else:
                await message.channel.send(f"[ExchangeBot] {result}")
        else:
            await message.channel.send(f"[ExchangeBot] Failed: {result}")
