from discord.ext import commands
from discord import app_commands
import discord
from configure import DISCORD_TOKEN
from commands.commands import setup as wallet_setup

intents = discord.Intents.all()
intents.message_content = True
bot = commands.Bot(command_prefix="!", intents=intents)
GUILD = discord.Object(id=1376608254741713008)


@bot.event
async def on_ready():
    try:
        wallet_setup(bot, GUILD)
        synced = await bot.tree.sync(guild=GUILD)
        print(f"Synced {len(synced)}")
    except Exception as e:
        print(e)
    print(f'Bot Name: {bot.user}')


bot.run(DISCORD_TOKEN)
