from discord.ui import View, Button, Select
import discord
import asyncio
from commands.wallet_tools import claim_rewards, wallet_info
from api import create_2fa_api, get_user_address, mine_orbit_api, get_user_tokens
from core.ioutil import fetch_chain
from ui.modals.send_token import SendTokenModal
from ui.modals.lock_token import LockOrbitModal


class WalletDashboard(View):
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

    @discord.ui.button(label="Send", style=discord.ButtonStyle.primary)
    async def send_orbit(self, interaction: discord.Interaction, button: Button):
        address = await get_user_address(self.user_id)
        tokens = get_user_tokens(address)
        if not tokens:
            await interaction.response.send_message("You don’t own any tokens to send.", ephemeral=True)
            return

        await interaction.response.send_message(
            "Select a token to send:", view=SendTokenView(self.user_id, tokens), ephemeral=True
        )

    @discord.ui.button(label="Mine", style=discord.ButtonStyle.green)
    async def mine_orbit(self, interaction: discord.Interaction, button: Button):
        address = await get_user_address(self.user_id)
        status, result = await mine_orbit_api(address)

        if status == "fail":
            msg = f"❌ {result}"
        else:
            msg = (
                f"⛏️ **Mining Started**\n"
                f"📈 Rate: `{result['rate']}` Orbit/sec\n"
                f"💰 Total Mined: `{result['mined']}` Orbit\n"
                f"🏆 User Reward: `{result['payout']}` Orbit"
            )

        await interaction.response.send_message(msg, ephemeral=True)
        embed = await wallet_info(self.user_id)
        await interaction.message.edit(embed=embed, view=WalletDashboard(self.user_id), delete_after=60)

    @discord.ui.button(label="Private Wallet", style=discord.ButtonStyle.danger)
    async def open_private_channel(self, interaction: discord.Interaction, button: Button):
        await interaction.response.defer(ephemeral=True)
        guild = interaction.guild
        author = interaction.user
        bot_member = guild.me

        channel_name = f"private-{author.name}".replace(" ", "-").lower()
        existing = discord.utils.get(guild.text_channels, name=channel_name)

        if existing:
            await interaction.response.send_message(
                f"⚠️ You already have a private channel: {existing.mention}",
                ephemeral=True
            )
            return

        await interaction.message.delete()

        # Set permissions
        overwrites = {
            guild.default_role: discord.PermissionOverwrite(view_channel=False),
            author: discord.PermissionOverwrite(view_channel=True, send_messages=True, read_message_history=True),
            bot_member: discord.PermissionOverwrite(view_channel=True, send_messages=True, manage_channels=True),
        }

        category = discord.Object(id=1382136935031771257)


        # Create the private channel
        private_channel = await guild.create_text_channel(
            name=channel_name,
            overwrites=overwrites,
            category=category,
            reason=f"Private wallet for {author.display_name}"
        )

        await interaction.followup.send(f"✅ Private channel created: {private_channel.mention}", ephemeral=True)

        # Send a new message with the same view in the private channel
        await private_channel.send(f"👋 Welcome {author.mention}! Reopening your dashboard...")
        await private_channel.send(
            embed=await wallet_info(author.id),
            view=WalletDashboard(author.id)  # Use a new instance of the view
        )


class TokenSelectDropdown(Select):
    def __init__(self, uid, token_list):
        self.uid = uid
        options = [discord.SelectOption(label=token) for token in token_list]
        super().__init__(placeholder="Select token to send", options=options, min_values=1, max_values=1)

    async def callback(self, interaction: discord.Interaction):
        token = self.values[0]
        await interaction.response.send_modal(SendTokenModal(self.uid, token))

class SendTokenView(View):
    def __init__(self, uid, token_list):
        super().__init__(timeout=60)
        self.add_item(TokenSelectDropdown(uid, token_list))

