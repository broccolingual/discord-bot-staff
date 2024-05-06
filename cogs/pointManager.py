import discord
from discord.ext import commands

from utils.template import getSubcommandsEmbed
from db.interfaces import DB

class PointManager(commands.Cog):
  def __init__ (self, bot):
    self.bot = bot
    
  @commands.group()
  async def point(self, ctx):
      if ctx.invoked_subcommand is None:
          await ctx.reply(f"{ctx.author.mention}Subcommand is required.", embed=getSubcommandsEmbed(ctx.command))
          
  @point.command(
    description="Check the points a user has earned on the server",
  )
  async def earned(self, ctx, user: discord.User = None):
      if user is None:
          user = ctx.author
      point = await self.getPoint(ctx.guild.id, user.id)
      await ctx.reply(f"{user.mention}'s points on `{ctx.guild.name}` are **{point}**.")
      
  @point.command(
    description="Ranking of the points earned by users on the server",
  )
  async def ranking(self, ctx):
      userPoints = await self.getUserPointsOnServer(ctx.guild.id)
      if userPoints is None:
          await ctx.reply("No user has earned points on this server.")
          return
      userPoints = sorted(userPoints, key=lambda x: list(x.values())[0], reverse=True)
      embed = discord.Embed(title="Ranking of the points earned by users on the server",
                            description=f"Top 10 users on `{ctx.guild.name}`",
                            color=discord.Colour.yellow())
      rankingContents = ""
      for i, userPoint in enumerate(userPoints):
          user_id = list(userPoint.keys())[0]
          point = list(userPoint.values())[0]
          user = await self.bot.fetch_user(user_id)
          if i == 0:
            rankingContents += f"`{i+1}.` {user.mention} - **{point}** points  :tada: :tada: :tada: \n"
          elif i == 9:
              break
          else:
              rankingContents += f"`{i+1}.` {user.mention} - {point} points\n"
      embed.add_field(name="Ranking", value=rankingContents, inline=False)
      await ctx.reply(embed=embed)
  
  @point.command(
    description="Check the rules for earning points",
  )
  async def rules(self, ctx):
      await ctx.reply("You can earn points by sending messages, creating invites, reacting to messages, creating threads, and joining voice channels.")
  
  @commands.Cog.listener()
  async def on_message(self, message):
    if message.author.bot:
      return
    await self.addPoint(message.guild.id, message.author.id, 2)
  
  @commands.Cog.listener()
  async def on_invite_create(self, invite):
    if invite.inviter.bot:
      return
    await self.addPoint(invite.guild.id, invite.inviter.id, 5)
    
  @commands.Cog.listener()
  async def on_raw_reaction_add(self, reaction, user):
    if user.bot:
      return
    await self.addPoint(reaction.message.guild.id, user.id, 1)
  
  @commands.Cog.listener()
  async def on_thread_create(self, thread):
    if thread.owner.bot:
      return
    await self.addPoint(thread.guild.id, thread.owner.id, 5)
  
  @commands.Cog.listener()
  async def on_voice_state_update(self, member, before, after):
    if member.bot or after.channel is not None:
      return
    await self.addPoint(member.guild.id, member.id, 5)
  
  @staticmethod
  async def addPoint(server_id, user_id: int, point: int):
    db = DB()
    if db.getPoint(server_id, user_id) is None:
      db.initPoint(server_id, user_id)
    db.updatePoint(server_id, user_id, point)
    print(f"Added {point} points to {server_id} on {user_id}")
  
  @staticmethod
  async def removePoint(server_id, user_id: int, point: int):
    db = DB()
    if db.getPoint(server_id, user_id) is None:
      db.initPoint(server_id, user_id)
    db.removePoint(server_id, user_id, point)
    print(f"Removed {point} points to {server_id} on {user_id}")
  
  @staticmethod
  async def getPoint(server_id, user_id: int):
    db = DB()
    if db.getPoint(server_id, user_id) is None:
      db.initPoint(server_id, user_id)
    point = db.getPoint(server_id, user_id)
    return point.point
  
  @staticmethod
  async def getUserPointsOnServer(server_id):
    db = DB()
    userPoints = db.getUserPointsOnServer(server_id)
    if userPoints is None:
      return None
    return [{userPoint.user_id: userPoint.point} for userPoint in userPoints]

async def setup(bot):
  await bot.add_cog(PointManager(bot))
