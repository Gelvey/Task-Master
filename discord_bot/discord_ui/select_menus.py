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
        
        # Add buttons from TaskBoardButtons inline
        from .buttons import TaskBoardButtons
        # Copy buttons from TaskBoardButtons to this view
        button_view = TaskBoardButtons()
        for item in button_view.children:
            self.add_item(item)
