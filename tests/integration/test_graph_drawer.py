"""Integration tests for GraphDrawer orchestration."""

import pytest
from visualization.graph_drawer import GraphDrawer


class TestGraphDrawerIntegration:
    """Integration tests for GraphDrawer orchestration."""

    @pytest.fixture
    def drawer(self):
        """Create GraphDrawer instance."""
        return GraphDrawer()

    def test_initialization(self, drawer):
        """Test GraphDrawer initialization."""
        assert drawer.node_radius > 0
        assert drawer.line_width > 0
        assert drawer.font_size > 0
        assert drawer.column_widths == {}
        # Components should be None initially (lazy init)
        assert drawer.connection_drawer is None
        assert drawer.commit_drawer is None
        assert drawer.tag_drawer is None
        assert drawer.branch_flag_drawer is None

    def test_draw_graph_initializes_components(self, drawer, canvas, mock_commits):
        """Test that draw_graph initializes all components."""
        drawer.draw_graph(canvas, mock_commits)

        # All components should be initialized
        assert drawer.connection_drawer is not None
        assert drawer.commit_drawer is not None
        assert drawer.tag_drawer is not None
        assert drawer.branch_flag_drawer is not None
        assert drawer.column_manager is not None
        assert drawer.tooltip_manager is not None
        assert drawer.text_formatter is not None

    def test_draw_graph_creates_canvas_items(self, drawer, canvas, mock_commits):
        """Test that draw_graph creates canvas elements."""
        initial_items = len(canvas.find_all())
        drawer.draw_graph(canvas, mock_commits)
        final_items = len(canvas.find_all())

        # Should have created some canvas items
        assert final_items > initial_items

    def test_draw_graph_calculates_column_widths(self, drawer, canvas, mock_commits):
        """Test that draw_graph calculates column widths."""
        drawer.draw_graph(canvas, mock_commits)

        # Column widths should be calculated
        assert 'message' in drawer.column_widths
        assert 'author' in drawer.column_widths
        assert 'email' in drawer.column_widths
        assert 'date' in drawer.column_widths

        # All widths should be positive
        assert all(w > 0 for w in drawer.column_widths.values())

    def test_draw_graph_with_tags(self, drawer, canvas, mock_commits_with_tags):
        """Test drawing graph with tagged commits."""
        drawer.draw_graph(canvas, mock_commits_with_tags)

        # Should have created items
        items = canvas.find_all()
        assert len(items) > 0

        # Should have calculated flag width
        assert drawer.flag_width is not None
        assert drawer.flag_width > 0

    def test_reset_clears_state(self, drawer, canvas, mock_commits):
        """Test that reset clears drawer state."""
        # First draw to initialize
        drawer.draw_graph(canvas, mock_commits)
        assert drawer.column_widths

        # Reset
        drawer.reset()

        # State should be cleared
        assert drawer.column_widths == {}
        assert drawer.flag_width is None
        assert drawer.required_tag_space is None

    def test_draw_graph_empty_commits(self, drawer, canvas):
        """Test drawing graph with empty commit list."""
        # Should not crash
        drawer.draw_graph(canvas, [])

        # Should not initialize components for empty list
        assert drawer.connection_drawer is None

    def test_setup_column_resize_events(self, drawer, canvas, mock_commits):
        """Test setting up column resize events."""
        # First draw to initialize
        drawer.draw_graph(canvas, mock_commits)

        callback_called = False

        def test_callback():
            nonlocal callback_called
            callback_called = True

        # Setup should not crash
        drawer.setup_column_resize_events(canvas, test_callback)

    def test_multiple_draws_same_canvas(self, drawer, canvas, mock_commits):
        """Test drawing multiple times on same canvas."""
        drawer.draw_graph(canvas, mock_commits)
        items_first = len(canvas.find_all())

        # Draw again
        drawer.draw_graph(canvas, mock_commits)
        items_second = len(canvas.find_all())

        # Should have items both times
        assert items_first > 0
        assert items_second > 0

    def test_make_color_pale_wrapper(self, drawer):
        """Test that _make_color_pale wrapper works."""
        pale = drawer._make_color_pale("#FF0000", "remote")
        assert pale.startswith("#")
        assert len(pale) == 7

    def test_backward_compatibility_draw_column_separators(self, drawer, canvas, mock_commits):
        """Test legacy _draw_column_separators method."""
        # Initialize components
        drawer.draw_graph(canvas, mock_commits)

        # Legacy method should not crash
        drawer._draw_column_separators(canvas)

    def test_get_table_start_position(self, drawer, canvas, mock_commits):
        """Test table start position calculation."""
        drawer.draw_graph(canvas, mock_commits)

        # Should have calculated table position
        table_start = drawer._get_table_start_position()
        assert table_start > 0

    def test_calculate_graph_column_width(self, drawer, canvas, mock_commits):
        """Test graph column width calculation."""
        drawer.draw_graph(canvas, mock_commits)

        width = drawer._calculate_graph_column_width()
        assert width > 0

    def test_move_separators_to_scroll_position(self, drawer, canvas, mock_commits):
        """Test moving separators when scrolling."""
        drawer.draw_graph(canvas, mock_commits)

        # Should not crash
        drawer.move_separators_to_scroll_position(canvas, 100.0)
