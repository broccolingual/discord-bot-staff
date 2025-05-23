import logging
import os

from aiohttp import web
import discord
from discord import app_commands
from discord.ext import commands, tasks

import settings

# Set up logging
logger = logging.getLogger("discord")
if logger.hasHandlers():
    logger.handlers.clear()
logger.setLevel(logging.DEBUG)
handler = logging.StreamHandler()
handler.setFormatter(logging.Formatter(
    '%(asctime)s:%(name)s:%(lineno)d:%(levelname)s:%(message)s'))
logger.addHandler(handler)


async def start_healthcheck_server():
    app = web.Application()
    app.router.add_get(
        "/health", lambda request: web.Response(text="OK"))
    runner = web.AppRunner(app)
    await runner.setup()
    site = web.TCPSite(runner, "0.0.0.0", 8080)
    await site.start()


class StaffBot(commands.Bot):
    def __init__(self):
        super().__init__(
            command_prefix="/",
            intents=discord.Intents.all(),
            case_insensitive=True,
            activity=discord.Game(name="/help"))

    async def setup_hook(self):
        # load extensions
        for filename in os.listdir("./cogs"):
            if filename.endswith(".py") and not filename.startswith("_"):
                await self.load_extension(f"cogs.{filename[:-3]}")
        synced_commands = await self.tree.sync()
        logger.info(f"Synced {len(synced_commands)} commands")

        # start healthcheck server
        self.loop.create_task(start_healthcheck_server())
        logger.info("Healthcheck server started on port 8080")

    async def on_ready(self):
        logger.info(f'Bot ready, Logged in as {self.user.name}.')

        # add View to the bot
        # TODO

    async def on_connect(self):
        logger.info(f'Bot connected. (discord.py: v{discord.__version__})')

    async def on_disconnect(self):
        logger.warning('Bot disconnected.')

    async def on_resumed(self):
        logger.warning(f'Bot session resumed.')

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


@bot.tree.command(name="ping", description="Check if the bot is alive")
async def ping(interaction: discord.Interaction):
    await interaction.response.send_message(f"Pong! ({round(bot.latency * 1000)}ms)")


@bot.tree.command(name="help", description="Shows help about the bot, a command, or a category")
async def help(interaction: discord.Interaction):
    embed = discord.Embed(
        title="Help", description="List of all commands", color=discord.Colour.blurple())
    for command in bot.tree.walk_commands():
        if command is None:
            continue
        if command is not discord.app_commands.Group:
            embed.add_field(name=command.name,
                            value=command.description, inline=False)
        else:
            embed.add_field(name=command.name, value="\n".join(
                [f"`{subcommand.name}`: {subcommand.description}" for subcommand in command.children]), inline=False)

    await interaction.response.send_message(embed=embed)

if __name__ == "__main__":
    bot.run(settings.TOKEN, reconnect=True,
            log_handler=handler, log_level=logging.INFO)
