"""
Discord modal forms for task input
"""
import asyncio
import discord
from discord import ui
from typing import Optional
import logging
from utils.validators import (
    validate_deadline,
    validate_priority,
    validate_status,
    validate_url,
    format_deadline_for_display,
)
from config.settings import Settings

logger = logging.getLogger(__name__)


async def _auto_delete(msg, delay: float):
    """Delete a message after a delay (background task)."""
    await asyncio.sleep(delay)
    try:
        await msg.delete()
    except Exception:
        pass


async def _send_ephemeral_reply(interaction: discord.Interaction, content: str):
    """Send an ephemeral message safely for modal interactions."""
    try:
        if interaction.response.is_done():
            msg = await interaction.followup.send(
                content,
                ephemeral=True,
            )
            if Settings.EPHEMERAL_DELETE_AFTER:
                asyncio.create_task(_auto_delete(
                    msg, Settings.EPHEMERAL_DELETE_AFTER))
        else:
            await interaction.response.send_message(
                content,
                ephemeral=True,
                delete_after=Settings.EPHEMERAL_DELETE_AFTER,
            )
    except discord.NotFound:
        logger.warning("Interaction expired before reply could be sent")
    except discord.HTTPException as exc:
        logger.warning("Failed to send interaction reply: %s", exc)


async def _defer_ephemeral(interaction: discord.Interaction) -> bool:
    """Defer a modal interaction safely; returns False if interaction is no longer valid."""
    if interaction.response.is_done():
        return True

    try:
        await interaction.response.defer(ephemeral=True)
        return True
    except discord.NotFound:
        logger.warning("Interaction expired before defer could be sent")
        return False
    except discord.HTTPException as exc:
        logger.warning("Failed to defer interaction: %s", exc)
        return False


class ConfigureTaskModal(ui.Modal, title="Configure Task"):
    """Single modal for configuring a task from within a task thread"""

    def __init__(
        self,
        task_uuid: str,
        task_name: str,
        current_status: str,
        current_priority: str,
        current_owner: str,
        current_deadline: str,
        current_description: str,
        current_url: str,
    ):
        super().__init__()
        self.task_uuid = task_uuid
        self.task_name = task_name
        self._current_status = current_status
        self._current_priority = current_priority
        self._current_owner = current_owner
        self._current_deadline = current_deadline
        self._current_description = current_description
        self._current_url = current_url

        self.status_priority = ui.TextInput(
            label="Status / Priority",
            default=f"{current_status} / {current_priority}",
            placeholder="To Do / default",
            required=False,
            max_length=100,
        )
        self.add_item(self.status_priority)

        self.owner = ui.TextInput(
            label="Owner",
            default=current_owner or "",
            placeholder="Owner name",
            required=False,
            max_length=100,
        )
        self.add_item(self.owner)

        self.deadline = ui.TextInput(
            label="Deadline (DD-MM-YYYY HH:MM AM/PM)",
            default=format_deadline_for_display(current_deadline or ""),
            placeholder="16-02-2026 09:30 PM",
            required=False,
            max_length=50,
        )
        self.add_item(self.deadline)

        self.description = ui.TextInput(
            label="Description",
            default=current_description or "",
            required=False,
            style=discord.TextStyle.paragraph,
            max_length=1000,
        )
        self.add_item(self.description)

        self.url = ui.TextInput(
            label="URL",
            default=current_url or "",
            placeholder="https://example.com",
            required=False,
            max_length=200,
        )
        self.add_item(self.url)

    def _parse_status_priority(self):
        raw = (self.status_priority.value or "").strip()
        if not raw:
            return validate_status(self._current_status), validate_priority(self._current_priority)

        for delimiter in ["/", "|", ","]:
            if delimiter in raw:
                status_part, priority_part = raw.split(delimiter, 1)
                return validate_status(status_part), validate_priority(priority_part)

        return validate_status(raw), validate_priority(self._current_priority)

    async def on_submit(self, interaction: discord.Interaction):
        from services.task_service import TaskService
        from config.settings import Settings
        from database.firebase_manager import DatabaseManager
        from services.forum_sync_service import ForumSyncService
        from services.dashboard_service import DashboardService
        from services.logging_service import get_logging_service

        status, priority = self._parse_status_priority()
        owner = (self.owner.value or "").strip()

        deadline_input = (self.deadline.value or "").strip()
        normalized_deadline = validate_deadline(
            deadline_input) if deadline_input else None
        if deadline_input and not normalized_deadline:
            await interaction.response.send_message(
                "❌ Invalid deadline format. Use DD-MM-YYYY HH:MM AM/PM (example: 16-02-2026 09:30 PM).",
                ephemeral=True,
                delete_after=Settings.EPHEMERAL_DELETE_AFTER,
            )
            return

        url = (self.url.value or "").strip()
        if url and not validate_url(url):
            await interaction.response.send_message(
                "❌ Invalid URL format. Use a full URL starting with http:// or https://.",
                ephemeral=True,
                delete_after=Settings.EPHEMERAL_DELETE_AFTER,
            )
            return

        description = self.description.value if self.description.value is not None else ""

        if not await _defer_ephemeral(interaction):
            return

        task_service = TaskService()
        try:
            await task_service.update_task_by_uuid(
                task_uuid=self.task_uuid,
                status=status,
                priority=priority,
                owner=owner,
                deadline=normalized_deadline,
                description=description,
                url=url,
            )

            if Settings.TASK_FORUM_CHANNEL:
                db_manager = DatabaseManager(
                    use_firebase=not Settings.USE_LOCAL_STORAGE)
                forum_service = ForumSyncService()
                forum_service.set_bot(interaction.client)
                forum_service.set_database(db_manager)
                await forum_service.sync_from_database()

                dashboard_service = DashboardService()
                dashboard_service.set_bot(interaction.client)
                dashboard_service.set_database(db_manager)
                await dashboard_service.update_dashboard()

            # Audit log: show only changed fields
            await get_logging_service().log_task_configured(
                actor=interaction.user,
                task_name=self.task_name,
                before={
                    "status": self._current_status,
                    "priority": self._current_priority,
                    "owner": self._current_owner,
                    "deadline": self._current_deadline,
                    "description": self._current_description,
                    "url": self._current_url,
                },
                after={
                    "status": status,
                    "priority": priority,
                    "owner": owner,
                    "deadline": normalized_deadline or "",
                    "description": description,
                    "url": url,
                },
            )

            await _send_ephemeral_reply(interaction, "✅ Task configuration updated.")
        except Exception as e:
            await _send_ephemeral_reply(interaction, f"❌ Error updating task: {str(e)}")


class AddSubtaskModal(ui.Modal, title="Add Sub-task"):
    """Modal for adding a new sub-task (auto-assigns the next available ID)."""

    def __init__(self, task_uuid: str):
        super().__init__()
        self.task_uuid = task_uuid

        self.subtask_name = ui.TextInput(
            label="Sub-task Name",
            placeholder="Enter sub-task name...",
            required=True,
            max_length=200,
        )
        self.add_item(self.subtask_name)

        self.subtask_description = ui.TextInput(
            label="Description",
            placeholder="Optional sub-task description",
            required=False,
            style=discord.TextStyle.paragraph,
            max_length=1000,
        )
        self.add_item(self.subtask_description)

        self.subtask_url = ui.TextInput(
            label="URL",
            placeholder="https://example.com (optional)",
            required=False,
            max_length=200,
        )
        self.add_item(self.subtask_url)

    async def on_submit(self, interaction: discord.Interaction):
        from services.task_service import TaskService
        from config.settings import Settings
        from database.firebase_manager import DatabaseManager
        from services.forum_sync_service import ForumSyncService
        from services.dashboard_service import DashboardService
        from services.logging_service import get_logging_service

        url = (self.subtask_url.value or "").strip()
        if url and not validate_url(url):
            await interaction.response.send_message(
                "❌ Invalid URL format. Use a full URL starting with http:// or https://.",
                ephemeral=True,
                delete_after=Settings.EPHEMERAL_DELETE_AFTER,
            )
            return

        description = (self.subtask_description.value or "").strip()

        if not await _defer_ephemeral(interaction):
            return

        task_service = TaskService()
        try:
            await task_service.add_subtask(
                self.task_uuid,
                self.subtask_name.value,
                description=description,
                url=url,
            )

            if Settings.TASK_FORUM_CHANNEL:
                db_manager = DatabaseManager(
                    use_firebase=not Settings.USE_LOCAL_STORAGE)
                forum_service = ForumSyncService()
                forum_service.set_bot(interaction.client)
                forum_service.set_database(db_manager)
                await forum_service.sync_from_database()

                dashboard_service = DashboardService()
                dashboard_service.set_bot(interaction.client)
                dashboard_service.set_database(db_manager)
                await dashboard_service.update_dashboard()

            # Audit log
            task = await task_service.get_task_by_uuid(self.task_uuid)
            task_name = task.name if task else self.task_uuid
            await get_logging_service().log_subtask_added(
                actor=interaction.user,
                task_name=task_name,
                subtask={
                    "name": self.subtask_name.value,
                    "description": description,
                    "url": url,
                },
            )

            await _send_ephemeral_reply(
                interaction,
                f"✅ Sub-task '{self.subtask_name.value}' added successfully!",
            )
        except Exception as e:
            await _send_ephemeral_reply(interaction, f"❌ Error adding sub-task: {str(e)}")


class ConfigureSubtaskModal(ui.Modal):
    """Create or edit a specific subtask by numeric ID"""

    def __init__(self, task_uuid: str, subtask_id: int, existing_subtask: Optional[dict] = None):
        title = f"Edit Sub-task #{subtask_id}" if existing_subtask else f"Create Sub-task #{subtask_id}"
        super().__init__(title=title)
        self.task_uuid = task_uuid
        self.subtask_id = subtask_id
        self._is_editing = existing_subtask is not None
        self._before_subtask = existing_subtask or {}

        existing_subtask = existing_subtask or {}

        self.subtask_name = ui.TextInput(
            label="Sub-task Name",
            default=existing_subtask.get('name', ''),
            placeholder="Enter sub-task name...",
            required=True,
            max_length=200,
        )
        self.add_item(self.subtask_name)

        self.subtask_description = ui.TextInput(
            label="Description",
            default=existing_subtask.get('description', ''),
            placeholder="Optional sub-task description",
            required=False,
            style=discord.TextStyle.paragraph,
            max_length=1000,
        )
        self.add_item(self.subtask_description)

        self.subtask_url = ui.TextInput(
            label="URL",
            default=existing_subtask.get('url', ''),
            placeholder="https://example.com (optional)",
            required=False,
            max_length=200,
        )
        self.add_item(self.subtask_url)

    async def on_submit(self, interaction: discord.Interaction):
        from services.task_service import TaskService
        from config.settings import Settings
        from database.firebase_manager import DatabaseManager
        from services.forum_sync_service import ForumSyncService
        from services.dashboard_service import DashboardService
        from services.logging_service import get_logging_service

        name = (self.subtask_name.value or '').strip()
        if not name:
            await interaction.response.send_message(
                "❌ Sub-task name is required.",
                ephemeral=True,
                delete_after=Settings.EPHEMERAL_DELETE_AFTER,
            )
            return

        url = (self.subtask_url.value or '').strip()
        if url and not validate_url(url):
            await interaction.response.send_message(
                "❌ Invalid URL format. Use a full URL starting with http:// or https://.",
                ephemeral=True,
                delete_after=Settings.EPHEMERAL_DELETE_AFTER,
            )
            return

        description = (self.subtask_description.value or '').strip()

        if not await _defer_ephemeral(interaction):
            return

        task_service = TaskService()
        try:
            await task_service.upsert_subtask_by_id(
                task_uuid=self.task_uuid,
                subtask_id=self.subtask_id,
                name=name,
                description=description,
                url=url,
            )

            if Settings.TASK_FORUM_CHANNEL:
                db_manager = DatabaseManager(
                    use_firebase=not Settings.USE_LOCAL_STORAGE)
                forum_service = ForumSyncService()
                forum_service.set_bot(interaction.client)
                forum_service.set_database(db_manager)
                await forum_service.sync_from_database()

                dashboard_service = DashboardService()
                dashboard_service.set_bot(interaction.client)
                dashboard_service.set_database(db_manager)
                await dashboard_service.update_dashboard()

            # Audit log
            task = await task_service.get_task_by_uuid(self.task_uuid)
            task_name = task.name if task else self.task_uuid
            if self._is_editing:
                await get_logging_service().log_subtask_edited(
                    actor=interaction.user,
                    task_name=task_name,
                    subtask_id=self.subtask_id,
                    before={
                        "name": self._before_subtask.get("name", ""),
                        "description": self._before_subtask.get("description", ""),
                        "url": self._before_subtask.get("url", ""),
                    },
                    after={
                        "name": name,
                        "description": description,
                        "url": url,
                    },
                )
            else:
                await get_logging_service().log_subtask_added(
                    actor=interaction.user,
                    task_name=task_name,
                    subtask={"name": name, "description": description, "url": url},
                )

            action = "updated" if self._is_editing else "created"
            await _send_ephemeral_reply(interaction, f"✅ Sub-task #{self.subtask_id} {action} successfully.")
        except Exception as e:
            await _send_ephemeral_reply(interaction, f"❌ Error saving sub-task: {str(e)}")
