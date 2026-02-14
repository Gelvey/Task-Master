"""
Task-Master Discord Bot
Main entry point
"""
import discord
from discord.ext import commands, tasks
import logging
import asyncio
from config.settings import Settings
from services.message_updater import MessageUpdater
from services.reminder_service import ReminderService
from discord_ui.select_menus import TaskFilterView
from utils.logger import setup_logging

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
message_updater = MessageUpdater()
reminder_service = ReminderService()


@bot.event
async def on_ready():
    """Bot startup event"""
    logger.info(f"Bot logged in as {bot.user.name} (ID: {bot.user.id})")
    logger.info(f"Connected to {len(bot.guilds)} guild(s)")
    
    # Set bot instance in services
    message_updater.set_bot(bot)
    reminder_service.set_bot(bot)
    
    # Register persistent views
    bot.add_view(TaskFilterView())
    
    # Initialize task boards
    await message_updater.initialize_task_boards()
    
    # Start background tasks
    task_board_updater.start()
    reminder_checker.start()
    
    logger.info("Bot is ready!")


@tasks.loop(seconds=Settings.TASK_BOARD_REFRESH_INTERVAL)
async def task_board_updater():
    """Background task to periodically update task boards"""
    try:
        await message_updater.update_all_task_boards()
        logger.debug("Task boards updated")
    except Exception as e:
        logger.error(f"Error updating task boards: {e}")


@tasks.loop(seconds=Settings.REMINDER_CHECK_INTERVAL)
async def reminder_checker():
    """Background task to check for task reminders"""
    try:
        await reminder_service.check_and_send_reminders()
        logger.debug("Checked task reminders")
    except Exception as e:
        logger.error(f"Error checking reminders: {e}")


@task_board_updater.before_loop
async def before_task_board_updater():
    """Wait until bot is ready before starting updater"""
    await bot.wait_until_ready()


@reminder_checker.before_loop
async def before_reminder_checker():
    """Wait until bot is ready before starting reminder checker"""
    await bot.wait_until_ready()


@bot.command(name="taskboard")
@commands.has_permissions(administrator=True)
async def create_taskboard(ctx):
    """Admin command to manually create a task board in current channel"""
    if ctx.channel.id not in Settings.TASK_CHANNELS:
        await ctx.send("❌ This channel is not configured as a task channel.")
        return
    
    await message_updater.update_task_board(ctx.channel)
    await ctx.send("✅ Task board created/updated!", delete_after=5)
    await ctx.message.delete()


@bot.command(name="refresh")
async def refresh_taskboard(ctx):
    """Command to manually refresh the task board"""
    if ctx.channel.id not in Settings.TASK_CHANNELS:
        await ctx.send("❌ This channel is not configured as a task channel.")
        return
    
    await message_updater.update_task_board(ctx.channel)
    await ctx.send("✅ Task board refreshed!", delete_after=5)
    await ctx.message.delete(delay=5)


@bot.command(name="help")
async def help_command(ctx):
    """Show help information"""
    embed = discord.Embed(
        title="📋 Task-Master Discord Bot Help",
        description="Task management bot integrated with Task-Master database",
        color=discord.Color.blue()
    )
    
    embed.add_field(
        name="Task Board",
        value="The task board shows all your tasks in a persistent message. "
              "It updates automatically every minute.",
        inline=False
    )
    
    embed.add_field(
        name="Adding Tasks",
        value="Click the **➕ Add Task** button and fill out the form. "
              "Set a deadline, priority, description, and URL (all optional).",
        inline=False
    )
    
    embed.add_field(
        name="Editing Tasks",
        value="Click **✏️ Edit Task**, enter the task name, and update the details.",
        inline=False
    )
    
    embed.add_field(
        name="Deleting Tasks",
        value="Click **🗑️ Delete Task** and enter the task name to delete.",
        inline=False
    )
    
    embed.add_field(
        name="Status Changes",
        value="Use **✅ Mark Complete** or **🔄 Mark In Progress** buttons "
              "to change task status.",
        inline=False
    )
    
    embed.add_field(
        name="Filtering",
        value="Use the dropdown menu to filter tasks by status "
              "(All, To Do, In Progress, Complete).",
        inline=False
    )
    
    embed.add_field(
        name="Reminders",
        value=f"You'll receive reminders in <#{Settings.REMINDER_CHANNEL}> "
              "when task deadlines are within 24 hours.",
        inline=False
    )
    
    embed.add_field(
        name="Commands",
        value="`!help` - Show this help message\n"
              "`!refresh` - Manually refresh the task board\n"
              "`!taskboard` - (Admin) Create a new task board",
        inline=False
    )
    
    await ctx.send(embed=embed)


@bot.event
async def on_command_error(ctx, error):
    """Handle command errors"""
    if isinstance(error, commands.MissingPermissions):
        await ctx.send("❌ You don't have permission to use this command.")
    elif isinstance(error, commands.CommandNotFound):
        pass  # Ignore unknown commands
    else:
        logger.error(f"Command error: {error}")
        await ctx.send(f"❌ An error occurred: {str(error)}")


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
