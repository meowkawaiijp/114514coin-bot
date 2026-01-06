import json
import os
from typing import Dict, Any, Optional
from dataclasses import dataclass, asdict

CONFIG_FILE = "data/config.json"
USER_CONFIG_FILE = "data/user_config.json"

@dataclass
class ChannelConfig:
    channel_id: int
    guild_id: Optional[int] = None # 参考情報として保持
    window_minutes: int = 5
    threshold_percent: float = 2.0
    monitoring_enabled: bool = False
    symbol: str = "114514USDT" # デフォルト
    rename_enabled: bool = False # チャンネル名の自動更新

@dataclass
class UserConfig:
    user_id: int
    window_minutes: int = 5
    threshold_percent: float = 2.0
    monitoring_enabled: bool = False
    symbol: str = "114514USDT"
    holdings: float = 0.0 # 保有枚数

class ConfigStore:
    def __init__(self):
        # channel_id -> ChannelConfig
        self.configs: Dict[int, ChannelConfig] = {}
        # user_id -> UserConfig
        self.user_configs: Dict[int, UserConfig] = {}
        
        self.load()
        self.load_users()

    def load(self):
        if not os.path.exists(CONFIG_FILE):
            return

        try:
            with open(CONFIG_FILE, "r", encoding="utf-8") as f:
                data = json.load(f)
                
                for key_str, config_data in data.items():
                    channel_id = config_data.get("channel_id")
                    
                    if channel_id:
                         cid = int(channel_id)
                         self.configs[cid] = ChannelConfig(
                             channel_id=cid,
                             guild_id=int(key_str) if key_str.isdigit() else None,
                             window_minutes=config_data.get("window_minutes", 5),
                             threshold_percent=config_data.get("threshold_percent", 2.0),
                             monitoring_enabled=config_data.get("monitoring_enabled", False),
                             symbol=config_data.get("symbol", "114514USDT"),
                             rename_enabled=config_data.get("rename_enabled", False)
                         )
                    elif key_str.isdigit():
                        cid = int(key_str)
                        self.configs[cid] = ChannelConfig(
                             channel_id=cid,
                             guild_id=config_data.get("guild_id"),
                             window_minutes=config_data.get("window_minutes", 5),
                             threshold_percent=config_data.get("threshold_percent", 2.0),
                             monitoring_enabled=config_data.get("monitoring_enabled", False),
                             symbol=config_data.get("symbol", "114514USDT"),
                             rename_enabled=config_data.get("rename_enabled", False)
                         )

        except Exception as e:
            print(f"Error loading config: {e}")

    def load_users(self):
        if not os.path.exists(USER_CONFIG_FILE):
            return

        try:
            with open(USER_CONFIG_FILE, "r", encoding="utf-8") as f:
                data = json.load(f)
                for uid_str, config_data in data.items():
                    uid = int(uid_str)
                    self.user_configs[uid] = UserConfig(
                        user_id=uid,
                        window_minutes=config_data.get("window_minutes", 5),
                        threshold_percent=config_data.get("threshold_percent", 2.0),
                        monitoring_enabled=config_data.get("monitoring_enabled", False),
                        symbol=config_data.get("symbol", "114514USDT"),
                        holdings=config_data.get("holdings", 0.0)
                    )
        except Exception as e:
            print(f"Error loading user config: {e}")

    def save(self):
        data = {str(cid): asdict(cfg) for cid, cfg in self.configs.items()}
        try:
            os.makedirs(os.path.dirname(CONFIG_FILE), exist_ok=True)
            with open(CONFIG_FILE, "w", encoding="utf-8") as f:
                json.dump(data, f, indent=2)
        except Exception as e:
            print(f"Error saving config: {e}")

    def save_users(self):
        data = {str(uid): asdict(cfg) for uid, cfg in self.user_configs.items()}
        try:
            os.makedirs(os.path.dirname(USER_CONFIG_FILE), exist_ok=True)
            with open(USER_CONFIG_FILE, "w", encoding="utf-8") as f:
                json.dump(data, f, indent=2)
        except Exception as e:
            print(f"Error saving user config: {e}")

    def get_config(self, channel_id: int) -> ChannelConfig:
        if channel_id not in self.configs:
            self.configs[channel_id] = ChannelConfig(channel_id=channel_id)
            self.save()
        return self.configs[channel_id]
    
    def get_user_config(self, user_id: int) -> UserConfig:
        if user_id not in self.user_configs:
            self.user_configs[user_id] = UserConfig(user_id=user_id)
            self.save_users()
        return self.user_configs[user_id]

    def update_config(self, channel_id: int, **kwargs):
        config = self.get_config(channel_id)
        for key, value in kwargs.items():
            if hasattr(config, key):
                setattr(config, key, value)
        self.save()

    def update_user_config(self, user_id: int, **kwargs):
        config = self.get_user_config(user_id)
        for key, value in kwargs.items():
            if hasattr(config, key):
                setattr(config, key, value)
        self.save_users()

config_store = ConfigStore()
