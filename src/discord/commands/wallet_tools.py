from api import get_user_balance, get_user_address, lock_orbit_api, claim_rewards_api, claim_check_api, mine_check_api
from discord.ext import commands
import discord
from core.ioutil import fetch_chain

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
    address = await get_user_address(uid)
    balance = await get_wallet_balance(address)
    total, wallet, locked = await get_user_balance(address)

    embed = discord.Embed(title="Orbit Wallet", color=0x00ffcc)
    embed.add_field(name="Address", value=address, inline=False)
    embed.add_field(name="Wallet", value=f"{wallet} ORBIT", inline=True)
    embed.add_field(name="Locked", value=f"{locked} ORBIT", inline=True)
    embed.add_field(name="Total", value=f"{total} ORBIT", inline=True)
    embed.add_field(name="View on Explorer", value=f"[Explorer]( https://40af-173-187-247-149.ngrok-free.app/address/{address})", inline=False)
    status, mine_cooldown = await mine_check_api(address)
    if not mine_cooldown:
        mine_cooldown = "Now"
    embed.add_field(name="Next Mine", value=f"{mine_cooldown[1]}", inline=True)
    status, claim_cooldown = await claim_check_api(address)
    embed.add_field(name="Next Claim", value=f"{claim_cooldown['message']}", inline=True)
    return embed
