import discord

async def blank_interaction(interaction: discord.Interaction):
    try:
        await interaction.response.send_message("")
    except discord.errors.HTTPException:
        pass
