from api import get_user_balance, get_user_address, lock_orbit_api
from discord.ext import commands
import discord


def get_wallet_balance(address):
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

def claim_rewards(username):
    return True

async def wallet_info(uid):
    address = await get_user_address(uid)
    balance = get_wallet_balance(address)
    total, wallet, locked = get_user_balance(address)

    embed = discord.Embed(title="Orbit Wallet", color=0x00ffcc)
    embed.add_field(name="Address", value=address, inline=False)
    embed.add_field(name="Wallet", value=f"{wallet} ORBIT", inline=True)
    embed.add_field(name="Locked", value=f"{locked} ORBIT", inline=True)
    embed.add_field(name="Total", value=f"{total} ORBIT", inline=True)
    embed.add_field(name="View on Explorer", value=f"[Explorer](http://127.0.0.1:7000/address/{address})", inline=False)
    embed.add_field(name="Validator Stats", value="{}", inline=False)
    embed.add_field(name="Security Circle", value="{}", inline=False)

    tx_summary = "\n".join([f"{tx['timestamp']}: {tx['from']} ➔ {tx['to']} ({tx['amount']} ORBIT) - {tx['note']}" for tx in balance['transactions']])
    embed.add_field(name="Last Transactions", value=tx_summary, inline=False)
    return embed
