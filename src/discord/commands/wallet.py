from discord.ext import commands
import discord
from wallet import get_wallet_balance
from api import get_user_balance, get_user_address
from views import WalletDashboard, Register2FAView

def setup(bot):
    @bot.command(name="register2fa")
    async def register_2fa(ctx):
        view = Register2FAView(ctx.author.id)
        await ctx.send("Click below to register 2FA.", view=view)

    @bot.command(name="wallet")
    async def wallet(ctx):
        try:
            await ctx.message.delete()
        except (discord.Forbidden, discord.HTTPException):
            pass

        username = ctx.author.name
        uid = ctx.author.id
        balance = get_wallet_balance(username)
        address = await get_user_address(uid)
        total, wallet, locked = get_user_balance(username)

        embed = discord.Embed(title="Orbit Wallet", color=0x00ffcc)
        embed.add_field(name="Address", value=address, inline=False)
        embed.add_field(name="Wallet", value=f"{wallet} ORBIT", inline=True)
        embed.add_field(name="Locked", value=f"{locked} ORBIT", inline=True)
        embed.add_field(name="Total", value=f"{total} ORBIT", inline=True)
        embed.add_field(name="View on Explorer", value=f"[Explorer](https://3599-173-187-247-149.ngrok-free.app/address/{username})", inline=False)
        embed.add_field(name="Validator Stats", value="{}", inline=False)
        embed.add_field(name="Security Circle", value="{}", inline=False)

        tx_summary = "\n".join([f"{tx['timestamp']}: {tx['from']} ➔ {tx['to']} ({tx['amount']} ORBIT) - {tx['note']}" for tx in balance['transactions']])
        embed.add_field(name="Last Transactions", value=tx_summary, inline=False)

        await ctx.send(embed=embed, view=WalletDashboard(uid, username), delete_after=60)
