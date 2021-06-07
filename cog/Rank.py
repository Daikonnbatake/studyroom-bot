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

from datetime import datetime, timedelta, timezone
from discord.ext import tasks,commands

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

    # guildごとのランク更新処理
    def _updateGuild(self, guild):
        guildID = guild.id
        members = guild.members
        rankRoles = self.config['rank']['roles']
        rankRoles[''] = -1
        sortedRankRoles = sorted([[key,value] for key, value in self.config['rank']['roles'].items()], key=lambda x: x[1])
        enableChannels = set(self.config['rank']['enableChannel']['voice'])
        voiceStateLogPath = '%s/log/voiceStateLog/%s.csv' % (self.root, guildID)
        futureVoiceStateLog = deque([])
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
            logData = deque([])

        with open(voiceStateLogPath, 'r', encoding='utf-8') as voiceStateLog:
            
            for voiceStateLogOneLine in csv.reader(voiceStateLog):

                # もし空行を読み取ったなら処理を飛ばす。
                # 空でなければリストに追加する。
                if len(voiceStateLogOneLine)==4: logData.appendleft(voiceStateLogOneLine)
                else:continue
        
        for userName, beforeSt, afterSt, timeStamp in logData:

            timeStamp = int(timeStamp)

            # 7日以上前のログは参照しない
            if 6 < (nowUnixTime - timeStamp) // day: continue

            # ランク対象外のボイスチャンネルの入退室はカウントしない
            if (not beforeSt in enableChannels) and (not afterSt in enableChannels): continue
            
            # ユーザーごとにログを振り分ける
            separateLogsForMembers[userName].append([beforeSt, afterSt, timeStamp])

            # voiceStateLog に最終的に反映される7日以上前のログを排除した新しいログ
            futureVoiceStateLog.appendleft([userName, beforeSt, afterSt, timeStamp])
        
        # ユーザー毎のアクティビティを求め、fixedRank を作成する
        for userName, logs in separateLogsForMembers.items():
            
            _in, _out, _active = 0, 0, False
            
            # もしアクティビティのないメンバーならこの処理を飛ばす
            if len(logs) == 0 :
                fixedRank[userName]['nowRank'] = 'なし'
                continue
            
            for beforeSt, afterSt, timeStamp in logs:

                # 通常の入室ログが来た場合
                if _active and (afterSt in enableChannels) and (not beforeSt in enableChannels):
                    fixedRank[userName]['activity'][(nowUnixTime - timeStamp) // day] += _out - timeStamp
                    _active = False

                # 通常の退室ログが来た場合
                elif (not _active) and (beforeSt in enableChannels) and (not afterSt in enableChannels):
                    _out = timeStamp
                    _active = True
                
                # ランク更新が入室中に掛かった場合
                elif (not _active) and (afterSt in enableChannels) and (not beforeSt in enableChannels):
                    fixedRank[userName]['activity'][0] += nowUnixTime - timeStamp + _in
                    _in = timeStamp

            # ランク有効期間外からのアクティビティがあった場合
            if _active and (beforeSt in enableChannels) and (not afterSt in enableChannels):
                fixedRank[userName]['activity'][-1] += timeStamp - (nowUnixTime - (day * 7))

            
            # 称号の条件(時間) <= アクティブタイム を満たす最大の 称号を fixedRank['nowRank'] に設定する
            # もしアクティビティがないなら 称号は無し
            
            activeTime = sum(fixedRank[userName]['activity'])
            
            for rank, value in sortedRankRoles:
                if activeTime//7 <= value: break
                fixedRank[userName]['nowRank'] = rank
            
            # 昇格/維持/降格 を反映

            old = rankRoles[fixedRank[userName]['oldRank']]
            now = rankRoles[fixedRank[userName]['nowRank']]

            if old < now: fixedRank[userName]['status'] = '昇格'
            elif old > now: fixedRank[userName]['status'] = '降格'
            else: fixedRank[userName]['status'] = '維持'
        
        with open(voiceStateLogPath, 'w', encoding='utf-8') as f:
            writer = csv.writer(f)
            for log in futureVoiceStateLog:
                writer.writerow(log)

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
            if datetime.now(self.JST).strftime('%H:%M') == self.config['rank']['updateTime']:
                await self._fixRank()
                self.lastUpdate = int(time.time())
    
    # VoiceStatus を監視するevent
    @commands.Cog.listener()
    async def on_voice_state_update(self, member, before, after):
        user = member.name
        beforeState = before.channel
        afterState = after.channel
        guildID = str(member.guild.id)

        # 関係ないステータス更新は記録しない
        if beforeState == afterState: return

        with open(self.root+'/log/voiceStateLog/'+ guildID +'.csv', 'a', encoding='utf-8') as f:
            writer = csv.writer(f)
            # log/voiceStateLog.csv のフォーマットは [ユーザー名, 遷移前のボイチャ名, 遷移後のボイチャ名, 遷移した時間]
            writer.writerow([user, str(beforeState), str(afterState), str(int(time.time()))])

    # ユーザー毎の詳細な戦績を表示するコマンド
    # mee6 の !rank みたいな画像を出す
    @commands.command()
    async def rank(self, ctx, user=None):
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
        fixedRank = self._updateGuild(ctx.guild)[user]
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
            draw.text((355+(-i * 52), 230 - (fixedRank['activity'][i]*3//3600)), '%sh' % (fixedRank['activity'][i]//3600), defaultColor, font=nomalFont, anchor='mb')
            draw.rectangle((340+(-i * 52), 240 - fixedRank['activity'][i]*3//3600, 370+(-i * 52), 240), fill=defaultColor)

        image.save(savePath)
        await ctx.send(file=discord.File(savePath))

def setup(bot):
    bot.add_cog(Rank(bot))
    print('[cog] Rank was loaded!')
