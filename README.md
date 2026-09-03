# Break Reminder App

Windows 常駐を想定した休憩促進アプリです。  
作業タイマー、休憩ダイアログ、SQLiteログ、ntfy通知（任意）を MVP として実装しています。

## 初回セットアップ

1. Python 3.11.9 を用意
2. 依存関係をインストール

```bash
pip install -r requirements.txt
```

3. 設定ファイルを作成

```powershell
Copy-Item config.example.json config.json
```

4. 必要に応じて `config.json` を編集

## 設定項目（config.json）

- `work_minutes`: 作業タイマーの分数（整数、1〜240）
- `min_break_seconds`: 最低休憩秒数
- `ntfy_enabled`: ntfy通知の有効/無効
- `ntfy_topic`: ntfyトピック名（空なら送信しない）
- `notification_level`: 通知レベル（MVPでは2想定）
- `notion_enabled`: 体調ログのNotion同期の有効/無効
- `notion_database_id`: 同期先のNotionデータベースIDまたはURL
- `notion_api_token`: Notion内部インテグレーションのトークン
- `effects_enabled`: 休憩オーバーレイ画像演出の有効/無効
- `effect_image_path`: 休憩オーバーレイに表示する画像ファイルパス（空なら表示しない）
- `start_with_windows`: Windowsログイン時の自動起動
- `hotkey_enabled`: グローバル作業開始ホットキーの有効/無効
- `hotkey_start_work`: 作業開始ホットキー文字列（MVP既定: `Ctrl+Alt+B`）
- `messages`: ダイアログ/通知文言のカスタマイズ

`config.json` が存在しない場合や、JSON/型が不正な場合はデフォルト値で起動し、エラー内容を標準出力へ表示します。

## ntfy 設定方法

1. Android に `ntfy` アプリをインストール
2. 任意トピックを購読
3. `config.json` で `ntfy_enabled: true` と `ntfy_topic` を設定

## Notion同期

1. [Notion integrations](https://www.notion.so/profile/integrations) で内部インテグレーションを作成し、コンテンツの読み取り・挿入権限を付与
2. 同期先データベースをそのインテグレーションと共有
3. アプリの「設定」でNotion同期を有効化し、DB ID/URLとintegration tokenを保存
4. トレイメニューの「Notionへ同期」を実行

同期はバックグラウンドで実行され、`notion_synced=false` の記録だけを転送します。ローカルの同期状態更新前にアプリが終了しても、次回は同期キーで既存ページを確認するため重複作成しません。

Notion側ではタイトル列を必須とし、次の名前と型が存在する場合は自動で列に割り当てます。

| 列名 | 推奨型 |
| --- | --- |
| `日時` | 日付 |
| `体調` / `気分` / `余力` | 数値 |
| `不調項目` | マルチセレクト |
| `コメント` / `source` | テキスト |

列がない場合でも、元のJSONレコードをNotionページ本文に保存します。`notion_api_token` はGit管理対象外の `config.json` に保存されますが、平文であるためファイルの取り扱いに注意してください。

### メッセージ文言の編集

`messages` は現状の設定画面では編集できないため、`config.json` を直接編集してください。

```json
{
  "messages": {
    "break_normal": "休憩時間です。PCから離れてください。",
    "break_too_short": "まだ休憩できていません。もう少しPCから離れてください。",
    "end_confirm": "本当に今日の作業を終了しますか？"
  }
}
```

## 休憩オーバーレイ画像

- 設定ダイアログの「演出」を有効化し、「演出画像」でファイルを選択できます
- 対応形式: `.jpg` `.jpeg` `.bmp` `.png` `.gif`
- `effects_enabled=true` かつ `effect_image_path` が有効な場合のみ表示します

## 起動方法

```bash
python main.py
```

## Windows連携機能

- 設定ダイアログの「Windows起動時に自動起動」をONにすると、Startupフォルダへ `Break Reminder App.lnk` を作成します
- 「作業開始ショートカットを有効化」をONにすると、グローバルホットキーで作業開始できます（既定: `Ctrl+Alt+B`）
- いずれも設定保存後に即時反映されます

## MVP機能一覧

- タスクトレイ常駐
- 起動時に作業開始ダイアログを自動表示
- 作業開始/停止
- 作業開始ダイアログからの体調入力
- 作業タイマー満了で休憩ダイアログ表示
- 最低休憩秒数チェックと再通知
- Windowsスタートアップ登録（任意）
- グローバルホットキー開始（任意）
- ntfy によるAndroid通知（任意）
- SQLiteログ記録
- 体調ログのNotion同期（任意）
- アプリ内ログビューア

## ログファイル

- SQLite DB は `data/logs.db` に作成されます
- `data/logs.db` は Git 管理対象外です
