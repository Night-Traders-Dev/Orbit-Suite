from discord.ui import View, Button
import discord
from modals import SendOrbitModal, LockOrbitModal
from wallet import claim_rewards
from api import create_2fa_api, get_user_address

class WalletDashboard(View):
    def __init__(self, discord_id, username):
        super().__init__(timeout=None)
        self.user_id = discord_id
        self.username = username

    @discord.ui.button(label="Send ORBIT", style=discord.ButtonStyle.primary)
    async def send_orbit(self, interaction: discord.Interaction, button: Button):
        await interaction.response.send_modal(SendOrbitModal(self.user_id, self.username))

    @discord.ui.button(label="Lock ORBIT", style=discord.ButtonStyle.secondary)
    async def lock_orbit(self, interaction: discord.Interaction, button: Button):
        await interaction.response.send_modal(LockOrbitModal(self.username))

    @discord.ui.button(label="Claim Rewards", style=discord.ButtonStyle.secondary)
    async def claim(self, interaction: discord.Interaction, button: Button):
        msg = "🌟 Rewards claimed!" if claim_rewards(self.username) else "❌ Claim failed."
        await interaction.response.send_message(msg, ephemeral=True)

class Register2FAView(View):
    def __init__(self, discord_id):
        super().__init__(timeout=None)
        self.user_id = discord_id

    @discord.ui.button(label="Register 2FA", style=discord.ButtonStyle.primary)
    async def register(self, interaction: discord.Interaction, button: Button):
        address = await get_user_address(self.user_id)
        secret = await create_2fa_api(address)
        await interaction.response.send_message(
            content=f"Address: {address}\n2FA Secret: {secret}", ephemeral=True
        )
