import csv
import discord
import io
import json
import os
import requests
import sys
import time

from asyncio import tasks
from collections import deque
from PIL import Image, ImageFilter, ImageDraw, ImageFont
sys.path.append(os.path.dirname(os.path.dirname(os.path.abspath(__file__))))

from datetime import datetime
from datetime import timedelta
from datetime import timezone
from discord.ext import tasks
from discord.ext import commands

class Rank(commands.Cog):
    def __init__(self, bot):
        self.bot = bot
        self.root = os.path.dirname(__file__)[:-4]
        self.JST = timezone(timedelta(hours=+9), 'JST')
        self.lastUpdate = 0
        self.imagePath = '%s/img' % self.root
        with open('%s/bot.conf' % self.root, 'r', encoding='utf-8')as f:
            self.config = json.loads(f.read())
        self.autoUpdate.start()
    
    # 暦上の何日前か求める
    def _howManyDaysAgo(self, fromTime, today):
        day = 86400
        ret = (today + day - fromTime) //day
        return ret

    # 日を跨ぐアクティビティを正常に出力する
    def _straddle(self, before, now):
        day = 86400
        today = now // day * day
        if (before % day) <= (now % day):return (now - before, 0)
        else: return (today-before, now-today)

    # guildごとのランク更新処理
    def _updateGuild(self, guild):
        guildID = guild.id
        members = guild.members
        rankRoles = self.config['rank']['roles']
        rankRoles[''] = -1
        sortedRankRoles = sorted([[key,value] for key, value in self.config['rank']['roles'].items()], key=lambda x: x[1])
        enableChannels = set(self.config['rank']['enableChannel']['voice'])
        voiceStateLogPath = '%s/log/voiceStateLog/%s.csv' % (self.root, guildID)
        futureVoiceStateLog = []
        nowUnixTime = int(time.time())
        separateLogsForMembers = {member.id : deque([]) for member in members}
        fixedRank = dict()
        day = 86400
        today = nowUnixTime // day * day

        # fixedRank のフォーマット
        for member in members:
            userId = member.id
            rank = [role.name for role in member.roles if role.name in rankRoles]
            rank = '' if rank == [] else rank[0]
            fixedRank[userId] = {'name':member.name, 'activity':[0]*8, 'oldRank':rank, 'nowRank':'', 'status':'幽霊'}
            logData = []

        with open(voiceStateLogPath, 'r', encoding='utf-8') as voiceStateLog:

            for voiceStateLogOneLine in csv.reader(voiceStateLog):

                # もし空行を読み取ったなら処理を飛ばす。
                # 空でなければリストに追加する。
                if len(voiceStateLogOneLine)==4: logData.append(voiceStateLogOneLine)
                else:continue

        for userId, beforeSt, afterSt, timeStamp in logData:

            userId = int(userId)
            timeStamp = int(timeStamp)

            # 7日以上前のログは参照しない
            if timeStamp < today - (day*7): continue

            # ランク対象外のボイスチャンネルの入退室はカウントしない
            if (not beforeSt in enableChannels) and (not afterSt in enableChannels): continue

            # ユーザーごとにログを振り分ける
            separateLogsForMembers[userId].appendleft([beforeSt, afterSt, timeStamp])

            # voiceStateLog に最終的に反映される7日以上前のログを排除した新しいログ
            futureVoiceStateLog.append([userId, beforeSt, afterSt, timeStamp])

        # ユーザー毎のアクティビティを求め、fixedRank を作成する
        for userId, logs in separateLogsForMembers.items():

            _out, _count, _active = 0, 0, False

            # もしアクティビティのないメンバーならこの処理を飛ばす
            if len(logs) == 0:
                fixedRank[userId]['nowRank'] = 'なし'
                continue

            for beforeSt, afterSt, timeStamp in logs:
                
                _count += 1

                # 入室
                if (afterSt in enableChannels) and (not beforeSt in enableChannels):
                    # 通常
                    if _active:
                        _active = False
                        index = self._howManyDaysAgo(timeStamp, today)
                        straddle = self._straddle(timeStamp, _out)
                        fixedRank[userId]['activity'][index] += straddle[1]
                        fixedRank[userId]['activity'][index+1] += straddle[0]
                    # ボイチャ接続中に更新がかかった場合
                    else:
                        index = self._howManyDaysAgo(timeStamp, today)
                        straddle = self._straddle(timeStamp, nowUnixTime)
                        print(userId, straddle)
                        fixedRank[userId]['activity'][index] += straddle[1]
                        fixedRank[userId]['activity'][index+1] += straddle[0]

                # 退室
                elif (beforeSt in enableChannels) and (not afterSt in enableChannels):
                    # ランク範囲外を跨ぐアクティビティの退室処理(最古のログが退室の場合)
                    if _count==len(logs):
                        # fixedRank[userId]['activity'][self._howManyDaysAgo(timeStamp, today)] += timeStamp - (today - (day*7))
                        index = self._howManyDaysAgo(timeStamp, today)
                        straddle = self._straddle(today - (day*7), timeStamp)
                        fixedRank[userId]['activity'][index] += straddle[1]
                        fixedRank[userId]['activity'][index+1] += straddle[0]
                    # 通常
                    else:
                        _out = timeStamp
                        _active = True


            # 称号の条件(時間) <= アクティブタイム を満たす最大の 称号を fixedRank['nowRank'] に設定する
            # もしアクティビティがないなら 称号は無し

            activeTime = sum(fixedRank[userId]['activity'])

            for rank, value in sortedRankRoles:
                if activeTime//7 <= value: break
                fixedRank[userId]['nowRank'] = rank

            # 昇格/維持/降格 を反映

            old = rankRoles[fixedRank[userId]['oldRank']]
            now = rankRoles[fixedRank[userId]['nowRank']]

            if old < now: fixedRank[userId]['status'] = '昇格'
            elif old > now: fixedRank[userId]['status'] = '降格'
            else: fixedRank[userId]['status'] = '維持'

        with open(voiceStateLogPath, 'w', encoding='utf-8') as f:
            writer = csv.writer(f)
            for log in futureVoiceStateLog:
                writer.writerow(log)

        return fixedRank

    # Rank更新通知 Embed
    def _createGuildMessage(self, fixedRank):
        userName, info = '\n'*2
        for key, value in fixedRank.items():
            userName += '%s\n' % value['name']
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
            fixedRank = self._updateGuild(guild) # 更新したランク情報を取得
            # 全てのメンバーを更新
            for member in guild.members:
                # botは飛ばす
                if member.bot:
                    fixedRank.pop(member.id)
                    continue

                oldRank = fixedRank[member.id]['oldRank']
                nowRank = fixedRank[member.id]['nowRank']

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

    @tasks.loop(seconds=1)
    async def autoUpdate(self):
        # 1日1回更新
        if 1000 < int(time.time()) - self.lastUpdate:
            if datetime.now(self.JST).strftime('%H:%M') == self.config['rank']['updateTime']:
                self.lastUpdate = int(time.time())
                await self._fixRank()

    # VoiceStatus を監視するevent
    @commands.Cog.listener()
    async def on_voice_state_update(self, member, before, after):
        user = member.id
        beforeState = before.channel
        afterState = after.channel
        guildID = str(member.guild.id)

        # 関係ないステータス更新は記録しない
        if beforeState == afterState: return

        with open('%s/log/voiceStateLog/%s.csv'%(self.root, guildID), 'a', encoding='utf-8') as f:
            writer = csv.writer(f)
            # log/voiceStateLog.csv のフォーマットは [ユーザーID, 遷移前のボイチャ名, 遷移後のボイチャ名, 遷移した時間]
            writer.writerow([user, str(beforeState), str(afterState), str(int(time.time()))])

    # ユーザー毎の詳細な戦績を表示するコマンド
    # mee6 の !rank みたいな画像を出す
    @commands.command()
    async def rank(self, ctx, user=None):
        userid = 0
        if user == None:
            userid = ctx.author.id
        else:
            for member in ctx.guild.members:
                if member.name == user:
                    userid = member.id

        user = ctx.author.name if user == None else user

        avatarURL = ctx.message.author.avatar_url
        
        if not user in [member.name for member in ctx.guild.members]: return
        
        # アバター取得
        for member in ctx.guild.members:
            if member.name == user:
                avatarURL = member.avatar_url

        baseImagePath = '%s/rank_base.png' % self.imagePath
        avatarMaskPath = '%s/avatar_mask.png' % self.imagePath
        savePath = '%s/%s.png' % (self.imagePath, ctx.author.id)
        fixedRank = self._updateGuild(ctx.guild)[userid]
        defaultColor = (185, 187, 190)
        rankColor = defaultColor

        # ランクの色を取得
        for role in ctx.guild.roles:
            if role.name == fixedRank['nowRank']:
                color = role.color
                rankColor = (color.r, color.g, color.b)

        image = Image.open(baseImagePath)
        avatar = Image.open(io.BytesIO(requests.get(avatarURL).content)).convert('RGBA')
        
        # ユーザーアイコンの整形
        avatarBase = Image.new('RGBA', (64, 64), (54, 57, 63, 255))
        draw = ImageDraw.Draw(avatarBase)
        draw.ellipse((0, 0, 64, 64), fill=(47, 49, 54))
        avatarMask = Image.open(avatarMaskPath).convert('1')
        avatar = avatar.resize((64, 64), Image.HAMMING)
        avatar = Image.composite(avatar, avatarBase, avatarMask)
        avatar = Image.alpha_composite(avatarBase, avatar)

        # テキスト定義
        #nfontPath = '%s/font/MEIRYO.TTC' % self.root
        bfontPath = '%s/font/MEIRYOB.TTC' % self.root

        # 合成
        draw = ImageDraw.Draw(image)
        memberNameFont = ImageFont.truetype(bfontPath, 24)
        nomalFont = ImageFont.truetype(bfontPath, 14)

        image.paste(avatar, (21, 17))
        draw.text((100, 18), user, (255, 255, 255, 255), font=memberNameFont)
        draw.text((100, 48), fixedRank['nowRank'], rankColor, font=nomalFont)
        draw.text((20, 104), '過去7日間の自習時間: %s h' % (sum(fixedRank['activity'])//3600), defaultColor, font=nomalFont)
        draw.rectangle((102, 72, 250*(sum(fixedRank['activity'])/(3600*14)%1) + 102, 77), fill=rankColor)

        now=datetime.now(timezone(timedelta(hours=+9), 'JST'))
        for i in range(7):
            d = now - timedelta(days=i)
            draw.text((355+(-i * 52), 245), '%s/%s' % (d.month, d.day), defaultColor, font=nomalFont, anchor='ma')
            draw.text((355+(-i * 52), 230 - (fixedRank['activity'][i+1]*3//3600)), '%sh' % (fixedRank['activity'][i+1]//3600), defaultColor, font=nomalFont, anchor='mb')
            draw.rectangle((340+(-i * 52), 240 - fixedRank['activity'][i+1]*3//3600, 370+(-i * 52), 240), fill=defaultColor)

        image.save(savePath)
        print(userid, fixedRank['activity'])
        await ctx.send(file=discord.File(savePath))

def setup(bot):
    bot.add_cog(Rank(bot))
    print('[cog] Rank was loaded!')