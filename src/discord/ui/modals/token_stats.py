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


class ViewOrdersModal(Modal):
    def __init__(self, uid):
        super().__init__(title="View Token Orders")
        self.uid = uid
        self.symbol = TextInput(label="Token Symbol", placeholder="e.g., ORBIT")
        self.add_item(self.symbol)

    async def on_submit(self, interaction: discord.Interaction):
        token = self.symbol.value.upper()
        chain = fetch_chain()

        buy_orders = []
        sell_orders = []

        for block in reversed(chain):
            for tx in block.get("transactions", []):
                note = tx.get("note")
                if not isinstance(note, dict):
                    continue
                tx_type = note.get("type", {})

                if "buy_token" in tx_type:
                    data = tx_type["buy_token"]
                    if data.get("symbol") == token:
                        buy_orders.append({
                            "address": data.get("buyer") or tx.get("sender"),
                            "amount": data.get("amount"),
                            "price": data.get("price"),
                        })
                elif "sell_token" in tx_type:
                    data = tx_type["sell_token"]
                    if data.get("symbol") == token:
                        sell_orders.append({
                            "address": data.get("seller") or tx.get("sender"),
                            "amount": data.get("amount"),
                            "price": data.get("price"),
                        })

        embed = discord.Embed(title=f"📈 {token} Order Book", color=discord.Color.teal())
        if not buy_orders and not sell_orders:
            embed.description = "No recent buy or sell orders found."
        else:
            if buy_orders:
                embed.add_field(
                    name="🟢 Buy Orders",
                    value="\n".join([
                        f"`{o['amount']} @ {o['price']} ORB` — `{o['address'][:8]}...`"
                        for o in buy_orders[:10]
                    ]) or "None",
                    inline=False
                )
            if sell_orders:
                embed.add_field(
                    name="🔴 Sell Orders",
                    value="\n".join([
                        f"`{o['amount']} @ {o['price']} ORB` — `{o['address'][:8]}...`"
                        for o in sell_orders[:10]
                    ]) or "None",
                    inline=False
                )

        await interaction.response.send_message(embed=embed, ephemeral=True)
