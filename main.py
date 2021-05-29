from json import load
from discord import activity, client
from discord.ext import commands

import csv
import time
import discord
import os


ROOT = os.path.dirname(__file__)
TOKEN = input('please token here: ')
INTENTS = discord.Intents.all()

bot = commands.Bot(command_prefix='srb ', intents=INTENTS)

# Cog の読み込み
def loadCogs():
    cogs = os.listdir(ROOT + '/cog')
    for cog in cogs:
        if(cog[len(cog)-3:] == '.py'):
            bot.load_extension('cog.' + str(cog[:-3]))

# 初期化
@bot.event
async def on_ready():
    await bot.change_presence(activity=discord.Game(name='srb help をチャットに入力!'))


# VoiceStatus を監視するevent
@bot.event
async def on_voice_state_update(member, before, after):
    user = member.name
    beforeState = before.channel
    afterState = after.channel
    guildID = str(member.guild.id)

    # 関係ないステータス更新は記録しない
    if beforeState == afterState: return
    
    with open(ROOT+'/log/voiceStateLog/'+ guildID +'.csv', 'a', encoding='utf-8') as f:
        writer = csv.writer(f)
        # log/voiceStateLog.csv のフォーマットは [ユーザー名, 遷移前のボイチャ名, 遷移後のボイチャ名, 遷移した時間]
        writer.writerow([user, str(beforeState), str(afterState), str(int(time.time()))])


loadCogs()
bot.run(TOKEN)