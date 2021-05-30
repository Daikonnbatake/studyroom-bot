import csv
import json
import os
import time

class RankSys:

    # 自習室ランクの情報をアップデート
    @staticmethod
    def updateRank(guild):
        root = os.path.dirname(__file__)[:-7]
        with open(root + '/bot.conf', 'r', encoding='utf-8')as f:
            config = json.loads(f.read())

        guildID = str(guild.id)
        logPath = root + '/log/voiceStateLog/' + guildID + '.csv'
        aggregate = dict()
        activity = dict()
        day = 86400
        nowTime = int(time.time())
        today = nowTime//day
        afterLog = []

        with open(logPath, 'r', encoding='utf-8') as f:
            
            # リクエスト元サーバーのvoiceStateLog を読み込み、
            # ユーザー毎にアクティブタイムの累積和を取る

            userlr = dict()
            enable = config['rank_enable']['voice']
            for data in csv.reader(f):
                
                if len(data) == 4: userName, beforeSt, afterSt, timeStamp = data
                else: continue

                # 7日以上前のログは参照しない
                loggedDay = int(timeStamp)//day
                if 6 < today - loggedDay: continue

                # ユーザーごとにアクティビティを分離
                if (beforeSt in enable) or (afterSt in enable):
                    if userName in aggregate: aggregate[userName].append([beforeSt, afterSt, timeStamp])
                    else:
                        aggregate[userName] = [[beforeSt, afterSt, timeStamp]]
                        activity[userName] = {'activity':[0]*7, 'old':'', 'now':''}
                afterLog.append([userName, beforeSt, afterSt, timeStamp])

            # ユーザーごとのアクティビティの時間を求める
            for userName, value in aggregate.items():
                
                l, r,activ = 0, 0, False

                for beforeSt, afterSt, timeStamp in value:

                    timeStamp = int(timeStamp)
                    logindex = today - (timeStamp//day)

                    if activ and (afterSt in enable):
                        r = timeStamp
                        activ = True

                    elif activ and (beforeSt in enable):
                        r = timeStamp
                        activity[userName]['activity'][logindex] += r-l
                        activ = False
                    
                    else:
                        l = timeStamp
                        r = timeStamp
                        activ = True
            
            with open(root + '/log/fixedRank/' + str(guildID) + '.json', 'w', encoding='utf-8') as js:
                text = json.dumps(activity, indent=2, ensure_ascii=False)
                js.write(text)
        
        # voiceStateLog を更新
        with open(logPath, 'w', encoding='utf-8') as f:
            writer = csv.writer(f, lineterminator='\n')
            writer.writerows(afterLog)