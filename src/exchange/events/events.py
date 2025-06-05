import json
from parser.parser import parse_exchange_command
from logic.logic import (
    create_order,
    create_buy_order,
    create_sell_order,
    cancel_order,
    quote_symbol,
    create_token,
    buy_token_from_exchange
)
from bot.api import get_user_address

EXCHANGE_UID = 1379645991782846608
BOT_OPS_CHANNEL_ID = 1379630873174872197

def register_events(bot):
    @bot.event
    async def on_ready():
        address = await get_user_address(bot.user.id)
        print(f"[✓] Orbit Exchange Bot is online as {address}")
        channel = bot.get_channel(BOT_OPS_CHANNEL_ID)
        if channel:
            await channel.send("[ExchangeBot] Ready and listening for orders.")

    @bot.event
    async def on_message(message):
        if message.author == bot.user or message.channel.id != BOT_OPS_CHANNEL_ID:
            return

        command = await parse_exchange_command(message.content)
        if not command:
            await message.channel.send("[ExchangeBot] Unrecognized or malformed command.")
            return

        action = command["action"]

        if action == "buy":
            success, result = await create_order(action, command["symbol"], command["price"], command["amount"], command["buyer"])
        elif action == "buy_token_from_exchange":
            success, result = await buy_token_from_exchange(command["symbol"], command["amount"], command["buyer"])
        elif action == "sell":
            success, result = await create_order(action, command["symbol"], command["price"], command["amount"], command["seller"])
        elif action == "cancel":
            success, result = await cancel_order(command["order_id"])
        elif action == "quote":
            success, result = await quote_symbol(command["symbol"])
        elif action == "create":
            success, result = await create_token(
                name=command["name"],
                symbol=command["symbol"],
                supply=command["supply"],
                creator=command["creator"]
            )
        else:
            success, result = False, "Unknown action."

        if success:
            if isinstance(result, dict):
                msg = json.dumps(result, indent=2)
                await message.channel.send(f"[ExchangeBot] Success:\n```json\n{msg}\n```")
            else:
                await message.channel.send(f"[ExchangeBot] {result}")
        else:
            await message.channel.send(f"[ExchangeBot] Failed: {result}")
