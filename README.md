# Break Reminder App

Windows 常駐を想定した休憩促進アプリの土台プロジェクトです。  
現在はファイル構成と最小スタブのみを用意しています。

## 実行方法

1. Python 3.11.9 を使用
2. 依存関係をインストール

```bash
pip install -r requirements.txt
```

3. アプリ起動

```bash
python main.py
```

## MVP 予定機能

- タスクトレイからの開始/停止/一時停止操作
- 作業タイマーと休憩ダイアログ表示
- `ntfy` 通知連携
- SQLite へのイベントログ保存
- 演出エフェクトの有効/無効切り替え
