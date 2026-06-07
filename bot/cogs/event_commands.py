import datetime
import logging
import pytz

import discord
from discord import app_commands
from discord.ext import commands
from matplotlib import pyplot as plt
import matplotlib.ticker as ticker
import numpy as np

logger = logging.getLogger("discord").getChild("event_commands")
tz = pytz.timezone("Asia/Tokyo")


class EventNotifyChannelRegisterView(discord.ui.View):
    """通知チャンネルを選択・登録するUIビュー。"""

    def __init__(self, bot: commands.Bot, timeout: int = 60) -> None:
        """UIコンポーネントとボット参照を初期化する。"""
        super().__init__(timeout=timeout)
        self.bot = bot
        self.channel: discord.ui.ChannelSelect | None = None

    @discord.ui.select(
        placeholder="通知を受け取るチャンネルを選択してください",
        cls=discord.ui.ChannelSelect,
        channel_types=[discord.ChannelType.text],
    )
    async def select_channel(
        self,
        interaction: discord.Interaction,
        select: discord.ui.ChannelSelect,
    ) -> None:
        """チャンネルセレクト変更時に選択値を保持する。"""
        self.channel = select
        await interaction.response.edit_message(
            content="チャンネルが選択されました。登録するにはボタンをクリックしてください。")

    @discord.ui.button(label="登録", style=discord.ButtonStyle.success)
    async def register(
        self,
        interaction: discord.Interaction,
        button: discord.ui.Button,
    ) -> None:
        """登録ボタン押下時に通知チャンネルを保存または更新する。"""
        if self.channel is None:
            await interaction.response.send_message(
                "チャンネルを選択してください。", ephemeral=True, delete_after=10)
            return

        channel_id = self.channel.values[0].id
        existing = await self.bot.event_repo.get_notify_channel(interaction.guild.id)
        if existing is None:
            await self.bot.event_repo.add_notify_channel(interaction.guild.id, channel_id)
            await interaction.response.edit_message(
                content="通知チャンネルが登録されました。", view=None, delete_after=10)
        else:
            await self.bot.event_repo.update_notify_channel(interaction.guild.id, channel_id)
            await interaction.response.edit_message(
                content="通知チャンネルが更新されました。", view=None, delete_after=10)


class EventNotifyChannelCommands(app_commands.Group):
    """通知チャンネルの登録・変更コマンドグループ。"""

    def __init__(self, bot: commands.Bot, name: str, description: str) -> None:
        """コマンドグループとボット参照を初期化する。"""
        super().__init__(name=name, description=description)
        self.bot = bot

    @app_commands.command(name="resister", description="通知チャンネルの登録(管理者専用)")
    @app_commands.checks.has_permissions(administrator=True)
    async def register(self, interaction: discord.Interaction) -> None:
        """通知チャンネルを登録または変更するUIを表示する。"""
        await interaction.response.send_message(
            "チャンネルを登録するにはボタンをクリックしてください。",
            view=EventNotifyChannelRegisterView(self.bot),
            ephemeral=True)

    @register.error
    async def register_error(
        self,
        interaction: discord.Interaction,
        error: app_commands.AppCommandError,
    ) -> None:
        """権限不足エラーを処理する。"""
        if isinstance(error, app_commands.MissingPermissions):
            await interaction.response.send_message(
                "このコマンドを使用する権限がありません。", ephemeral=True, delete_after=10)


class EventMetricsCommands(app_commands.Group):
    """イベントメトリクス表示のコマンドグループ。"""

    def __init__(self, bot: commands.Bot, name: str, description: str) -> None:
        """コマンドグループとボット参照を初期化する。"""
        super().__init__(name=name, description=description)
        self.bot = bot

    @app_commands.command(name="metrics", description="イベント履歴などのメトリクスの表示")
    @app_commands.describe(scale="集計期間")
    @app_commands.choices(scale=[
        app_commands.Choice(name="Past 7 Days", value="7days"),
        app_commands.Choice(name="Past 4 Weeks", value="4weeks"),
        app_commands.Choice(name="Past 12 Months", value="12months"),
    ])
    async def metrics(self, interaction: discord.Interaction, scale: str) -> None:
        """指定期間のイベント開催数の棒グラフを生成して送信する。"""
        events = await self.bot.event_repo.get_all_events_held_on_server(interaction.guild.id)
        if not events:
            await interaction.response.send_message(
                "このサーバではイベントが開催されていません。", ephemeral=True, delete_after=10)
            return

        await interaction.response.defer()

        counts: dict[str, int] = {}
        now = datetime.datetime.now(tz)

        for event in events:
            start_time = event.start_time.astimezone(tz)
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

        if scale == "7days":
            for i in range(6, -1, -1):
                counts.setdefault((now - datetime.timedelta(days=i)).strftime("%Y-%m-%d"), 0)
        elif scale == "4weeks":
            for i in range(3, -1, -1):
                counts.setdefault((now - datetime.timedelta(weeks=i)).strftime("%Y-%W"), 0)
        elif scale == "12months":
            for i in range(11, -1, -1):
                counts.setdefault((now - datetime.timedelta(days=30 * i)).strftime("%Y-%m"), 0)

        sorted_counts = dict(sorted(counts.items()))
        values = np.array(list(sorted_counts.values()))
        norm = plt.Normalize(values.min(), values.max() if values.max() > 0 else 1)
        colors = plt.get_cmap("viridis")(norm(values))

        plt.bar(sorted_counts.keys(), sorted_counts.values(), color=colors)
        plt.xlabel("Date")
        plt.ylabel("Number of Events")
        plt.xticks(rotation=45)
        plt.gca().yaxis.set_major_locator(ticker.MaxNLocator(integer=True))
        plt.tight_layout()

        chart_path = f"event_metrics_{interaction.guild.id}_{scale}.png"
        plt.savefig(chart_path)
        plt.close()

        file = discord.File(chart_path, filename="event_metrics.png")
        embed = discord.Embed(
            title=f"{interaction.guild.name}のイベントメトリクス ({scale.capitalize()})",
            description="過去のイベント開催回数を表示しています。",
            color=discord.Colour.blue(),
        )
        embed.set_image(url="attachment://event_metrics.png")
        embed.set_footer(text=f"スケール: {scale.capitalize()}")
        embed.timestamp = datetime.datetime.now(tz)
        await interaction.followup.send(embed=embed, file=file)


async def setup(bot: commands.Bot) -> None:
    """イベントコマンドグループをボットのコマンドツリーに登録する。"""
    bot.tree.add_command(EventMetricsCommands(bot, name="event", description="イベントに関連するコマンド"))
    bot.tree.add_command(EventNotifyChannelCommands(bot, name="notify", description="通知チャンネルの登録"))
