import json
import os
import sys
sys.path.append(os.path.dirname(os.path.dirname(os.path.abspath(__file__))))

from discord.ext import commands
from module.ranksys import RankSys

class Rank(commands.Cog):
    def __init__(self, bot):
        self.bot = bot
        self.root = os.path.dirname(__file__)[:-4]
        with open(self.root + '/bot.conf', 'r', encoding='utf-8')as f:
            self.config = json.loads(f.read())
    
    @commands.command()
    async def rank(self, ctx):
        # ランク情報を更新
        RankSys.updateRank(ctx)
        
        # ランク情報を反映
        guildID = ctx.guild.id
        members = ctx.guild.members
        guildRoles = {role.name:role.id for role in ctx.guild.roles}
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
                activityAverage = sum([i for i in js[user]])//7
                for roleName, minTime in sorted(rankRole.items(), key=lambda x: x[1]):
                    if activityAverage < minTime: break
                    if roleName in guildRoles: setRole = guildRoles[roleName]
                
                if setRole==None: continue
                await member.add_roles(ctx.guild.get_role(setRole))
                
                # ランクに変動があった場合は古いロールは削除する
                if oldRank == None: continue
                if setRole != oldRank:
                    await member.remove_roles(ctx.guild.get_role(oldRank))
            
            else:
                # 過去7日間で活動がないユーザーはランク剥奪
                for role in member.roles:
                    if role.name in rankRole:
                        await member.remove_roles(role)

def setup(bot):
    bot.add_cog(Rank(bot))
    print('[cog] Rank was loaded!')