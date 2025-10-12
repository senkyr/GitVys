"""BranchFlagDrawer - handles drawing branch flags and their connections."""

import tkinter as tk
from typing import List, Set
from utils.data_structures import Commit
from utils.constants import BASE_MARGIN, LINE_WIDTH, NODE_RADIUS
from utils.theme_manager import get_theme_manager
from utils.logging_config import get_logger

logger = get_logger(__name__)


class BranchFlagDrawer:
    """Handles drawing branch flags (labels) and their connections to commits."""

    def __init__(self, canvas: tk.Canvas):
        self.canvas = canvas
        self.theme_manager = get_theme_manager()
        self.BASE_MARGIN = BASE_MARGIN
        self.line_width = LINE_WIDTH
        self.node_radius = NODE_RADIUS
        self.flag_width = None  # Will be calculated
        self.flag_tooltips = {}  # Store tooltip tags

    def calculate_flag_width(self, commits: List[Commit]) -> int:
        """Calculates uniform flag width based on longest branch name with room for symbols.

        Args:
            commits: List of commits to calculate width for

        Returns:
            Calculated flag width
        """
        font = ('Arial', 8, 'bold')  # Font used for flags (updated to correct size)
        max_text_width = 0

        # Find all unique branch names for width calculation
        unique_branches = set()
        for commit in commits:
            if commit.branch == 'unknown':
                continue  # Skip unknown branches

            branch_name = commit.branch
            is_remote = commit.is_remote

            # Adjust branch name for remote branches
            display_name = branch_name
            if is_remote and branch_name.startswith('origin/'):
                display_name = branch_name[7:]  # Remove "origin/"

            # Truncate name for width calculation
            truncated_name = self._truncate_branch_name(display_name)
            unique_branches.add(truncated_name)

        # Find longest branch name
        for display_name in unique_branches:
            # Measure width of clean branch name text
            try:
                text_width = self.canvas.tk.call("font", "measure", font, display_name)
                max_text_width = max(max_text_width, text_width)
            except Exception as e:
                logger.warning(f"Failed to measure text width for branch {display_name}: {e}")
                # Fallback in case of error
                max_text_width = max(max_text_width, len(display_name) * 6)

        # Total flag width calculation:
        # - Symbols at edges: 12px (left) + 12px (right) = 24px
        # - Padding between symbols and text: 12px (left) + 12px (right) = 24px (increased for better spacing)
        # - Text width: max_text_width
        symbol_space = 24  # Space for symbols at edges
        padding = 24       # Padding between symbols and text (increased from 16 to 24)

        self.flag_width = symbol_space + padding + max_text_width

        # Minimum width 90px (to fit symbols with bigger padding), maximum reasonable width 120px (reduced)
        self.flag_width = max(90, min(self.flag_width, 120))
        return self.flag_width

    def draw_branch_flag(self, x: int, y: int, branch_name: str, branch_color: str,
                        is_remote: bool = False, branch_availability: str = "local_only"):
        """Draws flag with branch name and availability symbols in fixed left column.

        Args:
            x: X position of commit
            y: Y position of commit
            branch_name: Branch name to display
            branch_color: Branch color
            is_remote: Whether this is a remote branch
            branch_availability: Branch availability ("local_only", "remote_only", "both")
        """
        # Use calculated flag width
        flag_width = self.flag_width if self.flag_width else 80  # Fallback to 80 if not calculated
        flag_height = 20

        # Flag position - margin from left same as margin from top (BASE_MARGIN + half flag width)
        flag_x = self.BASE_MARGIN + flag_width // 2
        flag_y = y

        # Uniform black border (remote status is visible from emoji)
        outline_color = 'black'

        # Create flag rectangle
        self.canvas.create_rectangle(
            flag_x - flag_width // 2, flag_y - flag_height // 2,
            flag_x + flag_width // 2, flag_y + flag_height // 2,
            fill=branch_color,
            outline=outline_color,
            width=1
        )

        # Add branch name text - adjust for remote branches
        display_name = branch_name
        if is_remote and branch_name.startswith('origin/'):
            # Display only part after origin/ but in different color
            display_name = branch_name[7:]  # Remove "origin/"

        # Truncate name for display
        full_name = display_name  # Save for tooltip
        display_name = self._truncate_branch_name(display_name)

        # Determine which symbols to display according to branch availability
        has_local = branch_availability in ["local_only", "both"]
        has_remote = branch_availability in ["remote_only", "both"]

        local_symbol = "💻"  # Laptop for local
        remote_symbol = "☁"  # Outline cloud for remote
        local_fallback = "PC"
        remote_fallback = "☁"

        tm = get_theme_manager()
        emoji_font = ('Segoe UI Emoji', 10)  # Correct font for emoji
        text_font = ('Arial', 8, 'bold')     # Font for text

        # Calculate contrasting text color based on branch color (not on remote)
        # This ensures readability on any branch color
        text_color = tm.get_contrasting_text_color(
            branch_color,
            dark_color='#000000',
            light_color='#ffffff'
        )

        # Outline must be opposite color from text for maximum contrast
        outline_color = '#ffffff' if text_color == '#000000' else '#000000'

        # Always draw branch name in center with contrasting outline
        # First outline - draw text shifted by 1px in all directions
        for dx, dy in [(-1,-1), (-1,1), (1,-1), (1,1)]:
            self.canvas.create_text(
                flag_x + dx, flag_y + dy,
                text=display_name,
                anchor='center',
                font=text_font,
                fill=outline_color
            )

        # Then text on top in contrasting color
        text_item = self.canvas.create_text(
            flag_x, flag_y,
            text=display_name,
            anchor='center',
            font=text_font,
            fill=text_color
        )

        # Add tooltip if text was truncated
        if full_name != display_name:
            self._add_tooltip_to_flag(text_item, flag_x, flag_y, flag_width, flag_height, full_name)

        # Draw remote symbol on left if branch exists remotely
        # Symbols use same contrasting colors as text
        if has_remote:
            remote_x = flag_x - flag_width // 2 + 12  # 12px from left edge of flag (increased padding)
            try:
                # First outline for cloud symbol (opposite color from text)
                for dx, dy in [(-1,-1), (-1,1), (1,-1), (1,1)]:
                    self.canvas.create_text(
                        remote_x + dx, flag_y - 1 + dy,
                        text=remote_symbol,
                        anchor='center',
                        font=emoji_font,
                        fill=outline_color
                    )
                # Then symbol on top in contrasting color
                self.canvas.create_text(
                    remote_x, flag_y - 1,
                    text=remote_symbol,
                    anchor='center',
                    font=emoji_font,
                    fill=text_color
                )
            except Exception as e:
                logger.debug(f"Failed to render remote symbol with emoji font: {e}")
                # Fallback - also with outline
                for dx, dy in [(-1,-1), (-1,1), (1,-1), (1,1)]:
                    self.canvas.create_text(
                        remote_x + dx, flag_y - 1 + dy,
                        text=remote_fallback,
                        anchor='center',
                        font=text_font,
                        fill=outline_color
                    )
                self.canvas.create_text(
                    remote_x, flag_y - 1,
                    text=remote_fallback,
                    anchor='center',
                    font=text_font,
                    fill=text_color
                )

        # Draw local symbol on right if branch exists locally
        # Symbols use same contrasting colors as text
        if has_local:
            local_x = flag_x + flag_width // 2 - 12  # 12px from right edge of flag (increased padding)
            try:
                # First outline for laptop symbol (opposite color from text)
                for dx, dy in [(-1,-1), (-1,1), (1,-1), (1,1)]:
                    self.canvas.create_text(
                        local_x + dx, flag_y - 1 + dy,
                        text=local_symbol,
                        anchor='center',
                        font=emoji_font,
                        fill=outline_color
                    )
                # Then symbol on top in contrasting color
                self.canvas.create_text(
                    local_x, flag_y - 1,
                    text=local_symbol,
                    anchor='center',
                    font=emoji_font,
                    fill=text_color
                )
            except Exception as e:
                logger.debug(f"Failed to render local symbol with emoji font: {e}")
                # Fallback - also with outline
                for dx, dy in [(-1,-1), (-1,1), (1,-1), (1,1)]:
                    self.canvas.create_text(
                        local_x + dx, flag_y - 1 + dy,
                        text=local_fallback,
                        anchor='center',
                        font=text_font,
                        fill=outline_color
                    )
                self.canvas.create_text(
                    local_x, flag_y - 1,
                    text=local_fallback,
                    anchor='center',
                    font=text_font,
                    fill=text_color
                )

    def draw_flag_connection(self, commit_x: int, commit_y: int, branch_color: str):
        """Draws horizontal connection from commit to flag.

        Args:
            commit_x: X position of commit
            commit_y: Y position of commit
            branch_color: Branch color for connection
        """
        # Use calculated flag width
        flag_width = self.flag_width if self.flag_width else 80

        # Flag position (consistent with _draw_branch_flag)
        flag_x = self.BASE_MARGIN + flag_width // 2

        # Horizontal line from commit to flag
        self.canvas.create_line(
            flag_x + flag_width // 2 + 1, commit_y,  # From right edge of flag + 1px outside border
            commit_x - self.node_radius, commit_y,  # To left edge of commit
            fill=branch_color,
            width=self.line_width
        )

    def _truncate_branch_name(self, branch_name: str, max_length: int = 12) -> str:
        """Truncates branch name if too long.

        Args:
            branch_name: Branch name to truncate
            max_length: Maximum length

        Returns:
            Truncated branch name with ellipsis if needed
        """
        if len(branch_name) <= max_length:
            return branch_name
        return branch_name[:max_length-3] + "..."

    def _add_tooltip_to_flag(self, flag_item, flag_x, flag_y, flag_width, flag_height, full_name):
        """Adds tooltip functionality to flag.

        Args:
            flag_item: Canvas item ID of flag
            flag_x: X position of flag center
            flag_y: Y position of flag center
            flag_width: Width of flag
            flag_height: Height of flag
            full_name: Full branch name to display in tooltip
        """
        tooltip_tag = None

        def show_tooltip(event):
            nonlocal tooltip_tag
            if tooltip_tag:
                return

            # Create unique tag for this tooltip
            tooltip_tag = f"tooltip_{id(flag_item)}_{id(event)}"

            # Calculate dynamic width based on text length
            # Approximately 6px per character + padding
            text_width = len(full_name) * 6 + 20
            tooltip_height = 20

            # Determine tooltip position
            tooltip_top_y = flag_y + flag_height // 2 + 5
            tooltip_bottom_y = tooltip_top_y + tooltip_height

            # Determine horizontal position - default centered
            tooltip_left_x = flag_x - text_width // 2
            tooltip_right_x = flag_x + text_width // 2

            # Get canvas width
            canvas_width = self.canvas.winfo_width()

            # Check overflow right
            if tooltip_right_x > canvas_width:
                # Shift left so right edge is at canvas_width
                offset = tooltip_right_x - canvas_width
                tooltip_left_x -= offset
                tooltip_right_x -= offset

            # Check overflow left
            if tooltip_left_x < 0:
                # Shift right so left edge is at 0
                offset = -tooltip_left_x
                tooltip_left_x += offset
                tooltip_right_x += offset

            # Calculate center for text
            tooltip_center_x = (tooltip_left_x + tooltip_right_x) // 2

            tm = get_theme_manager()

            # Create tooltip window with tag
            self.canvas.create_rectangle(
                tooltip_left_x, tooltip_top_y,
                tooltip_right_x, tooltip_bottom_y,
                fill=tm.get_color('tag_tooltip_bg'), outline=tm.get_color('commit_node_outline'), width=1,
                tags=tooltip_tag
            )

            self.canvas.create_text(
                tooltip_center_x, tooltip_top_y + tooltip_height // 2,
                text=full_name,
                anchor='center',
                font=('Arial', 8),
                fill=tm.get_color('tooltip_fg'),
                tags=tooltip_tag
            )

        def hide_tooltip(event):
            nonlocal tooltip_tag
            if tooltip_tag:
                self.canvas.delete(tooltip_tag)
                tooltip_tag = None

        # Bind events to entire flag area
        self.canvas.tag_bind(flag_item, '<Enter>', show_tooltip)
        self.canvas.tag_bind(flag_item, '<Leave>', hide_tooltip)
