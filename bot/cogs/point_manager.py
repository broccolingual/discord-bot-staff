import logging
import traceback

import discord
from discord import app_commands
from discord.ext import commands

logger = logging.getLogger("discord").getChild("point_manager")


class Point(app_commands.Group):
    def __init__(self, bot, name, description):
        super().__init__(name=name, description=description)
        self.bot = bot

    @app_commands.command(
        name="earned",
        description="ユーザーの獲得したポイントの確認",
    )
    async def earned(self, interaction: discord.Interaction, user: discord.User = None):
        if user is None:
            user = interaction.user
        try:
            point = await self.bot.db.get_point(interaction.guild.id, user.id)
            await interaction.response.send_message(f"{user.mention}のポイントは`{interaction.guild.name}`で**{point}**です。", ephemeral=True, delete_after=10)
        except Exception as e:
            await interaction.response.send_message("Oops... An error occurred while fetching the points.", ephemeral=True, delete_after=10)

    @app_commands.command(
        name="ranking",
        description="サーバのポイントランキングの確認",
    )
    async def ranking(self, interaction: discord.Interaction):
        try:
            userPointsData = await self.bot.db.get_user_points_on_server(interaction.guild.id, limit=10)
            if not userPointsData:
                await interaction.response.send_message("このサーバにはポイントを獲得しているユーザがいません。", ephemeral=True, delete_after=10)
            else:
                userPoints = [[userPoint["user_id"], userPoint["point"]]
                              for userPoint in userPointsData]
                embed = discord.Embed(title=":medal: コミュニティポイントランキング",
                                      description=f"Top 10 users on `{interaction.guild.name}`",
                                      color=discord.Colour.yellow())
                rankingContents = ""
                for i, userPoint in enumerate(userPoints):
                    user_id = userPoint[0]
                    point = userPoint[1]
                    user = discord.utils.get(
                        interaction.guild.members, id=user_id)
                    user_mention = "*unknown user*"
                    if user:
                        user_mention = user.mention

                    if i == 0:
                        rankingContents += f":first_place: **{point}** ポイント - {user_mention} :tada:\n"
                    elif i == 1:
                        rankingContents += f":second_place: **{point}** ポイント - {user_mention}\n"
                    elif i == 2:
                        rankingContents += f":third_place: **{point}** ポイント - {user_mention}\n"
                    elif i == 9:
                        break
                    else:
                        rankingContents += f"`{i+1}.` **{point}** ポイント - {user_mention}\n"
                embed.add_field(
                    name="Ranking", value=rankingContents, inline=False)
                await interaction.response.send_message(embed=embed)
        except Exception as e:
            await interaction.response.send_message("Oops... An error occurred while fetching the points.", ephemeral=True, delete_after=10)
            traceback.print_exception(type(e), e, e.__traceback__)

    @app_commands.command(
        name="rules",
        description="ポイント獲得のルールの確認",
    )
    async def rules(self, interaction: discord.Interaction):
        await interaction.response.send_message("メッセージを送信したり、招待を作成したり、メッセージにリアクションしたり、スレッドを作成したり、ボイスチャンネルに参加することでポイントを獲得できます。", ephemeral=True, delete_after=10)


class PointListener(commands.Cog):
    def __init__(self, bot):
        self.bot = bot

    @commands.Cog.listener()
    async def on_message(self, message):
        if message.author.bot:
            return
        await self.bot.db.increment_point(message.guild.id, message.author.id, 2)

    @commands.Cog.listener()
    async def on_invite_create(self, invite):
        if invite.inviter.bot:
            return
        await self.bot.db.increment_point(invite.guild.id, invite.inviter.id, 5)

    @commands.Cog.listener()
    async def on_raw_reaction_add(self, payload: discord.RawReactionActionEvent):
        if payload.member is None or payload.member.bot:
            return
        guild = self.bot.get_guild(payload.guild_id)
        if guild is None:
            return
        user = guild.get_member(payload.user_id)
        if user is None or user.bot:
            return
        await self.bot.db.increment_point(payload.guild_id, payload.user_id, 1)

    @commands.Cog.listener()
    async def on_thread_create(self, thread):
        if thread.owner.bot:
            return
        await self.bot.db.increment_point(thread.guild.id, thread.owner.id, 5)

    @commands.Cog.listener()
    async def on_voice_state_update(self, member, before, after):
        if member.bot or after.channel is not None:
            return
        await self.bot.db.increment_point(member.guild.id, member.id, 5)


async def setup(bot):
    await bot.add_cog(PointListener(bot))
    bot.tree.add_command(
        Point(bot, name="point", description="コミュニティポイントに関連するコマンド"))
