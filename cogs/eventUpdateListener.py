import datetime
import json
import settings

import discord
from discord.ext import commands

class EventForm(discord.ui.Modal):
    about = discord.ui.TextInput(label="内容", placeholder="~というゲームをみんなでしませんか?...", style=discord.TextStyle.long)

    def __init__(self, bot, timeout=86400, origInteraction=None): # timeout - 24h
        super().__init__(title="イベントへの提案", timeout=timeout)
        self.bot = bot
        self.origInteraction = origInteraction

    async def on_submit(self, interaction: discord.Interaction):
        oldEmbed = self.origInteraction.message.embeds[1]
        if oldEmbed.description is None:
            oldEmbed.description = ""
        oldEmbed.description += f"From {interaction.user.mention} **{self.about}**\n"
        await self.origInteraction.message.edit(embeds=[self.origInteraction.message.embeds[0], oldEmbed])
        # 「インタラクションに失敗しました」対策
        await interaction.response.send_message("")

class EventView(discord.ui.View):
    joiningUser = 0

    def __init__(self, bot, timeout=86400): # timeout - 24h
        super().__init__(timeout=timeout)
        self.bot = bot

    async def disable_all_items(self):
        for item in self.children:
            item.disable = True
        await self.message.edit(view=self)

    async def on_timeout(self):
        await self.disable_all_items()

    @discord.ui.button(label="参加する",
                       style=discord.ButtonStyle.success)
    async def join(self, interaction: discord.Interaction, button: discord.ui.Button):
        try:
            with open("data/joiningUser.json") as f:
                    jd = json.load(f)
            if str(interaction.message.id) in jd:
                if interaction.user.id not in jd[str(interaction.message.id)]["joining"]:
                    self.joiningUser += 1
                    jd[str(interaction.message.id)]["joining"].append(interaction.user.id)
                    with open("data/joiningUser.json", "w") as f:
                        json.dump(jd, f, indent=2)
                    oldEmbed = interaction.message.embeds[0]
                    oldEmbed.description = ""
                    for i, user_id in enumerate(jd[str(interaction.message.id)]["joining"]):
                        user = self.bot.get_user(user_id)
                        if user is not None:
                            oldEmbed.description += f"{i+1}: {user.mention}\n"
                    await interaction.message.edit(embeds=[oldEmbed, interaction.message.embeds[1]])
            # 「インタラクションに失敗しました」対策
            await interaction.response.send_message("")
        except Exception as e:
            print(e)

    @discord.ui.button(label="参加する(遅れます)",
                       style=discord.ButtonStyle.primary)
    async def join_not_on_time(self, interaction: discord.Interaction, button: discord.ui.Button):
        try:
            with open("data/joiningUser.json") as f:
                    jd = json.load(f)
            if str(interaction.message.id) in jd:
                if interaction.user.id not in jd[str(interaction.message.id)]["joining"]:
                    self.joiningUser += 1
                    jd[str(interaction.message.id)]["joining"].append(interaction.user.id)
                    with open("data/joiningUser.json", "w") as f:
                        json.dump(jd, f, indent=2)
                    oldEmbed = interaction.message.embeds[0]
                    oldEmbed.description = ""
                    for i, user_id in enumerate(jd[str(interaction.message.id)]["joining"]):
                        user = self.bot.get_user(user_id)
                        if user is not None:
                            if user == interaction.user:
                                oldEmbed.description += f"{i+1}: {user.mention} (遅れます)\n"
                            else:
                                oldEmbed.description += f"{i+1}: {user.mention}\n"
                    await interaction.message.edit(embeds=[oldEmbed, interaction.message.embeds[1]])
            # 「インタラクションに失敗しました」対策
            await interaction.response.send_message("")
        except Exception as e:
            print(e)

    @discord.ui.button(label="辞退する",
                       style=discord.ButtonStyle.red)
    async def decline(self, interaction: discord.Interaction, button: discord.ui.Button):
        try:
            with open("data/joiningUser.json") as f:
                    jd = json.load(f)
            if str(interaction.message.id) in jd:
                if interaction.user.id in jd[str(interaction.message.id)]["joining"]:
                    self.joiningUser -= 1
                    jd[str(interaction.message.id)]["joining"].remove(interaction.user.id)
                    with open("data/joiningUser.json", "w") as f:
                        json.dump(jd, f, indent=2)
                    oldEmbed = interaction.message.embeds[0]
                    oldEmbed.description = ""
                    for i, user_id in enumerate(jd[str(interaction.message.id)]["joining"]):
                        user = self.bot.get_user(user_id)
                        if user is not None:
                            oldEmbed.description += f"{i+1}: {user.mention}\n"
                    await interaction.message.edit(embeds=[oldEmbed, interaction.message.embeds[1]])
            # 「インタラクションに失敗しました」対策
            await interaction.response.send_message("")
        except Exception as e:
            print(e)

    @discord.ui.button(label="イベントへの提案",
                       style=discord.ButtonStyle.gray)
    async def about_event(self, interaction: discord.Interaction, button: discord.ui.Button):
        try:
            await interaction.response.send_modal(EventForm(self.bot, timeout=86400, origInteraction=interaction))
        except Exception as e:
            print(e)

class Event(commands.Cog):
    def __init__(self, bot):
        self.bot = bot

    @commands.Cog.listener()
    async def on_scheduled_event_create(self, e):
        try:
            # create & send embed
            notifyEmbed = discord.Embed(
                description="",
                color=discord.Colour.green()
            )
            notifyEmbed.set_author(name="参加希望者リスト")
            eventEmbed = discord.Embed(
                description="",
                color=discord.Colour.blue()
            )
            eventEmbed.set_author(name="イベントへの提案")
            notifyView = EventView(self.bot, timeout=86400) # timeout - 24h
            notifyChan = self.bot.get_partial_messageable(settings.NOTIFY_CHAN)
            embed = await notifyChan.send(e.url, embeds=[notifyEmbed, eventEmbed], view=notifyView)

            # register event by message id
            with open("data/joiningUser.json") as f:
                jd = json.load(f)
            jd[embed.id] = {"joining": []}
            with open("data/joiningUser.json", "w") as f:
                json.dump(jd, f, indent=2)
        except Exception as e:
            print(e)


    @commands.group()
    async def event(self, ctx):
        if ctx.invoked_subcommand is None:
            try:
                # create & send embed
                notifyEmbed = discord.Embed(
                    description="",
                    color=discord.Colour.green()
                )
                notifyEmbed.set_author(name="参加希望者リスト")
                eventEmbed = discord.Embed(
                    description="",
                    color=discord.Colour.blue()
                )
                eventEmbed.set_author(name="イベントへの提案")
                notifyView = EventView(self.bot, timeout=86400) # timeout - 24h
                notifyChan = self.bot.get_partial_messageable(settings.NOTIFY_CHAN)
                embed = await notifyChan.send("Test", embeds=[notifyEmbed, eventEmbed], view=notifyView)

                # register event by message id
                with open("data/joiningUser.json") as f:
                    jd = json.load(f)
                jd[embed.id] = {"joining": []}
                with open("data/joiningUser.json", "w") as f:
                    json.dump(jd, f, indent=2)
            except Exception as e:
                print(e)

async def setup(bot):
    await bot.add_cog(Event(bot))