import discord
import os

ROOT = os.path.dirname(__file__)

# TOKEN 読み込み
with open(ROOT + '/meta/token.txt') as f:
    TOKEN = f.read()

print(ROOT)
print(TOKEN)