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
