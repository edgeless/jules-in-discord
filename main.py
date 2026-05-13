import os
import sys
import logging
import discord
from discord.ext import commands
import aiohttp

# ログ設定
logging.basicConfig(level=logging.INFO)
logger = logging.getLogger('discord_bot')

intents = discord.Intents.default()
intents.message_content = True

class JulesBot(commands.Bot):
    def __init__(self):
        super().__init__(command_prefix="!", intents=intents)

    async def setup_hook(self):
        guild_id_str = os.environ.get("DISCORD_GUILD_ID")
        if guild_id_str:
            try:
                guild_id = int(guild_id_str)
                guild = discord.Object(id=guild_id)
                self.tree.copy_global_to(guild=guild)
                await self.tree.sync(guild=guild)
                logger.info(f"Synced commands to guild {guild_id}")
            except ValueError:
                logger.error("Invalid DISCORD_GUILD_ID format.")
        else:
            await self.tree.sync()
            logger.info("Synced commands globally")

client = JulesBot()

@client.event
async def on_ready():
    logger.info(f'We have logged in as {client.user}')

@client.tree.command(name="jules-list-sources", description="List Jules API sources")
async def jules_list_sources(interaction: discord.Interaction):
    api_key = os.environ.get("JULES_API_KEY")
    if not api_key:
        await interaction.response.send_message("エラー: JULES_API_KEY が設定されていません。", ephemeral=True)
        return

    await interaction.response.defer()

    url = "https://jules.googleapis.com/v1alpha/sources"
    headers = {"x-goog-api-key": api_key}

    try:
        async with aiohttp.ClientSession() as session:
            async with session.get(url, headers=headers) as response:
                response.raise_for_status()
                data = await response.text()
    except Exception as e:
        await interaction.followup.send(f"APIリクエスト中にエラーが発生しました: {e}")
        return

    formatted_response = f"```json\n{data}\n```"

    if len(formatted_response) > 2000:
        # Discordの2000文字制限に収めるため切り詰める
        # "```" (3文字) を考慮して、1997文字まででカットする
        truncated_length = 2000 - 3
        formatted_response = formatted_response[:truncated_length] + "```"

    await interaction.followup.send(formatted_response)

@client.event
async def on_message(message):
    # bot自身や他のbotからのメッセージは無視する（無限ループ防止）
    if message.author.bot:
        return

    # 内容が空のメッセージ（画像のみなど）は無視する
    if not message.content:
        return

    # メッセージをそのままechoする
    await message.channel.send(message.content)

def main():
    token = os.environ.get("DISCORD_TOKEN")
    if not token:
        logger.error("Error: DISCORD_TOKEN environment variable not set.")
        sys.exit(1)
    client.run(token)

if __name__ == "__main__":
    main()
