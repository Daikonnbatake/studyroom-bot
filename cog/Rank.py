from asyncio import tasks
import csv
import discord
import json
import os
import sys
import time
from discord import activity

from discord.ext.commands.core import command
sys.path.append(os.path.dirname(os.path.dirname(os.path.abspath(__file__))))

from datetime import datetime, timedelta, timezone
from discord.ext import tasks,commands

class Rank(commands.Cog):
    def __init__(self, bot):
        self.bot = bot
        self.root = os.path.dirname(__file__)[:-4]
        self.JST = timezone(timedelta(hours=+9), 'JST')
        self.lastUpdate = 0
        with open(self.root + '/bot.conf', 'r', encoding='utf-8')as f:
            self.config = json.loads(f.read())
        self.autoUpdate.start()

    # guildごとのランク更新処理
    def _updateGuild(self, guild):
        guildID = guild.id
        members = guild.members
        rankRoles = self.config['rankRoles']
        rankRoles[''] = -1
        sortedRankRoles = sorted([[key,value] for key, value in self.config['rankRoles'].items()], key=lambda x: x[1])
        enableChannels = set(self.config['rankEnable']['voice'])
        voiceStateLogPath = '%s/log/voiceStateLog/%s.csv' % (self.root, guildID)
        futureVoiceStateLog = list()
        nowUnixTime = int(time.time())
        separateLogsForMembers = {member.name : [] for member in members}
        fixedRank = dict()
        day = 86400

        # fixedRank のフォーマット
        for member in members:
            name = member.name
            rank = [role.name for role in member.roles if role.name in rankRoles]
            rank = '' if rank == [] else rank[0]
            fixedRank[name] = {'activity':[0]*7, 'oldRank':rank, 'nowRank':'', 'status':'幽霊'}

        with open(voiceStateLogPath, 'r', encoding='utf-8') as voiceStateLog:
            
            for voiceStateLogOneLine in csv.reader(voiceStateLog):

                # もし空行を読み取ったなら処理を飛ばす。
                # 空でなければ変数に代入する。
                if len(voiceStateLogOneLine)==4: userName, beforeSt, afterSt, timeStamp = voiceStateLogOneLine
                else:continue

                timeStamp = int(timeStamp)

                # 7日以上前のログは参照しない
                if 6 < (nowUnixTime - timeStamp)//day: continue

                # ランク対象外のボイスチャンネルの入退室はカウントしない
                if (not beforeSt in enableChannels) and (not afterSt in enableChannels): continue
                
                # ユーザーごとにログを振り分ける
                separateLogsForMembers[userName].append([beforeSt, afterSt, timeStamp])

                # voiceStateLog に最終的に反映される7日以上前のログを排除した新しいログ
                futureVoiceStateLog.append([userName, beforeSt, afterSt, timeStamp])
        
        # ユーザー毎のアクティビティを求め、fixedRank を作成する
        for userName, logs in separateLogsForMembers.items():
            
            _in, _active = 0, False
            
            # もしアクティビティのないメンバーならこの処理を飛ばす
            if len(logs) == 0 :
                fixedRank[userName]['nowRank'] = 'なし'
                continue
            
            for beforeSt, afterSt, timeStamp in logs:

                if _active and (afterSt in enableChannels):
                    _active = True

                elif _active and (beforeSt in enableChannels):
                    fixedRank[userName]['activity'][(nowUnixTime - timeStamp) // day] += timeStamp - _in
                    _active = False

                else:
                    _in = timeStamp
                    _active = True
            
            # 称号の条件(時間) <= アクティブタイム を満たす最大の 称号を fixedRank['nowRank'] に設定する
            # もしアクティビティがないなら 称号は無し
            
            activeTime = sum(fixedRank[userName]['activity'])
            
            for rank, value in sortedRankRoles:
                if activeTime//7 < value: break
                fixedRank[userName]['nowRank'] = rank
            
            # 昇格/維持/降格 を反映

            old = rankRoles[fixedRank[userName]['oldRank']]
            now = rankRoles[fixedRank[userName]['nowRank']]

            if old < now: fixedRank[userName]['status'] = '昇格'
            elif old > now: fixedRank[userName]['status'] = '降格'
            else: fixedRank[userName]['status'] = '維持'

        return fixedRank
    
    # Rank更新通知 Embed
    def _createGuildMessage(self, fixedRank):
        userName, info = '\n'*2
        for key, value in fixedRank.items():
            userName += '%s\n' % key
            info += '%sh　 %s　　%s\n' % (str(sum(value['activity'])//3600).zfill(3), value['status'], value['nowRank'])
        
        now = datetime.now(timezone(timedelta(hours=+9), 'JST'))
        start = now - timedelta(weeks=1)
        start = '%s月%s日' % (start.month, start.day)
        end = '%s月%s日' % (now.month, now.day)
        description = '```%s のランク更新情報です。``````\n%s ~ %s までの自習室利用時間を集計して算出しています。```' % (end, start, end)
        emb = discord.Embed(title=':confetti_ball: ランク更新 :confetti_ball:', description=description)
        emb.add_field(name='ユーザー', value='```%s```' % userName, inline=True)
        emb.add_field(name='　時間　　変動　　称号', value='```%s```' % info, inline=True)

        return emb
    
    # ランク反映処理
    async def _fixRank(self):
        # Log を記録しているGuild をすべて取得
        guilds = [self.bot.get_guild(int(guildID[:-4])) for guildID in os.listdir('%s/log/voiceStateLog/'%(self.root)) if guildID != 'dummy.csv']
        
        # 全てのギルドを更新
        for guild in guilds:

            # 更新したランク情報を取得
            fixedRank = self._updateGuild(guild)

            # 全てのメンバーを更新
            for member in guild.members:
                # botは飛ばす
                if member.bot:
                    fixedRank.pop(member.name)
                    continue

                oldRank = fixedRank[member.name]['oldRank']
                nowRank = fixedRank[member.name]['nowRank']

                # ランクが変わっていないメンバーは飛ばす
                if oldRank == nowRank: continue

                # メンバーのロールを更新
                for role in guild.roles:
                    if role.name == oldRank: await member.remove_roles(role)
                    if role.name == nowRank: await member.add_roles(role)
        
            # ランク反映通知を送る
            channels = guild.channels
            for channel in channels:
                if channel.name == self.config['announce']['channel']:
                    await channel.send(embed=self._createGuildMessage(fixedRank))
 
    @tasks.loop(seconds=10)
    async def autoUpdate(self):
        # 1日1回更新
        if 70 < int(time.time()) - self.lastUpdate:
            if datetime.now(self.JST).strftime('%H:%M') == self.config['rankUpdate']['updateTime']:
                await self._fixRank()
                self.lastUpdate = int(time.time())

    @commands.command()
    async def rank(self, ctx):
        if not ctx.author.name in self.config['admin']: return None
        await self._fixRank()

def setup(bot):
    bot.add_cog(Rank(bot))
    print('[cog] Rank was loaded!')
