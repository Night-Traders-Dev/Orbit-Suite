from discord.ext import commands
from discord import app_commands
import discord
from configure import DISCORD_TOKEN
from commands.commands import setup as wallet_setup
import json

intents = discord.Intents.all()
intents.message_content = True
bot = commands.Bot(command_prefix="!", intents=intents)
GUILD = discord.Object(id=1376608254741713008)


EXCHANGE_CHANNEL_ID = 1379630873174872197
PRICE_UPDATE_CHANNEL_ID = 1386066535193509948

price_data = {}  # { 'CORAL': {'buy': {'price': X, 'change': Y}, 'sell': {...}} }

def calc_change(old, new):
    if old == 0:
        return 0
    return round(((new - old) / old) * 100, 2)

@bot.event
async def on_ready():
    try:
        wallet_setup(bot, GUILD)
        synced = await bot.tree.sync(guild=GUILD)
        print(f"Synced {len(synced)}")
    except Exception as e:
        print(e)
    print(f'Bot Name: {bot.user}')

@bot.event
async def on_message(message):
    if message.channel.id != EXCHANGE_CHANNEL_ID:
        return

    if not message.content.startswith("[ExchangeBot] Success"):
        return

    try:
        content = message.content.split("```json")[1].split("```")[0].strip()
        data = json.loads(content)

        symbol = data.get("symbol")
        action = data.get("action")
        update_channel = bot.get_channel(PRICE_UPDATE_CHANNEL_ID)

        if not symbol or not action:
            return

        # Initialize token tracking
        if symbol not in price_data:
            price_data[symbol] = {"buy": {"price": 0, "change": 0}, "sell": {"price": 0, "change": 0}}

        if action == "BUY":
            tokens = data["tokens_received"]
            orbit = data["orbit_spent"]
            new_price = round(orbit / tokens, 6)
            old_price = price_data[symbol]["buy"]["price"]
            change = calc_change(old_price, new_price)

            price_data[symbol]["buy"]["price"] = new_price
            price_data[symbol]["buy"]["change"] = change

            await update_channel.send(
                f"📈 **{symbol} BUY Price Updated**\n"
                f"> 💸 `Price:` {new_price:.6f} ORBIT/token\n"
                f"> 🔄 `Change:` {change:+.2f}%"
            )

        elif action == "SELL":
            tokens = data["tokens_sold"]
            orbit = data["orbit_received"]
            new_price = round(orbit / tokens, 6)
            old_price = price_data[symbol]["sell"]["price"]
            change = calc_change(old_price, new_price)

            price_data[symbol]["sell"]["price"] = new_price
            price_data[symbol]["sell"]["change"] = change

            await update_channel.send(
                f"📉 **{symbol} SELL Price Updated**\n"
                f"> 💸 `Price:` {new_price:.6f} ORBIT/token\n"
                f"> 🔄 `Change:` {change:+.2f}%"
            )

    except Exception as e:
        print(f"[ERROR] Failed to parse ExchangeBot message: {e}")




bot.run(DISCORD_TOKEN)
