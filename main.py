import asyncio
import logging
import os
from pathlib import Path

import discord
from discord.ext import commands, tasks

from helpCommand import MyHelpCommand
import settings

logger = logging.getLogger(__name__)
logger.setLevel(logging.INFO)

# StreamHandler作成
handler = logging.StreamHandler()
handler.setFormatter(logging.Formatter('%(asctime)s:%(name)s:%(lineno)d:%(levelname)s:%(message)s'))
logger.addHandler(handler)

class StaffBot(commands.Bot):
    def __init__(self):
        super().__init__(
            command_prefix="^",
            intents=discord.Intents.all(),
            help_command=MyHelpCommand(),
            case_insensitive=True,
            activity=discord.Game(name="^help"),
        )
        
    async def setup_hook(self):
        # load extensions
        for filename in os.listdir("./cogs"):
            if filename.endswith(".py") and not filename.startswith("_"):
                await self.load_extension(f"cogs.{filename[:-3]}")
        await self.tree.sync()

    async def on_ready(self):
        logger.info(f'Bot ready, Logged in as {self.user.name}.')
        
    async def on_connect():
        logger.info(f'Bot connected. (discord.py: v{discord.__version__})')

    async def on_disconnect():
        logger.warning('Bot disconnected.')
        
    async def on_resumed():
        logger.info(f'Bot session resumed.')

    # async def on_command_error(ctx, error):
    #     if isinstance(error, commands.MissingRequiredArgument):
    #         return

    #     if isinstance(error, commands.BadArgument):
    #         return

    #     if isinstance(error, commands.CommandNotFound):
    #         return

    #     if isinstance(error, commands.CommandInvokeError):
    #         return

    #     if isinstance(error, commands.TooManyArguments):
    #         return

    #     if isinstance(error, commands.NotOwner):
    #         return

    #     if isinstance(error, commands.MissingPermissions):
    #         return

bot = StaffBot()

@bot.command()
async def ping(ctx):
    await ctx.reply(f"Pong! ({round(bot.latency * 1000)}ms)")

async def run():
    async with bot:
        await bot.login(settings.TOKEN)
        await bot.connect()

if __name__ == "__main__":
    try:
        asyncio.run(run())
    except KeyboardInterrupt:
        logger.info('Bot interrupted.')
