"""Unit tests for repo.parsers.commit_parser module."""

import pytest
from datetime import datetime, timezone
from unittest.mock import MagicMock, patch
from repo.parsers.commit_parser import CommitParser
from utils.data_structures import Commit, Tag


class TestCommitParserInitialization:
    """Tests for CommitParser initialization."""

    def test_initialization(self, mock_git_repo):
        """Test CommitParser initialization with GitPython Repo."""
        parser = CommitParser(mock_git_repo)
        assert parser.repo is not None
        assert parser.repo == mock_git_repo


class TestParseCommits:
    """Tests for parsing commits from local branches."""

    def test_parse_commits_basic(self, mock_git_repo, mock_git_commits):
        """Test basic commit parsing from local branches."""
        # Setup mock iteration
        mock_git_repo.iter_commits.return_value = mock_git_commits[:3]

        parser = CommitParser(mock_git_repo)

        # Prepare input maps
        commit_to_branch = {commit.hexsha: "main" for commit in mock_git_commits[:3]}
        commit_to_tags = {}
        branch_availability = {"main": "local_only"}
        branch_colors = {}
        used_colors = set()

        # Parse commits
        commits = parser.parse_commits(
            commit_to_branch, commit_to_tags, branch_availability,
            branch_colors, used_colors
        )

        assert len(commits) == 3
        assert all(isinstance(c, Commit) for c in commits)
        assert commits[0].branch == "main"

    def test_parse_commits_with_tags(self, mock_git_repo, mock_git_commits):
        """Test parsing commits with tags."""
        mock_git_repo.iter_commits.return_value = mock_git_commits[:2]

        parser = CommitParser(mock_git_repo)

        # Prepare input with tags
        commit_to_branch = {commit.hexsha: "main" for commit in mock_git_commits[:2]}
        commit_to_tags = {
            mock_git_commits[0].hexsha: [Tag(name="v1.0.0", is_remote=False)]
        }
        branch_availability = {"main": "local_only"}
        branch_colors = {}
        used_colors = set()

        commits = parser.parse_commits(
            commit_to_branch, commit_to_tags, branch_availability,
            branch_colors, used_colors
        )

        assert len(commits[0].tags) == 1
        assert commits[0].tags[0].name == "v1.0.0"
        assert len(commits[1].tags) == 0

    def test_parse_commits_branch_colors(self, mock_git_repo, mock_git_commits):
        """Test branch color assignment."""
        mock_git_repo.iter_commits.return_value = mock_git_commits[:2]

        parser = CommitParser(mock_git_repo)

        commit_to_branch = {
            mock_git_commits[0].hexsha: "main",
            mock_git_commits[1].hexsha: "feature/test"
        }
        commit_to_tags = {}
        branch_availability = {"main": "local_only", "feature/test": "local_only"}
        branch_colors = {}
        used_colors = set()

        commits = parser.parse_commits(
            commit_to_branch, commit_to_tags, branch_availability,
            branch_colors, used_colors
        )

        # Should have assigned colors for both branches
        assert "main" in branch_colors
        assert "feature/test" in branch_colors
        assert branch_colors["main"] in used_colors
        assert branch_colors["feature/test"] in used_colors


class TestParseCommitsWithRemote:
    """Tests for parsing commits with remote branches."""

    def test_parse_with_remote_maps(self, mock_git_repo, mock_git_commits):
        """Test parsing with separate local and remote maps."""
        # Mock both local and remote branches
        mock_git_repo.iter_commits.return_value = mock_git_commits[:3]

        parser = CommitParser(mock_git_repo)

        local_commit_map = {mock_git_commits[0].hexsha: "main"}
        remote_commit_map = {
            mock_git_commits[1].hexsha: "origin/feature/test",
            mock_git_commits[2].hexsha: "origin/feature/test"
        }
        commit_to_tags = {}
        branch_availability = {
            "main": "local_only",
            "feature/test": "remote_only"
        }
        branch_divergences = {
            "main": {"diverged": False, "local_head": None, "remote_head": None},
            "feature/test": {"diverged": False, "local_head": None, "remote_head": None}
        }
        branch_colors = {}
        used_colors = set()

        commits = parser.parse_commits_with_remote(
            local_commit_map, remote_commit_map, commit_to_tags,
            branch_availability, branch_divergences, branch_colors, used_colors
        )

        assert len(commits) == 3
        # First commit is local
        assert commits[0].is_remote is False
        assert commits[0].branch == "main"
        # Second and third are remote
        assert commits[1].is_remote is True
        assert commits[2].is_remote is True

    def test_parse_with_branch_head_detection(self, mock_git_repo, mock_git_commits):
        """Test branch head detection (local/remote/both)."""
        mock_git_repo.iter_commits.return_value = [mock_git_commits[0]]

        parser = CommitParser(mock_git_repo)

        local_commit_map = {mock_git_commits[0].hexsha: "main"}
        remote_commit_map = {}
        commit_to_tags = {}
        branch_availability = {"main": "both"}

        # Mock branch head
        mock_local_head = MagicMock()
        mock_local_head.hexsha = mock_git_commits[0].hexsha
        mock_remote_head = MagicMock()
        mock_remote_head.hexsha = mock_git_commits[0].hexsha

        branch_divergences = {
            "main": {
                "diverged": False,
                "local_head": mock_local_head,
                "remote_head": mock_remote_head
            }
        }
        branch_colors = {}
        used_colors = set()

        commits = parser.parse_commits_with_remote(
            local_commit_map, remote_commit_map, commit_to_tags,
            branch_availability, branch_divergences, branch_colors, used_colors
        )

        assert len(commits) == 1
        assert commits[0].is_branch_head is True
        assert commits[0].branch_head_type == "both"


class TestTextTruncation:
    """Tests for text truncation methods."""

    def test_truncate_message(self, mock_git_repo):
        """Test message truncation."""
        parser = CommitParser(mock_git_repo)

        short_msg = "Short message"
        assert parser.truncate_message(short_msg, 50) == short_msg

        long_msg = "A" * 100
        truncated = parser.truncate_message(long_msg, 50)
        assert len(truncated) <= 50
        assert truncated.endswith("...")

    def test_truncate_name(self, mock_git_repo):
        """Test author name truncation."""
        parser = CommitParser(mock_git_repo)

        short_name = "John Doe"
        assert parser.truncate_name(short_name) == short_name

        long_name = "John Jacob Jingleheimer Schmidt"
        truncated = parser.truncate_name(long_name)
        # Should be "J. Schmidt" format
        assert truncated.startswith("J.")
        assert "Schmidt" in truncated

    def test_truncate_description(self, mock_git_repo):
        """Test description truncation."""
        parser = CommitParser(mock_git_repo)

        # Empty description
        assert parser.truncate_description("") == ""

        # Single line, short
        short_desc = "Fix bug"
        assert parser.truncate_description(short_desc) == short_desc

        # Multiple lines
        multi_line = "First line\nSecond line\nThird line"
        truncated = parser.truncate_description(multi_line, 50)
        assert truncated.endswith("...")
        assert "First line" in truncated
        assert "Second line" not in truncated

        # Single line, too long
        long_line = "A" * 200
        truncated = parser.truncate_description(long_line, 50)
        assert len(truncated) <= 53  # 50 + "..."
        assert truncated.endswith("...")


class TestDateFormatting:
    """Tests for date formatting methods."""

    def test_get_relative_date_recent(self, mock_git_repo):
        """Test relative date formatting for recent commits."""
        parser = CommitParser(mock_git_repo)

        # Test with a date 2 days ago
        now = datetime.now(timezone.utc)
        from datetime import timedelta
        two_days_ago = now - timedelta(days=2)

        relative = parser.get_relative_date(two_days_ago)
        assert "2 dní" in relative or "2 den" in relative

    def test_get_relative_date_weeks(self, mock_git_repo):
        """Test relative date for weeks ago."""
        parser = CommitParser(mock_git_repo)

        from datetime import timedelta
        now = datetime.now(timezone.utc)
        two_weeks_ago = now - timedelta(weeks=2)

        relative = parser.get_relative_date(two_weeks_ago)
        assert "týdn" in relative

    def test_get_short_date(self, mock_git_repo):
        """Test short date formatting."""
        parser = CommitParser(mock_git_repo)

        test_date = datetime(2025, 1, 15, 10, 30, 0)
        short_date = parser.get_short_date(test_date)
        assert short_date == "15.01"

    def test_get_full_date(self, mock_git_repo):
        """Test full date formatting."""
        parser = CommitParser(mock_git_repo)

        test_date = datetime(2025, 1, 15, 10, 30, 0)
        full_date = parser.get_full_date(test_date)
        assert full_date == "15.01.2025 @ 10:30"
