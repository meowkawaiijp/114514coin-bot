import discord
from discord import app_commands
from bot.config_store import config_store
from bot.monitor import monitor
from bot.mexc_api import mexc_api
from bot.exchange_rate import exchange_rate_api

def setup_commands(tree: app_commands.CommandTree, bot: discord.Client):
    
    # ----------------------------------------------------
    # /config (チャンネル設定)
    # ----------------------------------------------------
    config_group = app_commands.Group(name="config", description="Bot設定の管理（チャンネル用）")

    @config_group.command(name="set", description="このチャンネルの監視設定を変更します")
    @app_commands.describe(
        window_minutes="変動率判定の時間窓（分）",
        threshold_percent="通知する変動率の閾値（%）",
        symbol="監視するシンボル（例: 114514USDT）",
        rename="チャンネル名に価格を表示するか(True/False)"
    )
    async def config_set(interaction: discord.Interaction, 
                         window_minutes: int = None, 
                         threshold_percent: float = None, 
                         symbol: str = None,
                         rename: bool = None):
        
        channel_id = interaction.channel_id
        if not channel_id:
             await interaction.response.send_message("DMでは使用できません。", ephemeral=True)
             return

        # 権限チェック
        if interaction.guild and not interaction.user.guild_permissions.manage_channels:
             await interaction.response.send_message("このコマンドを実行するには権限(チャンネル管理)が必要です。", ephemeral=True)
             return
        
        updates = {}
        msg_parts = []
        
        if interaction.guild_id:
            updates["guild_id"] = interaction.guild_id

        if window_minutes is not None:
            updates["window_minutes"] = window_minutes
            msg_parts.append(f"時間窓: {window_minutes}分")
        
        if threshold_percent is not None:
            updates["threshold_percent"] = threshold_percent
            msg_parts.append(f"閾値: {threshold_percent}%")
            
        if symbol is not None:
            exists = await mexc_api.check_symbol_exists(symbol)
            if not exists:
                await interaction.response.send_message(f"シンボル `{symbol}` はMEXCに見つかりませんでした。", ephemeral=True)
                return
            updates["symbol"] = symbol
            msg_parts.append(f"監視シンボル: {symbol}")

        if rename is not None:
            updates["rename_enabled"] = rename
            status = "有効" if rename else "無効"
            msg_parts.append(f"チャンネル名自動更新: {status}")

        if not updates:
            await interaction.response.send_message("変更する項目を指定してください。", ephemeral=True)
            return

        config_store.update_config(channel_id, **updates)
        await interaction.response.send_message(f"このチャンネルの設定を更新しました:\n" + "\n".join(msg_parts))

    @config_group.command(name="show", description="このチャンネルの設定を表示します")
    async def config_show(interaction: discord.Interaction):
        channel_id = interaction.channel_id
        if not channel_id:
             await interaction.response.send_message("DMでは使用できません。", ephemeral=True)
             return

        # 権限チェック
        if interaction.guild and not interaction.user.guild_permissions.manage_channels:
             await interaction.response.send_message("このコマンドを実行するには権限(チャンネル管理)が必要です。", ephemeral=True)
             return

        config = config_store.get_config(channel_id)
        status_emoji = "✅ 稼働中" if config.monitoring_enabled else "zk 停止中"
        rename_emoji = "✅ ON" if config.rename_enabled else "zk OFF"

        embed = discord.Embed(title="このチャンネルの監視設定", color=0x3498db)
        embed.add_field(name="状態", value=status_emoji, inline=False)
        embed.add_field(name="監視シンボル", value=config.symbol, inline=True)
        embed.add_field(name="時間窓", value=f"{config.window_minutes}分", inline=True)
        embed.add_field(name="閾値", value=f"±{config.threshold_percent}%", inline=True)
        embed.add_field(name="チャンネル名更新", value=rename_emoji, inline=True)
        
        await interaction.response.send_message(embed=embed)

    tree.add_command(config_group)

    # ----------------------------------------------------
    # /dm (個人設定)
    # ----------------------------------------------------
    dm_group = app_commands.Group(name="dm", description="個人通知（DM）の設定管理")

    @dm_group.command(name="config", description="個人通知の設定を変更します")
    @app_commands.describe(
        window_minutes="変動率判定の時間窓（分）",
        threshold_percent="通知する変動率の閾値（%）",
        symbol="監視するシンボル（例: 114514USDT）",
        holdings="保有しているコインの枚数（通知時の資産計算用）"
    )
    async def dm_config(interaction: discord.Interaction, 
                        window_minutes: int = None, 
                        threshold_percent: float = None, 
                        symbol: str = None,
                        holdings: float = None):
        
        user_id = interaction.user.id
        updates = {}
        msg_parts = []
        
        if window_minutes is not None:
            updates["window_minutes"] = window_minutes
            msg_parts.append(f"時間窓: {window_minutes}分")
        
        if threshold_percent is not None:
            updates["threshold_percent"] = threshold_percent
            msg_parts.append(f"閾値: {threshold_percent}%")
            
        if symbol is not None:
            exists = await mexc_api.check_symbol_exists(symbol)
            if not exists:
                await interaction.response.send_message(f"シンボル `{symbol}` はMEXCに見つかりませんでした。", ephemeral=True)
                return
            updates["symbol"] = symbol
            msg_parts.append(f"監視シンボル: {symbol}")

        if holdings is not None:
            updates["holdings"] = holdings
            msg_parts.append(f"保有枚数: {holdings:,.4f}")

        if not updates and not config_store.get_user_config(user_id):
            await interaction.response.send_message("変更する項目を指定してください。", ephemeral=True)
            return

        config_store.update_user_config(user_id, **updates)
        
        # 現在設定を表示して完了
        config = config_store.get_user_config(user_id)
        msg_parts.insert(0, "✅ **個人設定を更新しました**")
        msg_parts.append(f"現在の設定: {config.symbol} | {config.window_minutes}分 | ±{config.threshold_percent}% | 保有: {config.holdings:,.4f}")
        
        await interaction.response.send_message("\n".join(msg_parts), ephemeral=True)

    @dm_group.command(name="start", description="個人通知（DM）を開始します")
    async def dm_start(interaction: discord.Interaction):
        user_id = interaction.user.id
        config_store.update_user_config(user_id, monitoring_enabled=True)
        config = config_store.get_user_config(user_id)
        await interaction.response.send_message(f"DMでの監視通知を開始しました。\n条件: {config.symbol}が{config.window_minutes}分で±{config.threshold_percent}%動いた場合", ephemeral=True)

    @dm_group.command(name="stop", description="個人通知（DM）を停止します")
    async def dm_stop(interaction: discord.Interaction):
        user_id = interaction.user.id
        config_store.update_user_config(user_id, monitoring_enabled=False)
        await interaction.response.send_message("DMでの監視通知を停止しました。", ephemeral=True)

    @dm_group.command(name="show", description="現在の個人設定を表示します")
    async def dm_show(interaction: discord.Interaction):
        user_id = interaction.user.id
        config = config_store.get_user_config(user_id)
        status = "✅ 稼働中" if config.monitoring_enabled else "zk 停止中"
        
        embed = discord.Embed(title="👤 個人監視設定 (DM)", color=0x9b59b6)
        embed.add_field(name="状態", value=status, inline=False)
        embed.add_field(name="監視シンボル", value=config.symbol, inline=True)
        embed.add_field(name="時間窓", value=f"{config.window_minutes}分", inline=True)
        embed.add_field(name="閾値", value=f"±{config.threshold_percent}%", inline=True)
        
        if config.holdings > 0:
            embed.add_field(name="保有枚数", value=f"{config.holdings:,.4f}", inline=True)
        
        await interaction.response.send_message(embed=embed, ephemeral=True)

    tree.add_command(dm_group)

    # ----------------------------------------------------
    # /monitor (チャンネル監視制御 - 既存)
    # ----------------------------------------------------
    monitor_group = app_commands.Group(name="monitor", description="監視の制御（チャンネル用）")

    @monitor_group.command(name="start", description="このチャンネルでの監視を開始します")
    async def monitor_start(interaction: discord.Interaction):
        channel_id = interaction.channel_id
        if not channel_id:
             await interaction.response.send_message("DMでは使用できません。", ephemeral=True)
             return

        # 権限チェック
        if interaction.guild and not interaction.user.guild_permissions.manage_channels:
             await interaction.response.send_message("このコマンドを実行するには権限(チャンネル管理)が必要です。", ephemeral=True)
             return

        config = config_store.get_config(channel_id)
        config_store.update_config(channel_id, monitoring_enabled=True)
        await interaction.response.send_message(f"監視を開始しました。{config.symbol}の変動をこのチャンネルに通知します。")

    @monitor_group.command(name="stop", description="このチャンネルでの監視を停止します")
    async def monitor_stop(interaction: discord.Interaction):
        channel_id = interaction.channel_id
        if not channel_id:
             await interaction.response.send_message("DMでは使用できません。", ephemeral=True)
             return

        # 権限チェック
        if interaction.guild and not interaction.user.guild_permissions.manage_channels:
             await interaction.response.send_message("このコマンドを実行するには権限(チャンネル管理)が必要です。", ephemeral=True)
             return

        config_store.update_config(channel_id, monitoring_enabled=False)
        await interaction.response.send_message("このチャンネルでの監視を停止しました。")

    tree.add_command(monitor_group)

    # /status コマンド
    @tree.command(name="status", description="現在の価格と変動状況を表示します")
    async def status(interaction: discord.Interaction):
        await interaction.response.defer()
        
        symbol = "114514USDT"
        window_minutes = 5
        threshold = 2.0
        
        # チャンネル設定があればそれを使用、なければ個人設定、なければデフォルト
        if interaction.channel_id:
            c_config = config_store.configs.get(interaction.channel_id)
            if c_config:
                symbol = c_config.symbol
                window_minutes = c_config.window_minutes
                threshold = c_config.threshold_percent
        
        # 明示的に個人設定が優先されるべきかは議論があるが、
        # /status は「今のコンテキスト」で見たいことが多いのでチャンネル優先、
        # DMなら個人設定を見るようにする
        if not interaction.guild_id: # DMの場合
            u_config = config_store.get_user_config(interaction.user.id)
            symbol = u_config.symbol
            window_minutes = u_config.window_minutes
            threshold = u_config.threshold_percent

        price = await mexc_api.get_price(symbol)
        if price is None:
            await interaction.followup.send(f"{symbol} の価格取得に失敗しました。")
            return

        past_price = monitor._get_price_n_minutes_ago(symbol, window_minutes)
        usd_jpy = await exchange_rate_api.get_usd_jpy_rate()
        price_jpy = price * usd_jpy
        
        embed = discord.Embed(title=f"{symbol} 現在状況", color=0x0099ff)
        embed.add_field(name="現在価格", value=f"${price:.6f}\n(約¥{price_jpy:.2f})", inline=True)
        
        if past_price:
            change_percent = ((price - past_price) / past_price) * 100
            emoji = "↗️" if change_percent > 0 else "↘️"
            embed.add_field(name=f"{window_minutes}分前の価格", value=f"${past_price:.6f}", inline=True)
            embed.add_field(name="変動率", value=f"{emoji} {change_percent:+.3f}%", inline=True)
        else:
            embed.add_field(name=f"{window_minutes}分前", value="データ収集中...", inline=True)
            
        embed.set_footer(text=f"閾値: ±{threshold}%")
        
        # チャート画像の生成
        history = monitor.get_recent_history(symbol)
        if len(history) > 2:
            try:
                # データを間引いてURL長を抑える（最大50点くらいに）
                step = max(1, len(history) // 50)
                chart_data = history[::step]
                
                prices = [h[1] for h in chart_data]
                labels = ["" for _ in chart_data] # ラベルは省略
                
                # QuickChart API URL生成
                # 背景透過、線グラフ、点なし
                qc_config = {
                    "type": "line",
                    "data": {
                        "labels": labels,
                        "datasets": [{
                            "label": symbol,
                            "data": prices,
                            "borderColor": "rgb(75, 192, 192)",
                            "borderWidth": 2,
                            "pointRadius": 0,
                            "fill": False
                        }]
                    },
                    "options": {
                        "legend": {"display": False},
                        "scales": {
                            "xAxes": [{"display": False}], # X軸非表示
                            "yAxes": [{"display": True}]
                        }
                    }
                }
                import json
                import urllib.parse
                chart_json = json.dumps(qc_config)
                chart_url = f"https://quickchart.io/chart?c={urllib.parse.quote(chart_json)}"
                embed.set_image(url=chart_url)
            except Exception as e:
                print(f"Chart generation error: {e}")

        await interaction.followup.send(embed=embed)

    # /calc コマンド
    @tree.command(name="calc", description="保有コイン数を日本円に換算します")
    @app_commands.describe(amount="保有しているコインの枚数")
    async def calc(interaction: discord.Interaction, amount: float):
        await interaction.response.defer()
        
        symbol = "114514USDT"
        
        # コンテキストに合わせてシンボルを決定
        if interaction.guild_id:
             if interaction.channel_id in config_store.configs:
                 symbol = config_store.configs[interaction.channel_id].symbol
        else:
             if interaction.user.id in config_store.user_configs:
                 symbol = config_store.user_configs[interaction.user.id].symbol

        price = await mexc_api.get_price(symbol)
        if price is None:
            await interaction.followup.send(f"{symbol} の価格取得に失敗しました。")
            return

        usd_jpy = await exchange_rate_api.get_usd_jpy_rate()
        price_jpy = price * usd_jpy
        
        total_jpy = amount * price_jpy
        total_usd = amount * price

        embed = discord.Embed(title="💰 資産計算", color=0xf1c40f)
        embed.add_field(name="保有枚数", value=f"{amount:,.0f} {symbol.replace('USDT', '')}", inline=False)
        embed.add_field(name="現在レート", value=f"1枚 = {price_jpy:.4f}円", inline=False)
        embed.add_field(name="評価額", value=f"**{total_jpy:,.0f} 円**\n(${total_usd:,.2f})", inline=False)
        
        await interaction.followup.send(embed=embed)
