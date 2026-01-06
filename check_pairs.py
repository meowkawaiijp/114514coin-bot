import asyncio
from bot.mexc_api import MexcApi

async def main():
    api = MexcApi()
    
    symbols = ["USDTJPY", "USDCJPY", "BTCJPY"]
    
    print("Checking JPY pairs on MEXC...")
    for symbol in symbols:
        exists = await api.check_symbol_exists(symbol)
        price = await api.get_price(symbol) if exists else "N/A"
        print(f"Symbol: {symbol}, Exists: {exists}, Price: {price}")
    
    await api.close()

if __name__ == "__main__":
    asyncio.run(main())
