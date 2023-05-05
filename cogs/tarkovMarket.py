import datetime
import settings

import discord
from discord.ext import commands
import requests

def getPriceFromKeyword(keyword):
    query = f"""
query {{
    items(name: "{keyword}") {{
        id
        name
        shortName
        avg24hPrice
        changeLast48h
        image8xLink
        updated
    }}
}}
"""
    try:
        resp = requests.post("https://api.tarkov.dev/graphql", headers={"Content-Type": "application/json"}, json={'query': query})
    except Exception:
        return None
    if resp.status_code != 200:
        return None
    return resp.json()

class Tarkov(commands.Cog):
    def __init__(self, bot):
        self.bot = bot

    @commands.group()
    async def tarkov(self, ctx):
        if ctx.invoked_subcommand is None:
            await ctx.reply(f"{ctx.author.mention}サブコマンドが必要です。")

    @tarkov.command()
    async def price(self, ctx, *keywords):
        if type(ctx.channel) is not discord.channel.DMChannel:
            await ctx.reply(f"{ctx.author.mention}このコマンドはDMで実行してください。")
            return
        keyword = " ".join(keywords)
        if keyword == "":
            await ctx.author.send(f"{ctx.author.mention}価格を調べるアイテムのキーワードが必要です。")
        resp = getPriceFromKeyword(keyword)
        if resp is None:
            await ctx.author.send(f"{ctx.author.mention}エラーが発生しました。少し時間を置いてお試しください。")
        if resp["data"]["items"] == []:
            await ctx.author.send(f"{ctx.author.mention}アイテムが見つかりませんでした。")
        topItem = resp["data"]["items"][0]
        embed = discord.Embed(title=topItem["name"], color=discord.Colour.random())
        embed.set_thumbnail(url=topItem["image8xLink"])
        embed.set_footer(text="Powered by tarkov.dev")
        embed.timestamp = datetime.datetime.now()
        embed.add_field(name="Avg 24h", value=f"{topItem['avg24hPrice']} Roubles")
        embed.add_field(name="Change last 48h", value=f"{topItem['changeLast48h']} Roubles")
        await ctx.author.send(embed=embed)

async def setup(bot):
    await bot.add_cog(Tarkov(bot))