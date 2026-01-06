import discord
from discord import app_commands
import os
import asyncio
from dotenv import load_dotenv
from bot.commands import setup_commands
from bot.monitor import monitor
from bot.mexc_api import mexc_api

# .env読み込み
load_dotenv()

TOKEN = os.getenv("DISCORD_TOKEN")

class MexcBot(discord.Client):
    def __init__(self):
        intents = discord.Intents.default()
        super().__init__(intents=intents)
        self.tree = app_commands.CommandTree(self)

    async def setup_hook(self):
        # コマンドの登録
        setup_commands(self.tree, self)
        
        # グローバルコマンドとして同期（即時反映にはギルド指定が必要だが、汎用のためグローバルで）
        # 開発中は特定のギルドIDを指定してsyncすると早い
        # await self.tree.sync(guild=discord.Object(id=YOUR_GUILD_ID))
        await self.tree.sync()
        print("Commands synced.")
        
        # 監視タスク開始
        self.loop.create_task(monitor.start(self))

    async def on_ready(self):
        print(f'Logged in as {self.user} (ID: {self.user.id})')
        print('------')

    async def close(self):
        monitor.running = False
        await mexc_api.close()
        await super().close()

def main():
    if not TOKEN:
        print("Error: DISCORD_TOKEN is not set in .env")
        return

    bot = MexcBot()
    bot.run(TOKEN)

if __name__ == "__main__":
    main()
