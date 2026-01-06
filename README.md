# MEXC 114514 Coin Monitor Bot

MEXCの `114514/USDT` 価格変動を監視し、Discordに通知するBotです。
JPY換算価格（参考値）も併記します。

## 機能
- **価格監視**: 指定された時間窓（例: 5分）での価格変動率を監視します。
- **通知**: 変動率が閾値（例: 2%）を超えた場合にDiscordチャンネルに通知します。
- **設定変更**: Discordのスラッシュコマンドを使用して、監視設定（時間窓、閾値、通知チャンネル）を変更できます。
- **JPY換算**: `114514/JPY` ペアはMEXCに存在しないため、`USD/JPY` レートを自動取得して換算表示します。

## セットアップ

### 1. 前提条件
- Python 3.9以上
- Discord Bot Token

### 2. インストール
```bash
# リポジトリのクローン（またはダウンロード）
# 依存関係のインストール
pip install -r requirements.txt
```

### 3. 設定
1. `env.example` を `.env` にリネームまたはコピーします。
2. `.env` ファイルを開き、Discord Bot Tokenを設定します。
   ```
   DISCORD_TOKEN=your_discord_bot_token_here
   ```

### 4. 起動
```bash
python -m bot.main
```

## 使い方（Discordコマンド）

Botをサーバーに招待した後、以下のスラッシュコマンドが使用できます。

### 設定コマンド
- `/config set`
  - 監視設定を変更します。
  - パラメータ:
    - `window_minutes`: 変動率を判定する時間幅（分）。デフォルト5分。
    - `threshold_percent`: 通知トリガーとなる変動率（%）。デフォルト2.0%。
    - `channel`: 通知を送信するチャンネル。
    - `symbol`: 監視対象（デフォルト `114514USDT`）。
  - 例: `/config set window_minutes:10 threshold_percent:3 channel:#general`

- `/config show`
  - 現在の設定を表示します。

### 監視制御
- `/monitor start`
  - 監視を開始します（先にチャンネル設定が必要です）。
- `/monitor stop`
  - 監視を停止します。
- `/status`
  - 現在の価格、N分前の価格、変動率を手動で確認します。

## ファイル構成
- `bot/`: ソースコード
  - `main.py`: エントリーポイント
  - `monitor.py`: 監視ロジック
  - `commands.py`: コマンド定義
  - `mexc_api.py`: MEXC APIクライアント
- `data/`: 設定ファイル保存場所（`config.json` が生成されます）

## 注意事項
- JPY価格は外部APIから取得したUSD/JPYレートに基づく参考値です。
- Botを停止すると、メモリ上の価格履歴はリセットされます（再起動直後は履歴不足のため変動率判定ができない場合があります）。
