import discord
from discord import app_commands
from discord.ext import commands

from utils.template import getSubcommandsEmbed
from db.interfaces import DB

class Point(app_commands.Group):
  @app_commands.command(
    name="earned",
    description="Check the points a user has earned on the server",
  )
  async def earned(self, interaction: discord.Interaction, user: discord.User = None):
      if user is None:
          user = interaction.author
      point = await PointManager.getPoint(interaction.guild.id, user.id)
      await interaction.response.send_message(f"{user.mention}'s points on `{interaction.guild.name}` are **{point}**.")
      
  @app_commands.command(
    name="ranking",
    description="Ranking of the points earned by users on the server",
  )
  async def ranking(self, interaction: discord.Interaction):
      userPoints = await PointManager.getUserPointsOnServer(interaction.guild.id, limit=10)
      # print(userPoints)
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
          user = await self.bot.fetch_user(user_id)
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
    db = DB()
    if db.getPoint(server_id, user_id) is None:
      db.initPoint(server_id, user_id)
    db.updatePoint(server_id, user_id, point)
    # print(f"Added {point} points to {server_id} on {user_id}")
  
  @staticmethod
  async def removePoint(server_id, user_id: int, point: int):
    db = DB()
    if db.getPoint(server_id, user_id) is None:
      db.initPoint(server_id, user_id)
    db.removePoint(server_id, user_id, point)
    # print(f"Removed {point} points to {server_id} on {user_id}")
  
  @staticmethod
  async def getPoint(server_id, user_id: int):
    db = DB()
    if db.getPoint(server_id, user_id) is None:
      db.initPoint(server_id, user_id)
    point = db.getPoint(server_id, user_id)
    return point.point
  
  @staticmethod
  async def getUserPointsOnServer(server_id, limit=10):
    db = DB()
    userPoints = db.getUserPointsOnServer(server_id, limit=limit)
    if userPoints is None:
      return None
    return [[userPoint.user_id, userPoint.point] for userPoint in userPoints]

async def setup(bot):
  await bot.add_cog(PointListener(bot))
  bot.tree.add_command(Point(name="point", description="Commands related to community points."))
