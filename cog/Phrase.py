import json
import os

from discord.ext import commands

class Phrase(commands.Cog):

    def __init__(self, bot):
        self.bot = bot
        self.root = os.path.dirname(__file__)[:-4]
        with open(self.root + '/bot.conf', 'r', encoding='utf-8')as f:
            self.config = json.loads(f.read())
    
    @commands.Cog.listener()
    # 単語に反応するおまけ要素
    async def on_message(self, message):
        phrase = self.config['phrase']
        if message.content in phrase:
            await message.channel.send(phrase[message.content])

def setup(bot):
    bot.add_cog(Phrase(bot))
    print('[cog] Phrase was loaded!')
