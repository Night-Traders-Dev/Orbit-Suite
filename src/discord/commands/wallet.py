from discord.ext import commands
import discord
from wallet import get_wallet_balance
from api import get_user_balance, get_user_address
from views import WalletDashboard, Register2FAView

def setup(bot):
    @bot.command(name="register")
    async def register_2fa(ctx):
        try:
            await ctx.message.delete()
        except (discord.Forbidden, discord.HTTPException):
            pass
        view = Register2FAView(ctx.author.id)
        await ctx.send("Click below to register 2FA.", view=view, delete_after=60)

    @bot.command(name="wallet")
    async def wallet(ctx):
        try:
            await ctx.message.delete()
        except (discord.Forbidden, discord.HTTPException):
            pass

        uid = ctx.author.id
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

        await ctx.send(embed=embed, view=WalletDashboard(uid), delete_after=60)
