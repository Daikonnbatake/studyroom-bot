import discord
import json
import os

from datetime import datetime, timedelta, timezone
from discord import embeds
from discord.ext import commands
from discord.ext.commands import bot
from discord.ext.commands.core import command

class Manage(commands.Cog):

    def __init__(self, bot):
        self.bot = bot
        self.root = os.path.dirname(__file__)[:-4]
        self.JST = timezone(timedelta(hours=+9), 'JST')
        with open(self.root + '/bot.conf', 'r', encoding='utf-8')as f:
            self.config = json.loads(f.read())

    # member オブジェクトが admin に該当するかを確認する
    def isAdmin(self, member):
        return member.name in self.config['bot']['admin']

    # Cogのリロード
    def _reloadCog(self):
        cogs = os.listdir(self.root + '/cog')
        for cog in cogs:
            if(cog[len(cog)-3:] == '.py'):
                self.bot.reload_extension('cog.' + str(cog[:-3]))

    # conf ファイルの出力
    async def _outputConf(self, ctx):
        conf = json.dumps(self.config, indent=2, ensure_ascii=False)
        emb = discord.Embed(title='bot.conf', description= '```' + conf + '```')
        await ctx.send(embed=emb)

    # reload コマンド
    @commands.command()
    async def reload(self, ctx):
        if self.isAdmin(ctx.message.author):
            self._reloadCog()
    
    # output コマンド
    @commands.command()
    async def output(self, ctx, op=None):
        if self.isAdmin(ctx.message.author):
            if op == None: return
            if op == 'conf': await self._outputConf(ctx)

def setup(bot):
    bot.add_cog(Manage(bot))
    print('[cog] Manage was loaded!')