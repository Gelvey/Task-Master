"""
Service for central dashboard message management
"""
import discord
import logging
from config.settings import Settings

logger = logging.getLogger(__name__)


class DashboardService:
    """Maintains a single central dashboard message"""

    def __init__(self):
        self._bot = None
        self._db = None
        self.dashboard_message_id = None

    def set_bot(self, bot):
        self._bot = bot

    def set_database(self, db):
        self._db = db
        self._load_dashboard_message_id()

    def _load_dashboard_message_id(self):
        if not self._db:
            return
        try:
            self.dashboard_message_id = self._db.get_bot_metadata("dashboard_message_id")
        except Exception as e:
            logger.error(f"Failed to load dashboard message id: {e}")

    def _save_dashboard_message_id(self):
        if not self._db:
            return
        try:
            self._db.save_bot_metadata("dashboard_message_id", self.dashboard_message_id)
        except Exception as e:
            logger.error(f"Failed to save dashboard message id: {e}")

    async def initialize_dashboard(self):
        """Ensure dashboard message exists and is up to date"""
        await self.update_dashboard()

    async def update_dashboard(self):
        """Update dashboard stats message"""
        if not self._bot or Settings.DASHBOARD_CHANNEL is None:
            return

        channel = self._bot.get_channel(Settings.DASHBOARD_CHANNEL)
        if not channel:
            logger.warning(f"Dashboard channel {Settings.DASHBOARD_CHANNEL} not found")
            return

        from services.task_service import TaskService
        from discord_ui.buttons import DashboardView
        task_service = TaskService()
        tasks = task_service.get_all_tasks()

        status_counts = {"To Do": 0, "In Progress": 0, "Complete": 0}
        for task in tasks:
            status_counts[task.status] = status_counts.get(task.status, 0) + 1

        embed = discord.Embed(
            title="📊 Task Master - Central Dashboard",
            description="High-level sync and task status overview.",
            color=discord.Color.blurple()
        )
        embed.add_field(name="Sync Status", value="✅ Online", inline=True)
        embed.add_field(name="Total Tasks", value=str(len(tasks)), inline=True)
        embed.add_field(name="To Do", value=str(status_counts.get("To Do", 0)), inline=True)
        embed.add_field(name="In Progress", value=str(status_counts.get("In Progress", 0)), inline=True)
        embed.add_field(name="Complete", value=str(status_counts.get("Complete", 0)), inline=True)
        embed.set_footer(text="Dashboard is bot-managed and read-only.")

        view = DashboardView()

        if self.dashboard_message_id:
            try:
                message = await channel.fetch_message(int(self.dashboard_message_id))
                await message.edit(embed=embed, view=view)
                return
            except (discord.NotFound, discord.Forbidden):
                pass

        message = await channel.send(embed=embed, view=view)
        self.dashboard_message_id = message.id
        self._save_dashboard_message_id()
