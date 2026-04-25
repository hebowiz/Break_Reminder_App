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

- `work_minutes`: 作業タイマーの分数
- `min_break_seconds`: 最低休憩秒数
- `ntfy_enabled`: ntfy通知の有効/無効
- `ntfy_topic`: ntfyトピック名（空なら送信しない）
- `notification_level`: 通知レベル（MVPでは2想定）
- `effects_enabled`: 演出機能の有効/無効（MVPでは未使用）

`config.json` が存在しない場合や、JSON/型が不正な場合はデフォルト値で起動し、エラー内容を標準出力へ表示します。

## ntfy 設定方法

1. Android に `ntfy` アプリをインストール
2. 任意トピックを購読
3. `config.json` で `ntfy_enabled: true` と `ntfy_topic` を設定

## 起動方法

```bash
python main.py
```

## MVP機能一覧

- タスクトレイ常駐
- 作業開始/停止
- 作業タイマー満了で休憩ダイアログ表示
- 最低休憩秒数チェックと再通知
- ntfy によるAndroid通知（任意）
- SQLiteログ記録
- アプリ内ログビューア

## ログファイル

- SQLite DB は `data/logs.db` に作成されます
- `data/logs.db` は Git 管理対象外です
