サーバー連結BOT

Discordの異なるサーバーのチャンネルの発言をリアルタイムで共有し、疑似的な共有チャンネル（グルーバルチャンネル）を実現するためのBOTです。

セットアップ

1. setup.pyを実行します。
2. __init__.py に、BOT TOKEN, 連結本部サーバーのID, 管理者コマンドの実行チャンネルのID, 本部用中継カテゴリのIDを記入します。

必要動作環境
python3.8 (python3.7以上)
Discord.py 1.3
requests 2.13.0 (これ以上のバージョンでは誤動作の可能性があります。)
