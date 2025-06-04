import datetime
import logging
import traceback
import pytz

import discord
from discord import app_commands
from discord.ext import commands
from matplotlib import pyplot as plt
import matplotlib.ticker as ticker
import numpy as np

logger = logging.getLogger("discord").getChild("notify_event")
tz = pytz.timezone("Asia/Tokyo")


class EventCommentForm(discord.ui.Modal):
    comment = discord.ui.TextInput(
        label="Content", placeholder="Enter your comment...", style=discord.TextStyle.long)

    def __init__(self, timeout=600, origInteraction=None):  # timeout - 10min
        super().__init__(title="Leave a comment", timeout=timeout)
        self.origInteraction = origInteraction

    async def on_submit(self, interaction: discord.Interaction):
        comment_embed = discord.Embed(
            description=self.comment,
            color=discord.Colour.blue(),
            timestamp=datetime.datetime.now(tz)
        )
        comment_embed.set_footer(
            text=f"{interaction.user.display_name}",
            icon_url=interaction.user.avatar.url if interaction.user.avatar else interaction.user.default_avatar.url
        )
        await self.origInteraction.message.edit(embeds=[*self.origInteraction.message.embeds, comment_embed])
        await interaction.response.send_message("コメントが正常に送信されました。", ephemeral=True, delete_after=10)

    async def on_error(self, interaction: discord.Interaction, e: Exception):
        traceback.print_exception(type(e), e, e.__traceback__)


class EventView(discord.ui.View):
    def __init__(self, bot, event: discord.ScheduledEvent, timeout=None):  # Persistent View
        super().__init__(timeout=timeout)
        self.bot = bot
        self.event = event

    @discord.ui.button(label="参加",
                       style=discord.ButtonStyle.success,
                       custom_id="join_event_btn")
    async def join(self, interaction: discord.Interaction, button: discord.ui.Button):
        if self.event is None:
            await interaction.response.send_message("イベントの取得に失敗しました。", ephemeral=True, delete_after=10)
            return
        try:
            joining_user_ids = await self.bot.db.get_joined_user_ids(self.event.id)

            if interaction.user.id in joining_user_ids:
                await interaction.response.send_message("あなたはすでに参加しています。", ephemeral=True, delete_after=10)
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
            2, name=old_embed.fields[2].name, value=new_value)
        await interaction.response.edit_message(embeds=[old_embed, *interaction.message.embeds[1:]])

    @discord.ui.button(label="辞退",
                       style=discord.ButtonStyle.red,
                       custom_id="decline_event_btn")
    async def decline(self, interaction: discord.Interaction, button: discord.ui.Button):
        if self.event is None:
            await interaction.response.send_message("イベントの取得に失敗しました。", ephemeral=True, delete_after=10)
            return
        try:
            joining_user_ids = await self.bot.db.get_joined_user_ids(self.event.id)

            if interaction.user.id not in joining_user_ids:
                await interaction.response.send_message("あなたはこのイベントに参加していません。", ephemeral=True, delete_after=10)
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
            2, name=old_embed.fields[2].name, value=new_value)
        await interaction.response.edit_message(embeds=[old_embed, *interaction.message.embeds[1:]])

    @discord.ui.button(label="コメントを送信",
                       style=discord.ButtonStyle.blurple,
                       custom_id="comment_event_btn")
    async def comment(self, interaction: discord.Interaction, button: discord.ui.Button):
        try:
            await interaction.response.send_modal(EventCommentForm(timeout=600, origInteraction=interaction))
        except Exception:
            await interaction.response.send_message("Oops... An error occurred during processing.", ephemeral=True, delete_after=10)

    @discord.ui.button(label="イベントを開始",
                       style=discord.ButtonStyle.gray,
                       custom_id="start_event_btn")
    async def start(self, interaction: discord.Interaction, button: discord.ui.Button):
        if self.event is None:
            await interaction.response.send_message("イベントの取得に失敗しました。", ephemeral=True, delete_after=10)
            return

        if self.event.creator != interaction.user:
            await interaction.response.send_message("あなたはこのイベントの作成者ではありません。", ephemeral=True, delete_after=10)
            return

        if self.event.status == discord.EventStatus.scheduled:
            await self.event.start()
            await interaction.response.send_message("イベントが開始されました！", ephemeral=True, delete_after=10)
        elif self.event.status == discord.EventStatus.active or self.event.status == discord.EventStatus.ended:
            await interaction.response.send_message("このイベントはすでにアクティブです。", ephemeral=True, delete_after=10)

    @discord.ui.button(label="イベントをキャンセル/終了",
                       style=discord.ButtonStyle.gray,
                       custom_id="cancel_event_btn")
    async def cancel(self, interaction: discord.Interaction, button: discord.ui.Button):
        if self.event is None:
            await interaction.response.send_message("イベントの取得に失敗しました。", ephemeral=True, delete_after=10)
            return

        if self.event.creator != interaction.user:
            await interaction.response.send_message("あなたはこのイベントの作成者ではありません。", ephemeral=True, delete_after=10)
            return

        if self.event.status == discord.EventStatus.active:
            await self.event.end()
            await interaction.response.send_message("イベントが正常に終了しました。", ephemeral=True, delete_after=10)
        elif self.event.status == discord.EventStatus.scheduled:
            await self.event.cancel()
            await interaction.response.send_message("イベントが正常にキャンセルされました。", ephemeral=True, delete_after=10)
        elif self.event.status == discord.EventStatus.ended or self.event.status == discord.EventStatus.cancelled:
            await interaction.response.send_message("このイベントはすでに終了しています。", ephemeral=True, delete_after=10)

    @classmethod
    async def from_session_record(cls, bot, record: dict):
        guild_id = record.get("server_id")
        event_id = record.get("event_id")
        try:
            guild = await bot.fetch_guild(guild_id)
        except discord.NotFound:
            logger.warning(f"Guild with ID {guild_id} not found.")
            return None
        try:
            event = await guild.fetch_scheduled_event(event_id)
        except discord.NotFound:
            logger.warning(
                f"Event with ID {event_id} not found in guild {guild.name}.")
            return None
        return cls(bot, event)


async def load_event_view_sessions(bot):
    """
    Load all event view sessions from the database.
    """
    sessions = await bot.db.get_active_event_sessions(
        current_time=datetime.datetime.now(tz))
    if sessions is None:
        logger.info("No event view sessions found in the database.")
        return

    for session in sessions:
        view = await EventView.from_session_record(bot, session)
        if view is not None:
            bot.add_view(view)  # Recreate the view with the bot and event
    logger.info(
        f"Loaded {len(sessions)} event view sessions from the database.")


class EventNotify(commands.Cog):
    def __init__(self, bot):
        self.bot = bot

    @commands.Cog.listener()
    async def on_scheduled_event_create(self, e):
        # create & send embed
        notify_embed = discord.Embed(
            title=e.name, description=e.description, color=discord.Colour.orange())
        notify_embed.set_author(
            name="Scheduled Event", icon_url=e.guild.icon.url)
        fixed_start_time = e.start_time.astimezone(tz)
        notify_embed.add_field(name="🕒 Date",
                               value=f"**{fixed_start_time.strftime('%Y-%m-%d %H:%M')}~**")
        if e.location is not None:
            notify_embed.add_field(
                name="📍 Location", value=f"**{e.location}**")
        else:
            notify_embed.add_field(
                name="📡 Channel", value=e.channel.mention)
        notify_embed.add_field(name="👥 Participants",
                               value=f"`1.` {e.creator.mention}")
        notify_embed.set_footer(
            text=f"Created by {e.creator.display_name}", icon_url=e.creator.avatar.url)
        notify_embed.set_thumbnail(
            url=e.cover_image.url if e.cover_image is not None else e.guild.icon.url)
        notify_embed.timestamp = datetime.datetime.now()
        notify_view = EventView(self.bot, e)

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

        await self.bot.db.add_event(embed.id, e.id, e.guild.id, e.creator.id, e.name, e.description, fixed_start_time, notify_view.__class__.__name__, was_ended=False)
        await self.bot.db.add_joined_user(e.id, e.creator.id)
        await self.bot.db.increment_point(e.guild.id, e.creator.id, 10)

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
            new_embed.set_author(name="Ongoing Event",
                                 icon_url=after.guild.icon.url)
            logger.info(
                f"Event was started: {after.guild.name=} - {after.name=} - {after.start_time=}")
        elif after.status == discord.EventStatus.ended:
            new_embed = discord.Embed(
                title=after.name, description=after.description, color=discord.Colour.brand_red())
            new_embed.set_author(name="Finished Event",
                                 icon_url=after.guild.icon.url)
            await self.bot.db.update_event_status(
                msg_id=notify_msg.id, was_ended=True)
            logger.info(
                f"Event was ended: {after.guild.name=} - {after.name=} - {after.start_time=}")
        elif after.status == discord.EventStatus.cancelled:
            await self.bot.db.delete_event(notify_msg.id)
            await self.bot.db.delete_all_joined_users(after.id)
            await self.bot.db.decrement_point(after.guild.id, after.creator.id, 10)
            await notify_msg.delete()
            logger.info(
                f"Event was canceled: {after.guild.name=} - {after.name=} - {after.start_time=}")
            return
        else:
            new_embed = discord.Embed(
                title=after.name, description=after.description, color=discord.Colour.orange())
            new_embed.set_author(name="Scheduled Event",
                                 icon_url=after.guild.icon.url)
            logger.info(
                f"Event was updated: {after.guild.name=} - {after.name=} - {after.start_time=}")

        new_embed.set_thumbnail(
            url=after.cover_image.url if after.cover_image is not None else after.guild.icon.url)
        fixed_start_time = after.start_time.astimezone(tz)
        for i, field in enumerate(old_embed.fields):
            if i == 0:  # Schedule
                new_embed.add_field(
                    name=field.name, value=f"**{fixed_start_time.strftime('%Y-%m-%d %H:%M')}~**")
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

        if after.status == discord.EventStatus.ended:
            await notify_msg.edit(embeds=[new_embed, *notify_msg.embeds[1:]], view=None)
        else:
            await notify_msg.edit(embeds=[new_embed, *notify_msg.embeds[1:]])
            await self.bot.db.update_event(notify_msg.id, after.name, after.description, fixed_start_time)


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
        placeholder="通知を受け取るチャンネルを選択してください",
        cls=discord.ui.ChannelSelect,
        channel_types=[discord.ChannelType.text]
    )
    async def select_channel(self, interaction: discord.Interaction, select: discord.ui.ChannelSelect):
        self.channel = select
        await interaction.response.edit_message(
            content=f"チャンネルが選択されました。登録するにはボタンをクリックしてください。")

    @discord.ui.button(label="登録",
                       style=discord.ButtonStyle.success)
    async def register(self, interaction: discord.Interaction, button: discord.ui.Button):
        if self.channel is None:
            await interaction.response.send_message("チャンネルを選択してください。", ephemeral=True, delete_after=10)
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

                await interaction.response.edit_message(content="通知チャンネルが登録されました。", view=None, delete_after=10)
            except Exception as e:
                logger.error(
                    f"Failed to add notify channel: {interaction.guild.name=}, {e=}")
                return
        else:
            try:
                await self.bot.db.update_event_notify_channel(interaction.guild.id, self.channel.values[0].id)

                await interaction.response.edit_message(content="通知チャンネルが更新されました。", view=None, delete_after=10)
            except Exception:
                logger.error(
                    f"Failed to update notify channel: {interaction.guild.name=}")
                return


class EventAppCommands(app_commands.Group):
    def __init__(self, bot, name, description):
        super().__init__(name=name, description=description)
        self.bot = bot

    @app_commands.command(
        name="metrics",
        description="イベント履歴などのメトリクスの表示",
    )
    @app_commands.describe(scale="集計期間")
    @app_commands.choices(scale=[
        app_commands.Choice(name="Past 7 Days", value="7days"),
        app_commands.Choice(name="Past 4 Weeks", value="4weeks"),
        app_commands.Choice(name="Past 12 Months", value="12months"),
    ])
    async def metrics(self, interaction: discord.Interaction, scale: str):
        """
        日，週，月ごとのイベント開催回数の棒グラフを表示
        日の場合は過去7日間のイベント開催回数を表示
        週の場合は過去4週間のイベント開催回数を表示
        月の場合は過去12ヶ月のイベント開催回数を表示
        """
        events = await self.bot.db.get_all_events_held_on_server(interaction.guild.id)

        if not events:
            await interaction.response.send_message("このサーバではイベントが開催されていません。", ephemeral=True, delete_after=10)
            return
        if scale not in ["7days", "4weeks", "12months"]:
            await interaction.response.send_message("スケールは `7days`, `4weeks`, `12months` のいずれかを指定してください。", ephemeral=True, delete_after=10)
            return

        await interaction.response.defer()

        # 開催回数を集計(0の場合はカウント0として扱う)
        # 開催日時をタイムゾーンに合わせて変換
        counts = {}
        now = datetime.datetime.now(tz)

        for event in events:
            start_time = datetime.datetime.fromisoformat(
                event["start_time"]).astimezone(tz)

            # 開催日時をカウント
            if scale == "7days":
                key = start_time.strftime("%Y-%m-%d")
                if (now - start_time).days < 7:
                    counts[key] = counts.get(key, 0) + 1
            elif scale == "4weeks":
                key = start_time.strftime("%Y-%W")
                if (now - start_time).days < 28:
                    counts[key] = counts.get(key, 0) + 1
            elif scale == "12months":
                key = start_time.strftime("%Y-%m")
                if (now - start_time).days < 365:
                    counts[key] = counts.get(key, 0) + 1

        # 開催されていない日付を追加
        if scale == "7days":
            for i in range(6, -1, -1):
                d = (now - datetime.timedelta(days=i)).strftime("%Y-%m-%d")
                if d not in counts:
                    counts[d] = 0
        elif scale == "4weeks":
            for i in range(3, -1, -1):
                week = (now - datetime.timedelta(weeks=i))
                w = week.strftime("%Y-%W")
                if w not in counts:
                    counts[w] = 0
        elif scale == "12months":
            for i in range(11, -1, -1):
                m = (now - datetime.timedelta(days=30*i)).strftime("%Y-%m")
                if m not in counts:
                    counts[m] = 0

        # 日付をソート
        sorted_counts = dict(sorted(counts.items()))

        # カラーマップで色を生成
        cmap = plt.get_cmap("viridis")  # お好みで "viridis" や "plasma" なども可
        values = np.array(list(sorted_counts.values()))
        norm = plt.Normalize(values.min(), values.max()
                             if values.max() > 0 else 1)
        colors = cmap(norm(values))

        # 棒グラフを作成
        plt.bar(sorted_counts.keys(), sorted_counts.values(), color=colors)
        plt.xlabel("Date")
        plt.ylabel("Number of Events")
        plt.title(
            f"Number of Events Held in {interaction.guild.name} ({scale.capitalize()})")
        plt.xticks(rotation=45)
        plt.gca().yaxis.set_major_locator(ticker.MaxNLocator(integer=True))
        plt.tight_layout()

        # グラフを保存
        file_path = f"event_metrics_{interaction.guild.id}_{scale}.png"
        plt.savefig(file_path)
        plt.close()

        # グラフを画像として，embedに添付
        file = discord.File(file_path, filename="event_metrics.png")
        embed = discord.Embed(
            title=f"{interaction.guild.name}のイベントメトリクス ({scale.capitalize()})",
            description=f"過去のイベント開催回数を表示しています。",
            color=discord.Colour.blue()
        )
        embed.set_image(url="attachment://event_metrics.png")
        embed.set_footer(text=f"スケール: {scale.capitalize()}")
        embed.timestamp = datetime.datetime.now(tz)
        await interaction.followup.send(embed=embed, file=file)


class EventNotifyChannelResister(app_commands.Group):
    def __init__(self, bot, name, description):
        super().__init__(name=name, description=description)
        self.bot = bot

    @app_commands.command(
        name="resister",
        description="通知チャンネルの登録(管理者専用)",
    )
    @app_commands.checks.has_permissions(administrator=True)
    async def register(self, interaction: discord.Interaction):
        await interaction.response.send_message("チャンネルを登録するにはボタンをクリックしてください。", view=EventNotifyChannelResistrationView(self.bot), ephemeral=True)

    @register.error
    async def register_error(self, interaction: discord.Interaction, error: app_commands.AppCommandError):
        if isinstance(error, app_commands.MissingPermissions):
            await interaction.response.send_message("このコマンドを使用する権限がありません。", ephemeral=True, delete_after=10)


async def setup(bot):
    await bot.add_cog(EventNotify(bot))
    bot.tree.add_command(EventAppCommands(
        bot, name="event", description="イベントに関連するコマンド"))
    bot.tree.add_command(EventNotifyChannelResister(
        bot, name="notify", description="通知チャンネルの登録"))
