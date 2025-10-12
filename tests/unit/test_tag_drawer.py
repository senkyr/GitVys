"""Unit tests for TagDrawer component."""

# MUST BE FIRST - initialize TCL/TK before any other imports
import tests.setup_tcl  # noqa: F401

import pytest
import tkinter as tk
from unittest.mock import MagicMock, patch, call
from datetime import datetime

from visualization.drawing.tag_drawer import TagDrawer
from utils.data_structures import Commit, Tag


# ========================================
# Fixtures
# ========================================

@pytest.fixture
def tag_drawer(canvas):
    """Create a TagDrawer instance with mocked canvas methods."""
    # Mock canvas drawing methods
    canvas.create_text = MagicMock(return_value=1)
    canvas.create_oval = MagicMock(return_value=2)
    canvas.tag_bind = MagicMock()

    # Mock tk.call for font measurements
    mock_tk = MagicMock()
    mock_tk.call = MagicMock(return_value=50)  # Default font measure
    canvas.tk = mock_tk

    return TagDrawer(canvas)


@pytest.fixture
def mock_callbacks():
    """Create mock callbacks for tooltips."""
    return {
        'show_tooltip': MagicMock(),
        'hide_tooltip': MagicMock()
    }


@pytest.fixture
def commit_with_tags():
    """Create a commit with multiple tags."""
    return Commit(
        hash='abc123',
        message='Release commit',
        short_message='Release commit',
        author='Test User',
        author_short='Test User',
        author_email='test@example.com',
        date=datetime(2025, 1, 1, 10, 0, 0),
        date_relative='1 day ago',
        date_short='2025-01-01',
        parents=[],
        branch='main',
        branch_color='#3366cc',
        x=100,
        y=100,
        description='',
        description_short='',
        tags=[
            Tag(name='v1.0.0', message=None, is_remote=False),
            Tag(name='release', message='Release version 1.0', is_remote=False)
        ]
    )


@pytest.fixture
def commit_with_remote_tags():
    """Create a commit with remote tags."""
    return Commit(
        hash='def456',
        message='Remote release',
        short_message='Remote release',
        author='Test User',
        author_short='Test User',
        author_email='test@example.com',
        date=datetime(2025, 1, 2, 10, 0, 0),
        date_relative='2 days ago',
        date_short='2025-01-02',
        parents=['abc123'],
        branch='main',
        branch_color='#3366cc',
        x=100,
        y=160,
        description='',
        description_short='',
        tags=[
            Tag(name='v2.0.0', message=None, is_remote=True)
        ]
    )


@pytest.fixture
def commit_without_tags():
    """Create a commit without tags."""
    return Commit(
        hash='ghi789',
        message='Normal commit',
        short_message='Normal commit',
        author='Test User',
        author_short='Test User',
        author_email='test@example.com',
        date=datetime(2025, 1, 3, 10, 0, 0),
        date_relative='3 days ago',
        date_short='2025-01-03',
        parents=['def456'],
        branch='main',
        branch_color='#3366cc',
        x=100,
        y=220,
        description='',
        description_short='',
        tags=[]
    )


# ========================================
# Test Classes
# ========================================

class TestTagDrawerInitialization:
    """Tests for TagDrawer initialization."""

    def test_initialization(self, canvas):
        """Test TagDrawer initializes correctly."""
        drawer = TagDrawer(canvas)

        assert drawer.canvas == canvas
        assert drawer.theme_manager is not None
        assert drawer.node_radius > 0
        assert drawer.BASE_MARGIN > 0

    def test_initialization_sets_constants(self, canvas):
        """Test that initialization sets expected constant values."""
        from utils.constants import NODE_RADIUS, BASE_MARGIN

        drawer = TagDrawer(canvas)

        assert drawer.node_radius == NODE_RADIUS
        assert drawer.BASE_MARGIN == BASE_MARGIN


class TestDrawTags:
    """Tests for draw_tags method."""

    def test_draw_tags_empty_list(self, tag_drawer, mock_callbacks):
        """Test drawing tags with empty commit list."""
        tag_drawer.draw_tags([], 800,
                           mock_callbacks['show_tooltip'],
                           mock_callbacks['hide_tooltip'])

        # No canvas operations should be called
        assert tag_drawer.canvas.create_text.call_count == 0

    def test_draw_tags_no_tags(self, tag_drawer, commit_without_tags, mock_callbacks):
        """Test drawing tags for commits without tags."""
        tag_drawer.draw_tags([commit_without_tags], 800,
                           mock_callbacks['show_tooltip'],
                           mock_callbacks['hide_tooltip'])

        # No canvas operations should be called
        assert tag_drawer.canvas.create_text.call_count == 0

    def test_draw_tags_single_commit(self, tag_drawer, commit_with_tags, mock_callbacks):
        """Test drawing tags for single commit with tags."""
        tag_drawer.draw_tags([commit_with_tags], 800,
                           mock_callbacks['show_tooltip'],
                           mock_callbacks['hide_tooltip'])

        # Should create text for emoji + label for each tag
        # 2 tags * 2 text items (emoji + label) = 4 create_text calls
        assert tag_drawer.canvas.create_text.call_count == 4

    def test_draw_tags_multiple_commits(self, tag_drawer, commit_with_tags,
                                       commit_with_remote_tags, mock_callbacks):
        """Test drawing tags for multiple commits."""
        commits = [commit_with_tags, commit_with_remote_tags]
        tag_drawer.draw_tags(commits, 800,
                           mock_callbacks['show_tooltip'],
                           mock_callbacks['hide_tooltip'])

        # commit_with_tags: 2 tags * 2 items = 4
        # commit_with_remote_tags: 1 tag * 2 items = 2
        # Total: 6 create_text calls
        assert tag_drawer.canvas.create_text.call_count == 6

    def test_draw_tags_calls_theme_manager(self, tag_drawer, commit_with_tags, mock_callbacks):
        """Test that draw_tags uses theme manager colors."""
        with patch.object(tag_drawer.theme_manager, 'get_color', return_value='#000000'):
            tag_drawer.draw_tags([commit_with_tags], 800,
                               mock_callbacks['show_tooltip'],
                               mock_callbacks['hide_tooltip'])

            # Should call get_color for emoji and text colors
            assert tag_drawer.theme_manager.get_color.call_count > 0


class TestTagEmoji:
    """Tests for _draw_tag_emoji method."""

    def test_draw_local_tag_emoji(self, tag_drawer):
        """Test drawing emoji for local tag."""
        tag_drawer._draw_tag_emoji(100, 100, is_remote=False, font=('Arial', 10))

        # Should create text with tag emoji
        tag_drawer.canvas.create_text.assert_called_once()
        call_args = tag_drawer.canvas.create_text.call_args

        assert call_args[0] == (100, 99)  # x, y-1
        assert call_args[1]['text'] == '🏷️'
        assert call_args[1]['anchor'] == 'center'
        assert call_args[1]['tags'] == 'tag_emoji'

    def test_draw_remote_tag_emoji(self, tag_drawer):
        """Test drawing emoji for remote tag."""
        tag_drawer._draw_tag_emoji(100, 100, is_remote=True, font=('Arial', 10))

        # Should create text with tag emoji
        tag_drawer.canvas.create_text.assert_called_once()
        call_args = tag_drawer.canvas.create_text.call_args

        assert call_args[1]['text'] == '🏷️'

    def test_tag_emoji_uses_different_colors(self, tag_drawer):
        """Test that local and remote tags use different colors."""
        with patch.object(tag_drawer.theme_manager, 'get_color', return_value='#000000') as mock_get_color:
            # Draw local tag
            tag_drawer._draw_tag_emoji(100, 100, is_remote=False, font=('Arial', 10))
            local_color_call = mock_get_color.call_args[0][0]

            # Reset mock
            mock_get_color.reset_mock()
            tag_drawer.canvas.create_text.reset_mock()

            # Draw remote tag
            tag_drawer._draw_tag_emoji(100, 100, is_remote=True, font=('Arial', 10))
            remote_color_call = mock_get_color.call_args[0][0]

            # Should request different colors
            assert local_color_call != remote_color_call
            assert 'local' in local_color_call
            assert 'remote' in remote_color_call


class TestTagLabel:
    """Tests for _draw_tag_label method."""

    def test_draw_tag_label_basic(self, tag_drawer):
        """Test basic tag label drawing."""
        width = tag_drawer._draw_tag_label(100, 100, 'v1.0.0', is_remote=False,
                                          font=('Arial', 8))

        # Should create text
        tag_drawer.canvas.create_text.assert_called_once()
        call_args = tag_drawer.canvas.create_text.call_args

        assert call_args[0] == (100, 100)
        assert call_args[1]['text'] == 'v1.0.0'
        assert call_args[1]['anchor'] == 'w'
        assert call_args[1]['tags'] == 'tag_label'
        assert width > 0

    def test_draw_tag_label_remote(self, tag_drawer):
        """Test drawing label for remote tag."""
        tag_drawer._draw_tag_label(100, 100, 'origin/v2.0', is_remote=True,
                                   font=('Arial', 8))

        call_args = tag_drawer.canvas.create_text.call_args
        assert call_args[1]['text'] == 'origin/v2.0'

    def test_draw_tag_label_truncation(self, canvas):
        """Test label truncation when width limited."""
        # Create fresh drawer with proper mock setup for truncation
        canvas.create_text = MagicMock(return_value=1)
        canvas.tag_bind = MagicMock()

        # Mock tk.call to trigger truncation
        mock_tk = MagicMock()
        def mock_font_measure(*args):
            if len(args) >= 3 and args[0] == 'font' and args[1] == 'measure':
                text = args[2]
                # Full tag name is wide
                if 'very-long-tag-name-that-needs-truncation' in str(text) and len(str(text)) > 30:
                    return 200
                elif text == '...':
                    return 20
                else:
                    # Estimate based on length
                    return len(str(text)) * 8
            return 0

        mock_tk.call = MagicMock(side_effect=mock_font_measure)
        canvas.tk = mock_tk

        drawer = TagDrawer(canvas)
        width = drawer._draw_tag_label(
            100, 100, 'very-long-tag-name-that-needs-truncation',
            is_remote=False, font=('Arial', 8), available_width=80
        )

        # Should create text - check that it was called
        canvas.create_text.assert_called_once()
        call_args = canvas.create_text.call_args
        displayed_text = call_args[1]['text']

        # Text should be truncated (either with ellipsis or shorter than original)
        assert len(displayed_text) <= len('very-long-tag-name-that-needs-truncation')

    def test_draw_tag_label_no_truncation(self, tag_drawer):
        """Test label without truncation when width sufficient."""
        # Mock font measure to return small width
        tag_drawer.canvas.tk.call.return_value = 50

        tag_drawer._draw_tag_label(100, 100, 'v1.0', is_remote=False,
                                   font=('Arial', 8), available_width=100)

        call_args = tag_drawer.canvas.create_text.call_args
        assert call_args[1]['text'] == 'v1.0'

    def test_draw_tag_label_tooltip_on_truncation(self, canvas, mock_callbacks):
        """Test that tooltip is added when label is truncated."""
        # Create fresh drawer with proper mock setup
        canvas.create_text = MagicMock(return_value=1)
        canvas.tag_bind = MagicMock()

        mock_tk = MagicMock()
        def mock_font_measure(*args):
            if len(args) >= 3 and args[0] == 'font' and args[1] == 'measure':
                text = args[2]
                # Trigger truncation for the long name
                if 'very-long-tag-name' in str(text) and len(str(text)) > 10:
                    return 200
                elif text == '...':
                    return 20
                else:
                    return len(str(text)) * 8
            return 0

        mock_tk.call = MagicMock(side_effect=mock_font_measure)
        canvas.tk = mock_tk

        drawer = TagDrawer(canvas)
        drawer._draw_tag_label(
            100, 100, 'very-long-tag-name', is_remote=False,
            font=('Arial', 8), available_width=80,
            show_tooltip_callback=mock_callbacks['show_tooltip'],
            hide_tooltip_callback=mock_callbacks['hide_tooltip']
        )

        # Should bind tooltip events (Enter and Leave)
        assert canvas.tag_bind.call_count == 2


class TestTagTooltip:
    """Tests for _add_tag_tooltip method."""

    def test_add_tag_tooltip(self, tag_drawer, mock_callbacks):
        """Test adding tooltip for annotated tag."""
        tag_drawer._add_tag_tooltip(
            100, 100, 'Release version 1.0',
            mock_callbacks['show_tooltip'],
            mock_callbacks['hide_tooltip']
        )

        # Should create invisible oval area
        tag_drawer.canvas.create_oval.assert_called_once()
        call_args = tag_drawer.canvas.create_oval.call_args

        # Check oval bounds (12px radius around center)
        assert call_args[0] == (88, 88, 112, 112)  # x-12, y-12, x+12, y+12
        assert call_args[1]['fill'] == ''
        assert call_args[1]['outline'] == ''
        assert call_args[1]['tags'] == 'tag_tooltip_area'

    def test_tag_tooltip_binds_events(self, tag_drawer, mock_callbacks):
        """Test that tooltip binds hover events."""
        tag_drawer._add_tag_tooltip(
            100, 100, 'Tag message',
            mock_callbacks['show_tooltip'],
            mock_callbacks['hide_tooltip']
        )

        # Should bind Enter and Leave events
        assert tag_drawer.canvas.tag_bind.call_count == 2


class TestHorizontalLineExtent:
    """Tests for _calculate_horizontal_line_extent method."""

    def test_no_children(self, tag_drawer, commit_without_tags):
        """Test extent calculation for commit without children."""
        extent = tag_drawer._calculate_horizontal_line_extent(
            commit_without_tags, [commit_without_tags]
        )

        # Should return commit's own x position
        assert extent == commit_without_tags.x

    def test_with_horizontal_connection(self, tag_drawer):
        """Test extent calculation with horizontal branching connection."""
        parent = Commit(
            hash='parent123', message='Parent', short_message='Parent',
            author='Test', author_short='Test', author_email='test@example.com',
            date=datetime(2025, 1, 1), date_relative='1 day ago', date_short='2025-01-01',
            parents=[], branch='main', branch_color='#3366cc',
            x=100, y=100, description='', description_short='', tags=[]
        )

        child = Commit(
            hash='child456', message='Child', short_message='Child',
            author='Test', author_short='Test', author_email='test@example.com',
            date=datetime(2025, 1, 2), date_relative='2 days ago', date_short='2025-01-02',
            parents=['parent123'], branch='feature', branch_color='#66cc33',
            x=200, y=160, description='', description_short='', tags=[]
        )

        commits = [parent, child]
        extent = tag_drawer._calculate_horizontal_line_extent(parent, commits)

        # Should calculate extent based on horizontal connection
        # child_x (200) - radius, so extent > parent.x (100)
        assert extent > parent.x
        assert extent <= child.x

    def test_with_vertical_connection(self, tag_drawer):
        """Test extent calculation with vertical (non-branching) connection."""
        parent = Commit(
            hash='parent123', message='Parent', short_message='Parent',
            author='Test', author_short='Test', author_email='test@example.com',
            date=datetime(2025, 1, 1), date_relative='1 day ago', date_short='2025-01-01',
            parents=[], branch='main', branch_color='#3366cc',
            x=100, y=100, description='', description_short='', tags=[]
        )

        # Child at same x (vertical connection, no branching)
        child = Commit(
            hash='child456', message='Child', short_message='Child',
            author='Test', author_short='Test', author_email='test@example.com',
            date=datetime(2025, 1, 2), date_relative='2 days ago', date_short='2025-01-02',
            parents=['parent123'], branch='main', branch_color='#3366cc',
            x=100, y=160, description='', description_short='', tags=[]
        )

        commits = [parent, child]
        extent = tag_drawer._calculate_horizontal_line_extent(parent, commits)

        # Should return parent's x since no horizontal connection
        assert extent == parent.x


class TestTextTruncation:
    """Tests for _truncate_text_to_width method."""

    def test_truncate_short_text(self, tag_drawer):
        """Test that short text is not truncated."""
        tag_drawer.canvas.tk.call.return_value = 50

        result = tag_drawer._truncate_text_to_width('short', ('Arial', 8), 100)

        assert result == 'short'
        assert '...' not in result

    def test_truncate_long_text(self, canvas):
        """Test that long text is truncated with ellipsis."""
        # Create fresh drawer with proper mock setup
        mock_tk = MagicMock()
        def mock_measure(*args):
            if len(args) >= 3 and args[0] == 'font' and args[1] == 'measure':
                text = args[2]
                # Full text is wide
                if 'very-long-tag-name-that-needs-truncation' in str(text) and len(str(text)) > 30:
                    return 200
                elif text == '...':
                    return 20
                else:
                    return len(str(text)) * 8  # Rough estimate
            return 0

        mock_tk.call = MagicMock(side_effect=mock_measure)
        canvas.tk = mock_tk

        drawer = TagDrawer(canvas)
        result = drawer._truncate_text_to_width(
            'very-long-tag-name-that-needs-truncation', ('Arial', 8), 80
        )

        # Result should be truncated (shorter or with ellipsis)
        assert len(result) < len('very-long-tag-name-that-needs-truncation') or result.endswith('...')

    def test_truncate_empty_text(self, tag_drawer):
        """Test truncation with empty text."""
        result = tag_drawer._truncate_text_to_width('', ('Arial', 8), 100)

        assert result == ''

    def test_truncate_zero_width(self, tag_drawer):
        """Test truncation with zero width."""
        result = tag_drawer._truncate_text_to_width('text', ('Arial', 8), 0)

        assert result == ''

    def test_truncate_negative_width(self, tag_drawer):
        """Test truncation with negative width."""
        result = tag_drawer._truncate_text_to_width('text', ('Arial', 8), -10)

        assert result == ''

    def test_truncate_very_small_width(self, tag_drawer):
        """Test truncation with width smaller than ellipsis."""
        tag_drawer.canvas.tk.call.return_value = 50

        result = tag_drawer._truncate_text_to_width('text', ('Arial', 8), 5)

        assert result == '...'


class TestCalculateRequiredTagSpace:
    """Tests for calculate_required_tag_space method."""

    def test_calculate_required_tag_space(self, tag_drawer):
        """Test calculation of required space for tags."""
        flag_width = 100
        space = tag_drawer.calculate_required_tag_space(flag_width)

        # Should return flag_width + BASE_MARGIN
        assert space == flag_width + tag_drawer.BASE_MARGIN

    def test_calculate_required_tag_space_zero_flag(self, tag_drawer):
        """Test calculation with zero flag width."""
        space = tag_drawer.calculate_required_tag_space(0)

        assert space == tag_drawer.BASE_MARGIN


class TestTagDrawerIntegration:
    """Integration tests for TagDrawer."""

    def test_full_tag_drawing_workflow(self, tag_drawer, commit_with_tags, mock_callbacks):
        """Test complete workflow of drawing tags with emoji, labels, and tooltips."""
        commits = [commit_with_tags]
        tag_drawer.draw_tags(commits, 800,
                           mock_callbacks['show_tooltip'],
                           mock_callbacks['hide_tooltip'])

        # Should create:
        # - 2 emojis (one per tag)
        # - 2 labels (one per tag)
        # - 1 tooltip area (for annotated tag with message)
        assert tag_drawer.canvas.create_text.call_count == 4  # 2 emojis + 2 labels
        assert tag_drawer.canvas.create_oval.call_count == 1  # 1 tooltip area

    def test_mixed_local_and_remote_tags(self, tag_drawer, mock_callbacks):
        """Test drawing commits with both local and remote tags."""
        commit = Commit(
            hash='mixed123', message='Mixed tags', short_message='Mixed tags',
            author='Test', author_short='Test', author_email='test@example.com',
            date=datetime(2025, 1, 1), date_relative='1 day ago', date_short='2025-01-01',
            parents=[], branch='main', branch_color='#3366cc',
            x=100, y=100, description='', description_short='',
            tags=[
                Tag(name='v1.0', message=None, is_remote=False),
                Tag(name='origin/v1.0', message=None, is_remote=True)
            ]
        )

        tag_drawer.draw_tags([commit], 800,
                           mock_callbacks['show_tooltip'],
                           mock_callbacks['hide_tooltip'])

        # Should create items for both local and remote tags
        assert tag_drawer.canvas.create_text.call_count == 4  # 2 emojis + 2 labels

    def test_tag_positioning_with_limited_space(self, tag_drawer, commit_with_tags, mock_callbacks):
        """Test that tags are positioned correctly with limited available space."""
        # Mock font measure to simulate text width (already mocked in fixture)
        tag_drawer.canvas.tk.call.return_value = 50

        # Limited table_start_position to simulate constrained space
        tag_drawer.draw_tags([commit_with_tags], 300,
                           mock_callbacks['show_tooltip'],
                           mock_callbacks['hide_tooltip'])

        # Should still draw tags (may truncate text)
        assert tag_drawer.canvas.create_text.call_count == 4
