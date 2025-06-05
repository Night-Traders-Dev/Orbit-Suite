from discord.ui import Modal, TextInput, Select
import discord
import asyncio
from core.ioutil import fetch_chain
from api import verify_2fa_api, send_orbit_api, get_user_address, get_user_balance, get_user_tokens
from core.tx_util.tx_types import TXExchange
from configure import BOT_OPS_CHANNEL_ID


class BuyTokenModal(Modal):
    def __init__(self, uid):
        super().__init__(title="Buy Tokens")
        self.address = ""
        self.uid = uid

        self.symbol = TextInput(label="Token Symbol", placeholder="e.g., ORBIT")
        self.amount = TextInput(label="Amount", placeholder="e.g., 50")
        self.price = TextInput(label="Price", placeholder="e.g., 10", style=discord.TextStyle.short)

        self.add_item(self.symbol)
        self.add_item(self.amount)
        self.add_item(self.price)

    async def on_submit(self, interaction: discord.Interaction):
        self.address = await get_user_address(self.uid)
        message = f"[ExchangeRequest] BUY {self.symbol.value.upper()} {self.price.value} {self.amount.value} {self.address}"
        bot_ops_channel = interaction.client.get_channel(BOT_OPS_CHANNEL_ID)

        if bot_ops_channel:
            await bot_ops_channel.send(message)
            await interaction.response.send_message(f"🟢 Sent buy request for `{self.amount.value}` {self.symbol.value.upper()} at `{self.price.value} ORBIT`", ephemeral=True)
        else:
            await interaction.response.send_message("❌ Bot-ops channel not found.", ephemeral=True)


class SellTokenModal(Modal):
    def __init__(self, uid):
        super().__init__(title="Sell Tokens")
        self.address = ""
        self.uid = uid

        self.symbol = TextInput(label="Token Symbol", placeholder="e.g., ORBIT")
        self.amount = TextInput(label="Amount", placeholder="e.g., 50")
        self.price = TextInput(label="Price", placeholder="e.g., 10", style=discord.TextStyle.short)

        self.add_item(self.symbol)
        self.add_item(self.amount)
        self.add_item(self.price)

    async def on_submit(self, interaction: discord.Interaction):
        self.address = await get_user_address(self.uid)
        message = f"[ExchangeRequest] SELL {self.symbol.value.upper()} {self.price.value} {self.amount.value} {self.address}"
        bot_ops_channel = interaction.client.get_channel(BOT_OPS_CHANNEL_ID)

        if bot_ops_channel:
            await bot_ops_channel.send(message)
            await interaction.response.send_message(f"🔴 Sent sell request for `{self.amount.value}` {self.symbol.value.upper()} at `{self.price.value} ORBIT`", ephemeral=True)
        else:
            await interaction.response.send_message("❌ Bot-ops channel not found.", ephemeral=True)


class BuyFromExchangeModal(Modal):
    def __init__(self, uid):
        super().__init__(title="Buy From Exchange")
        self.address = ""
        self.uid = uid

        self.symbol = TextInput(label="Token Symbol", placeholder="e.g., ORBIT")
        self.amount = TextInput(label="Amount", placeholder="e.g., 50", style=discord.TextStyle.short)

        self.add_item(self.symbol)
        self.add_item(self.amount)

    async def on_submit(self, interaction: discord.Interaction):
        self.address = await get_user_address(self.uid)
        message = f"[ExchangeRequest] BUYEX {self.symbol.value.upper()} {self.amount.value} {self.address}"
        bot_ops_channel = interaction.client.get_channel(BOT_OPS_CHANNEL_ID)

        if bot_ops_channel:
            await bot_ops_channel.send(message)
            await interaction.response.send_message(
                f"🟢 Sent direct exchange buy request for `{self.amount.value}` {self.symbol.value.upper()}",
                ephemeral=True
            )
        else:
            await interaction.response.send_message("❌ Bot-ops channel not found.", ephemeral=True)
