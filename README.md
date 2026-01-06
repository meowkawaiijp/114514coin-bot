# MEXC 114514 Coin Monitor Bot

MEXCの `114514/USDT` (または指定した通貨ペア) の価格変動を監視し、Discordに通知するBotです。
JPY換算価格（参考値）の表示や、チャート表示、保有資産の計算機能も備えています。

## 主な機能

- **価格監視**: 指定された時間窓（例: 5分）での価格変動率を監視します。
- **通知**: 変動率が閾値（例: 2%）を超えた場合にDiscordチャンネルまたはDMに通知します。
- **チャンネル名更新**: 監視対象の価格をDiscordのチャンネル名にリアルタイム反映（更新頻度はAPI制限に依存）させることができます。
- **DM通知**: 個人設定に基づき、Direct Messageで価格変動通知を受け取れます。
- **資産計算**: 保有枚数を入力すると、現在のレートで円換算/ドル換算した評価額を計算します。
- **チャート表示**: `/status` コマンドで直近の価格推移をチャート画像で表示します。
- **JPY換算**: `USD/JPY` レートを自動取得し、USDTペアの価格を日本円換算して表示します。

## セットアップ

### 1. 前提条件
- Python 3.9以上
- Discord Bot Token

### 2. インストール
```bash
# リポジトリのクローン（またはダウンロード）
git clone <repository_url>
cd <repository_directory>

# 依存関係のインストール
pip install -r requirements.txt
```

### 3. 設定
1. プロジェクトルートに `.env` ファイルを作成します。
2. `.env` ファイルにDiscord Bot Tokenを設定します。
   ```env
   DISCORD_TOKEN=your_discord_bot_token_here
   ```

### 4. 起動
```bash
python -m bot.main
```

## 使い方（Discordコマンド）

Botをサーバーに招待した後、以下のスラッシュコマンドが使用できます。

### 📡 チャンネル設定・監視 (`/config`, `/monitor`)
サーバーのチャンネルに対する設定です。実行には「チャンネルの管理」権限が必要です。

- **/config set**
  - 監視設定を変更します。
  - パラメータ:
    - `window_minutes`: 変動率を判定する時間幅（分）。デフォルト5分。
    - `threshold_percent`: 通知トリガーとなる変動率（%）。デフォルト2.0%。
    - `symbol`: 監視対象（デフォルト `114514USDT`）。MEXCに存在するペアを指定可能。
    - `rename`: チャンネル名に現在価格を表示するか (`True`/`False`)。
  - 例: `/config set window_minutes:10 threshold_percent:3 symbol:BTCUSDT rename:True`

- **/config show**
  - 現在のチャンネル設定を表示します。

- **/monitor start**
  - このチャンネルでの監視を開始します。

- **/monitor stop**
  - このチャンネルでの監視を停止します。

### 📩 個人通知設定 (`/dm`)
BotからDMで通知を受け取るための個人設定です。サーバー設定とは独立して動作します。

- **/dm config**
  - 個人通知の設定を変更します。
  - パラメータ: `window_minutes`, `threshold_percent`, `symbol`, `holdings` (保有枚数)
  - 保有枚数を設定しておくと、通知時に資産価値もあわせて表示されます。

- **/dm start**
  - DMでの監視通知を開始します。

- **/dm stop**
  - DMでの監視通知を停止します。

- **/dm show**
  - 現在の個人設定を表示します。

### 🛠️ ツール・状態確認 (`/status`, `/calc`)

- **/status**
  - 現在の価格、N分前の価格、変動率を表示します。
  - 直近の価格推移チャートも表示されます。

- **/calc**
  - 保有コイン数を日本円/米ドルに換算します。
  - パラメータ: `amount` (枚数)
  - 例: `/calc amount:10000`

## ファイル構成
- `bot/`: ソースコード
  - `main.py`: エントリーポイント
  - `commands.py`: コマンド定義
  - `monitor.py`: 監視ロジック
  - `mexc_api.py`: MEXC APIクライアント
  - `config_store.py`: 設定管理
  - `exchange_rate.py`: 為替レート取得
- `data/`: 設定ファイル保存場所 (`config.json`, `user_config.json` が生成されます)

## 注意事項
- JPY価格は外部APIから取得したUSD/JPYレートに基づく参考値です。
- Botを再起動すると、メモリ上の価格履歴はリセットされます（再起動直後は履歴不足のため変動率判定ができない場合があります）。
