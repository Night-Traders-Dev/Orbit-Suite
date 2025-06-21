from discord.ext import commands, tasks
from discord import app_commands
import discord
from configure import DISCORD_TOKEN
from commands.commands import setup as wallet_setup
import json
from collections import defaultdict
from datetime import datetime

intents = discord.Intents.all()
intents.message_content = True
bot = commands.Bot(command_prefix="!", intents=intents)
GUILD = discord.Object(id=1376608254741713008)


EXCHANGE_CHANNEL_ID = 1379630873174872197
PRICE_UPDATE_CHANNEL_ID = 1386066535193509948

# token => current stats
price_data = {}
# token => price snapshot from 5 minutes ago
previous_snapshot = {}

# token => aggregates for 5-min reporting
volume_tracker = defaultdict(lambda: {
    "buy": {"count": 0, "orbit": 0.0, "tokens": 0.0},
    "sell": {"count": 0, "orbit": 0.0, "tokens": 0.0}
})


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
        data = json.loads(message.content.split("```json")[1].split("```")[0].strip())
        action = data.get("action")
        symbol = data.get("symbol", "").upper()
        if not symbol or not action:
            return

        if symbol not in price_data:
            price_data[symbol] = {"buy": 0.0, "sell": 0.0}

        if action == "BUY":
            tokens = data["tokens_received"]
            orbit = data["orbit_spent"]
            price = round(orbit / tokens, 6)
            price_data[symbol]["buy"] = price

            volume_tracker[symbol]["buy"]["count"] += 1
            volume_tracker[symbol]["buy"]["tokens"] += tokens
            volume_tracker[symbol]["buy"]["orbit"] += orbit

        elif action == "SELL":
            tokens = data["tokens_sold"]
            orbit = data["orbit_received"]
            price = round(orbit / tokens, 6)
            price_data[symbol]["sell"] = price

            volume_tracker[symbol]["sell"]["count"] += 1
            volume_tracker[symbol]["sell"]["tokens"] += tokens
            volume_tracker[symbol]["sell"]["orbit"] += orbit

    except Exception as e:
        print(f"[ERROR] Parsing failed: {e}")


@tasks.loop(minutes=1)
async def token_price_report():
    channel = bot.get_channel(PRICE_UPDATE_CHANNEL_ID)
    if not channel:
        print("[ERROR] Price channel not found.")
        return

    timestamp = datetime.utcnow().strftime('%H:%M UTC')
    lines = [f"📊 **5-Minute Market Update** (`{timestamp}`)"]

    for token, stats in price_data.items():
        old = previous_snapshot.get(token, {"buy": stats["buy"], "sell": stats["sell"]})
        change_buy = calc_change(old["buy"], stats["buy"])
        change_sell = calc_change(old["sell"], stats["sell"])

        buy_stats = volume_tracker[token]["buy"]
        sell_stats = volume_tracker[token]["sell"]

        lines.append(
            f"\n**{token}**"
            f"\n🟢 Buy: `{stats['buy']:.6f}` ORBIT ({change_buy:+.2f}%)"
            f"\n🔴 Sell: `{stats['sell']:.6f}` ORBIT ({change_sell:+.2f}%)"
            f"\n🔼 {buy_stats['count']} buys | {buy_stats['tokens']:.2f} tokens | {buy_stats['orbit']:.2f} ORBIT"
            f"\n🔽 {sell_stats['count']} sells | {sell_stats['tokens']:.2f} tokens | {sell_stats['orbit']:.2f} ORBIT"
        )

        # snapshot current price for next interval
        previous_snapshot[token] = {
            "buy": stats["buy"],
            "sell": stats["sell"]
        }

        # reset tracker
        volume_tracker[token] = {
            "buy": {"count": 0, "orbit": 0.0, "tokens": 0.0},
            "sell": {"count": 0, "orbit": 0.0, "tokens": 0.0}
        }

    await channel.send("\n".join(lines))



bot.run(DISCORD_TOKEN)
