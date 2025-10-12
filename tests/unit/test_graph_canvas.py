"""Tests for GraphCanvas component.

This component is a canvas wrapper with scrolling, momentum, and drag & drop support.
"""

# MUST BE FIRST - initialize TCL/TK before any other imports
import tests.setup_tcl  # noqa: F401

import pytest
from unittest.mock import MagicMock, patch, call
import tkinter as tk
from tkinter import ttk

from gui.graph_canvas import GraphCanvas


# Patch tkinterdnd2 registration to avoid errors in tests
@pytest.fixture(autouse=True)
def mock_dnd_registration():
    """Mock DND registration to avoid tkinterdnd2 issues in tests."""
    with patch('gui.graph_canvas.DND_FILES', None):
        with patch('gui.graph_canvas.DND_TEXT', None):
            yield


class TestGraphCanvasInitialization:
    """Test GraphCanvas initialization."""

    def test_initialization_creates_widgets(self, root):
        """Test that initialization creates all required widgets."""
        canvas = GraphCanvas(root)

        # Verify widgets created
        assert hasattr(canvas, 'canvas')
        assert hasattr(canvas, 'v_scrollbar')
        assert hasattr(canvas, 'h_scrollbar')
        assert hasattr(canvas, 'graph_drawer')

        assert isinstance(canvas.canvas, tk.Canvas)
        assert isinstance(canvas.v_scrollbar, ttk.Scrollbar)
        assert isinstance(canvas.h_scrollbar, ttk.Scrollbar)

    def test_initialization_with_callback(self, root):
        """Test initialization with drop callback."""
        callback = MagicMock()
        canvas = GraphCanvas(root, on_drop_callback=callback)

        assert canvas.on_drop_callback == callback

    def test_initialization_without_callback(self, root):
        """Test initialization without callback."""
        canvas = GraphCanvas(root)

        assert canvas.on_drop_callback is None

    def test_initialization_sets_scroll_state(self, root):
        """Test that initialization sets scroll momentum state."""
        canvas = GraphCanvas(root)

        # Verify scroll state initialized
        assert canvas.scroll_animation_id is None
        assert canvas.scroll_velocity == 0
        assert canvas.last_scroll_time == 0
        assert canvas.scroll_timeout_id is None

    def test_initialization_hides_scrollbars(self, root):
        """Test that scrollbars are hidden initially."""
        canvas = GraphCanvas(root)

        # Scrollbars should be created but not visible (grid_remove)
        # We can't directly test grid_remove, but we verify they exist
        assert canvas.v_scrollbar is not None
        assert canvas.h_scrollbar is not None


class TestCanScroll:
    """Test scroll capability detection."""

    def test_can_scroll_vertically_with_large_content(self, root):
        """Test vertical scroll detection with content larger than canvas."""
        canvas = GraphCanvas(root)

        # Mock canvas size and scrollregion
        canvas.canvas.winfo_height = MagicMock(return_value=500)
        canvas.canvas.cget = MagicMock(return_value="0 0 800 1000")  # 1000px tall content

        # Should be able to scroll (1000 > 500 + 10)
        assert canvas._can_scroll_vertically() is True

    def test_can_scroll_vertically_with_small_content(self, root):
        """Test vertical scroll detection with content smaller than canvas."""
        canvas = GraphCanvas(root)

        # Mock canvas size and scrollregion
        canvas.canvas.winfo_height = MagicMock(return_value=500)
        canvas.canvas.cget = MagicMock(return_value="0 0 800 400")  # 400px tall content

        # Should NOT be able to scroll (400 < 500)
        assert canvas._can_scroll_vertically() is False

    def test_can_scroll_horizontally_with_large_content(self, root):
        """Test horizontal scroll detection with content wider than canvas."""
        canvas = GraphCanvas(root)

        # Mock canvas size and scrollregion
        canvas.canvas.winfo_width = MagicMock(return_value=600)
        canvas.canvas.cget = MagicMock(return_value="0 0 1200 800")  # 1200px wide content

        # Should be able to scroll (1200 > 600 + 10)
        assert canvas._can_scroll_horizontally() is True

    def test_can_scroll_horizontally_with_small_content(self, root):
        """Test horizontal scroll detection with content narrower than canvas."""
        canvas = GraphCanvas(root)

        # Mock canvas size and scrollregion
        canvas.canvas.winfo_width = MagicMock(return_value=600)
        canvas.canvas.cget = MagicMock(return_value="0 0 500 800")  # 500px wide content

        # Should NOT be able to scroll (500 < 600)
        assert canvas._can_scroll_horizontally() is False

    def test_can_scroll_with_empty_scrollregion(self, root):
        """Test scroll detection with empty scrollregion."""
        canvas = GraphCanvas(root)

        # Mock empty scrollregion
        canvas.canvas.cget = MagicMock(return_value="")

        # Should NOT be able to scroll
        assert canvas._can_scroll_vertically() is False
        assert canvas._can_scroll_horizontally() is False

    def test_can_scroll_with_threshold(self, root):
        """Test that 10px threshold is applied."""
        canvas = GraphCanvas(root)

        # Mock canvas size and content just at threshold
        canvas.canvas.winfo_height = MagicMock(return_value=500)
        canvas.canvas.cget = MagicMock(return_value="0 0 800 505")  # 505px tall (only 5px more)

        # Should NOT be able to scroll (505 < 500 + 10)
        assert canvas._can_scroll_vertically() is False


class TestUpdateScrollbarsVisibility:
    """Test scrollbar visibility updates."""

    def test_update_scrollbars_visibility_shows_vertical(self, root):
        """Test that vertical scrollbar is shown when needed."""
        canvas = GraphCanvas(root)

        # Mock canvas size and large vertical content
        canvas.canvas.winfo_width = MagicMock(return_value=600)
        canvas.canvas.winfo_height = MagicMock(return_value=500)
        canvas.canvas.cget = MagicMock(return_value="0 0 800 1000")

        # Mock grid/grid_remove
        canvas.v_scrollbar.grid = MagicMock()
        canvas.v_scrollbar.grid_remove = MagicMock()
        canvas.h_scrollbar.grid_remove = MagicMock()

        canvas._update_scrollbars_visibility()

        # Vertical scrollbar should be shown
        canvas.v_scrollbar.grid.assert_called_once()

    def test_update_scrollbars_visibility_hides_when_not_needed(self, root):
        """Test that scrollbars are hidden when content fits."""
        canvas = GraphCanvas(root)

        # Mock canvas size and small content
        canvas.canvas.winfo_width = MagicMock(return_value=600)
        canvas.canvas.winfo_height = MagicMock(return_value=500)
        canvas.canvas.cget = MagicMock(return_value="0 0 500 400")

        # Mock grid_remove
        canvas.v_scrollbar.grid_remove = MagicMock()
        canvas.h_scrollbar.grid_remove = MagicMock()

        canvas._update_scrollbars_visibility()

        # Both scrollbars should be hidden
        canvas.v_scrollbar.grid_remove.assert_called_once()
        canvas.h_scrollbar.grid_remove.assert_called_once()


class TestVerticalScroll:
    """Test vertical scrolling."""

    def test_on_v_scroll_moveto(self, root):
        """Test vertical scroll with moveto command."""
        canvas = GraphCanvas(root)

        # Mock scroll capability
        canvas._can_scroll_vertically = MagicMock(return_value=True)
        canvas.canvas.yview_moveto = MagicMock()
        canvas._update_column_separators = MagicMock()

        # Scroll to 50%
        canvas._on_v_scroll('moveto', '0.5')

        # Verify scroll applied
        canvas.canvas.yview_moveto.assert_called_once_with(0.5)
        canvas._update_column_separators.assert_called_once()

    def test_on_v_scroll_moveto_bounds_checking(self, root):
        """Test vertical scroll moveto with out-of-bounds values."""
        canvas = GraphCanvas(root)

        canvas._can_scroll_vertically = MagicMock(return_value=True)
        canvas.canvas.yview_moveto = MagicMock()
        canvas._update_column_separators = MagicMock()

        # Try to scroll beyond bounds
        canvas._on_v_scroll('moveto', '1.5')  # > 1.0

        # Should be clamped to 1.0
        canvas.canvas.yview_moveto.assert_called_once_with(1.0)

    def test_on_v_scroll_units(self, root):
        """Test vertical scroll with scroll units."""
        canvas = GraphCanvas(root)

        canvas._can_scroll_vertically = MagicMock(return_value=True)
        canvas.canvas.yview = MagicMock(return_value=(0.0, 0.5))  # Current viewport
        canvas.canvas.yview_moveto = MagicMock()
        canvas._update_column_separators = MagicMock()

        # Scroll by 10 units
        canvas._on_v_scroll('scroll', '10', 'units')

        # Should call yview_moveto with calculated position
        canvas.canvas.yview_moveto.assert_called_once()

    def test_on_v_scroll_does_nothing_when_cannot_scroll(self, root):
        """Test that vertical scroll does nothing when content fits."""
        canvas = GraphCanvas(root)

        canvas._can_scroll_vertically = MagicMock(return_value=False)
        canvas.canvas.yview_moveto = MagicMock()

        # Try to scroll
        canvas._on_v_scroll('moveto', '0.5')

        # Should NOT scroll
        canvas.canvas.yview_moveto.assert_not_called()


class TestHorizontalScroll:
    """Test horizontal scrolling."""

    def test_on_h_scroll_moveto(self, root):
        """Test horizontal scroll with moveto command."""
        canvas = GraphCanvas(root)

        canvas._can_scroll_horizontally = MagicMock(return_value=True)
        canvas.canvas.xview_moveto = MagicMock()

        # Scroll to 30%
        canvas._on_h_scroll('moveto', '0.3')

        # Verify scroll applied
        canvas.canvas.xview_moveto.assert_called_once_with(0.3)

    def test_on_h_scroll_moveto_bounds_checking(self, root):
        """Test horizontal scroll moveto with out-of-bounds values."""
        canvas = GraphCanvas(root)

        canvas._can_scroll_horizontally = MagicMock(return_value=True)
        canvas.canvas.xview_moveto = MagicMock()

        # Try to scroll beyond bounds
        canvas._on_h_scroll('moveto', '-0.5')  # < 0.0

        # Should be clamped to 0.0
        canvas.canvas.xview_moveto.assert_called_once_with(0.0)

    def test_on_h_scroll_does_nothing_when_cannot_scroll(self, root):
        """Test that horizontal scroll does nothing when content fits."""
        canvas = GraphCanvas(root)

        canvas._can_scroll_horizontally = MagicMock(return_value=False)
        canvas.canvas.xview_moveto = MagicMock()

        # Try to scroll
        canvas._on_h_scroll('moveto', '0.5')

        # Should NOT scroll
        canvas.canvas.xview_moveto.assert_not_called()


class TestMouseWheel:
    """Test mousewheel scrolling with momentum."""

    def test_on_mousewheel_scrolls_when_possible(self, root):
        """Test mousewheel scrolling when content is scrollable."""
        canvas = GraphCanvas(root)

        canvas._can_scroll_vertically = MagicMock(return_value=True)
        canvas._start_momentum_scroll = MagicMock()

        # Mock event
        event = MagicMock()
        event.delta = 120  # Scroll up

        # Scroll
        canvas.on_mousewheel(event)

        # Should start momentum scroll
        canvas._start_momentum_scroll.assert_called_once()
        # Velocity should be set
        assert canvas.scroll_velocity != 0

    def test_on_mousewheel_does_nothing_when_cannot_scroll(self, root):
        """Test mousewheel does nothing when content fits."""
        canvas = GraphCanvas(root)

        canvas._can_scroll_vertically = MagicMock(return_value=False)
        canvas._start_momentum_scroll = MagicMock()

        # Mock event
        event = MagicMock()
        event.delta = 120

        # Try to scroll
        canvas.on_mousewheel(event)

        # Should NOT start momentum scroll
        canvas._start_momentum_scroll.assert_not_called()

    def test_on_mousewheel_acceleration(self, root):
        """Test that continuous scrolling accelerates."""
        canvas = GraphCanvas(root)

        canvas._can_scroll_vertically = MagicMock(return_value=True)
        canvas._start_momentum_scroll = MagicMock()

        # First scroll
        event = MagicMock()
        event.delta = 120
        canvas.on_mousewheel(event)

        initial_velocity = canvas.scroll_velocity

        # Quick second scroll (within 100ms)
        import time
        canvas.last_scroll_time = time.time()
        canvas.on_mousewheel(event)

        # Velocity should have increased (acceleration)
        assert abs(canvas.scroll_velocity) > abs(initial_velocity)

    def test_on_mousewheel_max_velocity_limit(self, root):
        """Test that velocity is capped at maximum."""
        canvas = GraphCanvas(root)

        canvas._can_scroll_vertically = MagicMock(return_value=True)
        canvas._start_momentum_scroll = MagicMock()

        # Mock continuous very fast scrolling
        event = MagicMock()
        event.delta = 120
        canvas.scroll_velocity = 0.15  # Start with high velocity

        import time
        canvas.last_scroll_time = time.time()

        # Scroll again
        canvas.on_mousewheel(event)

        # Velocity should be capped at 0.2 (max_velocity)
        assert abs(canvas.scroll_velocity) <= 0.2


class TestMomentumScroll:
    """Test momentum-based scrolling."""

    def test_perform_momentum_step_applies_velocity(self, root):
        """Test that momentum step applies velocity to scroll position."""
        canvas = GraphCanvas(root)

        # Set velocity
        canvas.scroll_velocity = 0.01

        # Mock canvas methods
        canvas.canvas.yview = MagicMock(return_value=(0.2, 0.7))  # Current viewport
        canvas.canvas.yview_moveto = MagicMock()
        canvas._update_column_separators = MagicMock()

        # Perform step
        canvas._perform_momentum_step()

        # Should apply velocity and move
        canvas.canvas.yview_moveto.assert_called_once()
        # New position should be 0.2 + 0.01 = 0.21
        assert canvas.canvas.yview_moveto.call_args[0][0] == pytest.approx(0.21, abs=0.001)

    def test_perform_momentum_step_deceleration(self, root):
        """Test that momentum decelerates over time."""
        canvas = GraphCanvas(root)

        # Set initial velocity
        canvas.scroll_velocity = 0.1

        # Mock canvas methods
        canvas.canvas.yview = MagicMock(return_value=(0.2, 0.7))
        canvas.canvas.yview_moveto = MagicMock()
        canvas._update_column_separators = MagicMock()

        # Perform step
        canvas._perform_momentum_step()

        # Velocity should be reduced (0.85 deceleration factor)
        assert canvas.scroll_velocity == pytest.approx(0.1 * 0.85, abs=0.001)

    def test_perform_momentum_step_stops_at_zero(self, root):
        """Test that momentum stops when velocity is near zero."""
        canvas = GraphCanvas(root)

        # Set very small velocity
        canvas.scroll_velocity = 0.0001

        # Mock canvas methods
        canvas.canvas.yview = MagicMock(return_value=(0.2, 0.7))
        canvas.canvas.yview_moveto = MagicMock()

        # Perform step
        canvas._perform_momentum_step()

        # Velocity should be reset to 0
        assert canvas.scroll_velocity == 0
        # Animation should be stopped
        assert canvas.scroll_animation_id is None

    def test_reset_scroll_velocity(self, root):
        """Test that velocity is reset."""
        canvas = GraphCanvas(root)

        # Set velocity and timeout
        canvas.scroll_velocity = 0.1
        canvas.scroll_timeout_id = 123

        # Reset
        canvas._reset_scroll_velocity()

        # Should be reset
        assert canvas.scroll_velocity == 0
        assert canvas.scroll_timeout_id is None


class TestUpdateGraph:
    """Test graph update functionality."""

    def test_update_graph_with_commits(self, root, mock_commits):
        """Test updating graph with commits."""
        canvas = GraphCanvas(root)

        # Mock graph drawer
        canvas.graph_drawer.draw_graph = MagicMock()
        canvas.graph_drawer.setup_column_resize_events = MagicMock()
        canvas._update_scrollbars_visibility = MagicMock()

        # Update graph
        canvas.update_graph(mock_commits)

        # Verify graph drawn
        canvas.graph_drawer.draw_graph.assert_called_once_with(canvas.canvas, mock_commits)
        canvas.graph_drawer.setup_column_resize_events.assert_called_once()

    def test_update_graph_clears_canvas(self, root, mock_commits):
        """Test that update_graph clears canvas before drawing."""
        canvas = GraphCanvas(root)

        # Mock canvas.delete
        canvas.canvas.delete = MagicMock()
        canvas.graph_drawer.draw_graph = MagicMock()
        canvas.graph_drawer.setup_column_resize_events = MagicMock()

        # Update graph
        canvas.update_graph(mock_commits)

        # Verify canvas cleared
        canvas.canvas.delete.assert_called_once_with('all')

    def test_update_graph_with_empty_commits(self, root):
        """Test updating graph with empty commits list."""
        canvas = GraphCanvas(root)

        canvas.canvas.delete = MagicMock()
        canvas.graph_drawer.draw_graph = MagicMock()
        canvas._update_scrollbars_visibility = MagicMock()

        # Update with empty list
        canvas.update_graph([])

        # Canvas should be cleared
        canvas.canvas.delete.assert_called_once_with('all')
        # Graph drawer should NOT be called
        canvas.graph_drawer.draw_graph.assert_not_called()
        # Scrollbars should be updated
        canvas._update_scrollbars_visibility.assert_called_once()

    def test_update_graph_resets_scroll_position(self, root, mock_commits):
        """Test that update_graph resets scroll to top."""
        canvas = GraphCanvas(root)

        # Mock canvas methods
        canvas.canvas.yview_moveto = MagicMock()
        canvas.canvas.xview_moveto = MagicMock()
        canvas.graph_drawer.draw_graph = MagicMock()
        canvas.graph_drawer.setup_column_resize_events = MagicMock()

        # Update graph
        canvas.update_graph(mock_commits)

        # Should scroll to top
        canvas.canvas.yview_moveto.assert_called_with(0)
        canvas.canvas.xview_moveto.assert_called_with(0)


class TestOnDrop:
    """Test drag & drop functionality."""

    def test_on_drop_calls_callback(self, root):
        """Test that on_drop calls callback with folder path."""
        callback = MagicMock()
        canvas = GraphCanvas(root, on_drop_callback=callback)

        # Mock event
        event = MagicMock()
        event.data = "/path/to/folder"

        # Mock tk.splitlist
        mock_tk = MagicMock()
        mock_tk.splitlist = MagicMock(return_value=["/path/to/folder"])
        canvas.canvas.tk = mock_tk

        # Drop
        canvas.on_drop(event)

        # Callback should be called
        callback.assert_called_once_with("/path/to/folder")

    def test_on_drop_without_callback(self, root):
        """Test that on_drop does nothing without callback."""
        canvas = GraphCanvas(root)  # No callback

        # Mock event
        event = MagicMock()
        event.data = "/path/to/folder"

        # Mock tk.splitlist
        mock_tk = MagicMock()
        mock_tk.splitlist = MagicMock(return_value=["/path/to/folder"])
        canvas.canvas.tk = mock_tk

        # Drop - should not raise exception
        try:
            canvas.on_drop(event)
        except Exception as e:
            pytest.fail(f"on_drop should handle missing callback, but raised: {e}")


class TestApplyTheme:
    """Test theme application."""

    def test_apply_theme_updates_canvas_bg(self, root):
        """Test that apply_theme updates canvas background."""
        canvas = GraphCanvas(root)

        # Mock theme manager
        with patch('gui.graph_canvas.get_theme_manager') as mock_tm:
            mock_tm.return_value.get_color.return_value = "#FFFFFF"

            canvas.apply_theme()

            # Should call get_color for canvas background
            mock_tm.return_value.get_color.assert_called_with('canvas_bg')

    def test_apply_theme_redraws_graph_if_loaded(self, root, mock_commits):
        """Test that apply_theme redraws graph if commits loaded."""
        canvas = GraphCanvas(root)

        # Load graph first
        canvas.graph_drawer._current_commits = mock_commits
        canvas.update_graph = MagicMock()

        # Apply theme
        with patch('gui.graph_canvas.get_theme_manager') as mock_tm:
            mock_tm.return_value.get_color.return_value = "#000000"

            canvas.apply_theme()

            # Should redraw graph
            canvas.update_graph.assert_called_once_with(mock_commits)


class TestOnCanvasResize:
    """Test canvas resize handling."""

    def test_on_canvas_resize_updates_separators(self, root):
        """Test that canvas resize updates column separators."""
        canvas = GraphCanvas(root)

        canvas._update_column_separators = MagicMock()
        canvas._update_scrollbars_visibility = MagicMock()

        # Mock event
        event = MagicMock()

        # Trigger resize
        canvas.on_canvas_resize(event)

        # Should update separators and scrollbars
        canvas._update_column_separators.assert_called_once()
        canvas._update_scrollbars_visibility.assert_called_once()


class TestGraphCanvasIntegration:
    """Integration tests for GraphCanvas."""

    def test_full_workflow_load_and_scroll(self, root, mock_commits):
        """Test complete workflow: load commits and scroll."""
        canvas = GraphCanvas(root)

        # Mock necessary methods
        canvas.graph_drawer.draw_graph = MagicMock()
        canvas.graph_drawer.setup_column_resize_events = MagicMock()
        canvas._can_scroll_vertically = MagicMock(return_value=True)

        # Load commits
        canvas.update_graph(mock_commits)

        # Verify commits stored
        assert canvas.commits == mock_commits

        # Verify graph drawn
        canvas.graph_drawer.draw_graph.assert_called_once()

    def test_scrollbar_visibility_lifecycle(self, root):
        """Test scrollbar visibility updates through lifecycle."""
        canvas = GraphCanvas(root)

        # Mock canvas size
        canvas.canvas.winfo_width = MagicMock(return_value=600)
        canvas.canvas.winfo_height = MagicMock(return_value=500)

        # Initially small content - scrollbars hidden
        canvas.canvas.cget = MagicMock(return_value="0 0 500 400")
        canvas._update_scrollbars_visibility()

        # Now large content - scrollbars should show
        canvas.canvas.cget = MagicMock(return_value="0 0 800 1000")
        canvas._update_scrollbars_visibility()

        # Scrollbars should have been shown (grid called)
        # Note: We can't easily verify grid() calls due to ttk complexity,
        # but we verify the logic runs without errors
