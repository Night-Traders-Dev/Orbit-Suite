# bot.py
import discord
from discord.ext import commands
from config import DISCORD_TOKEN
from events.events import register_events

intents = discord.Intents.all()
intents.messages = True
intents.guilds = True

bot = commands.Bot(command_prefix="!", intents=intents)

# Register handlers
register_events(bot)

# Run the bot
if __name__ == "__main__":
    bot.run(DISCORD_TOKEN)
