from discord.ext import commands
import discord
from config import DISCORD_TOKEN

intents = discord.Intents.default()
intents.message_content = True
bot = commands.Bot(command_prefix="!", intents=intents)

# Load commands
from commands.wallet import setup as wallet_setup
wallet_setup(bot)

bot.run(DISCORD_TOKEN)
