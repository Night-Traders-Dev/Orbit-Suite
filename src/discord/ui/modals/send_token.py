import discord
from discord.ui import Modal, TextInput
from api import get_user_address, verify_2fa_api, send_orbit_api
from core.tx_util.tx_types import TXExchange
from ui.views.wallet import WalletDashboard, wallet_info

class SendTokenModal(Modal):
    def __init__(self, uid: str, token_symbol: str):
        super().__init__(title=f"Send {token_symbol}")
        self.uid = uid
        self.token_symbol = token_symbol

        self.recipient = TextInput(label="Recipient ID", required=True)
        self.amount    = TextInput(label="Amount",       required=True)
        self.totp      = TextInput(label="2FA Code",     required=True)

        self.add_item(self.recipient)
        self.add_item(self.amount)
        self.add_item(self.totp)

    async def on_submit(self, interaction: discord.Interaction):
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
            orbit_amount = 0.5  # gas-fee in ORBIT
        else:
            orbit_amount = amount
            token_tx = None

        success = await send_orbit_api(address, self.recipient.value, orbit_amount, token_tx)
        msg = (
            f"✉️ Sent {amount} {self.token_symbol} to {self.recipient.value}"
            if success else
            "⛔️ Transaction failed."
        )
        await interaction.followup.send(msg, ephemeral=True)

        embed = await wallet_info(self.uid)

        try:
            await interaction.message.edit(
                embed=embed,
                view=WalletDashboard(self.uid),
                delete_after=60
            )
        except discord.NotFound:
            # fallback: original message was deleted or expired
            await interaction.channel.send(
                embed=embed,
                view=WalletDashboard(self.uid),
                delete_after=60
            )