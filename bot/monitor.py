import asyncio
import time
import io
from collections import deque
from typing import Dict, Deque, Tuple, Optional, List, Union
from bot.mexc_api import mexc_api
from bot.exchange_rate import exchange_rate_api
from bot.config_store import config_store, ChannelConfig, UserConfig

class PriceMonitor:
    def __init__(self):
        # symbol -> deque[(timestamp, price)]
        self.price_history: Dict[str, Deque[Tuple[float, float]]] = {}
        
        self.last_check_time = 0
        self.running = False
        
        # 通知クールダウン: channel_id (or user_id) -> last_notification_time
        # チャンネルごと、ユーザーごとに通知を管理
        # user_id は正の整数、channel_id も正の整数だが、重複する可能性は低い（Snowflake IDはユニーク）
        # ただし厳密には分けたほうが安全だが、DiscordのID体系では衝突しない。
        self.cooldowns: Dict[int, float] = {}
        self.cooldown_seconds = 60 # 連投防止時間
        
        # チャンネル名更新のレート制限管理
        self.last_rename_times: Dict[int, float] = {}
        self.rename_interval = 600 # 10分に1回（Discordの制限対策）

    async def start(self, bot):
        self.running = True
        print("Starting PriceMonitor...")
        while self.running:
            try:
                await self.tick(bot)
            except Exception as e:
                print(f"Error in monitor loop: {e}")
            
            await asyncio.sleep(15) # 15秒ごとにチェック

    async def tick(self, bot):
        # 1. アクティブな設定から必要なシンボルを収集
        active_symbols = set()
        for config in config_store.configs.values():
            if config.monitoring_enabled or config.rename_enabled:
                active_symbols.add(config.symbol)
        
        for u_config in config_store.user_configs.values():
            if u_config.monitoring_enabled:
                active_symbols.add(u_config.symbol)
        
        if not active_symbols:
            return

        # 2. 価格取得
        current_prices = {}
        for symbol in active_symbols:
            price = await mexc_api.get_price(symbol)
            if price is not None:
                current_prices[symbol] = price
                self._add_history(symbol, price)
        
        # 3a. チャンネル設定に基づいて判定
        for channel_id, config in config_store.configs.items():
            symbol = config.symbol
            if symbol not in current_prices:
                continue

            current_price = current_prices[symbol]
            
            # チャンネル名の更新
            if config.rename_enabled:
                await self._update_channel_name(bot, channel_id, config, current_price)

            if not config.monitoring_enabled:
                continue

            past_price = self._get_price_n_minutes_ago(symbol, config.window_minutes)
            if past_price is None:
                continue 
            
            change_percent = ((current_price - past_price) / past_price) * 100
            
            if abs(change_percent) >= config.threshold_percent:
                await self._notify(bot, channel_id, config, current_price, past_price, change_percent, is_user=False)

        # 3b. ユーザー設定に基づいて判定（DM通知）
        for user_id, u_config in config_store.user_configs.items():
            if not u_config.monitoring_enabled:
                continue

            symbol = u_config.symbol
            if symbol not in current_prices:
                continue

            current_price = current_prices[symbol]
            past_price = self._get_price_n_minutes_ago(symbol, u_config.window_minutes)
            
            if past_price is None:
                continue
            
            change_percent = ((current_price - past_price) / past_price) * 100
            
            if abs(change_percent) >= u_config.threshold_percent:
                await self._notify(bot, user_id, u_config, current_price, past_price, change_percent, is_user=True)

    def _add_history(self, symbol: str, price: float):
        now = time.time()
        if symbol not in self.price_history:
            self.price_history[symbol] = deque()
        
        queue = self.price_history[symbol]
        queue.append((now, price))
        
        # 古い履歴（最大60分保持あれば十分）を削除
        cutoff = now - 3600
        while queue and queue[0][0] < cutoff:
            queue.popleft()

    def _get_price_n_minutes_ago(self, symbol: str, minutes: int) -> Optional[float]:
        if symbol not in self.price_history:
            return None
            
        queue = self.price_history[symbol]
        if not queue:
            return None
            
        now = time.time()
        target_time = now - (minutes * 60)
        
        # 最も近い時刻を探す
        closest_price = None
        min_diff = float('inf')
        
        for ts, price in queue:
            diff = abs(ts - target_time)
            if diff < min_diff:
                min_diff = diff
                closest_price = price
            else:
                if ts > target_time: 
                     break
        
        if min_diff > 60:
            return None
            
        return closest_price

    def get_recent_history(self, symbol: str) -> List[Tuple[float, float]]:
        if symbol not in self.price_history:
            return []
        history = list(self.price_history[symbol])
        return history[-100:] if len(history) > 100 else history

    async def _notify(self, bot, target_id: int, config: Union[ChannelConfig, UserConfig], current_price: float, past_price: float, change_percent: float, is_user: bool = False):
        now = time.time()
        last_notified = self.cooldowns.get(target_id, 0)
        
        if now - last_notified < self.cooldown_seconds:
            return

        target = None
        if is_user:
            try:
                target = await bot.fetch_user(target_id)
            except Exception:
                target = None
        else:
            target = bot.get_channel(target_id)

        if not target:
            return

        self.cooldowns[target_id] = now
        
        direction_emoji = "🚀 上昇" if change_percent > 0 else "📉 下落"
        usd_jpy = await exchange_rate_api.get_usd_jpy_rate()
        price_jpy = current_price * usd_jpy
        past_price_jpy = past_price * usd_jpy
        
        # メッセージ作成
        embed_dict = {
            "title": f"{config.symbol} {direction_emoji} {abs(change_percent):.2f}%",
            "description": f"{config.window_minutes}分前と比較して閾値({config.threshold_percent}%)を超えました。",
            "color": 0x00ff00 if change_percent > 0 else 0xff0000,
            "fields": [
                {
                    "name": "現在価格",
                    "value": f"${current_price:.6f} (約¥{price_jpy:.4f})",
                    "inline": True
                },
                {
                    "name": f"{config.window_minutes}分前",
                    "value": f"${past_price:.6f} (約¥{past_price_jpy:.4f})",
                    "inline": True
                },
            ],
            "footer": {"text": "MEXC Monitor Bot (DM通知)" if is_user else "MEXC Monitor Bot"}
        }

        # 個人通知で保有数が設定されている場合、資産額を表示
        if is_user and hasattr(config, 'holdings') and config.holdings > 0:
            total_jpy = config.holdings * price_jpy
            total_usd = config.holdings * current_price
            
            past_total_jpy = config.holdings * past_price_jpy
            diff_jpy = total_jpy - past_total_jpy
            diff_sign = "+" if diff_jpy >= 0 else ""
            
            embed_dict["fields"].append({
                "name": "💰 保有資産",
                "value": f"¥{total_jpy:,.0f} (${total_usd:,.2f})\n(前比: {diff_sign}¥{diff_jpy:,.0f})",
                "inline": False
            })

        embed_dict["fields"].append({
            "name": "チャート",
            "value": f"[MEXC 114514/USDT](https://www.mexc.com/ja-JP/exchange/114514_USDT)",
            "inline": False
        })
        
        try:
            from discord import Embed, File
            discord_embed = Embed.from_dict(embed_dict)
            file = None
            
            # QuickChart (共通ロジック)
            history = self.get_recent_history(config.symbol)
            if len(history) > 2:
                try:
                    step = max(1, len(history) // 50)
                    chart_data = history[::step]
                    prices = [h[1] for h in chart_data]
                    labels = ["" for _ in chart_data]
                    
                    qc_config = {
                        "type": "line",
                        "data": {
                            "labels": labels,
                            "datasets": [{
                                "label": config.symbol,
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
                                "xAxes": [{"display": False}],
                                "yAxes": [{"display": True}]
                            }
                        }
                    }
                    
                    # URL生成ではなくPOSTで画像を取得する (URL長制限回避)
                    session = await mexc_api.get_session()
                    async with session.post("https://quickchart.io/chart", json={"chart": qc_config, "width": 500, "height": 300, "backgroundColor": "white"}) as resp:
                        if resp.status == 200:
                            image_data = await resp.read()
                            file = File(io.BytesIO(image_data), filename="chart.png")
                            discord_embed.set_image(url="attachment://chart.png")
                        else:
                            print(f"QuickChart error: {resp.status}")
                            
                except Exception as e:
                    print(f"Chart error: {e}")

            if file:
                await target.send(embed=discord_embed, file=file)
            else:
                await target.send(embed=discord_embed)
        except Exception as e:
            print(f"Error sending notification to {target_id}: {e}")

    async def _update_channel_name(self, bot, channel_id: int, config: ChannelConfig, price: float):
        now = time.time()
        last_rename = self.last_rename_times.get(channel_id, 0)
        
        if now - last_rename < self.rename_interval:
            return

        channel = bot.get_channel(channel_id)
        if not channel:
            return
            
        try:
            usd_jpy = await exchange_rate_api.get_usd_jpy_rate()
            price_jpy = price * usd_jpy
            
            # 設定された期間（window_minutes）の価格変動を表示
            past_price = self._get_price_n_minutes_ago(config.symbol, config.window_minutes)
            
            suffix = ""
            if past_price is not None:
                past_price_jpy = past_price * usd_jpy
                diff_jpy = price_jpy - past_price_jpy
                sign = "+" if diff_jpy >= 0 else ""
                suffix = f"({sign}¥{diff_jpy:.2f})"
            else:
                # 履歴不足時は現在価格を表示（あるいは収集中表示）
                suffix = f"(¥{price_jpy:.2f})"

            import re
            original_name = channel.name
            # 末尾の (...) を削除
            base_name = re.sub(r'\s*\([^)]+\)$', '', original_name)
            new_name = f"{base_name} {suffix}"
            
            if original_name != new_name:
                await channel.edit(name=new_name)
                self.last_rename_times[channel_id] = now
                
        except Exception as e:
            print(f"Error renaming channel {channel_id}: {e}")
            self.last_rename_times[channel_id] = now

monitor = PriceMonitor()
