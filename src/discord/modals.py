from discord.ui import Modal, TextInput
import discord
from api import verify_2fa_api, send_orbit_api
from wallet import lock_orbit

class SendOrbitModal(Modal):
    def __init__(self, username):
        super().__init__(title="Send ORBIT")
        self.user_id = username
        self.recipient = TextInput(label="Recipient ID")
        self.amount = TextInput(label="Amount")
        self.totp = TextInput(label="2FA Code", required=True)
        self.add_item(self.recipient)
        self.add_item(self.amount)
        self.add_item(self.totp)

    async def on_submit(self, interaction: discord.Interaction):
        await interaction.response.defer(ephemeral=True)
        try:
            amount = float(self.amount.value)
        except ValueError:
            await interaction.followup.send("⛔️ Invalid amount format.", ephemeral=True)
            return

        if not await verify_2fa_api(self.user_id, self.totp.value):
            await interaction.followup.send("⛔️ Invalid 2FA code.", ephemeral=True)
            return

        success, msg = await send_orbit_api(self.user_id, self.recipient.value, amount)
        await interaction.followup.send(msg, ephemeral=True)

class LockOrbitModal(Modal):
    def __init__(self, username):
        super().__init__(title="Lock ORBIT")
        self.user_id = username
        self.amount = TextInput(label="Amount to Lock")
        self.duration = TextInput(label="Lock Duration (days)")
        self.add_item(self.amount)
        self.add_item(self.duration)

    async def on_submit(self, interaction: discord.Interaction):
        success = lock_orbit(self.user_id, float(self.amount.value), int(self.duration.value))
        msg = "🔒 Lockup successful!" if success else "⛔️ Lockup failed."
        await interaction.response.send_message(msg, ephemeral=True)
