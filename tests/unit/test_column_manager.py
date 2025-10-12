"""Unit tests for visualization.ui.column_manager module."""

# MUST BE FIRST - initialize TCL/TK before any other imports
import tests.setup_tcl  # noqa: F401

import pytest
import tkinter as tk
from unittest.mock import MagicMock, patch, call
from visualization.ui.column_manager import ColumnManager


@pytest.fixture
def mock_canvas():
    """Create a mock tkinter Canvas."""
    canvas = MagicMock(spec=tk.Canvas)
    canvas.canvasy.return_value = 0  # Default scroll position
    canvas.winfo_width.return_value = 800  # Default width
    canvas.xview.return_value = (0.0, 1.0)  # Not scrolled
    canvas.cget.return_value = "0 0 1000 1000"  # Default scrollregion
    canvas.find_withtag.return_value = []  # No items by default
    return canvas


@pytest.fixture
def mock_theme_manager():
    """Create a mock ThemeManager."""
    with patch('visualization.ui.column_manager.get_theme_manager') as mock:
        theme_mgr = MagicMock()
        theme_mgr.get_color.return_value = '#FFFFFF'  # Default color
        mock.return_value = theme_mgr
        yield theme_mgr


@pytest.fixture
def column_manager(mock_canvas, mock_theme_manager):
    """Create a ColumnManager instance."""
    return ColumnManager(mock_canvas)


@pytest.fixture
def sample_column_widths():
    """Sample column widths for testing."""
    return {
        'message': 300,
        'author': 150,
        'email': 200,
        'date': 100
    }


# ===== Initialization Tests =====

class TestColumnManagerInitialization:
    """Tests for ColumnManager initialization."""

    def test_initialization(self, mock_canvas, mock_theme_manager):
        """Test that ColumnManager initializes correctly."""
        manager = ColumnManager(mock_canvas)

        assert manager.canvas is mock_canvas
        assert manager.theme_manager is mock_theme_manager
        assert manager.column_widths == {}
        assert manager.column_separators == {}
        assert manager.dragging_separator is None
        assert manager.drag_start_x == 0
        assert manager.drag_redraw_scheduled is False
        assert manager.on_resize_callback is None
        assert manager.user_column_widths == {}
        assert manager.graph_column_width is None

    def test_initialization_sets_constants(self, column_manager):
        """Test that initialization sets height and margin constants."""
        assert column_manager.HEADER_HEIGHT > 0
        assert column_manager.BASE_MARGIN >= 0
        assert column_manager.separator_height > 0


# ===== Column Setup Tests =====

class TestColumnSetup:
    """Tests for setting up columns."""

    def test_setup_column_separators(self, column_manager, sample_column_widths):
        """Test that setup_column_separators stores widths and draws separators."""
        with patch.object(column_manager, '_draw_column_separators') as mock_draw:
            column_manager.setup_column_separators(sample_column_widths, 100)

            assert column_manager.column_widths == sample_column_widths
            mock_draw.assert_called_once_with(100)

    def test_setup_resize_events_stores_callback(self, column_manager):
        """Test that setup_resize_events stores callback."""
        callback = MagicMock()

        column_manager.setup_resize_events(callback)

        assert column_manager.on_resize_callback is callback

    def test_setup_resize_events_binds_canvas_events(self, column_manager, mock_canvas):
        """Test that setup_resize_events binds drag and release events."""
        column_manager.setup_resize_events()

        # Verify that canvas events are bound
        assert mock_canvas.bind.call_count >= 2
        mock_canvas.bind.assert_any_call('<B1-Motion>', column_manager._on_separator_drag)
        mock_canvas.bind.assert_any_call('<ButtonRelease-1>', column_manager._on_separator_release)


# ===== Getter/Setter Tests =====

class TestColumnGettersSetters:
    """Tests for column width getters and setters."""

    def test_get_column_widths(self, column_manager, sample_column_widths):
        """Test that get_column_widths returns column widths."""
        column_manager.column_widths = sample_column_widths

        result = column_manager.get_column_widths()

        assert result == sample_column_widths

    def test_get_user_column_widths(self, column_manager):
        """Test that get_user_column_widths returns user-set widths."""
        user_widths = {'message': 400, 'author': 200}
        column_manager.user_column_widths = user_widths

        result = column_manager.get_user_column_widths()

        assert result == user_widths

    def test_set_graph_column_width(self, column_manager):
        """Test that set_graph_column_width stores width."""
        column_manager.set_graph_column_width(250)

        assert column_manager.graph_column_width == 250

    def test_get_graph_column_width(self, column_manager):
        """Test that get_graph_column_width returns width."""
        column_manager.graph_column_width = 250

        result = column_manager.get_graph_column_width()

        assert result == 250

    def test_get_graph_column_width_returns_none_if_not_set(self, column_manager):
        """Test that get_graph_column_width returns None if not set."""
        result = column_manager.get_graph_column_width()

        assert result is None


# ===== Separator Drawing Tests =====

class TestSeparatorDrawing:
    """Tests for drawing column separators."""

    @patch('visualization.ui.column_manager.t')
    def test_draw_column_separators_creates_canvas_items(self, mock_t, column_manager, sample_column_widths, mock_canvas):
        """Test that _draw_column_separators creates canvas items."""
        mock_t.side_effect = lambda key: f"translated_{key}"
        column_manager.column_widths = sample_column_widths

        column_manager._draw_column_separators(100)

        # Should create rectangles and lines for separators
        assert mock_canvas.create_rectangle.call_count > 0
        assert mock_canvas.create_line.call_count > 0
        assert mock_canvas.create_text.call_count > 0

    @patch('visualization.ui.column_manager.t')
    def test_draw_column_separators_deletes_old_items(self, mock_t, column_manager, sample_column_widths, mock_canvas):
        """Test that _draw_column_separators deletes old separators."""
        mock_t.side_effect = lambda key: f"translated_{key}"
        column_manager.column_widths = sample_column_widths

        column_manager._draw_column_separators(100)

        # Should delete old separators and headers
        mock_canvas.delete.assert_any_call("column_separator")
        mock_canvas.delete.assert_any_call("column_header")

    @patch('visualization.ui.column_manager.t')
    def test_draw_column_separators_stores_positions(self, mock_t, column_manager, sample_column_widths):
        """Test that _draw_column_separators stores separator positions."""
        mock_t.side_effect = lambda key: f"translated_{key}"
        column_manager.column_widths = sample_column_widths

        column_manager._draw_column_separators(100)

        # Should store positions for graph column and text columns
        assert 'graph' in column_manager.column_separators
        assert 'message' in column_manager.column_separators

    @patch('visualization.ui.column_manager.t')
    def test_draw_column_separators_binds_events(self, mock_t, column_manager, sample_column_widths, mock_canvas):
        """Test that _draw_column_separators binds events to separators."""
        mock_t.side_effect = lambda key: f"translated_{key}"
        column_manager.column_widths = sample_column_widths

        column_manager._draw_column_separators(100)

        # Should bind events to separator tags
        assert mock_canvas.tag_bind.call_count > 0


# ===== Drag and Drop Tests =====

class TestSeparatorDragDrop:
    """Tests for separator drag and drop functionality."""

    def test_start_drag_sets_state(self, column_manager, mock_canvas):
        """Test that _start_drag sets dragging state."""
        event = MagicMock()
        event.x = 150
        event.widget = mock_canvas

        column_manager._start_drag(event, 'message')

        assert column_manager.dragging_separator == 'message'
        assert column_manager.drag_start_x == 150
        mock_canvas.config.assert_called_once_with(cursor='sb_h_double_arrow')

    def test_on_separator_drag_does_nothing_if_not_dragging(self, column_manager):
        """Test that _on_separator_drag does nothing if not dragging."""
        event = MagicMock()
        event.x = 200

        column_manager._on_separator_drag(event)

        # Should not schedule redraw
        assert column_manager.drag_redraw_scheduled is False

    def test_on_separator_drag_adjusts_text_column_width(self, column_manager, sample_column_widths):
        """Test that _on_separator_drag adjusts text column width."""
        column_manager.column_widths = sample_column_widths
        column_manager.dragging_separator = 'message'
        column_manager.drag_start_x = 150

        event = MagicMock()
        event.x = 200  # +50 delta

        column_manager._on_separator_drag(event)

        # Width should increase by delta
        assert column_manager.column_widths['message'] == 350  # 300 + 50
        assert column_manager.user_column_widths['message'] == 350
        assert column_manager.drag_start_x == 200

    def test_on_separator_drag_enforces_minimum_width(self, column_manager, sample_column_widths):
        """Test that _on_separator_drag enforces minimum width of 50px."""
        column_manager.column_widths = sample_column_widths
        column_manager.dragging_separator = 'date'
        column_manager.drag_start_x = 200

        event = MagicMock()
        event.x = 50  # -150 delta (would make width negative)

        column_manager._on_separator_drag(event)

        # Width should not go below 50px
        assert column_manager.column_widths['date'] == 50

    def test_on_separator_drag_adjusts_graph_column_width(self, column_manager):
        """Test that _on_separator_drag adjusts graph column width."""
        column_manager.graph_column_width = 200
        column_manager.dragging_separator = 'graph'
        column_manager.drag_start_x = 150

        event = MagicMock()
        event.x = 200  # +50 delta

        column_manager._on_separator_drag(event)

        # Graph column width should increase by delta
        assert column_manager.graph_column_width == 250

    def test_on_separator_drag_enforces_graph_minimum_width(self, column_manager):
        """Test that _on_separator_drag enforces minimum graph width of 100px."""
        column_manager.graph_column_width = 150
        column_manager.dragging_separator = 'graph'
        column_manager.drag_start_x = 200

        event = MagicMock()
        event.x = 50  # -150 delta

        column_manager._on_separator_drag(event)

        # Graph width should not go below 100px
        assert column_manager.graph_column_width == 100

    def test_on_separator_drag_schedules_throttled_redraw(self, column_manager, sample_column_widths, mock_canvas):
        """Test that _on_separator_drag schedules throttled redraw (60 FPS)."""
        column_manager.column_widths = sample_column_widths
        column_manager.dragging_separator = 'message'
        column_manager.drag_start_x = 150

        event = MagicMock()
        event.x = 200

        column_manager._on_separator_drag(event)

        # Should schedule redraw with 16ms delay (60 FPS)
        assert column_manager.drag_redraw_scheduled is True
        mock_canvas.after.assert_called_once()
        args = mock_canvas.after.call_args[0]
        assert args[0] == 16  # 16ms = 60 FPS

    def test_on_separator_drag_does_not_schedule_if_already_scheduled(self, column_manager, sample_column_widths, mock_canvas):
        """Test that _on_separator_drag does not schedule if redraw already scheduled."""
        column_manager.column_widths = sample_column_widths
        column_manager.dragging_separator = 'message'
        column_manager.drag_start_x = 150
        column_manager.drag_redraw_scheduled = True

        event = MagicMock()
        event.x = 200

        column_manager._on_separator_drag(event)

        # Should not schedule another redraw
        mock_canvas.after.assert_not_called()

    def test_on_separator_release_clears_state(self, column_manager, mock_canvas):
        """Test that _on_separator_release clears dragging state."""
        column_manager.dragging_separator = 'message'
        column_manager.drag_redraw_scheduled = True

        event = MagicMock()
        event.widget = mock_canvas

        column_manager._on_separator_release(event)

        assert column_manager.dragging_separator is None
        assert column_manager.drag_redraw_scheduled is False
        mock_canvas.config.assert_called_once_with(cursor='')

    def test_on_separator_release_triggers_final_redraw(self, column_manager):
        """Test that _on_separator_release triggers final redraw."""
        callback = MagicMock()
        column_manager.on_resize_callback = callback
        column_manager.dragging_separator = 'message'

        event = MagicMock()
        event.widget = MagicMock()

        column_manager._on_separator_release(event)

        # Should call callback for final redraw
        callback.assert_called_once()


# ===== Throttled Redraw Tests =====

class TestThrottledRedraw:
    """Tests for throttled redraw mechanism."""

    def test_throttled_redraw_calls_callback_if_dragging(self, column_manager):
        """Test that _throttled_redraw calls callback if still dragging."""
        callback = MagicMock()
        column_manager.on_resize_callback = callback
        column_manager.dragging_separator = 'message'
        column_manager.drag_redraw_scheduled = True

        column_manager._throttled_redraw()

        callback.assert_called_once()
        assert column_manager.drag_redraw_scheduled is False

    def test_throttled_redraw_does_nothing_if_not_dragging(self, column_manager):
        """Test that _throttled_redraw does nothing if not dragging."""
        callback = MagicMock()
        column_manager.on_resize_callback = callback
        column_manager.dragging_separator = None
        column_manager.drag_redraw_scheduled = True

        column_manager._throttled_redraw()

        # Should not call callback if drag ended
        callback.assert_not_called()
        assert column_manager.drag_redraw_scheduled is False

    def test_throttled_redraw_does_nothing_if_no_callback(self, column_manager):
        """Test that _throttled_redraw does nothing if no callback set."""
        column_manager.on_resize_callback = None
        column_manager.dragging_separator = 'message'
        column_manager.drag_redraw_scheduled = True

        # Should not raise exception
        column_manager._throttled_redraw()

        assert column_manager.drag_redraw_scheduled is False


# ===== Scrolling Tests =====

class TestScrolling:
    """Tests for moving separators during scrolling."""

    def test_move_separators_to_scroll_position_updates_items(self, column_manager, mock_canvas):
        """Test that move_separators_to_scroll_position updates separator positions."""
        # Mock separator items
        mock_canvas.find_withtag.side_effect = lambda tag: [1, 2, 3] if tag == "column_separator" else []
        mock_canvas.coords.return_value = [100, 0, 105, 25]  # Rectangle
        mock_canvas.gettags.return_value = ("column_separator", "sep_message")

        column_manager.move_separators_to_scroll_position(50)

        # Should update coordinates for all separator items
        assert mock_canvas.coords.call_count >= 3  # Called for each item

    def test_move_separators_to_scroll_position_handles_empty_coords(self, column_manager, mock_canvas):
        """Test that move_separators_to_scroll_position handles items with no coords."""
        mock_canvas.find_withtag.return_value = [1, 2]

        # Create mock that returns empty list for first item, coords for second
        coords_calls = 0
        def coords_side_effect(item, *args):
            nonlocal coords_calls
            coords_calls += 1
            # First call (item 1, reading) - empty
            if coords_calls == 1:
                return []
            # Second call (item 2, reading) - has coords
            elif coords_calls == 2:
                return [100, 0, 105, 25]
            # Third call (item 2, updating) - accept new coords
            else:
                return None

        mock_canvas.coords.side_effect = coords_side_effect
        mock_canvas.gettags.return_value = ("column_separator",)

        # Should not raise exception
        column_manager.move_separators_to_scroll_position(50)

    def test_move_separators_to_scroll_position_updates_header_items(self, column_manager, mock_canvas):
        """Test that move_separators_to_scroll_position updates header positions."""
        mock_canvas.find_withtag.side_effect = lambda tag: [] if tag == "column_separator" else [1, 2]
        mock_canvas.coords.return_value = [100, 0, 200, 25]  # Header background
        mock_canvas.gettags.return_value = ("column_header", "column_bg_message")

        column_manager.move_separators_to_scroll_position(50)

        # Should update header item coordinates
        assert mock_canvas.coords.call_count >= 2

    def test_move_separators_to_scroll_position_adjusts_layering(self, column_manager, mock_canvas):
        """Test that move_separators_to_scroll_position adjusts layer order."""
        mock_canvas.find_withtag.return_value = []

        column_manager.move_separators_to_scroll_position(50)

        # Should adjust layering
        mock_canvas.tag_lower.assert_any_call("graph_header_bg")
        mock_canvas.tag_raise.assert_any_call("column_separator")
        mock_canvas.tag_raise.assert_any_call("column_header")


# ===== Edge Cases and Error Handling =====

class TestEdgeCases:
    """Tests for edge cases and error handling."""

    def test_setup_column_separators_with_empty_widths(self, column_manager):
        """Test that setup_column_separators handles empty widths."""
        with patch.object(column_manager, '_draw_column_separators'):
            column_manager.setup_column_separators({}, 100)

            assert column_manager.column_widths == {}

    def test_drag_with_uninitialized_graph_width(self, column_manager):
        """Test that dragging graph separator works with uninitialized width."""
        column_manager.graph_column_width = None
        column_manager.dragging_separator = 'graph'
        column_manager.drag_start_x = 150

        event = MagicMock()
        event.x = 200

        column_manager._on_separator_drag(event)

        # Should use default width of 100
        assert column_manager.graph_column_width == 150  # 100 + 50 delta

    @patch('visualization.ui.column_manager.t')
    def test_draw_separators_uses_translations(self, mock_t, column_manager, sample_column_widths):
        """Test that _draw_column_separators uses translation function."""
        mock_t.side_effect = lambda key: f"translated_{key}"
        column_manager.column_widths = sample_column_widths

        column_manager._draw_column_separators(100)

        # Should call t() for header translations
        mock_t.assert_any_call('header_message')
        mock_t.assert_any_call('header_author')
        mock_t.assert_any_call('header_date')
        mock_t.assert_any_call('header_branch')

    def test_move_separators_handles_invalid_tags(self, column_manager, mock_canvas):
        """Test that move_separators_to_scroll_position handles invalid tags."""
        mock_canvas.find_withtag.return_value = [1]
        mock_canvas.coords.return_value = [100, 0, 105, 25]
        mock_canvas.gettags.return_value = ("unknown_tag",)

        # Should not raise exception
        column_manager.move_separators_to_scroll_position(50)


# ===== Integration Tests =====

class TestColumnManagerIntegration:
    """Integration tests for ColumnManager workflow."""

    @patch('visualization.ui.column_manager.t')
    def test_full_resize_workflow(self, mock_t, column_manager, sample_column_widths, mock_canvas):
        """Test complete resize workflow: setup → drag → release."""
        mock_t.side_effect = lambda key: f"translated_{key}"
        callback = MagicMock()

        # 1. Setup
        column_manager.setup_column_separators(sample_column_widths, 100)
        column_manager.setup_resize_events(callback)

        # 2. Start drag
        start_event = MagicMock()
        start_event.x = 150
        start_event.widget = mock_canvas
        column_manager._start_drag(start_event, 'message')

        assert column_manager.dragging_separator == 'message'

        # 3. Drag
        drag_event = MagicMock()
        drag_event.x = 200
        column_manager._on_separator_drag(drag_event)

        assert column_manager.column_widths['message'] == 350
        assert column_manager.drag_redraw_scheduled is True

        # 4. Release
        release_event = MagicMock()
        release_event.widget = mock_canvas
        column_manager._on_separator_release(release_event)

        assert column_manager.dragging_separator is None
        callback.assert_called()

    @patch('visualization.ui.column_manager.t')
    def test_multiple_drag_operations_throttle_correctly(self, mock_t, column_manager, sample_column_widths, mock_canvas):
        """Test that multiple drag operations throttle correctly."""
        mock_t.side_effect = lambda key: f"translated_{key}"
        callback = MagicMock()

        column_manager.setup_column_separators(sample_column_widths, 100)
        column_manager.setup_resize_events(callback)

        start_event = MagicMock()
        start_event.x = 150
        start_event.widget = mock_canvas
        column_manager._start_drag(start_event, 'message')

        # Multiple drags in quick succession
        for x in range(160, 210, 10):
            drag_event = MagicMock()
            drag_event.x = x
            column_manager._on_separator_drag(drag_event)

        # Should only schedule once (throttling)
        assert mock_canvas.after.call_count == 1
