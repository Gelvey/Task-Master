"""
Configuration settings for Discord bot
"""
import os
from typing import Dict, List, Optional
from dotenv import load_dotenv
import logging

# Load environment variables
load_dotenv()

logger = logging.getLogger(__name__)


class Settings:
    """Bot configuration settings"""

    # Discord settings
    DISCORD_BOT_TOKEN: str = os.getenv("DISCORD_BOT_TOKEN", "")
    DASHBOARD_CHANNEL: Optional[int] = None
    TASK_FORUM_CHANNEL: Optional[int] = None
    REMINDER_CHANNEL: int = None

    # Task-Master settings
    TASKMASTER_USERNAME: str = os.getenv("TASKMASTER_USERNAME", "")
    OWNERS: List[str] = []

    # User mapping (Discord ID -> Owner name)
    USER_MAPPING: Dict[int, str] = {}

    # Firebase settings
    FIREBASE_DATABASE_URL: str = os.getenv("FIREBASE_DATABASE_URL", "")
    USE_LOCAL_STORAGE: bool = os.getenv(
        "USE_LOCAL_STORAGE", "false").lower() == "true"

    # Refresh intervals (seconds)
    FORUM_SYNC_REFRESH_INTERVAL: int = int(
        os.getenv("FORUM_SYNC_REFRESH_INTERVAL", os.getenv(
            "TASK_BOARD_REFRESH_INTERVAL", "60"))
    )
    REMINDER_CHECK_INTERVAL: int = int(
        os.getenv("REMINDER_CHECK_INTERVAL", "300"))

    # Logging
    LOG_LEVEL: str = os.getenv("LOG_LEVEL", "INFO")
    LOG_FILE: str = os.getenv("LOG_FILE", "discord_bot.log")

    @classmethod
    def load(cls):
        """Load and validate settings"""
        # Parse dashboard/forum channels for forum-only architecture
        dashboard_channel_str = os.getenv("DASHBOARD_CHANNEL", "").strip()
        if dashboard_channel_str:
            try:
                cls.DASHBOARD_CHANNEL = int(dashboard_channel_str)
            except ValueError:
                logger.error(
                    "Invalid DASHBOARD_CHANNEL format. Use a single channel ID.")
                cls.DASHBOARD_CHANNEL = None

        task_forum_channel_str = os.getenv("TASK_FORUM_CHANNEL", "").strip()
        if task_forum_channel_str:
            try:
                cls.TASK_FORUM_CHANNEL = int(task_forum_channel_str)
            except ValueError:
                logger.error(
                    "Invalid TASK_FORUM_CHANNEL format. Use a single forum channel ID.")
                cls.TASK_FORUM_CHANNEL = None

        # Parse owners
        owners_str = os.getenv("OWNERS", "")
        if owners_str:
            cls.OWNERS = owners_str.split()
            logger.info(f"Loaded {len(cls.OWNERS)} task owners: {cls.OWNERS}")

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
                    logger.info(
                        f"Mapped Discord user {discord_id} to owner '{value}'")
                except ValueError:
                    logger.warning(f"Invalid Discord user ID in {key}")

        # Validate required settings
        if not cls.DISCORD_BOT_TOKEN:
            raise ValueError("DISCORD_BOT_TOKEN is required")

        if not cls.TASKMASTER_USERNAME:
            logger.warning(
                "No TASKMASTER_USERNAME configured. Using 'default' as username.")
            cls.TASKMASTER_USERNAME = "default"

        if cls.TASK_FORUM_CHANNEL is None:
            logger.warning(
                "No TASK_FORUM_CHANNEL configured. Forum sync will be disabled.")

        if cls.DASHBOARD_CHANNEL is None:
            logger.warning(
                "No DASHBOARD_CHANNEL configured. Dashboard updates will be skipped.")

        if not cls.FIREBASE_DATABASE_URL and not cls.USE_LOCAL_STORAGE:
            logger.warning(
                "No FIREBASE_DATABASE_URL and USE_LOCAL_STORAGE=false. Bot may not persist data.")

        logger.info(f"Loaded settings: username='{cls.TASKMASTER_USERNAME}', "
                    f"{len(cls.OWNERS)} owners, {len(cls.USER_MAPPING)} user mappings")

    @classmethod
    def is_dashboard_channel(cls, channel_id: int) -> bool:
        """Check if a channel is the configured dashboard channel"""
        return cls.DASHBOARD_CHANNEL is not None and channel_id == cls.DASHBOARD_CHANNEL

    @classmethod
    def is_task_forum_channel(cls, channel_id: int) -> bool:
        """Check if a channel is the configured task forum channel"""
        return cls.TASK_FORUM_CHANNEL is not None and channel_id == cls.TASK_FORUM_CHANNEL

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
