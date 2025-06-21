from discord.ui import View, Button, Select
import discord
import asyncio
from api import get_user_address, get_user_tokens
from commands.token_stats import token_stats
from core.ioutil import fetch_chain
from core.walletutil import get_wallet_stats
from ui.modals.buy_sell import BuyTokenModal, SellTokenModal
from ui.modals.create_token import CreateTokenModal


class ExchangeView(View):
    def __init__(self, user_id):
        super().__init__(timeout=None)
        self.user_id = user_id

    async def interaction_check(self, interaction: discord.Interaction) -> bool:
        if interaction.user.id != self.user_id:
            await interaction.response.send_message(
                "⚠️ You are not authorized to use this dashboard.",
                ephemeral=True
            )
            return False
        return True

    @discord.ui.button(label="💱 Trading", style=discord.ButtonStyle.green)
    async def trading_menu(self, interaction: discord.Interaction, button: Button):
        await interaction.response.edit_message(content="**💱 Trading Menu**", view=TradingView(self.user_id))

    @discord.ui.button(label="📃 Orders", style=discord.ButtonStyle.gray)
    async def orders_menu(self, interaction: discord.Interaction, button: Button):
        await interaction.response.edit_message(content="**📃 Orders Menu**", view=OrdersView(self.user_id))

    @discord.ui.button(label="🧬 Token Management", style=discord.ButtonStyle.blurple)
    async def token_menu(self, interaction: discord.Interaction, button: Button):
        await interaction.response.edit_message(content="**🧬 Token Management Menu**", view=TokenView(self.user_id))


# 💱 Trading View
class TradingView(View):
    def __init__(self, user_id):
        super().__init__(timeout=None)
        self.user_id = user_id

    async def interaction_check(self, interaction: discord.Interaction) -> bool:
        if interaction.user.id != self.user_id:
            await interaction.response.send_message(
                "⚠️ You are not authorized to use this dashboard.",
                ephemeral=True
            )
            return False
        return True

#    @discord.ui.button(label="Place Order", style=discord.ButtonStyle.green)
#    async def place_order(self, interaction: discord.Interaction, button: Button):
#        await interaction.response.send_modal(PlaceOrderModal(self.user_id))


    @discord.ui.button(label="Token Stats", style=discord.ButtonStyle.primary)
    async def top_wallet(self, interaction: discord.Interaction, button: Button):
        address = await get_user_address(self.user_id)
        tokens = get_user_tokens(address)
        token_list = []
        for token in tokens:
            if token.upper() != "ORBIT":
                token_list.append(token)
        await interaction.response.send_message(
            "Select a token to view:", view=SelectTokenView(token_list), ephemeral=True
        )

    @discord.ui.button(label="Buy Tokens", style=discord.ButtonStyle.green)
    async def buy_tokens(self, interaction: discord.Interaction, button: Button):
        await interaction.response.send_modal(BuyTokenModal(self.user_id))

    @discord.ui.button(label="Sell Tokens", style=discord.ButtonStyle.red)
    async def sell_tokens(self, interaction: discord.Interaction, button: Button):
        await interaction.response.send_modal(SellTokenModal(self.user_id))

    @discord.ui.button(label="🔙 Back", style=discord.ButtonStyle.gray)
    async def back(self, interaction: discord.Interaction, button: Button):
        await interaction.response.edit_message(content="**📊 Exchange Menu**", view=ExchangeView(self.user_id))


# 📃 Orders View
class OrdersView(View):
    def __init__(self, user_id):
        super().__init__(timeout=None)
        self.user_id = user_id


    async def interaction_check(self, interaction: discord.Interaction) -> bool:
        if interaction.user.id != self.user_id:
            await interaction.response.send_message(
                "⚠️ You are not authorized to use this dashboard.",
                ephemeral=True
            )
            return False
        return True


    @discord.ui.button(label="🔙 Back", style=discord.ButtonStyle.gray)
    async def back(self, interaction: discord.Interaction, button: Button):
        await interaction.response.edit_message(content="**📊 Exchange Menu**", view=ExchangeView(self.user_id))


# 🧬 Token Management View
class TokenView(View):
    def __init__(self, user_id):
        super().__init__(timeout=None)
        self.user_id = user_id

    async def interaction_check(self, interaction: discord.Interaction) -> bool:
        if interaction.user.id != self.user_id:
            await interaction.response.send_message(
                "⚠️ You are not authorized to use this dashboard.",
                ephemeral=True
            )
            return False
        return True

    @discord.ui.button(label="Create Token", style=discord.ButtonStyle.blurple)
    async def create_token(self, interaction: discord.Interaction, button: Button):
        await interaction.response.send_modal(CreateTokenModal(self.user_id))


    @discord.ui.button(label="🔙 Back", style=discord.ButtonStyle.gray)
    async def back(self, interaction: discord.Interaction, button: Button):
        await interaction.response.edit_message(content="**📊 Exchange Menu**", view=ExchangeView(self.user_id))


class TokenSelectDropdown(Select):
    def __init__(self, token_list):
        options = [discord.SelectOption(label=token) for token in token_list]
        super().__init__(placeholder="Select token to view", options=options, min_values=1, max_values=1)

    async def callback(self, interaction: discord.Interaction):
        token = self.values[0]
        wallet_stats = await get_wallet_stats(token.upper())
        embed = discord.Embed(title=f"{token} Top Wallets", color=discord.Color.blue())
        for wallet in wallet_stats:
            embed.add_field(
                name=f"---------------------",
                value=(wallet),
                 inline=False
            )
        await interaction.response.send_message(embed=embed)

class SelectTokenView(View):
    def __init__(self, token_list):
        super().__init__(timeout=60)
        self.add_item(TokenSelectDropdown(token_list))
