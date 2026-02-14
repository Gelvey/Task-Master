# Discord Bot Implementation Guide for Task-Master

## Executive Summary

This guide provides detailed instructions for implementing a Discord bot integration for Task-Master that seamlessly connects to the existing Firebase/local JSON database backend. The bot will display tasks in a persistent, auto-updating message within designated Discord channels, allowing users to interact through buttons, select menus, and modal forms.

---

## Architecture Overview

### Core Concepts

1. **Persistent Task Board**: A single Discord message per channel that displays all tasks and updates in real-time
2. **Modal-Based Input**: Discord modals (popup forms) for adding/editing tasks
3. **Button/Menu Interactions**: Interactive components for status changes, filtering, and actions
4. **User Mapping**: Discord User IDs mapped to Task-Master "Owners" via environment variables
5. **Shared Database**: Uses the same Firebase Realtime Database (or local JSON) as web app and desktop client
6. **Channel-Based Permissions**: Bot operates in specific designated channels only
7. **Separate Notification Channel**: Task reminders posted to a dedicated channel with user mentions

---

## Directory Structure

Create the following structure in `/home/gelvey/github-repos/Task-Master/discord_bot/`:

```
discord_bot/
├── bot.py                      # Main bot entry point
├── requirements.txt            # Python dependencies
├── .env.example               # Example environment variables
├── .env                       # Actual environment variables (not committed)
├── .gitignore                 # Git ignore file
├── README.md                  # Discord bot documentation
├── config/
│   ├── __init__.py
│   └── settings.py            # Configuration loader
├── database/
│   ├── __init__.py
│   ├── firebase_manager.py    # Firebase database operations
│   └── task_model.py          # Task data model
├── discord_ui/
│   ├── __init__.py
│   ├── embeds.py             # Task display embeds
│   ├── buttons.py            # Button components
│   ├── modals.py             # Modal forms
│   └── select_menus.py       # Dropdown menus
├── services/
│   ├── __init__.py
│   ├── task_service.py       # Task CRUD operations
│   ├── message_updater.py    # Task board message updater
│   └── reminder_service.py   # Task deadline reminders
└── utils/
    ├── __init__.py
    ├── logger.py             # Logging configuration
    └── validators.py         # Input validation
```

---

## Environment Variables Configuration

### File: `discord_bot/.env`

```env
# Discord Bot Configuration
DISCORD_BOT_TOKEN=your_discord_bot_token_here
TASK_CHANNELS=1234567890,9876543210  # Comma-separated channel IDs where task board displays
REMINDER_CHANNEL=1122334455          # Channel ID for deadline reminders

# User Mapping (Discord User ID -> Task-Master Owner)
# Format: DISCORD_USER_<discord_user_id>=Task-Master-Owner-Name
DISCORD_USER_123456789012345678=Circuit
DISCORD_USER_987654321098765432=Gelvey
# Add more mappings as needed

# Firebase Configuration (same as web app)
FIREBASE_DATABASE_URL=https://your-project-id.firebasedatabase.app/
FIREBASE_TYPE=service_account
FIREBASE_PROJECT_ID=your-project-id
FIREBASE_PRIVATE_KEY_ID=your-private-key-id
FIREBASE_PRIVATE_KEY="-----BEGIN PRIVATE KEY-----\n...\n-----END PRIVATE KEY-----\n"
FIREBASE_CLIENT_EMAIL=firebase-adminsdk-xxxxx@your-project-id.iam.gserviceaccount.com
FIREBASE_CLIENT_ID=your-client-id
FIREBASE_AUTH_URI=https://accounts.google.com/o/oauth2/auth
FIREBASE_TOKEN_URI=https://oauth2.googleapis.com/token
FIREBASE_AUTH_PROVIDER_CERT_URL=https://www.googleapis.com/oauth2/v1/certs
FIREBASE_CLIENT_CERT_URL=https://www.googleapis.com/robot/v1/metadata/x509/...

# Optional: Local storage fallback
USE_LOCAL_STORAGE=false

# Task Refresh Settings
TASK_BOARD_REFRESH_INTERVAL=60  # Seconds between task board updates
REMINDER_CHECK_INTERVAL=300     # Seconds between reminder checks (5 minutes)

# Logging
LOG_LEVEL=INFO
LOG_FILE=discord_bot.log
```

### File: `discord_bot/.env.example`

Create a copy of the above with placeholder values for documentation.

---

## Database Integration

### File: `discord_bot/database/task_model.py`

```python
"""
Task data model matching the Task-Master schema
"""
from dataclasses import dataclass, asdict
from typing import Optional
from datetime import datetime


@dataclass
class Task:
    """Task model matching Task-Master structure"""
    name: str
    id: Optional[str] = None
    deadline: Optional[str] = None  # ISO format string or None
    status: str = "To Do"
    order: int = 0
    description: str = ""
    url: str = ""
    owner: str = ""
    colour: str = "default"  # Priority: default, Important, Moderately Important, Not Important
    
    def to_dict(self):
        """Convert task to dictionary for database storage"""
        return {
            'name': self.name,
            'deadline': self.deadline,
            'status': self.status,
            'order': self.order,
            'description': self.description,
            'url': self.url,
            'owner': self.owner,
            'colour': self.colour
        }
    
    @classmethod
    def from_dict(cls, data: dict, task_id: str = None):
        """Create Task from database dictionary"""
        return cls(
            id=task_id or data.get('id', data.get('name')),
            name=data.get('name', ''),
            deadline=data.get('deadline'),
            status=data.get('status', 'To Do'),
            order=data.get('order', 0),
            description=data.get('description', ''),
            url=data.get('url', ''),
            owner=data.get('owner', ''),
            colour=data.get('colour', 'default')
        )
    
    @property
    def deadline_datetime(self) -> Optional[datetime]:
        """Parse deadline string to datetime object"""
        if not self.deadline:
            return None
        try:
            # Try parsing various formats
            for fmt in ["%Y-%m-%d %H:%M:%S", "%Y-%m-%d %H:%M", "%Y-%m-%d"]:
                try:
                    return datetime.strptime(self.deadline, fmt)
                except ValueError:
                    continue
            return None
        except Exception:
            return None
    
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


# Priority/Color options
COLOUR_OPTIONS = {
    "default": "Default",
    "Important": "Important",
    "Moderately Important": "Moderately Important",
    "Not Important": "Not Important"
}

# Status options
STATUS_OPTIONS = ["To Do", "In Progress", "Complete"]
```

### File: `discord_bot/database/firebase_manager.py`

```python
"""
Firebase database manager - uses same backend as web app and desktop client
"""
import os
import json
import logging
from typing import List, Optional, Dict
import firebase_admin
from firebase_admin import credentials, db
from .task_model import Task

logger = logging.getLogger(__name__)


class DatabaseManager:
    """Manages database operations for tasks"""
    
    def __init__(self, use_firebase: bool = True):
        """Initialize database manager"""
        self.use_firebase = use_firebase
        self.initialized = False
        
        if use_firebase:
            self._initialize_firebase()
        else:
            self._initialize_local()
    
    def _initialize_firebase(self):
        """Initialize Firebase connection"""
        try:
            firebase_database_url = os.getenv("FIREBASE_DATABASE_URL")
            if not firebase_database_url:
                logger.warning("FIREBASE_DATABASE_URL not set, falling back to local storage")
                self.use_firebase = False
                self._initialize_local()
                return
            
            # Check if already initialized
            try:
                firebase_admin.get_app()
                logger.info("Firebase already initialized")
                self.initialized = True
                return
            except ValueError:
                pass
            
            # Try environment variables first
            firebase_creds = {
                "type": os.getenv("FIREBASE_TYPE", "service_account"),
                "project_id": os.getenv("FIREBASE_PROJECT_ID"),
                "private_key_id": os.getenv("FIREBASE_PRIVATE_KEY_ID"),
                "private_key": os.getenv("FIREBASE_PRIVATE_KEY", "").replace('\\n', '\n'),
                "client_email": os.getenv("FIREBASE_CLIENT_EMAIL"),
                "client_id": os.getenv("FIREBASE_CLIENT_ID"),
                "auth_uri": os.getenv("FIREBASE_AUTH_URI", "https://accounts.google.com/o/oauth2/auth"),
                "token_uri": os.getenv("FIREBASE_TOKEN_URI", "https://oauth2.googleapis.com/token"),
                "auth_provider_x509_cert_url": os.getenv("FIREBASE_AUTH_PROVIDER_CERT_URL", 
                                                         "https://www.googleapis.com/oauth2/v1/certs"),
                "client_x509_cert_url": os.getenv("FIREBASE_CLIENT_CERT_URL")
            }
            
            if all([firebase_creds["project_id"], firebase_creds["private_key"], firebase_creds["client_email"]]):
                cred = credentials.Certificate(firebase_creds)
                firebase_admin.initialize_app(cred, {"databaseURL": firebase_database_url})
                logger.info("Firebase initialized from environment variables")
                self.initialized = True
            else:
                # Fallback to credentials.json in parent directory
                cred_path = os.path.join(os.path.dirname(__file__), "..", "..", "credentials.json")
                if os.path.isfile(cred_path):
                    cred = credentials.Certificate(cred_path)
                    firebase_admin.initialize_app(cred, {"databaseURL": firebase_database_url})
                    logger.info("Firebase initialized from credentials.json")
                    self.initialized = True
                else:
                    logger.warning("Firebase credentials not found, using local storage")
                    self.use_firebase = False
                    self._initialize_local()
        except Exception as e:
            logger.error(f"Failed to initialize Firebase: {e}")
            self.use_firebase = False
            self._initialize_local()
    
    def _initialize_local(self):
        """Initialize local JSON storage"""
        self.data_dir = os.path.join(os.path.dirname(__file__), "..", "data")
        os.makedirs(self.data_dir, exist_ok=True)
        logger.info(f"Using local storage at {self.data_dir}")
        self.initialized = True
    
    def _get_local_file_path(self, username: str) -> str:
        """Get local JSON file path for a username"""
        return os.path.join(self.data_dir, f"tasks_{username}.json")
    
    def load_tasks(self, username: str) -> List[Task]:
        """Load all tasks for a user"""
        tasks = []
        
        if self.use_firebase:
            try:
                tasks_ref = db.reference(f"users/{username}/tasks")
                tasks_data = tasks_ref.get()
                if tasks_data:
                    for task_id, task_data in tasks_data.items():
                        task = Task.from_dict(task_data, task_id)
                        tasks.append(task)
            except Exception as e:
                logger.error(f"Failed to load tasks from Firebase: {e}")
        else:
            # Local JSON
            local_file = self._get_local_file_path(username)
            if os.path.isfile(local_file):
                try:
                    with open(local_file, "r", encoding="utf-8") as f:
                        tasks_data = json.load(f)
                        if tasks_data:
                            for task_id, task_data in tasks_data.items():
                                task = Task.from_dict(task_data, task_id)
                                tasks.append(task)
                except Exception as e:
                    logger.error(f"Failed to read local tasks file: {e}")
        
        # Sort by order
        tasks.sort(key=lambda x: x.order)
        return tasks
    
    def save_tasks(self, username: str, tasks: List[Task]):
        """Save all tasks for a user"""
        tasks_data = {}
        for task in tasks:
            task_id = task.id or task.name
            tasks_data[task_id] = task.to_dict()
        
        if self.use_firebase:
            try:
                tasks_ref = db.reference(f"users/{username}/tasks")
                tasks_ref.set(tasks_data)
                logger.info(f"Tasks saved to Firebase for user {username}")
            except Exception as e:
                logger.error(f"Failed to save tasks to Firebase: {e}")
                raise
        else:
            # Local JSON
            local_file = self._get_local_file_path(username)
            try:
                with open(local_file, "w", encoding="utf-8") as f:
                    json.dump(tasks_data, f, indent=2)
                logger.info(f"Tasks saved locally for user {username}")
            except Exception as e:
                logger.error(f"Failed to save local tasks file: {e}")
                raise
    
    def add_task(self, username: str, task: Task):
        """Add a new task"""
        tasks = self.load_tasks(username)
        task.order = len(tasks)
        task.id = task.name  # Use name as ID
        tasks.append(task)
        self.save_tasks(username, tasks)
        logger.info(f"Added task '{task.name}' for user {username}")
    
    def update_task(self, username: str, task_id: str, updates: Dict):
        """Update an existing task"""
        tasks = self.load_tasks(username)
        for task in tasks:
            if task.id == task_id:
                for key, value in updates.items():
                    setattr(task, key, value)
                break
        self.save_tasks(username, tasks)
        logger.info(f"Updated task '{task_id}' for user {username}")
    
    def delete_task(self, username: str, task_id: str):
        """Delete a task"""
        tasks = self.load_tasks(username)
        tasks = [t for t in tasks if t.id != task_id]
        # Reorder remaining tasks
        for idx, task in enumerate(tasks):
            task.order = idx
        self.save_tasks(username, tasks)
        logger.info(f"Deleted task '{task_id}' for user {username}")
    
    def reorder_tasks(self, username: str, task_ids: List[str]):
        """Reorder tasks within same priority group"""
        tasks = self.load_tasks(username)
        task_map = {t.id: t for t in tasks}
        
        # Validate all task_ids exist
        for tid in task_ids:
            if tid not in task_map:
                raise ValueError(f"Task ID not found: {tid}")
        
        # All tasks must have same priority
        group_colour = task_map[task_ids[0]].colour
        for tid in task_ids:
            if task_map[tid].colour != group_colour:
                raise ValueError("Cannot reorder tasks across different priority groups")
        
        # Rebuild task list with new order
        provided_set = set(task_ids)
        new_order_iter = iter(task_ids)
        new_tasks = []
        
        for t in tasks:
            if t.colour == group_colour and t.id in provided_set:
                next_id = next(new_order_iter)
                new_tasks.append(task_map[next_id])
            else:
                new_tasks.append(t)
        
        # Reassign order indexes
        for idx, task in enumerate(new_tasks):
            task.order = idx
        
        self.save_tasks(username, new_tasks)
        logger.info(f"Reordered tasks for user {username}")
```

---

## Configuration Management

### File: `discord_bot/config/settings.py`

```python
"""
Configuration settings for Discord bot
"""
import os
from typing import Dict, List
from dotenv import load_dotenv
import logging

# Load environment variables
load_dotenv()

logger = logging.getLogger(__name__)


class Settings:
    """Bot configuration settings"""
    
    # Discord settings
    DISCORD_BOT_TOKEN: str = os.getenv("DISCORD_BOT_TOKEN", "")
    TASK_CHANNELS: List[int] = []
    REMINDER_CHANNEL: int = None
    
    # User mapping (Discord ID -> Owner name)
    USER_MAPPING: Dict[int, str] = {}
    
    # Firebase settings
    FIREBASE_DATABASE_URL: str = os.getenv("FIREBASE_DATABASE_URL", "")
    USE_LOCAL_STORAGE: bool = os.getenv("USE_LOCAL_STORAGE", "false").lower() == "true"
    
    # Refresh intervals (seconds)
    TASK_BOARD_REFRESH_INTERVAL: int = int(os.getenv("TASK_BOARD_REFRESH_INTERVAL", "60"))
    REMINDER_CHECK_INTERVAL: int = int(os.getenv("REMINDER_CHECK_INTERVAL", "300"))
    
    # Logging
    LOG_LEVEL: str = os.getenv("LOG_LEVEL", "INFO")
    LOG_FILE: str = os.getenv("LOG_FILE", "discord_bot.log")
    
    @classmethod
    def load(cls):
        """Load and validate settings"""
        # Parse task channels
        task_channels_str = os.getenv("TASK_CHANNELS", "")
        if task_channels_str:
            try:
                cls.TASK_CHANNELS = [int(ch.strip()) for ch in task_channels_str.split(",")]
            except ValueError:
                logger.error("Invalid TASK_CHANNELS format. Use comma-separated channel IDs.")
                cls.TASK_CHANNELS = []
        
        # Parse reminder channel
        reminder_channel_str = os.getenv("REMINDER_CHANNEL", "")
        if reminder_channel_str:
            try:
                cls.REMINDER_CHANNEL = int(reminder_channel_str)
            except ValueError:
                logger.error("Invalid REMINDER_CHANNEL format.")
        
        # Parse user mappings
        for key, value in os.environ.items():
            if key.startswith("DISCORD_USER_"):
                try:
                    discord_id = int(key.replace("DISCORD_USER_", ""))
                    cls.USER_MAPPING[discord_id] = value
                    logger.info(f"Mapped Discord user {discord_id} to owner '{value}'")
                except ValueError:
                    logger.warning(f"Invalid Discord user ID in {key}")
        
        # Validate required settings
        if not cls.DISCORD_BOT_TOKEN:
            raise ValueError("DISCORD_BOT_TOKEN is required")
        
        if not cls.TASK_CHANNELS:
            logger.warning("No TASK_CHANNELS configured. Bot will not display task boards.")
        
        if not cls.FIREBASE_DATABASE_URL and not cls.USE_LOCAL_STORAGE:
            logger.warning("No FIREBASE_DATABASE_URL and USE_LOCAL_STORAGE=false. Bot may not persist data.")
        
        logger.info(f"Loaded settings: {len(cls.USER_MAPPING)} user mappings, "
                   f"{len(cls.TASK_CHANNELS)} task channels")
    
    @classmethod
    def get_owner_for_user(cls, discord_user_id: int) -> str:
        """Get Task-Master owner name for Discord user ID"""
        return cls.USER_MAPPING.get(discord_user_id, f"user_{discord_user_id}")
    
    @classmethod
    def get_discord_user_for_owner(cls, owner: str) -> int:
        """Get Discord user ID for Task-Master owner name (reverse lookup)"""
        for discord_id, owner_name in cls.USER_MAPPING.items():
            if owner_name == owner:
                return discord_id
        return None


# Load settings on module import
Settings.load()
```

---

## Discord UI Components

### File: `discord_bot/discord_ui/embeds.py`

```python
"""
Discord embed builders for task display
"""
import discord
from typing import List
from database.task_model import Task
from datetime import datetime


def create_task_board_embed(tasks: List[Task], owner: str = None, filter_status: str = None) -> discord.Embed:
    """
    Create a comprehensive task board embed
    
    Args:
        tasks: List of tasks to display
        owner: Optional owner filter
        filter_status: Optional status filter (To Do, In Progress, Complete, or None for all)
    """
    # Filter tasks
    filtered_tasks = tasks
    if owner:
        filtered_tasks = [t for t in filtered_tasks if t.owner == owner]
    if filter_status and filter_status != "All":
        filtered_tasks = [t for t in filtered_tasks if t.status == filter_status]
    
    # Create embed
    embed = discord.Embed(
        title="📋 Task Master - Task Board",
        description=f"Displaying {len(filtered_tasks)} task(s)",
        color=discord.Color.blue(),
        timestamp=datetime.now()
    )
    
    # Group by priority
    priority_groups = {
        "Important": [],
        "Moderately Important": [],
        "Not Important": [],
        "default": []
    }
    
    for task in filtered_tasks:
        priority_groups[task.colour].append(task)
    
    # Add fields for each priority group
    for priority, group_tasks in priority_groups.items():
        if not group_tasks:
            continue
        
        priority_label = "Default" if priority == "default" else priority
        emoji = {
            "Important": "🔴",
            "Moderately Important": "🟡",
            "Not Important": "🟢",
            "default": "⚪"
        }.get(priority, "⚪")
        
        field_value = ""
        for task in group_tasks:
            status_emoji = task.status_emoji
            deadline_str = ""
            if task.deadline:
                deadline_str = f" • 📅 {task.deadline}"
                if task.is_overdue:
                    deadline_str = f" • ⚠️ **OVERDUE** {task.deadline}"
            
            owner_str = f" • 👤 {task.owner}" if task.owner else ""
            url_str = f" • [🔗 Link]({task.url})" if task.url else ""
            
            field_value += (f"{status_emoji} **{task.name}**\n"
                          f"    ↳ Status: {task.status}{deadline_str}{owner_str}{url_str}\n")
            
            if task.description:
                desc_preview = task.description[:50] + "..." if len(task.description) > 50 else task.description
                field_value += f"    ↳ 📝 {desc_preview}\n"
            
            field_value += "\n"
        
        embed.add_field(
            name=f"{emoji} {priority_label} ({len(group_tasks)})",
            value=field_value or "No tasks",
            inline=False
        )
    
    if not filtered_tasks:
        embed.add_field(
            name="No Tasks",
            value="No tasks match the current filter. Use the dropdown menu to change filters or add a new task!",
            inline=False
        )
    
    embed.set_footer(text="Last updated")
    
    return embed


def create_task_detail_embed(task: Task) -> discord.Embed:
    """Create detailed embed for a single task"""
    color_map = {
        "Important": discord.Color.red(),
        "Moderately Important": discord.Color.gold(),
        "Not Important": discord.Color.green(),
        "default": discord.Color.greyple()
    }
    
    embed = discord.Embed(
        title=f"{task.status_emoji} {task.name}",
        description=task.description or "*No description*",
        color=color_map.get(task.colour, discord.Color.greyple())
    )
    
    embed.add_field(name="Status", value=task.status, inline=True)
    embed.add_field(name="Priority", value=task.colour if task.colour != "default" else "Default", inline=True)
    
    if task.deadline:
        deadline_display = task.deadline
        if task.is_overdue:
            deadline_display = f"⚠️ **OVERDUE** {task.deadline}"
        embed.add_field(name="Deadline", value=deadline_display, inline=True)
    
    if task.owner:
        embed.add_field(name="Owner", value=task.owner, inline=True)
    
    if task.url:
        embed.add_field(name="URL", value=f"[Click here]({task.url})", inline=True)
    
    return embed


def create_reminder_embed(task: Task, discord_user_mention: str) -> discord.Embed:
    """Create embed for task deadline reminder"""
    embed = discord.Embed(
        title="⏰ Task Deadline Reminder",
        description=f"{discord_user_mention}, you have a task approaching its deadline!",
        color=discord.Color.orange(),
        timestamp=datetime.now()
    )
    
    embed.add_field(name="Task", value=task.name, inline=False)
    embed.add_field(name="Deadline", value=task.deadline, inline=True)
    embed.add_field(name="Status", value=task.status, inline=True)
    
    if task.description:
        desc_preview = task.description[:100] + "..." if len(task.description) > 100 else task.description
        embed.add_field(name="Description", value=desc_preview, inline=False)
    
    if task.url:
        embed.add_field(name="URL", value=f"[Click here]({task.url})", inline=False)
    
    return embed
```

### File: `discord_bot/discord_ui/buttons.py`

```python
"""
Discord button components for task interactions
"""
import discord
from discord.ui import Button, View


class TaskBoardButtons(View):
    """Buttons for task board interactions"""
    
    def __init__(self):
        super().__init__(timeout=None)  # Persistent view
    
    @discord.ui.button(label="➕ Add Task", style=discord.ButtonStyle.success, custom_id="add_task")
    async def add_task_button(self, interaction: discord.Interaction, button: Button):
        """Button to add a new task"""
        from .modals import AddTaskModal
        await interaction.response.send_modal(AddTaskModal())
    
    @discord.ui.button(label="✏️ Edit Task", style=discord.ButtonStyle.primary, custom_id="edit_task")
    async def edit_task_button(self, interaction: discord.Interaction, button: Button):
        """Button to edit an existing task"""
        from .modals import SelectTaskModal
        await interaction.response.send_modal(SelectTaskModal(action="edit"))
    
    @discord.ui.button(label="🗑️ Delete Task", style=discord.ButtonStyle.danger, custom_id="delete_task")
    async def delete_task_button(self, interaction: discord.Interaction, button: Button):
        """Button to delete a task"""
        from .modals import SelectTaskModal
        await interaction.response.send_modal(SelectTaskModal(action="delete"))
    
    @discord.ui.button(label="✅ Mark Complete", style=discord.ButtonStyle.secondary, custom_id="mark_complete")
    async def mark_complete_button(self, interaction: discord.Interaction, button: Button):
        """Button to mark a task as complete"""
        from .modals import SelectTaskModal
        await interaction.response.send_modal(SelectTaskModal(action="complete"))
    
    @discord.ui.button(label="🔄 Mark In Progress", style=discord.ButtonStyle.secondary, custom_id="mark_in_progress")
    async def mark_in_progress_button(self, interaction: discord.Interaction, button: Button):
        """Button to mark a task as in progress"""
        from .modals import SelectTaskModal
        await interaction.response.send_modal(SelectTaskModal(action="in_progress"))


class ConfirmationButtons(View):
    """Generic confirmation buttons"""
    
    def __init__(self, timeout=60):
        super().__init__(timeout=timeout)
        self.value = None
    
    @discord.ui.button(label="Confirm", style=discord.ButtonStyle.success)
    async def confirm(self, interaction: discord.Interaction, button: Button):
        self.value = True
        await interaction.response.defer()
        self.stop()
    
    @discord.ui.button(label="Cancel", style=discord.ButtonStyle.danger)
    async def cancel(self, interaction: discord.Interaction, button: Button):
        self.value = False
        await interaction.response.defer()
        self.stop()
```

### File: `discord_bot/discord_ui/modals.py`

```python
"""
Discord modal forms for task input
"""
import discord
from discord import ui
from typing import Optional


class AddTaskModal(ui.Modal, title="Add New Task"):
    """Modal form for adding a new task"""
    
    task_name = ui.TextInput(
        label="Task Name",
        placeholder="Enter task name...",
        required=True,
        max_length=100
    )
    
    deadline = ui.TextInput(
        label="Deadline (YYYY-MM-DD HH:MM)",
        placeholder="2026-12-31 23:59 (optional)",
        required=False,
        max_length=50
    )
    
    priority = ui.TextInput(
        label="Priority",
        placeholder="Important / Moderately Important / Not Important / default",
        required=False,
        default="default",
        max_length=50
    )
    
    description = ui.TextInput(
        label="Description",
        placeholder="Enter task description (optional)...",
        required=False,
        style=discord.TextStyle.paragraph,
        max_length=500
    )
    
    url = ui.TextInput(
        label="URL",
        placeholder="https://example.com (optional)",
        required=False,
        max_length=200
    )
    
    async def on_submit(self, interaction: discord.Interaction):
        """Handle form submission"""
        # Import here to avoid circular imports
        from services.task_service import TaskService
        from config.settings import Settings
        
        owner = Settings.get_owner_for_user(interaction.user.id)
        
        # Validate and normalize priority
        priority = self.priority.value.strip() if self.priority.value else "default"
        valid_priorities = ["Important", "Moderately Important", "Not Important", "default"]
        if priority not in valid_priorities:
            priority = "default"
        
        task_service = TaskService()
        try:
            await task_service.add_task_from_modal(
                owner=owner,
                name=self.task_name.value,
                deadline=self.deadline.value if self.deadline.value else None,
                priority=priority,
                description=self.description.value if self.description.value else "",
                url=self.url.value if self.url.value else ""
            )
            await interaction.response.send_message(
                f"✅ Task '{self.task_name.value}' added successfully!",
                ephemeral=True
            )
        except Exception as e:
            await interaction.response.send_message(
                f"❌ Error adding task: {str(e)}",
                ephemeral=True
            )


class EditTaskModal(ui.Modal, title="Edit Task"):
    """Modal form for editing an existing task"""
    
    def __init__(self, task_id: str, current_name: str, current_deadline: str, 
                 current_priority: str, current_description: str, current_url: str):
        super().__init__()
        
        self.task_id = task_id
        
        self.task_name = ui.TextInput(
            label="Task Name",
            default=current_name,
            required=True,
            max_length=100
        )
        self.add_item(self.task_name)
        
        self.deadline = ui.TextInput(
            label="Deadline (YYYY-MM-DD HH:MM)",
            default=current_deadline or "",
            required=False,
            max_length=50
        )
        self.add_item(self.deadline)
        
        self.priority = ui.TextInput(
            label="Priority",
            default=current_priority,
            required=False,
            max_length=50
        )
        self.add_item(self.priority)
        
        self.description = ui.TextInput(
            label="Description",
            default=current_description or "",
            required=False,
            style=discord.TextStyle.paragraph,
            max_length=500
        )
        self.add_item(self.description)
        
        self.url = ui.TextInput(
            label="URL",
            default=current_url or "",
            required=False,
            max_length=200
        )
        self.add_item(self.url)
    
    async def on_submit(self, interaction: discord.Interaction):
        """Handle form submission"""
        from services.task_service import TaskService
        from config.settings import Settings
        
        owner = Settings.get_owner_for_user(interaction.user.id)
        
        # Validate and normalize priority
        priority = self.priority.value.strip() if self.priority.value else "default"
        valid_priorities = ["Important", "Moderately Important", "Not Important", "default"]
        if priority not in valid_priorities:
            priority = "default"
        
        task_service = TaskService()
        try:
            await task_service.update_task_from_modal(
                owner=owner,
                task_id=self.task_id,
                name=self.task_name.value,
                deadline=self.deadline.value if self.deadline.value else None,
                priority=priority,
                description=self.description.value if self.description.value else "",
                url=self.url.value if self.url.value else ""
            )
            await interaction.response.send_message(
                f"✅ Task '{self.task_name.value}' updated successfully!",
                ephemeral=True
            )
        except Exception as e:
            await interaction.response.send_message(
                f"❌ Error updating task: {str(e)}",
                ephemeral=True
            )


class SelectTaskModal(ui.Modal, title="Select Task"):
    """Modal for selecting a task by name"""
    
    def __init__(self, action: str):
        super().__init__()
        self.action = action  # edit, delete, complete, in_progress
        
        action_labels = {
            "edit": "Edit",
            "delete": "Delete",
            "complete": "Mark Complete",
            "in_progress": "Mark In Progress",
            "to_do": "Mark To Do"
        }
        
        self.title = f"{action_labels.get(action, 'Select')} Task"
        
        self.task_name = ui.TextInput(
            label="Enter Task Name",
            placeholder="Type the exact task name...",
            required=True,
            max_length=100
        )
        self.add_item(self.task_name)
    
    async def on_submit(self, interaction: discord.Interaction):
        """Handle task selection"""
        from services.task_service import TaskService
        from config.settings import Settings
        
        owner = Settings.get_owner_for_user(interaction.user.id)
        task_service = TaskService()
        
        try:
            if self.action == "edit":
                # Load task and open edit modal
                task = await task_service.get_task_by_name(owner, self.task_name.value)
                if not task:
                    await interaction.response.send_message(
                        f"❌ Task '{self.task_name.value}' not found.",
                        ephemeral=True
                    )
                    return
                
                edit_modal = EditTaskModal(
                    task_id=task.id,
                    current_name=task.name,
                    current_deadline=task.deadline or "",
                    current_priority=task.colour,
                    current_description=task.description,
                    current_url=task.url
                )
                await interaction.response.send_modal(edit_modal)
                
            elif self.action == "delete":
                await task_service.delete_task(owner, self.task_name.value)
                await interaction.response.send_message(
                    f"✅ Task '{self.task_name.value}' deleted successfully!",
                    ephemeral=True
                )
                
            elif self.action in ["complete", "in_progress", "to_do"]:
                status_map = {
                    "complete": "Complete",
                    "in_progress": "In Progress",
                    "to_do": "To Do"
                }
                new_status = status_map[self.action]
                await task_service.update_task_status(owner, self.task_name.value, new_status)
                await interaction.response.send_message(
                    f"✅ Task '{self.task_name.value}' marked as {new_status}!",
                    ephemeral=True
                )
        except Exception as e:
            await interaction.response.send_message(
                f"❌ Error: {str(e)}",
                ephemeral=True
            )
```

### File: `discord_bot/discord_ui/select_menus.py`

```python
"""
Discord select menu components for filtering
"""
import discord
from discord.ui import Select, View


class TaskFilterSelect(Select):
    """Select menu for filtering tasks by status"""
    
    def __init__(self):
        options = [
            discord.SelectOption(label="All Tasks", value="All", emoji="📋", default=True),
            discord.SelectOption(label="To Do", value="To Do", emoji="📝"),
            discord.SelectOption(label="In Progress", value="In Progress", emoji="🔄"),
            discord.SelectOption(label="Complete", value="Complete", emoji="✅"),
        ]
        
        super().__init__(
            placeholder="Filter by status...",
            options=options,
            custom_id="filter_status"
        )
    
    async def callback(self, interaction: discord.Interaction):
        """Handle filter selection"""
        from services.message_updater import MessageUpdater
        from config.settings import Settings
        
        selected_status = self.values[0]
        owner = Settings.get_owner_for_user(interaction.user.id)
        
        updater = MessageUpdater()
        await updater.update_task_board(
            interaction.channel,
            owner=owner,
            filter_status=selected_status if selected_status != "All" else None
        )
        
        await interaction.response.send_message(
            f"✅ Filtered to show: {selected_status}",
            ephemeral=True,
            delete_after=3
        )


class TaskFilterView(View):
    """View containing filter select menu and action buttons"""
    
    def __init__(self):
        super().__init__(timeout=None)
        self.add_item(TaskFilterSelect())
```

---

## Services Layer

### File: `discord_bot/services/task_service.py`

```python
"""
Task service layer for business logic
"""
import logging
from typing import List, Optional
from database.firebase_manager import DatabaseManager
from database.task_model import Task

logger = logging.getLogger(__name__)


class TaskService:
    """Service for task operations"""
    
    def __init__(self):
        self.db = DatabaseManager(use_firebase=True)
    
    def get_all_tasks(self, owner: str) -> List[Task]:
        """Get all tasks for an owner"""
        return self.db.load_tasks(owner)
    
    async def get_task_by_name(self, owner: str, task_name: str) -> Optional[Task]:
        """Get a specific task by name"""
        tasks = self.db.load_tasks(owner)
        for task in tasks:
            if task.name == task_name:
                return task
        return None
    
    async def add_task_from_modal(self, owner: str, name: str, deadline: Optional[str] = None,
                                   priority: str = "default", description: str = "",
                                   url: str = ""):
        """Add a new task from modal input"""
        task = Task(
            name=name,
            deadline=deadline,
            status="To Do",
            description=description,
            url=url,
            owner=owner,
            colour=priority
        )
        self.db.add_task(owner, task)
        logger.info(f"Added task '{name}' for owner {owner}")
        
        # Trigger task board update
        from .message_updater import MessageUpdater
        updater = MessageUpdater()
        await updater.update_all_task_boards()
    
    async def update_task_from_modal(self, owner: str, task_id: str, name: str,
                                     deadline: Optional[str] = None, priority: str = "default",
                                     description: str = "", url: str = ""):
        """Update a task from modal input"""
        updates = {
            'name': name,
            'deadline': deadline,
            'colour': priority,
            'description': description,
            'url': url
        }
        self.db.update_task(owner, task_id, updates)
        logger.info(f"Updated task '{task_id}' for owner {owner}")
        
        # Trigger task board update
        from .message_updater import MessageUpdater
        updater = MessageUpdater()
        await updater.update_all_task_boards()
    
    async def update_task_status(self, owner: str, task_name: str, new_status: str):
        """Update task status"""
        task = await self.get_task_by_name(owner, task_name)
        if not task:
            raise ValueError(f"Task '{task_name}' not found")
        
        self.db.update_task(owner, task.id, {'status': new_status})
        logger.info(f"Updated task '{task_name}' status to {new_status}")
        
        # Trigger task board update
        from .message_updater import MessageUpdater
        updater = MessageUpdater()
        await updater.update_all_task_boards()
    
    async def delete_task(self, owner: str, task_name: str):
        """Delete a task by name"""
        task = await self.get_task_by_name(owner, task_name)
        if not task:
            raise ValueError(f"Task '{task_name}' not found")
        
        self.db.delete_task(owner, task.id)
        logger.info(f"Deleted task '{task_name}' for owner {owner}")
        
        # Trigger task board update
        from .message_updater import MessageUpdater
        updater = MessageUpdater()
        await updater.update_all_task_boards()
```

### File: `discord_bot/services/message_updater.py`

```python
"""
Service to update task board messages
"""
import discord
import logging
from typing import Optional
from config.settings import Settings
from discord_ui.embeds import create_task_board_embed
from discord_ui.buttons import TaskBoardButtons
from discord_ui.select_menus import TaskFilterView

logger = logging.getLogger(__name__)


class MessageUpdater:
    """Updates task board messages in Discord channels"""
    
    def __init__(self):
        self.task_board_messages = {}  # {channel_id: message_id}
        self._bot = None
    
    def set_bot(self, bot):
        """Set bot instance for accessing channels"""
        self._bot = bot
    
    async def initialize_task_boards(self):
        """Initialize task boards in all configured channels"""
        if not self._bot:
            logger.error("Bot not set in MessageUpdater")
            return
        
        for channel_id in Settings.TASK_CHANNELS:
            try:
                channel = self._bot.get_channel(channel_id)
                if not channel:
                    logger.warning(f"Channel {channel_id} not found")
                    continue
                
                # Create initial task board message
                from services.task_service import TaskService
                task_service = TaskService()
                
                # Get all tasks (we'll show all users' tasks in the board)
                all_tasks = []
                for owner in Settings.USER_MAPPING.values():
                    tasks = task_service.get_all_tasks(owner)
                    all_tasks.extend(tasks)
                
                embed = create_task_board_embed(all_tasks)
                
                # Create view with buttons and filters
                view = TaskFilterView()
                view.add_item(TaskBoardButtons())
                
                message = await channel.send(embed=embed, view=view)
                self.task_board_messages[channel_id] = message.id
                
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
            
            if owner:
                tasks = task_service.get_all_tasks(owner)
            else:
                # Get all tasks from all users
                all_tasks = []
                for owner_name in Settings.USER_MAPPING.values():
                    tasks = task_service.get_all_tasks(owner_name)
                    all_tasks.extend(tasks)
                tasks = all_tasks
            
            embed = create_task_board_embed(tasks, owner=owner, filter_status=filter_status)
            
            # Find existing task board message or create new one
            message_id = self.task_board_messages.get(channel.id)
            
            view = TaskFilterView()
            view.add_item(TaskBoardButtons())
            
            if message_id:
                try:
                    message = await channel.fetch_message(message_id)
                    await message.edit(embed=embed, view=view)
                except discord.NotFound:
                    # Message was deleted, create new one
                    message = await channel.send(embed=embed, view=view)
                    self.task_board_messages[channel.id] = message.id
            else:
                message = await channel.send(embed=embed, view=view)
                self.task_board_messages[channel.id] = message.id
            
            logger.info(f"Updated task board in channel {channel.id}")
        except Exception as e:
            logger.error(f"Failed to update task board in channel {channel.id}: {e}")
    
    async def update_all_task_boards(self):
        """Update task boards in all configured channels"""
        if not self._bot:
            logger.error("Bot not set in MessageUpdater")
            return
        
        for channel_id in Settings.TASK_CHANNELS:
            try:
                channel = self._bot.get_channel(channel_id)
                if not channel:
                    logger.warning(f"Channel {channel_id} not found")
                    continue
                
                await self.update_task_board(channel)
            except Exception as e:
                logger.error(f"Failed to update task board in channel {channel_id}: {e}")
```

### File: `discord_bot/services/reminder_service.py`

```python
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
        self.reminded_tasks = set()  # Track which tasks we've already reminded about
    
    def set_bot(self, bot):
        """Set bot instance"""
        self._bot = bot
    
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
        
        # Get all tasks from all users
        for discord_user_id, owner in Settings.USER_MAPPING.items():
            tasks = task_service.get_all_tasks(owner)
            
            for task in tasks:
                if task.status == "Complete":
                    continue  # Skip completed tasks
                
                if not task.deadline_datetime:
                    continue  # Skip tasks without deadlines
                
                # Check if deadline is within next 24 hours
                time_until_deadline = task.deadline_datetime - datetime.now()
                
                # Create unique reminder key
                reminder_key = f"{owner}:{task.id}:{task.deadline}"
                
                if time_until_deadline.total_seconds() > 0 and time_until_deadline < timedelta(hours=24):
                    # Send reminder if we haven't already
                    if reminder_key not in self.reminded_tasks:
                        await self._send_reminder(reminder_channel, task, discord_user_id)
                        self.reminded_tasks.add(reminder_key)
                        logger.info(f"Sent reminder for task '{task.name}' to user {discord_user_id}")
                elif time_until_deadline.total_seconds() < 0:
                    # Task is overdue, send overdue notification (once per day)
                    overdue_key = f"{reminder_key}:overdue:{datetime.now().date()}"
                    if overdue_key not in self.reminded_tasks:
                        await self._send_overdue_notification(reminder_channel, task, discord_user_id)
                        self.reminded_tasks.add(overdue_key)
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
```

---

## Main Bot Implementation

### File: `discord_bot/bot.py`

```python
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
from discord_ui.buttons import TaskBoardButtons
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
    bot.add_view(TaskBoardButtons())
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


@bot.event
async def on_interaction(interaction: discord.Interaction):
    """Handle interactions (buttons, modals, etc.)"""
    # Check if interaction is in allowed channel
    if interaction.channel_id not in Settings.TASK_CHANNELS:
        if interaction.type == discord.InteractionType.component:
            await interaction.response.send_message(
                "❌ This bot only works in designated task channels.",
                ephemeral=True
            )
        return
    
    # Discord.py handles the rest automatically


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
```

---

## Utilities

### File: `discord_bot/utils/logger.py`

```python
"""
Logging configuration
"""
import logging
import sys
from config.settings import Settings


def setup_logging():
    """Setup logging configuration"""
    log_level = getattr(logging, Settings.LOG_LEVEL.upper(), logging.INFO)
    
    # Create formatter
    formatter = logging.Formatter(
        '%(asctime)s - %(name)s - %(levelname)s - %(message)s',
        datefmt='%Y-%m-%d %H:%M:%S'
    )
    
    # Console handler
    console_handler = logging.StreamHandler(sys.stdout)
    console_handler.setFormatter(formatter)
    console_handler.setLevel(log_level)
    
    # File handler
    file_handler = logging.FileHandler(Settings.LOG_FILE, encoding='utf-8')
    file_handler.setFormatter(formatter)
    file_handler.setLevel(log_level)
    
    # Configure root logger
    root_logger = logging.getLogger()
    root_logger.setLevel(log_level)
    root_logger.addHandler(console_handler)
    root_logger.addHandler(file_handler)
    
    # Reduce discord.py logging verbosity
    logging.getLogger('discord').setLevel(logging.WARNING)
    logging.getLogger('discord.http').setLevel(logging.WARNING)
    
    logging.info(f"Logging configured at {Settings.LOG_LEVEL} level")
```

### File: `discord_bot/utils/validators.py`

```python
"""
Input validation utilities
"""
import re
from datetime import datetime
from typing import Optional


def validate_deadline(deadline_str: str) -> Optional[str]:
    """
    Validate and normalize deadline string
    
    Returns:
        Normalized deadline string or None if invalid
    """
    if not deadline_str or not deadline_str.strip():
        return None
    
    deadline_str = deadline_str.strip()
    
    # Try parsing various formats
    formats = [
        "%Y-%m-%d %H:%M:%S",
        "%Y-%m-%d %H:%M",
        "%Y-%m-%d",
    ]
    
    for fmt in formats:
        try:
            dt = datetime.strptime(deadline_str, fmt)
            return dt.strftime("%Y-%m-%d %H:%M:%S")
        except ValueError:
            continue
    
    return None


def validate_url(url: str) -> bool:
    """Validate URL format"""
    if not url or not url.strip():
        return True  # Empty URL is valid
    
    url_pattern = re.compile(
        r"^https?://"
        r"(?:(?:[A-Z0-9](?:[A-Z0-9-]{0,61}[A-Z0-9])?\.)+[A-Z]{2,6}\.?|"
        r"localhost|"
        r"\d{1,3}\.\d{1,3}\.\d{1,3}\.\d{1,3})"
        r"(?::\d+)?"
        r"(?:/?|[/?]\S+)$",
        re.IGNORECASE,
    )
    
    return bool(url_pattern.match(url.strip()))


def validate_priority(priority: str) -> str:
    """
    Validate and normalize priority/colour value
    
    Returns:
        Normalized priority or "default"
    """
    valid_priorities = ["Important", "Moderately Important", "Not Important", "default"]
    
    if not priority or not priority.strip():
        return "default"
    
    priority = priority.strip()
    
    if priority in valid_priorities:
        return priority
    
    # Case-insensitive matching
    for valid in valid_priorities:
        if priority.lower() == valid.lower():
            return valid
    
    return "default"


def validate_status(status: str) -> str:
    """
    Validate and normalize status value
    
    Returns:
        Normalized status or "To Do"
    """
    valid_statuses = ["To Do", "In Progress", "Complete"]
    
    if not status or not status.strip():
        return "To Do"
    
    status = status.strip()
    
    if status in valid_statuses:
        return status
    
    # Case-insensitive matching
    for valid in valid_statuses:
        if status.lower() == valid.lower():
            return valid
    
    return "To Do"
```

---

## Additional Files

### File: `discord_bot/requirements.txt`

```
# Discord.py library
discord.py>=2.3.0

# Firebase Admin SDK (same as main app)
firebase-admin>=6.0.0

# Environment variables
python-dotenv>=1.0.0

# Async utilities
aiohttp>=3.9.0

# Logging and monitoring
colorlog>=6.7.0
```

### File: `discord_bot/.gitignore`

```
# Environment variables
.env

# Python
__pycache__/
*.py[cod]
*$py.class
*.so
.Python
build/
develop-eggs/
dist/
downloads/
eggs/
.eggs/
lib/
lib64/
parts/
sdist/
var/
wheels/
*.egg-info/
.installed.cfg
*.egg

# Virtual environments
venv/
ENV/
env/

# IDE
.vscode/
.idea/
*.swp
*.swo
*~

# Logs
*.log
logs/

# Local data
data/
*.json

# OS
.DS_Store
Thumbs.db
```

### File: `discord_bot/README.md`

```markdown
# Task-Master Discord Bot

Discord bot integration for Task-Master task management system. Provides full task management capabilities through Discord's interactive UI components.

## Features

- **Persistent Task Board**: Single message per channel displaying all tasks, updated in real-time
- **Interactive Modals**: Add and edit tasks through Discord popup forms
- **Button Controls**: Mark tasks complete, in progress, or delete with button clicks
- **Status Filtering**: Filter tasks by status using dropdown menus
- **Priority Levels**: Support for Important, Moderately Important, Not Important priorities
- **Deadline Reminders**: Automatic notifications for upcoming deadlines (24-hour warning)
- **Overdue Alerts**: Daily notifications for overdue tasks
- **Multi-User Support**: Maps Discord users to Task-Master owners via environment variables
- **Shared Database**: Uses same Firebase/local JSON backend as web app and desktop client

## Prerequisites

- Python 3.11 or higher
- Discord bot token ([Create one here](https://discord.com/developers/applications))
- Firebase credentials (shared with main Task-Master app) or local storage
- Discord server with admin permissions to add the bot

## Installation

### 1. Create Discord Bot

1. Go to [Discord Developer Portal](https://discord.com/developers/applications)
2. Click "New Application" and give it a name
3. Go to "Bot" section and click "Add Bot"
4. Enable the following Privileged Gateway Intents:
   - SERVER MEMBERS INTENT
   - MESSAGE CONTENT INTENT
5. Copy the bot token (you'll need this for `.env`)

### 2. Invite Bot to Server

1. In Discord Developer Portal, go to "OAuth2" → "URL Generator"
2. Select scopes: `bot`, `applications.commands`
3. Select permissions:
   - Read Messages/View Channels
   - Send Messages
   - Embed Links
   - Read Message History
   - Add Reactions
   - Use Slash Commands
4. Copy generated URL and open in browser to invite bot

### 3. Setup Project

```bash
# Navigate to discord_bot directory
cd /path/to/Task-Master/discord_bot

# Create virtual environment (recommended)
python -m venv venv
source venv/bin/activate  # On Windows: venv\Scripts\activate

# Install dependencies
pip install -r requirements.txt
```

### 4. Configure Environment

1. Copy `.env.example` to `.env`:
   ```bash
   cp .env.example .env
   ```

2. Edit `.env` and configure:
   - `DISCORD_BOT_TOKEN`: Your Discord bot token
   - `TASK_CHANNELS`: Channel IDs where task boards will display (comma-separated)
   - `REMINDER_CHANNEL`: Channel ID for deadline reminders
   - `DISCORD_USER_*`: Map Discord user IDs to Task-Master owners
   - Firebase credentials (copy from main app's `.env` or use `credentials.json`)

### 5. Get Discord IDs

To get channel and user IDs:

1. Enable Developer Mode in Discord: Settings → Advanced → Developer Mode
2. Right-click on channel → Copy ID
3. Right-click on user → Copy ID

### 6. Configure User Mapping

In `.env`, map Discord users to Task-Master owners:

```env
DISCORD_USER_123456789012345678=Circuit
DISCORD_USER_987654321098765432=Gelvey
```

Replace the numbers with actual Discord user IDs.

## Running the Bot

```bash
# Make sure virtual environment is activated
source venv/bin/activate  # On Windows: venv\Scripts\activate

# Run the bot
python bot.py
```

The bot should now:
- Connect to Discord
- Initialize task boards in configured channels
- Start listening for interactions

## Usage

### Task Board

The task board is a persistent message that displays all tasks grouped by priority. It updates automatically every minute (configurable).

### Adding Tasks

1. Click **➕ Add Task** button
2. Fill out the modal form:
   - **Task Name**: Required
   - **Deadline**: Optional (format: YYYY-MM-DD HH:MM)
   - **Priority**: Optional (Important, Moderately Important, Not Important, or default)
   - **Description**: Optional
   - **URL**: Optional
3. Click Submit

### Editing Tasks

1. Click **✏️ Edit Task** button
2. Enter the exact task name
3. Update fields in the modal
4. Click Submit

### Deleting Tasks

1. Click **🗑️ Delete Task** button
2. Enter the exact task name
3. Confirm deletion

### Changing Status

1. Click **✅ Mark Complete** or **🔄 Mark In Progress**
2. Enter the task name
3. Task status will update

### Filtering Tasks

Use the dropdown menu at the top of the task board to filter by:
- All Tasks
- To Do
- In Progress
- Complete

### Reminders

The bot automatically checks for tasks with deadlines approaching within 24 hours and sends reminders to the configured reminder channel, mentioning the task owner.

## Commands

- `!help` - Show help information
- `!refresh` - Manually refresh the task board
- `!taskboard` - (Admin only) Create a new task board in current channel

## Architecture

```
discord_bot/
├── bot.py                 # Main bot entry point
├── config/                # Configuration management
│   └── settings.py
├── database/              # Database layer (Firebase/local)
│   ├── firebase_manager.py
│   └── task_model.py
├── discord_ui/            # Discord UI components
│   ├── embeds.py
│   ├── buttons.py
│   ├── modals.py
│   └── select_menus.py
├── services/              # Business logic
│   ├── task_service.py
│   ├── message_updater.py
│   └── reminder_service.py
└── utils/                 # Utilities
    ├── logger.py
    └── validators.py
```

## Troubleshooting

### Bot doesn't respond

- Check bot has required permissions in the channel
- Verify `TASK_CHANNELS` includes the channel ID
- Check bot is online (green status in Discord)
- Review logs in `discord_bot.log`

### Firebase connection failed

- Verify Firebase credentials in `.env` or `credentials.json`
- Check `FIREBASE_DATABASE_URL` is correct
- Ensure Firebase rules allow read/write access
- Bot can fall back to local JSON storage if Firebase fails

### Task board not updating

- Check bot has "Send Messages" and "Embed Links" permissions
- Verify task board message wasn't deleted
- Try `!refresh` command to force update
- Check `TASK_BOARD_REFRESH_INTERVAL` setting

### User mapping not working

- Verify Discord user IDs are correct (enable Developer Mode)
- Check `.env` format: `DISCORD_USER_<id>=OwnerName`
- Restart bot after changing `.env`

## Deployment

### Systemd Service (Linux)

Create `/etc/systemd/system/taskmaster-bot.service`:

```ini
[Unit]
Description=Task-Master Discord Bot
After=network.target

[Service]
Type=simple
User=your-user
WorkingDirectory=/path/to/Task-Master/discord_bot
Environment="PATH=/path/to/venv/bin"
ExecStart=/path/to/venv/bin/python bot.py
Restart=always
RestartSec=10

[Install]
WantedBy=multi-user.target
```

Enable and start:
```bash
sudo systemctl enable taskmaster-bot
sudo systemctl start taskmaster-bot
sudo systemctl status taskmaster-bot
```

### Docker (Optional)

```dockerfile
FROM python:3.11-slim

WORKDIR /app

COPY requirements.txt .
RUN pip install --no-cache-dir -r requirements.txt

COPY . .

CMD ["python", "bot.py"]
```

Build and run:
```bash
docker build -t taskmaster-discord-bot .
docker run -d --name taskmaster-bot --env-file .env taskmaster-discord-bot
```

## Contributing

This bot is part of the Task-Master project. Contributions welcome!

## License

Same as Task-Master (MIT License)

## Authors

- Circuit
- Gelvey

## Support

For issues or questions, open an issue in the Task-Master GitHub repository.
```

---

## Implementation Checklist

When implementing this Discord bot, follow these steps:

### Phase 1: Setup (Day 1)
1. ✅ Create `discord_bot/` directory structure
2. ✅ Create all `__init__.py` files for Python packages
3. ✅ Install dependencies: `pip install -r discord_bot/requirements.txt`
4. ✅ Setup `.env` file with Discord bot token and channel IDs
5. ✅ Create Discord bot in Developer Portal and invite to server
6. ✅ Configure user mappings in `.env`

### Phase 2: Database Layer (Day 1-2)
1. ✅ Implement `database/task_model.py` with Task dataclass
2. ✅ Implement `database/firebase_manager.py` with DatabaseManager
3. ✅ Test database connection (Firebase or local fallback)
4. ✅ Verify task CRUD operations work correctly

### Phase 3: Configuration (Day 2)
1. ✅ Implement `config/settings.py` with environment variable loading
2. ✅ Test user mapping functionality
3. ✅ Validate all required settings present

### Phase 4: Discord UI (Day 2-3)
1. ✅ Implement `discord_ui/embeds.py` with task board and detail embeds
2. ✅ Implement `discord_ui/buttons.py` with button views
3. ✅ Implement `discord_ui/modals.py` with input forms
4. ✅ Implement `discord_ui/select_menus.py` with filter dropdowns
5. ✅ Test UI components in Discord (use test server)

### Phase 5: Services (Day 3-4)
1. ✅ Implement `services/task_service.py` with business logic
2. ✅ Implement `services/message_updater.py` for task board updates
3. ✅ Implement `services/reminder_service.py` for deadline notifications
4. ✅ Test service layer integration

### Phase 6: Main Bot (Day 4-5)
1. ✅ Implement `bot.py` with Discord client setup
2. ✅ Register event handlers (on_ready, on_interaction)
3. ✅ Implement background tasks (task board updater, reminder checker)
4. ✅ Add admin commands (!taskboard, !refresh, !help)
5. ✅ Test bot startup and initialization

### Phase 7: Testing (Day 5-6)
1. ✅ Test adding tasks via modal
2. ✅ Test editing tasks
3. ✅ Test deleting tasks
4. ✅ Test status changes (Complete, In Progress, To Do)
5. ✅ Test filtering (All, To Do, In Progress, Complete)
6. ✅ Test task board auto-refresh
7. ✅ Test reminder notifications (set deadline within 24 hours)
8. ✅ Test overdue notifications
9. ✅ Test with multiple users
10. ✅ Verify Firebase/local storage synchronization

### Phase 8: Integration Testing (Day 6)
1. ✅ Test cross-platform sync: Add task in web app, verify shows in Discord
2. ✅ Test cross-platform sync: Edit task in Discord, verify updates in web app
3. ✅ Test cross-platform sync: Delete task in desktop app, verify removes from Discord
4. ✅ Test with multiple users simultaneously
5. ✅ Verify owner assignment works correctly

### Phase 9: Documentation & Deployment (Day 7)
1. ✅ Complete README.md with setup instructions
2. ✅ Document environment variables in .env.example
3. ✅ Create deployment guide (systemd, Docker)
4. ✅ Add troubleshooting section
5. ✅ Deploy to production environment
6. ✅ Monitor logs for errors

### Phase 10: Polish (Ongoing)
1. ✅ Add error handling and user feedback
2. ✅ Optimize database queries
3. ✅ Add rate limiting if needed
4. ✅ Implement task reordering (drag-drop simulation)
5. ✅ Add more admin commands as needed

---

## Key Integration Points

### With Web App (`web_app/app.py`)
- **Shared Database**: Both use identical Firebase/local JSON structure
- **User Mapping**: Web app uses usernames, bot maps Discord IDs → usernames
- **Task Schema**: Exact same Task model with name, deadline, status, order, description, url, owner, colour

### With Desktop Client (`Task-Master.py`)
- **Shared Database**: Both use identical Firebase/local JSON structure  
- **Task Class**: Discord bot's Task dataclass mirrors desktop's Task class
- **Firebase Setup**: Same credentials.json and initialization logic

### Database Schema
```json
{
  "users": {
    "Circuit": {
      "tasks": {
        "Task Name": {
          "name": "Task Name",
          "deadline": "2026-12-31 23:59:00",
          "status": "To Do",
          "order": 0,
          "description": "Task description",
          "url": "https://example.com",
          "owner": "Circuit",
          "colour": "Important"
        }
      }
    }
  }
}
```

---

## Environment Variables Reference

```env
# Required
DISCORD_BOT_TOKEN=your_bot_token
TASK_CHANNELS=123456789,987654321
REMINDER_CHANNEL=111222333

# User Mappings (at least one required)
DISCORD_USER_<ID>=Task-Master-Owner

# Firebase (copy from main app)
FIREBASE_DATABASE_URL=...
FIREBASE_PROJECT_ID=...
# ... etc

# Optional
TASK_BOARD_REFRESH_INTERVAL=60
REMINDER_CHECK_INTERVAL=300
LOG_LEVEL=INFO
LOG_FILE=discord_bot.log
```

---

## Discord Bot Permissions

Required permissions (integer: 277025508416):
- View Channels
- Send Messages
- Embed Links
- Read Message History
- Add Reactions
- Use Application Commands

OAuth2 Scopes:
- `bot`
- `applications.commands`

---

## Testing Scenarios

1. **Single User Workflow**
   - Add task via Discord → Verify in web app
   - Edit task in web app → Verify in Discord
   - Complete task in desktop app → Verify in Discord

2. **Multi-User Workflow**  
   - User A adds task for themselves
   - User B adds task for themselves
   - Both see all tasks in Discord board
   - Filters work correctly per user

3. **Deadline Reminders**
   - Create task with deadline 12 hours away
   - Wait for reminder (or adjust interval for testing)
   - Verify reminder appears in reminder channel with correct mention

4. **Error Handling**
   - Try adding task with invalid deadline format
   - Try editing non-existent task
   - Try using bot in non-designated channel
   - Disconnect Firebase and verify local fallback

---

## Performance Considerations

- **Task Board Updates**: Default 60-second refresh. Adjust if database grows large.
- **Reminder Checks**: Default 5-minute interval. Can be reduced for faster reminders.
- **Message Editing**: Discord has rate limits (50 requests per second). Bot queues updates.
- **Database Queries**: Each task board update loads all users' tasks. Consider pagination for 100+ tasks.

---

## Future Enhancements

1. **Slash Commands**: Convert to Discord slash commands (/) for better discoverability
2. **Task Reordering**: Add drag-drop simulation using reactions/buttons
3. **Recurring Tasks**: Support repeating tasks (daily, weekly, etc.)
4. **Task Categories**: Add tags or categories beyond priorities
5. **Search**: Add search command to find tasks by keyword
6. **Statistics**: Add dashboard showing task completion stats
7. **Webhooks**: Add webhook support for external integrations
8. **Voice Commands**: Integrate with Discord voice channels for voice task management

---

## Security Considerations

1. **Environment Variables**: Never commit `.env` to git
2. **Firebase Rules**: Ensure proper read/write rules in Firebase console
3. **Bot Token**: Keep token secret, regenerate if exposed
4. **Channel Permissions**: Bot only operates in designated channels
5. **User Verification**: Bot verifies Discord user is in mapping before allowing operations
6. **Input Validation**: All user inputs validated before database operations

---

## Conclusion

This Discord bot provides a seamless, interactive interface for Task-Master directly within Discord. It maintains 100% compatibility with the existing web app and desktop client by sharing the same database backend and task schema.

The bot leverages Discord's modern UI components (modals, buttons, select menus) to create an intuitive task management experience without requiring users to type commands or learn special syntax.

Users can manage their tasks entirely through clicking buttons and filling out forms, while the task board automatically updates to reflect changes from any platform (Discord, web, desktop).

The reminder system proactively notifies users of upcoming deadlines, and the multi-user support with owner mapping allows teams to collaborate on tasks within their Discord server.

---

**Implementation Time Estimate**: 5-7 days for a Copilot agent with experience in Python, Discord.py, and Firebase.

**Maintenance**: Low - shares maintenance with main Task-Master application.

**Scalability**: Handles up to ~100 tasks per user smoothly. For larger scale, implement pagination and caching.

---

## Additional Resources

- [Discord.py Documentation](https://discordpy.readthedocs.io/)
- [Discord Developer Portal](https://discord.com/developers/docs)
- [Firebase Python Admin SDK](https://firebase.google.com/docs/admin/setup)
- [Discord UI Components Guide](https://discordpy.readthedocs.io/en/stable/interactions/api.html)

---

**END OF IMPLEMENTATION GUIDE**
