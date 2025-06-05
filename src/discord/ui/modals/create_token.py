from discord.ui import Modal, TextInput, Select
import discord
import asyncio
from core.ioutil import fetch_chain
from api import verify_2fa_api, send_orbit_api, get_user_address, get_user_balance, get_user_tokens
from core.tx_util.tx_types import TXExchange
from configure import BOT_OPS_CHANNEL_ID, TOKEN_CREATION_FEE



class CreateTokenModal(Modal):
    def __init__(self, uid):
        super().__init__(title="Orbit Exchange - Create Token")
        self.uid = uid
        self.address = ""
        self.name = TextInput(label="Token Name", placeholder="ExampleToken", max_length=32)
        self.symbol = TextInput(label="Symbol", placeholder="EXT", max_length=8)
        self.supply = TextInput(label="Total Supply", placeholder="1000000", max_length=18)
        self.add_item(self.name)
        self.add_item(self.symbol)
        self.add_item(self.supply)

    async def on_submit(self, interaction: discord.Interaction):
        self.address = await get_user_address(self.uid)

        try:
            supply_val = float(self.supply.value)
            if supply_val <= 0:
                raise ValueError("Supply must be positive.")
        except ValueError:
            await interaction.response.send_message("❌ Invalid supply amount.", ephemeral=True)
            return

        total, available, locked = await get_user_balance(self.address)
        if available < TOKEN_CREATION_FEE:
            await interaction.response.send_message(
                f"❌ You need at least {TOKEN_CREATION_FEE} ORBIT to list a token. Your balance: {balance:.2f}",
                ephemeral=True
            )
            return

        channel = interaction.client.get_channel(BOT_OPS_CHANNEL_ID)
        if channel:
            await channel.send(
                f"[ExchangeRequest] CREATE {self.name.value.strip()} {self.symbol.value.strip().upper()} {supply_val} {self.address}"
            )
            await interaction.response.send_message(
                f"✅ Token listing request submitted to Exchange Bot.",
                ephemeral=True
            )
        else:
            await interaction.response.send_message("❌ Could not reach Exchange Bot channel.", ephemeral=True)
