from discord.ext import commands
import discord
from commands.wallet_tools import get_wallet_balance, wallet_info
from api import get_user_balance, get_user_address
from ui.views.register import Register2FAView
from ui.views.wallet import WalletDashboard
from ui.views.exchange import ExchangeView

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



    @bot.tree.command(
        name="exchange",
        description="Access the Orbit token exchange",
        guild=GUILD
    )
    async def exchange(interaction: discord.Interaction):
        uid = interaction.user.id
        embed = discord.Embed(
            title="Orbit Exchange",
            color=0x00ffcc
        )
        embed.add_field(
            name="Exchange Info",
            value="• Use buttons below to buy, sell, or list tokens.\n• Only community-created tokens are listed.",
            inline=False
        )

        await interaction.response.send_message(
            embed=embed,
            view=ExchangeView(uid),
            delete_after=120
        )

