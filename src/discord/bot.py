import aiohttp
from discord.ext import commands, tasks
import discord
import json
from collections import defaultdict
from datetime import datetime, timedelta
from configure import DISCORD_TOKEN
from commands.commands import setup as wallet_setup
import matplotlib.pyplot as plt
import os

# — CONFIG —
EXCHANGE_CHANNEL_ID     = 1379630873174872197
PRICE_UPDATE_CHANNEL_ID = 1386066535193509948
GUILD                   = discord.Object(id=1376608254741713008)
CHAIN_API_URL           = "https://oliver-butler-oasis-builder.trycloudflare.com/api/chain"

# — STATE —
# Current per-token prices (ORBIT per token) for each side.
price_data = defaultdict(lambda: {"buy": 0.0, "sell": 0.0})

# Snapshots (previous interval prices) for % change calculations.
snapshot_5m  = defaultdict(lambda: {"buy": 0.0, "sell": 0.0})
snapshot_1h  = defaultdict(lambda: {"buy": 0.0, "sell": 0.0})
snapshot_24h = defaultdict(lambda: {"buy": 0.0, "sell": 0.0})

# Accumulators for tokens and ORBIT amounts over each interval.
# For buys:
buy_vol_5m   = defaultdict(lambda: {"tokens": 0.0, "orbit": 0.0})
buy_vol_1h   = defaultdict(lambda: {"tokens": 0.0, "orbit": 0.0})
buy_vol_24h  = defaultdict(lambda: {"tokens": 0.0, "orbit": 0.0})
# For sells:
sell_vol_5m  = defaultdict(lambda: {"tokens": 0.0, "orbit": 0.0})
sell_vol_1h  = defaultdict(lambda: {"tokens": 0.0, "orbit": 0.0})
sell_vol_24h = defaultdict(lambda: {"tokens": 0.0, "orbit": 0.0})

def calc_change(old, new):
    return round(((new - old) / old) * 100, 2) if old else 0.0

bot = commands.Bot(command_prefix="!", intents=discord.Intents.all())

@bot.event
async def on_ready():
    wallet_setup(bot, GUILD)
    await bot.tree.sync(guild=GUILD)
    print("✅ Ready:", bot.user)
    await bootstrap_chain()
    periodic_report.start()

async def bootstrap_chain():
    """
    Load the full chain, process each token_transfer to:
      • Compute per-transaction price (ORBIT per token)
      • Allocate token volumes and ORBIT amounts to intervals:
           - 5 minutes, 1 hour, and 24 hours (separately for buy and sell)
      • Set snapshot prices for each interval.
    """
    now  = datetime.utcnow()
    t5   = now - timedelta(minutes=5)
    t1   = now - timedelta(hours=1)
    t24  = now - timedelta(hours=24)
    print("🔄 Loading chain…")
    async with aiohttp.ClientSession() as sess:
        r = await sess.get(CHAIN_API_URL)
        chain = await r.json() if r.status == 200 else []
    print(f"⛓️  {len(chain)} blocks")

    for blk in chain:
        for tx in blk.get("transactions", []):
            amt = tx.get("amount", 0.0)
            ts  = datetime.utcfromtimestamp(tx.get("timestamp", 0))
            note = tx.get("note") or {}
            if not isinstance(note, dict):
                continue
            xfer = note.get("type", {}).get("token_transfer")
            if not isinstance(xfer, dict):
                continue
            sym = xfer.get("token_symbol")
            toks = xfer.get("amount", 0.0)
            txt = xfer.get("note", "")
            act = "buy" if "purchased" in txt else "sell" if "sold" in txt else None
            if not sym or not act or toks <= 0:
                continue

            price_data[sym][act] = round(amt / toks, 6)

            if ts >= t24:
                if act == "buy":
                    buy_vol_24h[sym]["tokens"] += toks
                    buy_vol_24h[sym]["orbit"] += amt
                else:
                    sell_vol_24h[sym]["tokens"] += toks
                    sell_vol_24h[sym]["orbit"] += amt
            if ts >= t1:
                if act == "buy":
                    buy_vol_1h[sym]["tokens"] += toks
                    buy_vol_1h[sym]["orbit"] += amt
                else:
                    sell_vol_1h[sym]["tokens"] += toks
                    sell_vol_1h[sym]["orbit"] += amt
            if ts >= t5:
                if act == "buy":
                    buy_vol_5m[sym]["tokens"] += toks
                    buy_vol_5m[sym]["orbit"] += amt
                else:
                    sell_vol_5m[sym]["tokens"] += toks
                    sell_vol_5m[sym]["orbit"] += amt

            if ts <= t5:
                snapshot_5m[sym][act] = price_data[sym][act]
            if ts <= t1:
                snapshot_1h[sym][act] = price_data[sym][act]
            if ts <= t24:
                snapshot_24h[sym][act] = price_data[sym][act]
    print("✅ Chain init:", list(price_data.keys()))

@bot.event
async def on_message(msg):
    if msg.channel.id != EXCHANGE_CHANNEL_ID:
        return
    if not msg.content.startswith("[ExchangeBot] Success"):
        return
    try:
        payload = msg.content.split("```json")[1].split("```")[0].strip()
        data = json.loads(payload)
    except Exception as e:
        print("[ERR] on_message parse:", e)
        return

    act = data["action"].lower()
    sym = data["symbol"].upper()
    toks = data["tokens_received"] if act == "buy" else data["tokens_sold"]
    amt = data["orbit_spent"] if act == "buy" else data["orbit_received"]

    price_data[sym][act] = round(amt / toks, 6)

    if act == "buy":
        buy_vol_5m[sym]["tokens"] += toks
        buy_vol_5m[sym]["orbit"] += amt
        buy_vol_1h[sym]["tokens"] += toks
        buy_vol_1h[sym]["orbit"] += amt
        buy_vol_24h[sym]["tokens"] += toks
        buy_vol_24h[sym]["orbit"] += amt
    elif act == "sell":
        sell_vol_5m[sym]["tokens"] += toks
        sell_vol_5m[sym]["orbit"] += amt
        sell_vol_1h[sym]["tokens"] += toks
        sell_vol_1h[sym]["orbit"] += amt
        sell_vol_24h[sym]["tokens"] += toks
        sell_vol_24h[sym]["orbit"] += amt

    if snapshot_5m[sym][act] == 0:
        snapshot_5m[sym][act] = price_data[sym][act]
    if snapshot_1h[sym][act] == 0:
        snapshot_1h[sym][act] = price_data[sym][act]
    if snapshot_24h[sym][act] == 0:
        snapshot_24h[sym][act] = price_data[sym][act]

    pfx = "🟢 BUY" if act == "buy" else "🔴 SELL"
    await bot.get_channel(PRICE_UPDATE_CHANNEL_ID).send(
        f"💱 **{sym} {act.upper()}**\n"
        f"{pfx}: `{price_data[sym][act]:.6f}` ORBIT per {sym}\n"
        f"Tokens: `{toks}` | ORBIT: `{amt}`"
    )

@tasks.loop(minutes=5)
async def periodic_report():
    now = datetime.utcnow()
    ch = bot.get_channel(PRICE_UPDATE_CHANNEL_ID)
    tm = now.strftime("%H:%M UTC")
    lines = [f"📊 **5-Min Update** (`{tm}`)"]

    for s, stats in price_data.items():
        b = stats["buy"]
        sll = stats["sell"]
        old_b = snapshot_5m[s]["buy"]
        old_s = snapshot_5m[s]["sell"]
        cb = calc_change(old_b, b)
        cs = calc_change(old_s, sll)

        buy_tok = buy_vol_5m[s]["tokens"]
        buy_orb = buy_vol_5m[s]["orbit"]
        sell_tok = sell_vol_5m[s]["tokens"]
        sell_orb = sell_vol_5m[s]["orbit"]

        avg_buy = buy_orb / buy_tok if buy_tok else 0.0
        avg_sell = sell_orb / sell_tok if sell_tok else 0.0

        lines.append(
            f"\n**{s}**\n"
            f"🟢 Buy: {b:.6f} ({cb:+.2f}%)\n"
            f"🔴 Sell: {sll:.6f} ({cs:+.2f}%)\n"
            f"🔼 Buy: {buy_tok:,.2f} tokens, Orbit Spent: {buy_orb:,.2f} ORBIT\n"
            f"🔽 Sell: {sell_tok:,.2f} tokens, Orbit Received: {sell_orb:,.2f} ORBIT\n"
            f"💹 Avg Buy Price: {avg_buy:.6f} ORBIT\n"
            f"💹 Avg Sell Price: {avg_sell:.6f} ORBIT"
        )
        snapshot_5m[s] = {"buy": b, "sell": sll}
        buy_vol_5m[s] = {"tokens": 0.0, "orbit": 0.0}
        sell_vol_5m[s] = {"tokens": 0.0, "orbit": 0.0}

    await ch.send("\n".join(lines))

    await bootstrap_chain()
    await report_interval(ch, "Hourly", snapshot_1h, buy_vol_1h, sell_vol_1h)
    await report_interval(ch, "Daily", snapshot_24h, buy_vol_24h, sell_vol_24h)
    await generate_daily_chart(ch)

async def report_interval(channel, label, snap, buy_map, sell_map):
    tm = datetime.utcnow().strftime("%H:%M UTC" if label=="Hourly" else "%Y-%m-%d")
    lines = [f"🕐 **{label} Summary** (`{tm}`)"]
    for s, stats in price_data.items():
        b = stats["buy"]
        sll = stats["sell"]
        old_b = snap[s]["buy"]
        old_s = snap[s]["sell"]
        cb = calc_change(old_b, b)
        cs = calc_change(old_s, sll)

        buy_tok = buy_map[s]["tokens"]
        buy_orb = buy_map[s]["orbit"]
        sell_tok = sell_map[s]["tokens"]
        sell_orb = sell_map[s]["orbit"]
        total_vol = buy_tok + sell_tok
        avg_buy = buy_orb / buy_tok if buy_tok else 0.0
        avg_sell = sell_orb / sell_tok if sell_tok else 0.0

        lines.append(
            f"\n**{s}**\n"
            f"🟢 Buy: {b:.6f} ({cb:+.2f}%)\n"
            f"🔴 Sell: {sll:.6f} ({cs:+.2f}%)\n"
            f"Vol: {total_vol:,.2f} tokens\n"
            f"🔼 Buy: {buy_tok:,.2f} tokens\n🔼 Orbit Spent: {buy_orb:,.2f} ORBIT\n"
            f"🔽 Sell: {sell_tok:,.2f} tokens\n🔽 Orbit Received: {sell_orb:,.2f} ORBIT\n"
            f"💹 Avg Buy Price: {avg_buy:.6f} ORBIT\n💹 Avg Sell Price: {avg_sell:.6f} ORBIT"
        )
        snap[s] = {"buy": b, "sell": sll}
        buy_map[s] = {"tokens": 0.0, "orbit": 0.0}
        sell_map[s] = {"tokens": 0.0, "orbit": 0.0}
    await channel.send("\n".join(lines))

async def generate_daily_chart(channel):
    """
    For each token, generates and sends a line chart that displays the daily average buy and sell prices
    based on the 24h accumulators. Each chart has two data points (indices 0 and 1) representing the average
    buy and sell prices, drawn as a line with markers.
    """
    for sym in price_data:
        btoks = buy_vol_24h[sym]["tokens"]
        borbit = buy_vol_24h[sym]["orbit"]
        stoks = sell_vol_24h[sym]["tokens"]
        sorbit = sell_vol_24h[sym]["orbit"]
        avg_buy = borbit / btoks if btoks else 0.0
        avg_sell = sorbit / stoks if stoks else 0.0
        print(f"Token {sym}: avg_buy = {avg_buy}, avg_sell = {avg_sell}")
        if avg_buy == 0 and avg_sell == 0:
            continue
        fig, ax = plt.subplots(figsize=(8, 4))
        x = [0, 1]
        y = [avg_buy, avg_sell]
        ax.plot(x, y, color='black', linewidth=2)
        ax.scatter([0], [avg_buy], color='green', s=100, label='Avg Buy Price')
        ax.scatter([1], [avg_sell], color='red', s=100, label='Avg Sell Price')
        ax.set_xticks(x)
        ax.set_xticklabels(["Buy", "Sell"])
        ax.set_ylabel("Price (ORBIT)")
        ax.set_title(f"{sym} - Daily Average Prices")
        ax.legend()
        plt.tight_layout()
        chart_path = f"daily_chart_{sym}.png"
        plt.savefig(chart_path)
        plt.close(fig)
        await channel.send(f"Daily Average Price Chart for {sym}:", file=discord.File(chart_path))
        os.remove(chart_path)
    print("✅ Daily charts generated and sent.")
    # Reset accumulators for the next day
    for sym in price_data:
        buy_vol_24h[sym] = {"tokens": 0.0, "orbit": 0.0}
        sell_vol_24h[sym] = {"tokens": 0.0, "orbit": 0.0}
        

bot.run(DISCORD_TOKEN)