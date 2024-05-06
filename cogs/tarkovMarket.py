import datetime

import discord
from discord.ext import commands
import requests

from utils.template import getSubcommandsEmbed

class TarkovPriceView(discord.ui.View):
    def __init__(self, bot, result, timeout=300): # timeout - 5m
        super().__init__(timeout=timeout)
        self.bot = bot
        self.result = result
        self.resultIndex = 0
        self.resultMax = len(result)

    async def disable_all_items(self):
        for item in self.children:
            item.disable = True
        await self.message.edit(view=self)

    async def on_timeout(self):
        await self.disable_all_items()

    @discord.ui.button(label="←",
                       style=discord.ButtonStyle.blurple)
    async def prevSugesstion(self, interaction: discord.Interaction, button: discord.ui.Button):
        if self.resultIndex == 0:
            self.resultIndex = self.resultMax-1
        else:
            self.resultIndex -= 1
        currentItem = self.result[self.resultIndex]
        oldEmbed = interaction.message.embeds[0]
        oldEmbed.description = f"[{self.resultIndex+1}/{self.resultMax}] {currentItem['name']}"
        oldEmbed.set_thumbnail(url=currentItem["image8xLink"])
        oldEmbed.set_field_at(0, name="Avg 24h", value=f"**{'{:,}'.format(currentItem['avg24hPrice'])}** Roubles")
        if currentItem['changeLast48h'] < 0:
            oldEmbed.set_field_at(1, name="Change last 48h", value=f"**{'{:,}'.format(currentItem['changeLast48h'])}** Roubles :arrow_heading_down:")
        else:
            oldEmbed.set_field_at(1, name="Change last 48h", value=f"**{'{:,}'.format(currentItem['changeLast48h'])}** Roubles :arrow_heading_up:")
        await interaction.message.edit(embeds=[oldEmbed])
        await interaction.response.send_message("") # 「インタラクションに失敗しました」対策

    @discord.ui.button(label="→",
                       style=discord.ButtonStyle.success)
    async def nextSuggestion(self, interaction: discord.Interaction, button: discord.ui.Button):
        if self.resultIndex == self.resultMax-1:
            self.resultIndex = 0
        else:
            self.resultIndex += 1
        try:
            currentItem = self.result[self.resultIndex]
            oldEmbed = interaction.message.embeds[0]
            oldEmbed.description = f"[{self.resultIndex+1}/{self.resultMax}] {currentItem['name']}"
            oldEmbed.set_thumbnail(url=currentItem["image8xLink"])
            oldEmbed.set_field_at(0, name="Avg 24h", value=f"**{'{:,}'.format(currentItem['avg24hPrice'])}** Roubles")
            if currentItem['changeLast48h'] < 0:
                oldEmbed.set_field_at(1, name="Change last 48h", value=f"**{'{:,}'.format(currentItem['changeLast48h'])}** Roubles :arrow_heading_down:")
            else:
                oldEmbed.set_field_at(1, name="Change last 48h", value=f"**{'{:,}'.format(currentItem['changeLast48h'])}** Roubles :arrow_heading_up:")
            await interaction.message.edit(embeds=[oldEmbed])
            await interaction.response.send_message("") # 「インタラクションに失敗しました」対策
        except Exception as e:
            print(e)


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
        types
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

    @commands.group(
        description="Commands related to Escape from Tarkov",
    )
    async def tarkov(self, ctx):
        if ctx.invoked_subcommand is None:
            await ctx.reply(f"{ctx.author.mention}Subcommand is required.", embed=getSubcommandsEmbed(ctx.command))

    @tarkov.command(
        description="Search the price of the item",
    )
    async def price(self, ctx, *keywords):
        # if type(ctx.channel) is not discord.channel.DMChannel:
        #     await ctx.reply(f"{ctx.author.mention}This command should be executed by DM.")
        #     return
        keyword = " ".join(keywords)
        if keyword == "":
            await ctx.author.send(f"{ctx.author.mention}Need keywords for items to check prices.")
            return
        resp = getPriceFromKeyword(keyword)
        if resp is None:
            await ctx.author.send(f"{ctx.author.mention}An error has occurred. Please try again in a few minutes.")
            return
        searchItems = resp["data"]["items"]
        if len(searchItems) == 0:
            await ctx.author.send(f"{ctx.author.mention}Item not found.")
            return
        
        priceView = TarkovPriceView(self.bot, searchItems)
        embed = discord.Embed(title=f"Search Result ({len(searchItems)} search results)",
                            description=f"[1/{len(searchItems)}] {searchItems[0]['name']}",
                            color=discord.Colour.random())
        embed.set_footer(text="Powered by tarkov.dev")
        embed.timestamp = datetime.datetime.now()
        embed.set_thumbnail(url=searchItems[0]["image8xLink"])
        embed.add_field(name="Avg 24h", value=f"**{'{:,}'.format(searchItems[0]['avg24hPrice'])}** Roubles")
        if searchItems[0]['changeLast48h'] < 0:
            embed.add_field(name="Change last 48h", value=f"**{'{:,}'.format(searchItems[0]['changeLast48h'])}** Roubles :arrow_heading_down:")
        else:
            embed.add_field(name="Change last 48h", value=f"**{'{:,}'.format(searchItems[0]['changeLast48h'])}** Roubles :arrow_heading_up:")
        await ctx.author.send(embeds=[embed], view=priceView)

async def setup(bot):
    await bot.add_cog(Tarkov(bot))
