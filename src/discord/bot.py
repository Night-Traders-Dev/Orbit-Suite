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
price_data        = defaultdict(lambda: {"buy":0.0, "sell":0.0})
snapshot_5m       = defaultdict(lambda: {"buy":0.0, "sell":0.0})
snapshot_1h       = defaultdict(lambda: {"buy":0.0, "sell":0.0})
snapshot_24h      = defaultdict(lambda: {"buy":0.0, "sell":0.0})

vol_5m   = defaultdict(lambda: {"tokens":0.0, "orbit":0.0})
vol_1h   = defaultdict(lambda: {"tokens":0.0, "orbit":0.0})
vol_24h  = defaultdict(lambda: {"tokens":0.0, "orbit":0.0})

orb_5m   = defaultdict(lambda: {"tokens":0.0, "orbit":0.0})
orb_1h   = defaultdict(lambda: {"tokens":0.0, "orbit":0.0})
orb_24h  = defaultdict(lambda: {"tokens":0.0, "orbit":0.0})

def calc_change(old, new):
    return round(((new-old)/old)*100, 2) if old else 0.0

bot = commands.Bot(command_prefix="!", intents=discord.Intents.all())

@bot.event
async def on_ready():
    wallet_setup(bot, GUILD)
    await bot.tree.sync(guild=GUILD)
    print("✅ Ready:", bot.user)
    await bootstrap_chain()
    periodic_report.start()

async def bootstrap_chain():
    now  = datetime.utcnow()
    t5   = now - timedelta(minutes=5)
    t1   = now - timedelta(hours=1)
    t24  = now - timedelta(hours=24)

    print("🔄 Loading chain…")
    async with aiohttp.ClientSession() as sess:
        r = await sess.get(CHAIN_API_URL)
        chain = await r.json() if r.status==200 else []
    print(f"⛓️  {len(chain)} blocks")

    for blk in chain:
        for tx in blk.get("transactions", []):
            amt = tx.get("amount", 0.0)
            ts  = datetime.utcfromtimestamp(tx.get("timestamp",0))
            note= tx.get("note") or {}
            if not isinstance(note, dict): continue
            xfer = note.get("type",{}).get("token_transfer")
            if not isinstance(xfer, dict): continue

            sym   = xfer.get("token_symbol")
            toks  = xfer.get("amount",0.0)
            txt   = xfer.get("note","")
            act   = "buy" if "purchased" in txt else "sell" if "sold" in txt else None
            if not sym or not act or toks<=0: continue

            price_data[sym][act] = round(amt/toks, 6)

            # allocate to intervals
            if ts>=t24:
                vol_24h[sym]["tokens"] += toks
                orb_24h[sym]["orbit"]  += amt
            if ts>=t1:
                vol_1h[sym]["tokens"] += toks
                orb_1h[sym]["orbit"]  += amt
            if ts>=t5:
                vol_5m[sym]["tokens"] += toks
                orb_5m[sym]["orbit"]  += amt

            # snapshots: last value before interval
            if ts<=t5:
                snapshot_5m[sym][act] = price_data[sym][act]
            if ts<=t1:
                snapshot_1h[sym][act] = price_data[sym][act]
            if ts<=t24:
                snapshot_24h[sym][act] = price_data[sym][act]

    print("✅ Chain init:", list(price_data.keys()))

@bot.event
async def on_message(msg):
    if msg.channel.id!=EXCHANGE_CHANNEL_ID: return
    if not msg.content.startswith("[ExchangeBot] Success"): return

    data = json.loads(msg.content.split("```json")[1].split("```")[0])
    act  = data["action"].lower()
    sym  = data["symbol"].upper()
    toks = data["tokens_received" if act=="buy" else "tokens_sold"]
    amt  = data["orbit_spent" if act=="buy" else "orbit_received"]

    price_data[sym][act] = round(amt/toks,6)

    now = datetime.utcnow()
    # update vol/orb
    for d,orb,limit in ((vol_5m,orb_5m,5),(vol_1h,orb_1h,60),(vol_24h,orb_24h,1440)):
        d[sym]["tokens"] += toks
        orb[sym]["orbit"] += amt

    # update snapshots only if first in interval
    for snap in (snapshot_5m, snapshot_1h, snapshot_24h):
        if snap[sym][act]==0:
            snap[sym][act] = price_data[sym][act]

    pfx = "🟢 BUY" if act=="buy" else "🔴 SELL"
    await bot.get_channel(PRICE_UPDATE_CHANNEL_ID).send(
        f"💱 **{sym} {act.upper()}**\n"
        f"{pfx}: `{price_data[sym][act]:.6f}`\n"
        f"Tokens: `{toks}` | ORBIT: `{amt}`"
    )

@tasks.loop(minutes=5)
async def periodic_report():
    now = datetime.utcnow()
    ch  = bot.get_channel(PRICE_UPDATE_CHANNEL_ID)

    # 5-min
    tm = now.strftime("%H:%M UTC")
    lines=[f"📊 **5-Min Update** (`{tm}`)"]
    for s,(b,sell) in price_data.items():
        old_b,old_s = snapshot_5m[s]["buy"], snapshot_5m[s]["sell"]
        cb=calc_change(old_b, b); cs=calc_change(old_s, sell)
        vt=vol_5m[s]["tokens"]
        lines.append(
          f"\n**{s}**\n🟢 `{b:.6f}` ({cb:+.2f}%) 🔴 `{sell:.6f}` ({cs:+.2f}%)"
          f"\n🔼 {vt:.2f} tok"
        )
        snapshot_5m[s]={"buy":b,"sell":sell}
        vol_5m[s]= {"tokens":0.0}; orb_5m[s]={"orbit":0.0}
    await ch.send("\n".join(lines))

    # hourly on :05
    if now.minute==5:
        await do_interval(ch, "Hourly", snapshot_1h, vol_1h, orb_1h)
    # daily on 00:05
    if now.hour==0 and now.minute==5:
        await do_interval(ch, "Daily", snapshot_24h, vol_24h, orb_24h)

async def do_interval(ch, label, snap, vol, orb):
    tm = datetime.utcnow().strftime("%H:%M UTC" if label=="Hourly" else "%Y-%m-%d")
    lines=[f"🕐 **{label} Summary** (`{tm}`)"]
    for s,(b,sell) in price_data.items():
        old_b,old_s = snap[s]["buy"], snap[s]["sell"]
        cb=calc_change(old_b,b); cs=calc_change(old_s,sell)
        v=vol[s]["tokens"]; o=orb[s]["orbit"]
        avg_buy  = o/v if v else 0
        lines.append(
          f"\n**{s}**\n🟢 `{b:.6f}`({cb:+.2f}%) 🔴 `{sell:.6f}`({cs:+.2f}%)"
          f"\nVol: {v:.2f} tok | Avg Price: {avg_buy:.6f}"
        )
        snap[s]={"buy":b,"sell":sell}
        vol[s]={"tokens":0.0}; orb[s]={"orbit":0.0}
    await ch.send("\n".join(lines))

bot.run(DISCORD_TOKEN)