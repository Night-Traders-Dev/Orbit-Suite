from discord.ui import Modal, TextInput, Select
import discord
import asyncio
from core.ioutil import fetch_chain
from api import verify_2fa_api, send_orbit_api, get_user_address, get_user_balance, get_user_tokens
from commands.wallet_tools import lock_orbit, wallet_info
from core.tx_util.tx_types import TXExchange


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
