import os
import sys
import logging
import discord

# ログ設定
logging.basicConfig(level=logging.INFO)
logger = logging.getLogger('discord_bot')

intents = discord.Intents.default()
intents.message_content = True

client = discord.Client(intents=intents)

@client.event
async def on_ready():
    logger.info(f'We have logged in as {client.user}')

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
