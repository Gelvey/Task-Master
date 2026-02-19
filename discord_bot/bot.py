"""
Task-Master Discord Bot
Main entry point
"""
import asyncio
import discord
from discord.ext import commands, tasks
import logging
from config.settings import Settings
from services.reminder_service import ReminderService
from services.dashboard_service import DashboardService
from services.forum_sync_service import ForumSyncService
from utils.logger import setup_logging
from database.firebase_manager import DatabaseManager

# Setup logging
setup_logging()
logger = logging.getLogger(__name__)

# Bot setup with required intents
intents = discord.Intents.default()
intents.message_content = True
intents.guilds = True
intents.members = True

bot = commands.Bot(command_prefix="!", intents=intents)

# Services
reminder_service = ReminderService()
dashboard_service = DashboardService()
forum_sync_service = ForumSyncService()

# Database
db_manager = None
status_index = 0


def _build_status_messages(tasks_data):
    """Build rotating bot status lines from task data."""
    total = len(tasks_data)
    todo = sum(1 for t in tasks_data if getattr(t, "status", "") == "To Do")
    in_progress = sum(1 for t in tasks_data if getattr(
        t, "status", "") == "In Progress")
    complete = sum(1 for t in tasks_data if getattr(
        t, "status", "") == "Complete")
    critical = sum(1 for t in tasks_data if getattr(
        t, "colour", "") == "Important")

    if total == 0:
        return [
            "🧠 planning world domination",
            "✨ waiting for the first task",
        ]

    return [
        f"📋 {todo} To Do • 🔄 {in_progress} In Progress",
        f"✅ {complete}/{total} complete",
        f"🔥 {critical} critical on top",
    ]


async def refresh_bot_presence():
    """Refresh bot presence from current task state."""
    global status_index

    if not db_manager:
        return

    try:
        task_data = db_manager.load_tasks(Settings.TASKMASTER_USERNAME)
        status_messages = _build_status_messages(task_data)
        if not status_messages:
            status_messages = ["Task-Master online"]

        next_status = status_messages[status_index % len(status_messages)]
        status_index += 1

        await bot.change_presence(
            status=discord.Status.online,
            activity=discord.Activity(
                type=discord.ActivityType.watching,
                name=next_status,
            ),
        )
    except Exception as e:
        logger.warning(f"Failed to refresh bot presence: {e}")


@bot.event
async def on_ready():
    """Bot startup event"""
    global db_manager

    logger.info(f"Bot logged in as {bot.user.name} (ID: {bot.user.id})")
    logger.info(f"Connected to {len(bot.guilds)} guild(s)")

    # Initialize database
    db_manager = DatabaseManager(use_firebase=not Settings.USE_LOCAL_STORAGE)

    # Set bot instance and database in services
    reminder_service.set_bot(bot)
    reminder_service.set_database(db_manager)

    dashboard_service.set_bot(bot)
    dashboard_service.set_database(db_manager)

    forum_sync_service.set_bot(bot)
    forum_sync_service.set_database(db_manager)

    # Sync slash commands
    try:
        synced = await bot.tree.sync()
        logger.info(f"Synced {len(synced)} slash command(s)")
    except Exception as e:
        logger.error(f"Failed to sync commands: {e}")

    # Initialize forum/dashboard surfaces
    await dashboard_service.initialize_dashboard()
    await forum_sync_service.sync_from_database()

    # Start background tasks
    if not forum_sync_updater.is_running():
        forum_sync_updater.start()
    if not reminder_checker.is_running():
        reminder_checker.start()
    if Settings.BOT_STATUS_ENABLED and not status_updater.is_running():
        status_updater.start()

    await refresh_bot_presence()

    logger.info("Bot is ready!")


@tasks.loop(seconds=Settings.FORUM_SYNC_REFRESH_INTERVAL)
async def forum_sync_updater():
    """Background task to keep dashboard and forum threads in sync"""
    if not Settings.TASK_FORUM_CHANNEL:
        return
    try:
        await forum_sync_service.sync_from_database()
        await dashboard_service.update_dashboard()
    except Exception as e:
        logger.error(f"Error syncing forum/dashboard: {e}")


@tasks.loop(seconds=Settings.REMINDER_CHECK_INTERVAL)
async def reminder_checker():
    """Background task to check for task reminders"""
    try:
        await reminder_service.check_and_send_reminders()
        logger.debug("Checked task reminders")
    except Exception as e:
        logger.error(f"Error checking reminders: {e}")


@tasks.loop(seconds=Settings.BOT_STATUS_REFRESH_INTERVAL)
async def status_updater():
    """Background task to keep bot presence fresh and informative"""
    if not Settings.BOT_STATUS_ENABLED:
        return

    try:
        await refresh_bot_presence()
    except Exception as e:
        logger.error(f"Error updating bot status: {e}")


@forum_sync_updater.before_loop
async def before_forum_sync_updater():
    """Wait until bot is ready before starting forum sync"""
    await bot.wait_until_ready()


@reminder_checker.before_loop
async def before_reminder_checker():
    """Wait until bot is ready before starting reminder checker"""
    await bot.wait_until_ready()


@status_updater.before_loop
async def before_status_updater():
    """Wait until bot is ready before updating presence"""
    await bot.wait_until_ready()


@bot.event
async def on_message(message: discord.Message):
    """Keep dashboard channel read-only (except bot messages)"""
    if message.author.bot:
        return

    if Settings.is_dashboard_channel(message.channel.id):
        try:
            await message.delete()
        except Exception as e:
            logger.warning(
                f"Failed to delete message in dashboard channel: {e}")


@bot.event
async def on_thread_update(before: discord.Thread, after: discord.Thread):
    """Sync thread title edits back to task names"""
    if not Settings.TASK_FORUM_CHANNEL:
        return

    if after.parent_id != Settings.TASK_FORUM_CHANNEL:
        return

    if before.name != after.name:
        try:
            await forum_sync_service.handle_thread_rename(after)
            await dashboard_service.update_dashboard()
        except Exception as e:
            logger.error(
                f"Failed to sync thread rename '{before.name}' -> '{after.name}': {e}")


# Slash Commands

@bot.tree.command(name="help", description="Show help information about the Task-Master bot")
async def help_command(interaction: discord.Interaction):
    """Show help information"""
    embed = discord.Embed(
        title="📋 Task-Master Discord Bot Help",
        description="Task management bot integrated with Task-Master database",
        color=discord.Color.blue()
    )

    embed.add_field(
        name="Forum Mode",
        value="This bot runs in forum mode only: one thread per task in the configured task forum, "
              "plus an optional read-only dashboard channel.",
        inline=False
    )

    embed.add_field(
        name="Configure Tasks",
        value="Each task thread has an **⚙️ Configure Task** button at the top. "
              "Click it to update status, priority, owner, deadline, description, and URL in one modal.",
        inline=False
    )

    embed.add_field(
        name="Filter by Priority",
        value="In the forum search bar, type **🔴** for Important, **🟠** for Moderately Important, "
              "or **⚪** for Not Important/default tasks.",
        inline=False
    )

    embed.add_field(
        name="Manage Sub-tasks",
        value="Use the **➕ Add Sub-task** button to create a new sub-task. "
              "Select an existing sub-task from the dropdown to **✏️ Edit**, **✅ Toggle** its completion, "
              "or **🗑️ Delete** it (with confirmation).",
        inline=False
    )

    embed.add_field(
        name="Reminders",
        value=f"You'll receive reminders in <#{Settings.REMINDER_CHANNEL}> "
        "when task deadlines are within 24 hours.",
        inline=False
    )

    embed.add_field(
        name="Slash Commands",
        value="`/help` - Show this help message\n"
              "`/refresh` - Manually refresh forum threads and dashboard",
        inline=False
    )

    await interaction.response.send_message(
        embed=embed,
        ephemeral=True,
    )


@bot.tree.command(name="refresh", description="Manually refresh forum threads and dashboard")
async def refresh_taskboard(interaction: discord.Interaction):
    """Command to manually refresh forum threads/dashboard"""
    await interaction.response.defer(ephemeral=True)
    await forum_sync_service.sync_from_database()
    await dashboard_service.update_dashboard()
    msg = await interaction.followup.send(
        "✅ Forum threads and dashboard refreshed!",
        ephemeral=True,
    )
    if Settings.EPHEMERAL_DELETE_AFTER:
        async def _delete_later():
            await asyncio.sleep(Settings.EPHEMERAL_DELETE_AFTER)
            try:
                await msg.delete()
            except Exception:
                pass
        asyncio.create_task(_delete_later())


def main():
    """Main entry point"""
    try:
        logger.info("Starting Task-Master Discord Bot...")
        bot.run(Settings.DISCORD_BOT_TOKEN)
    except Exception as e:
        logger.error(f"Failed to start bot: {e}")
        raise


if __name__ == "__main__":
    main()
