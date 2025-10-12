"""ColumnManager - handles column separators, resizing, and drag & drop events."""

import tkinter as tk
from typing import Dict, Callable, List
from utils.constants import SEPARATOR_HEIGHT, HEADER_HEIGHT, BASE_MARGIN
from utils.theme_manager import get_theme_manager
from utils.logging_config import get_logger
from utils.translations import t

logger = get_logger(__name__)


class ColumnManager:
    """Manages columns - resizing, separators, drag & drop events."""

    def __init__(self, canvas: tk.Canvas):
        self.canvas = canvas
        self.theme_manager = get_theme_manager()
        self.column_widths = {}
        self.column_separators = {}  # position of separators {column_name: x_position}
        self.dragging_separator = None  # name of column whose separator is being dragged
        self.drag_start_x = 0
        self.drag_redraw_scheduled = False  # Flag for throttling redrawing during drag
        self.on_resize_callback = None  # Callback called after column width change
        self.user_column_widths = {}  # user-set widths
        self.graph_column_width = None  # graph column width
        self.HEADER_HEIGHT = HEADER_HEIGHT
        self.BASE_MARGIN = BASE_MARGIN
        self.separator_height = SEPARATOR_HEIGHT

    def setup_column_separators(self, column_widths: Dict, table_start_position: int):
        """Creates separators between columns.

        Args:
            column_widths: Dictionary with column widths
            table_start_position: X position where table starts
        """
        self.column_widths = column_widths
        self._draw_column_separators(table_start_position)

    def setup_resize_events(self, on_resize_callback: Callable = None):
        """Sets up event handlers for resizing.

        Args:
            on_resize_callback: Callback called after resize
        """
        self.on_resize_callback = on_resize_callback

        # Instead of binding to entire canvas, bind directly to separators
        # This is done in _draw_column_separators()

        # For drag operation we need global handlers
        self.canvas.bind('<B1-Motion>', self._on_separator_drag)
        self.canvas.bind('<ButtonRelease-1>', self._on_separator_release)

    def move_separators_to_scroll_position(self, new_y: float):
        """Moves existing separators to new Y position when scrolling.

        Args:
            new_y: New Y position
        """
        # Find all objects with separators
        separator_items = self.canvas.find_withtag("column_separator")
        header_items = self.canvas.find_withtag("column_header")

        for item in separator_items + header_items:
            # Get current coordinates
            coords = self.canvas.coords(item)
            if not coords:
                continue

            # Determine object type by tags
            tags = self.canvas.gettags(item)

            if "column_bg_" in str(tags) or "graph_header_bg" in tags:
                # For header background - rectangle
                self.canvas.coords(item, coords[0], new_y, coords[2], new_y + 25)
            elif "graph_header_text" in tags:
                # For graph header text - centered vertically
                self.canvas.coords(item, coords[0], new_y + 12)
            elif "header_text_" in str(tags):
                # For header text - centered vertically
                self.canvas.coords(item, coords[0], new_y + 12)
            elif "column_header" in tags and len(coords) == 2:
                # For old format header text
                self.canvas.coords(item, coords[0], new_y + 12)
            elif len(coords) == 4:  # Rectangle or line (separator background, clickable area, or separator)
                # For both rectangle and line change Y1 and Y2
                self.canvas.coords(item, coords[0], new_y, coords[2], new_y + self.separator_height)

        # Ensure correct layering: header backgrounds down, separators up, header text on top
        self.canvas.tag_lower("graph_header_bg")   # Graph header background down
        for column in ['message', 'author', 'email', 'date']:
            try:
                self.canvas.tag_lower(f"column_bg_{column}")  # Individual column backgrounds down
            except Exception as e:
                logger.debug(f"Failed to lower column background {column}: {e}")
                pass
        self.canvas.tag_raise("column_separator")  # Separators up (to be clickable)
        self.canvas.tag_raise("column_header")      # Header text on top

    def get_column_widths(self) -> Dict:
        """Returns current column widths.

        Returns:
            Dictionary with column widths
        """
        return self.column_widths

    def get_user_column_widths(self) -> Dict:
        """Returns user-set column widths.

        Returns:
            Dictionary with user-set column widths
        """
        return self.user_column_widths

    def set_graph_column_width(self, width: int):
        """Sets graph column width.

        Args:
            width: Graph column width
        """
        self.graph_column_width = width

    def get_graph_column_width(self) -> int:
        """Returns graph column width.

        Returns:
            Graph column width or None if not set
        """
        return self.graph_column_width

    def _draw_column_separators(self, table_start_position: int):
        """Draws interactive column separators at top edge.

        Args:
            table_start_position: X position where table starts
        """
        # Header must always be on top of visible area (without gap)
        # canvasy(0) converts window coordinate 0 to canvas coordinate
        scroll_top = self.canvas.canvasy(0)
        separator_y = scroll_top  # header always at top of visible area

        # Always delete old separators and labels and redraw
        self.canvas.delete("column_separator")
        self.canvas.delete("column_header")

        current_x = table_start_position

        # Column names (with translation)
        column_names = {
            'message': t('header_message'),
            'author': t('header_author'),
            'email': 'Email',  # Email is not localized
            'date': t('header_date')
        }

        columns = ['message', 'author', 'email', 'date']

        # FIRST draw separator before first text column (Branch/Commit | Message)
        graph_separator_x = table_start_position

        # Separator background for graph column
        self.canvas.create_rectangle(
            graph_separator_x - 5, separator_y,
            graph_separator_x + 5, separator_y + self.HEADER_HEIGHT,
            outline='',
            fill=self.theme_manager.get_color('separator_bg'),
            tags=("column_separator", "sep_graph_bg")
        )

        # Separator itself for graph column
        self.canvas.create_line(
            graph_separator_x, separator_y,
            graph_separator_x, separator_y + self.HEADER_HEIGHT,
            width=3,
            fill=self.theme_manager.get_color('separator'),
            tags=("column_separator", "sep_graph"),
            activefill=self.theme_manager.get_color('separator_active')
        )

        # Save separator position for graph column
        self.column_separators['graph'] = graph_separator_x

        # Add interactivity for graph separator
        area_id = self.canvas.create_rectangle(
            graph_separator_x - 5, separator_y,
            graph_separator_x + 5, separator_y + self.HEADER_HEIGHT,
            outline='',
            fill='',
            tags=("column_separator", "sep_graph_area")
        )

        # Event handlers for graph separator
        self.canvas.tag_bind("sep_graph", '<Button-1>', lambda e: self._start_drag(e, 'graph'))
        self.canvas.tag_bind("sep_graph_area", '<Button-1>', lambda e: self._start_drag(e, 'graph'))
        self.canvas.tag_bind("sep_graph_bg", '<Button-1>', lambda e: self._start_drag(e, 'graph'))

        for tag in ["sep_graph", "sep_graph_area", "sep_graph_bg"]:
            self.canvas.tag_bind(tag, '<Enter>', lambda e: self.canvas.config(cursor='sb_h_double_arrow'))
            self.canvas.tag_bind(tag, '<Leave>', lambda e: self.canvas.config(cursor='') if not self.dragging_separator else None)

        # THEN draw separators between text columns (to be under background)
        temp_current_x = table_start_position
        for i, column in enumerate(columns):
            temp_current_x += self.column_widths[column]

            # Draw separator (except for last column)
            if i < len(columns) - 1:
                # Separator background (dark gray, well visible)
                background_id = self.canvas.create_rectangle(
                    temp_current_x - 5, separator_y,
                    temp_current_x + 5, separator_y + self.separator_height,
                    outline='',
                    fill=self.theme_manager.get_color('separator_bg'),
                    tags=("column_separator", f"sep_{column}_bg")
                )

                # Separator itself (dark)
                separator_id = self.canvas.create_line(
                    temp_current_x, separator_y,
                    temp_current_x, separator_y + self.separator_height,
                    width=3,
                    fill=self.theme_manager.get_color('separator'),
                    tags=("column_separator", f"sep_{column}"),
                    activefill=self.theme_manager.get_color('separator_active')
                )

                # Save separator position
                self.column_separators[column] = temp_current_x

                # Add invisible area for better mouse capture
                area_id = self.canvas.create_rectangle(
                    temp_current_x - 5, separator_y,
                    temp_current_x + 5, separator_y + self.separator_height,
                    outline='',
                    fill='',
                    tags=("column_separator", f"sep_{column}_area")
                )

                # Bind click directly to separator and area
                def make_handler(col):
                    return lambda e: self._start_drag(e, col)

                self.canvas.tag_bind(f"sep_{column}", '<Button-1>', make_handler(column))
                self.canvas.tag_bind(f"sep_{column}_area", '<Button-1>', make_handler(column))
                self.canvas.tag_bind(f"sep_{column}_bg", '<Button-1>', make_handler(column))

                # Add cursor events for all parts of separator
                def set_cursor_enter(e):
                    self.canvas.config(cursor='sb_h_double_arrow')
                def set_cursor_leave(e):
                    if not self.dragging_separator:
                        self.canvas.config(cursor='')

                self.canvas.tag_bind(f"sep_{column}", '<Enter>', set_cursor_enter)
                self.canvas.tag_bind(f"sep_{column}", '<Leave>', set_cursor_leave)
                self.canvas.tag_bind(f"sep_{column}_area", '<Enter>', set_cursor_enter)
                self.canvas.tag_bind(f"sep_{column}_area", '<Leave>', set_cursor_leave)
                self.canvas.tag_bind(f"sep_{column}_bg", '<Enter>', set_cursor_enter)
                self.canvas.tag_bind(f"sep_{column}_bg", '<Leave>', set_cursor_leave)

        # THEN draw backgrounds (with cutouts for separators)
        # Background for graph column - with cutout for separator
        graph_column_bg = self.canvas.create_rectangle(
            0, separator_y,
            table_start_position - 5, separator_y + 25,  # -5 for separator cutout
            outline='',
            fill=self.theme_manager.get_color('header_bg'),
            tags=("column_header", "graph_header_bg")
        )

        # Header for graph column
        graph_header_x = table_start_position // 2
        graph_header_text = self.canvas.create_text(
            graph_header_x, separator_y + 12,
            text=t('header_branch'),
            anchor='center',
            font=('Arial', 8, 'bold'),
            fill=self.theme_manager.get_color('header_text'),
            tags=("column_header", "graph_header_text")
        )

        # Background and text for text columns (with gaps for separators)
        for i, column in enumerate(columns):

            # Draw background for this column (with cutout for separators)
            if i < len(columns) - 1:
                # Not last column - leave gap for separator
                column_bg = self.canvas.create_rectangle(
                    current_x, separator_y,
                    current_x + self.column_widths[column] - 5, separator_y + 25,  # -5 for gap
                    outline='',
                    fill=self.theme_manager.get_color('header_bg'),
                    tags=("column_header", f"column_bg_{column}")
                )
            else:
                # Last column - no gap
                column_bg = self.canvas.create_rectangle(
                    current_x, separator_y,
                    current_x + self.column_widths[column], separator_y + 25,
                    outline='',
                    fill=self.theme_manager.get_color('header_bg'),
                    tags=("column_header", f"column_bg_{column}")
                )

            # Draw column label
            header_x = current_x + self.column_widths[column] // 2
            header_text = self.canvas.create_text(
                header_x, separator_y + 12,
                text=column_names[column],
                anchor='center',
                font=('Arial', 8, 'bold'),
                fill=self.theme_manager.get_color('header_text'),
                tags=("column_header", f"header_text_{column}")
            )

            current_x += self.column_widths[column]

        # Fill remaining space to the right up to visible window edge
        viewport_width = self.canvas.winfo_width()
        if viewport_width > 1:  # winfo_width returns 1 if not yet initialized
            # Get scroll position and calculate right edge of visible viewport
            scroll_x_left, scroll_x_right = self.canvas.xview()
            scrollregion = self.canvas.cget('scrollregion').split()
            if scrollregion and len(scrollregion) == 4:
                total_width = float(scrollregion[2])
                right_edge = scroll_x_left * total_width + viewport_width
            else:
                right_edge = current_x + viewport_width

            # Draw fill from end of last column to right edge of viewport
            if right_edge > current_x:
                header_fill = self.canvas.create_rectangle(
                    current_x, separator_y,
                    right_edge, separator_y + 25,
                    outline='',
                    fill=self.theme_manager.get_color('header_bg'),
                    tags=("column_header", "header_fill")
                )

        # Ensure correct layering: header backgrounds down, separators up, header text on top
        self.canvas.tag_lower("graph_header_bg")   # Graph header background down
        for column in ['message', 'author', 'email', 'date']:
            try:
                self.canvas.tag_lower(f"column_bg_{column}")  # Individual column backgrounds down
            except Exception as e:
                logger.debug(f"Failed to lower column background {column}: {e}")
                pass
        self.canvas.tag_raise("column_separator")  # Separators up (to be clickable)
        self.canvas.tag_raise("column_header")      # Header text on top

    def _start_drag(self, event, column):
        """Starts dragging separator for given column.

        Args:
            event: Mouse event
            column: Column name
        """
        self.dragging_separator = column
        self.drag_start_x = event.x
        event.widget.config(cursor='sb_h_double_arrow')

    def _on_separator_drag(self, event):
        """Drags separator and adjusts column width.

        Args:
            event: Mouse event
        """
        if not self.dragging_separator:
            return

        delta_x = event.x - self.drag_start_x

        if self.dragging_separator == 'graph':
            # Special processing for graph column
            current_width = self.graph_column_width if self.graph_column_width else 100
            new_width = max(100, current_width + delta_x)  # minimum width 100px for graph column

            # Save new graph column width
            self.graph_column_width = new_width
        else:
            # Standard processing for text columns
            current_width = self.column_widths[self.dragging_separator]
            new_width = max(50, current_width + delta_x)  # minimum width 50px

            self.user_column_widths[self.dragging_separator] = new_width
            self.column_widths[self.dragging_separator] = new_width

        self.drag_start_x = event.x

        # Throttled redrawing - maximum every 16ms (60 FPS)
        if not self.drag_redraw_scheduled:
            self.drag_redraw_scheduled = True
            self.canvas.after(16, lambda: self._throttled_redraw())

    def _throttled_redraw(self):
        """Throttled redrawing during drag operation."""
        self.drag_redraw_scheduled = False
        if self.dragging_separator:  # Only if still dragging
            if self.on_resize_callback:
                self.on_resize_callback()

    def _on_separator_release(self, event):
        """Ends separator dragging.

        Args:
            event: Mouse event
        """
        self.dragging_separator = None
        event.widget.config(cursor='')

        # Final redraw after release (if throttled redraw is waiting, cancel it and do immediately)
        self.drag_redraw_scheduled = False
        if self.on_resize_callback:
            self.on_resize_callback()
