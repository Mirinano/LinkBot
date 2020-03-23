#!python3.8
__title__ = 'Discord ServerLink Bot'
__author__ = 'Mirinano'
__copyright__ = 'Copyright 2020 Mirinano'
__version__ = '1.0.0' #2020/03/23

from collections import namedtuple

VersionInfo = namedtuple('VersionInfo', 'major minor micro releaselevel serial')

version_info = VersionInfo(major=1, minor=0, micro=0, releaselevel='final', serial=0)

class Config:
    TOKEN = ""
    MAS_SERVER = 
    MAS_CHANNEL= 
    MAS_CATEGORY = 
    DB = "Link.db"

    #cmd trigger
    join_cmd = "&join"
    left_cmd = "&left"
    help_cmd = "&help"
    list_cmd = "&group"

    #master cmd trigger
    del_cmd = "&del"
    blacklist_cmd = "&blacklist"
    sql_cmd = "&sql"

    #file path
    help_fp = "help.txt"

class Error:
    already_linkd = "【エラー】このチャンネルは既に連結されています。\n新しいグループに接続する場合は、`&left`コマンドでグループから切断してから実行してください。"
    unset_unit = "【エラー】グループ名が指定されていません。\nコマンドは`&help`で確認することができます。"
    invalid_char = "【エラー】グループ名に不正な文字が含まれています。\nグループ名に指定可能な文字は半角小文字英字のみです。"
    manage_webhooks = "【エラー】BOTにwebhookを管理(Manage Webhook)権限がありません。\nBOTがWebhookを管理できるチャンネルのみ連結させることができます。"

    unset_msg = "【エラー】メッセージIDが指定されていません。\n削除したいメッセージの下に書かれている数字を指定してください。"
    unset_action = "【エラー】Actionが未指定です。\nコマンドが正しいか確認してください。"
    
    unknowe_action = "【エラー】存在しないActionです。\nコマンドが正しいか確認してください。"
    unknown_user = "【エラー】存在しないユーザーIDです。"
    
    no_exist_db = "【エラー】データベースに該当するデータが存在しません。\nBOT管理者にお問い合わせください。"

    timeout = "【エラー】タイムアウトエラー。\n再度実行してください。"

    unexpected = "【エラー】<@391943696809197568> 予期せぬエラーです。\n詳細:\n{}"

class BotMessage:
    message_link = "https://discordapp.com/channels/{server}/{channel}/{message}"

    cancel = "コマンドの実行をキャンセルしました。"

    join_msg = "【{join}が{unit}に参加しました】\n現在{unit}に参加しているサーバー: {servers}"
    left_msg = "【{left}が{unit}から退出しました】\n現在{unit}に参加しているサーバー: {servers}"
    group_list_msg = "現在「{unit}」に参加しているサーバー一覧:\n\t{servers}"
    
    cmd_cancel = "コマンドの実行をキャンセルしました。"

    delete_cmd_check = """メッセージの削除を実施します。
連結グループ名: {unit}
メッセージID: {msg_id}
送信者: {author}
チャンネル: {channel} ({server})
同メッセージが投稿されたチャンネル一覧:
\t{channels}
メッセージ内容:
```
{content}
```
削除する場合は✅を、キャンセルする場合には❌を選択してください。"""
    delete_cmd_result = """【削除完了】
連結グループ名: {unit}
メッセージID: {msg_id}\n"""
    delete_cmd_result_done = "削除成功チャンネル一覧:\n\t{}\n"
    delete_cmd_result_fail = "削除失敗チャンネル一覧:\n\t{}\n"

    blacklist_user   = "{name} <@{id}> (ID: {id})"
    blacklist_add    = "{name} <@{id}> (ID: {id})をブラックリストに追加しました。"
    blacklist_remove = "{name} <@{id}> (ID: {id})をブラックリストから除外しました。"
