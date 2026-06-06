import datetime
import logging
import pytz

import discord
from discord.ext import commands

from models.event import EventInfo
from views.event_layout_view import EventNotificationLayoutView

logger = logging.getLogger("discord").getChild("notify_event")
tz = pytz.timezone("Asia/Tokyo")


async def reregister_event_views(bot: commands.Bot) -> None:
    """再起動後にアクティブなイベントビューをDiscordに再登録する。"""
    event_infos = await bot.event_repo.get_active_sessions(current_time=datetime.datetime.now(tz))
    if not event_infos:
        logger.info("No active event sessions found in the database.")
        return

    for event_info in event_infos:
        try:
            guild = await bot.fetch_guild(event_info.server_id)
        except discord.NotFound:
            logger.warning(f"Guild not found: guild_id={event_info.server_id}")
            continue
        try:
            discord_event = await guild.fetch_scheduled_event(event_info.event_id)
        except discord.NotFound:
            logger.warning(
                f"Event not found: event_id={event_info.event_id}, guild_id={event_info.server_id}")
            continue

        logger.info(f"Recreating event view: event_id={event_info.event_id}, guild_id={event_info.server_id}")
        bot.add_view(EventNotificationLayoutView(bot, discord_event, event_info.participant_ids))


class EventNotify(commands.Cog):
    """スケジュールイベントの作成・更新を監視し通知メッセージを管理するCog。"""

    def __init__(self, bot: commands.Bot) -> None:
        """Cogとボット参照を初期化する。"""
        self.bot = bot

    @commands.Cog.listener()
    async def on_scheduled_event_create(self, event: discord.ScheduledEvent) -> None:
        """イベント作成時に通知メッセージを送信しDBに記録する。"""
        jst_start_time = event.start_time.astimezone(tz)

        notify_channel = await self.bot.event_repo.get_notify_channel(event.guild.id)
        if notify_channel is None:
            logger.warning(f"Notify channel not registered: guild={event.guild.name}")
            return

        partial_channel = self.bot.get_partial_messageable(notify_channel.channel_id)
        try:
            notify_msg = await partial_channel.send(
                view=EventNotificationLayoutView(self.bot, event, [event.creator.id]))
        except discord.HTTPException as e:
            logger.error(f"Failed to send event notification: {e}")
            return

        event_info = EventInfo(
            event_id=event.id,
            server_id=event.guild.id,
            msg_id=notify_msg.id,
            author_id=event.creator.id,
            name=event.name,
            description=event.description,
            start_time=jst_start_time,
            was_ended=False,
            view_name=EventNotificationLayoutView.__name__,
            participant_ids=[event.creator.id],
        )
        await self.bot.event_repo.save_event(event_info)
        await self.bot.event_repo.add_participant(event.id, event.creator.id)
        await self.bot.point_repo.increment_point(event.guild.id, event.creator.id, 10)

    @commands.Cog.listener()
    async def on_scheduled_event_update(
        self,
        before: discord.ScheduledEvent,
        after: discord.ScheduledEvent,
    ) -> None:
        """イベント更新時に参加者リストを維持しながら通知メッセージを再描画する。"""
        notify_channel = await self.bot.event_repo.get_notify_channel(before.guild.id)
        if notify_channel is None:
            logger.warning(f"Notify channel not registered: guild={before.guild.name}")
            return

        event_info = await self.bot.event_repo.get_event_by_event_id(before.id)
        if event_info is None:
            logger.warning(f"Event record not found: event_id={before.id}")
            return

        partial_channel = self.bot.get_partial_messageable(notify_channel.channel_id)
        try:
            notify_msg = await partial_channel.fetch_message(event_info.msg_id)
            await notify_msg.edit(
                view=EventNotificationLayoutView(self.bot, after, event_info.participant_ids))
        except discord.NotFound:
            logger.warning(f"Notify message not found: msg_id={event_info.msg_id}")
        except discord.HTTPException as e:
            logger.error(f"Failed to update event notification: {e}")


async def setup(bot: commands.Bot) -> None:
    """EventNotify CogをBotに登録する。"""
    await bot.add_cog(EventNotify(bot))
