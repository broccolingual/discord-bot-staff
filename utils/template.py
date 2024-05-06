import discord

def getSubcommandsEmbed(parent_command):
    embed = discord.Embed(title=f"Subcommands of `{parent_command.name}`", description=parent_command.description, color=discord.Colour.blurple())
    for subcommand in parent_command.commands:
        embed.add_field(name=f"`{subcommand.name}`", value=subcommand.description, inline=False)
    return embed
