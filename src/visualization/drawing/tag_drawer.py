"""TagDrawer - handles drawing Git tags with emoji icons and tooltips."""

import tkinter as tk
from typing import Dict, List, Callable
from utils.data_structures import Commit
from utils.constants import NODE_RADIUS, BASE_MARGIN
from utils.theme_manager import get_theme_manager
from utils.logging_config import get_logger

logger = get_logger(__name__)


class TagDrawer:
    """Handles drawing Git tags with emoji icons and tooltips."""

    def __init__(self, canvas: tk.Canvas):
        self.canvas = canvas
        self.theme_manager = get_theme_manager()
        self.node_radius = NODE_RADIUS
        self.BASE_MARGIN = BASE_MARGIN

    def draw_tags(self, commits: List[Commit], table_start_position: int,
                 show_tooltip_callback: Callable,
                 hide_tooltip_callback: Callable) -> None:
        """Draws all tags for commits with tags.

        Args:
            commits: List of commits to draw tags for
            table_start_position: X position where table starts
            show_tooltip_callback: Callback to show tooltip
            hide_tooltip_callback: Callback to hide tooltip
        """
        emoji_font = ('Segoe UI Emoji', 10)  # Font for emoji
        text_font = ('Arial', 8, 'bold')     # Font for tag names

        if not any(commit.tags for commit in commits):
            return

        # Potomci každého commitu jednou předem - dřív se pro každý otagovaný
        # commit procházely všechny commity (tagy × commity operací)
        children = self._build_children_index(commits)
        commit_map = {c.hash: c for c in commits}

        for commit in commits:
            if not commit.tags:
                continue

            x, y = commit.x, commit.y

            # Detect collision with horizontal connections and dynamically shift tags
            horizontal_line_extent = self._calculate_horizontal_line_extent(
                commit, commits, children=children, commit_map=commit_map)

            # Standard position for tags
            standard_tag_x = x + self.node_radius + 15  # 15px space from circle

            # If horizontal connection reaches beyond standard tag position, shift tags
            if horizontal_line_extent > standard_tag_x:
                # Shift tags beyond end of longest horizontal connection + safe space
                tag_x_start = horizontal_line_extent + 20  # 20px safe space
            else:
                # Use standard position
                tag_x_start = standard_tag_x

            # Calculate real available space for tags up to table start
            available_tag_space = table_start_position - tag_x_start - self.BASE_MARGIN

            # Calculate available space for individual tags of this commit
            tags_total_space = max(0, available_tag_space)  # Ensure not negative
            tags_count = len(commit.tags)

            if tags_count > 0:
                # Reserve space for emoji and spacing
                emoji_and_spacing_width = tags_count * 15 + (tags_count - 1) * 20  # emoji + spaces between tags
                available_text_space = max(0, tags_total_space - emoji_and_spacing_width)

                # Minimal width for text of one tag (to fit at least 3 chars + ellipsis)
                min_text_width_per_tag = 30

                # Calculate maximum text width per tag
                if available_text_space > 0 and tags_count > 0:
                    max_text_width_per_tag = max(min_text_width_per_tag, available_text_space // tags_count)
                else:
                    max_text_width_per_tag = min_text_width_per_tag

            current_x = tag_x_start
            for tag in commit.tags:
                # Draw tag emoji
                emoji_x = current_x
                self._draw_tag_emoji(emoji_x, y, tag.is_remote, emoji_font)

                # Draw tag name next to emoji with limited width
                text_x = emoji_x + 15  # 15px space after emoji
                label_width = self._draw_tag_label(text_x, y, tag.name, tag.is_remote,
                                                   text_font, max_text_width_per_tag,
                                                   show_tooltip_callback, hide_tooltip_callback)

                # Add tooltip for annotated tags
                if tag.message:
                    self._add_tag_tooltip(emoji_x, y, tag.message, show_tooltip_callback, hide_tooltip_callback)

                # Move position for next tag
                current_x = text_x + label_width + 20  # 20px space between tags

    def _draw_tag_emoji(self, x: int, y: int, is_remote: bool, font):
        """Draws tag emoji 🏷️."""
        # Tag emoji
        tag_emoji = "🏷️"

        tm = get_theme_manager()
        # Color distinction - use grayer color for remote tags
        if is_remote:
            # For remote use lighter/smaller emoji or different approach
            text_color = tm.get_color('tag_emoji_remote')
        else:
            text_color = tm.get_color('tag_emoji_local')

        self.canvas.create_text(
            x, y - 1,
            text=tag_emoji,
            anchor='center',
            font=font,
            fill=text_color,
            tags="tag_emoji"
        )

    def _draw_tag_label(self, x: int, y: int, tag_name: str, is_remote: bool, font,
                       available_width: int = None,
                       show_tooltip_callback: Callable = None,
                       hide_tooltip_callback: Callable = None):
        """Draws label with tag name and returns text width.

        Args:
            x: X position
            y: Y position
            tag_name: Tag name to display
            is_remote: Whether this is a remote tag
            font: Font to use
            available_width: Available width for text
            show_tooltip_callback: Callback to show tooltip
            hide_tooltip_callback: Callback to hide tooltip

        Returns:
            Width of displayed text
        """
        display_name = tag_name
        needs_tooltip = False

        # Truncate name if too long
        if available_width and available_width > 0:
            full_width = self.canvas.tk.call("font", "measure", font, tag_name)
            if full_width > available_width:
                # Name is too long, truncate it
                display_name = self._truncate_text_to_width(tag_name, font, available_width)
                needs_tooltip = True

        tm = get_theme_manager()
        # Text colors - more consistent with emoji
        text_color = tm.get_color('tag_text_remote') if is_remote else tm.get_color('tag_text_local')

        text_item = self.canvas.create_text(
            x, y,
            text=display_name,
            anchor='w',  # Align left instead of center
            font=font,
            fill=text_color,
            tags="tag_label"
        )

        # Add tooltip if text was truncated
        if needs_tooltip and show_tooltip_callback and hide_tooltip_callback:
            self.canvas.tag_bind(text_item, "<Enter>",
                lambda e, full_name=tag_name: show_tooltip_callback(e, full_name))
            self.canvas.tag_bind(text_item, "<Leave>",
                lambda e: hide_tooltip_callback())

        # Return width of displayed text for calculating next tag position
        text_width = self.canvas.tk.call("font", "measure", font, display_name)
        return text_width

    def _add_tag_tooltip(self, x: int, y: int, message: str,
                        show_tooltip_callback: Callable,
                        hide_tooltip_callback: Callable):
        """Adds tooltip for annotated tags."""
        # Create invisible area for tooltip
        tooltip_area = self.canvas.create_oval(
            x - 12, y - 12, x + 12, y + 12,
            fill='',
            outline='',
            tags="tag_tooltip_area"
        )

        # Bind tooltip events
        self.canvas.tag_bind(tooltip_area, "<Enter>",
            lambda e, msg=message: show_tooltip_callback(e, msg))
        self.canvas.tag_bind(tooltip_area, "<Leave>",
            lambda e: hide_tooltip_callback())

    def calculate_required_tag_space(self, flag_width: int) -> int:
        """Estimates space needed for tags (simplified version - now calculated dynamically).

        Args:
            flag_width: Width of flag

        Returns:
            Estimated space needed for tags
        """
        # Fixed estimate of space for tags - real space is calculated dynamically in _draw_tags
        # This estimate serves only for calculating total graph column width
        return flag_width + self.BASE_MARGIN

    @staticmethod
    def _build_children_index(commits: List[Commit]) -> Dict[str, List[Commit]]:
        """Mapa hash rodiče -> potomci."""
        children: Dict[str, List[Commit]] = {}
        for commit in commits:
            for parent_hash in commit.parents:
                children.setdefault(parent_hash, []).append(commit)
        return children

    @staticmethod
    def _corner_radius(dx: int, dy: int) -> float:
        # Same logic as ConnectionDrawer._draw_bezier_curve (curve_intensity 0.8)
        radius = min(dx, dy, 20) * 0.8
        return max(3, min(radius, 15))

    def _calculate_horizontal_line_extent(self, commit: Commit, commits: List[Commit],
                                          children: Dict[str, List[Commit]] = None,
                                          commit_map: Dict[str, Commit] = None) -> int:
        """Calculates how far right horizontal connections reach in this commit's row.

        Vodorovné části spojnic (viz ConnectionDrawer) leží v řádku commitu:
        - u odbočky z tohoto commitu (potomek v jiném sloupci, ne merge hrana)
          vede čára k potomkovi v řádku rodiče = tohoto commitu;
        - u merge commitu vede čára od 2.+ rodiče v řádku merge commitu.

        Args:
            commit: Commit to calculate extent for
            commits: All commits
            children: Precomputed parent hash -> children (optional, for speed)
            commit_map: Precomputed hash -> commit (optional, for speed)

        Returns:
            Maximum horizontal extent in pixels
        """
        if children is None:
            children = self._build_children_index(commits)
        if commit_map is None:
            commit_map = {c.hash: c for c in commits}

        max_extent = commit.x  # Default commit position

        # Branching connections: horizontal part in THIS commit's row, towards the child
        for child in children.get(commit.hash, []):
            is_merge_connection = len(child.parents) >= 2 and child.parents.index(commit.hash) > 0
            if is_merge_connection or child.x == commit.x:
                continue
            dx = abs(child.x - commit.x)
            radius = self._corner_radius(dx, abs(child.y - commit.y))
            horizontal_end = child.x - radius if dx > radius else child.x
            max_extent = max(max_extent, horizontal_end)

        # Merge connections into this commit: horizontal part in this row, from the merged parent
        if len(commit.parents) >= 2:
            for parent_hash in commit.parents[1:]:
                parent = commit_map.get(parent_hash)
                if parent is None or parent.x <= commit.x:
                    continue
                max_extent = max(max_extent, parent.x)

        return max_extent

    def _truncate_text_to_width(self, text: str, font, max_width: int) -> str:
        """Truncates text to fit within specified width in pixels.

        Args:
            text: Text to truncate
            font: Font to use
            max_width: Maximum width in pixels

        Returns:
            Truncated text with ellipsis if needed
        """
        if not text or max_width <= 0:
            return ""

        # Measure width of full text
        text_width = self.canvas.tk.call("font", "measure", font, text)

        if text_width <= max_width:
            return text

        # Text is too wide, truncate it
        ellipsis_width = self.canvas.tk.call("font", "measure", font, "...")
        available_width = max_width - ellipsis_width

        if available_width <= 0:
            return "..."

        # Binary search to find correct length
        left, right = 0, len(text)
        result = ""

        while left <= right:
            mid = (left + right) // 2
            test_text = text[:mid]
            test_width = self.canvas.tk.call("font", "measure", font, test_text)

            if test_width <= available_width:
                result = test_text
                left = mid + 1
            else:
                right = mid - 1

        return result + "..." if result else "..."
