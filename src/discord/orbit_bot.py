import discord
from discord.ext import commands
from discord.ui import View, Button, Modal, TextInput
import json
import asyncio
import requests

intents = discord.Intents.default()
intents.message_content = True
bot = commands.Bot(command_prefix="!", intents=intents)

def get_user_balance(username, host="https://3599-173-187-247-149.ngrok-free.app"):
    try:
        response = requests.get(f"{host}/api/balance/{username}")
        if response.status_code == 200:
            data = response.json()
            return data['total_balance'], data['available_balance'], data['locked_balance']
        else:
            print(f"Error {response.status_code}: {response.json().get('error')}")
            return None
    except Exception as e:
        print(f"Request failed: {e}")
        return None

def get_wallet_balance(username):
    return {
        "address": f"address",
        "available": 0.0,
        "locked": 0.0,
        "total": 0.0,
        "transactions": [],
        "validators": {},
        "security_circle": []
    }



def send_orbit(sender_id, recipient_id, amount):
    return True

def lock_orbit(username, amount, duration):
    return True

def claim_rewards(username):
    return True

# Views and Modals
class WalletDashboard(View):
    def __init__(self, username):
        super().__init__(timeout=None)
        self.user_id = username

    @discord.ui.button(label="Send ORBIT", style=discord.ButtonStyle.primary)
    async def send_orbit_button(self, interaction: discord.Interaction, button: Button):
        await interaction.response.send_modal(SendOrbitModal(self.user_id))

    @discord.ui.button(label="Lock ORBIT", style=discord.ButtonStyle.secondary)
    async def lock_orbit_button(self, interaction: discord.Interaction, button: Button):
        await interaction.response.send_modal(LockOrbitModal(self.user_id))

    @discord.ui.button(label="Claim Rewards", style=discord.ButtonStyle.secondary)
    async def claim_rewards_button(self, interaction: discord.Interaction, button: Button):
        success = claim_rewards(self.user_id)
        msg = "🌟 Rewards claimed!" if success else "❌ Claim failed."
        await interaction.response.send_message(msg, ephemeral=True)

class SendOrbitModal(Modal):
    def __init__(self, username):
        super().__init__(title="Send ORBIT")
        self.user_id = username
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

@bot.command(name="wallet")
async def wallet(ctx):
    username = ctx.author.name
    balance = get_wallet_balance(username)
    total, wallet, locked = get_user_balance(username)

    embed = discord.Embed(title=f"Orbit Wallet", color=0x00ffcc)
    embed.add_field(name="Address", value=username, inline=False)
    embed.add_field(name="Wallet", value=f"{wallet} ORBIT", inline=True)
    embed.add_field(name="Locked", value=f"{locked} ORBIT", inline=True)
    embed.add_field(name="Total", value=f"{total} ORBIT", inline=True)

    explorer_link = f"https://3599-173-187-247-149.ngrok-free.app/address/{username}"
    embed.add_field(name="View on Explorer", value=f"[Open Explorer]({explorer_link})", inline=False)

    embed.add_field(name="Validator Stats", value="{}", inline=False)
    embed.add_field(name="Security Circle", value="{}", inline=False)

    tx_summary = "\n".join([f"{tx['timestamp']}: {tx['from']} ➔ {tx['to']} ({tx['amount']} ORBIT) - {tx['note']}" for tx in balance['transactions']])
    embed.add_field(name="Last Transactions", value=tx_summary, inline=False)

    await ctx.send(embed=embed, view=WalletDashboard(username))

with open('secret', 'r') as file:
    discord_key = file.read()

bot.run(discord_key)
