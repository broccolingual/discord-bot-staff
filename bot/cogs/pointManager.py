import logging

import discord
from discord import app_commands
from discord.ext import commands

from db.interfaces import DB as db

logger = logging.getLogger("bot").getChild("pointManager")

class Point(app_commands.Group):
  @app_commands.command(
    name="earned",
    description="Check the points a user has earned on the server",
  )
  async def earned(self, interaction: discord.Interaction, user: discord.User = None):
      logger.info(f"command: 'point earned' executed by {interaction.user.name}")
      if user is None:
          user = interaction.user
      point = await PointManager.getPoint(interaction.guild.id, user.id)
      await interaction.response.send_message(f"{user.mention}'s points on `{interaction.guild.name}` are **{point}**.")
      
  @app_commands.command(
    name="ranking",
    description="Ranking of the points earned by users on the server",
  )
  async def ranking(self, interaction: discord.Interaction):
      logger.info(f"command: 'point ranking' executed by {interaction.user.name}")
      userPoints = await PointManager.getUserPointsOnServer(interaction.guild.id, limit=10)
      if userPoints is None:
          await interaction.response.send_message("No user has earned points on this server.")
          return
      embed = discord.Embed(title=":medal: Community Point Ranking",
                            description=f"Top 10 users on `{interaction.guild.name}`",
                            color=discord.Colour.yellow())
      rankingContents = ""
      for i, userPoint in enumerate(userPoints):
          user_id = userPoint[0]
          point = userPoint[1]
          user = discord.utils.get(interaction.guild.members, id=user_id)
          if i == 0:
            rankingContents += f":first_place: **{point}** points - {user.mention} :tada:\n"
          elif i == 1:
            rankingContents += f":second_place: **{point}** points - {user.mention}\n"
          elif i == 2:
            rankingContents += f":third_place: **{point}** points - {user.mention}\n"
          elif i == 9:
              break
          else:
              rankingContents += f"`{i+1}.` **{point}** points - {user.mention}\n"
      embed.add_field(name="Ranking", value=rankingContents, inline=False)
      await interaction.response.send_message(embed=embed)
  
  @app_commands.command(
    name="rules",
    description="Check the rules for earning points",
  )
  async def rules(self, interaction: discord.Interaction):
      logger.info(f"command: 'point rules' executed by {interaction.user.name}")
      await interaction.response.send_message("You can earn points by sending messages, creating invites, reacting to messages, creating threads, and joining voice channels.")
  

class PointListener(commands.Cog):
  def __init__ (self, bot):
    self.bot = bot
  
  @commands.Cog.listener()
  async def on_message(self, message):
    if message.author.bot:
      return
    await PointManager.addPoint(message.guild.id, message.author.id, 2)
  
  @commands.Cog.listener()
  async def on_invite_create(self, invite):
    if invite.inviter.bot:
      return
    await PointManager.addPoint(invite.guild.id, invite.inviter.id, 5)
    
  @commands.Cog.listener()
  async def on_raw_reaction_add(self, reaction, user):
    if user.bot:
      return
    await PointManager.addPoint(reaction.message.guild.id, user.id, 1)
  
  @commands.Cog.listener()
  async def on_thread_create(self, thread):
    if thread.owner.bot:
      return
    await PointManager.addPoint(thread.guild.id, thread.owner.id, 5)
  
  @commands.Cog.listener()
  async def on_voice_state_update(self, member, before, after):
    if member.bot or after.channel is not None:
      return
    await PointManager.addPoint(member.guild.id, member.id, 5)

class PointManager():
  @staticmethod
  async def addPoint(server_id, user_id: int, point: int):
    if await db.getPoint(server_id, user_id) is None:
      await db.initPoint(server_id, user_id)
    await db.updatePoint(server_id, user_id, point)
  
  @staticmethod
  async def removePoint(server_id, user_id: int, point: int):
    if await db.getPoint(server_id, user_id) is None:
      await db.initPoint(server_id, user_id)
    await db.removePoint(server_id, user_id, point)
  
  @staticmethod
  async def getPoint(server_id, user_id: int):
    if await db.getPoint(server_id, user_id) is None:
      await db.initPoint(server_id, user_id)
    point = await db.getPoint(server_id, user_id)
    return point.point
  
  @staticmethod
  async def getUserPointsOnServer(server_id, limit=10):
    userPoints = await db.getUserPointsOnServer(server_id, limit=limit)
    if userPoints is None:
      return None
    return [[userPoint.user_id, userPoint.point] for userPoint in userPoints]

async def setup(bot):
  await bot.add_cog(PointListener(bot))
  bot.tree.add_command(Point(name="point", description="Commands related to community points."))
