"""
Service for checking and sending task deadline reminders
"""
import discord
import logging
from datetime import datetime, timedelta
from typing import List
from config.settings import Settings
from discord_ui.embeds import create_reminder_embed
from database.task_model import Task

logger = logging.getLogger(__name__)


class ReminderService:
    """Checks for upcoming task deadlines and sends reminders"""
    
    def __init__(self):
        self._bot = None
        self._db = None
        self.reminded_tasks = set()  # Track which tasks we've already reminded about
    
    def set_bot(self, bot):
        """Set bot instance"""
        self._bot = bot
    
    def set_database(self, db):
        """Set database instance for persistence"""
        self._db = db
        self._load_reminded_tasks()
    
    def _load_reminded_tasks(self):
        """Load persisted reminder tracking from database"""
        if not self._db:
            return
        
        try:
            data = self._db.get_bot_metadata("reminded_tasks")
            if data and isinstance(data, list):
                self.reminded_tasks = set(data)
                logger.info(f"Loaded {len(self.reminded_tasks)} reminded task records from database")
        except Exception as e:
            logger.error(f"Failed to load reminded tasks: {e}")
    
    def _save_reminded_tasks(self):
        """Persist reminder tracking to database"""
        if not self._db:
            return
        
        try:
            # Convert set to list for JSON serialization
            data = list(self.reminded_tasks)
            self._db.save_bot_metadata("reminded_tasks", data)
        except Exception as e:
            logger.error(f"Failed to save reminded tasks: {e}")
    
    async def check_and_send_reminders(self):
        """Check all tasks for upcoming deadlines and send reminders"""
        if not self._bot:
            logger.error("Bot not set in ReminderService")
            return
        
        if not Settings.REMINDER_CHANNEL:
            logger.warning("REMINDER_CHANNEL not configured, skipping reminders")
            return
        
        reminder_channel = self._bot.get_channel(Settings.REMINDER_CHANNEL)
        if not reminder_channel:
            logger.error(f"Reminder channel {Settings.REMINDER_CHANNEL} not found")
            return
        
        from services.task_service import TaskService
        task_service = TaskService()
        
        # Get all tasks
        all_tasks = task_service.get_all_tasks()
        
        for task in all_tasks:
            if task.status == "Complete":
                continue  # Skip completed tasks
            
            if not task.deadline_datetime:
                continue  # Skip tasks without deadlines
            
            # Find Discord user for this task's owner
            discord_user_id = Settings.get_discord_user_for_owner(task.owner)
            if not discord_user_id:
                continue  # No Discord user mapped for this owner
            
            # Check if deadline is within next 24 hours
            time_until_deadline = task.deadline_datetime - datetime.now()
            
            # Create unique reminder key
            reminder_key = f"{task.owner}:{task.id}:{task.deadline}"
            
            if time_until_deadline.total_seconds() > 0 and time_until_deadline < timedelta(hours=24):
                # Send reminder if we haven't already
                if reminder_key not in self.reminded_tasks:
                    await self._send_reminder(reminder_channel, task, discord_user_id)
                    self.reminded_tasks.add(reminder_key)
                    self._save_reminded_tasks()
                    logger.info(f"Sent reminder for task '{task.name}' to user {discord_user_id}")
            elif time_until_deadline.total_seconds() < 0:
                # Task is overdue, send overdue notification (once per day)
                overdue_key = f"{reminder_key}:overdue:{datetime.now().date()}"
                if overdue_key not in self.reminded_tasks:
                    await self._send_overdue_notification(reminder_channel, task, discord_user_id)
                    self.reminded_tasks.add(overdue_key)
                    self._save_reminded_tasks()
                    logger.info(f"Sent overdue notification for task '{task.name}' to user {discord_user_id}")
    
    async def _send_reminder(self, channel: discord.TextChannel, task: Task, discord_user_id: int):
        """Send a reminder for an upcoming task deadline"""
        try:
            user_mention = f"<@{discord_user_id}>"
            embed = create_reminder_embed(task, user_mention)
            await channel.send(content=user_mention, embed=embed)
        except Exception as e:
            logger.error(f"Failed to send reminder: {e}")
    
    async def _send_overdue_notification(self, channel: discord.TextChannel, task: Task, discord_user_id: int):
        """Send notification for overdue task"""
        try:
            user_mention = f"<@{discord_user_id}>"
            embed = create_reminder_embed(task, user_mention)
            embed.title = "⚠️ Task is OVERDUE"
            embed.color = discord.Color.red()
            await channel.send(content=user_mention, embed=embed)
        except Exception as e:
            logger.error(f"Failed to send overdue notification: {e}")
