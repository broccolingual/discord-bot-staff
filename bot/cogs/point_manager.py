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
        description="Check the points a user has earned on the server",
    )
    async def earned(self, interaction: discord.Interaction, user: discord.User = None):
        if user is None:
            user = interaction.user
        try:
            point = await PointManager.getPoint(self.bot, interaction.guild.id, user.id)
            await interaction.response.send_message(f"{user.mention}'s points on `{interaction.guild.name}` are **{point}**.")
        except Exception as e:
            await interaction.response.send_message("Oops... An error occurred while fetching the points.", ephemeral=True, delete_after=10)

    @app_commands.command(
        name="ranking",
        description="Ranking of the points earned by users on the server",
    )
    async def ranking(self, interaction: discord.Interaction):
        try:
            userPoints = await PointManager.getUserPointsOnServer(self.bot, interaction.guild.id, limit=10)
            if not userPoints:
                await interaction.response.send_message("No user has earned points on this server.", ephemeral=True, delete_after=10)
            else:
                embed = discord.Embed(title=":medal: Community Point Ranking",
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
                        rankingContents += f":first_place: **{point}** points - {user_mention} :tada:\n"
                    elif i == 1:
                        rankingContents += f":second_place: **{point}** points - {user_mention}\n"
                    elif i == 2:
                        rankingContents += f":third_place: **{point}** points - {user_mention}\n"
                    elif i == 9:
                        break
                    else:
                        rankingContents += f"`{i+1}.` **{point}** points - {user_mention}\n"
                embed.add_field(
                    name="Ranking", value=rankingContents, inline=False)
                await interaction.response.send_message(embed=embed)
        except Exception as e:
            await interaction.response.send_message("Oops... An error occurred while fetching the points.", ephemeral=True, delete_after=10)
            traceback.print_exception(type(e), e, e.__traceback__)

    @app_commands.command(
        name="rules",
        description="Check the rules for earning points",
    )
    async def rules(self, interaction: discord.Interaction):
        await interaction.response.send_message("You can earn points by sending messages, creating invites, reacting to messages, creating threads, and joining voice channels.")


class PointListener(commands.Cog):
    def __init__(self, bot):
        self.bot = bot

    @commands.Cog.listener()
    async def on_message(self, message):
        if message.author.bot:
            return
        await PointManager.addPoint(self.bot, message.guild.id, message.author.id, 2)

    @commands.Cog.listener()
    async def on_invite_create(self, invite):
        if invite.inviter.bot:
            return
        await PointManager.addPoint(self.bot, invite.guild.id, invite.inviter.id, 5)

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
        await PointManager.addPoint(self.bot, payload.guild_id, payload.user_id, 1)

    @commands.Cog.listener()
    async def on_thread_create(self, thread):
        if thread.owner.bot:
            return
        await PointManager.addPoint(thread.guild.id, thread.owner.id, 5)

    @commands.Cog.listener()
    async def on_voice_state_update(self, member, before, after):
        if member.bot or after.channel is not None:
            return
        await PointManager.addPoint(self.bot, member.guild.id, member.id, 5)


class PointManager():
    @staticmethod
    async def addPoint(bot, server_id, user_id: int, point: int):
        current_points = await bot.db.get_earned_point(server_id, user_id)
        if current_points is None:
            await bot.db.init_earned_point(server_id, user_id)
        await bot.db.update_earned_point(server_id, user_id, current_points["point"] + point)

    @staticmethod
    async def removePoint(bot, server_id, user_id: int, point: int):
        current_points = await bot.db.get_earned_point(server_id, user_id)
        if current_points is None:
            await bot.db.init_earned_point(server_id, user_id)
        if current_points["point"] - point < 0:
            point = 0
        else:
            point = current_points["point"] - point
        await bot.db.remove_earned_point(server_id, user_id, point)

    @staticmethod
    async def getPoint(bot, server_id, user_id: int):
        if await bot.db.get_earned_point(server_id, user_id) is None:
            await bot.db.init_earned_point(server_id, user_id)
        point = await bot.db.get_earned_point(server_id, user_id)
        return point["point"]

    @staticmethod
    async def getUserPointsOnServer(bot, server_id, limit=10):
        user_points = await bot.db.get_user_earned_points_on_server(server_id, limit=limit)
        if user_points is None:
            return None
        return [[user_point["user_id"], user_point["point"]] for user_point in user_points]


async def setup(bot):
    await bot.add_cog(PointListener(bot))
    bot.tree.add_command(
        Point(bot, name="point", description="Commands related to community points."))
