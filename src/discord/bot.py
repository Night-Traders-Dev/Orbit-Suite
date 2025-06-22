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
GUILD = discord.Object(id=1376608254741713008)
CHAIN_API_URL           = "https://oliver-butler-oasis-builder.trycloudflare.com/api/chain"

# — IN-MEMORY STATE —
price_data        = {}  # token -> { "buy": float, "sell": float }
previous_snapshot = {}
# volume counters per token
volume_5m  = defaultdict(lambda: {"buy": 0.0, "sell": 0.0})
volume_1h  = defaultdict(lambda: {"buy": 0.0, "sell": 0.0})
volume_24h = defaultdict(lambda: {"buy": 0.0, "sell": 0.0})


def calc_change(old, new):
    if old == 0: return 0.0
    return round(((new - old)/old)*100, 2)


bot = commands.Bot(command_prefix="!", intents=discord.Intents.all())

@bot.event
async def on_ready():
    # register slash commands, etc.
    wallet_setup(bot, GUILD)
    synced = await bot.tree.sync(guild=GUILD)
    print(f"Synced {len(synced)} commands")

    print(f"✅ Bot ready as {bot.user}")

    # bootstrap everything from the full chain
    await bootstrap_from_chain()

    # start reporting loop
    periodic_report.start()


async def bootstrap_from_chain():
    """
    Fetch the entire chain once, parse every token_transfer:
     • last seen prices => price_data + previous_snapshot
     • volume in last 5m, 1h, 24h
    """
    print("🔄 Bootstrapping from chain…")
    now = datetime.utcnow()
    t5  = now - timedelta(minutes=5)
    t1  = now - timedelta(hours=1)
    t24 = now - timedelta(hours=24)

    async with aiohttp.ClientSession() as sess:
        async with sess.get(CHAIN_API_URL) as resp:
            if resp.status != 200:
                print(f"[WARN] Chain fetch failed: {resp.status}")
                return
            chain = await resp.json()

    # iterate every block, every tx
    for block in chain:
        for tx in block.get("transactions", []):
            # top-level ORBIT amount
            orbit_amt = tx.get("amount", 0.0)
            ts = datetime.utcfromtimestamp(tx.get("timestamp", 0))
            # guard against note being a string or None
            raw_note = tx.get("note", {})
            note_obj = raw_note if isinstance(raw_note, dict) else {}
            note_type = note_obj.get("type", {})

            xfer = note_type.get("token_transfer")
            if not xfer:
                continue

            sym    = xfer.get("token_symbol")
            tokens = xfer.get("amount", 0.0)
            note   = xfer.get("note", "")

            # classify buy vs sell
            action = None
            if "purchased from exchange" in note:
                action = "buy"
            elif "sold to exchange" in note:
                action = "sell"
            if not (sym and action):
                continue

            # 1) last‐seen price
            price = round(orbit_amt / tokens, 6) if tokens else 0.0
            price_data.setdefault(sym, {})[action] = price

            # 2) volume windows
            if ts >= t24:
                volume_24h[sym][action] += tokens
            if ts >= t1:
                volume_1h[sym][action] += tokens
            if ts >= t5:
                volume_5m[sym][action] += tokens

    # snapshot = current price_data
    previous_snapshot.update({t: dict(price_data[t]) for t in price_data})
    print("✅ Bootstrap complete. Tokens:", list(price_data.keys()))


@bot.event
async def on_message(message):
    # existing live‐update listener (no change)
    if message.channel.id != EXCHANGE_CHANNEL_ID:
        return
    if not message.content.startswith("[ExchangeBot] Success"):
        return

    try:
        payload = message.content.split("```json")[1].split("```")[0].strip()
        data = json.loads(payload)
        action = data["action"].lower()
        sym    = data["symbol"].upper()
        if action not in ("buy","sell"):
            return

        # update price_data
        if sym not in price_data:
            price_data[sym] = {"buy":0.0,"sell":0.0}
            previous_snapshot[sym] = {"buy":0.0,"sell":0.0}

        if action=="buy":
            tokens = data["tokens_received"]
            orbit  = data["orbit_spent"]
        else:
            tokens = data["tokens_sold"]
            orbit  = data["orbit_received"]

        price = round(orbit / tokens, 6) if tokens else 0.0
        price_data[sym][action] = price

        # increment 5m & 1h & 24h counters
        volume_5m[sym][action]  += tokens
        volume_1h[sym][action]  += tokens
        volume_24h[sym][action] += tokens

        # live post
        prefix = "🟢 BUY" if action=="buy" else "🔴 SELL"
        msg = f"💱 **{sym} {action.upper()}**\n" \
              f"{prefix}: `{price}` ORBIT per {sym}\n" \
              f"Tokens: `{tokens}` | ORBIT: `{orbit}`"
        await bot.get_channel(PRICE_UPDATE_CHANNEL_ID).send(msg)

    except Exception as e:
        print("[ERR] parsing on_message:", e)


@tasks.loop(minutes=5)
async def periodic_report():
    """
    Runs every 5 minutes:
      • Always: 5-min market update
      • If minute==5: post the hourly summary (last 60m)
      • If hour==0 and minute==5: post the daily summary (last 24h)
    """
    now = datetime.utcnow()
    ch  = bot.get_channel(PRICE_UPDATE_CHANNEL_ID)

    # --- 5-min update ---
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
        # reset for next window & snapshot
        previous_snapshot[sym] = dict(stats)
        volume_5m[sym] = {"buy":0.0,"sell":0.0}

    await ch.send("\n".join(lines))

    # --- hourly at :05 ---
    await post_summary(ch, volume_1h, "🕐 Hourly Market Summary", now)

    # --- daily at 00:05 UTC ---
    await post_summary(ch, volume_24h, "📅 Daily Market Summary", now, date_fmt="%Y-%m-%d")

async def post_summary(channel, tracker, title, now, date_fmt="%H:%M UTC"):
    ts = now.strftime(date_fmt)
    lines = [f"**{title}** (`{ts}`)"]
    for sym, vol in tracker.items():
        lines.append(
            f"\n**{sym}**"
            f"\n🔼 {vol['buy']:.2f} tokens"
            f"\n🔽 {vol['sell']:.2f} tokens"
        )
        # reset
        tracker[sym] = {"buy":0.0,"sell":0.0}
    await channel.send("\n".join(lines))


bot.run(DISCORD_TOKEN)