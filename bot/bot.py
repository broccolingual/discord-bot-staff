import datetime
import pytz
import logging
import os

import discord
from discord import app_commands
from discord.ext import commands, tasks

import settings
from supabase_db.interfaces import SupabaseDB

# Set up logging
logger = logging.getLogger("discord")
if logger.hasHandlers():
    logger.handlers.clear()
logger.setLevel(logging.DEBUG)
handler = logging.StreamHandler()
handler.setFormatter(logging.Formatter(
    '%(asctime)s:%(name)s:%(lineno)d:%(levelname)s:%(message)s'))
logger.addHandler(handler)

tz = pytz.timezone("Asia/Tokyo")


class StaffBot(commands.Bot):
    def __init__(self):
        super().__init__(
            command_prefix="/",
            intents=discord.Intents.all(),
            case_insensitive=True,
            activity=discord.Game(name="/help"))
        self.db = SupabaseDB()

    async def setup_hook(self):
        # load extensions
        for filename in os.listdir("./cogs"):
            if filename.endswith(".py") and not filename.startswith("_"):
                await self.load_extension(f"cogs.{filename[:-3]}")
        synced_commands = await self.tree.sync()
        logger.info(f"Synced {len(synced_commands)} commands")

        await self.db.get_client()

    async def on_ready(self):
        logger.info(f'Bot ready, Logged in as {self.user.name}.')
        self.check_and_start_events.start()

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

    @tasks.loop(minutes=1)
    async def check_and_start_events(self):
        logger.info("Checking for events to start...")
        now = datetime.datetime.now(tz)
        events_already_started = await bot.db.get_events_should_have_been_started(current_time=now)
        if events_already_started:
            for event_already_started in events_already_started:
                event_id = event_already_started["event_id"]
                guild = self.get_guild(event_already_started["server_id"])
                if guild is None:
                    continue
                event = await guild.fetch_scheduled_event(event_id)
                if event is None:
                    await self.db.update_event_status(
                        msg_id=event_already_started["msg_id"], was_ended=True)
                    continue
                if event.status == discord.EventStatus.scheduled:
                    await event.start()


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
