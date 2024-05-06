import datetime

import discord
from discord.ext import commands

from utils.template import getSubcommandsEmbed
from db.interfaces import DB
from cogs.pointManager import PointManager

class EventForm(discord.ui.Modal):
    about = discord.ui.TextInput(label="Contents", placeholder="I'll be a little late...", style=discord.TextStyle.long)

    def __init__(self, bot, timeout=86400, origInteraction=None): # timeout - 24h
        super().__init__(title="Comment", timeout=timeout)
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
        await interaction.response.send_message("") # 「インタラクションに失敗しました」対策

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
    
    @discord.ui.button(label="Join",
                       style=discord.ButtonStyle.success)
    async def join(self, interaction: discord.Interaction, button: discord.ui.Button):
        try:
            # database
            db = DB()
            event = db.getEvent(interaction.message.id)
            if event is not None:
                db.addJoinedUser(event.event_id, interaction.user.id)
            joiningUsers = db.getJoinedUsers(event.event_id)
            oldEmbed = interaction.message.embeds[0] # get old embed
            newValue = ""
            for i, joiningUser in enumerate(joiningUsers):
                user = self.bot.get_user(joiningUser.user_id)
                if user is not None:
                    newValue += f"`{i+1}.` {user.mention}\n"
            oldEmbed.set_field_at(0, name=oldEmbed.fields[0].name, value=newValue)
            await PointManager.addPoint(interaction.guild.id, interaction.user.id, 2) # Point
            await interaction.message.edit(embeds=[oldEmbed])
            await interaction.response.send_message("") # 「インタラクションに失敗しました」対策
        except Exception as e:
            print(e)

    @discord.ui.button(label="Decline",
                       style=discord.ButtonStyle.red)
    async def decline(self, interaction: discord.Interaction, button: discord.ui.Button):
        try:
            # database
            db = DB()
            event = db.getEvent(interaction.message.id)
            if event is not None:
                db.deleteJoinedUser(event.event_id, interaction.user.id)
            joiningUsers = db.getJoinedUsers(event.event_id)
            oldEmbed = interaction.message.embeds[0] # get old embed
            newValue = ""
            for i, joiningUser in enumerate(joiningUsers):
                user = self.bot.get_user(joiningUser.user_id)
                if user is not None:
                    newValue += f"{i+1}: {user.mention}\n"
            oldEmbed.set_field_at(0, name=oldEmbed.fields[0].name, value=newValue)
            await PointManager.removePoint(interaction.guild.id, interaction.user.id, 2) # Point
            await interaction.message.edit(embeds=[oldEmbed])
            await interaction.response.send_message("") # 「インタラクションに失敗しました」対策
        except Exception as e:
            print(e)

    @discord.ui.button(label="Leave a comment",
                       style=discord.ButtonStyle.gray)
    async def comment(self, interaction: discord.Interaction, button: discord.ui.Button):
        try:
            await interaction.response.send_modal(EventForm(self.bot, timeout=86400, origInteraction=interaction))
        except Exception as e:
            print(e)

class EventNotify(commands.Cog):
    def __init__(self, bot):
        self.bot = bot

    @commands.Cog.listener()
    async def on_scheduled_event_create(self, e):
        try:
            # create & send embed
            notifyEmbed = discord.Embed(description="Event details", color=discord.Colour.random())
            notifyEmbed.add_field(name="👥 Applicants", value=f"1: {e.creator.mention}")
            notifyEmbed.add_field(name="💬 Comments", value="")
            notifyEmbed.set_footer(text=f"Event was created by {e.creator.display_name}", icon_url=e.creator.avatar.url)
            notifyEmbed.timestamp = datetime.datetime.now()
            notifyView = EventView(self.bot, timeout=86400) # timeout - 24h
            
            # database
            db = DB()
            channel = db.getEventNotifyChannel(e.guild.id)
            if channel is None:
                return
            notifyChan = self.bot.get_partial_messageable(channel.channel_id)
            embed = await notifyChan.send(e.url, embeds=[notifyEmbed], view=notifyView)
            db.addEvent(embed.id, e.id, e.creator.id)
            db.addJoinedUser(e.id, e.creator.id)
            await PointManager.addPoint(e.guild.id, e.creator.id, 5) # Point
        except Exception as e:
            print(e)
            
class EventNotifyChannelResistrationView(discord.ui.View):
    def __init__(self, bot, timeout=60):
        super().__init__(timeout=timeout)
        self.bot = bot
        self.channel = None
        
    async def disable_all_items(self):
        for item in self.children:
            item.disable = True
        await self.message.edit(view=self)
        
    async def on_timeout(self):
        await self.disable_all_items()
    
    @discord.ui.select(
        placeholder="Select a channel to notify",
        cls=discord.ui.ChannelSelect,
        channel_types=[discord.ChannelType.text]
    )
    async def select_channel(self, interaction: discord.Interaction, channel: discord.TextChannel):
        self.channel = channel
        await interaction.response.send_message("")
    
    @discord.ui.button(label="Register",
                       style=discord.ButtonStyle.success)
    async def register(self, interaction: discord.Interaction, button: discord.ui.Button):
        try:
            if self.channel is None:
                await interaction.response.send_message("Please select a channel.")
                return
            # database
            db = DB()
            registeredId = db.getEventNotifyChannel(interaction.guild.id)
            if registeredId is None:
                db.addEventNotifyChannel(interaction.guild.id, self.channel.values[0].id)
                await interaction.response.edit_message(content="Notify channel is registered.", view=None)
            else:
                db.updateEventNotifyChannel(interaction.guild.id, self.channel.values[0].id)
                await interaction.response.edit_message(content="Notify channel is updated.", view=None)
        except Exception as e:
            await interaction.response.edit_message(content="Notify channel is not updated by some reason.", view=None)
            print(e)
            
class EventNotifyChannelResister(commands.Cog):
    def __init__(self, bot):
        self.bot = bot
    
    @commands.group(
        description="Notify channel registration",
    )
    async def notify(self, ctx):
        if ctx.invoked_subcommand is None:
            await ctx.reply(f"{ctx.author.mention}Subcommand is required.", embed=getSubcommandsEmbed(ctx.command))
            
    @notify.command(
        description="Register the channel to notify (only for administrators)",
    )
    @commands.has_permissions(administrator=True)
    async def register(self, ctx):
        try:
            await ctx.reply("Please click the button to register the channel.", view=EventNotifyChannelResistrationView(self.bot))
        except Exception as e:
            print(e)

async def setup(bot):
    await bot.add_cog(EventNotify(bot))
    await bot.add_cog(EventNotifyChannelResister(bot))
