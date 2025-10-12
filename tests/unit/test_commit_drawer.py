"""Unit tests for visualization.drawing.commit_drawer module."""

import pytest
import math
from unittest.mock import MagicMock, patch, call
from visualization.drawing.commit_drawer import CommitDrawer
from utils.data_structures import Commit
from datetime import datetime


@pytest.fixture
def mock_canvas():
    """Create a mock tkinter Canvas."""
    canvas = MagicMock()
    canvas.create_oval.return_value = 1
    canvas.create_polygon.return_value = 2
    canvas.create_text.return_value = 3
    canvas.tag_bind = MagicMock()
    # Mock font measure
    canvas.tk = MagicMock()
    canvas.tk.call = MagicMock(return_value=100)  # Default text width
    return canvas


@pytest.fixture
def mock_theme_manager():
    """Create a mock ThemeManager."""
    with patch('visualization.drawing.commit_drawer.get_theme_manager') as mock:
        theme_mgr = MagicMock()
        theme_mgr.get_color.return_value = '#000000'
        mock.return_value = theme_mgr
        yield theme_mgr


@pytest.fixture
def commit_drawer(mock_canvas, mock_theme_manager):
    """Create a CommitDrawer instance."""
    return CommitDrawer(mock_canvas)


@pytest.fixture
def mock_callbacks():
    """Create mock callbacks for draw_commits."""
    return {
        'show_tooltip': MagicMock(),
        'hide_tooltip': MagicMock(),
        'truncate_text': MagicMock(side_effect=lambda c, f, t, w: t),  # No truncation by default
        'make_color_pale': MagicMock(side_effect=lambda c: f"{c}_pale"),
        'draw_flag_connection': MagicMock()
    }


@pytest.fixture
def mock_branch_flag_drawer():
    """Create mock BranchFlagDrawer."""
    drawer = MagicMock()
    drawer.draw_branch_flag = MagicMock()
    return drawer


@pytest.fixture
def sample_column_widths():
    """Sample column widths."""
    return {
        'message': 400,
        'author': 150,
        'email': 200,
        'date': 100
    }


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
        tags=[],
        is_remote=False,
        is_branch_head=False,
        branch_head_type=None,
        branch_availability='local_only'
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
        tags=[],
        is_remote=False,
        is_branch_head=False,
        branch_head_type=None,
        branch_availability='local_only'
    )

    return [commit1, commit2]


# ===== Initialization Tests =====

class TestCommitDrawerInitialization:
    """Tests for CommitDrawer initialization."""

    def test_initialization(self, mock_canvas, mock_theme_manager):
        """Test that CommitDrawer initializes correctly."""
        drawer = CommitDrawer(mock_canvas)

        assert drawer.canvas is mock_canvas
        assert drawer.theme_manager is mock_theme_manager
        assert drawer.node_radius > 0
        assert drawer.font_size > 0

    def test_initialization_sets_constants(self, commit_drawer):
        """Test that initialization sets node radius and font size from constants."""
        from utils.constants import NODE_RADIUS, FONT_SIZE

        assert commit_drawer.node_radius == NODE_RADIUS
        assert commit_drawer.font_size == FONT_SIZE


# ===== Draw Commits Tests =====

class TestDrawCommits:
    """Tests for drawing commits."""

    def test_draw_commits_empty_list(self, commit_drawer, mock_callbacks, mock_branch_flag_drawer, sample_column_widths, mock_canvas):
        """Test that draw_commits handles empty commit list."""
        commit_drawer.draw_commits(
            [], sample_column_widths,
            mock_callbacks['show_tooltip'],
            mock_callbacks['hide_tooltip'],
            mock_callbacks['truncate_text'],
            100,
            mock_callbacks['make_color_pale'],
            mock_branch_flag_drawer,
            mock_callbacks['draw_flag_connection']
        )

        # Should not draw any nodes
        mock_canvas.create_oval.assert_not_called()
        mock_canvas.create_polygon.assert_not_called()

    def test_draw_commits_draws_nodes(self, commit_drawer, sample_commits, mock_callbacks, mock_branch_flag_drawer, sample_column_widths, mock_canvas):
        """Test that draw_commits draws commit nodes."""
        commit_drawer.draw_commits(
            sample_commits, sample_column_widths,
            mock_callbacks['show_tooltip'],
            mock_callbacks['hide_tooltip'],
            mock_callbacks['truncate_text'],
            100,
            mock_callbacks['make_color_pale'],
            mock_branch_flag_drawer,
            mock_callbacks['draw_flag_connection']
        )

        # Should draw 2 oval nodes (one for each commit)
        assert mock_canvas.create_oval.call_count == 2

    def test_draw_commits_draws_text(self, commit_drawer, sample_commits, mock_callbacks, mock_branch_flag_drawer, sample_column_widths, mock_canvas):
        """Test that draw_commits draws commit text."""
        commit_drawer.draw_commits(
            sample_commits, sample_column_widths,
            mock_callbacks['show_tooltip'],
            mock_callbacks['hide_tooltip'],
            mock_callbacks['truncate_text'],
            100,
            mock_callbacks['make_color_pale'],
            mock_branch_flag_drawer,
            mock_callbacks['draw_flag_connection']
        )

        # Should draw text for message, author, email, date for each commit
        # 2 commits * 4 fields = 8 text items
        assert mock_canvas.create_text.call_count >= 8


# ===== Node Types Tests =====

class TestNodeTypes:
    """Tests for different node types (normal, remote, uncommitted)."""

    def test_draw_normal_commit(self, commit_drawer, mock_callbacks, mock_branch_flag_drawer, sample_column_widths, mock_canvas):
        """Test drawing normal commit node."""
        commit = Commit(
            hash='abc', message='Test', short_message='Test',
            author='User', author_short='User', author_email='email@test.com',
            date=datetime(2025, 1, 1), date_relative='1 day ago', date_short='2025-01-01',
            parents=[], branch='main', branch_color='#3366cc',
            x=50, y=50, description='', description_short='', tags=[],
            is_remote=False, is_branch_head=False, branch_head_type=None, branch_availability='local_only'
        )

        commit_drawer.draw_commits(
            [commit], sample_column_widths,
            mock_callbacks['show_tooltip'],
            mock_callbacks['hide_tooltip'],
            mock_callbacks['truncate_text'],
            100,
            mock_callbacks['make_color_pale'],
            mock_branch_flag_drawer,
            mock_callbacks['draw_flag_connection']
        )

        # Should draw oval (not polygon)
        mock_canvas.create_oval.assert_called_once()
        # Check that it used branch color
        call_kwargs = mock_canvas.create_oval.call_args[1]
        assert call_kwargs['fill'] == '#3366cc'

    def test_draw_remote_commit(self, commit_drawer, mock_callbacks, mock_branch_flag_drawer, sample_column_widths, mock_canvas):
        """Test drawing remote commit node (pale color)."""
        commit = Commit(
            hash='abc', message='Test', short_message='Test',
            author='User', author_short='User', author_email='email@test.com',
            date=datetime(2025, 1, 1), date_relative='1 day ago', date_short='2025-01-01',
            parents=[], branch='origin/main', branch_color='#3366cc',
            x=50, y=50, description='', description_short='', tags=[],
            is_remote=True, is_branch_head=False, branch_head_type=None, branch_availability='remote_only'
        )

        commit_drawer.draw_commits(
            [commit], sample_column_widths,
            mock_callbacks['show_tooltip'],
            mock_callbacks['hide_tooltip'],
            mock_callbacks['truncate_text'],
            100,
            mock_callbacks['make_color_pale'],
            mock_branch_flag_drawer,
            mock_callbacks['draw_flag_connection']
        )

        # Should draw oval with pale color
        mock_canvas.create_oval.assert_called_once()
        call_kwargs = mock_canvas.create_oval.call_args[1]
        assert call_kwargs['fill'] == '#3366cc_pale'

    def test_draw_uncommitted_commit(self, commit_drawer, mock_callbacks, mock_branch_flag_drawer, sample_column_widths, mock_canvas):
        """Test drawing uncommitted (WIP) commit node (stippled polygon)."""
        commit = Commit(
            hash='wip', message='WIP: Work in progress', short_message='WIP: Work in progress',
            author='User', author_short='User', author_email='email@test.com',
            date=datetime(2025, 1, 1), date_relative='1 day ago', date_short='2025-01-01',
            parents=[], branch='main', branch_color='#3366cc',
            x=50, y=50, description='', description_short='', tags=[],
            is_remote=False, is_branch_head=False, branch_head_type=None, branch_availability='local_only'
        )
        commit.is_uncommitted = True

        commit_drawer.draw_commits(
            [commit], sample_column_widths,
            mock_callbacks['show_tooltip'],
            mock_callbacks['hide_tooltip'],
            mock_callbacks['truncate_text'],
            100,
            mock_callbacks['make_color_pale'],
            mock_branch_flag_drawer,
            mock_callbacks['draw_flag_connection']
        )

        # Should draw polygon (not oval) with stipple
        mock_canvas.create_polygon.assert_called_once()
        call_kwargs = mock_canvas.create_polygon.call_args[1]
        assert call_kwargs['stipple'] == 'gray50'


# ===== Text Rendering Tests =====

class TestTextRendering:
    """Tests for text rendering (message, author, email, date)."""

    def test_draw_message_without_description(self, commit_drawer, mock_callbacks, mock_branch_flag_drawer, sample_column_widths, mock_canvas):
        """Test drawing commit message without description."""
        commit = Commit(
            hash='abc', message='Simple message', short_message='Simple message',
            author='User', author_short='User', author_email='email@test.com',
            date=datetime(2025, 1, 1), date_relative='1 day ago', date_short='2025-01-01',
            parents=[], branch='main', branch_color='#3366cc',
            x=50, y=50, description='', description_short='', tags=[],
            is_remote=False, is_branch_head=False, branch_head_type=None, branch_availability='local_only'
        )

        commit_drawer.draw_commits(
            [commit], sample_column_widths,
            mock_callbacks['show_tooltip'],
            mock_callbacks['hide_tooltip'],
            mock_callbacks['truncate_text'],
            100,
            mock_callbacks['make_color_pale'],
            mock_branch_flag_drawer,
            mock_callbacks['draw_flag_connection']
        )

        # Should draw message text
        text_calls = [c for c in mock_canvas.create_text.call_args_list if 'Simple message' in str(c)]
        assert len(text_calls) > 0

    def test_draw_message_with_description(self, commit_drawer, mock_callbacks, mock_branch_flag_drawer, sample_column_widths, mock_canvas):
        """Test drawing commit message with description."""
        commit = Commit(
            hash='abc', message='Message', short_message='Message',
            author='User', author_short='User', author_email='email@test.com',
            date=datetime(2025, 1, 1), date_relative='1 day ago', date_short='2025-01-01',
            parents=[], branch='main', branch_color='#3366cc',
            x=50, y=50, description='Full description text', description_short='Full description text', tags=[],
            is_remote=False, is_branch_head=False, branch_head_type=None, branch_availability='local_only'
        )

        commit_drawer.draw_commits(
            [commit], sample_column_widths,
            mock_callbacks['show_tooltip'],
            mock_callbacks['hide_tooltip'],
            mock_callbacks['truncate_text'],
            100,
            mock_callbacks['make_color_pale'],
            mock_branch_flag_drawer,
            mock_callbacks['draw_flag_connection']
        )

        # Should draw both message and description
        assert mock_canvas.create_text.call_count >= 5  # message, description, author, email, date

    def test_draw_author_and_email(self, commit_drawer, sample_commits, mock_callbacks, mock_branch_flag_drawer, sample_column_widths, mock_canvas):
        """Test drawing author and email fields."""
        commit_drawer.draw_commits(
            sample_commits, sample_column_widths,
            mock_callbacks['show_tooltip'],
            mock_callbacks['hide_tooltip'],
            mock_callbacks['truncate_text'],
            100,
            mock_callbacks['make_color_pale'],
            mock_branch_flag_drawer,
            mock_callbacks['draw_flag_connection']
        )

        # Check that author and email were drawn
        text_calls = [str(c) for c in mock_canvas.create_text.call_args_list]
        has_author = any('Test User' in c for c in text_calls)
        has_email = any('test@example.com' in c for c in text_calls)
        assert has_author
        assert has_email

    def test_uncommitted_skips_author_email_date(self, commit_drawer, mock_callbacks, mock_branch_flag_drawer, sample_column_widths, mock_canvas):
        """Test that uncommitted commits don't draw author/email/date."""
        commit = Commit(
            hash='wip', message='WIP', short_message='WIP',
            author='User', author_short='User', author_email='email@test.com',
            date=datetime(2025, 1, 1), date_relative='1 day ago', date_short='2025-01-01',
            parents=[], branch='main', branch_color='#3366cc',
            x=50, y=50, description='', description_short='', tags=[],
            is_remote=False, is_branch_head=False, branch_head_type=None, branch_availability='local_only'
        )
        commit.is_uncommitted = True

        commit_drawer.draw_commits(
            [commit], sample_column_widths,
            mock_callbacks['show_tooltip'],
            mock_callbacks['hide_tooltip'],
            mock_callbacks['truncate_text'],
            100,
            mock_callbacks['make_color_pale'],
            mock_branch_flag_drawer,
            mock_callbacks['draw_flag_connection']
        )

        # Should only draw message (no author, email, date for WIP)
        # 1 text = message only
        assert mock_canvas.create_text.call_count == 1


# ===== Text Truncation Tests =====

class TestTextTruncation:
    """Tests for text truncation and tooltips."""

    def test_truncate_long_message(self, commit_drawer, mock_callbacks, mock_branch_flag_drawer, sample_column_widths, mock_canvas):
        """Test that long messages are truncated."""
        # Mock truncate callback to return truncated text
        mock_callbacks['truncate_text'].side_effect = lambda c, f, t, w: t[:10] + '...' if len(t) > 10 else t

        commit = Commit(
            hash='abc', message='This is a very long message that should be truncated',
            short_message='This is a very long message that should be truncated',
            author='User', author_short='User', author_email='email@test.com',
            date=datetime(2025, 1, 1), date_relative='1 day ago', date_short='2025-01-01',
            parents=[], branch='main', branch_color='#3366cc',
            x=50, y=50, description='', description_short='', tags=[],
            is_remote=False, is_branch_head=False, branch_head_type=None, branch_availability='local_only'
        )

        commit_drawer.draw_commits(
            [commit], sample_column_widths,
            mock_callbacks['show_tooltip'],
            mock_callbacks['hide_tooltip'],
            mock_callbacks['truncate_text'],
            100,
            mock_callbacks['make_color_pale'],
            mock_branch_flag_drawer,
            mock_callbacks['draw_flag_connection']
        )

        # Should have called truncate callback
        assert mock_callbacks['truncate_text'].called

    def test_tooltip_for_truncated_message(self, commit_drawer, mock_callbacks, mock_branch_flag_drawer, sample_column_widths, mock_canvas):
        """Test that tooltip is added for truncated message."""
        # Mock truncate to return truncated text
        mock_callbacks['truncate_text'].side_effect = lambda c, f, t, w: 'Short...'

        commit = Commit(
            hash='abc', message='Very long message',
            short_message='Very long message',
            author='User', author_short='User', author_email='email@test.com',
            date=datetime(2025, 1, 1), date_relative='1 day ago', date_short='2025-01-01',
            parents=[], branch='main', branch_color='#3366cc',
            x=50, y=50, description='', description_short='', tags=[],
            is_remote=False, is_branch_head=False, branch_head_type=None, branch_availability='local_only'
        )

        commit_drawer.draw_commits(
            [commit], sample_column_widths,
            mock_callbacks['show_tooltip'],
            mock_callbacks['hide_tooltip'],
            mock_callbacks['truncate_text'],
            100,
            mock_callbacks['make_color_pale'],
            mock_branch_flag_drawer,
            mock_callbacks['draw_flag_connection']
        )

        # Should bind tooltip events
        assert mock_canvas.tag_bind.called


# ===== Branch Flags Tests =====

class TestBranchFlags:
    """Tests for branch flag drawing."""

    def test_draw_branch_head_flag(self, commit_drawer, mock_callbacks, mock_branch_flag_drawer, sample_column_widths):
        """Test drawing branch flag for branch head commit."""
        commit = Commit(
            hash='abc', message='Test', short_message='Test',
            author='User', author_short='User', author_email='email@test.com',
            date=datetime(2025, 1, 1), date_relative='1 day ago', date_short='2025-01-01',
            parents=[], branch='main', branch_color='#3366cc',
            x=50, y=50, description='', description_short='', tags=[],
            is_remote=False, is_branch_head=True, branch_head_type='local', branch_availability='local_only'
        )

        commit_drawer.draw_commits(
            [commit], sample_column_widths,
            mock_callbacks['show_tooltip'],
            mock_callbacks['hide_tooltip'],
            mock_callbacks['truncate_text'],
            100,
            mock_callbacks['make_color_pale'],
            mock_branch_flag_drawer,
            mock_callbacks['draw_flag_connection']
        )

        # Should draw branch flag
        mock_branch_flag_drawer.draw_branch_flag.assert_called_once()

    def test_no_flag_for_merge_branch(self, commit_drawer, mock_callbacks, mock_branch_flag_drawer, sample_column_widths):
        """Test that merge branches don't get flags."""
        commit = Commit(
            hash='abc', message='Test', short_message='Test',
            author='User', author_short='User', author_email='email@test.com',
            date=datetime(2025, 1, 1), date_relative='1 day ago', date_short='2025-01-01',
            parents=[], branch='merge-feature', branch_color='#3366cc',
            x=50, y=50, description='', description_short='', tags=[],
            is_remote=False, is_branch_head=True, branch_head_type='local', branch_availability='local_only'
        )

        commit_drawer.draw_commits(
            [commit], sample_column_widths,
            mock_callbacks['show_tooltip'],
            mock_callbacks['hide_tooltip'],
            mock_callbacks['truncate_text'],
            100,
            mock_callbacks['make_color_pale'],
            mock_branch_flag_drawer,
            mock_callbacks['draw_flag_connection']
        )

        # Should NOT draw branch flag for merge branches
        mock_branch_flag_drawer.draw_branch_flag.assert_not_called()

    def test_draw_flag_connection(self, commit_drawer, mock_callbacks, mock_branch_flag_drawer, sample_column_widths):
        """Test drawing connection line to branch flag."""
        commit = Commit(
            hash='abc', message='Test', short_message='Test',
            author='User', author_short='User', author_email='email@test.com',
            date=datetime(2025, 1, 1), date_relative='1 day ago', date_short='2025-01-01',
            parents=[], branch='main', branch_color='#3366cc',
            x=50, y=50, description='', description_short='', tags=[],
            is_remote=False, is_branch_head=True, branch_head_type='local', branch_availability='local_only'
        )

        commit_drawer.draw_commits(
            [commit], sample_column_widths,
            mock_callbacks['show_tooltip'],
            mock_callbacks['hide_tooltip'],
            mock_callbacks['truncate_text'],
            100,
            mock_callbacks['make_color_pale'],
            mock_branch_flag_drawer,
            mock_callbacks['draw_flag_connection']
        )

        # Should draw flag connection
        mock_callbacks['draw_flag_connection'].assert_called_once()


# ===== Dominant Author Tests =====

class TestDominantAuthor:
    """Tests for dominant author detection and tooltip handling."""

    def test_detect_dominant_author(self, commit_drawer, mock_callbacks, mock_branch_flag_drawer, sample_column_widths, mock_canvas):
        """Test that dominant author (>80%) is detected."""
        # Create 10 commits, 9 by same author
        commits = []
        for i in range(9):
            commit = Commit(
                hash=f'abc{i}', message=f'Commit {i}', short_message=f'Commit {i}',
                author='Dominant Author', author_short='Dominant Author', author_email='dominant@test.com',
                date=datetime(2025, 1, i+1), date_relative=f'{i+1} days ago', date_short=f'2025-01-0{i+1}',
                parents=[], branch='main', branch_color='#3366cc',
                x=50, y=50 + i*60, description='', description_short='', tags=[],
                is_remote=False, is_branch_head=False, branch_head_type=None, branch_availability='local_only'
            )
            commits.append(commit)

        # Add 1 commit by different author
        commit = Commit(
            hash='xyz', message='Other commit', short_message='Other commit',
            author='Other Author', author_short='Other Author', author_email='other@test.com',
            date=datetime(2025, 1, 10), date_relative='10 days ago', date_short='2025-01-10',
            parents=[], branch='main', branch_color='#3366cc',
            x=50, y=590, description='', description_short='', tags=[],
            is_remote=False, is_branch_head=False, branch_head_type=None, branch_availability='local_only'
        )
        commits.append(commit)

        commit_drawer.draw_commits(
            commits, sample_column_widths,
            mock_callbacks['show_tooltip'],
            mock_callbacks['hide_tooltip'],
            mock_callbacks['truncate_text'],
            100,
            mock_callbacks['make_color_pale'],
            mock_branch_flag_drawer,
            mock_callbacks['draw_flag_connection']
        )

        # Should have bound tooltip only for non-dominant author (1 commit)
        # Check tag_bind calls for node tooltips
        node_tooltip_calls = [c for c in mock_canvas.tag_bind.call_args_list if 'node_' in str(c[0][0])]
        assert len(node_tooltip_calls) >= 2  # Enter and Leave for the 1 non-dominant commit


# ===== Circle Polygon Tests =====

class TestCirclePolygon:
    """Tests for circle polygon helper method."""

    def test_create_circle_polygon_returns_points(self, commit_drawer):
        """Test that _create_circle_polygon returns list of points."""
        points = commit_drawer._create_circle_polygon(100, 100, 10)

        assert isinstance(points, list)
        assert len(points) > 0
        assert len(points) % 2 == 0  # Even number (x, y pairs)

    def test_create_circle_polygon_default_points(self, commit_drawer):
        """Test default number of points (20 = 40 coordinates)."""
        points = commit_drawer._create_circle_polygon(100, 100, 10)

        # Default is 20 points = 40 coordinates
        assert len(points) == 40

    def test_create_circle_polygon_custom_points(self, commit_drawer):
        """Test custom number of points."""
        points = commit_drawer._create_circle_polygon(100, 100, 10, num_points=8)

        # 8 points = 16 coordinates
        assert len(points) == 16

    def test_create_circle_polygon_forms_circle(self, commit_drawer):
        """Test that points form approximate circle."""
        x_center, y_center, radius = 100, 100, 10
        points = commit_drawer._create_circle_polygon(x_center, y_center, radius)

        # Check that all points are approximately at radius distance from center
        for i in range(0, len(points), 2):
            px, py = points[i], points[i+1]
            dist = math.sqrt((px - x_center)**2 + (py - y_center)**2)
            # Should be very close to radius (within floating point precision)
            assert abs(dist - radius) < 0.01


# ===== Integration Tests =====

class TestCommitDrawerIntegration:
    """Integration tests for CommitDrawer workflow."""

    def test_full_commit_drawing_workflow(self, commit_drawer, sample_commits, mock_callbacks, mock_branch_flag_drawer, sample_column_widths, mock_canvas):
        """Test complete workflow: create drawer → draw commits → verify canvas calls."""
        commit_drawer.draw_commits(
            sample_commits, sample_column_widths,
            mock_callbacks['show_tooltip'],
            mock_callbacks['hide_tooltip'],
            mock_callbacks['truncate_text'],
            100,
            mock_callbacks['make_color_pale'],
            mock_branch_flag_drawer,
            mock_callbacks['draw_flag_connection']
        )

        # Should have drawn nodes
        assert mock_canvas.create_oval.called or mock_canvas.create_polygon.called
        # Should have drawn text
        assert mock_canvas.create_text.called

    def test_mixed_commit_types(self, commit_drawer, mock_callbacks, mock_branch_flag_drawer, sample_column_widths, mock_canvas):
        """Test drawing mixed commit types (normal, remote, uncommitted)."""
        commits = []

        # Normal commit
        commits.append(Commit(
            hash='abc1', message='Normal', short_message='Normal',
            author='User', author_short='User', author_email='email@test.com',
            date=datetime(2025, 1, 1), date_relative='1 day ago', date_short='2025-01-01',
            parents=[], branch='main', branch_color='#3366cc',
            x=50, y=50, description='', description_short='', tags=[],
            is_remote=False, is_branch_head=False, branch_head_type=None, branch_availability='local_only'
        ))

        # Remote commit
        remote_commit = Commit(
            hash='abc2', message='Remote', short_message='Remote',
            author='User', author_short='User', author_email='email@test.com',
            date=datetime(2025, 1, 2), date_relative='2 days ago', date_short='2025-01-02',
            parents=[], branch='origin/main', branch_color='#3366cc',
            x=50, y=110, description='', description_short='', tags=[],
            is_remote=True, is_branch_head=False, branch_head_type=None, branch_availability='remote_only'
        )
        commits.append(remote_commit)

        # Uncommitted commit
        wip_commit = Commit(
            hash='wip', message='WIP', short_message='WIP',
            author='User', author_short='User', author_email='email@test.com',
            date=datetime(2025, 1, 3), date_relative='3 days ago', date_short='2025-01-03',
            parents=[], branch='main', branch_color='#3366cc',
            x=50, y=170, description='', description_short='', tags=[],
            is_remote=False, is_branch_head=False, branch_head_type=None, branch_availability='local_only'
        )
        wip_commit.is_uncommitted = True
        commits.append(wip_commit)

        commit_drawer.draw_commits(
            commits, sample_column_widths,
            mock_callbacks['show_tooltip'],
            mock_callbacks['hide_tooltip'],
            mock_callbacks['truncate_text'],
            100,
            mock_callbacks['make_color_pale'],
            mock_branch_flag_drawer,
            mock_callbacks['draw_flag_connection']
        )

        # Should draw 2 ovals (normal + remote) and 1 polygon (uncommitted)
        assert mock_canvas.create_oval.call_count == 2
        assert mock_canvas.create_polygon.call_count == 1
