import asyncio
import aiohttp
from typing import Dict, Optional, List

BASE_URL = "https://api.mexc.com"

class MexcApi:
    def __init__(self):
        self.session: Optional[aiohttp.ClientSession] = None

    async def get_session(self) -> aiohttp.ClientSession:
        if self.session is None or self.session.closed:
            self.session = aiohttp.ClientSession()
        return self.session

    async def close(self):
        if self.session and not self.session.closed:
            await self.session.close()

    async def get_price(self, symbol: str) -> Optional[float]:
        """
        指定されたシンボルの最新価格を取得します。
        symbol形式: '114514USDT' など
        """
        session = await self.get_session()
        url = f"{BASE_URL}/api/v3/ticker/price"
        params = {"symbol": symbol}
        
        try:
            async with session.get(url, params=params, timeout=10) as response:
                if response.status == 200:
                    data = await response.json()
                    # レスポンス形式: {"symbol": "114514USDT", "price": "0.000123"}
                    return float(data["price"])
                else:
                    print(f"Error fetching price for {symbol}: {response.status}")
                    return None
        except Exception as e:
            print(f"Exception fetching price for {symbol}: {e}")
            return None

    async def check_symbol_exists(self, symbol: str) -> bool:
        price = await self.get_price(symbol)
        return price is not None

# シングルトンインスタンスとして利用する場合
mexc_api = MexcApi()
