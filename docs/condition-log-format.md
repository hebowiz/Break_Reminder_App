# Break Reminder 体調ログ仕様

## 概要

Break Reminder の体調ログは、SQLite DB ではなく UTF-8 の JSONL ファイルを正本として保存する。

| 項目 | 現行仕様 |
| --- | --- |
| 保存先 | `data/condition_log.jsonl` |
| 形式 | JSON Lines: 1行 = 1 JSON |
| 書き込み | ファイル末尾へ append |
| 文字コード | UTF-8 |
| 日本語 | JSONへそのまま保存 |
| Git管理 | `.gitignore` 対象 |

SQLite の `data/logs.db` は作業セッション専用であり、体調ログ用テーブルは存在しない。

## 体調入力ダイアログ

入力項目は以下の順序で表示する。

1. 体調
2. 気分
3. 余力
4. 不調項目
5. コメント

体調・気分・余力はスライダー入力とする。初期値は `50`、範囲は `0..100`、UI上は `10` 刻みである。

固定の不調項目:

```text
IBS, 眠気, 倦怠感, 疲れやすい, 頭痛, 動悸, 下痢, 火照り,
目眩, 鼻炎, 目のかすみ, 発熱, 悪寒, 思考乱れ
```

`その他` は保存値ではなく、自由入力欄を有効化するためのUI項目である。

## 現行 JSONL フォーマット

新規保存されるレコード:

```json
{
  "log_version": 1,
  "timestamp": "2026-06-01T14:35:12",
  "condition": 60,
  "mood": 40,
  "energy": 30,
  "comment": "午前中からややだるい",
  "symptoms": ["眠気", "吐き気"],
  "source": "break_reminder",
  "notion_synced": false
}
```

| キー | JSON型 | 新規ログで必須 | nullable | 補足 |
| --- | --- | --- | --- | --- |
| `log_version` | number / integer | Yes | No | 現在は `1` 固定 |
| `timestamp` | string | Yes | No | ISO 8601、秒単位。現在はタイムゾーンなし |
| `condition` | number / integer | Yes | No | `0..100` |
| `mood` | number / integer | Yes | No | `0..100` |
| `energy` | number / integer | Yes | No | `0..100` |
| `comment` | string | Yes | No | 未入力時は `""` |
| `symptoms` | array of string | Yes | No | 未選択時は `[]` |
| `source` | string | Yes | No | 現在は `"break_reminder"` 固定 |
| `notion_synced` | boolean | Yes | No | 現在は常に `false` |

## 正規化ルール

`symptoms` は保存前に以下のルールで正規化する。

- 半角カンマ `,` と全角読点 `、` で分割する
- 各項目の前後空白を除去する
- 空文字を除外する
- `"その他"` という文字列自体は除外する
- 重複を除外する
- 初出順を維持する
- 大文字小文字や Unicode 表記揺れの統一は行わない

例:

```text
入力: 眠気, 吐き気、 胃もたれ, 眠気
保存: ["眠気", "吐き気", "胃もたれ"]
```

コメントはダイアログ確定時に前後空白を除去する。

## 旧ログ互換

旧形式のログには `comment` がなく、自由入力された症状が `other_symptom` に保存されている。

```json
{
  "symptoms": ["眠気"],
  "other_symptom": "吐き気, 胃もたれ"
}
```

閲覧時には `other_symptom` を分割し、`symptoms` と統合して表示する。旧レコード自体の書き換えは行わない。

新規保存では `other_symptom` を使用しない。

## 保存・閲覧・エクスポート

- 体調入力ダイアログで OK を押した場合のみ保存する
- Cancel 時は保存しない
- 閲覧ダイアログでは JSONL を全件読み込み、日時の降順で表示する
- 表示列は `日時 | 体調 | 気分 | 余力 | 不調項目 | コメント`
- 専用の CSV・JSON エクスポート処理は未実装
- 現状は JSONL ファイル自体が持ち出し可能な原本

## PWA 共通化時に固定すべき外部仕様

まずは現行の新形式を共通フォーマットの基準とする。

```json
{
  "log_version": 1,
  "timestamp": "2026-06-01T14:35:12",
  "condition": 60,
  "mood": 40,
  "energy": 30,
  "comment": "",
  "symptoms": [],
  "source": "break_reminder",
  "notion_synced": false
}
```

PWA 実装前に、以下を外部仕様として明示的に決定する。

### timestamp

現行アプリはタイムゾーンなしのローカル時刻を保存している。

```text
2026-06-01T14:35:12
```

スマートフォン連携では、タイムゾーン付き ISO 8601 への移行を推奨する。

```text
2026-06-01T14:35:12+09:00
```

### source

現行アプリは `"break_reminder"` 固定で保存している。PWA 導入後は送信元を区別できる値を定義する。

例:

```text
break_reminder
break_reminder_pwa
```

### score

`condition`、`mood`、`energy` の `10` 刻みは入力UI仕様である。共有データ仕様では `0..100` の整数として定義する。

### notion_synced

現行互換のため JSONL では boolean として保持する。複数端末同期を導入する場合は、同期状態をログ本体から分離する設計も検討する。

## 現行実装の参照先

| 内容 | ファイル |
| --- | --- |
| 入力ダイアログ | `app/ui/condition_dialog.py` |
| JSONL生成・保存・読込・正規化 | `app/infra/condition_logger.py` |
| 体調ログ閲覧 | `app/ui/condition_log_viewer.py` |
| ダイアログ起動と保存処理 | `app/ui/tray.py` |
| 作業セッション用SQLiteスキーマ | `app/infra/logger.py` |

