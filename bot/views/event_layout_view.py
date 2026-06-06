import logging
import pytz

import discord
from discord.ext import commands

logger = logging.getLogger("discord").getChild("event_layout_view")
tz = pytz.timezone("Asia/Tokyo")


class EventNotificationLayoutView(discord.ui.LayoutView):
    """イベント通知の埋め込みレイアウトビュー。参加/辞退/開始/キャンセルボタンを含む。"""

    def __init__(
        self,
        bot: commands.Bot,
        event: discord.ScheduledEvent,
        participant_ids: list[int] | None = None,
    ) -> None:
        """イベント情報と参加者リストからUIコンポーネントを構築する。"""
        super().__init__(timeout=None)
        self.bot = bot
        self.event = event

        if participant_ids is None:
            participant_ids = [event.creator.id]

        jst_start_time = self.event.start_time.astimezone(tz)

        thumbnail_url = (
            self.event.cover_image.url if self.event.cover_image
            else self.event.creator.avatar.url if self.event.creator.avatar
            else self.event.creator.default_avatar.url
        )
        section = discord.ui.Section(
            discord.ui.TextDisplay(content=f"🕒 **{jst_start_time.strftime('%Y-%m-%d %H:%M')}~**"),
            accessory=discord.ui.Thumbnail(thumbnail_url),
        )
        section.add_item(discord.ui.TextDisplay(content=f"## [{self.event.name}]({self.event.url})"))
        section.add_item(discord.ui.TextDisplay(
            content=f"> {self.event.description}" if self.event.description else "> 説明なし"))

        accent_color, status_label = self._resolve_status_style(self.event.status)

        container = discord.ui.Container(accent_color=accent_color)
        container.add_item(section)

        if self.event.location is not None:
            container.add_item(discord.ui.TextDisplay(content=f"📍 {self.event.location}"))
        else:
            container.add_item(discord.ui.TextDisplay(content=f"📡 <#{self.event.channel_id}>"))

        self.text_participants = discord.ui.TextDisplay(
            content="👥 " + ", ".join(f"<@{uid}>" for uid in participant_ids))
        container.add_item(self.text_participants)

        if self.event.status not in (discord.EventStatus.ended, discord.EventStatus.cancelled):
            container.add_item(self._build_action_row())

        container.add_item(discord.ui.Separator())
        container.add_item(discord.ui.TextDisplay(
            content=f"> 作成者: {self.event.creator.mention} | ステータス: {status_label}"))

        self.add_item(container)

    @staticmethod
    def _resolve_status_style(
        status: discord.EventStatus,
    ) -> tuple[discord.Colour, str]:
        """イベントステータスに対応するアクセントカラーとラベル文字列を返す。"""
        if status == discord.EventStatus.active:
            return discord.Colour.brand_green(), "開催中"
        if status == discord.EventStatus.ended:
            return discord.Colour.brand_red(), "終了"
        if status == discord.EventStatus.cancelled:
            return discord.Colour.dark_gray(), "キャンセル"
        return discord.Colour.orange(), "開催予定"

    def _build_action_row(self) -> discord.ui.ActionRow:
        """参加・辞退・開始・キャンセルの4ボタンを持つアクションローを作成する。"""
        btn_join = discord.ui.Button(
            label="✋参加", style=discord.ButtonStyle.success, custom_id="btn_join_event")
        btn_decline = discord.ui.Button(
            label="❌辞退", style=discord.ButtonStyle.red, custom_id="btn_decline_event")
        btn_start = discord.ui.Button(
            label="▶️イベントを開始", style=discord.ButtonStyle.gray, custom_id="btn_start_event")
        btn_cancel = discord.ui.Button(
            label="❌イベントをキャンセル/終了", style=discord.ButtonStyle.gray, custom_id="btn_cancel_event")

        btn_join.callback = self._on_join_pressed
        btn_decline.callback = self._on_decline_pressed
        btn_start.callback = self._on_start_pressed
        btn_cancel.callback = self._on_cancel_pressed

        row = discord.ui.ActionRow()
        row.add_item(btn_join)
        row.add_item(btn_decline)
        row.add_item(btn_start)
        row.add_item(btn_cancel)
        return row

    async def _on_join_pressed(self, itr: discord.Interaction) -> None:
        """参加ボタン押下時に参加者リストへユーザーを追加する。"""
        participant_ids = await self.bot.event_repo.get_participant_ids(self.event.id)
        if itr.user.id in participant_ids:
            await itr.response.send_message("あなたはすでに参加しています。", ephemeral=True, delete_after=10)
            return

        await self.bot.event_repo.add_participant(self.event.id, itr.user.id)
        participant_ids.append(itr.user.id)
        self.text_participants.content = "👥 " + ", ".join(f"<@{uid}>" for uid in participant_ids)
        try:
            await itr.response.edit_message(view=self)
        except discord.HTTPException as e:
            logger.error(f"Failed to update join view: {e}")

    async def _on_decline_pressed(self, itr: discord.Interaction) -> None:
        """辞退ボタン押下時に参加者リストからユーザーを削除する。"""
        participant_ids = await self.bot.event_repo.get_participant_ids(self.event.id)
        if itr.user.id not in participant_ids:
            await itr.response.send_message("あなたはこのイベントに参加していません。", ephemeral=True, delete_after=10)
            return

        await self.bot.event_repo.remove_participant(self.event.id, itr.user.id)
        participant_ids.remove(itr.user.id)
        self.text_participants.content = "👥 " + ", ".join(f"<@{uid}>" for uid in participant_ids)
        try:
            await itr.response.edit_message(view=self)
        except discord.HTTPException as e:
            logger.error(f"Failed to update decline view: {e}")

    async def _on_start_pressed(self, itr: discord.Interaction) -> None:
        """開始ボタン押下時にDiscordスケジュールイベントを開始する。"""
        if self.event.creator != itr.user:
            await itr.response.send_message("あなたはこのイベントの作成者ではありません。", ephemeral=True, delete_after=10)
            return
        if self.event.status == discord.EventStatus.scheduled:
            await self.event.start()
            await itr.response.send_message("イベントが開始されました！", ephemeral=True, delete_after=10)
        elif self.event.status in (discord.EventStatus.active, discord.EventStatus.ended):
            await itr.response.send_message("このイベントはすでにアクティブです。", ephemeral=True, delete_after=10)

    async def _on_cancel_pressed(self, itr: discord.Interaction) -> None:
        """キャンセル/終了ボタン押下時にイベントを終了またはキャンセルする。"""
        if self.event.creator != itr.user:
            await itr.response.send_message("あなたはこのイベントの作成者ではありません。", ephemeral=True, delete_after=10)
            return
        if self.event.status == discord.EventStatus.active:
            await self.event.end()
            await itr.response.send_message("イベントが正常に終了しました。", ephemeral=True, delete_after=10)
        elif self.event.status == discord.EventStatus.scheduled:
            await self.event.cancel()
            await itr.response.send_message("イベントが正常にキャンセルされました。", ephemeral=True, delete_after=10)
        elif self.event.status in (discord.EventStatus.ended, discord.EventStatus.cancelled):
            await itr.response.send_message("このイベントはすでに終了しています。", ephemeral=True, delete_after=10)
