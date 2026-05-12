import os
import discord

intents = discord.Intents.default()
intents.message_content = True

client = discord.Client(intents=intents)

@client.event
async def on_ready():
    print(f'We have logged in as {client.user}')

@client.event
async def on_message(message):
    # bot自身や他のbotからのメッセージは無視する（無限ループ防止）
    if message.author.bot:
        return

    # メッセージをそのままechoする
    await message.channel.send(message.content)

def main():
    token = os.environ.get("DISCORD_TOKEN")
    if not token:
        print("Error: DISCORD_TOKEN environment variable not set.")
        return
    client.run(token)

if __name__ == "__main__":
    main()
