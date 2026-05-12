# AI Agent Guidelines (AGENTS.md)

This project is a Discord Bot implemented in Python using the `discord.py` library. It runs inside a Docker container using Docker Compose.

## 概要 (Overview)
- **Language**: Python 3.11+
- **Library**: `discord.py`
- **Environment**: Docker, Docker Compose

## コーディングガイドライン (Coding Guidelines)
1. **依存関係 (Dependencies)**
   - 必要なライブラリは `requirements.txt` に追記してください。
   - `pip install` コマンドで追加インストールが必要な場合は必ず `requirements.txt` を更新してください。

2. **環境変数 (Environment Variables)**
   - 機密情報（Discordトークンなど）はソースコードに直書きせず、必ず環境変数経由で取得してください（例: `os.environ.get("DISCORD_TOKEN")`）。
   - 環境変数を追加した場合は、`compose.yaml` の `environment` セクションおよび `README.md` の実行手順を適宜更新してください。

3. **Discord Bot の仕様 (Discord Bot Specifications)**
   - `discord.Intents.message_content = True` を有効にしています（メッセージの内容を読み取るため）。新しい機能を追加する際に他のIntentsが必要になった場合は、`main.py` のIntents設定を更新してください。
   - 無限ループを防ぐため、bot自身や他のbotからのメッセージには反応しないガード句を維持してください (`if message.author.bot: return`)。
   - 現在の仕様は「すべてのメッセージに反応してechoする」というシンプルなものですが、将来的に特定のコマンド等にのみ反応するように変更される可能性があります。その場合は `on_message` イベント内のロジックを修正してください。

4. **テスト・実行 (Testing & Execution)**
   - ローカルでの動作確認にはDocker Composeを利用することが推奨されます。
   - 変更を加えた際は、`docker compose build` および `docker compose up` で正常に起動することを確認してください。
