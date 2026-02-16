"""
Discord button components for task interactions
"""
import discord
from discord.ui import Button, View


class ConfirmationButtons(View):
    """Generic confirmation buttons"""

    def __init__(self, timeout=60, requester_id: int = None):
        super().__init__(timeout=timeout)
        self.value = None
        self.requester_id = requester_id

    async def interaction_check(self, interaction: discord.Interaction) -> bool:
        if self.requester_id is not None and interaction.user.id != self.requester_id:
            await interaction.response.send_message(
                "❌ Only the user who requested this action can confirm it.",
                ephemeral=True
            )
            return False
        return True

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
