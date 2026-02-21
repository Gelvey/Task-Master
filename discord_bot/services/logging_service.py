"""
Discord channel logging service for human-readable audit logs.

Sends structured embeds to a configurable LOG_CHANNEL whenever a user
performs an action through the bot (task configure, subtask add/edit/
toggle/delete, task rename).
"""
import logging
import discord
from datetime import datetime, timezone
from typing import Optional

logger = logging.getLogger(__name__)

# Maximum characters shown for description fields in log embeds.
_MAX_DESCRIPTION_PREVIEW = 512

_LOG_COLORS = {
    "create": discord.Color.green(),
    "update": discord.Color.blue(),
    "delete": discord.Color.red(),
    "rename": discord.Color.gold(),
    "toggle": discord.Color.purple(),
}


class LoggingService:
    """Sends human-readable audit-log embeds to a configured Discord channel."""

    def __init__(self):
        self._bot = None

    def set_bot(self, bot):
        self._bot = bot

    async def _send_log(self, embed: discord.Embed):
        from config.settings import Settings
        if not self._bot or not Settings.LOG_CHANNEL:
            return
        try:
            channel = self._bot.get_channel(Settings.LOG_CHANNEL)
            if channel:
                await channel.send(embed=embed)
            else:
                logger.warning(
                    f"LOG_CHANNEL {Settings.LOG_CHANNEL} not found or not cached.")
        except Exception as exc:
            logger.warning(f"Failed to send audit log to channel: {exc}")

    def _make_embed(
        self,
        title: str,
        color: discord.Color,
        actor: Optional[discord.User] = None,
    ) -> discord.Embed:
        embed = discord.Embed(
            title=title,
            color=color,
            timestamp=datetime.now(timezone.utc),
        )
        if actor:
            embed.set_footer(
                text=f"{actor.display_name} (@{actor.name})",
                icon_url=str(
                    actor.display_avatar.url) if actor.display_avatar else None,
            )
        return embed

    async def log_task_configured(
        self,
        actor: discord.User,
        task_name: str,
        before: dict,
        after: dict,
    ):
        """Log task field changes with a before/after diff.

        *before* and *after* are dicts with keys:
        status, priority, owner, deadline, description, url.
        Only changed fields are shown.
        """
        field_labels = {
            "status": "Status",
            "priority": "Priority",
            "owner": "Owner",
            "deadline": "Deadline",
            "description": "Description",
            "url": "URL",
        }
        changes = [
            (label, before.get(key) or "*empty*", after.get(key) or "*empty*")
            for key, label in field_labels.items()
            if before.get(key) != after.get(key)
        ]
        if not changes:
            return

        embed = self._make_embed(
            f"⚙️ Task Configured: **{task_name}**",
            _LOG_COLORS["update"],
            actor,
        )
        embed.add_field(name="By", value=actor.mention, inline=False)
        for label, old_val, new_val in changes:
            embed.add_field(
                name=label,
                value=f"**Before:** {old_val}\n**After:** {new_val}",
                inline=True,
            )
        await self._send_log(embed)

    async def log_task_renamed(
        self,
        old_name: str,
        new_name: str,
        actor: Optional[discord.User] = None,
    ):
        """Log a task rename (e.g. from a thread title edit)."""
        embed = self._make_embed(
            "✏️ Task Renamed", _LOG_COLORS["rename"], actor)
        embed.add_field(name="Before", value=old_name, inline=True)
        embed.add_field(name="After", value=new_name, inline=True)
        if actor:
            embed.add_field(name="By", value=actor.mention, inline=False)
        await self._send_log(embed)

    async def log_task_updated_externally(
        self,
        source: str,
        task_name: str,
    ):
        """Log a task update made outside Discord (e.g. via the Web App).

        *source* is a plain-text label such as "Web App" or "Desktop App".
        """
        embed = discord.Embed(
            title=f"⚙️ Task Updated: **{task_name}**",
            color=_LOG_COLORS["update"],
            timestamp=datetime.now(timezone.utc),
        )
        embed.set_footer(text=f"Changed via {source}")
        embed.add_field(name="By", value=source, inline=False)
        await self._send_log(embed)

    async def log_subtask_added(
        self,
        actor: discord.User,
        task_name: str,
        subtask: dict,
    ):
        """Log a new subtask being added to a task."""
        embed = self._make_embed(
            f"➕ Sub-task Added to **{task_name}**",
            _LOG_COLORS["create"],
            actor,
        )
        embed.add_field(name="By", value=actor.mention, inline=False)
        embed.add_field(
            name="Sub-task", value=subtask.get("name", "Unnamed"), inline=True)
        if subtask.get("description"):
            embed.add_field(
                name="Description",
                value=subtask["description"][:_MAX_DESCRIPTION_PREVIEW],
                inline=False,
            )
        if subtask.get("url"):
            embed.add_field(name="URL", value=subtask["url"], inline=False)
        await self._send_log(embed)

    async def log_subtask_edited(
        self,
        actor: discord.User,
        task_name: str,
        subtask_id: int,
        before: dict,
        after: dict,
    ):
        """Log subtask field edits with a before/after diff.

        *before* and *after* are dicts with keys: name, description, url.
        """
        field_labels = {
            "name": "Name",
            "description": "Description",
            "url": "URL",
        }
        changes = [
            (label, before.get(key) or "*empty*", after.get(key) or "*empty*")
            for key, label in field_labels.items()
            if before.get(key) != after.get(key)
        ]
        if not changes:
            return

        embed = self._make_embed(
            f"✏️ Sub-task #{subtask_id} Edited on **{task_name}**",
            _LOG_COLORS["update"],
            actor,
        )
        embed.add_field(name="By", value=actor.mention, inline=False)
        for label, old_val, new_val in changes:
            embed.add_field(
                name=label,
                value=f"**Before:** {old_val}\n**After:** {new_val}",
                inline=True,
            )
        await self._send_log(embed)

    async def log_subtask_toggled(
        self,
        actor: discord.User,
        task_name: str,
        subtask_id: int,
        subtask_name: str,
        completed: bool,
    ):
        """Log a subtask completion toggle."""
        status = "✅ Complete" if completed else "☐ Incomplete"
        embed = self._make_embed(
            f"🔄 Sub-task #{subtask_id} Toggled on **{task_name}**",
            _LOG_COLORS["toggle"],
            actor,
        )
        embed.add_field(name="By", value=actor.mention, inline=False)
        embed.add_field(name="Sub-task", value=subtask_name, inline=True)
        embed.add_field(name="New Status", value=status, inline=True)
        await self._send_log(embed)

    async def log_subtask_deleted(
        self,
        actor: discord.User,
        task_name: str,
        subtask_id: int,
        subtask_name: str,
    ):
        """Log a subtask deletion."""
        embed = self._make_embed(
            f"🗑️ Sub-task #{subtask_id} Deleted from **{task_name}**",
            _LOG_COLORS["delete"],
            actor,
        )
        embed.add_field(name="By", value=actor.mention, inline=False)
        embed.add_field(name="Sub-task", value=subtask_name, inline=False)
        await self._send_log(embed)


# ---------------------------------------------------------------------------
# Module-level singleton – initialised once and shared across all importers.
# ---------------------------------------------------------------------------

_logging_service: Optional[LoggingService] = None


def get_logging_service() -> LoggingService:
    """Return (creating if necessary) the module-level LoggingService singleton."""
    global _logging_service
    if _logging_service is None:
        _logging_service = LoggingService()
    return _logging_service
