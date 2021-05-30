from asyncio import tasks
import discord
import json
import os
import sys
import time

from discord.ext.commands.core import command
sys.path.append(os.path.dirname(os.path.dirname(os.path.abspath(__file__))))

from datetime import datetime, timedelta, timezone
from discord.ext import tasks,commands
from module.ranksys import RankSys
from module.embedKit import EmbedKit

class Rank(commands.Cog):
    def __init__(self, bot):
        self.bot = bot
        self.root = os.path.dirname(__file__)[:-4]
        self.JST = timezone(timedelta(hours=+9), 'JST')
        with open(self.root + '/bot.conf', 'r', encoding='utf-8')as f:
            self.config = json.loads(f.read())
        self.autoUpdate.start()

    async def _rank(self):
        
        guilds = [self.bot.get_guild(gid) for gid in [int(i[:-4]) for i in os.listdir(self.root + '/log/voiceStateLog/')if i[0]!='d']]

        for guild in guilds:

            if guild == None: continue

            # ランク情報を更新
            RankSys.updateRank(guild)
            
            # ランク情報を反映
            guildID = guild.id
            members = guild.members
            guildRoles = {role.name:role.id for role in guild.roles}
            rankRole = self.config['roles']
            with open('%s/log/fixedRank/%s.json' %(self.root, str(guildID)), 'r', encoding='utf-8')as f:
                js = json.loads(f.read())

            for member in members:
                user = member.name
                setRole = None
                oldRank = None
                for role in member.roles:
                    if role.name in rankRole: oldRank = guildRoles[role.name]

                # 適切なランクを割り当て
                if user in js:
                    activityAverage = sum(js[user]['activity'])//7
                    for roleName, minTime in sorted(rankRole.items(), key=lambda x: x[1]):
                        if activityAverage < minTime: break
                        if roleName in guildRoles: setRole = guildRoles[roleName]
                    
                    if setRole==None: continue
                    await member.add_roles(guild.get_role(setRole))
                    
                    # ランクに変動があった場合は古いロールは削除する
                    if oldRank == None: continue
                    if setRole != oldRank:
                        await member.remove_roles(guild.get_role(oldRank))
                    
                    js[member.name]['old'] = guild.get_role(oldRank).name
                    js[member.name]['now'] = guild.get_role(setRole).name
                
                else:
                    # 過去7日間で活動がないユーザーはランク剥奪
                    for role in member.roles:
                        if role.name in rankRole:
                            await member.remove_roles(role)
            
            with open('%s/log/fixedRank/%s.json' %(self.root, str(guildID)), 'w', encoding='utf-8')as f:
                jsonTxt = json.dumps(js, indent=2, ensure_ascii=False)
                f.write(jsonTxt)
        
            emb = EmbedKit.rankUpdate(guildID)
            channels = guild.channels
            for channel in channels:
                if channel.name == self.config['announce']['channel']:
                    await channel.send(embed=emb)
            
    
    @tasks.loop(seconds=10)
    async def autoUpdate(self):
        # 1日1回更新
        # lastRankUpadate.txt は自動更新が最後に行われた時間のUNIXtime
        with open(self.root + '/log/system/lastRankUpadate.txt', 'r', encoding='utf-8') as f:
            lastUpdate = int(f.read())
        
        if 60 < time.time() - lastUpdate:
            if datetime.now(self.JST).strftime('%H:%M') == self.config['rankUpdate']['updateTime']:
                await self._rank()

                with open(self.root + '/log/system/lastRankUpadate.txt', 'w', encoding='utf-8') as f:
                    f.write(str(int(time.time())))

    @commands.command()
    async def rank(self, ctx):
        if not ctx.author.name in self.config['admin']: return None
        await self._rank()

def setup(bot):
    bot.add_cog(Rank(bot))
    print('[cog] Rank was loaded!')