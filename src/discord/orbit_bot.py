import discord
from discord.ext import commands
from discord.ui import View, Button, Modal, TextInput
import json
import asyncio

intents = discord.Intents.default()
intents.message_content = True
bot = commands.Bot(command_prefix="!", intents=intents)

# Dummy blockchain interaction functions (replace with real Orbit functions)
def get_wallet_balance(user_id):
    return {
        "address": f"orbit_{user_id[-6:]}",
        "available": 123.45,
        "staked": 100.00,
        "locked": 50.00,
        "rewards": 5.67,
        "transactions": [
            {"to": "orbit_111111", "from": "orbit_222222", "amount": 12.5, "note": "Payment", "timestamp": "2025-05-28"},
            {"to": "orbit_333333", "from": f"orbit_{user_id[-6:]}", "amount": 6.0, "note": "Gift", "timestamp": "2025-05-27"}
        ],
        "validators": {
            "uptime": "98.5%",
            "trust": "4.8/5",
            "blocks_validated": 42
        },
        "security_circle": ["orbit_222222", "orbit_333333", "orbit_444444"]
    }

def send_orbit(sender_id, recipient_id, amount):
    return True

def stake_orbit(user_id, amount):
    return True

def lock_orbit(user_id, amount, duration):
    return True

def claim_rewards(user_id):
    return True

# Views and Modals
class WalletDashboard(View):
    def __init__(self, user_id):
        super().__init__(timeout=None)
        self.user_id = user_id

    @discord.ui.button(label="Send ORBIT", style=discord.ButtonStyle.primary)
    async def send_orbit_button(self, interaction: discord.Interaction, button: Button):
        await interaction.response.send_modal(SendOrbitModal(self.user_id))

    @discord.ui.button(label="Stake ORBIT", style=discord.ButtonStyle.success)
    async def stake_orbit_button(self, interaction: discord.Interaction, button: Button):
        await interaction.response.send_modal(StakeOrbitModal(self.user_id))

    @discord.ui.button(label="Lock ORBIT", style=discord.ButtonStyle.secondary)
    async def lock_orbit_button(self, interaction: discord.Interaction, button: Button):
        await interaction.response.send_modal(LockOrbitModal(self.user_id))

    @discord.ui.button(label="Claim Rewards", style=discord.ButtonStyle.secondary)
    async def claim_rewards_button(self, interaction: discord.Interaction, button: Button):
        success = claim_rewards(self.user_id)
        msg = "🌟 Rewards claimed!" if success else "❌ Claim failed."
        await interaction.response.send_message(msg, ephemeral=True)

class SendOrbitModal(Modal):
    def __init__(self, user_id):
        super().__init__(title="Send ORBIT")
        self.user_id = user_id
        self.recipient = TextInput(label="Recipient ID")
        self.amount = TextInput(label="Amount")
        self.note = TextInput(label="Note", required=False)
        self.add_item(self.recipient)
        self.add_item(self.amount)
        self.add_item(self.note)

    async def on_submit(self, interaction: discord.Interaction):
        success = send_orbit(self.user_id, self.recipient.value, float(self.amount.value))
        msg = "✉️ Transaction successful!" if success else "⛔️ Transaction failed."
        await interaction.response.send_message(msg, ephemeral=True)

class StakeOrbitModal(Modal):
    def __init__(self, user_id):
        super().__init__(title="Stake ORBIT")
        self.user_id = user_id
        self.amount = TextInput(label="Amount to Stake")
        self.add_item(self.amount)

    async def on_submit(self, interaction: discord.Interaction):
        success = stake_orbit(self.user_id, float(self.amount.value))
        msg = "🔄 Staking successful!" if success else "⚠️ Staking failed."
        await interaction.response.send_message(msg, ephemeral=True)

class LockOrbitModal(Modal):
    def __init__(self, user_id):
        super().__init__(title="Lock ORBIT")
        self.user_id = user_id
        self.amount = TextInput(label="Amount to Lock")
        self.duration = TextInput(label="Lock Duration (days)")
        self.add_item(self.amount)
        self.add_item(self.duration)

    async def on_submit(self, interaction: discord.Interaction):
        success = lock_orbit(self.user_id, float(self.amount.value), int(self.duration.value))
        msg = "🔒 Lockup successful!" if success else "⛔️ Lockup failed."
        await interaction.response.send_message(msg, ephemeral=True)

@bot.command(name="wallet")
async def wallet(ctx):
    user_id = str(ctx.author.id)
    balance = get_wallet_balance(user_id)

    embed = discord.Embed(title=f"{ctx.author.name}'s ORBIT Wallet", color=0x00ffcc)
    embed.add_field(name="Address", value=balance["address"], inline=False)
    embed.add_field(name="Available", value=f"{balance['available']} ORBIT", inline=True)
    embed.add_field(name="Staked", value=f"{balance['staked']} ORBIT", inline=True)
    embed.add_field(name="Locked", value=f"{balance['locked']} ORBIT", inline=True)
    embed.add_field(name="Rewards", value=f"{balance['rewards']} ORBIT", inline=True)

    explorer_link = f"https://3599-173-187-247-149.ngrok-free.app/"
    embed.add_field(name="View on Explorer", value=f"[Open Explorer]({explorer_link})", inline=False)

    embed.add_field(name="Validator Stats", value=f"Uptime: {balance['validators']['uptime']}\nTrust: {balance['validators']['trust']}\nBlocks: {balance['validators']['blocks_validated']}", inline=False)
    embed.add_field(name="Security Circle", value=", ".join(balance['security_circle']), inline=False)

    tx_summary = "\n".join([f"{tx['timestamp']}: {tx['from']} ➔ {tx['to']} ({tx['amount']} ORBIT) - {tx['note']}" for tx in balance['transactions']])
    embed.add_field(name="Last Transactions", value=tx_summary, inline=False)

    await ctx.send(embed=embed, view=WalletDashboard(user_id))

# Run the bot
