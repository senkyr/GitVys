"""TextFormatter - handles text formatting, truncation, and DPI handling."""

import tkinter as tk
from typing import List, Dict
from utils.data_structures import Commit
from utils.constants import FONT_SIZE
from utils.logging_config import get_logger

logger = get_logger(__name__)


class TextFormatter:
    """Handles text formatting - truncation, DPI handling, width measurement."""

    def __init__(self, canvas: tk.Canvas):
        self.canvas = canvas
        self.font_size = FONT_SIZE
        self.scaling_factor = self._detect_scaling_factor()
        self.max_description_length = 50  # Base length

    def detect_scaling_factor(self) -> float:
        """Detects DPI scaling factor.

        Returns:
            DPI scaling factor (1.0 = 100%, 1.25 = 125%, etc.)
        """
        try:
            dpi = self.canvas.winfo_fpixels('1i')
            self.scaling_factor = dpi / 96  # 96 is standard DPI
        except Exception as e:
            logger.warning(f"Failed to detect DPI scaling factor: {e}")
            self.scaling_factor = 1.0  # Fallback
        return self.scaling_factor

    def adjust_descriptions_for_scaling(self, commits: List[Commit]):
        """Adjusts description_short length according to DPI scaling.

        Args:
            commits: List of commits to adjust descriptions for
        """
        # Calculate target length according to scaling
        if self.scaling_factor <= 1.0:
            target_length = 120  # Increased for better space utilization
        elif self.scaling_factor <= 1.25:
            target_length = 100  # 125% scaling
        elif self.scaling_factor <= 1.5:
            target_length = 80  # 150% scaling
        else:
            target_length = 60  # 200%+ scaling

        self.max_description_length = target_length

        # Adjust description_short for all commits according to correct logic
        for commit in commits:
            commit.description_short = self._truncate_description_for_dpi(commit.description, target_length)

    def truncate_description_for_dpi(self, description: str, max_length: int) -> str:
        """Truncates description according to specification with respect to DPI scaling.

        Args:
            description: Description to truncate
            max_length: Maximum length

        Returns:
            Truncated description with ellipsis if needed
        """
        if not description:
            return ""

        # Take only first line
        first_line = description.split('\n')[0].strip()
        has_more_lines = '\n' in description

        # Determine if we need ellipsis
        needs_ellipsis = False

        if has_more_lines:
            # If has more lines, always need ellipsis
            needs_ellipsis = True
        elif len(first_line) > max_length:
            # If first line is too long
            needs_ellipsis = True
        elif first_line.endswith(':'):
            # If line ends with colon, also need ellipsis
            needs_ellipsis = True

        # Truncate text if needed and add ellipsis
        if needs_ellipsis:
            if first_line.endswith(':'):
                # If ends with colon, replace it with three dots
                # but verify it fits in limit
                potential_result = first_line[:-1] + '...'
                if len(potential_result) > max_length:
                    # Truncate even more so ellipsis fits
                    first_line = first_line[:max_length-3] + '...'
                else:
                    first_line = potential_result
            elif len(first_line) > max_length:
                # Normal truncation
                first_line = first_line[:max_length-3] + '...'
            else:
                # Text fits but has more lines
                first_line = first_line + '...'

        return first_line

    def truncate_text_to_width(self, canvas: tk.Canvas, font, text: str, max_width: int) -> str:
        """Truncates text to fit within specified width in pixels.

        Args:
            canvas: Canvas to measure text on
            font: Font to use
            text: Text to truncate
            max_width: Maximum width in pixels

        Returns:
            Truncated text with ellipsis if needed
        """
        if not text or max_width <= 0:
            return ""

        # Measure width of entire text
        text_width = canvas.tk.call("font", "measure", font, text)

        if text_width <= max_width:
            return text

        # Text is too wide, truncate it
        ellipsis_width = canvas.tk.call("font", "measure", font, "...")
        available_width = max_width - ellipsis_width

        if available_width <= 0:
            return "..."

        # Binary search to find correct length
        left, right = 0, len(text)
        result = ""

        while left <= right:
            mid = (left + right) // 2
            test_text = text[:mid]
            test_width = canvas.tk.call("font", "measure", font, test_text)

            if test_width <= available_width:
                result = test_text
                left = mid + 1
            else:
                right = mid - 1

        return result + "..." if result else "..."

    def recalculate_descriptions_for_width(self, canvas: tk.Canvas, commits: List[Commit],
                                          column_widths: Dict):
        """Recalculates description texts according to current message column width.

        Args:
            canvas: Canvas to measure text on
            commits: List of commits to recalculate descriptions for
            column_widths: Dictionary with column widths
        """
        font = ('Arial', self.font_size)

        for commit in commits:
            if not commit.description:
                commit.description_short = ""
                continue

            # Apply original truncation logic according to DPI scaling
            commit.description_short = self._truncate_description_for_dpi(
                commit.description, self.max_description_length
            )

            # If description is empty, continue
            if not commit.description_short:
                continue

            # Calculate available space for description in message column
            message_width = canvas.tk.call("font", "measure", font, commit.message)
            available_space = column_widths['message'] - message_width - 40  # 40px margins

            # Truncate description to fit available space
            if available_space > 0:
                commit.description_short = self.truncate_text_to_width(
                    canvas, font, commit.description_short, available_space
                )
            else:
                # If no space, hide description
                commit.description_short = ""

    def _detect_scaling_factor(self) -> float:
        """Internal method to detect DPI scaling factor."""
        try:
            dpi = self.canvas.winfo_fpixels('1i')
            return dpi / 96  # 96 is standard DPI
        except Exception as e:
            logger.warning(f"Failed to detect DPI scaling factor: {e}")
            return 1.0  # Fallback

    def _truncate_description_for_dpi(self, description: str, max_length: int) -> str:
        """Internal method to truncate description (calls public method)."""
        return self.truncate_description_for_dpi(description, max_length)
