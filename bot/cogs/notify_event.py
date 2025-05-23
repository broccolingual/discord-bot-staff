import datetime
import logging
import traceback

import discord
from discord import app_commands
from discord.ext import commands

from utils import blank_interaction

logger = logging.getLogger("discord").getChild("notify_event")


class EventCommentForm(discord.ui.Modal):
    comment = discord.ui.TextInput(
        label="Contents", placeholder="I'll be a little late...", style=discord.TextStyle.long)

    def __init__(self, timeout=86400, origInteraction=None):  # timeout - 24h
        super().__init__(title="Comment", timeout=timeout)
        self.origInteraction = origInteraction

    async def on_submit(self, interaction: discord.Interaction):
        old_embed = self.origInteraction.message.embeds[0]
        if old_embed.fields[4] is None:
            old_embed.set_field_at(1, "💬 Comments", "")
        old_value = old_embed.fields[4].value
        old_value += f"\nFrom {interaction.user.mention} : **{self.comment}**"
        old_embed.set_field_at(
            4, name=old_embed.fields[4].name, value=old_value)
        await self.origInteraction.message.edit(embeds=[old_embed])
        await interaction.response.send_message("Your comment has been sent correctly.", ephemeral=True, delete_after=10)

    async def on_error(self, interaction: discord.Interaction, e: Exception):
        traceback.print_exception(type(e), e, e.__traceback__)


class EventView(discord.ui.View):
    def __init__(self, bot, event: discord.ScheduledEvent, timeout=86400):  # timeout - 24h
        super().__init__(timeout=timeout)
        self.bot = bot
        self.event = event

    async def disable_all_items(self):
        for item in self.children:
            item.disable = True

    async def on_timeout(self):
        await self.disable_all_items()

    @discord.ui.button(label="Join",
                       style=discord.ButtonStyle.success,
                       custom_id="join_event_btn")
    async def join(self, interaction: discord.Interaction, button: discord.ui.Button):
        if self.event is None:
            await interaction.response.send_message("Failed to retrieve event.", ephemeral=True, delete_after=10)
            return
        try:
            joining_user_ids = await self.bot.db.get_joined_user_ids(self.event.id)

            if interaction.user.id in joining_user_ids:
                await interaction.response.send_message("You have already joined.", ephemeral=True, delete_after=10)
                return

            await self.bot.db.add_joined_user(self.event.id, interaction.user.id)

            joining_user_ids.append(interaction.user.id)
        except Exception as e:
            await interaction.response.send_message("Oops... An error occurred during processing.", ephemeral=True, delete_after=10)
            traceback.print_exception(type(e), e, e.__traceback__)
            return

        # update embed
        old_embed = interaction.message.embeds[0]  # get old embed
        new_value = ""
        for i, joining_user_id in enumerate(joining_user_ids):
            user = self.bot.get_user(joining_user_id)
            if user is not None:
                new_value += f"`{i+1}.` {user.mention}\n"
        old_embed.set_field_at(
            3, name=old_embed.fields[3].name, value=new_value)
        await interaction.response.edit_message(embed=old_embed)

    @discord.ui.button(label="Decline",
                       style=discord.ButtonStyle.red,
                       custom_id="decline_event_btn")
    async def decline(self, interaction: discord.Interaction, button: discord.ui.Button):
        if self.event is None:
            await interaction.response.send_message("Failed to retrieve event.", ephemeral=True, delete_after=10)
            return
        try:
            joining_user_ids = await self.bot.db.get_joined_user_ids(self.event.id)

            if interaction.user.id not in joining_user_ids:
                await interaction.response.send_message("You are not participating in this event.", ephemeral=True, delete_after=10)
                return

            await self.bot.db.delete_joined_user(self.event.id, interaction.user.id)

            joining_user_ids.remove(interaction.user.id)
        except Exception as e:
            await interaction.response.send_message("Oops... An error occurred during processing.", ephemeral=True, delete_after=10)
            return

        # update embed
        old_embed = interaction.message.embeds[0]  # get old embed
        new_value = ""
        for i, joining_user_id in enumerate(joining_user_ids):
            user = self.bot.get_user(joining_user_id)
            if user is not None:
                new_value += f"`{i+1}.` {user.mention}\n"
        old_embed.set_field_at(
            3, name=old_embed.fields[3].name, value=new_value)
        await interaction.response.edit_message(embed=old_embed)

    @discord.ui.button(label="Leave a comment",
                       style=discord.ButtonStyle.blurple,
                       custom_id="comment_event_btn")
    async def comment(self, interaction: discord.Interaction, button: discord.ui.Button):
        try:
            await interaction.response.send_modal(EventCommentForm(timeout=600, origInteraction=interaction))
        except Exception:
            await interaction.response.send_message("Oops... An error occurred during processing.", ephemeral=True, delete_after=10)

    @discord.ui.button(label="Start event",
                       style=discord.ButtonStyle.gray,
                       custom_id="start_event_btn")
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
                       style=discord.ButtonStyle.gray,
                       custom_id="cancel_event_btn")
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
        logger.info(
            f"Event was created: {e.guild.name=} - {e.name=} - {e.start_time=}")

        # create & send embed
        notify_embed = discord.Embed(
            title=e.name, description=e.description, color=discord.Colour.orange())
        notify_embed.set_author(
            name="Event (Scheduled)", icon_url=e.guild.icon.url)
        notify_embed.add_field(name="🕒 Schedule",
                               value=f"**{e.start_time.astimezone(datetime.timezone(datetime.timedelta(hours=9))).strftime('%Y-%m-%d %H:%M')}~**")
        if e.location is not None:
            notify_embed.add_field(
                name="📍 Location", value=f"**{e.location}**")
        else:
            notify_embed.add_field(
                name="📡 Channel", value=e.channel.mention)
        notify_embed.add_field(name="🔗 Event link", value=e.url)
        notify_embed.add_field(name="👥 Applicants",
                               value=f"`1.` {e.creator.mention}")
        notify_embed.add_field(name="💬 Comments", value="")
        notify_embed.set_footer(
            text=f"Event was created by {e.creator.display_name}", icon_url=e.creator.avatar.url)
        notify_embed.set_thumbnail(
            url=e.cover_image.url if e.cover_image is not None else e.creator.avatar.url)
        notify_embed.timestamp = datetime.datetime.now()
        notify_view = EventView(self.bot, e, timeout=86400)  # timeout - 24h

        try:
            channel = await self.bot.db.get_event_notify_channel(e.guild.id)
        except Exception:
            logger.error(
                f"Failed to get notify channel: {e.guild.name=}")
            return

        if channel is None:
            logger.warning(
                f"Notify channel is not registered: {e.guild.name=}")
            return

        notify_chan = self.bot.get_partial_messageable(channel["channel_id"])
        embed = await notify_chan.send(embeds=[notify_embed], view=notify_view)

        await self.bot.db.add_event(embed.id, e.id, e.creator.id)
        await self.bot.db.add_joined_user(e.id, e.creator.id)

    @commands.Cog.listener()
    async def on_scheduled_event_update(self, before, after):
        notify_channel_data = await self.bot.db.get_event_notify_channel(before.guild.id)

        if notify_channel_data is None:
            logger.warning(
                f"Notify channel is not registered: {before.guild.name=}")
            return

        notify_channel = self.bot.get_partial_messageable(
            notify_channel_data["channel_id"])

        notify_msg_data = await self.bot.db.get_message(before.id)

        if notify_msg_data is None:
            logger.warning(
                f"Notify message is not registered: {before.guild.name=}")
            return

        notify_msg = await notify_channel.fetch_message(notify_msg_data["msg_id"])
        old_embed = notify_msg.embeds[0]

        if after.status == discord.EventStatus.active:
            new_embed = discord.Embed(
                title=after.name, description=after.description, color=discord.Colour.brand_green())
            new_embed.set_author(name="Event (Ongoing)",
                                 icon_url=after.guild.icon.url)
            logger.info(
                f"Event was started: {after.guild.name=} - {after.name=} - {after.start_time=}")
        elif after.status == discord.EventStatus.ended or after.status == discord.EventStatus.cancelled:
            new_embed = discord.Embed(
                title=after.name, description=after.description, color=discord.Colour.brand_red())
            new_embed.set_author(name="Event (Inactive)",
                                 icon_url=after.guild.icon.url)
            logger.info(
                f"Event was ended: {after.guild.name=} - {after.name=} - {after.start_time=}")
        else:
            new_embed = discord.Embed(
                title=after.name, description=after.description, color=discord.Colour.orange())
            new_embed.set_author(name="Event (Scheduled)",
                                 icon_url=after.guild.icon.url)
            logger.info(
                f"Event was updated: {after.guild.name=} - {after.name=} - {after.start_time=}")

        new_embed.set_thumbnail(
            url=after.cover_image.url if after.cover_image is not None else after.creator.avatar.url)

        for i, field in enumerate(old_embed.fields):
            if i == 0:  # Schedule
                new_embed.add_field(
                    name=field.name, value=f"**{after.start_time.astimezone(datetime.timezone(datetime.timedelta(hours=9))).strftime('%Y-%m-%d %H:%M')}~**")
            elif i == 1:  # Location or Channel
                if after.location is not None:
                    new_embed.add_field(
                        name="📍 Location", value=f"**{after.location}**")
                else:
                    new_embed.add_field(
                        name="📡 Channel", value=after.channel.mention)
            else:
                new_embed.add_field(name=field.name, value=field.value)

        new_embed.set_footer(text=old_embed.footer.text,
                             icon_url=old_embed.footer.icon_url)
        new_embed.timestamp = old_embed.timestamp

        if after.status == discord.EventStatus.ended or after.status == discord.EventStatus.cancelled:
            await notify_msg.edit(embeds=[new_embed], view=None)
        else:
            await notify_msg.edit(embeds=[new_embed])


class EventNotifyChannelResistrationView(discord.ui.View):
    def __init__(self, bot, timeout=60):
        super().__init__(timeout=timeout)
        self.bot = bot
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
        await blank_interaction(interaction)  # 「インタラクションに失敗しました」対策

    @discord.ui.button(label="Register",
                       style=discord.ButtonStyle.success)
    async def register(self, interaction: discord.Interaction, button: discord.ui.Button):
        if self.channel is None:
            await interaction.response.send_message("Please select a channel.")
            return

        try:
            registeredId = await self.bot.db.get_event_notify_channel(interaction.guild.id)
        except Exception as e:
            logger.error(
                f"Failed to get notify channel: {interaction.guild.name=}, {e=}")
            return

        if registeredId is None:
            try:
                await self.bot.db.add_event_notify_channel(interaction.guild.id, self.channel.values[0].id)

                await interaction.response.edit_message(content="Notify channel is registered.", view=None)
            except Exception as e:
                logger.error(
                    f"Failed to add notify channel: {interaction.guild.name=}, {e=}")
                return
        else:
            try:
                await self.bot.db.update_event_notify_channel(interaction.guild.id, self.channel.values[0].id)

                await interaction.response.edit_message(content="Notify channel is updated.", view=None)
            except Exception:
                logger.error(
                    f"Failed to update notify channel: {interaction.guild.name=}")
                return


class EventNotifyChannelResister(app_commands.Group):
    def __init__(self, bot, name, description):
        super().__init__(name=name, description=description)
        self.bot = bot

    @app_commands.command(
        name="resister",
        description="Register the channel to notify (only for administrators)",
    )
    @app_commands.checks.has_permissions(administrator=True)
    async def register(self, interaction: discord.Interaction):
        await interaction.response.send_message("Please click the button to register the channel.", view=EventNotifyChannelResistrationView(self.bot), ephemeral=True)

    @register.error
    async def register_error(self, interaction: discord.Interaction, error: app_commands.AppCommandError):
        if isinstance(error, app_commands.MissingPermissions):
            await interaction.response.send_message("You don't have permission to use this command.", ephemeral=True, delete_after=10)


async def setup(bot):
    await bot.add_cog(EventNotify(bot))
    bot.tree.add_command(EventNotifyChannelResister(
        bot, name="notify", description="Notify channel registration"))
