import datetime
import settings

import discord
from discord.ext import commands

from db import *

class EventForm(discord.ui.Modal):
    about = discord.ui.TextInput(label="内容", placeholder="少し遅れます...", style=discord.TextStyle.long)

    def __init__(self, bot, timeout=86400, origInteraction=None): # timeout - 24h
        super().__init__(title="コメント", timeout=timeout)
        self.bot = bot
        self.origInteraction = origInteraction

    async def on_submit(self, interaction: discord.Interaction):
        oldEmbed = self.origInteraction.message.embeds[0]
        if oldEmbed.fields[1] is None:
            oldEmbed.set_field_at(1, "💬 Comments", "")
        oldValue = oldEmbed.fields[1].value
        oldValue += f"\nFrom {interaction.user.mention} : **{self.about}**"
        oldEmbed.set_field_at(1, name=oldEmbed.fields[1].name, value=oldValue)
        await self.origInteraction.message.edit(embeds=[oldEmbed])
        # 「インタラクションに失敗しました」対策
        await interaction.response.send_message("")

class EventView(discord.ui.View):
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
            # database
            eventId = getEventID(interaction.message.id)
            if eventId is not None:
                insertJoinedUser(eventId, interaction.user.id)
            joiningUserIDs = getJoinedUsers(eventId)
            oldEmbed = interaction.message.embeds[0] # get old embed
            newValue = ""
            for i, userId in enumerate(joiningUserIDs):
                user = self.bot.get_user(userId)
                if user is not None:
                    newValue += f"{i+1}: {user.mention}\n"
            oldEmbed.set_field_at(0, name=oldEmbed.fields[0].name, value=newValue)
            await interaction.message.edit(embeds=[oldEmbed])

            # 「インタラクションに失敗しました」対策
            await interaction.response.send_message("")
        except Exception as e:
            print(e)

    @discord.ui.button(label="辞退する",
                       style=discord.ButtonStyle.red)
    async def decline(self, interaction: discord.Interaction, button: discord.ui.Button):
        try:
            # database
            eventId = getEventID(interaction.message.id)
            if eventId is not None:
                deleteJoinedUser(eventId, interaction.user.id)
            joiningUserIDs = getJoinedUsers(eventId)
            oldEmbed = interaction.message.embeds[0] # get old embed
            newValue = ""
            for i, userId in enumerate(joiningUserIDs):
                user = self.bot.get_user(userId)
                if user is not None:
                    newValue += f"{i+1}: {user.mention}\n"
            oldEmbed.set_field_at(0, name=oldEmbed.fields[0].name, value=newValue)
            await interaction.message.edit(embeds=[oldEmbed])

            # 「インタラクションに失敗しました」対策
            await interaction.response.send_message("")
        except Exception as e:
            print(e)

    @discord.ui.button(label="コメント",
                       style=discord.ButtonStyle.gray)
    async def comment(self, interaction: discord.Interaction, button: discord.ui.Button):
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
                color=discord.Colour.random()
            )
            notifyEmbed.add_field(name="👥 Applicants", value=f"1: {e.creator.mention}")
            notifyEmbed.add_field(name="💬 Comments", value="")
            notifyEmbed.set_footer(text=f"Event was created by {e.creator.display_name}", icon_url=e.creator.avatar.url)
            notifyEmbed.timestamp = datetime.datetime.now()
            notifyView = EventView(self.bot, timeout=86400) # timeout - 24h
            notifyChan = self.bot.get_partial_messageable(settings.NOTIFY_CHAN)
            embed = await notifyChan.send(e.url, embeds=[notifyEmbed], view=notifyView)

            # database
            createTables()
            insertEvent(embed.id, e.id, e.creator_id)
            insertJoinedUser(e.id, e.creator_id)
        except Exception as e:
            print(e)

async def setup(bot):
    await bot.add_cog(Event(bot))