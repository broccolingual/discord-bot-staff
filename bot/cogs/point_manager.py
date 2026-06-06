import logging

import discord
from discord import app_commands
from discord.ext import commands

logger = logging.getLogger("discord").getChild("point_manager")

ON_MESSAGE_POINT = 2
ON_INVITE_CREATE_POINT = 5
ON_REACTION_ADD_POINT = 1
ON_THREAD_CREATE_POINT = 3
ON_VOICE_LEAVE_POINT = 3


class PointCommands(app_commands.Group):
    """コミュニティポイントの確認・ランキング表示コマンドグループ。"""

    def __init__(self, bot: commands.Bot, name: str, description: str) -> None:
        """コマンドグループとボット参照を初期化する。"""
        super().__init__(name=name, description=description)
        self.bot = bot

    @app_commands.command(name="earned", description="ユーザーの獲得したポイントの確認")
    async def earned(
        self,
        interaction: discord.Interaction,
        user: discord.User | None = None,
    ) -> None:
        """指定ユーザー（省略時は自分）の現在ポイントを表示する。"""
        target = user or interaction.user
        point = await self.bot.point_repo.get_point(interaction.guild.id, target.id)
        await interaction.response.send_message(
            f"{target.mention}のポイントは`{interaction.guild.name}`で**{point}**です。",
            ephemeral=True, delete_after=10)

    @app_commands.command(name="ranking", description="サーバのポイントランキングの確認")
    async def ranking(self, interaction: discord.Interaction) -> None:
        """サーバーのポイントランキング上位10件を表示する。"""
        leaderboard = await self.bot.point_repo.get_leaderboard(interaction.guild.id, limit=10)
        if not leaderboard:
            await interaction.response.send_message(
                "このサーバにはポイントを獲得しているユーザがいません。", ephemeral=True, delete_after=10)
            return

        embed = discord.Embed(
            title=":medal: コミュニティポイントランキング",
            description=f"Top 10 users on `{interaction.guild.name}`",
            color=discord.Colour.yellow(),
        )
        lines = ""
        for i, entry in enumerate(leaderboard):
            member = discord.utils.get(interaction.guild.members, id=entry.user_id)
            mention = member.mention if member else "*unknown user*"
            if i == 0:
                lines += f":first_place: **{entry.point}** ポイント - {mention} :tada:\n"
            elif i == 1:
                lines += f":second_place: **{entry.point}** ポイント - {mention}\n"
            elif i == 2:
                lines += f":third_place: **{entry.point}** ポイント - {mention}\n"
            else:
                lines += f"`{i + 1}.` **{entry.point}** ポイント - {mention}\n"

        embed.add_field(name="Ranking", value=lines, inline=False)
        await interaction.response.send_message(embed=embed)

    @app_commands.command(name="rules", description="ポイント獲得のルールの確認")
    async def rules(self, interaction: discord.Interaction) -> None:
        """ポイント獲得条件の一覧を表示する。"""
        await interaction.response.send_message(
            "メッセージを送信したり、招待を作成したり、メッセージにリアクションしたり、"
            "スレッドを作成したり、ボイスチャンネルに参加することでポイントを獲得できます。",
            ephemeral=True, delete_after=10)


class PointListener(commands.Cog):
    """各種 Discord イベントを監視してポイントを付与する Cog。"""

    def __init__(self, bot: commands.Bot) -> None:
        """Cog とボット参照を初期化する。"""
        self.bot = bot

    @commands.Cog.listener()
    async def on_message(self, message: discord.Message) -> None:
        """メッセージ送信時にポイントを付与する。"""
        if message.author.bot:
            return
        await self.bot.point_repo.increment_point(
            message.guild.id, message.author.id, ON_MESSAGE_POINT)

    @commands.Cog.listener()
    async def on_invite_create(self, invite: discord.Invite) -> None:
        """招待作成時にポイントを付与する。"""
        if invite.inviter.bot:
            return
        await self.bot.point_repo.increment_point(
            invite.guild.id, invite.inviter.id, ON_INVITE_CREATE_POINT)

    @commands.Cog.listener()
    async def on_raw_reaction_add(self, payload: discord.RawReactionActionEvent) -> None:
        """リアクション追加時にポイントを付与する。"""
        if payload.member is None or payload.member.bot:
            return
        guild = self.bot.get_guild(payload.guild_id)
        if guild is None:
            return
        member = guild.get_member(payload.user_id)
        if member is None or member.bot:
            return
        await self.bot.point_repo.increment_point(
            payload.guild_id, payload.user_id, ON_REACTION_ADD_POINT)

    @commands.Cog.listener()
    async def on_thread_create(self, thread: discord.Thread) -> None:
        """スレッド作成時にポイントを付与する。"""
        if thread.owner.bot:
            return
        await self.bot.point_repo.increment_point(
            thread.guild.id, thread.owner.id, ON_THREAD_CREATE_POINT)

    @commands.Cog.listener()
    async def on_voice_state_update(
        self,
        member: discord.Member,
        _before: discord.VoiceState,
        after: discord.VoiceState,
    ) -> None:
        """ボイスチャンネル退出時にポイントを付与する。"""
        if member.bot or after.channel is not None:
            return
        await self.bot.point_repo.increment_point(
            member.guild.id, member.id, ON_VOICE_LEAVE_POINT)


async def setup(bot: commands.Bot) -> None:
    """PointListener Cog とポイントコマンドグループをボットに登録する。"""
    await bot.add_cog(PointListener(bot))
    bot.tree.add_command(
        PointCommands(bot, name="point", description="コミュニティポイントに関連するコマンド"))
