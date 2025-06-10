from discord.ui import View, Button, Select
import discord
import asyncio
from api import create_2fa_api, get_user_address


class Register2FAView(View):
    def __init__(self, discord_id):
        super().__init__(timeout=None)
        self.user_id = discord_id

    async def interaction_check(self, interaction: discord.Interaction) -> bool:
        if interaction.user.id != self.user_id:
            await interaction.response.send_message(
                "⚠️ You are not authorized to use this dashboard.",
                ephemeral=True
            )
            return False
        return True

    @discord.ui.button(label="Register 2FA", style=discord.ButtonStyle.primary)
    async def register(self, interaction: discord.Interaction, button: Button):
        await interaction.response.defer(thinking=True, ephemeral=True)
        address = await get_user_address(self.user_id)
        secret = await create_2fa_api(address)
        ROLE_ID = 1379507259180060742
        role = interaction.guild.get_role(ROLE_ID)
        if role:
            await interaction.user.add_roles(role)
            await interaction.followup.send(
                content=f"Address: {address}", ephemeral=True
            )
            await interaction.followup.send(
                content=f"2FA Secret: {secret}", ephemeral=True
            )
