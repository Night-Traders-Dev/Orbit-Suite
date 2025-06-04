from api import get_user_balance, get_user_address, lock_orbit_api, claim_rewards_api, claim_check_api, mine_check_api
from discord.ext import commands
import discord


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
    embed.add_field(name="View on Explorer", value=f"[Explorer](http://127.0.0.1:7000/address/{address})", inline=False)
    status, mine_cooldown = await mine_check_api(address)
    if not mine_cooldown:
        mine_cooldown = "Now"
    embed.add_field(name="Next Mine", value=f"{mine_cooldown[1]}", inline=True)
    status, claim_cooldown = await claim_check_api(address)
    embed.add_field(name="Next Claim", value=f"{claim_cooldown['message']}", inline=True)
    return embed
