from discord.ui import Modal, TextInput, Select
import discord
import asyncio
from core.ioutil import fetch_chain
from api import verify_2fa_api, send_orbit_api, get_user_address, get_user_balance, get_user_tokens
from commands.wallet_tools import lock_orbit, wallet_info
from core.tx_util.tx_types import TXExchange


class SendTokenModal(Modal):
    def __init__(self, uid, token_symbol):
        super().__init__(title=f"Send {token_symbol}")
        self.uid = uid
        self.token_symbol = token_symbol

        self.recipient = TextInput(label="Recipient ID", required=True)
        self.amount = TextInput(label="Amount", required=True)
        self.totp = TextInput(label="2FA Code", required=True)

        self.add_item(self.recipient)
        self.add_item(self.amount)
        self.add_item(self.totp)

    async def on_submit(self, interaction: discord.Interaction):
        from api import get_user_address, send_orbit_api, verify_2fa_api
        from ui.views.wallet import WalletDashboard, wallet_info

        address = await get_user_address(self.uid)
        await interaction.response.defer(ephemeral=True)

        try:
            amount = float(self.amount.value)
        except ValueError:
            await interaction.followup.send("⛔️ Invalid amount format.", ephemeral=True)
            return

        if not await verify_2fa_api(address, self.totp.value):
            await interaction.followup.send("⛔️ Invalid 2FA code.", ephemeral=True)
            return

        if self.token_symbol.lower() != "orbit":
            token_tx = TXExchange.create_token_transfer_tx(
            sender=address,
            receiver=self.recipient.value,
            amount=amount,
            token_symbol=self.token_symbol.upper(),
            note=""
            )
            orbit_amount = 0.5
        else:
            orbit_amount = amount
            token_tx = ""

        success = await send_orbit_api(address, self.recipient.value, orbit_amount, token_tx)
        msg = f"✉️ Sent {amount} {self.token_symbol} to {self.recipient.value}" if success else "⛔️ Transaction failed."
        await interaction.followup.send(msg, ephemeral=True)

        embed = await wallet_info(self.uid)
        await interaction.message.edit(embed=embed, view=WalletDashboard(self.uid), delete_after=60)
