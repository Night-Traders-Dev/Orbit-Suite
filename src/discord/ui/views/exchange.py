from discord.ui import View, Button, Select
import discord
import asyncio
from api import create_2fa_api, get_user_address, mine_orbit_api, get_user_tokens
from commands.token_stats import token_stats
from core.ioutil import fetch_chain
from ui.modals.buy_sell import BuyTokenModal, SellTokenModal, BuyFromExchangeModal, PlaceOrderModal
from ui.modals.create_token import CreateTokenModal
from ui.modals.orders import ViewOrdersModal


class ExchangeView(View):
    def __init__(self, user_id):
        super().__init__(timeout=None)
        self.user_id = user_id

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

    @discord.ui.button(label="Place Order", style=discord.ButtonStyle.green)
    async def place_order(self, interaction: discord.Interaction, button: Button):
        await interaction.response.send_modal(PlaceOrderModal(self.user_id))

    @discord.ui.button(label="ICO", style=discord.ButtonStyle.green)
    async def buy_ico(self, interaction: discord.Interaction, button: Button):
        await interaction.response.send_modal(BuyFromExchangeModal(self.user_id))

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

    @discord.ui.button(label="View Orders", style=discord.ButtonStyle.gray)
    async def view_orders(self, interaction: discord.Interaction, button: Button):
        await interaction.response.send_modal(ViewOrdersModal(self.user_id))

    @discord.ui.button(label="🔙 Back", style=discord.ButtonStyle.gray)
    async def back(self, interaction: discord.Interaction, button: Button):
        await interaction.response.edit_message(content="**📊 Exchange Menu**", view=ExchangeView(self.user_id))


# 🧬 Token Management View
class TokenView(View):
    def __init__(self, user_id):
        super().__init__(timeout=None)
        self.user_id = user_id

    @discord.ui.button(label="Create Token", style=discord.ButtonStyle.blurple)
    async def create_token(self, interaction: discord.Interaction, button: Button):
        await interaction.response.send_modal(CreateTokenModal(self.user_id))

    @discord.ui.button(label="My Tokens", style=discord.ButtonStyle.gray)
    async def my_tokens(self, interaction: discord.Interaction, button: Button):
        address = await get_user_address(self.user_id)
        result = await token_stats(address)
        embed = discord.Embed(title="📊 Your Token Holdings", color=discord.Color.blue())

        if not result:
            embed.description = "You don't own any tokens."
        else:
            for token_data in result:
                (
                    symbol, balance,
                    buy_tokens, buy_orbit,
                    sell_tokens, sell_orbit,
                    avg_buy_price, avg_sell_price,
                    current_price
                ) = token_data

                embed.add_field(
                    name=f"{symbol} — {balance:,.2f} tokens",
                    value=(
                        f"**Bought:** {buy_tokens:,.2f} for {buy_orbit:,.2f} Orbit\n"
                        f"**Sold:** {sell_tokens:,.2f} for {sell_orbit:,.2f} Orbit\n"
                        f"**Avg Buy Price:** {avg_buy_price if avg_buy_price else '–'} Orbit\n"
                        f"**Avg Sell Price:** {avg_sell_price if avg_sell_price else '–'} Orbit\n"
                        f"**Current Price:** {current_price:.4f} Orbit"
                    ),
                    inline=False
                )
        await interaction.response.send_message(embed=embed, ephemeral=True)

    @discord.ui.button(label="🔙 Back", style=discord.ButtonStyle.gray)
    async def back(self, interaction: discord.Interaction, button: Button):
        await interaction.response.edit_message(content="**📊 Exchange Menu**", view=ExchangeView(self.user_id))
