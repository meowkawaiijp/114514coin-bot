import aiohttp
from typing import Optional

class ExchangeRateApi:
    def __init__(self):
        self.rate: Optional[float] = None
        self.last_updated: float = 0
        self.update_interval: int = 3600  # 1時間ごとに更新

    async def get_usd_jpy_rate(self) -> float:
        """
        USD/JPYのレートを取得します。キャッシュがあればそれを使います。
        """
        import time
        now = time.time()
        
        if self.rate is not None and (now - self.last_updated) < self.update_interval:
            return self.rate

        url = "https://api.exchangerate-api.com/v4/latest/USD"
        try:
            async with aiohttp.ClientSession() as session:
                async with session.get(url) as response:
                    if response.status == 200:
                        data = await response.json()
                        self.rate = data["rates"]["JPY"]
                        self.last_updated = now
                        return self.rate
        except Exception as e:
            print(f"Error fetching exchange rate: {e}")
        
        return self.rate if self.rate else 150.0  # フォールバック

exchange_rate_api = ExchangeRateApi()
