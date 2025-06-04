from discord.ui import View, Button
import discord
import asyncio
from modals import SendOrbitModal, LockOrbitModal, CreateTokenModal, BuyTokenModal, SellTokenModal, BuyFromExchangeModal, MyTokensModal
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

    @discord.ui.button(label="Sell Tokens", style=discord.ButtonStyle.red, custom_id="sell_tokens")
    async def sell_button(self, interaction: discord.Interaction, button: Button):
        await interaction.response.send_modal(SellTokenModal(self.user_id))

    @discord.ui.button(label="Create Token", style=discord.ButtonStyle.blurple, custom_id="create_token")
    async def list_button(self, interaction: discord.Interaction, button: Button):
        await interaction.response.send_modal(CreateTokenModal(self.user_id))

    @discord.ui.button(label="Buy ICO", style=discord.ButtonStyle.green, custom_id="buy_ico")
    async def buy_ico(self, interaction: discord.Interaction, button: Button):
        await interaction.response.send_modal(BuyFromExchangeModal(self.user_id))


    @discord.ui.button(label="My Tokens", style=discord.ButtonStyle.gray, custom_id="my_tokens")
    async def my_tokens_button(self, interaction: discord.Interaction, button: Button):
        address = await get_user_address(self.user_id)
        if not address:
            await interaction.response.send_message("Could not find your address. Please ensure you've linked it.", ephemeral=True)
            return

        chain = fetch_chain()
        tokens = {}
        token_stats = {}

        for block in chain:
            for tx in block.get("transactions", []):
                note = tx.get("note")
                orbit_amount = tx.get("amount")

                if isinstance(note, dict) and note.get("type", {}).get("token_transfer"):
                    data = note["type"]["token_transfer"]
                    token_symbol = data.get("token_symbol")
                    token_qty = data.get("amount")
                    sender = data.get("sender")
                    receiver = data.get("receiver")

                    if not token_symbol or not isinstance(token_qty, (int, float)):
                        continue

                    # Net holdings
                    if receiver == address:
                        tokens[token_symbol] = tokens.get(token_symbol, 0.0) + token_qty
                    elif sender == address:
                        tokens[token_symbol] = tokens.get(token_symbol, 0.0) - token_qty

                    # Buy stats (user receives token, spends Orbit)
                    if receiver == address and orbit_amount:
                        stats = token_stats.setdefault(token_symbol, {"buy_tokens": 0, "buy_orbit": 0.0, "sell_tokens": 0, "sell_orbit": 0.0})
                        stats["buy_tokens"] += token_qty
                        stats["buy_orbit"] += orbit_amount

                    # Sell stats (user sends token, receives Orbit)
                    if sender == address and orbit_amount:
                        stats = token_stats.setdefault(token_symbol, {"buy_tokens": 0, "buy_orbit": 0.0, "sell_tokens": 0, "sell_orbit": 0.0})
                        stats["sell_tokens"] += token_qty
                        stats["sell_orbit"] += orbit_amount

        embed = discord.Embed(
            title="📊 My Token Portfolio",
            color=discord.Color.blurple()
        )

        if not tokens:
            embed.description = "You don’t hold any tokens yet."
        else:
            for symbol, amount in tokens.items():
                stats = token_stats.get(symbol, {})
                buy_avg = (stats["buy_orbit"] / stats["buy_tokens"]) if stats.get("buy_tokens") else None
                sell_avg = (stats["sell_orbit"] / stats["sell_tokens"]) if stats.get("sell_tokens") else None

                value = f"**Holdings:** {amount:.2f} {symbol}\n"
                value += f"**Avg Buy Price:** {f'{buy_avg:.4f}' if buy_avg else 'N/A'} Orbit\n"
                value += f"**Avg Sell Price:** {f'{sell_avg:.4f}' if sell_avg else 'N/A'} Orbit"

                embed.add_field(name=symbol, value=value, inline=False)

        await interaction.response.send_message(embed=embed, ephemeral=True)
