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
