import discord
from discord.ext import commands
from discord.ui import View, Button, Modal, TextInput
import json
import asyncio, aiohttp
import requests

intents = discord.Intents.default()
intents.message_content = True
bot = commands.Bot(command_prefix="!", intents=intents)
explorer = "https://3599-173-187-247-149.ngrok-free.app"

def get_user_balance(username, host=explorer):
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


async def create_2fa_api(username):
    payload = {
        "username": username,
    }

    async with aiohttp.ClientSession() as session:
        try:
            async with session.post(f"{explorer}/api/create_2fa", json=payload) as response:
                if response.status == 200:
                    data = await response.json()
                    return data.get("message")
        except Exception as e:
            return False, f"Request failed: {str(e)}"

async def verify_2fa_api(username, totp):
    payload = {
        "username": username,
        "totp": totp
    }

    async with aiohttp.ClientSession() as session:
        try:
            async with session.post(f"{explorer}/api/verify_2fa", json=payload) as response:
                if response.status == 200:
                    data = await response.json()
                    return data.get("message")
                else:
                    data = await response.json()
                    return data.get("message")
        except Exception as e:
            return False, f"Request failed: {str(e)}"

async def send_orbit_api(sender, recipient, amount):
    payload = {
        "sender": sender,
        "recipient": recipient,
        "amount": amount
    }

    async with aiohttp.ClientSession() as session:
        try:
            async with session.post(f"{explorer}/api/send", json=payload) as response:
                if response.status == 200:
                    data = await response.json()
                    return True, data.get("message", "Transaction successful.")
                else:
                    data = await response.json()
                    return False, data.get("error") or data.get("message", "Unknown error.")
        except Exception as e:
            return False, f"Request failed: {str(e)}"


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
        self.totp = TextInput(label="2FA", required=True)
        self.add_item(self.recipient)
        self.add_item(self.amount)
        self.add_item(self.totp)

    async def on_submit(self, interaction: discord.Interaction):
        result = await verify_2fa_api(self.user_id, self.totp)
        if not result:
            msg = "⛔️ Transaction failed."
            await interaction.response.send_message(msg, ephemeral=True)
            pass
        else:
            success = await send_orbit_api(self.user_id, self.recipient.value, float(self.amount.value))
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

class Register2FAView(View):
    def __init__(self, username):
        super().__init__(timeout=None)
        self.user_id = username

    @discord.ui.button(label="Register 2FA", style=discord.ButtonStyle.primary)
    async def register(self, interaction: discord.Interaction, button: discord.ui.Button):
        secret = await create_2fa_api(self.user_id)

        await interaction.response.send_message(
            content=f"Here is your 2FA QR code. {secret}",
            ephemeral=True
        )

@bot.command(name="register2fa")
async def register_2fa(ctx):
    view = Register2FAView(ctx.author.name)
    await ctx.send("Click the button below to register for 2FA.", view=view)

@bot.command(name="wallet")
async def wallet(ctx):
    try:
        await ctx.message.delete()
    except discord.Forbidden:
        pass
    except discord.HTTPException:
        pass
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

    await ctx.send(embed=embed, view=WalletDashboard(username), delete_after=60)

with open('secret', 'r') as file:
    discord_key = file.read()

bot.run(discord_key)
