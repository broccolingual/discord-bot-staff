import datetime
import json
import settings

import discord
from discord.ext import commands

class EventView(discord.ui.View):
    joiningUser = 0

    def __init__(self, bot, timeout=None):
        super().__init__(timeout=timeout)
        self.bot = bot

    @discord.ui.button(label="Join this event",
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
                    await interaction.message.edit(embed=oldEmbed)
        except Exception as e:
            print(e)

    @discord.ui.button(label="Decline this event",
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
                    await interaction.message.edit(embed=oldEmbed)
        except Exception as e:
            print(e)

class Event(commands.Cog):
    def __init__(self, bot):
        self.bot = bot

    @commands.Cog.listener()
    async def on_scheduled_event_create(self, e):
        try:
            notifyEmbed = discord.Embed(
                title="参加者",
                description="",
                timestamp=e.start_time,
                color=discord.Colour.green()
            )
            notifyView = EventView(self.bot, timeout=None)
            notifyChan = self.bot.get_partial_messageable(settings.NOTIFY_CHAN)
            embed = await notifyChan.send(e.url, embed=notifyEmbed, view=notifyView)

            # register event
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
                await ctx.send("This command is not available.")
            except Exception as e:
                print(e)

async def setup(bot):
    await bot.add_cog(Event(bot))