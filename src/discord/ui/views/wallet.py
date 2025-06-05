from discord.ui import View, Button, Select
import discord
import asyncio
from commands.wallet_tools import claim_rewards, wallet_info
from api import create_2fa_api, get_user_address, mine_orbit_api, get_user_tokens
from core.ioutil import fetch_chain
from ui.modals import lock_token, send_token


class WalletDashboard(View):
    def __init__(self, discord_id):
        super().__init__(timeout=None)
        self.user_id = discord_id

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

    @discord.ui.button(label="Lock", style=discord.ButtonStyle.secondary)
    async def lock_orbit(self, interaction: discord.Interaction, button: Button):
        await interaction.response.send_modal(lock_token(self.user_id))

    @discord.ui.button(label="Claim Rewards", style=discord.ButtonStyle.secondary)
    async def claim(self, interaction: discord.Interaction, button: Button):
        address = await get_user_address(self.user_id)
        data = await claim_rewards(address)

        if data["status"] == "success":
            msg = (
                f"🎉 **Rewards Claimed!**\n"
                f"• Total Rewards: `{data['rewards']}` Orbit\n"
                f"• Node Fee: `{data['node_fee']}` Orbit\n"
                f"• Net Credited: `{data['net_credited']}` Orbit\n"
                f"• Matured Unlocked: `{data['matured_unlocked']}` Orbit\n"
            )
            if "relock_status" in data:
                msg += f"• {data['relock_status']}"
        elif data["status"] == "cooldown":
            msg = f"🕒 Cooldown active. {data['message']}"
        elif data["status"] == "ok":
            msg = f"ℹ️ {data['message']}"
        else:
            msg = f"❌ Error: {data.get('message', 'Unknown error')}"

        await interaction.response.send_message(msg, ephemeral=True)

class TokenSelectDropdown(Select):
    def __init__(self, uid, token_list):
        self.uid = uid
        options = [discord.SelectOption(label=token) for token in token_list]
        super().__init__(placeholder="Select token to send", options=options, min_values=1, max_values=1)

    async def callback(self, interaction: discord.Interaction):
        token = self.values[0]
        await interaction.response.send_modal(send_token(self.uid, token))

class SendTokenView(View):
    def __init__(self, uid, token_list):
        super().__init__(timeout=60)
        self.add_item(TokenSelectDropdown(uid, token_list))

