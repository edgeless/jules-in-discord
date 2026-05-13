# jules-in-discord
discordでjules連携します。

## インストールと実行手順

このBotはDockerおよびDocker Composeを使用して実行することを想定しています。

### 必要なもの
- Docker
- Docker Compose
- Discord Botのトークン

### 実行方法

1. リポジトリをクローンまたはダウンロードします。

2. ルートディレクトリに `.env` ファイルを作成し、Discordのトークンやその他の環境変数を設定します。
   ```
   DISCORD_TOKEN=あなたのDiscordボットのトークン
   JULES_API_KEY=あなたのJules APIキー
   DISCORD_GUILD_ID=コマンドを登録するDiscordサーバーのID
   ```
   または、実行時に環境変数として渡すこともできます。

3. Docker Composeを使用してコンテナをビルドおよび起動します。
   ```sh
   # バックグラウンドで起動する場合
   docker compose up -d --build
   ```

   `.env` ファイルを使用しない場合は、以下のように実行します。
   ```sh
   DISCORD_TOKEN=あなたのDiscordボットのトークン JULES_API_KEY=キー DISCORD_GUILD_ID=ID docker compose up -d --build
   ```

### 停止方法

コンテナを停止する場合は、以下のコマンドを実行します。
```sh
docker compose down
```

## 現在の仕様
- 参加しているサーバーでのすべてのメッセージに反応して、同じメッセージを返します（echo機能）。
- 他のBotからのメッセージには反応しません。
