from discord.ui import Modal, TextInput
import discord
import asyncio
from api import verify_2fa_api, send_orbit_api, get_user_address, get_user_balance
from wallet import lock_orbit, wallet_info

BOT_OPS_CHANNEL_ID = 1379630873174872197

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





class BuyTokenModal(Modal):
    def __init__(self, uid):
        super().__init__(title="Buy Tokens")
        self.address = ""
        self.uid = uid

        self.symbol = TextInput(label="Token Symbol", placeholder="e.g., ORBIT")
        self.amount = TextInput(label="Amount", placeholder="e.g., 50", style=discord.TextStyle.short)
        self.price = TextInput(label="Price", placeholder="e.g., 10", style=discord.TextStyle.short)

        self.add_item(self.symbol)
        self.add_item(self.amount)
        self.add_item(self.price)

    async def on_submit(self, interaction: discord.Interaction):
        self.address = await get_user_address(self.uid)
        message = f"[ExchangeRequest] BUY {self.symbol.value.upper()} {self.amount.value} {self.price.value} {self.address}"
        bot_ops_channel = interaction.client.get_channel(BOT_OPS_CHANNEL_ID)

        if bot_ops_channel:
            await bot_ops_channel.send(message)
            await interaction.response.send_message(f"🟢 Sent buy request for `{self.amount.value}` {self.symbol.value.upper()} at `{self.price.value} ORBIT`", ephemeral=True)
        else:
            await interaction.response.send_message("❌ Bot-ops channel not found.", ephemeral=True)


class SellTokenModal(Modal):
    def __init__(self, uid):
        super().__init__(title="Sell Tokens")
        self.address = ""
        self.uid = uid

        self.symbol = TextInput(label="Token Symbol", placeholder="e.g., ORBIT")
        self.amount = TextInput(label="Amount", placeholder="e.g., 50", style=discord.TextStyle.short)
        self.price = TextInput(label="Price", placeholder="e.g., 10", style=discord.TextStyle.short)

        self.add_item(self.symbol)
        self.add_item(self.amount)
        self.add_item(self.price)

    async def on_submit(self, interaction: discord.Interaction):
        self.address = await get_user_address(self.uid)
        message = f"[ExchangeRequest] SELL {self.symbol.value.upper()} {self.amount.value} {self.price.value} {self.address}"
        bot_ops_channel = interaction.client.get_channel(BOT_OPS_CHANNEL_ID)

        if bot_ops_channel:
            await bot_ops_channel.send(message)
            await interaction.response.send_message(f"🔴 Sent sell request for `{self.amount.value}` {self.symbol.value.upper()} at `{self.price.value} ORBIT`", ephemeral=True)
        else:
            await interaction.response.send_message("❌ Bot-ops channel not found.", ephemeral=True)


class BuyFromExchangeModal(Modal):
    def __init__(self, uid):
        super().__init__(title="Buy From Exchange")
        self.address = ""
        self.uid = uid

        self.symbol = TextInput(label="Token Symbol", placeholder="e.g., ORBIT")
        self.amount = TextInput(label="Amount", placeholder="e.g., 50", style=discord.TextStyle.short)

        self.add_item(self.symbol)
        self.add_item(self.amount)

    async def on_submit(self, interaction: discord.Interaction):
        self.address = await get_user_address(self.uid)
        message = f"[ExchangeRequest] BUYEX {self.symbol.value.upper()} {self.amount.value} {self.address}"
        bot_ops_channel = interaction.client.get_channel(BOT_OPS_CHANNEL_ID)

        if bot_ops_channel:
            await bot_ops_channel.send(message)
            await interaction.response.send_message(
                f"🟢 Sent direct exchange buy request for `{self.amount.value}` {self.symbol.value.upper()}",
                ephemeral=True
            )
        else:
            await interaction.response.send_message("❌ Bot-ops channel not found.", ephemeral=True)


TOKEN_CREATION_FEE = 250  # ORBIT

class CreateTokenModal(Modal):
    def __init__(self, uid):
        super().__init__(title="Orbit Exchange - Create Token")
        self.uid = uid
        self.address = ""
        self.name = TextInput(label="Token Name", placeholder="ExampleToken", max_length=32)
        self.symbol = TextInput(label="Symbol", placeholder="EXT", max_length=8)
        self.supply = TextInput(label="Total Supply", placeholder="1000000", max_length=18)
        self.add_item(self.name)
        self.add_item(self.symbol)
        self.add_item(self.supply)

    async def on_submit(self, interaction: discord.Interaction):
        self.address = await get_user_address(self.uid)

        try:
            supply_val = float(self.supply.value)
            if supply_val <= 0:
                raise ValueError("Supply must be positive.")
        except ValueError:
            await interaction.response.send_message("❌ Invalid supply amount.", ephemeral=True)
            return

        total, available, locked = await get_user_balance(self.address)
        if available < TOKEN_CREATION_FEE:
            await interaction.response.send_message(
                f"❌ You need at least {TOKEN_CREATION_FEE} ORBIT to list a token. Your balance: {balance:.2f}",
                ephemeral=True
            )
            return

        channel = interaction.client.get_channel(BOT_OPS_CHANNEL_ID)
        if channel:
            await channel.send(
                f"[ExchangeRequest] CREATE {self.name.value.strip()} {self.symbol.value.strip().upper()} {supply_val} {self.address}"
            )
            await interaction.response.send_message(
                f"✅ Token listing request submitted to Exchange Bot.",
                ephemeral=True
            )
        else:
            await interaction.response.send_message("❌ Could not reach Exchange Bot channel.", ephemeral=True)



class MyTokensModal(Modal):
    def __init__(self, uid, portfolio_text="No tokens found."):
        super().__init__(title="My Tokens")
        self.uid = uid

        self.portfolio_display = TextInput(
            label="Your Token Holdings",
            style=discord.TextStyle.paragraph,
            required=False,
            max_length=4000
        )
        self.portfolio_display.default = portfolio_text

        self.add_item(self.portfolio_display)

    async def on_submit(self, interaction: discord.Interaction):
        await interaction.response.send_message("✅ Portfolio viewed.", ephemeral=True)
