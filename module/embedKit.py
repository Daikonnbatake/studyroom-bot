import discord
import json
import os

from datetime import datetime, timedelta, timezone

class EmbedKit:

    # ランク更新通知
    @staticmethod
    def rankUpdate(guildID):
        root = os.path.dirname(__file__)[:-7]
        guildID = str(guildID)
        jst = timezone(timedelta(hours=+9), 'JST')
        if not guildID+'.json' in os.listdir(root + '/log/fixedRank/'): return None
            
        with open(root + '/log/fixedRank/' + guildID + '.json', 'r', encoding='utf-8') as jsonfile:
            fixedRank = json.loads(jsonfile.read())

        with open(root + '/bot.conf', 'r', encoding='utf-8') as jsonfile:
            config = json.loads(jsonfile.read())

        now = datetime.now(jst)
        start = now - timedelta(weeks=1)
        now = str(now.month) + '月' + str(now.day) + '日'
        start =str(start.month) + '月' + str(start.day) + '日'
        
        description = '```' + now + ' のランク更新情報です。 ```' + '```' + start + ' ~ ' + now + ' (UST)までの自習室利用時間を集計して算出しています。```'
        emb = discord.Embed(title='ランク更新', description=description)
        
        # ユーザー名 000h 昇格 ランク
        userData = []

        for data in fixedRank.items():
            
            if len(data) == 2: userName, value = data
            else: continue

            oldRrank = fixedRank[userName]['old']
            nowRrank = fixedRank[userName]['now']
            time = str(sum(value['activity'])//3600).zfill(3) + 'h'

            if oldRrank == '' or nowRrank == '': change = '新規'
            elif config['roles'][oldRrank] < config['roles'][nowRrank]: change = '昇格'
            elif config['roles'][oldRrank] > config['roles'][nowRrank]: change = '降格'
            else: change = '維持'
            userName = userName if len(userName) <= 10 else userName[:11]
            
            userData.append([userName, time, change, nowRrank])
        user = '\n'.join([n for n,t,c,r in userData])
        grades = '\n'.join([' ' + t + '　' + '　' + c + '　' + r for n,t,c,r in userData])
        emb.add_field(name='ユーザー名', value='```\n'+user+'```', inline=True)
        emb.add_field(name='戦績', value= '```'+grades+'```', inline=True)
        emb.set_thumbnail(url='https://2.bp.blogspot.com/-GuJM5cIi3K8/VHbNOnnoEzI/AAAAAAAApU8/VAa2CK1C360/s400/hyousyou_sports_man.png')

        return emb