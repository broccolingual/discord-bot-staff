import datetime
import logging
import traceback

import discord
from discord import app_commands
from discord.ext import commands

from utils import blank_interaction
from db.interfaces import DB as db
from cogs.pointManager import PointManager

logger = logging.getLogger("discord.bot").getChild("eventManager")

class EventCommentForm(discord.ui.Modal):
    comment = discord.ui.TextInput(label="Contents", placeholder="I'll be a little late...", style=discord.TextStyle.long)
    
    def __init__(self, timeout=86400, origInteraction=None): # timeout - 24h
        super().__init__(title="Comment", timeout=timeout)
        self.origInteraction = origInteraction

    async def on_submit(self, interaction: discord.Interaction):
        oldEmbed = self.origInteraction.message.embeds[0]
        if oldEmbed.fields[4] is None:
            oldEmbed.set_field_at(1, "💬 Comments", "")
        oldValue = oldEmbed.fields[4].value
        oldValue += f"\nFrom {interaction.user.mention} : **{self.comment}**"
        oldEmbed.set_field_at(4, name=oldEmbed.fields[4].name, value=oldValue)
        await self.origInteraction.message.edit(embeds=[oldEmbed])
        await interaction.response.send_message("Your comment has sended correctly.", ephemeral=True, delete_after=10)
        
    async def on_error(self, interaction: discord.Interaction, e: Exception):
        traceback.print_exception(type(e), e, e.__traceback__)

class EventView(discord.ui.View):
    def __init__(self, bot, event: discord.ScheduledEvent, timeout=86400): # timeout - 24h
        super().__init__(timeout=timeout)
        self.bot = bot
        self.event = event

    async def disable_all_items(self):
        for item in self.children:
            item.disable = True

    async def on_timeout(self):
        await self.disable_all_items()
    
    @discord.ui.button(label="Join",
                       style=discord.ButtonStyle.success)
    async def join(self, interaction: discord.Interaction, button: discord.ui.Button):
        if self.event is None:
            await interaction.response.send_message("Failed to retrieve event.", ephemeral=True, delete_after=10)
            return
        try:
            joining_user_ids = [o.user_id for o in await db.getJoinedUsers(self.event.id)]
            if interaction.user.id in joining_user_ids:
                await interaction.response.send_message("You have already joined.", ephemeral=True, delete_after=10)
                return
            await db.addJoinedUser(self.event.id, interaction.user.id)
            joiningUserIDs.append(interaction.user.id)
            await PointManager.addPoint(interaction.guild.id, interaction.user.id, 2) # Point
        except Exception as e:
            await interaction.response.send_message("Oops... An error occurred during processing.", ephemeral=True, delete_after=10)
            traceback.print_exception(type(e), e, e.__traceback__)
            return
        
        # update embed
        oldEmbed = interaction.message.embeds[0] # get old embed
        newValue = ""
        for i, joining_user_id in enumerate(joining_user_ids):
            user = self.bot.get_user(joining_user_id)
            if user is not None:
                newValue += f"`{i+1}.` {user.mention}\n"
        oldEmbed.set_field_at(3, name=oldEmbed.fields[3].name, value=newValue)
        await interaction.response.edit_message(embed=oldEmbed)

    @discord.ui.button(label="Decline",
                       style=discord.ButtonStyle.red)
    async def decline(self, interaction: discord.Interaction, button: discord.ui.Button):
        if self.event is None:
            await interaction.response.send_message("Failed to retrieve event.", ephemeral=True, delete_after=10)
            return
        try:
            joining_user_ids = [o.user_id for o in await db.getJoinedUsers(self.event.id)]
            if interaction.user.id not in joining_user_ids:
                await interaction.response.send_message("You are not participating in this event.", ephemeral=True, delete_after=10)
                return
            await db.deleteJoinedUser(self.event.id, interaction.user.id)
            joiningUserIDs.remove(interaction.user.id)
            await PointManager.removePoint(interaction.guild.id, interaction.user.id, 2) # Point
        except Exception as e:
            await interaction.response.send_message("Oops... An error occurred during processing.", ephemeral=True, delete_after=10)
            traceback.print_exception(type(e), e, e.__traceback__)
            return
        
        # update embed
        oldEmbed = interaction.message.embeds[0] # get old embed
        newValue = ""
        for i, joining_user_id in enumerate(joining_user_ids):
            user = self.bot.get_user(joining_user_id)
            if user is not None:
                newValue += f"`{i+1}.` {user.mention}\n"
        oldEmbed.set_field_at(3, name=oldEmbed.fields[3].name, value=newValue)
        await interaction.response.edit_message(embed=oldEmbed)

    @discord.ui.button(label="Leave a comment",
                       style=discord.ButtonStyle.blurple)
    async def comment(self, interaction: discord.Interaction, button: discord.ui.Button):
        try:
            await interaction.response.send_modal(EventCommentForm(timeout=86400, origInteraction=interaction))
        except Exception as e:
            await interaction.response.send_message("Oops... An error occurred during processing.", ephemeral=True, delete_after=10)
            print(e)
            
    @discord.ui.button(label="Start event",
                       style=discord.ButtonStyle.gray)
    async def start(self, interaction: discord.Interaction, button: discord.ui.Button):
        if self.event is None:
            await interaction.response.send_message("Failed to retrieve event.", ephemeral=True, delete_after=10)
            return
        
        if self.event.creator != interaction.user:
            await interaction.response.send_message("You are not the creator of this event.", ephemeral=True, delete_after=10)
            return
        
        if self.event.status == discord.EventStatus.scheduled:
            await self.event.start()
            await interaction.response.send_message("Event has started!", ephemeral=True, delete_after=10)
        elif self.event.status == discord.EventStatus.active or self.event.status == discord.EventStatus.ended:
            await interaction.response.send_message("This event is already active.", ephemeral=True, delete_after=10)
            
    @discord.ui.button(label="Cancel/End event",
                       style=discord.ButtonStyle.gray)
    async def cancel(self, interaction: discord.Interaction, button: discord.ui.Button):
        if self.event is None:
            await interaction.response.send_message("Failed to retrieve event.", ephemeral=True, delete_after=10)
            return
        
        if self.event.creator != interaction.user:
            await interaction.response.send_message("You are not the creator of this event.", ephemeral=True, delete_after=10)
            return
        
        if self.event.status == discord.EventStatus.active:
            await self.event.end()
            await interaction.response.send_message("Event was ended correctly.", ephemeral=True, delete_after=10)
        elif self.event.status == discord.EventStatus.scheduled:
            await self.event.cancel()
            await interaction.response.send_message("Event was canceled correctly.", ephemeral=True, delete_after=10)

class EventNotify(commands.Cog):
    def __init__(self, bot):
        self.bot = bot

    @commands.Cog.listener()
    async def on_scheduled_event_create(self, e):
        try:
            # create & send embed
            notifyEmbed = discord.Embed(title=e.name, description=e.description, color=discord.Colour.orange())
            notifyEmbed.set_author(name="Event (Scheduled)", icon_url=e.guild.icon.url)
            notifyEmbed.add_field(name="🕒 Schedule",
                                  value=f"**{e.start_time.astimezone(datetime.timezone(datetime.timedelta(hours=9))).strftime('%Y-%m-%d %H:%M')}~**")
            if e.location is not None:
                notifyEmbed.add_field(name="📍 Location", value=f"**{e.location}**")
            else:
                notifyEmbed.add_field(name="📡 Channel", value=e.channel.mention)
            notifyEmbed.add_field(name="🔗 Event link", value=e.url)
            notifyEmbed.add_field(name="👥 Applicants", value=f"`1.` {e.creator.mention}")
            notifyEmbed.add_field(name="💬 Comments", value="")
            notifyEmbed.set_footer(text=f"Event was created by {e.creator.display_name}", icon_url=e.creator.avatar.url)
            notifyEmbed.set_thumbnail(url=e.cover_image.url if e.cover_image is not None else e.creator.avatar.url)
            notifyEmbed.timestamp = datetime.datetime.now()
            notifyView = EventView(self.bot, e, timeout=86400) # timeout - 24h
            
            # database
            channel = await db.getEventNotifyChannel(e.guild.id)
            if channel is None:
                return
            notifyChan = self.bot.get_partial_messageable(channel.channel_id)
            embed = await notifyChan.send(embeds=[notifyEmbed], view=notifyView)
            await db.addEvent(embed.id, e.id, e.creator.id)
            await db.addJoinedUser(e.id, e.creator.id)
            await PointManager.addPoint(e.guild.id, e.creator.id, 5) # Point
        except Exception as err:
            print(err)
            
    @commands.Cog.listener()
    async def on_scheduled_event_update(self, before, after):
        try:
            # database
            notifyChanData = await db.getEventNotifyChannel(before.guild.id)
            if notifyChanData is None:
                return
            notifyChan = self.bot.get_partial_messageable(notifyChanData.channel_id)
            notifyMsgData = await db.getMessage(before.id)
            if notifyMsgData is None:
                return
            notifyMsg = await notifyChan.fetch_message(notifyMsgData.msg_id)
            oldEmbed = notifyMsg.embeds[0]
            if after.status == discord.EventStatus.active:
                newEmbed = discord.Embed(title=after.name, description=after.description, color=discord.Colour.brand_green())
                newEmbed.set_author(name="Event (Ongoing)", icon_url=after.guild.icon.url)
            elif after.status == discord.EventStatus.ended or after.status == discord.EventStatus.cancelled:
                newEmbed = discord.Embed(title=after.name, description=after.description, color=discord.Colour.brand_red())
                newEmbed.set_author(name="Event (Inactive)", icon_url=after.guild.icon.url)
            else:
                newEmbed = discord.Embed(title=after.name, description=after.description, color=discord.Colour.orange())
                newEmbed.set_author(name="Event (Scheduled)", icon_url=after.guild.icon.url)
            newEmbed.set_thumbnail(url=after.cover_image.url if after.cover_image is not None else after.creator.avatar.url)
            for i, field in enumerate(oldEmbed.fields):
                if i == 0: # Schedule
                    newEmbed.add_field(name=field.name, value=f"**{after.start_time.astimezone(datetime.timezone(datetime.timedelta(hours=9))).strftime('%Y-%m-%d %H:%M')}~**")
                elif i == 1: # Location or Channel
                    if after.location is not None:
                        newEmbed.add_field(name="📍 Location", value=f"**{after.location}**")
                    else:
                        newEmbed.add_field(name="📡 Channel", value=after.channel.mention)
                else:
                    newEmbed.add_field(name=field.name, value=field.value)
            newEmbed.set_footer(text=oldEmbed.footer.text, icon_url=oldEmbed.footer.icon_url)
            newEmbed.timestamp = oldEmbed.timestamp
            if after.status == discord.EventStatus.ended or after.status == discord.EventStatus.cancelled:
                await notifyMsg.edit(embeds=[newEmbed], view=None)
            else:
                await notifyMsg.edit(embeds=[newEmbed])
        except Exception as err:
            print(err)
            
class EventNotifyChannelResistrationView(discord.ui.View):
    def __init__(self, timeout=60):
        super().__init__(timeout=timeout)
        self.channel = None
        
    async def disable_all_items(self):
        for item in self.children:
            item.disable = True
        
    async def on_timeout(self):
        await self.disable_all_items()
    
    @discord.ui.select(
        placeholder="Select a channel to notify",
        cls=discord.ui.ChannelSelect,
        channel_types=[discord.ChannelType.text]
    )
    async def select_channel(self, interaction: discord.Interaction, channel: discord.TextChannel):
        self.channel = channel
        await blank_interaction(interaction) # 「インタラクションに失敗しました」対策
    
    @discord.ui.button(label="Register",
                       style=discord.ButtonStyle.success)
    async def register(self, interaction: discord.Interaction, button: discord.ui.Button):
        try:
            if self.channel is None:
                await interaction.response.send_message("Please select a channel.")
                return
            # database
            registeredId = await db.getEventNotifyChannel(interaction.guild.id)
            if registeredId is None:
                await db.addEventNotifyChannel(interaction.guild.id, self.channel.values[0].id)
                await interaction.response.edit_message(content="Notify channel is registered.", view=None)
            else:
                await db.updateEventNotifyChannel(interaction.guild.id, self.channel.values[0].id)
                await interaction.response.edit_message(content="Notify channel is updated.", view=None)
        except Exception as err:
            await interaction.response.edit_message(content="Notify channel is not updated by some reason.", view=None)
            print(err)
            
class EventNotifyChannelResister(app_commands.Group):            
    @app_commands.command(
        name="resister",
        description="Register the channel to notify (only for administrators)",
    )
    @app_commands.checks.has_permissions(administrator=True)
    async def register(self, interaction: discord.Interaction):
        logger.info(f"command: 'notify resister' executed by {interaction.user.name}")
        try:
            await interaction.response.send_message("Please click the button to register the channel.", view=EventNotifyChannelResistrationView())
        except Exception as err:
            print(err)

async def setup(bot):
    await bot.add_cog(EventNotify(bot))
    bot.tree.add_command(EventNotifyChannelResister(name="notify", description="Notify channel registration"))
