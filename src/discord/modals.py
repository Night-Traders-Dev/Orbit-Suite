from discord.ui import Modal, TextInput, Select
import discord
import asyncio
from core.ioutil import fetch_chain
from api import verify_2fa_api, send_orbit_api, get_user_address, get_user_balance, get_user_tokens
from wallet import lock_orbit, wallet_info

BOT_OPS_CHANNEL_ID = 1379630873174872197


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
        from views import WalletDashboard, wallet_info

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

        success = await send_orbit_api(address, self.recipient.value, amount, self.token_symbol)
        msg = f"✉️ Sent {amount} {self.token_symbol} to {self.recipient.value}" if success else "⛔️ Transaction failed."
        await interaction.followup.send(msg, ephemeral=True)

        embed = await wallet_info(self.uid)
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
        self.amount = TextInput(label="Amount", placeholder="e.g., 50")
        self.price = TextInput(label="Price", placeholder="e.g., 10", style=discord.TextStyle.short)

        self.add_item(self.symbol)
        self.add_item(self.amount)
        self.add_item(self.price)

    async def on_submit(self, interaction: discord.Interaction):
        self.address = await get_user_address(self.uid)
        message = f"[ExchangeRequest] BUY {self.symbol.value.upper()} {self.price.value} {self.amount.value} {self.address}"
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
        self.amount = TextInput(label="Amount", placeholder="e.g., 50")
        self.price = TextInput(label="Price", placeholder="e.g., 10", style=discord.TextStyle.short)

        self.add_item(self.symbol)
        self.add_item(self.amount)
        self.add_item(self.price)

    async def on_submit(self, interaction: discord.Interaction):
        self.address = await get_user_address(self.uid)
        message = f"[ExchangeRequest] SELL {self.symbol.value.upper()} {self.price.value} {self.amount.value} {self.address}"
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


class ViewOrdersModal(Modal):
    def __init__(self, uid):
        super().__init__(title="View Token Orders")
        self.uid = uid
        self.symbol = TextInput(label="Token Symbol", placeholder="e.g., ORBIT")
        self.add_item(self.symbol)

    async def on_submit(self, interaction: discord.Interaction):
        token = self.symbol.value.upper()
        chain = fetch_chain()

        buy_orders = []
        sell_orders = []

        for block in reversed(chain):
            for tx in block.get("transactions", []):
                note = tx.get("note")
                if not isinstance(note, dict):
                    continue
                tx_type = note.get("type", {})

                if "buy_token" in tx_type:
                    data = tx_type["buy_token"]
                    if data.get("symbol") == token:
                        buy_orders.append({
                            "address": data.get("buyer") or tx.get("sender"),
                            "amount": data.get("amount"),
                            "price": data.get("price"),
                        })
                elif "sell_token" in tx_type:
                    data = tx_type["sell_token"]
                    if data.get("symbol") == token:
                        sell_orders.append({
                            "address": data.get("seller") or tx.get("sender"),
                            "amount": data.get("amount"),
                            "price": data.get("price"),
                        })

        embed = discord.Embed(title=f"📈 {token} Order Book", color=discord.Color.teal())
        if not buy_orders and not sell_orders:
            embed.description = "No recent buy or sell orders found."
        else:
            if buy_orders:
                embed.add_field(
                    name="🟢 Buy Orders",
                    value="\n".join([
                        f"`{o['amount']} @ {o['price']} ORB` — `{o['address'][:8]}...`"
                        for o in buy_orders[:10]
                    ]) or "None",
                    inline=False
                )
            if sell_orders:
                embed.add_field(
                    name="🔴 Sell Orders",
                    value="\n".join([
                        f"`{o['amount']} @ {o['price']} ORB` — `{o['address'][:8]}...`"
                        for o in sell_orders[:10]
                    ]) or "None",
                    inline=False
                )

        await interaction.response.send_message(embed=embed, ephemeral=True)
