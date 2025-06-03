from discord.ui import View, Button
import discord
from modals import SendOrbitModal, LockOrbitModal, TokenListingModal
from wallet import claim_rewards, wallet_info
from api import create_2fa_api, get_user_address, mine_orbit_api

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
    def __init__(self):
        super().__init__(timeout=None)

    @discord.ui.button(label="Buy Tokens", style=discord.ButtonStyle.green, custom_id="buy_tokens")
    async def buy_button(self, interaction: discord.Interaction, button: Button):
        await interaction.response.send_message("🔍 Token marketplace coming soon!", ephemeral=True)

    @discord.ui.button(label="Sell Tokens", style=discord.ButtonStyle.red, custom_id="sell_tokens")
    async def sell_button(self, interaction: discord.Interaction, button: Button):
        await interaction.response.send_message("📝 Feature under construction!", ephemeral=True)

    @discord.ui.button(label="List a Token", style=discord.ButtonStyle.blurple, custom_id="list_token")
    async def list_button(self, interaction: discord.Interaction, button: Button):
        await interaction.response.send_modal(TokenListingModal())

    @discord.ui.button(label="My Tokens", style=discord.ButtonStyle.gray, custom_id="my_tokens")
    async def my_tokens_button(self, interaction: discord.Interaction, button: Button):
        await interaction.response.send_message("📊 Portfolio view under development.", ephemeral=True)
