from discord.ext import commands

import csv
import json
import time
import discord
import os
import sys

# コマンドライン引数を受け取る
_arg = sys.argv[1:]

# コマンドライン引数の検証
try:
    if len(_arg) == 1:
        tokenCheck = _arg[0]
        developMode = False

    elif len(_arg) == 2:
        if _arg[0] in ['True', 'False']:
            developMode = _arg[0] == 'True'

        else:
            raise ValueError('Illegal argument')

        tokenCheck = _arg[1]

    else:
        raise ValueError('Illegal argument')

except:
    print('---')
    print('Please try again: python3 [path] [develop mode] [bot token]')
    print('[path] = Path of this file')
    print('[develop mode] = Enter true if booted in "develop mode", false otherwise. (This argument is optional argument. Default is "False".)')
    print('[bot token] = Please enter to bot token.')
    print('---')
    exit()


TOKEN = tokenCheck
DEVELOPMODE = developMode
INTENTS = discord.Intents.all()
ROOT = os.path.dirname(__file__)

with open(ROOT + '/bot.conf', 'r', encoding='utf-8') as f:
    CONFIG = json.loads(f.read())

if DEVELOPMODE:
    bot = commands.Bot(command_prefix=CONFIG['bot']['developModeCommandPrefix'], intents=INTENTS)

else:
    bot = commands.Bot(command_prefix=CONFIG['bot']['developModeCommandPrefix'], intents=INTENTS)


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

# 単語に反応するおまけ要素
@bot.event
async def on_message(message):
    phrase = CONFIG['phrase']
    if message.content in phrase:
        await message.channel.send(phrase[message.content])
    await bot.process_commands(message)

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