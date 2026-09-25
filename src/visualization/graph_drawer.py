"""GraphDrawer - orchestrator for graph rendering components."""

import tkinter as tk
from bisect import bisect_left, bisect_right
from typing import List, Dict, Optional, Tuple
from utils.data_structures import Commit
from utils.logging_config import get_logger
from utils.theme_manager import get_theme_manager
from utils.constants import (
    NODE_RADIUS, LINE_WIDTH, FONT_SIZE, SEPARATOR_HEIGHT,
    MIN_COLUMN_WIDTH_TEXT, MIN_COLUMN_WIDTH_GRAPH,
    HEADER_HEIGHT, BASE_MARGIN, BRANCH_LANE_SPACING, COMMIT_VERTICAL_SPACING
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

# Virtualizace: hrany se indexují po blocích řádků, aby šlo rychle najít
# spojnice, které procházejí vykreslovaným výřezem.
EDGE_BLOCK_ROWS = 64
# Minimální výška výřezu, se kterou se počítá, než je canvas namapovaný
MIN_VIEWPORT_HEIGHT = 600
# Do tohoto počtu commitů se šířky textů pro sloupce měří přesně (viz _calculate_column_widths)
EXACT_MEASURE_LIMIT = 2000


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

        # Virtualized rendering state (viz draw_graph / render_visible)
        self._current_commits = None
        self._rows: List[Commit] = []        # commity seřazené podle y
        self._row_y: List[int] = []
        self._commit_map: Dict[str, Commit] = {}
        self._children: Dict[str, List[Commit]] = {}
        self._edge_blocks: Dict[int, set] = {}
        self._rendered_range: Optional[Tuple[float, float]] = None
        self._needs_description_recalc = False

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
        """Main entry point - prepares the graph and draws the visible part.

        Globální výpočty (šířky sloupců, vlaječky, lanes) se dělají nad všemi
        commity, ale na canvas se kreslí jen řádky kolem viditelné oblasti
        (render_visible). Dřív se kreslilo všech N commitů (~10 položek na
        řádek), takže desetitisíce commitů znamenaly statisíce položek canvasu,
        pomalé načtení, scrollování i překreslování.

        Args:
            canvas: Canvas to draw on
            commits: List of commits to draw (with layout positions)
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

        # Indexy pro virtualizované kreslení
        self._prepare_virtualization(commits)
        self._needs_description_recalc = False

        self.render_visible(canvas, force=True)

    def _prepare_virtualization(self, commits: List[Commit]):
        """Seřadí řádky podle y a zaindexuje hrany po blocích řádků."""
        self._rows = sorted(commits, key=lambda c: c.y)
        self._row_y = [c.y for c in self._rows]
        self._commit_map = {c.hash: c for c in self._rows}
        self._children = TagDrawer._build_children_index(self._rows)

        row_of = {c.hash: i for i, c in enumerate(self._rows)}
        blocks: Dict[int, set] = {}
        for i, commit in enumerate(self._rows):
            for parent_hash in commit.parents:
                j = row_of.get(parent_hash)
                if j is None:
                    continue
                low, high = (i, j) if i <= j else (j, i)
                for block in range(low // EDGE_BLOCK_ROWS, high // EDGE_BLOCK_ROWS + 1):
                    blocks.setdefault(block, set()).add(i)
        self._edge_blocks = blocks
        self._rendered_range = None

    def render_visible(self, canvas: tk.Canvas, force: bool = False) -> bool:
        """Vykreslí řádky kolem viditelné části canvasu (jednu výšku okna nad i pod).

        Volá se po každé změně pohledu (scroll, resize); překresluje se jen
        tehdy, když viditelná oblast opustí naposledy vykreslený výřez.

        Returns:
            True, pokud se překreslovalo
        """
        if not self._rows:
            return False

        top = canvas.canvasy(0)
        height = max(canvas.winfo_height(), 1)
        bottom = top + height
        if (not force and self._rendered_range is not None
                and top >= self._rendered_range[0] and bottom <= self._rendered_range[1]):
            return False

        margin = max(height, MIN_VIEWPORT_HEIGHT)
        range_top = top - margin
        range_bottom = bottom + margin
        first = bisect_left(self._row_y, range_top - COMMIT_VERTICAL_SPACING)
        last = bisect_right(self._row_y, range_bottom + COMMIT_VERTICAL_SPACING)
        visible = self._rows[first:last]

        # Commity, jejichž spojnice procházejí výřezem (i když samy leží mimo)
        edge_rows = set(range(first, last))
        if last > first:
            for block in range(first // EDGE_BLOCK_ROWS, (last - 1) // EDGE_BLOCK_ROWS + 1):
                edge_rows.update(self._edge_blocks.get(block, ()))
        edge_children = [self._rows[i] for i in sorted(edge_rows)]

        canvas.delete('all')
        if self.tooltip_manager:
            self.tooltip_manager.hide_tooltip()

        if self._needs_description_recalc:
            self.text_formatter.recalculate_descriptions_for_width(canvas, visible, self.column_widths)

        table_start_x = self._get_table_start_position()

        self.connection_drawer.draw_connections(edge_children, self._make_color_pale,
                                                commit_info=self._commit_map)

        self.commit_drawer.draw_commits(
            self._current_commits,
            self.column_widths,
            self.tooltip_manager.show_tooltip,
            self.tooltip_manager.hide_tooltip,
            self.text_formatter.truncate_text_to_width,
            table_start_x,
            self._make_color_pale,
            self.branch_flag_drawer,
            self.branch_flag_drawer.draw_flag_connection,
            visible_commits=visible
        )

        self.tag_drawer.draw_tags(
            self._current_commits,
            table_start_x,
            self.tooltip_manager.show_tooltip,
            self.tooltip_manager.hide_tooltip,
            visible_commits=visible,
            children=self._children,
            commit_map=self._commit_map
        )

        self.column_manager.setup_column_separators(self.column_widths, table_start_x)

        self._rendered_range = (range_top, range_bottom)
        return True

    def get_content_bounds(self) -> Optional[Tuple[int, int, int, int]]:
        """Rozměry celého (i nevykresleného) obsahu pro scrollregion."""
        if not self._rows:
            return None
        width = self._get_table_start_position() + sum(self.column_widths.values())
        height = self._row_y[-1] + COMMIT_VERTICAL_SPACING
        return (0, 0, int(width), int(height))

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

        # Autoři, e-maily a formáty data se opakují - každý řetězec měřit jen jednou
        measured = {}
        char_widths = {}
        # `font measure` stojí na Windows ~0,3 ms; u desetitisíců commitů by jen
        # výpočet šířek sloupců trval desítky sekund. Nad limitem se šířka
        # odhadne součtem šířek znaků (každý znak změřený jednou) - pro šířku
        # sloupce stačí, přesné zkracování textu se dělá jen u vykreslených řádků.
        estimate = len(commits) > EXACT_MEASURE_LIMIT

        def measure(text: str) -> int:
            width = measured.get(text)
            if width is None:
                if estimate:
                    width = 0
                    for ch in text:
                        ch_width = char_widths.get(ch)
                        if ch_width is None:
                            ch_width = char_widths[ch] = canvas.tk.call("font", "measure", font, ch)
                        width += ch_width
                else:
                    width = canvas.tk.call("font", "measure", font, text)
                measured[text] = width
            return width

        for commit in commits:
            # Combined width message + description with space
            message_width = measure(commit.message)
            if commit.description_short:
                desc_width = measure(commit.description_short)
                combined_width = message_width + 20 + desc_width  # 20px space
            else:
                combined_width = message_width

            # Limit width according to scaling factor
            combined_width = min(combined_width, max_allowed_message_width)
            max_message_width = max(max_message_width, combined_width)

            author_width = min(measure(commit.author), max_allowed_author_width)
            max_author_width = max(max_author_width, author_width)

            email_width = min(measure(commit.author_email), max_allowed_email_width)
            max_email_width = max(max_email_width, email_width)

            max_date_width = max(max_date_width, measure(commit.date_short))

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
        """Redraws graph with new column widths (only the rendered slice).

        Args:
            canvas: Canvas to redraw on
        """
        # Popisy se přepočítávají pro šířku sloupce jen u vykreslovaných řádků
        # (dřív u všech commitů při každém snímku tažení oddělovače)
        self._needs_description_recalc = True
        self.render_visible(canvas, force=True)

    def move_separators_to_scroll_position(self, canvas: tk.Canvas, new_y: float):
        """Moves existing separators to new Y position when scrolling.

        Args:
            canvas: Canvas
            new_y: New Y position
        """
        if self.column_manager:
            self.column_manager.move_separators_to_scroll_position(new_y)

    def _draw_column_separators(self, canvas: tk.Canvas):
        """Legacy wrapper for backward compatibility with graph_canvas.py.

        This method maintains the old API while delegating to the new ColumnManager component.

        Args:
            canvas: Canvas (not used, kept for API compatibility)
        """
        # Move separators to current scroll position
        scroll_y = canvas.canvasy(0)  # Get current scroll Y position
        self.move_separators_to_scroll_position(canvas, scroll_y)
