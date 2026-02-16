"""
Task-Master Discord Bot
Main entry point
"""
import discord
from discord import app_commands
from discord.ext import commands, tasks
import logging
import asyncio
from config.settings import Settings
from services.reminder_service import ReminderService
from services.dashboard_service import DashboardService
from services.forum_sync_service import ForumSyncService
from discord_ui.modals import ConfigureTaskModal, ConfigureSubtaskModal
from discord_ui.buttons import ConfirmationButtons
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


@forum_sync_updater.before_loop
async def before_forum_sync_updater():
    """Wait until bot is ready before starting forum sync"""
    await bot.wait_until_ready()


@reminder_checker.before_loop
async def before_reminder_checker():
    """Wait until bot is ready before starting reminder checker"""
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
        value="Use **/configure** inside a task thread to update status, priority, owner, "
              "deadline, description, and URL in one modal.",
        inline=False
    )

    embed.add_field(
        name="Manage Sub-tasks",
        value="Use **/subtask <id>** to create/edit, **/subtask-toggle <id>** to toggle completion, "
              "and **/subtask-delete <id>** to delete (with confirmation).",
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
              "`/refresh` - Manually refresh forum threads and dashboard\n"
              "`/configure` - Configure task fields from inside a task thread\n"
              "`/subtask` - Create or edit a sub-task by numeric ID in a task thread\n"
              "`/subtask-toggle` - Toggle completion for a sub-task by ID\n"
              "`/subtask-delete` - Delete a sub-task by ID",
        inline=False
    )

    await interaction.response.send_message(embed=embed, ephemeral=True)


@bot.tree.command(name="refresh", description="Manually refresh forum threads and dashboard")
async def refresh_taskboard(interaction: discord.Interaction):
    """Command to manually refresh forum threads/dashboard"""
    await interaction.response.defer(ephemeral=True)
    await forum_sync_service.sync_from_database()
    await dashboard_service.update_dashboard()
    await interaction.followup.send("✅ Forum threads and dashboard refreshed!", ephemeral=True)


@bot.tree.command(name="configure", description="Configure this task thread (status, priority, owner, deadline, description, URL)")
async def configure_task(interaction: discord.Interaction):
    """Configure task fields from within a task thread"""
    if not Settings.TASK_FORUM_CHANNEL:
        await interaction.response.send_message(
            "❌ Forum mode is not enabled.",
            ephemeral=True
        )
        return

    if not isinstance(interaction.channel, discord.Thread) or interaction.channel.parent_id != Settings.TASK_FORUM_CHANNEL:
        await interaction.response.send_message(
            "❌ Use this command inside a task thread in the configured forum.",
            ephemeral=True
        )
        return

    task_uuid = forum_sync_service.get_task_uuid_for_thread(
        interaction.channel.id)
    if not task_uuid:
        await interaction.response.send_message("❌ This thread is not linked to a task.", ephemeral=True)
        return

    from services.task_service import TaskService
    task_service = TaskService()
    task = await task_service.get_task_by_uuid(task_uuid)
    if not task:
        await interaction.response.send_message("❌ Linked task was not found.", ephemeral=True)
        return

    await interaction.response.send_modal(ConfigureTaskModal(
        task_uuid=task_uuid,
        current_status=task.status,
        current_priority=task.colour,
        current_owner=task.owner or "",
        current_deadline=task.deadline or "",
        current_description=task.description or "",
        current_url=task.url or "",
    ))


@bot.tree.command(name="subtask", description="Create or edit a sub-task by numeric ID in this task thread")
@app_commands.describe(subtask_id="Numeric sub-task ID (e.g. 1)")
async def configure_subtask(interaction: discord.Interaction, subtask_id: int):
    """Create or edit a sub-task by numeric ID from within a task thread"""
    if subtask_id <= 0:
        await interaction.response.send_message("❌ Sub-task ID must be a positive integer.", ephemeral=True)
        return

    if not Settings.TASK_FORUM_CHANNEL:
        await interaction.response.send_message(
            "❌ Forum mode is not enabled.",
            ephemeral=True
        )
        return

    if not isinstance(interaction.channel, discord.Thread) or interaction.channel.parent_id != Settings.TASK_FORUM_CHANNEL:
        await interaction.response.send_message(
            "❌ Use this command inside a task thread in the configured forum.",
            ephemeral=True
        )
        return

    task_uuid = forum_sync_service.get_task_uuid_for_thread(
        interaction.channel.id)
    if not task_uuid:
        await interaction.response.send_message("❌ This thread is not linked to a task.", ephemeral=True)
        return

    from services.task_service import TaskService
    task_service = TaskService()
    task = await task_service.get_task_by_uuid(task_uuid)
    if not task:
        await interaction.response.send_message("❌ Linked task was not found.", ephemeral=True)
        return

    existing_subtask = await task_service.get_subtask_by_id(task_uuid, subtask_id)
    await interaction.response.send_modal(ConfigureSubtaskModal(
        task_uuid=task_uuid,
        subtask_id=subtask_id,
        existing_subtask=existing_subtask,
    ))


@bot.tree.command(name="subtask-toggle", description="Toggle completion for a sub-task by numeric ID in this task thread")
@app_commands.describe(subtask_id="Numeric sub-task ID (e.g. 1)")
async def toggle_subtask(interaction: discord.Interaction, subtask_id: int):
    """Toggle completion for a sub-task by numeric ID from within a task thread"""
    if subtask_id <= 0:
        await interaction.response.send_message("❌ Sub-task ID must be a positive integer.", ephemeral=True)
        return

    if not Settings.TASK_FORUM_CHANNEL:
        await interaction.response.send_message("❌ Forum mode is not enabled.", ephemeral=True)
        return

    if not isinstance(interaction.channel, discord.Thread) or interaction.channel.parent_id != Settings.TASK_FORUM_CHANNEL:
        await interaction.response.send_message(
            "❌ Use this command inside a task thread in the configured forum.",
            ephemeral=True
        )
        return

    task_uuid = forum_sync_service.get_task_uuid_for_thread(
        interaction.channel.id)
    if not task_uuid:
        await interaction.response.send_message("❌ This thread is not linked to a task.", ephemeral=True)
        return

    from services.task_service import TaskService
    task_service = TaskService()

    try:
        subtask = await task_service.toggle_subtask_by_id(task_uuid, subtask_id)
        await forum_sync_service.sync_from_database()
        await dashboard_service.update_dashboard()

        status = "complete" if subtask.get('completed') else "incomplete"
        await interaction.response.send_message(
            f"✅ Sub-task #{subtask_id} marked {status}.",
            ephemeral=True,
        )
    except ValueError as e:
        await interaction.response.send_message(f"❌ {str(e)}", ephemeral=True)
    except Exception as e:
        await interaction.response.send_message(f"❌ Error toggling sub-task: {str(e)}", ephemeral=True)


@bot.tree.command(name="subtask-delete", description="Delete a sub-task by numeric ID in this task thread")
@app_commands.describe(subtask_id="Numeric sub-task ID (e.g. 1)")
async def delete_subtask(interaction: discord.Interaction, subtask_id: int):
    """Delete a sub-task by numeric ID from within a task thread"""
    if subtask_id <= 0:
        await interaction.response.send_message("❌ Sub-task ID must be a positive integer.", ephemeral=True)
        return

    if not Settings.TASK_FORUM_CHANNEL:
        await interaction.response.send_message("❌ Forum mode is not enabled.", ephemeral=True)
        return

    if not isinstance(interaction.channel, discord.Thread) or interaction.channel.parent_id != Settings.TASK_FORUM_CHANNEL:
        await interaction.response.send_message(
            "❌ Use this command inside a task thread in the configured forum.",
            ephemeral=True
        )
        return

    task_uuid = forum_sync_service.get_task_uuid_for_thread(
        interaction.channel.id)
    if not task_uuid:
        await interaction.response.send_message("❌ This thread is not linked to a task.", ephemeral=True)
        return

    from services.task_service import TaskService
    task_service = TaskService()

    try:
        existing_subtask = await task_service.get_subtask_by_id(task_uuid, subtask_id)
        if not existing_subtask:
            await interaction.response.send_message(f"❌ Sub-task #{subtask_id} not found.", ephemeral=True)
            return

        view = ConfirmationButtons(
            timeout=45, requester_id=interaction.user.id)
        await interaction.response.send_message(
            f"⚠️ Confirm delete for sub-task #{subtask_id}: {existing_subtask.get('name', 'Unnamed sub-task')}?",
            ephemeral=True,
            view=view,
        )

        timed_out = await view.wait()
        if timed_out or view.value is None:
            await interaction.edit_original_response(content="⌛ Delete request timed out.", view=None)
            return

        if not view.value:
            await interaction.edit_original_response(content="❎ Delete cancelled.", view=None)
            return

        removed = await task_service.delete_subtask_by_id(task_uuid, subtask_id)
        await forum_sync_service.sync_from_database()
        await dashboard_service.update_dashboard()

        await interaction.edit_original_response(
            content=f"✅ Deleted sub-task #{subtask_id}: {removed.get('name', 'Unnamed sub-task')}.",
            view=None,
        )
    except Exception as e:
        if interaction.response.is_done():
            await interaction.edit_original_response(content=f"❌ Error deleting sub-task: {str(e)}", view=None)
        else:
            await interaction.response.send_message(f"❌ Error deleting sub-task: {str(e)}", ephemeral=True)


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
