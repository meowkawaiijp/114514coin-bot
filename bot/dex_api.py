import aiohttp
from typing import Optional, Dict, List, Any

BASE_URL = "https://api.dexscreener.com/latest/dex"

class DexApi:
    def __init__(self):
        self.session: Optional[aiohttp.ClientSession] = None

    async def get_session(self) -> aiohttp.ClientSession:
        if self.session is None or self.session.closed:
            self.session = aiohttp.ClientSession()
        return self.session

    async def close(self):
        if self.session and not self.session.closed:
            await self.session.close()

    async def search_pairs(self, query: str) -> List[Dict[str, Any]]:
        """
        シンボルまたはアドレスでペアを検索します。
        """
        session = await self.get_session()
        url = f"{BASE_URL}/search"
        params = {"q": query}
        
        try:
            async with session.get(url, params=params, timeout=10) as response:
                if response.status == 200:
                    data = await response.json()
                    return data.get("pairs", [])
                else:
                    print(f"Error fetching DexScreener data for {query}: {response.status}")
                    return []
        except Exception as e:
            print(f"Exception fetching DexScreener data for {query}: {e}")
            return []

    async def get_token_stats(self, query: str) -> Optional[Dict[str, Any]]:
        """
        検索結果の中から最も流動性が高いペアの情報を返します。
        """
        pairs = await self.search_pairs(query)
        if not pairs:
            return None
            
        # 流動性(USD)でソートして最大のものを取得
        # liquidityフィールドがない、またはusdがない場合は0として扱う
        sorted_pairs = sorted(
            pairs, 
            key=lambda p: float(p.get("liquidity", {}).get("usd", 0) or 0), 
            reverse=True
        )
        
        return sorted_pairs[0]

dex_api = DexApi()
