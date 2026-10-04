from typing import Optional, List, Dict, Any
import logging
from discord.ui import View, Button, Select
from discord import Interaction, Embed

logger = logging.getLogger(__name__)

class RosterUI:
    """Handles UI interactions for the wowroster cog."""

    def __init__(self, config: Dict[str, Any]):
        """Initialize with configuration parameters."""
        self.config = config

    async def setup_view(self, interaction: Interaction) -> None:
        """Create and send the setup view for character configuration."""
        view = View()

        # Add spec selection dropdown
        spec_select = Select(
            placeholder="Select your class/spec",
            options=[
                SelectOption(label="Warrior", value="warrior"),
                SelectOption(label="Paladin", value="paladin"),
                SelectOption(label="Hunter", value="hunter")
            ]
        )
        spec_select.callback = self.handle_spec_selection
        view.add_item(spec_select)

        # Add confirm button
        confirm_btn = Button(label="Confirm", style=ButtonStyle.GREEN)
        confirm_btn.callback = self.handle_confirm
        view.add_item(confirm_btn)

        await interaction.response.send_message("Please configure your character:", view=view)

    async def handle_spec_selection(self, interaction: Interaction) -> None:
        """Handle spec selection from the dropdown."""
        spec = interaction.values[0]
        # Store selected spec in configuration
        self.config['user']['spec'] = spec
        await interaction.response.send_message(f"Selected spec: {spec}", ephemeral=True)

    async def handle_confirm(self, interaction: Interaction) -> None:
        """Handle confirmation of character setup."""
        # Validate configuration
        if not self.config['user'].get('spec'):
            await interaction.response.send_message("Please select a spec before confirming.", ephemeral=True)
            return

        # Build and send roster embed
        embed = Embed(title="Roster Setup Complete",
                      description=f"Character configured with spec: {self.config['user']['spec']}",
                      color=0x00ff00)
        await interaction.response.send_message(embed=embed)
        await interaction.message.delete()