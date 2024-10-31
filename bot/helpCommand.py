from typing import Mapping, Optional

from discord.ext import commands
import discord

class MyHelpCommand(commands.HelpCommand):
  def __init__(self):
    super().__init__(
      show_hidden=False,
      command_attrs={"brief": "Shows help about the bot, a command, or a category", "aliases": ["h"]}
    )
    
  async def send_bot_help(self, mapping: Mapping[Optional[commands.Cog], list[commands.Command]]) -> None:
    embed = discord.Embed(title="Help", description="List of all commands", color=discord.Colour.blurple())
    for cog, commands in mapping.items():
      if cog is None:
        continue
      embed.add_field(name=cog.qualified_name, value="\n".join([f"`{command.name}`" for command in commands]), inline=False)
    await self.get_destination().send(embed=embed)
