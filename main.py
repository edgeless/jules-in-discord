import os
import sys
import logging
import json
import discord
from discord.ext import commands, tasks
import aiohttp
from typing import Optional, Any, Dict, Tuple

# ログ設定
logging.basicConfig(level=logging.INFO)
logger = logging.getLogger('discord_bot')

intents = discord.Intents.default()
intents.message_content = True

class JulesBot(commands.Bot):
    def __init__(self):
        super().__init__(command_prefix="!", intents=intents)
        self.active_sessions: Dict[str, Dict[str, Any]] = {} # session_id -> {"thread_id": int, "last_state": str}

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

        self.poll_sessions.start()

    @tasks.loop(minutes=1)
    async def poll_sessions(self):
        if not self.active_sessions:
            return

        api_key = os.environ.get("JULES_API_KEY")
        if not api_key:
            return

        headers = {"x-goog-api-key": api_key}

        async with aiohttp.ClientSession() as session:
            # Create a copy of keys to safely remove items during iteration
            for session_id in list(self.active_sessions.keys()):
                info = self.active_sessions[session_id]
                url = f"https://jules.googleapis.com/v1alpha/sessions/{session_id}"

                try:
                    async with session.get(url, headers=headers) as response:
                        if response.status != 200:
                            if response.status in [401, 403, 404]:
                                # Stop tracking if the session was deleted externally or access is denied
                                del self.active_sessions[session_id]
                            continue

                        data = await response.json()
                        new_state = data.get("state")

                        if new_state and new_state != info["last_state"]:
                            self.active_sessions[session_id]["last_state"] = new_state

                            # Notify the thread
                            thread = self.get_channel(info["thread_id"])
                            if thread is None:
                                try:
                                    thread = await self.fetch_channel(info["thread_id"])
                                except discord.NotFound:
                                    # Thread deleted, stop tracking
                                    del self.active_sessions[session_id]
                                    continue
                                except discord.HTTPException:
                                    pass

                            if thread and isinstance(thread, discord.Thread):
                                msg = f"セッションの状態が更新されました: **{info['last_state']}** ➡️ **{new_state}**"
                                await thread.send(f"{msg}\n{format_json_response(data)}")

                            # Stop tracking if terminal state
                            if new_state in ["COMPLETED", "FAILED"]:
                                del self.active_sessions[session_id]

                except Exception as e:
                    logger.error(f"Error polling session {session_id}: {e}")

    @poll_sessions.before_loop
    async def before_poll_sessions(self):
        await self.wait_until_ready()

client = JulesBot()

@client.event
async def on_ready():
    logger.info(f'We have logged in as {client.user}')

def format_json_response(data: Any) -> str:
    if isinstance(data, str):
        try:
            data = json.loads(data)
        except json.JSONDecodeError:
            pass

    if isinstance(data, (dict, list)):
        formatted_str = json.dumps(data, indent=2, ensure_ascii=False)
    else:
        formatted_str = str(data)

    formatted_response = f"```json\n{formatted_str}\n```"
    if len(formatted_response) > 2000:
        truncated_length = 2000 - 3
        formatted_response = formatted_response[:truncated_length] + "```"
    return formatted_response

async def make_jules_api_request(
    interaction: discord.Interaction,
    method: str,
    endpoint: str,
    params: Optional[Dict[str, Any]] = None,
    json_data: Optional[Dict[str, Any]] = None
) -> Tuple[Optional[str], Optional[Any]]:
    api_key = os.environ.get("JULES_API_KEY")
    if not api_key:
        if not interaction.response.is_done():
            await interaction.response.send_message("エラー: JULES_API_KEY が設定されていません。", ephemeral=True)
        else:
            await interaction.followup.send("エラー: JULES_API_KEY が設定されていません。", ephemeral=True)
        return None, None

    if not interaction.response.is_done():
        await interaction.response.defer()

    url = f"https://jules.googleapis.com/v1alpha/{endpoint}"
    headers = {"x-goog-api-key": api_key}
    if json_data is not None:
        headers["Content-Type"] = "application/json"

    try:
        async with aiohttp.ClientSession() as session:
            async with session.request(method, url, headers=headers, params=params, json=json_data) as response:
                try:
                    response.raise_for_status()
                except aiohttp.ClientResponseError as e:
                    error_msg = f"APIエラー: {e.status} {e.message}"
                    if e.status == 401:
                        error_msg = "APIエラー: 認証に失敗しました (401)。APIキーを確認してください。"
                    elif e.status == 404:
                        error_msg = "APIエラー: リソースが見つかりません (404)。"

                    try:
                        error_text = await response.text()
                        error_msg += f"\n```json\n{error_text}\n```"
                    except:
                        pass

                    await interaction.followup.send(error_msg[:2000])
                    return None, None

                text_data = await response.text()
                try:
                    json_resp = await response.json()
                except Exception:
                    json_resp = None

                return text_data, json_resp
    except Exception as e:
        await interaction.followup.send(f"リクエスト送信中に予期せぬエラーが発生しました: {e}")
        return None, None

@client.tree.command(name="jules-list-sources", description="List Jules API sources")
async def jules_list_sources(interaction: discord.Interaction):
    text_data, _ = await make_jules_api_request(interaction, "GET", "sources")
    if text_data is not None:
        await interaction.followup.send(format_json_response(text_data))

@client.tree.command(name="create-a-session", description="Create a new Jules session")
async def create_a_session(interaction: discord.Interaction, prompt: str, title: Optional[str] = None, require_plan_approval: Optional[bool] = None):
    payload = {"prompt": prompt}
    if title is not None:
        payload["title"] = title
    if require_plan_approval is not None:
        payload["requirePlanApproval"] = require_plan_approval

    text_data, json_resp = await make_jules_api_request(interaction, "POST", "sessions", json_data=payload)
    if json_resp is None:
        return

    session_name = json_resp.get("name", "")
    session_id = session_name.split("/")[-1] if "/" in session_name else json_resp.get("id", "unknown_id")

    message = await interaction.followup.send(f"セッションを作成しました。", wait=True)
    try:
        thread = await message.create_thread(name=f"Session: {session_id}")
        await thread.send(format_json_response(json_resp))

        # Track session for polling
        state = json_resp.get("state", "QUEUED")
        if state not in ["COMPLETED", "FAILED"]:
            client.active_sessions[session_id] = {"thread_id": thread.id, "last_state": state}

    except Exception as e:
        await interaction.followup.send(f"スレッドの作成に失敗しました: {e}\n{format_json_response(json_resp)}")

@client.tree.command(name="list-sessions", description="List Jules sessions")
async def list_sessions(interaction: discord.Interaction, page_size: Optional[int] = None, page_token: Optional[str] = None):
    params = {}
    if page_size is not None:
        params["pageSize"] = page_size
    if page_token is not None:
        params["pageToken"] = page_token

    text_data, json_resp = await make_jules_api_request(interaction, "GET", "sessions", params=params)
    if text_data is not None:
        await interaction.followup.send(format_json_response(text_data))

@client.tree.command(name="get-a-session", description="Get a specific Jules session")
async def get_a_session(interaction: discord.Interaction, session_id: str):
    text_data, json_resp = await make_jules_api_request(interaction, "GET", f"sessions/{session_id}")
    if json_resp is None:
        return

    message = await interaction.followup.send(f"セッション {session_id} の情報を取得しました。", wait=True)
    try:
        thread = await message.create_thread(name=f"Session: {session_id}")
        await thread.send(format_json_response(json_resp))

        # Track session for polling
        state = json_resp.get("state", "QUEUED")
        if state not in ["COMPLETED", "FAILED"]:
            client.active_sessions[session_id] = {"thread_id": thread.id, "last_state": state}

    except Exception as e:
        await interaction.followup.send(f"スレッドの作成に失敗しました: {e}\n{format_json_response(json_resp)}")

@client.tree.command(name="delete-a-session", description="Delete a specific Jules session")
async def delete_a_session(interaction: discord.Interaction, session_id: str):
    text_data, _ = await make_jules_api_request(interaction, "DELETE", f"sessions/{session_id}")
    if text_data is not None:
        await interaction.followup.send(f"セッション {session_id} を削除しました。")
        # Untrack session
        if session_id in client.active_sessions:
            del client.active_sessions[session_id]

@client.tree.command(name="send-a-message", description="Send a message to an active Jules session")
async def send_a_message(interaction: discord.Interaction, prompt: str):
    if not isinstance(interaction.channel, discord.Thread):
        await interaction.response.send_message("エラー: このコマンドはセッションのスレッド内でのみ実行できます。", ephemeral=True)
        return

    thread_name = interaction.channel.name
    if not thread_name.startswith("Session: "):
        await interaction.response.send_message("エラー: このスレッドは有効なセッションスレッドではありません。", ephemeral=True)
        return

    session_id = thread_name.replace("Session: ", "").strip()
    payload = {"prompt": prompt}

    text_data, json_resp = await make_jules_api_request(interaction, "POST", f"sessions/{session_id}:sendMessage", json_data=payload)
    if text_data is not None:
        await interaction.followup.send(f"メッセージを送信しました。\n{format_json_response(text_data)}")

@client.tree.command(name="approve-a-plan", description="Approve a pending plan in a Jules session")
async def approve_a_plan(interaction: discord.Interaction):
    if not isinstance(interaction.channel, discord.Thread):
        await interaction.response.send_message("エラー: このコマンドはセッションのスレッド内でのみ実行できます。", ephemeral=True)
        return

    thread_name = interaction.channel.name
    if not thread_name.startswith("Session: "):
        await interaction.response.send_message("エラー: このスレッドは有効なセッションスレッドではありません。", ephemeral=True)
        return

    session_id = thread_name.replace("Session: ", "").strip()

    text_data, json_resp = await make_jules_api_request(interaction, "POST", f"sessions/{session_id}:approvePlan", json_data={})
    if text_data is not None:
        await interaction.followup.send(f"プランを承認しました。\n{format_json_response(text_data)}")

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
