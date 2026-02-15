"""
Service to update task board messages
"""
import discord
import logging
from typing import Optional
from config.settings import Settings
from discord_ui.embeds import create_task_board_embed
from discord_ui.select_menus import TaskFilterView

logger = logging.getLogger(__name__)


class MessageUpdater:
    """Updates task board messages in Discord channels"""
    
    def __init__(self):
        self.task_board_messages = {}  # {channel_id: message_id}
        self._bot = None
        self._db = None
    
    def set_bot(self, bot):
        """Set bot instance for accessing channels"""
        self._bot = bot
    
    def set_database(self, db):
        """Set database instance for persistence"""
        self._db = db
        self._load_message_ids()
    
    def _load_message_ids(self):
        """Load persisted message IDs from database"""
        if not self._db:
            return
        
        try:
            data = self._db.get_bot_metadata("task_board_messages")
            if data:
                # Convert string keys back to integers
                self.task_board_messages = {int(k): v for k, v in data.items()}
                logger.info(f"Loaded {len(self.task_board_messages)} task board message IDs from database")
        except Exception as e:
            logger.error(f"Failed to load message IDs: {e}")
    
    def _save_message_ids(self):
        """Persist message IDs to database"""
        if not self._db:
            return
        
        try:
            # Convert integer keys to strings for JSON compatibility
            data = {str(k): v for k, v in self.task_board_messages.items()}
            self._db.save_bot_metadata("task_board_messages", data)
        except Exception as e:
            logger.error(f"Failed to save message IDs: {e}")
    
    async def initialize_task_boards(self):
        """Initialize task boards in all configured channels"""
        if not self._bot:
            logger.error("Bot not set in MessageUpdater")
            return
        
        if Settings.TASK_CHANNEL is None:
            logger.warning("TASK_CHANNEL is not configured. Skipping task board initialization.")
            return
        
        for channel_id in [Settings.TASK_CHANNEL]:
            try:
                channel = self._bot.get_channel(channel_id)
                if not channel:
                    logger.warning(f"Channel {channel_id} not found")
                    continue
                
                # update_task_board handles both message reuse (edit) and creation.
                await self.update_task_board(channel)
                logger.info(f"Initialized task board in channel {channel_id}")
            except Exception as e:
                logger.error(f"Failed to initialize task board in channel {channel_id}: {e}")
    
    async def update_task_board(self, channel: discord.TextChannel, owner: str = None,
                                filter_status: str = None):
        """Update task board in a specific channel"""
        try:
            # Get all tasks
            from services.task_service import TaskService
            task_service = TaskService()
            
            tasks = task_service.get_all_tasks(owner=owner)
            
            embed = create_task_board_embed(tasks, owner=owner, filter_status=filter_status)
            
            # Find existing task board message or create new one
            message_id = self.task_board_messages.get(channel.id)
            
            view = TaskFilterView()
            
            if message_id:
                try:
                    message = await channel.fetch_message(message_id)
                    await message.edit(embed=embed, view=view)
                except discord.NotFound:
                    # Message was deleted, create new one
                    message = await channel.send(embed=embed, view=view)
                    self.task_board_messages[channel.id] = message.id
                    self._save_message_ids()
            else:
                message = await channel.send(embed=embed, view=view)
                self.task_board_messages[channel.id] = message.id
                self._save_message_ids()
            
            logger.info(f"Updated task board in channel {channel.id}")
        except Exception as e:
            logger.error(f"Failed to update task board in channel {channel.id}: {e}")
    
    async def update_all_task_boards(self):
        """Update task boards in all configured channels"""
        if not self._bot:
            logger.error("Bot not set in MessageUpdater")
            return
        
        if Settings.TASK_CHANNEL is None:
            return
        
        for channel_id in [Settings.TASK_CHANNEL]:
            try:
                channel = self._bot.get_channel(channel_id)
                if not channel:
                    logger.warning(f"Channel {channel_id} not found")
                    continue
                
                await self.update_task_board(channel)
            except Exception as e:
                logger.error(f"Failed to update task board in channel {channel_id}: {e}")
