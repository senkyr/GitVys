"""Unit tests for visualization.drawing.connection_drawer module."""

import pytest
import math
from unittest.mock import MagicMock, patch, call
from visualization.drawing.connection_drawer import ConnectionDrawer
from utils.data_structures import Commit
from datetime import datetime


@pytest.fixture
def mock_canvas():
    """Create a mock tkinter Canvas."""
    canvas = MagicMock()
    canvas.create_line.return_value = 1  # Return canvas item ID
    return canvas


@pytest.fixture
def mock_theme_manager():
    """Create a mock ThemeManager."""
    with patch('visualization.drawing.connection_drawer.get_theme_manager') as mock:
        theme_mgr = MagicMock()
        theme_mgr.get_color.return_value = '#FFFFFF'
        mock.return_value = theme_mgr
        yield theme_mgr


@pytest.fixture
def connection_drawer(mock_canvas, mock_theme_manager):
    """Create a ConnectionDrawer instance."""
    return ConnectionDrawer(mock_canvas)


@pytest.fixture
def sample_commits():
    """Create sample commits for testing."""
    commit1 = Commit(
        hash='abc123',
        message='First commit',
        short_message='First commit',
        author='Test User',
        author_short='Test User',
        author_email='test@example.com',
        date=datetime(2025, 1, 1, 10, 0, 0),
        date_relative='1 day ago',
        date_short='2025-01-01',
        parents=[],
        branch='main',
        branch_color='#3366cc',
        x=50,
        y=50,
        description='',
        description_short='',
        tags=[]
    )

    commit2 = Commit(
        hash='def456',
        message='Second commit',
        short_message='Second commit',
        author='Test User',
        author_short='Test User',
        author_email='test@example.com',
        date=datetime(2025, 1, 2, 10, 0, 0),
        date_relative='2 days ago',
        date_short='2025-01-02',
        parents=['abc123'],
        branch='main',
        branch_color='#3366cc',
        x=50,
        y=110,
        description='',
        description_short='',
        tags=[]
    )

    return [commit1, commit2]


@pytest.fixture
def make_color_pale():
    """Mock make_color_pale callback."""
    def callback(color):
        return f"{color}_pale"
    return callback


# ===== Initialization Tests =====

class TestConnectionDrawerInitialization:
    """Tests for ConnectionDrawer initialization."""

    def test_initialization(self, mock_canvas, mock_theme_manager):
        """Test that ConnectionDrawer initializes correctly."""
        drawer = ConnectionDrawer(mock_canvas)

        assert drawer.canvas is mock_canvas
        assert drawer.theme_manager is mock_theme_manager
        assert drawer.line_width > 0
        assert drawer.node_radius > 0
        assert 0 <= drawer.curve_intensity <= 1

    def test_initialization_sets_curve_intensity(self, connection_drawer):
        """Test that initialization sets curve intensity."""
        assert connection_drawer.curve_intensity == 0.8


# ===== Connection Drawing Tests =====

class TestDrawConnections:
    """Tests for drawing connections between commits."""

    def test_draw_connections_with_empty_list(self, connection_drawer, make_color_pale, mock_canvas):
        """Test that draw_connections handles empty commit list."""
        connection_drawer.draw_connections([], make_color_pale)

        # Should not draw any lines
        mock_canvas.create_line.assert_not_called()

    def test_draw_connections_with_single_commit(self, connection_drawer, sample_commits, make_color_pale, mock_canvas):
        """Test that draw_connections handles single commit (no parents)."""
        connection_drawer.draw_connections([sample_commits[0]], make_color_pale)

        # Should not draw any lines (no parents)
        mock_canvas.create_line.assert_not_called()

    def test_draw_connections_draws_line_between_commits(self, connection_drawer, sample_commits, make_color_pale, mock_canvas):
        """Test that draw_connections draws line between parent and child."""
        connection_drawer.draw_connections(sample_commits, make_color_pale)

        # Should draw line between commit1 (50, 50) and commit2 (50, 110)
        mock_canvas.create_line.assert_called()
        assert mock_canvas.create_line.call_count >= 1

    def test_draw_connections_uses_child_color_for_normal_connection(self, connection_drawer, sample_commits, make_color_pale):
        """Test that draw_connections uses child's color for normal connections."""
        with patch.object(connection_drawer, '_draw_line') as mock_draw:
            connection_drawer.draw_connections(sample_commits, make_color_pale)

            # Should use child's (commit2) color
            mock_draw.assert_called_once()
            args = mock_draw.call_args[0]
            assert args[2] == '#3366cc'  # Child's branch_color

    def test_draw_connections_detects_merge_commit(self, connection_drawer, make_color_pale):
        """Test that draw_connections detects merge commits (multiple parents)."""
        # Create merge commit
        parent1 = Commit(
            hash='parent1', message='Parent 1', short_message='Parent 1',
            author='Test', author_short='Test', author_email='test@example.com',
            date=datetime(2025, 1, 1), date_relative='1 day ago', date_short='2025-01-01',
            parents=[], branch='main', branch_color='#3366cc',
            x=50, y=50, description='', description_short='', tags=[]
        )
        parent2 = Commit(
            hash='parent2', message='Parent 2', short_message='Parent 2',
            author='Test', author_short='Test', author_email='test@example.com',
            date=datetime(2025, 1, 2), date_relative='2 days ago', date_short='2025-01-02',
            parents=[], branch='feature', branch_color='#66cc33',
            x=100, y=50, description='', description_short='', tags=[]
        )
        merge = Commit(
            hash='merge', message='Merge', short_message='Merge',
            author='Test', author_short='Test', author_email='test@example.com',
            date=datetime(2025, 1, 3), date_relative='3 days ago', date_short='2025-01-03',
            parents=['parent1', 'parent2'], branch='main', branch_color='#3366cc',
            x=50, y=110, description='', description_short='', tags=[]
        )

        with patch.object(connection_drawer, '_draw_line') as mock_draw:
            connection_drawer.draw_connections([parent1, parent2, merge], make_color_pale)

            # Should call _draw_line twice (one for each parent)
            assert mock_draw.call_count == 2

            # Second parent connection should be marked as merge connection
            # _draw_line signature: (start, end, color, is_remote, is_uncommitted, is_merge_connection, is_branching, make_color_pale_callback)
            second_call_args = mock_draw.call_args_list[1][0]
            assert second_call_args[5] is True  # 6th positional arg = is_merge_connection

    def test_draw_connections_uses_parent_color_for_merge_connection(self, connection_drawer, make_color_pale):
        """Test that draw_connections uses parent's color for merge connections."""
        parent1 = Commit(
            hash='parent1', message='Parent 1', short_message='Parent 1',
            author='Test', author_short='Test', author_email='test@example.com',
            date=datetime(2025, 1, 1), date_relative='1 day ago', date_short='2025-01-01',
            parents=[], branch='main', branch_color='#3366cc',
            x=50, y=50, description='', description_short='', tags=[]
        )
        parent2 = Commit(
            hash='parent2', message='Parent 2', short_message='Parent 2',
            author='Test', author_short='Test', author_email='test@example.com',
            date=datetime(2025, 1, 2), date_relative='2 days ago', date_short='2025-01-02',
            parents=[], branch='feature', branch_color='#66cc33',
            x=100, y=50, description='', description_short='', tags=[]
        )
        merge = Commit(
            hash='merge', message='Merge', short_message='Merge',
            author='Test', author_short='Test', author_email='test@example.com',
            date=datetime(2025, 1, 3), date_relative='3 days ago', date_short='2025-01-03',
            parents=['parent1', 'parent2'], branch='main', branch_color='#3366cc',
            x=50, y=110, description='', description_short='', tags=[]
        )

        with patch.object(connection_drawer, '_draw_line') as mock_draw:
            connection_drawer.draw_connections([parent1, parent2, merge], make_color_pale)

            # Second parent connection should use parent's color (#66cc33)
            second_call = mock_draw.call_args_list[1]
            assert second_call[0][2] == '#66cc33'  # Parent2's color


# ===== Line Drawing Tests =====

class TestDrawLine:
    """Tests for drawing individual lines."""

    def test_draw_line_straight_vertical(self, connection_drawer, mock_canvas):
        """Test that _draw_line draws straight vertical line for same column."""
        connection_drawer._draw_line((50, 50), (50, 110), '#3366cc')

        # Should draw straight line
        mock_canvas.create_line.assert_called_once()
        args = mock_canvas.create_line.call_args[0]
        assert args == (50, 50, 50, 110)

    def test_draw_line_calls_bezier_for_different_columns(self, connection_drawer):
        """Test that _draw_line calls _draw_bezier_curve for different columns."""
        with patch.object(connection_drawer, '_draw_bezier_curve') as mock_bezier:
            connection_drawer._draw_line((50, 50), (100, 110), '#3366cc')

            # Should call bezier curve drawing
            mock_bezier.assert_called_once()

    def test_draw_line_uses_color(self, connection_drawer, mock_canvas):
        """Test that _draw_line uses correct color."""
        connection_drawer._draw_line((50, 50), (50, 110), '#FF0000')

        kwargs = mock_canvas.create_line.call_args[1]
        assert kwargs['fill'] == '#FF0000'

    def test_draw_line_uses_stipple_for_uncommitted(self, connection_drawer, mock_canvas):
        """Test that _draw_line uses stipple pattern for uncommitted connections."""
        connection_drawer._draw_line((50, 50), (50, 110), '#3366cc', is_uncommitted=True)

        kwargs = mock_canvas.create_line.call_args[1]
        assert kwargs['stipple'] == 'gray50'

    def test_draw_line_makes_remote_color_pale(self, connection_drawer, make_color_pale, mock_canvas):
        """Test that _draw_line makes color pale for remote connections."""
        connection_drawer._draw_line((50, 50), (50, 110), '#3366cc', is_remote=True,
                                    make_color_pale_callback=make_color_pale)

        kwargs = mock_canvas.create_line.call_args[1]
        assert kwargs['fill'] == '#3366cc_pale'

    def test_draw_line_no_stipple_for_merge_connection(self, connection_drawer, mock_canvas):
        """Test that _draw_line does not use stipple for merge connections."""
        connection_drawer._draw_line((50, 50), (50, 110), '#3366cc', is_merge_connection=True)

        kwargs = mock_canvas.create_line.call_args[1]
        assert 'stipple' not in kwargs


# ===== Bézier Curve Tests =====

class TestDrawBezierCurve:
    """Tests for drawing Bézier curves."""

    def test_draw_bezier_curve_draws_segments(self, connection_drawer, mock_canvas):
        """Test that _draw_bezier_curve draws L-shaped connection."""
        connection_drawer._draw_bezier_curve(50, 50, 100, 110, '#3366cc')

        # Should draw multiple segments (first segment + arc + last segment)
        assert mock_canvas.create_line.call_count >= 2

    def test_draw_bezier_curve_straight_horizontal(self, connection_drawer, mock_canvas):
        """Test that _draw_bezier_curve handles straight horizontal line."""
        connection_drawer._draw_bezier_curve(50, 50, 100, 50, '#3366cc')

        # Should draw straight line (dy == 0)
        mock_canvas.create_line.assert_called_once()
        args = mock_canvas.create_line.call_args[0]
        assert args == (50, 50, 100, 50)

    def test_draw_bezier_curve_straight_vertical(self, connection_drawer, mock_canvas):
        """Test that _draw_bezier_curve handles straight vertical line."""
        connection_drawer._draw_bezier_curve(50, 50, 50, 110, '#3366cc')

        # Should draw straight line (dx == 0)
        mock_canvas.create_line.assert_called_once()
        args = mock_canvas.create_line.call_args[0]
        assert args == (50, 50, 50, 110)

    def test_draw_bezier_curve_merge_connection_type(self, connection_drawer):
        """Test that _draw_bezier_curve handles merge connection (horizontal at end)."""
        with patch.object(connection_drawer, '_calculate_rounded_corner_arc') as mock_arc:
            mock_arc.return_value = [100, 110, 102, 112, 104, 114]  # Mock arc points
            connection_drawer._draw_bezier_curve(50, 50, 100, 110, '#3366cc',
                                                is_merge_connection=True)

            # Should call arc calculation with is_merge=True
            mock_arc.assert_called_once()
            kwargs = mock_arc.call_args[1]
            assert kwargs['is_merge'] is True

    def test_draw_bezier_curve_branching_type(self, connection_drawer):
        """Test that _draw_bezier_curve handles branching connection (horizontal at start)."""
        with patch.object(connection_drawer, '_calculate_rounded_corner_arc') as mock_arc:
            mock_arc.return_value = [100, 110, 102, 112, 104, 114]
            connection_drawer._draw_bezier_curve(50, 50, 100, 110, '#3366cc',
                                                is_branching=True)

            # Should call arc calculation with is_merge=False
            mock_arc.assert_called_once()
            kwargs = mock_arc.call_args[1]
            assert kwargs['is_merge'] is False

    def test_draw_bezier_curve_uses_stipple(self, connection_drawer, mock_canvas):
        """Test that _draw_bezier_curve applies stipple pattern."""
        connection_drawer._draw_bezier_curve(50, 50, 100, 110, '#3366cc',
                                            stipple_pattern='gray50')

        # All line segments should have stipple
        for call in mock_canvas.create_line.call_args_list:
            if len(call[1]) > 0 and 'fill' in call[1]:
                assert call[1].get('stipple') == 'gray50'

    def test_draw_bezier_curve_fallback_for_short_distance(self, connection_drawer, mock_canvas):
        """Test that _draw_bezier_curve falls back to simple line for short distances."""
        # Very short distance (less than radius)
        connection_drawer._draw_bezier_curve(50, 50, 52, 52, '#3366cc')

        # Should include fallback line
        assert mock_canvas.create_line.called


# ===== Arc Calculation Tests =====

class TestCalculateRoundedCornerArc:
    """Tests for calculating rounded corner arcs."""

    def test_calculate_arc_returns_points(self, connection_drawer):
        """Test that _calculate_rounded_corner_arc returns point list."""
        points = connection_drawer._calculate_rounded_corner_arc(
            50, 50, 100, 110, 50, 110, 10, arc_type="right_down", is_merge=True
        )

        assert isinstance(points, list)
        assert len(points) > 2  # At least 2 points (x, y pairs)
        assert len(points) % 2 == 0  # Even number (x, y pairs)

    def test_calculate_arc_right_down_merge(self, connection_drawer):
        """Test arc calculation for right-down merge connection."""
        points = connection_drawer._calculate_rounded_corner_arc(
            50, 50, 100, 110, 50, 110, 10, arc_type="right_down", is_merge=True
        )

        # Should generate smooth arc
        assert len(points) >= 18  # 9 points * 2 coords (steps=8)

    def test_calculate_arc_right_up_merge(self, connection_drawer):
        """Test arc calculation for right-up merge connection."""
        points = connection_drawer._calculate_rounded_corner_arc(
            50, 110, 100, 50, 50, 50, 10, arc_type="right_up", is_merge=True
        )

        assert len(points) >= 18

    def test_calculate_arc_left_down_merge(self, connection_drawer):
        """Test arc calculation for left-down merge connection."""
        points = connection_drawer._calculate_rounded_corner_arc(
            100, 50, 50, 110, 100, 110, 10, arc_type="left_down", is_merge=True
        )

        assert len(points) >= 18

    def test_calculate_arc_left_up_merge(self, connection_drawer):
        """Test arc calculation for left-up merge connection."""
        points = connection_drawer._calculate_rounded_corner_arc(
            100, 110, 50, 50, 100, 50, 10, arc_type="left_up", is_merge=True
        )

        assert len(points) >= 18

    def test_calculate_arc_right_down_branching(self, connection_drawer):
        """Test arc calculation for right-down branching connection."""
        points = connection_drawer._calculate_rounded_corner_arc(
            50, 50, 100, 110, 100, 50, 10, arc_type="right_down", is_merge=False
        )

        assert len(points) >= 18

    def test_calculate_arc_right_up_branching(self, connection_drawer):
        """Test arc calculation for right-up branching connection."""
        points = connection_drawer._calculate_rounded_corner_arc(
            50, 110, 100, 50, 100, 110, 10, arc_type="right_up", is_merge=False
        )

        assert len(points) >= 18

    def test_calculate_arc_uses_correct_angles(self, connection_drawer):
        """Test that _calculate_rounded_corner_arc uses correct trigonometric angles."""
        points = connection_drawer._calculate_rounded_corner_arc(
            50, 50, 100, 110, 50, 110, 10, arc_type="right_down", is_merge=True
        )

        # Points should form smooth curve
        # Check that points progress smoothly (not jumping)
        for i in range(2, len(points) - 2, 2):
            x1, y1 = points[i-2], points[i-1]
            x2, y2 = points[i], points[i+1]
            x3, y3 = points[i+2], points[i+3]

            # Distance between consecutive points should be similar
            dist1 = math.sqrt((x2 - x1)**2 + (y2 - y1)**2)
            dist2 = math.sqrt((x3 - x2)**2 + (y3 - y2)**2)

            # Distances should be reasonably close (within 80% - less strict for arc endpoints)
            if dist1 > 0.1 and dist2 > 0.1:  # Skip very small distances
                assert abs(dist1 - dist2) / max(dist1, dist2, 1) < 0.8

    def test_calculate_arc_handles_angle_wrapping(self, connection_drawer):
        """Test that _calculate_rounded_corner_arc handles angle wrapping correctly."""
        # Test case that crosses 360°/0° boundary
        points = connection_drawer._calculate_rounded_corner_arc(
            50, 50, 100, 110, 100, 50, 10, arc_type="right_down", is_merge=False
        )

        # Should still generate valid points
        assert len(points) >= 18

    def test_calculate_arc_raises_on_unknown_type(self, connection_drawer):
        """Test that _calculate_rounded_corner_arc raises error for unknown arc type."""
        with pytest.raises(ValueError, match="Unknown arc_type"):
            connection_drawer._calculate_rounded_corner_arc(
                50, 50, 100, 110, 50, 110, 10, arc_type="invalid_type", is_merge=False
            )


# ===== Integration Tests =====

class TestConnectionDrawerIntegration:
    """Integration tests for ConnectionDrawer workflow."""

    def test_full_connection_drawing_workflow(self, connection_drawer, sample_commits, make_color_pale, mock_canvas):
        """Test complete workflow: create drawer → draw connections → verify canvas calls."""
        # Draw connections
        connection_drawer.draw_connections(sample_commits, make_color_pale)

        # Should have created at least one line
        assert mock_canvas.create_line.called

    def test_complex_graph_with_merge_and_branches(self, connection_drawer, make_color_pale, mock_canvas):
        """Test drawing connections for complex graph with merges and branches."""
        # Create complex commit structure
        main1 = Commit(
            hash='main1', message='Main 1', short_message='Main 1',
            author='Test', author_short='Test', author_email='test@example.com',
            date=datetime(2025, 1, 1), date_relative='1 day ago', date_short='2025-01-01',
            parents=[], branch='main', branch_color='#3366cc',
            x=50, y=50, description='', description_short='', tags=[]
        )
        branch1 = Commit(
            hash='branch1', message='Branch 1', short_message='Branch 1',
            author='Test', author_short='Test', author_email='test@example.com',
            date=datetime(2025, 1, 2), date_relative='2 days ago', date_short='2025-01-02',
            parents=['main1'], branch='feature', branch_color='#66cc33',
            x=100, y=110, description='', description_short='', tags=[]
        )
        merge1 = Commit(
            hash='merge1', message='Merge', short_message='Merge',
            author='Test', author_short='Test', author_email='test@example.com',
            date=datetime(2025, 1, 3), date_relative='3 days ago', date_short='2025-01-03',
            parents=['main1', 'branch1'], branch='main', branch_color='#3366cc',
            x=50, y=170, description='', description_short='', tags=[]
        )

        connection_drawer.draw_connections([main1, branch1, merge1], make_color_pale)

        # Should draw multiple lines/curves
        assert mock_canvas.create_line.call_count >= 2
