from discord.ui import Modal, TextInput, Select
import discord
import asyncio
from core.ioutil import fetch_chain
from api import verify_2fa_api, send_orbit_api, get_user_address, get_user_balance, get_user_tokens
from wallet import lock_orbit, wallet_info
from core.tx_util.tx_types import TXExchange

class MyTokensModal(Modal):
    def __init__(self, uid, portfolio_text="No tokens found."):
        super().__init__(title="My Tokens")
        self.uid = uid

        self.portfolio_display = TextInput(
            label="Your Token Holdings",
            style=discord.TextStyle.paragraph,
            required=False,
            max_length=4000
        )
        self.portfolio_display.default = portfolio_text

        self.add_item(self.portfolio_display)

    async def on_submit(self, interaction: discord.Interaction):
        await interaction.response.send_message("✅ Portfolio viewed.", ephemeral=True)


