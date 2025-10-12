"""TooltipManager - handles showing and hiding tooltips."""

import tkinter as tk
from utils.theme_manager import get_theme_manager


class TooltipManager:
    """Manages all tooltips (show/hide, positioning)."""

    def __init__(self):
        self.tooltip = None
        self.theme_manager = get_theme_manager()

    def show_tooltip(self, event, description_text: str):
        """Displays tooltip with complete description text.

        Args:
            event: Mouse event with position information
            description_text: Text to display in tooltip
        """
        if not description_text or not description_text.strip():
            return

        self.hide_tooltip()

        # Create tooltip window
        self.tooltip = tk.Toplevel()
        self.tooltip.wm_overrideredirect(True)
        self.tooltip.wm_attributes("-topmost", True)

        # Set tooltip window position
        x = event.x_root + 10
        y = event.y_root + 10
        self.tooltip.wm_geometry(f"+{x}+{y}")

        # Create label with text
        label = tk.Label(
            self.tooltip,
            text=description_text,
            background=self.theme_manager.get_color('tooltip_bg'),
            foreground=self.theme_manager.get_color('tooltip_fg'),
            font=('Arial', 9),
            wraplength=400,
            justify="left",
            relief="solid",
            borderwidth=1,
            padx=5,
            pady=3
        )
        label.pack()

    def hide_tooltip(self):
        """Hides tooltip window."""
        if self.tooltip:
            self.tooltip.destroy()
            self.tooltip = None
