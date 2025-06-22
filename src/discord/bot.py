import aiohttp
from discord.ext import commands, tasks
import discord
import json
from collections import defaultdict
from datetime import datetime, timedelta
from configure import DISCORD_TOKEN
from commands.commands import setup as wallet_setup

# — CONFIG —
EXCHANGE_CHANNEL_ID     = 1379630873174872197
PRICE_UPDATE_CHANNEL_ID = 1386066535193509948
GUILD                   = discord.Object(id=1376608254741713008)
CHAIN_API_URL           = "https://oliver-butler-oasis-builder.trycloudflare.com/api/chain"

# — STATE —
# Current per-token prices from chain (per side)
price_data = defaultdict(lambda: {"buy": 0.0, "sell": 0.0})

# Snapshots (last reported price) for each interval for % change calculation.
snapshot_5m  = defaultdict(lambda: {"buy": 0.0, "sell": 0.0})
snapshot_1h  = defaultdict(lambda: {"buy": 0.0, "sell": 0.0})
snapshot_24h = defaultdict(lambda: {"buy": 0.0, "sell": 0.0})

# Accumulators for token volumes and ORBIT amounts on each side and per interval.
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
    Loads the full chain and processes each token_transfer to:
      • Set a per-token price (ORBIT per token) for buy and sell actions.
      • Accumulate tokens and ORBIT amounts in separate maps on the intervals:
          - Last 5 minutes, 1 hour, and 24 hours.
      • Set snapshot prices to allow calculation of % changes.
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

            # Calculate the transaction's price.
            price_data[sym][act] = round(amt / toks, 6)

            # Allocate token volumes and ORBIT amounts into the appropriate interval accumulators:
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

            # Set snapshot prices (last price prior to the threshold)
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

    # Update live accumulators across intervals.
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

    # Set snapshots if not already set.
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

    # 5-minute update: compute average prices from the accumulators.
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

        # Average prices for 5-min interval.
        avg_buy = buy_orb / buy_tok if buy_tok else 0.0
        avg_sell = sell_orb / sell_tok if sell_tok else 0.0

        lines.append(
            f"\n**{s}**\n"
            f"🟢 Buy: {b:.6f} ({cb:+.2f}%)\n"
            f"🔴 Sell: {sll:.6f} ({cs:+.2f}%)\n"
            f"🔼 Buy: {buy_tok:,.2f} tokens\nOrbit Spent: {buy_orb:,.2f} ORBIT\n"
            f"🔽 Sell: {sell_tok:,.2f} tokens\nOrbit Received: {sell_orb:,.2f} ORBIT\n"
            f"💹 Avg Buy Price: {avg_buy:.6f} ORBIT\nAvg Sell Price: {avg_sell:.6f} ORBIT"
        )
        snapshot_5m[s] = {"buy": b, "sell": sll}
        buy_vol_5m[s] = {"tokens": 0.0, "orbit": 0.0}
        sell_vol_5m[s] = {"tokens": 0.0, "orbit": 0.0}

    await ch.send("\n".join(lines))
    await bootstrap_chain()
    # Hourly and daily reports.
    await report_interval(ch, "Hourly", snapshot_1h, buy_vol_1h, sell_vol_1h)
    await report_interval(ch, "Daily", snapshot_24h, buy_vol_24h, sell_vol_24h)

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
            f"🔼 Buy: {buy_tok:,.2f} tokens\nOrbit Spent: {buy_orb:,.2f} ORBIT\n"
            f"🔽 Sell: {sell_tok:,.2f} tokens\nOrbit Received: {sell_orb:,.2f} ORBIT\n"
            f"💹 Avg Buy Price: {avg_buy:.6f} ORBIT\nAvg Sell Price: {avg_sell:.6f} ORBIT"
        )
        snap[s] = {"buy": b, "sell": sll}
        buy_map[s] = {"tokens": 0.0, "orbit": 0.0}
        sell_map[s] = {"tokens": 0.0, "orbit": 0.0}
    await channel.send("\n".join(lines))

bot.run(DISCORD_TOKEN)