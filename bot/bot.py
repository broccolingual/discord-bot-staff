import datetime
import logging
import os
import pytz

import discord
from discord.ext import commands, tasks

import settings
from supabase_db.interfaces import SupabaseDB
from repositories.event_repository import EventRepository
from repositories.point_repository import PointRepository
from cogs.notify_event import reregister_event_views

logger = logging.getLogger("discord")
if logger.hasHandlers():
    logger.handlers.clear()
logger.setLevel(logging.DEBUG)
handler = logging.StreamHandler()
handler.setFormatter(logging.Formatter(
    "%(asctime)s:%(name)s:%(lineno)d:%(levelname)s:%(message)s"))
logger.addHandler(handler)

tz = pytz.timezone("Asia/Tokyo")


class StaffBot(commands.Bot):
    """スタッフ向け Discord Bot の本体クラス。"""

    def __init__(self) -> None:
        """Bot の基本設定とリポジトリの参照を初期化する。"""
        super().__init__(
            command_prefix="/",
            intents=discord.Intents.all(),
            case_insensitive=True,
            activity=discord.Game(name="/help"),
        )
        self.db = SupabaseDB()
        self.event_repo: EventRepository | None = None
        self.point_repo: PointRepository | None = None

    async def setup_hook(self) -> None:
        """Cog の読み込み・コマンド同期・DB 接続・ビュー再登録を行う。"""
        for filename in os.listdir("./cogs"):
            if filename.endswith(".py") and not filename.startswith("_"):
                await self.load_extension(f"cogs.{filename[:-3]}")
        synced = await self.tree.sync()
        logger.info(f"Synced {len(synced)} commands")

        await self.db.get_client()
        self.event_repo = EventRepository(self.db)
        self.point_repo = PointRepository(self.db)
        await reregister_event_views(self)

    async def on_ready(self) -> None:
        """Bot の準備完了時に定期タスクを開始する。"""
        logger.info(f"Bot ready, Logged in as {self.user.name}.")
        self.check_and_start_events.start()

    async def on_connect(self) -> None:
        """Discord へ接続した際にログを出力する。"""
        logger.info(f"Bot connected. (discord.py: v{discord.__version__})")

    async def on_disconnect(self) -> None:
        """Discord から切断された際にログを出力する。"""
        logger.warning("Bot disconnected.")

    async def on_resumed(self) -> None:
        """セッション再開時にログを出力する。"""
        logger.warning("Bot session resumed.")

    @tasks.loop(minutes=1)
    async def check_and_start_events(self) -> None:
        """開始時刻を過ぎた未開始イベントを検出し、自動で開始または完了済みとしてマークする。"""
        logger.info("Checking for overdue events...")
        overdue = await self.event_repo.get_overdue_events(
            current_time=datetime.datetime.now(tz))

        for event_info in overdue:
            try:
                guild = await self.fetch_guild(event_info.server_id)
            except discord.NotFound:
                await self.event_repo.update_event_status(
                    msg_id=event_info.msg_id, was_ended=True)
                logger.warning(f"Guild not found: guild_id={event_info.server_id}")
                continue

            try:
                event = await guild.fetch_scheduled_event(event_info.event_id)
            except discord.NotFound:
                await self.event_repo.update_event_status(
                    msg_id=event_info.msg_id, was_ended=True)
                logger.warning(
                    f"Event not found: event_id={event_info.event_id}, guild={guild.name}")
                continue

            if event.status == discord.EventStatus.completed:
                await self.event_repo.update_event_status(
                    msg_id=event_info.msg_id, was_ended=True)
            elif event.status == discord.EventStatus.scheduled:
                await event.start()


bot = StaffBot()


@bot.tree.command(name="ping", description="Check if the bot is alive")
async def ping(interaction: discord.Interaction) -> None:
    """Bot の応答速度をミリ秒で返す。"""
    await interaction.response.send_message(
        f"Pong! ({round(bot.latency * 1000)}ms)", ephemeral=True)


@bot.tree.command(name="help", description="Shows help about the bot, a command, or a category")
async def help_command(interaction: discord.Interaction) -> None:
    """登録されている全コマンドの一覧を表示する。"""
    embed = discord.Embed(
        title="Help", description="List of all commands", color=discord.Colour.blurple())
    for command in bot.tree.walk_commands():
        if command is None:
            continue
        if command is not discord.app_commands.Group:
            embed.add_field(name=command.name, value=command.description, inline=False)
        else:
            embed.add_field(
                name=command.name,
                value="\n".join(
                    f"`{sub.name}`: {sub.description}" for sub in command.children),
                inline=False,
            )
    await interaction.response.send_message(embed=embed, ephemeral=True)


if __name__ == "__main__":
    bot.run(settings.TOKEN, reconnect=True, log_handler=handler, log_level=logging.INFO)
