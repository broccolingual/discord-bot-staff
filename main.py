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

bot = commands.Bot(
    command_prefix="^",
    intents=discord.Intents.all(),
    help_command=MyHelpCommand(),
    case_insensitive=True,
    activity=discord.Game(name="^help"),
)

@bot.event
async def on_connect():
    logger.info(f'Bot connected. (discord.py: v{discord.__version__})')


@bot.event
async def on_disconnect():
    logger.warning('Bot disconnected.')


@bot.event
async def on_ready():
    logger.info(f'Bot ready, Logged in as {bot.user.name}.')


@bot.event
async def on_resumed():
    logger.info(f'Bot session resumed.')


# @bot.event
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

@bot.command()
async def ping(ctx):
    await ctx.reply(f"Pong! ({round(bot.latency * 1000)}ms)")

async def load_extensions():
    for filename in os.listdir("./cogs"):
        if filename.endswith(".py") and not filename.startswith("_"):
            await bot.load_extension(f"cogs.{filename[:-3]}")

async def run():
    async with bot:
        await load_extensions()
        await bot.login(settings.TOKEN)
        await bot.connect()

if __name__ == "__main__":
    try:
        asyncio.run(run())
    except KeyboardInterrupt:
        logger.info('Bot interrupted.')
