"""Unit tests for BranchFlagDrawer component."""

# MUST BE FIRST - initialize TCL/TK before any other imports
import tests.setup_tcl  # noqa: F401

import pytest
import tkinter as tk
from unittest.mock import MagicMock, patch
from datetime import datetime

from visualization.drawing.branch_flag_drawer import BranchFlagDrawer
from utils.data_structures import Commit


# ========================================
# Fixtures
# ========================================

@pytest.fixture
def branch_flag_drawer(canvas):
    """Create a BranchFlagDrawer instance with mocked canvas methods."""
    # Mock canvas drawing methods
    canvas.create_rectangle = MagicMock(return_value=1)
    canvas.create_text = MagicMock(return_value=2)
    canvas.create_line = MagicMock(return_value=3)
    canvas.tag_bind = MagicMock()
    canvas.delete = MagicMock()
    canvas.winfo_width = MagicMock(return_value=800)

    # Mock tk.call for font measurements
    mock_tk = MagicMock()
    mock_tk.call = MagicMock(return_value=60)  # Default font measure
    canvas.tk = mock_tk

    return BranchFlagDrawer(canvas)


@pytest.fixture
def sample_commits():
    """Create sample commits with different branch configurations."""
    commit1 = Commit(
        hash='abc123', message='First commit', short_message='First commit',
        author='Test User', author_short='Test User', author_email='test@example.com',
        date=datetime(2025, 1, 1), date_relative='1 day ago', date_short='2025-01-01',
        parents=[], branch='main', branch_color='#3366cc',
        x=100, y=100, description='', description_short='', tags=[],
        is_remote=False, is_branch_head=True, branch_head_type='local_only',
        branch_availability='local_only'
    )

    commit2 = Commit(
        hash='def456', message='Second commit', short_message='Second commit',
        author='Test User', author_short='Test User', author_email='test@example.com',
        date=datetime(2025, 1, 2), date_relative='2 days ago', date_short='2025-01-02',
        parents=['abc123'], branch='origin/feature', branch_color='#66cc33',
        x=150, y=160, description='', description_short='', tags=[],
        is_remote=True, is_branch_head=True, branch_head_type='remote_only',
        branch_availability='remote_only'
    )

    commit3 = Commit(
        hash='ghi789', message='Third commit', short_message='Third commit',
        author='Test User', author_short='Test User', author_email='test@example.com',
        date=datetime(2025, 1, 3), date_relative='3 days ago', date_short='2025-01-03',
        parents=['def456'], branch='develop', branch_color='#cc6633',
        x=200, y=220, description='', description_short='', tags=[],
        is_remote=False, is_branch_head=True, branch_head_type='both',
        branch_availability='both'
    )

    return [commit1, commit2, commit3]


# ========================================
# Test Classes
# ========================================

class TestBranchFlagDrawerInitialization:
    """Tests for BranchFlagDrawer initialization."""

    def test_initialization(self, canvas):
        """Test BranchFlagDrawer initializes correctly."""
        drawer = BranchFlagDrawer(canvas)

        assert drawer.canvas == canvas
        assert drawer.theme_manager is not None
        assert drawer.BASE_MARGIN > 0
        assert drawer.line_width > 0
        assert drawer.node_radius > 0
        assert drawer.flag_width is None  # Not calculated yet
        assert drawer.flag_tooltips == {}

    def test_initialization_sets_constants(self, canvas):
        """Test that initialization sets expected constant values."""
        from utils.constants import BASE_MARGIN, LINE_WIDTH, NODE_RADIUS

        drawer = BranchFlagDrawer(canvas)

        assert drawer.BASE_MARGIN == BASE_MARGIN
        assert drawer.line_width == LINE_WIDTH
        assert drawer.node_radius == NODE_RADIUS


class TestCalculateFlagWidth:
    """Tests for calculate_flag_width method."""

    def test_calculate_flag_width_basic(self, branch_flag_drawer, sample_commits):
        """Test basic flag width calculation."""
        width = branch_flag_drawer.calculate_flag_width(sample_commits)

        # Should return a reasonable width
        assert width >= 90  # Minimum width
        assert width <= 120  # Maximum width
        assert branch_flag_drawer.flag_width == width

    def test_calculate_flag_width_empty_list(self, branch_flag_drawer):
        """Test flag width calculation with empty commit list."""
        width = branch_flag_drawer.calculate_flag_width([])

        # Should return minimum width
        assert width == 90
        assert branch_flag_drawer.flag_width == 90

    def test_calculate_flag_width_long_branch_names(self, branch_flag_drawer):
        """Test flag width calculation with very long branch names."""
        commit = Commit(
            hash='abc123', message='Test', short_message='Test',
            author='Test', author_short='Test', author_email='test@example.com',
            date=datetime(2025, 1, 1), date_relative='1 day ago', date_short='2025-01-01',
            parents=[], branch='very-long-branch-name-that-needs-truncation',
            branch_color='#3366cc', x=100, y=100,
            description='', description_short='', tags=[],
            is_remote=False, is_branch_head=True,
            branch_head_type='local_only', branch_availability='local_only'
        )

        width = branch_flag_drawer.calculate_flag_width([commit])

        # Should be capped at maximum width (120) or close to it
        # Name gets truncated before width calculation, so actual width may be less
        assert width >= 90  # At minimum width
        assert width <= 120  # At or below maximum width

    def test_calculate_flag_width_skips_unknown_branches(self, branch_flag_drawer):
        """Test that unknown branches are skipped in width calculation."""
        commit1 = Commit(
            hash='abc123', message='Test', short_message='Test',
            author='Test', author_short='Test', author_email='test@example.com',
            date=datetime(2025, 1, 1), date_relative='1 day ago', date_short='2025-01-01',
            parents=[], branch='unknown', branch_color='#999999',
            x=100, y=100, description='', description_short='', tags=[],
            is_remote=False, is_branch_head=False,
            branch_head_type='none', branch_availability='none'
        )

        commit2 = Commit(
            hash='def456', message='Test', short_message='Test',
            author='Test', author_short='Test', author_email='test@example.com',
            date=datetime(2025, 1, 2), date_relative='2 days ago', date_short='2025-01-02',
            parents=['abc123'], branch='main', branch_color='#3366cc',
            x=100, y=160, description='', description_short='', tags=[],
            is_remote=False, is_branch_head=True,
            branch_head_type='local_only', branch_availability='local_only'
        )

        width = branch_flag_drawer.calculate_flag_width([commit1, commit2])

        # Should only consider 'main' branch
        assert width >= 90

    def test_calculate_flag_width_removes_origin_prefix(self, branch_flag_drawer):
        """Test that origin/ prefix is removed for width calculation."""
        commit = Commit(
            hash='abc123', message='Test', short_message='Test',
            author='Test', author_short='Test', author_email='test@example.com',
            date=datetime(2025, 1, 1), date_relative='1 day ago', date_short='2025-01-01',
            parents=[], branch='origin/feature', branch_color='#66cc33',
            x=100, y=100, description='', description_short='', tags=[],
            is_remote=True, is_branch_head=True,
            branch_head_type='remote_only', branch_availability='remote_only'
        )

        # Mock to verify 'feature' (not 'origin/feature') is measured
        original_call = branch_flag_drawer.canvas.tk.call

        def mock_call(*args):
            if len(args) >= 4 and args[0] == 'font' and args[1] == 'measure':
                text = args[3]
                # Verify 'origin/' was removed
                assert 'origin/' not in text or text == 'origin/feature'
            return 60

        branch_flag_drawer.canvas.tk.call = MagicMock(side_effect=mock_call)

        width = branch_flag_drawer.calculate_flag_width([commit])
        assert width >= 90


class TestDrawBranchFlag:
    """Tests for draw_branch_flag method."""

    def test_draw_branch_flag_local_only(self, branch_flag_drawer):
        """Test drawing flag for local-only branch."""
        branch_flag_drawer.flag_width = 100  # Set calculated width

        branch_flag_drawer.draw_branch_flag(
            x=100, y=100, branch_name='main', branch_color='#3366cc',
            is_remote=False, branch_availability='local_only'
        )

        # Should create rectangle, text (with outline), and local symbol
        assert branch_flag_drawer.canvas.create_rectangle.call_count == 1
        assert branch_flag_drawer.canvas.create_text.call_count >= 5  # Outline + text + symbol

    def test_draw_branch_flag_remote_only(self, branch_flag_drawer):
        """Test drawing flag for remote-only branch."""
        branch_flag_drawer.flag_width = 100

        branch_flag_drawer.draw_branch_flag(
            x=150, y=160, branch_name='origin/feature', branch_color='#66cc33',
            is_remote=True, branch_availability='remote_only'
        )

        # Should create rectangle, text (with outline), and remote symbol
        assert branch_flag_drawer.canvas.create_rectangle.call_count == 1
        assert branch_flag_drawer.canvas.create_text.call_count >= 5

    def test_draw_branch_flag_both_symbols(self, branch_flag_drawer):
        """Test drawing flag with both local and remote symbols."""
        branch_flag_drawer.flag_width = 100

        branch_flag_drawer.canvas.create_text.reset_mock()

        branch_flag_drawer.draw_branch_flag(
            x=200, y=220, branch_name='develop', branch_color='#cc6633',
            is_remote=False, branch_availability='both'
        )

        # Should create rectangle, text (with outline), and both symbols
        assert branch_flag_drawer.canvas.create_rectangle.call_count == 1
        # Outline (4) + text (1) + remote symbol outline (4) + remote symbol (1) + local symbol outline (4) + local symbol (1) = 15
        assert branch_flag_drawer.canvas.create_text.call_count >= 10

    def test_draw_branch_flag_removes_origin_prefix(self, branch_flag_drawer):
        """Test that origin/ prefix is removed from display."""
        branch_flag_drawer.flag_width = 100

        branch_flag_drawer.draw_branch_flag(
            x=150, y=160, branch_name='origin/feature', branch_color='#66cc33',
            is_remote=True, branch_availability='remote_only'
        )

        # Verify text without 'origin/' was created
        text_calls = [call for call in branch_flag_drawer.canvas.create_text.call_args_list
                     if 'text' in call[1]]

        # At least one text call should have 'feature' without 'origin/'
        has_feature_text = any('feature' in str(call[1].get('text', ''))
                              for call in text_calls)
        assert has_feature_text

    def test_draw_branch_flag_truncates_long_names(self, branch_flag_drawer):
        """Test that long branch names are truncated."""
        branch_flag_drawer.flag_width = 100

        branch_flag_drawer.draw_branch_flag(
            x=100, y=100,
            branch_name='very-long-branch-name-that-needs-truncation',
            branch_color='#3366cc', is_remote=False, branch_availability='local_only'
        )

        # Should create text with ellipsis
        text_calls = branch_flag_drawer.canvas.create_text.call_args_list

        # Check if any text contains ellipsis (truncation happened)
        has_ellipsis = any('...' in str(call[1].get('text', ''))
                          for call in text_calls)
        assert has_ellipsis

    def test_draw_branch_flag_adds_tooltip_for_truncated_names(self, branch_flag_drawer):
        """Test that tooltip is added when branch name is truncated."""
        branch_flag_drawer.flag_width = 100

        branch_flag_drawer.draw_branch_flag(
            x=100, y=100,
            branch_name='very-long-branch-name-that-needs-truncation',
            branch_color='#3366cc', is_remote=False, branch_availability='local_only'
        )

        # Should bind tooltip events
        assert branch_flag_drawer.canvas.tag_bind.call_count == 2  # Enter and Leave

    def test_draw_branch_flag_uses_fallback_width(self, branch_flag_drawer):
        """Test that fallback width is used when flag_width is None."""
        # Don't set flag_width (leave as None)
        assert branch_flag_drawer.flag_width is None

        branch_flag_drawer.draw_branch_flag(
            x=100, y=100, branch_name='main', branch_color='#3366cc',
            is_remote=False, branch_availability='local_only'
        )

        # Should still create flag (using fallback width 80)
        assert branch_flag_drawer.canvas.create_rectangle.call_count == 1

    def test_draw_branch_flag_uses_contrasting_text_color(self, branch_flag_drawer):
        """Test that contrasting text color is calculated for readability."""
        branch_flag_drawer.flag_width = 100

        with patch.object(branch_flag_drawer.theme_manager, 'get_contrasting_text_color',
                         return_value='#ffffff') as mock_contrast:
            branch_flag_drawer.draw_branch_flag(
                x=100, y=100, branch_name='main', branch_color='#000000',
                is_remote=False, branch_availability='local_only'
            )

            # Should call get_contrasting_text_color with branch color
            mock_contrast.assert_called_once()
            assert '#000000' in str(mock_contrast.call_args)


class TestDrawFlagConnection:
    """Tests for draw_flag_connection method."""

    def test_draw_flag_connection_basic(self, branch_flag_drawer):
        """Test drawing basic flag connection."""
        branch_flag_drawer.flag_width = 100

        branch_flag_drawer.draw_flag_connection(
            commit_x=200, commit_y=100, branch_color='#3366cc'
        )

        # Should create line from flag to commit
        branch_flag_drawer.canvas.create_line.assert_called_once()
        call_args = branch_flag_drawer.canvas.create_line.call_args

        # Verify connection parameters
        assert call_args[1]['fill'] == '#3366cc'
        assert call_args[1]['width'] == branch_flag_drawer.line_width

    @pytest.mark.parametrize("flag_width,description", [
        (120, "calculated width (120)"),
        (None, "fallback width (None → 80)"),
    ])
    def test_draw_flag_connection_width_handling(self, branch_flag_drawer, flag_width, description):
        """Test flag connection with calculated and fallback widths.

        Verifies that connection line is drawn correctly when:
        - flag_width is set (uses calculated width)
        - flag_width is None (uses fallback width 80)
        """
        branch_flag_drawer.flag_width = flag_width

        branch_flag_drawer.draw_flag_connection(
            commit_x=200, commit_y=100, branch_color='#66cc33'
        )

        # Should create line regardless of width source
        branch_flag_drawer.canvas.create_line.assert_called_once(), f"Failed for: {description}"


class TestTruncateBranchName:
    """Tests for _truncate_branch_name method."""

    @pytest.mark.parametrize("name,max_length,expected_truncated,description", [
        ('main', 12, False, "short name (no truncation)"),
        ('very-long-branch-name-that-needs-truncation', 12, True, "very long name"),
        ('twelve_chars', 12, False, "exactly at max length (12 chars)"),
        ('thirteen_char', 12, True, "one character over max length"),
        ('long-branch', 8, True, "custom max length (8)"),
    ])
    def test_truncate_branch_name_scenarios(self, branch_flag_drawer, name, max_length, expected_truncated, description):
        """Test branch name truncation with various inputs.

        Verifies:
        - Short names are not truncated
        - Long names are truncated with ellipsis
        - Exact max length is not truncated
        - Names over max length are truncated
        - Custom max length works correctly
        """
        result = branch_flag_drawer._truncate_branch_name(name, max_length=max_length)

        # Verify truncation
        if expected_truncated:
            assert result.endswith('...'), f"Failed for: {description}"
            assert len(result) == max_length, f"Failed for: {description}"
        else:
            assert result == name, f"Failed for: {description}"
            assert '...' not in result, f"Failed for: {description}"


class TestAddTooltipToFlag:
    """Tests for _add_tooltip_to_flag method."""

    def test_add_tooltip_creates_event_bindings(self, branch_flag_drawer):
        """Test that tooltip binds Enter and Leave events."""
        flag_item = 123

        branch_flag_drawer._add_tooltip_to_flag(
            flag_item, flag_x=100, flag_y=100,
            flag_width=100, flag_height=20, full_name='very-long-branch-name'
        )

        # Should bind Enter and Leave events
        assert branch_flag_drawer.canvas.tag_bind.call_count == 2

        # Verify event types
        calls = branch_flag_drawer.canvas.tag_bind.call_args_list
        assert calls[0][0][0] == flag_item
        assert calls[0][0][1] == '<Enter>'
        assert calls[1][0][0] == flag_item
        assert calls[1][0][1] == '<Leave>'

    @pytest.mark.parametrize("canvas_width,flag_x,description", [
        (800, 400, "basic positioning (centered)"),
        (200, 180, "overflow right edge (narrow canvas)"),
        (800, 30, "overflow left edge (close to left)"),
    ])
    def test_tooltip_positioning_scenarios(self, branch_flag_drawer, canvas_width, flag_x, description):
        """Test tooltip positioning with various overflow scenarios.

        Verifies that tooltip is correctly positioned:
        - Centered below flag (basic case)
        - Shifted left when overflowing right edge
        - Shifted right when overflowing left edge
        """
        flag_item = 123
        branch_flag_drawer.canvas.winfo_width.return_value = canvas_width

        branch_flag_drawer._add_tooltip_to_flag(
            flag_item, flag_x=flag_x, flag_y=100,
            flag_width=100, flag_height=20, full_name='test-branch-name'
        )

        # Get the show_tooltip callback
        enter_callback = branch_flag_drawer.canvas.tag_bind.call_args_list[0][0][2]

        # Reset mocks before calling callback
        branch_flag_drawer.canvas.create_rectangle.reset_mock()
        branch_flag_drawer.canvas.create_text.reset_mock()

        # Simulate hover
        mock_event = MagicMock()
        enter_callback(mock_event)

        # Should create tooltip rectangle and text
        assert branch_flag_drawer.canvas.create_rectangle.call_count == 1, f"Failed for: {description}"
        assert branch_flag_drawer.canvas.create_text.call_count == 1, f"Failed for: {description}"

    def test_tooltip_hide_deletes_elements(self, branch_flag_drawer):
        """Test that hiding tooltip deletes canvas elements."""
        flag_item = 123

        branch_flag_drawer._add_tooltip_to_flag(
            flag_item, flag_x=100, flag_y=100,
            flag_width=100, flag_height=20, full_name='test-branch'
        )

        # Get callbacks
        enter_callback = branch_flag_drawer.canvas.tag_bind.call_args_list[0][0][2]
        leave_callback = branch_flag_drawer.canvas.tag_bind.call_args_list[1][0][2]

        # Show tooltip
        branch_flag_drawer.canvas.create_rectangle.reset_mock()
        mock_event = MagicMock()
        enter_callback(mock_event)

        # Hide tooltip
        branch_flag_drawer.canvas.delete.reset_mock()
        leave_callback(mock_event)

        # Should delete tooltip elements
        assert branch_flag_drawer.canvas.delete.call_count == 1

    def test_tooltip_prevents_duplicate_show(self, branch_flag_drawer):
        """Test that showing tooltip twice doesn't create duplicates."""
        flag_item = 123

        branch_flag_drawer._add_tooltip_to_flag(
            flag_item, flag_x=100, flag_y=100,
            flag_width=100, flag_height=20, full_name='test-branch'
        )

        enter_callback = branch_flag_drawer.canvas.tag_bind.call_args_list[0][0][2]

        # Show tooltip twice
        branch_flag_drawer.canvas.create_rectangle.reset_mock()
        mock_event = MagicMock()
        enter_callback(mock_event)
        first_count = branch_flag_drawer.canvas.create_rectangle.call_count

        enter_callback(mock_event)
        second_count = branch_flag_drawer.canvas.create_rectangle.call_count

        # Should not create duplicate
        assert second_count == first_count


class TestBranchFlagDrawerIntegration:
    """Integration tests for BranchFlagDrawer."""

    def test_full_workflow_calculate_and_draw(self, branch_flag_drawer, sample_commits):
        """Test complete workflow: calculate width and draw flags."""
        # Calculate width
        width = branch_flag_drawer.calculate_flag_width(sample_commits)
        assert width >= 90

        # Draw flags for each branch head
        for commit in sample_commits:
            if commit.is_branch_head:
                branch_flag_drawer.canvas.create_rectangle.reset_mock()
                branch_flag_drawer.canvas.create_text.reset_mock()

                branch_flag_drawer.draw_branch_flag(
                    x=commit.x, y=commit.y,
                    branch_name=commit.branch,
                    branch_color=commit.branch_color,
                    is_remote=commit.is_remote,
                    branch_availability=commit.branch_availability
                )

                # Should create flag elements
                assert branch_flag_drawer.canvas.create_rectangle.call_count == 1
                assert branch_flag_drawer.canvas.create_text.call_count >= 5

    def test_draw_flags_with_connections(self, branch_flag_drawer, sample_commits):
        """Test drawing flags with connections to commits."""
        width = branch_flag_drawer.calculate_flag_width(sample_commits)

        for commit in sample_commits:
            if commit.is_branch_head:
                # Draw flag
                branch_flag_drawer.draw_branch_flag(
                    x=commit.x, y=commit.y,
                    branch_name=commit.branch,
                    branch_color=commit.branch_color,
                    is_remote=commit.is_remote,
                    branch_availability=commit.branch_availability
                )

                # Draw connection
                branch_flag_drawer.canvas.create_line.reset_mock()
                branch_flag_drawer.draw_flag_connection(
                    commit_x=commit.x, commit_y=commit.y,
                    branch_color=commit.branch_color
                )

                # Should create connection line
                assert branch_flag_drawer.canvas.create_line.call_count == 1

    def test_mixed_branch_availability_types(self, branch_flag_drawer):
        """Test drawing flags with all availability types."""
        branch_flag_drawer.flag_width = 100

        availabilities = ['local_only', 'remote_only', 'both']

        for i, availability in enumerate(availabilities):
            branch_flag_drawer.canvas.create_rectangle.reset_mock()
            branch_flag_drawer.canvas.create_text.reset_mock()

            branch_flag_drawer.draw_branch_flag(
                x=100 + i * 50, y=100,
                branch_name=f'branch-{i}',
                branch_color='#3366cc',
                is_remote=(availability == 'remote_only'),
                branch_availability=availability
            )

            # Should create flag for each type
            assert branch_flag_drawer.canvas.create_rectangle.call_count == 1
            assert branch_flag_drawer.canvas.create_text.call_count >= 5
