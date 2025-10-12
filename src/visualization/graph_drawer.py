"""GraphDrawer - orchestrator for graph rendering components."""

import tkinter as tk
from typing import List, Dict
from utils.data_structures import Commit
from utils.logging_config import get_logger
from utils.theme_manager import get_theme_manager
from utils.constants import (
    NODE_RADIUS, LINE_WIDTH, FONT_SIZE, SEPARATOR_HEIGHT,
    MIN_COLUMN_WIDTH_TEXT, MIN_COLUMN_WIDTH_GRAPH,
    HEADER_HEIGHT, BASE_MARGIN, BRANCH_LANE_SPACING
)

# Import all drawing and UI components
from visualization.drawing import (
    ConnectionDrawer,
    CommitDrawer,
    TagDrawer,
    BranchFlagDrawer
)
from visualization.ui import (
    ColumnManager,
    TooltipManager,
    TextFormatter
)
from visualization.colors import make_color_pale

logger = get_logger(__name__)


class GraphDrawer:
    """Main orchestrator for graph rendering - delegates to specialized components."""

    def __init__(self):
        self.node_radius = NODE_RADIUS
        self.line_width = LINE_WIDTH
        self.font_size = FONT_SIZE
        self.column_widths = {}
        self.branch_lanes = {}  # Store lanes for calculating table position
        self.curve_intensity = 0.8  # Intensity of curve rounding (0-1)

        # Layout constants - unified margin system
        self.HEADER_HEIGHT = HEADER_HEIGHT  # Header/separator height
        self.BASE_MARGIN = BASE_MARGIN    # Base margin (same as header height)
        self.BRANCH_SPACING = BRANCH_LANE_SPACING # Distance between branches (lanes)

        # Old name for backward compatibility
        self.separator_height = self.HEADER_HEIGHT

        # Component instances - lazy initialized
        self.connection_drawer = None
        self.commit_drawer = None
        self.tag_drawer = None
        self.branch_flag_drawer = None
        self.column_manager = None
        self.tooltip_manager = None
        self.text_formatter = None

        # Cached values for width calculations
        self.flag_width = None
        self.required_tag_space = None

    def reset(self):
        """Resets GraphDrawer state for new repository."""
        # Reset column widths - user-set and calculated
        if self.column_manager:
            self.column_manager.graph_column_width = None
            self.column_manager.user_column_widths = {}
        self.column_widths = {}

        # Reset cached values for width calculations
        self.flag_width = None
        self.required_tag_space = None

        # Reset interactive functions
        if self.column_manager:
            self.column_manager.dragging_separator = None
            self.column_manager.drag_start_x = 0
            self.column_manager.column_separators = {}

        # Hide tooltip
        if self.tooltip_manager:
            self.tooltip_manager.hide_tooltip()

    def draw_graph(self, canvas: tk.Canvas, commits: List[Commit]):
        """Main entry point - orchestrates entire graph rendering.

        Delegates to individual components in this order:
        1. ConnectionDrawer - connections
        2. CommitDrawer - commit nodes
        3. TagDrawer - tags
        4. BranchFlagDrawer - branch flags
        5. ColumnManager - separators

        Args:
            canvas: Canvas to draw on
            commits: List of commits to draw
        """
        if not commits:
            return

        # Save commits for potential redraw
        self._current_commits = commits

        # Initialize components if needed
        if not self.connection_drawer:
            self._initialize_components(canvas)

        # Detect DPI scaling
        self.text_formatter.detect_scaling_factor()

        # Adjust description_short according to scaling
        self.text_formatter.adjust_descriptions_for_scaling(commits)

        # Calculate flag_width before other calculations that use it
        self.flag_width = self.branch_flag_drawer.calculate_flag_width(commits)

        # Update lanes information for calculating table position
        self._update_branch_lanes(commits)

        # Calculate column widths
        self._calculate_column_widths(canvas, commits)

        # Calculate required tag space
        self._calculate_required_tag_space()

        # Get table start position for use by drawing components
        table_start_x = self._get_table_start_position()

        # Delegate drawing to components
        self.connection_drawer.draw_connections(commits, self._make_color_pale)

        self.commit_drawer.draw_commits(
            commits,
            self.column_widths,
            self.tooltip_manager.show_tooltip,
            self.tooltip_manager.hide_tooltip,
            self.text_formatter.truncate_text_to_width,
            table_start_x,
            self._make_color_pale,
            self.branch_flag_drawer,
            self.branch_flag_drawer.draw_flag_connection
        )

        self.tag_drawer.draw_tags(
            commits,
            table_start_x,
            self.tooltip_manager.show_tooltip,
            self.tooltip_manager.hide_tooltip
        )

        self.column_manager.setup_column_separators(self.column_widths, table_start_x)

    def _initialize_components(self, canvas: tk.Canvas):
        """Initializes all drawing and UI components.

        Args:
            canvas: Canvas to use for components
        """
        self.connection_drawer = ConnectionDrawer(canvas)
        self.commit_drawer = CommitDrawer(canvas)
        self.tag_drawer = TagDrawer(canvas)
        self.branch_flag_drawer = BranchFlagDrawer(canvas)
        self.column_manager = ColumnManager(canvas)
        self.tooltip_manager = TooltipManager()
        self.text_formatter = TextFormatter(canvas)

    def _calculate_column_widths(self, canvas: tk.Canvas, commits: List[Commit]):
        """Calculates column widths based on content.

        Args:
            canvas: Canvas to measure text on
            commits: List of commits
        """
        # Use standard font - scaling is handled by text length, not font size
        font = ('Arial', self.font_size)

        max_message_width = 0
        max_description_width = 0
        max_author_width = 0
        max_email_width = 0
        max_date_width = 0

        # Define maximum widths according to DPI scaling
        scaling_factor = self.text_formatter.scaling_factor
        if scaling_factor <= 1.0:
            max_allowed_message_width = 800  # Increased for better space utilization
            max_allowed_author_width = 250
            max_allowed_email_width = 300
        elif scaling_factor <= 1.25:
            max_allowed_message_width = 700  # 125% scaling
            max_allowed_author_width = 220
            max_allowed_email_width = 280
        elif scaling_factor <= 1.5:
            max_allowed_message_width = 600  # 150% scaling
            max_allowed_author_width = 200
            max_allowed_email_width = 250
        else:
            max_allowed_message_width = 500  # 200%+ scaling
            max_allowed_author_width = 180
            max_allowed_email_width = 220

        for commit in commits:
            # Combined width message + description with space
            message_width = canvas.tk.call("font", "measure", font, commit.message)
            if commit.description_short:
                desc_width = canvas.tk.call("font", "measure", font, commit.description_short)
                combined_width = message_width + 20 + desc_width  # 20px space
            else:
                combined_width = message_width

            # Limit width according to scaling factor
            combined_width = min(combined_width, max_allowed_message_width)
            max_message_width = max(max_message_width, combined_width)

            author_width = canvas.tk.call("font", "measure", font, commit.author)
            author_width = min(author_width, max_allowed_author_width)
            max_author_width = max(max_author_width, author_width)

            email_width = canvas.tk.call("font", "measure", font, commit.author_email)
            email_width = min(email_width, max_allowed_email_width)
            max_email_width = max(max_email_width, email_width)

            date_width = canvas.tk.call("font", "measure", font, commit.date_short)
            max_date_width = max(max_date_width, date_width)

        # Use user-set widths or calculated
        user_widths = self.column_manager.get_user_column_widths()
        self.column_widths = {
            'message': user_widths.get('message', max_message_width + 20),
            'author': user_widths.get('author', max_author_width + 20),
            'email': user_widths.get('email', max_email_width + 20),
            'date': user_widths.get('date', max_date_width + 20)
        }

    def _calculate_required_tag_space(self):
        """Estimates space needed for tags (simplified version - now calculated dynamically)."""
        # Fixed estimate of space for tags - real space is calculated dynamically in draw_tags
        # This estimate serves only for calculating total graph column width
        self.required_tag_space = self.tag_drawer.calculate_required_tag_space(self.flag_width)

    def _calculate_graph_column_width(self) -> int:
        """Calculates width of graph column (Branch/Commit).

        Returns:
            Calculated graph column width
        """
        graph_width = self.column_manager.get_graph_column_width()
        if graph_width is not None:
            # Use user-set width
            return graph_width

        # Calculate automatic width based on content
        flag_width = self.flag_width if self.flag_width else 80
        required_tag_space = self.required_tag_space if self.required_tag_space else flag_width + self.BASE_MARGIN

        # Find rightmost commit (most right drawn branch)
        max_commit_x = 0
        if hasattr(self, '_current_commits') and self._current_commits:
            max_commit_x = max((commit.x for commit in self._current_commits), default=0)

        # Width according to rightmost branch: position + space for one branch + space for tags
        # Space = BRANCH_SPACING (20px) - big enough to fit another branch
        # Space for tags: node_radius (end node) + small space + reasonable space for tag
        tag_reserve = self.node_radius + 15 + 50  # 8px (node) + 15px (space) + 50px (tag emoji+text)
        width_based_on_branches = max_commit_x + self.BRANCH_SPACING + tag_reserve

        # Minimum width: margin + flags + margin + tags (original calculation)
        min_width = self.BASE_MARGIN + flag_width + self.BASE_MARGIN + required_tag_space

        # Use larger of the two
        auto_width = max(width_based_on_branches, min_width)
        return auto_width

    def _update_branch_lanes(self, commits: List[Commit]):
        """Updates lanes information for calculating table position.

        Args:
            commits: List of commits
        """
        self.branch_lanes = {}
        flag_width = self.flag_width if self.flag_width else 80
        # Calculate position of first commit (lane 0)
        first_commit_x = self.BASE_MARGIN + flag_width + self.BASE_MARGIN  # flag + spacing

        for commit in commits:
            branch_lane = (commit.x - first_commit_x) // self.BRANCH_SPACING
            self.branch_lanes[commit.branch] = branch_lane

    def _get_table_start_position(self) -> int:
        """Returns X position where table starts (behind all branches).

        Returns:
            X position where table starts
        """
        # Use total graph column width
        graph_column_width = self._calculate_graph_column_width()
        return graph_column_width

    def _make_color_pale(self, color: str, blend_type: str = "remote") -> str:
        """Creates paler version of color using HSL manipulation.

        This is a convenience wrapper around the make_color_pale utility function.

        Args:
            color: Color to make pale
            blend_type: Type of blending ("remote" or "merge")

        Returns:
            Paler version of color
        """
        return make_color_pale(color, blend_type)

    def setup_column_resize_events(self, canvas: tk.Canvas, on_resize_callback=None):
        """Sets up event handlers for column resizing.

        Args:
            canvas: Canvas to bind events to
            on_resize_callback: Callback called after resize
        """
        # Set callback for redrawing after resize
        def resize_callback():
            self._redraw_with_new_widths(canvas)
            if on_resize_callback:
                on_resize_callback()

        self.column_manager.setup_resize_events(resize_callback)

    def _redraw_with_new_widths(self, canvas: tk.Canvas):
        """Redraws graph with new column widths.

        Args:
            canvas: Canvas to redraw on
        """
        # Delete commit texts, tags, separators and labels
        canvas.delete("commit_text")
        canvas.delete("tag_emoji")
        canvas.delete("tag_label")
        canvas.delete("tag_tooltip_area")
        canvas.delete("column_separator")
        canvas.delete("column_header")

        # Find commits from canvas (if stored there as data)
        if hasattr(self, '_current_commits') and self._current_commits:
            # Recalculate description texts according to new message column width
            self.text_formatter.recalculate_descriptions_for_width(
                canvas, self._current_commits, self.column_widths
            )

            # Get table start position
            table_start_x = self._get_table_start_position()

            # Redraw commits and tags
            self.commit_drawer.draw_commits(
                self._current_commits,
                self.column_widths,
                self.tooltip_manager.show_tooltip,
                self.tooltip_manager.hide_tooltip,
                self.text_formatter.truncate_text_to_width,
                table_start_x,
                self._make_color_pale,
                self.branch_flag_drawer,
                self.branch_flag_drawer.draw_flag_connection
            )

            self.tag_drawer.draw_tags(
                self._current_commits,
                table_start_x,
                self.tooltip_manager.show_tooltip,
                self.tooltip_manager.hide_tooltip
            )

        # Redraw separators
        table_start_x = self._get_table_start_position()
        self.column_manager.setup_column_separators(self.column_widths, table_start_x)

    def move_separators_to_scroll_position(self, canvas: tk.Canvas, new_y: float):
        """Moves existing separators to new Y position when scrolling.

        Args:
            canvas: Canvas
            new_y: New Y position
        """
        if self.column_manager:
            self.column_manager.move_separators_to_scroll_position(new_y)
