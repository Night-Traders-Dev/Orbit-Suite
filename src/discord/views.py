from discord.ui import View, Button
import discord
import asyncio
from modals import SendOrbitModal, LockOrbitModal, CreateTokenModal, BuyTokenModal, SellTokenModal, BuyFromExchangeModal, MyTokensModal, ViewOrdersModal
from wallet import claim_rewards, wallet_info
from api import create_2fa_api, get_user_address, mine_orbit_api
from core.ioutil import fetch_chain

BOT_OPS_CHANNEL_ID = 1379630873174872197

class WalletDashboard(View):
    def __init__(self, discord_id):
        super().__init__(timeout=None)
        self.user_id = discord_id

    @discord.ui.button(label="Send", style=discord.ButtonStyle.primary)
    async def send_orbit(self, interaction: discord.Interaction, button: Button):
        await interaction.response.send_modal(SendOrbitModal(self.user_id))

    @discord.ui.button(label="Mine", style=discord.ButtonStyle.green)
    async def mine_orbit(self, interaction: discord.Interaction, button: Button):
        address = await get_user_address(self.user_id)
        status, result = await mine_orbit_api(address)

        if status == "fail":
            msg = f"❌ {result}"
        else:
            msg = (
                f"⛏️ **Mining Started**\n"
                f"📈 Rate: `{result['rate']}` Orbit/sec\n"
                f"💰 Total Mined: `{result['mined']}` Orbit\n"
                f"🏆 User Reward: `{result['payout']}` Orbit"
            )

        await interaction.response.send_message(msg, ephemeral=True)
        embed = await wallet_info(self.user_id)
        await interaction.message.edit(embed=embed, view=WalletDashboard(self.user_id), delete_after=60)

    @discord.ui.button(label="Lock", style=discord.ButtonStyle.secondary)
    async def lock_orbit(self, interaction: discord.Interaction, button: Button):
        await interaction.response.send_modal(LockOrbitModal(self.user_id))

    @discord.ui.button(label="Claim Rewards", style=discord.ButtonStyle.secondary)
    async def claim(self, interaction: discord.Interaction, button: Button):
        address = await get_user_address(self.user_id)
        data = await claim_rewards(address)

        if data["status"] == "success":
            msg = (
                f"🎉 **Rewards Claimed!**\n"
                f"• Total Rewards: `{data['rewards']}` Orbit\n"
                f"• Node Fee: `{data['node_fee']}` Orbit\n"
                f"• Net Credited: `{data['net_credited']}` Orbit\n"
                f"• Matured Unlocked: `{data['matured_unlocked']}` Orbit\n"
            )
            if "relock_status" in data:
                msg += f"• {data['relock_status']}"
        elif data["status"] == "cooldown":
            msg = f"🕒 Cooldown active. {data['message']}"
        elif data["status"] == "ok":
            msg = f"ℹ️ {data['message']}"
        else:
            msg = f"❌ Error: {data.get('message', 'Unknown error')}"

        await interaction.response.send_message(msg, ephemeral=True)

class Register2FAView(View):
    def __init__(self, discord_id):
        super().__init__(timeout=None)
        self.user_id = discord_id

    @discord.ui.button(label="Register 2FA", style=discord.ButtonStyle.primary)
    async def register(self, interaction: discord.Interaction, button: Button):
        address = await get_user_address(self.user_id)
        secret = await create_2fa_api(address)
        ROLE_ID = 1379507259180060742
        role = interaction.guild.get_role(ROLE_ID)
        if role:
            await interaction.user.add_roles(role)
            await interaction.response.send_message(
                content=f"Address: {address}\n2FA Secret: {secret}", ephemeral=True
            )




class ExchangeView(View):
    def __init__(self, discord_id):
        super().__init__(timeout=None)
        self.user_id = discord_id

    @discord.ui.button(label="Buy Tokens", style=discord.ButtonStyle.green, custom_id="buy_tokens")
    async def buy_button(self, interaction: discord.Interaction, button: Button):
        await interaction.response.send_modal(BuyTokenModal(self.user_id))

    @discord.ui.button(label="Buy ICO", style=discord.ButtonStyle.green, custom_id="buy_ico")
    async def buy_ico(self, interaction: discord.Interaction, button: Button):
        await interaction.response.send_modal(BuyFromExchangeModal(self.user_id))


    @discord.ui.button(label="Sell Tokens", style=discord.ButtonStyle.red, custom_id="sell_tokens")
    async def sell_button(self, interaction: discord.Interaction, button: Button):
        await interaction.response.send_modal(SellTokenModal(self.user_id))

    @discord.ui.button(label="View Orders", style=discord.ButtonStyle.gray, custom_id="view_orders")
    async def view_orders_button(self, interaction: discord.Interaction, button: Button):
        await interaction.response.send_modal(ViewOrdersModal(self.user_id))


    @discord.ui.button(label="Create Token", style=discord.ButtonStyle.blurple, custom_id="create_token")
    async def list_button(self, interaction: discord.Interaction, button: Button):
        await interaction.response.send_modal(CreateTokenModal(self.user_id))


    @discord.ui.button(label="My Tokens", style=discord.ButtonStyle.gray, custom_id="my_tokens")
    async def my_tokens_button(self, interaction: discord.Interaction, button: Button):
        address = await get_user_address(self.user_id)
        if not address:
            await interaction.response.send_message("Could not find your address. Please ensure you've linked it.", ephemeral=True)
            return

        chain = fetch_chain()
        tokens = {}
        token_stats = {}

        for block in reversed(chain):
            for tx in block.get("transactions", []):
                note = tx.get("note")
                orbit_amount = tx.get("amount")
                if not isinstance(note, dict):
                    continue

                tx_type = note.get("type", {})

                # Token transfer
                if "token_transfer" in tx_type:
                    data = tx_type["token_transfer"]
                    token = data.get("token_symbol")
                    qty = data.get("amount")
                    sender = data.get("sender")
                    receiver = data.get("receiver")
                    is_exchange = data.get("note")
                    if not token or not isinstance(qty, (int, float)):
                        continue

                    stats = token_stats.setdefault(token, {"buy_tokens": 0, "buy_orbit": 0.0, "sell_tokens": 0, "sell_orbit": 0.0})

                    if receiver == address:
                        tokens[token] = tokens.get(token, 0) + qty
                        if is_exchange == "Token purchased from exchange":
                            stats["buy_tokens"] += qty
                            stats["buy_orbit"] += qty * 0.1
                        elif orbit_amount:
                            stats["buy_tokens"] += qty
                            stats["buy_orbit"] += orbit_amount

                    elif sender == address:
                        tokens[token] = tokens.get(token, 0) - qty
                        if orbit_amount:
                            stats["sell_tokens"] += qty
                            stats["sell_orbit"] += orbit_amount

                # Buy token
                elif "buy_token" in tx_type:
                    data = tx_type["buy_token"]
                    token = data.get("symbol")
                    qty = data.get("amount")
                    if not token or data.get("seller") == address:
                        continue
                    tokens[token] = tokens.get(token, 0) + qty
                    stats = token_stats.setdefault(token, {"buy_tokens": 0, "buy_orbit": 0.0, "sell_tokens": 0, "sell_orbit": 0.0})
                    stats["buy_tokens"] += qty
                    stats["buy_orbit"] += qty * data.get("price", 0)

                # Sell token
                elif "sell_token" in tx_type:
                    data = tx_type["sell_token"]
                    token = data.get("symbol")
                    qty = data.get("amount")
                    if not token or data.get("seller") != address:
                        continue
                    tokens[token] = tokens.get(token, 0) - qty
                    stats = token_stats.setdefault(token, {"buy_tokens": 0, "buy_orbit": 0.0, "sell_tokens": 0, "sell_orbit": 0.0})
                    stats["sell_tokens"] += qty
                    stats["sell_orbit"] += qty * data.get("price", 0)

        # Build embed
        embed = discord.Embed(title="📊 Your Token Holdings", color=discord.Color.blue())
        if not tokens:
            embed.description = "You don't own any tokens."
        else:
            for token, balance in tokens.items():
                if abs(balance) < 1e-8:
                    continue

                stats = token_stats.get(token, {})
                buy_tokens = stats.get("buy_tokens", 0)
                buy_orbit = stats.get("buy_orbit", 0)
                sell_tokens = stats.get("sell_tokens", 0)
                sell_orbit = stats.get("sell_orbit", 0)

                avg_buy_price = (buy_orbit / buy_tokens) if buy_tokens else None
                avg_sell_price = (sell_orbit / sell_tokens) if sell_tokens else None

                if avg_buy_price and avg_sell_price:
                    current_price = (avg_buy_price + avg_sell_price) / 2
                else:
                    current_price = avg_buy_price or avg_sell_price or 0.0

                embed.add_field(
                    name=f"{token} — {balance:.2f} tokens",
                    value=(
                        f"**Bought:** {buy_tokens:.2f} for {buy_orbit:.2f} ORB\n"
                        f"**Sold:** {sell_tokens:.2f} for {sell_orbit:.2f} ORB\n"
                        f"**Current Price:** {current_price:.4f} ORB"
                    ),
                    inline=False
                )

        await interaction.response.send_message(embed=embed, ephemeral=True)
