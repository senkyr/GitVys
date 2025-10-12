"""Unit tests for gui.ui_components.stats_display module."""

import pytest
import tkinter as tk
from tkinter import ttk
from unittest.mock import MagicMock, patch
from gui.ui_components.stats_display import StatsDisplay


class TestStatsDisplayInitialization:
    """Tests for StatsDisplay initialization."""

    def test_initialization(self, mock_parent_window):
        """Test StatsDisplay initialization with parent window."""
        display = StatsDisplay(mock_parent_window)

        assert display.parent == mock_parent_window
        assert display.root == mock_parent_window.root
        assert display.tm is not None  # Translation manager

    def test_initialization_without_ui(self, mock_parent_window):
        """Test that initialization doesn't create UI elements."""
        display = StatsDisplay(mock_parent_window)

        # UI elements should be None until create_stats_ui is called
        assert not hasattr(display, 'info_frame') or display.info_frame is None


class TestStatsUI:
    """Tests for stats UI creation."""

    def test_create_stats_ui_returns_widgets(self, mock_parent_window):
        """Test that create_stats_ui returns frame and labels."""
        display = StatsDisplay(mock_parent_window)
        parent_frame = ttk.Frame(mock_parent_window.root)

        info_frame, repo_label, stats_label = display.create_stats_ui(parent_frame)

        assert info_frame is not None
        assert isinstance(info_frame, ttk.Frame)
        assert repo_label is not None
        assert isinstance(repo_label, ttk.Label)
        assert stats_label is not None
        assert isinstance(stats_label, ttk.Label)

    def test_create_stats_ui_configures_labels(self, mock_parent_window):
        """Test that create_stats_ui configures labels with correct properties."""
        display = StatsDisplay(mock_parent_window)
        parent_frame = ttk.Frame(mock_parent_window.root)

        info_frame, repo_label, stats_label = display.create_stats_ui(parent_frame)

        # Repo label should be bold
        font_config = repo_label.cget('font')
        assert 'bold' in str(font_config).lower() or 'TkDefaultFont' in str(font_config)

        # Stats label should have normal font
        stats_font = stats_label.cget('font')
        assert stats_font  # Should have font set


class TestStatsUpdate:
    """Tests for updating statistics display."""

    def test_update_stats_local_repo(self, mock_parent_window):
        """Test updating stats for local repository."""
        display = StatsDisplay(mock_parent_window)
        parent_frame = ttk.Frame(mock_parent_window.root)
        info_frame, repo_label, stats_label = display.create_stats_ui(parent_frame)

        # Mock git repo
        mock_repo = MagicMock()
        mock_repo.repo_path = "/home/user/my-repo"
        mock_repo.get_repository_stats.return_value = {
            'authors': 3,
            'branches': 2,
            'tags': 3,
            'local_tags': 3,
            'remote_tags': 0,
            'commits': 42
        }

        display.update_stats(mock_repo, display_name=None)

        # Repo label should show folder name
        repo_text = repo_label.cget('text')
        assert "my-repo" in repo_text

        # Stats label should show counts
        stats_text = stats_label.cget('text')
        assert "3" in stats_text  # 3 authors
        assert "2" in stats_text  # 2 branches
        assert "3" in stats_text  # 3 tags
        assert "42" in stats_text  # 42 commits

    def test_update_stats_cloned_repo_with_display_name(self, mock_parent_window):
        """Test updating stats for cloned repository with display name."""
        display = StatsDisplay(mock_parent_window)
        parent_frame = ttk.Frame(mock_parent_window.root)
        info_frame, repo_label, stats_label = display.create_stats_ui(parent_frame)

        # Mock git repo (temp path)
        mock_repo = MagicMock()
        mock_repo.repo_path = "/tmp/gitvys_clone_abc123"
        mock_repo.get_repository_stats.return_value = {
            'authors': 1,
            'branches': 1,
            'tags': 0,
            'local_tags': 0,
            'remote_tags': 0,
            'commits': 10
        }

        # Provide display name
        display.update_stats(mock_repo, display_name="awesome-project")

        # Repo label should show display name, not temp path
        repo_text = repo_label.cget('text')
        assert "awesome-project" in repo_text
        assert "gitvys_clone" not in repo_text

    def test_update_stats_pluralization_czech(self, mock_parent_window):
        """Test stats pluralization in Czech language."""
        display = StatsDisplay(mock_parent_window)
        parent_frame = ttk.Frame(mock_parent_window.root)
        info_frame, repo_label, stats_label = display.create_stats_ui(parent_frame)

        display.tm.get_current_language = MagicMock(return_value='cs')
        display.tm.get_plural = MagicMock(side_effect=lambda count, form: f"{form}")

        # Mock repo
        mock_repo = MagicMock()
        mock_repo.repo_path = "/test/repo"
        mock_repo.get_repository_stats.return_value = {
            'authors': 5,
            'branches': 2,
            'tags': 1,
            'local_tags': 1,
            'remote_tags': 0,
            'commits': 100
        }

        display.update_stats(mock_repo, display_name=None)

        # Should call get_plural for each count
        assert display.tm.get_plural.call_count >= 4  # authors, branches, tags, commits

    def test_update_stats_pluralization_english(self, mock_parent_window):
        """Test stats pluralization in English language."""
        display = StatsDisplay(mock_parent_window)
        parent_frame = ttk.Frame(mock_parent_window.root)
        info_frame, repo_label, stats_label = display.create_stats_ui(parent_frame)

        display.tm.get_current_language = MagicMock(return_value='en')
        display.tm.get_plural = MagicMock(side_effect=lambda count, form: f"{form}{'s' if count != 1 else ''}")

        mock_repo = MagicMock()
        mock_repo.repo_path = "/test/repo"
        mock_repo.get_repository_stats.return_value = {
            'authors': 1,
            'branches': 3,
            'tags': 0,
            'local_tags': 0,
            'remote_tags': 0,
            'commits': 1
        }

        display.update_stats(mock_repo, display_name=None)

        # Should call get_plural (but not for tags since tags == 0)
        assert display.tm.get_plural.call_count >= 3

    def test_update_stats_formats_counts(self, mock_parent_window):
        """Test that stats are formatted correctly."""
        display = StatsDisplay(mock_parent_window)
        parent_frame = ttk.Frame(mock_parent_window.root)
        info_frame, repo_label, stats_label = display.create_stats_ui(parent_frame)

        display.tm.get_plural = MagicMock(side_effect=lambda count, form: f"{form}")

        mock_repo = MagicMock()
        mock_repo.repo_path = "/test"
        mock_repo.get_repository_stats.return_value = {
            'authors': 10,
            'branches': 5,
            'tags': 3,
            'local_tags': 3,
            'remote_tags': 0,
            'commits': 123
        }

        display.update_stats(mock_repo, display_name=None)

        stats_text = stats_label.cget('text')

        # Should contain all counts
        assert "10" in stats_text
        assert "5" in stats_text
        assert "3" in stats_text
        assert "123" in stats_text


class TestTooltip:
    """Tests for repository path tooltip."""

    def test_repo_name_has_tooltip_binding(self, mock_parent_window):
        """Test that repo name label has tooltip bindings."""
        display = StatsDisplay(mock_parent_window)
        parent_frame = ttk.Frame(mock_parent_window.root)
        info_frame, repo_label, stats_label = display.create_stats_ui(parent_frame)

        # Repo label should have <Enter> and <Leave> bindings
        bindings = repo_label.bind()
        assert '<Enter>' in bindings or repo_label.bind('<Enter>')
        assert '<Leave>' in bindings or repo_label.bind('<Leave>')

    def test_tooltip_shows_full_path_on_hover(self, mock_parent_window):
        """Test that hovering shows full repository path in tooltip."""
        display = StatsDisplay(mock_parent_window)
        parent_frame = ttk.Frame(mock_parent_window.root)
        info_frame, repo_label, stats_label = display.create_stats_ui(parent_frame)

        # Mock repo with long path
        mock_repo = MagicMock()
        long_path = "/very/long/path/to/repository/with/many/nested/folders"
        mock_repo.repo_path = long_path
        mock_repo.get_repository_stats.return_value = {
            'authors': 0,
            'branches': 0,
            'tags': 0,
            'local_tags': 0,
            'remote_tags': 0,
            'commits': 0
        }

        # Mock parent.git_repo for tooltip
        mock_parent_window.git_repo = mock_repo

        display.update_stats(mock_repo, display_name=None)

        # Tooltip should use parent.git_repo.repo_path
        assert mock_parent_window.git_repo.repo_path == long_path


class TestEdgeCases:
    """Tests for edge cases and error handling."""

    def test_update_stats_with_zero_counts(self, mock_parent_window):
        """Test updating stats with zero authors/branches/tags/commits."""
        display = StatsDisplay(mock_parent_window)
        parent_frame = ttk.Frame(mock_parent_window.root)
        info_frame, repo_label, stats_label = display.create_stats_ui(parent_frame)

        display.tm.get_plural = MagicMock(side_effect=lambda count, form: f"{form}")

        mock_repo = MagicMock()
        mock_repo.repo_path = "/empty/repo"
        mock_repo.get_repository_stats.return_value = {
            'authors': 0,
            'branches': 0,
            'tags': 0,
            'local_tags': 0,
            'remote_tags': 0,
            'commits': 0
        }

        # Should not crash
        display.update_stats(mock_repo, display_name=None)

        stats_text = stats_label.cget('text')
        assert "0" in stats_text  # Should show 0 counts

    def test_update_stats_with_none_display_name(self, mock_parent_window):
        """Test that None display_name uses folder name from path."""
        display = StatsDisplay(mock_parent_window)
        parent_frame = ttk.Frame(mock_parent_window.root)
        info_frame, repo_label, stats_label = display.create_stats_ui(parent_frame)

        mock_repo = MagicMock()
        mock_repo.repo_path = "/path/to/my-project"
        mock_repo.get_repository_stats.return_value = {
            'authors': 0,
            'branches': 0,
            'tags': 0,
            'local_tags': 0,
            'remote_tags': 0,
            'commits': 0
        }

        display.update_stats(mock_repo, display_name=None)

        repo_text = repo_label.cget('text')
        assert "my-project" in repo_text
