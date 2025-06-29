from api import get_user_balance, get_user_address, get_user_tokens, lock_orbit_api, claim_rewards_api, claim_check_api, mine_check_api
from discord.ext import commands
import discord
from core.ioutil import fetch_chain
from core.walletutil import get_wallet_stats

def find_best_price(symbol, direction, user_address):
    ledger = fetch_chain()
    if not ledger:
        return None

    relevant_orders = [
        tx for tx in ledger if tx.get("type") == "order"
        and tx.get("symbol", "").upper() == symbol.upper()
        and tx.get("direction") == direction
        and tx.get("address") != user_address
    ]

    if not relevant_orders:
        return None

    if direction == "SELL":
        # For BUY: Look for lowest SELL price
        return min(relevant_orders, key=lambda x: float(x.get("price", float("inf")))).get("price")
    elif direction == "BUY":
        # For SELL: Look for highest BUY price
        return max(relevant_orders, key=lambda x: float(x.get("price", 0))).get("price")
    return None

async def get_wallet_balance(address):
    return {
        "address": address,
        "available": 0.0,
        "locked": 0.0,
        "total": 0.0,
        "transactions": [],
        "validators": {},
        "security_circle": []
    }

async def lock_orbit(address, amount, duration):
    result, message = await lock_orbit_api(address, amount, duration)
    if result == "success":
        return True

async def claim_rewards(address):
    result, message = await claim_rewards_api(address)
    if result == "success":
        return message

async def wallet_info(uid):
    import re
    address = await get_user_address(uid)
    balance = await get_wallet_balance(address)
    total, wallet_bal, locked = await get_user_balance(address)
    tokens = get_user_tokens(address)
    token_value = 0.0
    for token in tokens:
        if token.upper() != "ORBIT":
            wallet_stats = await get_wallet_stats(token.upper())
            for wallet in wallet_stats:
                if address in wallet:
                    match = re.search(r': ([\d,\.]+)\(([\d,\.]+) Orbit\)', wallet)
                    if match:
                        quantity_str = match.group(1).replace(",", "")
                        orbit_value_str = match.group(2).replace(",", "")
                        quantity = float(quantity_str)
                        orbit_value = float(orbit_value_str)
                        token_value += orbit_value

    embed = discord.Embed(title="Orbit Wallet", color=0x00ffcc)
    embed.add_field(name="Address", value=address, inline=False)
    embed.add_field(name="Wallet", value=f"{wallet_bal:,.6f} Orbit", inline=True)
    embed.add_field(name="Locked", value=f"{locked} Orbit", inline=True)
    embed.add_field(name="DeFi", value=f"{token_value:,.6f} Orbit", inline=True)
    embed.add_field(name="Total", value=f"{(total + token_value):,.6f} Orbit", inline=True)
    embed.add_field(name="View on Explorer", value=f"[Explorer]( https://beginner-pop-temp-dennis.trycloudflare.com/address/{address})", inline=False)
    status, mine_cooldown = await mine_check_api(address)
    if not mine_cooldown:
        mine_cooldown = "Now"
    embed.add_field(name="Next Mine", value=f"{mine_cooldown[1]}", inline=True)
    status, claim_cooldown = await claim_check_api(address)
#    embed.add_field(name="Next Claim", value=f"{claim_cooldown['message']}", inline=True)
    return embed
