from discord import activity, client
from discord.ext import commands
import discord
import os

ROOT = os.path.dirname(__file__)
TOKEN = input('please token here: ')
bot = commands.Bot(command_prefix='srb ')

@bot.event
async def on_ready():
    await bot.change_presence(activity=discord.Game(name='\'srb help\''))

bot.run(TOKEN)