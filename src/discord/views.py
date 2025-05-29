from discord.ui import View, Button
import discord
from modals import SendOrbitModal, LockOrbitModal
from wallet import claim_rewards
from api import create_2fa_api

class WalletDashboard(View):
    def __init__(self, username):
        super().__init__(timeout=None)
        self.user_id = username

    @discord.ui.button(label="Send ORBIT", style=discord.ButtonStyle.primary)
    async def send_orbit(self, interaction: discord.Interaction, button: Button):
        await interaction.response.send_modal(SendOrbitModal(self.user_id))

    @discord.ui.button(label="Lock ORBIT", style=discord.ButtonStyle.secondary)
    async def lock_orbit(self, interaction: discord.Interaction, button: Button):
        await interaction.response.send_modal(LockOrbitModal(self.user_id))

    @discord.ui.button(label="Claim Rewards", style=discord.ButtonStyle.secondary)
    async def claim(self, interaction: discord.Interaction, button: Button):
        msg = "🌟 Rewards claimed!" if claim_rewards(self.user_id) else "❌ Claim failed."
        await interaction.response.send_message(msg, ephemeral=True)

class Register2FAView(View):
    def __init__(self, username):
        super().__init__(timeout=None)
        self.user_id = username

    @discord.ui.button(label="Register 2FA", style=discord.ButtonStyle.primary)
    async def register(self, interaction: discord.Interaction, button: Button):
        secret = await create_2fa_api(self.user_id)
        await interaction.response.send_message(
            content=f"Here is your 2FA QR code: {secret}", ephemeral=True
        )
