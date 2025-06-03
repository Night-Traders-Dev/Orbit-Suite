from discord.ui import Modal, TextInput
import discord
from api import verify_2fa_api, send_orbit_api, get_user_address
from wallet import lock_orbit, wallet_info

class SendOrbitModal(Modal):
    def __init__(self, uid):
        super().__init__(title="Send ORBIT")
        self.address  = ""
        self.uid = uid
        self.recipient = TextInput(label="Recipient ID")
        self.amount = TextInput(label="Amount")
        self.totp = TextInput(label="2FA Code", required=True)
        self.add_item(self.recipient)
        self.add_item(self.amount)
        self.add_item(self.totp)

    async def on_submit(self, interaction: discord.Interaction):
        self.address = await get_user_address(self.uid)
        await interaction.response.defer(ephemeral=True)
        try:
            amount = float(self.amount.value)
        except ValueError:
            await interaction.followup.send("⛔️ Invalid amount format.", ephemeral=True)
            return
        if not await verify_2fa_api(self.address, self.totp.value):
            await interaction.followup.send("⛔️ Invalid 2FA code.", ephemeral=True)
            return

        success = await send_orbit_api(self.address, self.recipient.value, amount)
        msg = f"✉️ Transaction successful!\nSent {amount} Orbit to {self.recipient}" if success else "⛔️ Transaction failed."
        await interaction.followup.send(msg, ephemeral=True)
        embed = await wallet_info(self.uid)
        from views import WalletDashboard
        await interaction.message.edit(embed=embed, view=WalletDashboard(self.uid), delete_after=60)


class LockOrbitModal(Modal):
    def __init__(self, uid):
        super().__init__(title="Lock ORBIT")
        self.address = ""
        self.uid = uid
        self.amount = TextInput(label="Amount to Lock")
        self.duration = TextInput(label="Duration in days (min 1, max 1825)")
        self.totp = TextInput(label="2FA Code", required=True)
        self.add_item(self.amount)
        self.add_item(self.duration)
        self.add_item(self.totp)

    async def on_submit(self, interaction: discord.Interaction):
        self.address = await get_user_address(self.uid)
        if not await verify_2fa_api(self.address, self.totp.value):
            await interaction.followup.send("⛔️ Invalid 2FA code.", ephemeral=True)
            return
        success = await lock_orbit(self.address, float(self.amount.value), int(self.duration.value))
        msg = "🔒 Lockup successful!" if success else "⛔️ Lockup failed."
        await interaction.response.send_message(msg, ephemeral=True)
        embed = await wallet_info(self.uid)
        from views import WalletDashboard
        await interaction.message.edit(embed=embed, view=WalletDashboard(self.uid), delete_after=60)



class TokenListingModal(Modal):
    def __init__(self):
        super().__init__(title="Orbit Exchange")
        name = TextInput(label="Token Name", placeholder="ExampleToken", max_length=32)
        symbol = TextInput(label="Symbol", placeholder="EXT", max_length=8)
        supply = TextInput(label="Total Supply", placeholder="1000000", max_length=18)

    async def on_submit(self, interaction: discord.Interaction):
        await interaction.response.send_message(
            f"✅ Token listed:\n**Name:** {self.name}\n**Symbol:** {self.symbol}\n**Supply:** {self.supply}",
            ephemeral=True
        )
