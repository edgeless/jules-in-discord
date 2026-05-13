import os
import sys
import logging
import json
import discord
from discord.ext import commands
import aiohttp
from typing import Optional

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

def format_json_response(data: str) -> str:
    formatted_response = f"```json\n{data}\n```"
    if len(formatted_response) > 2000:
        truncated_length = 2000 - 3
        formatted_response = formatted_response[:truncated_length] + "```"
    return formatted_response

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

    await interaction.followup.send(format_json_response(data))

@client.tree.command(name="create-a-session", description="Create a new Jules session")
async def create_a_session(interaction: discord.Interaction, prompt: str, title: Optional[str] = None, require_plan_approval: Optional[bool] = None):
    api_key = os.environ.get("JULES_API_KEY")
    if not api_key:
        await interaction.response.send_message("エラー: JULES_API_KEY が設定されていません。", ephemeral=True)
        return

    await interaction.response.defer()

    url = "https://jules.googleapis.com/v1alpha/sessions"
    headers = {
        "x-goog-api-key": api_key,
        "Content-Type": "application/json"
    }
    payload = {"prompt": prompt}
    if title is not None:
        payload["title"] = title
    if require_plan_approval is not None:
        payload["requirePlanApproval"] = require_plan_approval

    try:
        async with aiohttp.ClientSession() as session:
            async with session.post(url, headers=headers, json=payload) as response:
                response.raise_for_status()
                data_text = await response.text()
                data_json = await response.json()
    except Exception as e:
        await interaction.followup.send(f"APIリクエスト中にエラーが発生しました: {e}")
        return

    session_name = data_json.get("name", "")
    session_id = session_name.split("/")[-1] if "/" in session_name else data_json.get("id", "unknown_id")

    message = await interaction.followup.send(f"セッションを作成しました。", wait=True)
    try:
        thread = await message.create_thread(name=f"Session: {session_id}")
        await thread.send(format_json_response(data_text))
    except Exception as e:
        await interaction.followup.send(f"スレッドの作成に失敗しました: {e}\n{format_json_response(data_text)}")

@client.tree.command(name="list-sessions", description="List Jules sessions")
async def list_sessions(interaction: discord.Interaction, page_size: Optional[int] = None, page_token: Optional[str] = None):
    api_key = os.environ.get("JULES_API_KEY")
    if not api_key:
        await interaction.response.send_message("エラー: JULES_API_KEY が設定されていません。", ephemeral=True)
        return

    await interaction.response.defer()

    url = "https://jules.googleapis.com/v1alpha/sessions"
    headers = {"x-goog-api-key": api_key}
    params = {}
    if page_size is not None:
        params["pageSize"] = page_size
    if page_token is not None:
        params["pageToken"] = page_token

    try:
        async with aiohttp.ClientSession() as session:
            async with session.get(url, headers=headers, params=params) as response:
                response.raise_for_status()
                data = await response.text()
    except Exception as e:
        await interaction.followup.send(f"APIリクエスト中にエラーが発生しました: {e}")
        return

    await interaction.followup.send(format_json_response(data))

@client.tree.command(name="get-a-session", description="Get a specific Jules session")
async def get_a_session(interaction: discord.Interaction, session_id: str):
    api_key = os.environ.get("JULES_API_KEY")
    if not api_key:
        await interaction.response.send_message("エラー: JULES_API_KEY が設定されていません。", ephemeral=True)
        return

    await interaction.response.defer()

    url = f"https://jules.googleapis.com/v1alpha/sessions/{session_id}"
    headers = {"x-goog-api-key": api_key}

    try:
        async with aiohttp.ClientSession() as session:
            async with session.get(url, headers=headers) as response:
                response.raise_for_status()
                data_text = await response.text()
    except Exception as e:
        await interaction.followup.send(f"APIリクエスト中にエラーが発生しました: {e}")
        return

    message = await interaction.followup.send(f"セッション {session_id} の情報を取得しました。", wait=True)
    try:
        thread = await message.create_thread(name=f"Session: {session_id}")
        await thread.send(format_json_response(data_text))
    except Exception as e:
        await interaction.followup.send(f"スレッドの作成に失敗しました: {e}\n{format_json_response(data_text)}")

@client.tree.command(name="delete-a-session", description="Delete a specific Jules session")
async def delete_a_session(interaction: discord.Interaction, session_id: str):
    api_key = os.environ.get("JULES_API_KEY")
    if not api_key:
        await interaction.response.send_message("エラー: JULES_API_KEY が設定されていません。", ephemeral=True)
        return

    await interaction.response.defer()

    url = f"https://jules.googleapis.com/v1alpha/sessions/{session_id}"
    headers = {"x-goog-api-key": api_key}

    try:
        async with aiohttp.ClientSession() as session:
            async with session.delete(url, headers=headers) as response:
                response.raise_for_status()
    except Exception as e:
        await interaction.followup.send(f"APIリクエスト中にエラーが発生しました: {e}")
        return

    await interaction.followup.send(f"セッション {session_id} を削除しました。")

@client.tree.command(name="send-a-message", description="Send a message to an active Jules session")
async def send_a_message(interaction: discord.Interaction, prompt: str):
    api_key = os.environ.get("JULES_API_KEY")
    if not api_key:
        await interaction.response.send_message("エラー: JULES_API_KEY が設定されていません。", ephemeral=True)
        return

    # Check if executed in a thread
    if not isinstance(interaction.channel, discord.Thread):
        await interaction.response.send_message("エラー: このコマンドはセッションのスレッド内でのみ実行できます。", ephemeral=True)
        return

    thread_name = interaction.channel.name
    if not thread_name.startswith("Session: "):
        await interaction.response.send_message("エラー: このスレッドは有効なセッションスレッドではありません。", ephemeral=True)
        return

    session_id = thread_name.replace("Session: ", "").strip()

    await interaction.response.defer()

    url = f"https://jules.googleapis.com/v1alpha/sessions/{session_id}:sendMessage"
    headers = {
        "x-goog-api-key": api_key,
        "Content-Type": "application/json"
    }
    payload = {"prompt": prompt}

    try:
        async with aiohttp.ClientSession() as session:
            async with session.post(url, headers=headers, json=payload) as response:
                response.raise_for_status()
                data_text = await response.text()
    except Exception as e:
        await interaction.followup.send(f"APIリクエスト中にエラーが発生しました: {e}")
        return

    await interaction.followup.send(f"メッセージを送信しました。\n{format_json_response(data_text)}")


@client.tree.command(name="approve-a-plan", description="Approve a pending plan in a Jules session")
async def approve_a_plan(interaction: discord.Interaction):
    api_key = os.environ.get("JULES_API_KEY")
    if not api_key:
        await interaction.response.send_message("エラー: JULES_API_KEY が設定されていません。", ephemeral=True)
        return

    # Check if executed in a thread
    if not isinstance(interaction.channel, discord.Thread):
        await interaction.response.send_message("エラー: このコマンドはセッションのスレッド内でのみ実行できます。", ephemeral=True)
        return

    thread_name = interaction.channel.name
    if not thread_name.startswith("Session: "):
        await interaction.response.send_message("エラー: このスレッドは有効なセッションスレッドではありません。", ephemeral=True)
        return

    session_id = thread_name.replace("Session: ", "").strip()

    await interaction.response.defer()

    url = f"https://jules.googleapis.com/v1alpha/sessions/{session_id}:approvePlan"
    headers = {
        "x-goog-api-key": api_key,
        "Content-Type": "application/json"
    }
    payload = {}

    try:
        async with aiohttp.ClientSession() as session:
            async with session.post(url, headers=headers, json=payload) as response:
                response.raise_for_status()
                data_text = await response.text()
    except Exception as e:
        await interaction.followup.send(f"APIリクエスト中にエラーが発生しました: {e}")
        return

    await interaction.followup.send(f"プランを承認しました。\n{format_json_response(data_text)}")


@client.event
async def on_message(message):
    if message.author.bot:
        return
    if not message.content:
        return
    await message.channel.send(message.content)

def main():
    token = os.environ.get("DISCORD_TOKEN")
    if not token:
        logger.error("Error: DISCORD_TOKEN environment variable not set.")
        sys.exit(1)
    client.run(token)

if __name__ == "__main__":
    main()
