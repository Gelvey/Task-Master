"""
Configuration settings for Discord bot
"""
import os
from typing import Dict, List
from dotenv import load_dotenv
import logging

# Load environment variables
load_dotenv()

logger = logging.getLogger(__name__)


class Settings:
    """Bot configuration settings"""
    
    # Discord settings
    DISCORD_BOT_TOKEN: str = os.getenv("DISCORD_BOT_TOKEN", "")
    TASK_CHANNELS: List[int] = []
    REMINDER_CHANNEL: int = None
    
    # User mapping (Discord ID -> Owner name)
    USER_MAPPING: Dict[int, str] = {}
    
    # Firebase settings
    FIREBASE_DATABASE_URL: str = os.getenv("FIREBASE_DATABASE_URL", "")
    USE_LOCAL_STORAGE: bool = os.getenv("USE_LOCAL_STORAGE", "false").lower() == "true"
    
    # Refresh intervals (seconds)
    TASK_BOARD_REFRESH_INTERVAL: int = int(os.getenv("TASK_BOARD_REFRESH_INTERVAL", "60"))
    REMINDER_CHECK_INTERVAL: int = int(os.getenv("REMINDER_CHECK_INTERVAL", "300"))
    
    # Logging
    LOG_LEVEL: str = os.getenv("LOG_LEVEL", "INFO")
    LOG_FILE: str = os.getenv("LOG_FILE", "discord_bot.log")
    
    @classmethod
    def load(cls):
        """Load and validate settings"""
        # Parse task channels
        task_channels_str = os.getenv("TASK_CHANNELS", "")
        if task_channels_str:
            try:
                cls.TASK_CHANNELS = [int(ch.strip()) for ch in task_channels_str.split(",")]
            except ValueError:
                logger.error("Invalid TASK_CHANNELS format. Use comma-separated channel IDs.")
                cls.TASK_CHANNELS = []
        
        # Parse reminder channel
        reminder_channel_str = os.getenv("REMINDER_CHANNEL", "")
        if reminder_channel_str:
            try:
                cls.REMINDER_CHANNEL = int(reminder_channel_str)
            except ValueError:
                logger.error("Invalid REMINDER_CHANNEL format.")
        
        # Parse user mappings
        for key, value in os.environ.items():
            if key.startswith("DISCORD_USER_"):
                try:
                    discord_id = int(key.replace("DISCORD_USER_", ""))
                    cls.USER_MAPPING[discord_id] = value
                    logger.info(f"Mapped Discord user {discord_id} to owner '{value}'")
                except ValueError:
                    logger.warning(f"Invalid Discord user ID in {key}")
        
        # Validate required settings
        if not cls.DISCORD_BOT_TOKEN:
            raise ValueError("DISCORD_BOT_TOKEN is required")
        
        if not cls.TASK_CHANNELS:
            logger.warning("No TASK_CHANNELS configured. Bot will not display task boards.")
        
        if not cls.FIREBASE_DATABASE_URL and not cls.USE_LOCAL_STORAGE:
            logger.warning("No FIREBASE_DATABASE_URL and USE_LOCAL_STORAGE=false. Bot may not persist data.")
        
        logger.info(f"Loaded settings: {len(cls.USER_MAPPING)} user mappings, "
                   f"{len(cls.TASK_CHANNELS)} task channels")
    
    @classmethod
    def get_owner_for_user(cls, discord_user_id: int) -> str:
        """Get Task-Master owner name for Discord user ID"""
        return cls.USER_MAPPING.get(discord_user_id, f"user_{discord_user_id}")
    
    @classmethod
    def get_discord_user_for_owner(cls, owner: str) -> int:
        """Get Discord user ID for Task-Master owner name (reverse lookup)"""
        for discord_id, owner_name in cls.USER_MAPPING.items():
            if owner_name == owner:
                return discord_id
        return None


# Load settings on module import
Settings.load()
