from discord.ext import commands
import discord
from wallet import get_wallet_balance, wallet_info
from api import get_user_balance, get_user_address
from views import WalletDashboard, Register2FAView

def setup(bot, GUILD):
    @bot.tree.command(
        name="register",
        description="Register with Orbit Blockchain",
        guild=GUILD
    )
    async def register_2fa(interaction: discord.Interaction):
        view = Register2FAView(interaction.user.id)
        await interaction.response.send_message(
            "Click below to register 2FA.",
            view=view,
            delete_after=60
        )


    @bot.tree.command(
        name="wallet",
        description="Your orbit wallet",
        guild=GUILD
    )
    async def wallet(interaction: discord.Interaction):
        uid = interaction.user.id
        embed = await wallet_info(uid)
        await interaction.response.send_message(
            embed=embed,
            view=WalletDashboard(uid),
            delete_after=60
        )


