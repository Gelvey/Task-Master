"""
Service to sync tasks with Discord forum threads
"""
import logging
import discord
from config.settings import Settings

logger = logging.getLogger(__name__)


class ForumSyncService:
    """Synchronize DB tasks to forum threads and back"""

    def __init__(self):
        self._bot = None
        self._db = None
        self.task_to_thread = {}
        self.thread_to_task = {}

    def set_bot(self, bot):
        self._bot = bot

    def set_database(self, db):
        self._db = db
        self._load_mappings()

    def _load_mappings(self):
        if not self._db:
            return
        try:
            mappings = self._db.get_task_thread_mappings()
            self.task_to_thread = mappings.get("task_to_thread", {})
            self.thread_to_task = mappings.get("thread_to_task", {})
        except Exception as e:
            logger.error(f"Failed to load forum mappings: {e}")

    def _save_mappings(self):
        if not self._db:
            return
        try:
            self._db.save_task_thread_mappings(self.task_to_thread, self.thread_to_task)
        except Exception as e:
            logger.error(f"Failed to save forum mappings: {e}")

    def get_task_uuid_for_thread(self, thread_id: int):
        return self.thread_to_task.get(str(thread_id))

    def _task_content(self, task):
        lines = [
            f"**Status:** {task.status}",
            f"**Priority:** {task.colour}",
            f"**Owner:** {task.owner or 'Unassigned'}",
            f"**Deadline:** {task.deadline or 'None'}",
            "",
            f"**Description:** {task.description or '*No description*'}",
        ]
        if task.url:
            lines.append(f"**URL:** {task.url}")
        
        # Add subtasks section with progress bar
        if task.subtasks:
            lines.append("")
            lines.append(f"**Progress:** {task.progress_bar()}")
            lines.append("")
            lines.append("**Sub-tasks:**")
            for idx, subtask in enumerate(task.subtasks, 1):
                checkbox = "✅" if subtask.get('completed', False) else "☐"
                lines.append(f"{checkbox} {idx}. {subtask.get('name', 'Unnamed subtask')}")
        
        return "\n".join(lines)

    # Priority emoji constants
    PRIORITY_EMOJIS = {
        "Important": "🔴",
        "Moderately Important": "🟠",
        "Not Important": "⚪",
        "default": "⚪"
    }
    
    def _get_thread_name_with_priority(self, task):
        """Generate thread name with priority emoji prefix"""
        emoji = self.PRIORITY_EMOJIS.get(task.colour, "⚪")
        return f"{emoji} {task.name}"
    
    async def sync_from_database(self):
        if not self._bot or Settings.TASK_FORUM_CHANNEL is None:
            return

        forum_channel = self._bot.get_channel(Settings.TASK_FORUM_CHANNEL)
        if not isinstance(forum_channel, discord.ForumChannel):
            logger.warning(f"Channel {Settings.TASK_FORUM_CHANNEL} is not a forum channel")
            return

        from services.task_service import TaskService
        task_service = TaskService()
        tasks = task_service.get_all_tasks()

        for task in tasks:
            # Keep migration-safe fallback for legacy tasks while UUID backfill propagates.
            task_uuid = task.uuid or task.id or task.name
            if not task.uuid:
                logger.warning(f"Task '{task.name}' missing UUID during forum sync; using legacy fallback key.")
            thread = None
            thread_id = self.task_to_thread.get(task_uuid)
            
            # Migrate old mapping keys (name/id) to UUID to avoid duplicate thread creation.
            if not thread_id:
                for legacy_key in [task.id, task.name]:
                    if legacy_key and legacy_key in self.task_to_thread:
                        thread_id = self.task_to_thread.pop(legacy_key)
                        self.task_to_thread[task_uuid] = thread_id
                        self.thread_to_task[str(thread_id)] = task_uuid
                        self._save_mappings()
                        break

            if thread_id:
                thread = self._bot.get_channel(int(thread_id))
                if not isinstance(thread, discord.Thread):
                    try:
                        thread = await self._bot.fetch_channel(int(thread_id))
                    except Exception:
                        thread = None

            if not isinstance(thread, discord.Thread):
                thread_name = self._get_thread_name_with_priority(task)
                created = await forum_channel.create_thread(
                    name=thread_name,
                    content=self._task_content(task)
                )
                thread = created.thread
                self.task_to_thread[task_uuid] = str(thread.id)
                self.thread_to_task[str(thread.id)] = task_uuid
                self._save_mappings()
                logger.info(f"Created forum thread for task '{task.name}' ({task_uuid})")
                continue

            thread_name = self._get_thread_name_with_priority(task)
            if thread.name != thread_name:
                await thread.edit(name=thread_name)

            # Keep latest task snapshot in thread starter message where possible
            content = self._task_content(task)
            try:
                starter_message = await thread.fetch_message(thread.id)
                if starter_message.content != content:
                    await starter_message.edit(content=content)
            except Exception:
                # Fallback: post one sync snapshot if starter message isn't accessible
                await thread.send(content)

    async def handle_thread_rename(self, thread: discord.Thread):
        """Sync thread title changes back to database task name"""
        task_uuid = self.get_task_uuid_for_thread(thread.id)
        if not task_uuid:
            return
        # Strip priority emoji prefix from thread name before syncing
        thread_name = thread.name
        # Remove emoji prefix using PRIORITY_EMOJIS constants
        for emoji in self.PRIORITY_EMOJIS.values():
            if thread_name.startswith(emoji):
                thread_name = thread_name[len(emoji):].strip()
                break
        from services.task_service import TaskService
        task_service = TaskService()
        await task_service.update_task_name_by_uuid(task_uuid, thread_name)

    async def update_description_for_thread(self, thread_id: int, description: str):
        task_uuid = self.get_task_uuid_for_thread(thread_id)
        if not task_uuid:
            raise ValueError("This thread is not linked to a task")
        from services.task_service import TaskService
        task_service = TaskService()
        await task_service.update_task_description_by_uuid(task_uuid, description)
