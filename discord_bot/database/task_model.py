from utils.validators import parse_deadline, format_deadline_for_display
import uuid
from datetime import datetime
from typing import Optional, List, Dict, Any
from dataclasses import dataclass, field
s"""
Task data model matching the Task-Master schema
"""


def normalize_subtasks(subtasks: Any) -> List[Dict[str, Any]]:
    """Normalize subtask list to stable schema with numeric IDs."""
    if not isinstance(subtasks, list):
        return []

    normalized = []
    used_ids = set()
    next_id = 1

    for raw in subtasks:
        if isinstance(raw, dict):
            subtask = dict(raw)
        else:
            subtask = {'name': str(raw) if raw is not None else ''}

        subtask_id = subtask.get('id')
        if isinstance(subtask_id, str) and subtask_id.isdigit():
            subtask_id = int(subtask_id)
        if not isinstance(subtask_id, int) or subtask_id <= 0 or subtask_id in used_ids:
            while next_id in used_ids:
                next_id += 1
            subtask_id = next_id

        used_ids.add(subtask_id)
        next_id = max(next_id, subtask_id + 1)

        normalized.append({
            'id': subtask_id,
            'name': (subtask.get('name') or '').strip(),
            'description': (subtask.get('description') or '').strip(),
            'url': (subtask.get('url') or '').strip(),
            'completed': bool(subtask.get('completed', False)),
        })

    normalized.sort(key=lambda st: st['id'])
    return normalized


@dataclass
class Task:
    """Task model matching Task-Master structure"""
    name: str
    id: Optional[str] = None
    uuid: str = field(default_factory=lambda: str(uuid.uuid4()))
    deadline: Optional[str] = None  # ISO format string or None
    status: str = "To Do"
    order: int = 0
    description: str = ""
    url: str = ""
    owner: str = ""
    # Priority: default, Important, Moderately Important, Not Important
    colour: str = "default"
    # List of subtask dictionaries
    subtasks: list = field(default_factory=list)

    def to_dict(self):
        """Convert task to dictionary for database storage"""
        return {
            'name': self.name,
            'uuid': self.uuid,
            'deadline': self.deadline,
            'status': self.status,
            'order': self.order,
            'description': self.description,
            'url': self.url,
            'owner': self.owner,
            'colour': self.colour,
            'subtasks': normalize_subtasks(self.subtasks)
        }

    @classmethod
    def from_dict(cls, data: dict, task_id: Optional[str] = None):
        """Create Task from database dictionary"""
        task_uuid = data.get('uuid') or str(uuid.uuid4())
        return cls(
            id=task_id or data.get('id', data.get('name')),
            uuid=task_uuid,
            name=data.get('name', ''),
            deadline=data.get('deadline'),
            status=data.get('status', 'To Do'),
            order=data.get('order', 0),
            description=data.get('description', ''),
            url=data.get('url', ''),
            owner=data.get('owner', ''),
            colour=data.get('colour', 'default'),
            subtasks=normalize_subtasks(data.get('subtasks', []))
        )

    @property
    def deadline_datetime(self) -> Optional[datetime]:
        """Parse deadline string to datetime object"""
        if not self.deadline:
            return None
        return parse_deadline(self.deadline)

    @property
    def deadline_display(self) -> str:
        """Human-readable deadline for Discord UI."""
        return format_deadline_for_display(self.deadline)

    @property
    def is_overdue(self) -> bool:
        """Check if task is overdue"""
        if not self.deadline_datetime:
            return False
        return datetime.now() > self.deadline_datetime and self.status != "Complete"

    @property
    def priority_emoji(self) -> str:
        """Get emoji for priority level"""
        priority_map = {
            "Important": "🔴",
            "Moderately Important": "🟡",
            "Not Important": "🟢",
            "default": "⚪"
        }
        return priority_map.get(self.colour, "⚪")

    @property
    def status_emoji(self) -> str:
        """Get emoji for task status"""
        status_map = {
            "To Do": "📋",
            "In Progress": "🔄",
            "Complete": "✅"
        }
        return status_map.get(self.status, "❓")

    @property
    def progress_percentage(self) -> int:
        """Calculate progress percentage based on completed subtasks"""
        if not self.subtasks:
            return 0
        completed = sum(
            1 for st in self.subtasks if st.get('completed', False))
        return int((completed / len(self.subtasks)) * 100)

    def progress_bar(self, width: int = 10) -> str:
        """Generate a text-based progress bar"""
        if not self.subtasks:
            return ""
        percentage = self.progress_percentage
        filled = int((percentage / 100) * width)
        empty = width - filled
        bar = "█" * filled + "░" * empty
        return f"[{bar}] {percentage}%"


# Priority/Color options
COLOUR_OPTIONS = {
    "default": "Default",
    "Important": "Important",
    "Moderately Important": "Moderately Important",
    "Not Important": "Not Important"
}

# Status options
STATUS_OPTIONS = ["To Do", "In Progress", "Complete"]
