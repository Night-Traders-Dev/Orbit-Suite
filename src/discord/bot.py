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

# — IN-MEMORY STATE —
price_data        = {}  # token -> { "buy": float, "sell": float }
previous_snapshot = {}  # token -> { "buy": float, "sell": float }

# volume counters per token
volume_5m  = defaultdict(lambda: {"buy":0.0, "sell":0.0})
volume_1h  = defaultdict(lambda: {"buy":0.0, "sell":0.0})
volume_24h = defaultdict(lambda: {"buy":0.0, "sell":0.0})

# price snapshots for change calc
price_snap_1h  = {}  # token -> { "buy": float, "sell": float }
price_snap_24h = {}  # token -> { "buy": float, "sell": float }


def calc_change(old, new):
    if old == 0: return 0.0
    return round(((new - old)/old)*100, 2)


bot = commands.Bot(command_prefix="!", intents=discord.Intents.all())


@bot.event
async def on_ready():
    wallet_setup(bot, GUILD)
    await bot.tree.sync(guild=GUILD)
    print(f"✅ Bot ready as {bot.user}")

    await bootstrap_from_chain()

    periodic_report.start()


async def bootstrap_from_chain():
    """
    Fetch the full chain, update:
     • price_data & previous_snapshot (last‐seen prices)
     • volume_5m, volume_1h, volume_24h 
     • price_snap_1h & price_snap_24h
    """
    now = datetime.utcnow()
    t5  = now - timedelta(minutes=5)
    t1  = now - timedelta(hours=1)
    t24 = now - timedelta(hours=24)

    print("🔄 Bootstrapping from chain…")
    async with aiohttp.ClientSession() as sess:
        async with sess.get(CHAIN_API_URL) as resp:
            if resp.status != 200:
                print(f"[WARN] Chain fetch failed: {resp.status}")
                return
            chain = await resp.json()

    # walk through all transactions in chronological order
    for block in chain:
        for tx in block.get("transactions", []):
            orbit_amt = tx.get("amount", 0.0)
            ts = datetime.utcfromtimestamp(tx.get("timestamp", 0))
            # safe‐guard note
            raw_note = tx.get("note", {})
            note_obj = raw_note if isinstance(raw_note, dict) else {}
            xfer = note_obj.get("type", {}).get("token_transfer")
            if not xfer:
                continue

            sym    = xfer.get("token_symbol")
            tokens = xfer.get("amount", 0.0)
            note   = xfer.get("note", "")
            action = None
            if "Token purchased from exchange" in note:
                action = "buy"
            elif "Token sold to exchange" in note:
                action = "sell"
            if not sym or not action:
                continue

            # 1) compute price
            price = round(orbit_amt / tokens, 6) if tokens else 0.0
            price_data.setdefault(sym, {})[action] = price

            # 2) track volumes
            if ts >= t24:
                volume_24h[sym][action] += tokens
            if ts >= t1:
                volume_1h[sym][action] += tokens
            if ts >= t5:
                volume_5m[sym][action] += tokens

            # 3) capture price snapshots at thresholds
            # because chain is chronological, last write <= threshold wins
            if ts <= t1:
                price_snap_1h.setdefault(sym, {})[action] = price
            if ts <= t24:
                price_snap_24h.setdefault(sym, {})[action] = price

    # initialize previous_snapshot for 5-min change
    previous_snapshot.update({s: dict(price_data[s]) for s in price_data})
    print("✅ Bootstrap complete:", list(price_data.keys()))


@bot.event
async def on_message(message):
    """
    Mirror the live [ExchangeBot] messages to update
    in-memory price_data, volumes, and price snapshots.
    """
    if message.channel.id != EXCHANGE_CHANNEL_ID:
        return
    if not message.content.startswith("[ExchangeBot] Success"):
        return

    try:
        payload = message.content.split("```json")[1].split("```")[0].strip()
        data = json.loads(payload)
        action = data["action"].lower()
        sym    = data["symbol"].upper()
        if action not in ("buy","sell"): return

        # init if new
        price_data.setdefault(sym, {"buy":0.0, "sell":0.0})
        previous_snapshot.setdefault(sym, {"buy":0.0, "sell":0.0})
        price_snap_1h.setdefault(sym, {"buy":0.0, "sell":0.0})
        price_snap_24h.setdefault(sym, {"buy":0.0, "sell":0.0})

        # extract amounts
        if action == "buy":
            tokens = data["tokens_received"]
            orbit  = data["orbit_spent"]
        else:
            tokens = data["tokens_sold"]
            orbit  = data["orbit_received"]

        price = round(orbit / tokens, 6) if tokens else 0.0
        price_data[sym][action] = price

        # volumes
        volume_5m[sym][action]  += tokens
        volume_1h[sym][action]  += tokens
        volume_24h[sym][action] += tokens

        # update live price snapshots too (for ongoing hour/day)
        price_snap_1h[sym][action]  = price_snap_1h[sym][action] or price
        price_snap_24h[sym][action] = price_snap_24h[sym][action] or price

        # post immediate update
        prefix = "🟢 BUY" if action=="buy" else "🔴 SELL"
        msg = (
            f"💱 **{sym} {action.upper()}**\n"
            f"{prefix}: `{price}` ORBIT per {sym}\n"
            f"Tokens: `{tokens}` | ORBIT: `{orbit}`"
        )
        await bot.get_channel(PRICE_UPDATE_CHANNEL_ID).send(msg)

    except Exception as e:
        print("[ERR] on_message:", e)


@tasks.loop(minutes=5)
async def periodic_report():
    now = datetime.utcnow()
    ch  = bot.get_channel(PRICE_UPDATE_CHANNEL_ID)

    ts = now.strftime("%H:%M UTC")
    lines = [f"📊 **5-Minute Market Update** (`{ts}`)"]
    for sym, stats in price_data.items():
        prev = previous_snapshot.get(sym, {"buy":0,"sell":0})
        cb   = calc_change(prev["buy"],  stats["buy"])
        cs   = calc_change(prev["sell"], stats["sell"])
        v5   = volume_5m[sym]
        lines.append(
            f"\n**{sym}**"
            f"\n🟢 Buy: `{stats['buy']:.6f}` ({cb:+.2f}%)"
            f"\n🔴 Sell:`{stats['sell']:.6f}` ({cs:+.2f}%)"
            f"\n🔼 {v5['buy']:.2f} tokens"
            f"\n🔽 {v5['sell']:.2f} tokens"
        )
        # reset and snapshot for next window
        previous_snapshot[sym] = dict(stats)
        volume_5m[sym] = {"buy":0.0,"sell":0.0}

    await ch.send("\n".join(lines))
    await bootstrap_from_chain()

    await hourly_summary(ch, now)

    await daily_summary(ch, now)


async def hourly_summary(channel, now):
    ts = now.strftime("%H:%M UTC")
    lines = [f"🕐 **Hourly Market Summary** (`{ts}`)"]
    for sym, curr in price_data.items():
        # grab snapshot or default to current price
        old = price_snap_1h.get(sym, {})
        old_buy  = old.get("buy",  curr["buy"])
        old_sell = old.get("sell", curr["sell"])

        cb  = calc_change(old_buy,  curr["buy"])
        cs  = calc_change(old_sell, curr["sell"])
        vol = volume_1h[sym]

        lines.append(
            f"\n**{sym}**"
            f"\n🟢 Buy: `{curr['buy']:.6f}` ({cb:+.2f}%)"
            f"\n🔴 Sell:`{curr['sell']:.6f}` ({cs:+.2f}%)"
            f"\n🔼 {vol['buy']:.2f} tokens"
            f"\n🔽 {vol['sell']:.2f} tokens"
        )

        # reset counters & advance snapshot
        volume_1h[sym]    = {"buy":0.0, "sell":0.0}
        price_snap_1h[sym] = {"buy": curr["buy"], "sell": curr["sell"]}

    await channel.send("\n".join(lines))


async def daily_summary(channel, now):
    ts = now.strftime("%Y-%m-%d")
    lines = [f"📅 **Daily Market Summary** (`{ts}`)"]
    for sym, curr in price_data.items():
        old = price_snap_24h.get(sym, {})
        old_buy  = old.get("buy",  curr["buy"])
        old_sell = old.get("sell", curr["sell"])

        cb  = calc_change(old_buy,  curr["buy"])
        cs  = calc_change(old_sell, curr["sell"])
        vol = volume_24h[sym]

        lines.append(
            f"\n**{sym}**"
            f"\n🟢 Buy: `{curr['buy']:.6f}` ({cb:+.2f}%)"
            f"\n🔴 Sell:`{curr['sell']:.6f}` ({cs:+.2f}%)"
            f"\n🔼 {vol['buy']:.2f} tokens"
            f"\n🔽 {vol['sell']:.2f} tokens"
        )

        # reset counters & advance snapshot
        volume_24h[sym]     = {"buy":0.0, "sell":0.0}
        price_snap_24h[sym] = {"buy": curr["buy"], "sell": curr["sell"]}

    await channel.send("\n".join(lines) + "\n\n*End of day summary.*")


# Start the bot
bot.run(DISCORD_TOKEN)