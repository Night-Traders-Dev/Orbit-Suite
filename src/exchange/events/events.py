# events/events.py
import json
from parser.parser import parse_exchange_command
from logic.logic import create_buy_order

BOT_OPS_CHANNEL_ID = 1379630873174872197

def register_events(bot):
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
