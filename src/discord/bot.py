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
# Store current price per token per side.
price_data = defaultdict(lambda: {"buy": 0.0, "sell": 0.0})

# Snapshots of the last reported price (to calculate % change).
snapshot_5m  = defaultdict(lambda: {"buy": 0.0, "sell": 0.0})
snapshot_1h  = defaultdict(lambda: {"buy": 0.0, "sell": 0.0})
snapshot_24h = defaultdict(lambda: {"buy": 0.0, "sell": 0.0})

# We now accumulate volume and orbit separately for buy and sell:
# 5-minute accumulators
buy_vol_5m   = defaultdict(lambda: {"tokens": 0.0, "orbit": 0.0})
sell_vol_5m  = defaultdict(lambda: {"tokens": 0.0, "orbit": 0.0})
# Hourly accumulators
buy_vol_1h   = defaultdict(lambda: {"tokens": 0.0, "orbit": 0.0})
sell_vol_1h  = defaultdict(lambda: {"tokens": 0.0, "orbit": 0.0})
# Daily accumulators
buy_vol_24h  = defaultdict(lambda: {"tokens": 0.0, "orbit": 0.0})
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
    Loads the full chain from CHAIN_API_URL and allocates all transactions to the
    appropriate interval accumulators.
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
            # Get the overall ORBIT amount of the transaction
            amt = tx.get("amount", 0.0)
            ts  = datetime.utcfromtimestamp(tx.get("timestamp", 0))
            # Process the "note" field safely:
            note = tx.get("note") or {}
            if not isinstance(note, dict):
                continue
            xfer = note.get("type", {}).get("token_transfer")
            if not isinstance(xfer, dict):
                continue

            sym   = xfer.get("token_symbol")
            toks  = xfer.get("amount", 0.0)
            txt   = xfer.get("note", "")
            act   = None
            if "purchased" in txt:
                act = "buy"
            elif "sold" in txt:
                act = "sell"
            if not sym or not act or toks <= 0:
                continue

            # Calculate the per-tx price
            price_data[sym][act] = round(amt / toks, 6)

            # Accumulate volumes into separate maps by action:
            if ts >= t24:
                if act == "buy":
                    buy_vol_24h[sym]["tokens"] += toks
                    buy_vol_24h[sym]["orbit"]  += amt
                else:
                    sell_vol_24h[sym]["tokens"] += toks
                    sell_vol_24h[sym]["orbit"]  += amt
            if ts >= t1:
                if act == "buy":
                    buy_vol_1h[sym]["tokens"] += toks
                    buy_vol_1h[sym]["orbit"]  += amt
                else:
                    sell_vol_1h[sym]["tokens"] += toks
                    sell_vol_1h[sym]["orbit"]  += amt
            if ts >= t5:
                if act == "buy":
                    buy_vol_5m[sym]["tokens"] += toks
                    buy_vol_5m[sym]["orbit"]  += amt
                else:
                    sell_vol_5m[sym]["tokens"] += toks
                    sell_vol_5m[sym]["orbit"]  += amt

            # Set snapshots (last price before the threshold)
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
        data = json.loads(msg.content.split("```json")[1].split("```")[0])
    except Exception as e:
        print("[ERR] on_message parse:", e)
        return

    act  = data["action"].lower()
    sym  = data["symbol"].upper()
    toks = data["tokens_received"] if act == "buy" else data["tokens_sold"]
    amt  = data["orbit_spent"] if act == "buy" else data["orbit_received"]

    price_data[sym][act] = round(amt / toks, 6)

    # Update live accumulators in a similar way:
    if act == "buy":
        buy_vol_5m[sym]["tokens"] += toks
        buy_vol_5m[sym]["orbit"]  += amt
        buy_vol_1h[sym]["tokens"] += toks
        buy_vol_1h[sym]["orbit"]  += amt
        buy_vol_24h[sym]["tokens"] += toks
        buy_vol_24h[sym]["orbit"]  += amt
    elif act == "sell":
        sell_vol_5m[sym]["tokens"] += toks
        sell_vol_5m[sym]["orbit"]  += amt
        sell_vol_1h[sym]["tokens"] += toks
        sell_vol_1h[sym]["orbit"]  += amt
        sell_vol_24h[sym]["tokens"] += toks
        sell_vol_24h[sym]["orbit"]  += amt

    # Set snapshot if not already set
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

    # 5-minute update report
    tm = now.strftime("%H:%M UTC")
    lines = [f"📊 **5-Min Update** (`{tm}`)"]
    for s, stats in price_data.items():
        b = stats["buy"]
        sell = stats["sell"]
        old_b = snapshot_5m[s]["buy"]
        old_s = snapshot_5m[s]["sell"]
        cb = calc_change(old_b, b)
        cs = calc_change(old_s, sell)
        # For 5min, compute average prices separately:
        total_buy_tokens = buy_vol_5m[s]["tokens"]
        total_buy_orbit  = buy_vol_5m[s]["orbit"]
        total_sell_tokens = sell_vol_5m[s]["tokens"]
        total_sell_orbit  = sell_vol_5m[s]["orbit"]
        avg_buy = total_buy_orbit / total_buy_tokens if total_buy_tokens else 0.0
        avg_sell = total_sell_orbit / total_sell_tokens if total_sell_tokens else 0.0
        total_tokens = total_buy_tokens + total_sell_tokens
        lines.append(
            f"\n**{s}**"
            f"\n🟢 `{b:.6f}` ({cb:+.2f}%)  🔴 `{sell:.6f}` ({cs:+.2f}%)"
            f"\nVolume: {total_tokens:.2f} tok"
            f"\nAvg Buy Price: {avg_buy:.6f} | Avg Sell Price: {avg_sell:.6f}"
        )
        # Reset 5-min accumulators and update snapshot
        snapshot_5m[s] = {"buy": b, "sell": sell}
        buy_vol_5m[s] = {"tokens": 0.0, "orbit": 0.0}
        sell_vol_5m[s] = {"tokens": 0.0, "orbit": 0.0}
    await ch.send("\n".join(lines))

    # Hourly summary on minute 5 of the hour
    if now.minute == 5:
        await report_interval(ch, "Hourly", snapshot_1h, buy_vol_1h, sell_vol_1h)
    # Daily summary on 00:05 UTC
    if now.hour == 0 and now.minute == 5:
        await report_interval(ch, "Daily", snapshot_24h, buy_vol_24h, sell_vol_24h)

async def report_interval(channel, label, snap, buy_map, sell_map):
    tm = datetime.utcnow().strftime("%H:%M UTC" if label == "Hourly" else "%Y-%m-%d")
    lines = [f"🕐 **{label} Summary** (`{tm}`)"]
    for s, stats in price_data.items():
        b = stats["buy"]
        sell = stats["sell"]
        old_b = snap[s]["buy"]
        old_s = snap[s]["sell"]
        cb = calc_change(old_b, b)
        cs = calc_change(old_s, sell)
        buy_tokens = buy_map[s]["tokens"]
        buy_orbit  = buy_map[s]["orbit"]
        sell_tokens = sell_map[s]["tokens"]
        sell_orbit  = sell_map[s]["orbit"]
        avg_buy = buy_orbit / buy_tokens if buy_tokens else 0.0
        avg_sell = sell_orbit / sell_tokens if sell_tokens else 0.0
        total_vol = buy_tokens + sell_tokens
        lines.append(
            f"\n**{s}**"
            f"\n🟢 `{b:.6f}` ({cb:+.2f}%)  🔴 `{sell:.6f}` ({cs:+.2f}%)"
            f"\nVolume: {total_vol:.2f} tok"
            f"\nAvg Buy Price: {avg_buy:.6f} | Avg Sell Price: {avg_sell:.6f}"
        )
        # Reset the interval accumulators and update snapshot
        snap[s] = {"buy": b, "sell": sell}
        buy_map[s] = {"tokens": 0.0, "orbit": 0.0}
        sell_map[s] = {"tokens": 0.0, "orbit": 0.0}
    await channel.send("\n".join(lines))

bot.run(DISCORD_TOKEN)