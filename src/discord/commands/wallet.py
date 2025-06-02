from discord.ext import commands
import discord
from wallet import get_wallet_balance, wallet_info
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
        uid = ctx.author.id
        try:
            await ctx.message.delete()
        except (discord.Forbidden, discord.HTTPException):
            pass

        embed = await wallet_info(uid)

        await ctx.send(embed=embed, view=WalletDashboard(uid), delete_after=60)
