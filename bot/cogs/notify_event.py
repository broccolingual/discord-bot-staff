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


class EventNotificationLayoutView(discord.ui.LayoutView):
    def __init__(self, bot, event: discord.ScheduledEvent):
        super().__init__(timeout=None)
        self.bot = bot
        self.event = event

        fixed_start_time = self.event.start_time.astimezone(tz)

        section = discord.ui.Section(
            discord.ui.TextDisplay(
                content=f"🕒 **{fixed_start_time.strftime('%Y-%m-%d %H:%M')}~**"),
            accessory=discord.ui.Thumbnail(
                self.event.cover_image.url if self.event.cover_image is not None else self.event.creator.avatar.url if self.event.creator.avatar else self.event.creator.default_avatar.url)
        )
        section.add_item(discord.ui.TextDisplay(
            content=f"## [{self.event.name}]({self.event.url})"))
        section.add_item(discord.ui.TextDisplay(
            content=f"> {self.event.description}" if self.event.description else f"> 説明なし"))

        if self.event.status == discord.EventStatus.active:
            accent_color = discord.Colour.brand_green()
            status_msg = "開催中"
        elif self.event.status == discord.EventStatus.ended:
            accent_color = discord.Colour.brand_red()
            status_msg = "終了"
        elif self.event.status == discord.EventStatus.cancelled:
            accent_color = discord.Colour.dark_gray()
            status_msg = "キャンセル"
        else:
            accent_color = discord.Colour.orange()
            status_msg = "開催予定"

        container = discord.ui.Container(accent_color=accent_color)
        container.add_item(section)
        if self.event.location is not None:
            container.add_item(discord.ui.TextDisplay(
                content=f"📍 {self.event.location}"))
        else:
            container.add_item(discord.ui.TextDisplay(
                content=f"📡 <#{self.event.channel_id}>"))
        self.text_participants = discord.ui.TextDisplay(
            content=f"👥 <@{self.event.creator.id}>")
        container.add_item(self.text_participants)

        if self.event.status != discord.EventStatus.ended and self.event.status != discord.EventStatus.cancelled:
            self.btn_join = discord.ui.Button(
                label="✋参加", style=discord.ButtonStyle.success, custom_id="btn_join_event")
            self.btn_decline = discord.ui.Button(
                label="❌辞退", style=discord.ButtonStyle.red, custom_id="btn_decline_event")
            self.btn_start = discord.ui.Button(
                label="▶️イベントを開始", style=discord.ButtonStyle.gray, custom_id="btn_start_event")
            self.btn_cancel = discord.ui.Button(
                label="❌イベントをキャンセル/終了", style=discord.ButtonStyle.gray, custom_id="btn_cancel_event")

            self.btn_join.callback = self._on_join_button_pressed
            self.btn_decline.callback = self._on_decline_button_pressed
            self.btn_start.callback = self._on_start_button_pressed
            self.btn_cancel.callback = self._on_cancel_button_pressed

            action_row = discord.ui.ActionRow()
            action_row.add_item(self.btn_join)
            action_row.add_item(self.btn_decline)
            action_row.add_item(self.btn_start)
            action_row.add_item(self.btn_cancel)

            container.add_item(action_row)

        container.add_item(discord.ui.Separator())
        container.add_item(discord.ui.TextDisplay(
            content=f"> 作成者: {self.event.creator.mention} | ステータス: {status_msg}"))

        self.add_item(container)

    async def _on_join_button_pressed(self, itr: discord.Interaction):
        try:
            joining_user_ids = await self.bot.db.get_joined_user_ids(self.event.id)

            if itr.user.id in joining_user_ids:
                await itr.response.send_message("あなたはすでに参加しています。", ephemeral=True, delete_after=10)
                return

            await self.bot.db.add_joined_user(self.event.id, itr.user.id)
            joining_user_ids.append(itr.user.id)
        except Exception as e:
            await itr.response.send_message("イベントの参加処理に失敗しました。", ephemeral=True, delete_after=10)
            return

        self.text_participants.content = "👥 " + \
            ", ".join([f"<@{user_id}>" for user_id in joining_user_ids])
        # Update the view to reflect changes
        await itr.response.edit_message(view=self)

    async def _on_decline_button_pressed(self, itr: discord.Interaction):
        try:
            joining_user_ids = await self.bot.db.get_joined_user_ids(self.event.id)

            if itr.user.id not in joining_user_ids:
                await itr.response.send_message("あなたはこのイベントに参加していません。", ephemeral=True, delete_after=10)
                return

            await self.bot.db.delete_joined_user(self.event.id, itr.user.id)
            joining_user_ids.remove(itr.user.id)
        except Exception as e:
            await itr.response.send_message("イベントの辞退処理に失敗しました。", ephemeral=True, delete_after=10)
            return

        self.text_participants.content = "👥 " + \
            ", ".join([f"<@{user_id}>" for user_id in joining_user_ids])
        # Update the view to reflect changes
        await itr.response.edit_message(view=self)

    async def _on_start_button_pressed(self, itr: discord.Interaction):
        if self.event.creator != itr.user:
            await itr.response.send_message("あなたはこのイベントの作成者ではありません。", ephemeral=True, delete_after=10)
            return

        if self.event.status == discord.EventStatus.scheduled:
            await self.event.start()
            await itr.response.send_message("イベントが開始されました！", ephemeral=True, delete_after=10)
        elif self.event.status == discord.EventStatus.active or self.event.status == discord.EventStatus.ended:
            await itr.response.send_message("このイベントはすでにアクティブです。", ephemeral=True, delete_after=10)

    async def _on_cancel_button_pressed(self, itr: discord.Interaction):
        if self.event.creator != itr.user:
            await itr.response.send_message("あなたはこのイベントの作成者ではありません。", ephemeral=True, delete_after=10)
            return

        if self.event.status == discord.EventStatus.active:
            await self.event.end()
            await itr.response.send_message("イベントが正常に終了しました。", ephemeral=True, delete_after=10)
        elif self.event.status == discord.EventStatus.scheduled:
            await self.event.cancel()
            await itr.response.send_message("イベントが正常にキャンセルされました。", ephemeral=True, delete_after=10)
        elif self.event.status == discord.EventStatus.ended or self.event.status == discord.EventStatus.cancelled:
            await itr.response.send_message("このイベントはすでに終了しています。", ephemeral=True, delete_after=10)

    @classmethod
    async def from_session_record(cls, bot, record: dict):
        guild_id = record.get("server_id")
        event_id = record.get("event_id")
        try:
            guild = await bot.fetch_guild(guild_id)
        except discord.NotFound:
            logger.warning(f"Guild({guild_id}) not found.")
            return None
        try:
            event = await guild.fetch_scheduled_event(event_id)
        except discord.NotFound:
            logger.warning(
                f"Event({event_id}) not found in guild({guild_id}).")
            return None
        return cls(bot, event)


async def reregister_event_views(bot):
    """
    アクティブなイベントセッションをデータベースから取得し、対応するビューを再登録します。
    これにより、Botが再起動された場合でも、イベントの通知ビューが正しく表示され、機能するようになります。
    """
    sessions = await bot.db.get_active_event_sessions(
        current_time=datetime.datetime.now(tz))
    if sessions is None:
        logger.info("No event view sessions found in the database.")
        return

    for session in sessions:
        view = await EventNotificationLayoutView.from_session_record(bot, session)
        if view is not None:
            logger.info(
                f"Recreating event view: {session['event_id']} in guild {session['server_id']}")
            bot.add_view(view)  # Recreate the view with the bot and event


class EventNotify(commands.Cog):
    def __init__(self, bot):
        self.bot = bot

    @commands.Cog.listener()
    async def on_scheduled_event_create(self, e):
        fixed_start_time = e.start_time.astimezone(tz)

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
        msg_id = await notify_chan.send(view=EventNotificationLayoutView(self.bot, e))

        await self.bot.db.add_event(msg_id.id, e.id, e.guild.id, e.creator.id, e.name, e.description, fixed_start_time, EventNotificationLayoutView.__class__.__name__, was_ended=False)
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
        await notify_msg.edit(view=EventNotificationLayoutView(self.bot, after))


class EventNotifyChannelResistrationView(discord.ui.View):
    def __init__(self, bot, timeout=60):
        super().__init__(timeout=timeout)
        self.bot = bot
        self.channel = None

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
