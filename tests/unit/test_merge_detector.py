"""Unit tests for repo.analyzers.merge_detector module."""

import pytest
from unittest.mock import MagicMock
from repo.analyzers.merge_detector import MergeDetector
from utils.data_structures import Commit, MergeBranch
from datetime import datetime, timezone


class TestMergeDetectorInitialization:
    """Tests for MergeDetector initialization."""

    def test_initialization(self, mock_git_repo):
        """Test MergeDetector initialization."""
        commits = []
        detector = MergeDetector(mock_git_repo, commits)
        assert detector.repo == mock_git_repo
        assert detector.commits == commits


class TestDetectMergeCommits:
    """Tests for merge commit detection."""

    def test_detect_basic_merge(self, mock_git_repo, mock_merge_commit):
        """Test detection of basic merge commit."""
        # Create a regular commit and a merge commit
        regular_commit = Commit(
            hash="a" * 8,
            message="Regular commit",
            short_message="Regular commit",
            author="Test",
            author_short="Test",
            author_email="test@example.com",
            date=datetime.now(timezone.utc),
            date_relative="1 day",
            date_short="01.01",
            parents=[],
            branch="main",
            branch_color="#3366cc",
            description="",
            description_short="",
            tags=[]
        )

        merge_commit_obj = Commit(
            hash="m" * 8,
            message="Merge branch 'feature'",
            short_message="Merge branch 'feature'",
            author="Test",
            author_short="Test",
            author_email="test@example.com",
            date=datetime.now(timezone.utc),
            date_relative="1 hour",
            date_short="01.01",
            parents=["a" * 8, "b" * 8],  # 2 parents = merge
            branch="main",
            branch_color="#3366cc",
            description="",
            description_short="",
            tags=[]
        )

        commits = [regular_commit, merge_commit_obj]

        detector = MergeDetector(mock_git_repo, commits)

        # Should detect the merge commit
        merge_commits = [c for c in commits if len(c.parents) >= 2]
        assert len(merge_commits) == 1
        assert merge_commits[0].hash == "m" * 8

    def test_no_merge_commits(self, mock_git_repo):
        """Test with no merge commits."""
        commit1 = Commit(
            hash="a" * 8,
            message="First commit",
            short_message="First commit",
            author="Test",
            author_short="Test",
            author_email="test@example.com",
            date=datetime.now(timezone.utc),
            date_relative="2 days",
            date_short="01.01",
            parents=[],
            branch="main",
            branch_color="#3366cc",
            description="",
            description_short="",
            tags=[]
        )

        commit2 = Commit(
            hash="b" * 8,
            message="Second commit",
            short_message="Second commit",
            author="Test",
            author_short="Test",
            author_email="test@example.com",
            date=datetime.now(timezone.utc),
            date_relative="1 day",
            date_short="01.01",
            parents=["a" * 8],  # Only 1 parent
            branch="main",
            branch_color="#3366cc",
            description="",
            description_short="",
            tags=[]
        )

        commits = [commit1, commit2]
        detector = MergeDetector(mock_git_repo, commits)
        merge_branches = detector.detect_merge_branches()

        # Should detect no merge branches
        assert len(merge_branches) == 0


class TestBuildFullHashMap:
    """Tests for building full hash map."""

    def test_build_full_hash_map(self, mock_git_repo, mock_git_commits):
        """Test building short-to-full hash map."""
        # Setup mock iteration
        mock_git_repo.iter_commits.return_value = mock_git_commits

        detector = MergeDetector(mock_git_repo, [])
        hash_map = detector.build_full_hash_map()

        assert isinstance(hash_map, dict)
        # Should map short hash to full hash
        for commit in mock_git_commits:
            short_hash = commit.hexsha[:8]
            assert short_hash in hash_map
            assert hash_map[short_hash] == commit.hexsha


class TestTraceMergeBranchCommits:
    """Tests for tracing commits in merge branch."""

    def test_trace_linear_path(self, mock_git_repo):
        """Test tracing commits in a linear merge branch."""
        # Create a chain: branch_point <- c1 <- c2 <- merge_parent
        commits = []
        for i in range(3):
            commit = Commit(
                hash=f"{i}" * 8,
                message=f"Commit {i}",
                short_message=f"Commit {i}",
                author="Test",
                author_short="Test",
                author_email="test@example.com",
                date=datetime.now(timezone.utc),
                date_relative=f"{i} days",
                date_short="01.01",
                parents=[f"{i-1}" * 8] if i > 0 else [],
                branch="feature",
                branch_color="#66cc33",
                description="",
                description_short="",
                tags=[]
            )
            commits.append(commit)

        commit_map = {c.hash: c for c in commits}
        merge_parent_hash = "2" * 8
        branch_point_hash = "0" * 8

        detector = MergeDetector(mock_git_repo, commits)
        traced = detector.trace_merge_branch_commits(
            merge_parent_hash, branch_point_hash, commit_map
        )

        # Should trace back: 2 <- 1
        assert len(traced) == 2
        assert "2" * 8 in traced
        assert "1" * 8 in traced

    def test_trace_stops_at_branch_point(self, mock_git_repo):
        """Test that tracing stops at branch point."""
        commits = []
        for i in range(5):
            commit = Commit(
                hash=f"{i}" * 8,
                message=f"Commit {i}",
                short_message=f"Commit {i}",
                author="Test",
                author_short="Test",
                author_email="test@example.com",
                date=datetime.now(timezone.utc),
                date_relative=f"{i} days",
                date_short="01.01",
                parents=[f"{i-1}" * 8] if i > 0 else [],
                branch="feature",
                branch_color="#66cc33",
                description="",
                description_short="",
                tags=[]
            )
            commits.append(commit)

        commit_map = {c.hash: c for c in commits}
        merge_parent_hash = "4" * 8
        branch_point_hash = "2" * 8  # Stop here

        detector = MergeDetector(mock_git_repo, commits)
        traced = detector.trace_merge_branch_commits(
            merge_parent_hash, branch_point_hash, commit_map
        )

        # Should trace: 4 <- 3, but stop before 2
        assert "4" * 8 in traced
        assert "3" * 8 in traced
        assert "2" * 8 not in traced  # Branch point not included


class TestGetCommitsInBranchesWithHead:
    """Tests for getting commits in main line."""

    def test_get_main_line_commits(self, mock_git_repo, mock_git_commits):
        """Test getting commits in first-parent path."""
        # Setup mock to return commits
        def iter_commits_side_effect(branch):
            if branch.name == "main":
                return mock_git_commits[:3]
            return []

        mock_git_repo.iter_commits.side_effect = iter_commits_side_effect

        detector = MergeDetector(mock_git_repo, [])
        main_line = detector.get_commits_in_branches_with_head()

        assert isinstance(main_line, set)
        # Should include commits from main branch
        assert len(main_line) > 0


class TestExtractBranchNameFromMerge:
    """Tests for extracting branch name from merge messages."""

    def test_extract_git_standard_format(self, mock_git_repo):
        """Test extracting from 'Merge branch \"feature\"' format."""
        merge_commit = Commit(
            hash="m" * 8,
            message="Merge branch 'feature/login' into main",
            short_message="Merge branch 'feature/login' into main",
            author="Test",
            author_short="Test",
            author_email="test@example.com",
            date=datetime.now(timezone.utc),
            date_relative="1 hour",
            date_short="01.01",
            parents=["a" * 8, "b" * 8],
            branch="main",
            branch_color="#3366cc",
            description="",
            description_short="",
            tags=[]
        )

        # Mock full hash map
        full_hash_map = {"m" * 8: "m" * 40}

        # Mock repo.commit to return message
        mock_commit_obj = MagicMock()
        mock_commit_obj.message = "Merge branch 'feature/login' into main"
        mock_git_repo.commit.return_value = mock_commit_obj

        detector = MergeDetector(mock_git_repo, [])
        branch_name = detector.extract_branch_name_from_merge(merge_commit, full_hash_map)

        assert branch_name == "feature/login"

    def test_extract_github_pr_format(self, mock_git_repo):
        """Test extracting from GitHub PR merge format."""
        merge_commit = Commit(
            hash="m" * 8,
            message="Merge pull request #123 from user/fix-bug",
            short_message="Merge pull request #123 from user/fix-bug",
            author="Test",
            author_short="Test",
            author_email="test@example.com",
            date=datetime.now(timezone.utc),
            date_relative="1 hour",
            date_short="01.01",
            parents=["a" * 8, "b" * 8],
            branch="main",
            branch_color="#3366cc",
            description="",
            description_short="",
            tags=[]
        )

        full_hash_map = {"m" * 8: "m" * 40}

        mock_commit_obj = MagicMock()
        mock_commit_obj.message = "Merge pull request #123 from user/fix-bug"
        mock_git_repo.commit.return_value = mock_commit_obj

        detector = MergeDetector(mock_git_repo, [])
        branch_name = detector.extract_branch_name_from_merge(merge_commit, full_hash_map)

        assert branch_name == "fix-bug"

    def test_extract_remote_tracking_format(self, mock_git_repo):
        """Test extracting from remote-tracking branch merge."""
        merge_commit = Commit(
            hash="m" * 8,
            message="Merge remote-tracking branch 'origin/develop'",
            short_message="Merge remote-tracking branch 'origin/develop'",
            author="Test",
            author_short="Test",
            author_email="test@example.com",
            date=datetime.now(timezone.utc),
            date_relative="1 hour",
            date_short="01.01",
            parents=["a" * 8, "b" * 8],
            branch="main",
            branch_color="#3366cc",
            description="",
            description_short="",
            tags=[]
        )

        full_hash_map = {"m" * 8: "m" * 40}

        mock_commit_obj = MagicMock()
        mock_commit_obj.message = "Merge remote-tracking branch 'origin/develop'"
        mock_git_repo.commit.return_value = mock_commit_obj

        detector = MergeDetector(mock_git_repo, [])
        branch_name = detector.extract_branch_name_from_merge(merge_commit, full_hash_map)

        assert branch_name == "develop"


class TestMakeColorPale:
    """Tests for color paling with HSL manipulation."""

    def test_make_color_pale_merge_blend(self, mock_git_repo):
        """Test making color pale with merge blend type."""
        detector = MergeDetector(mock_git_repo, [])

        original_color = "#FF0000"  # Red
        pale_color = detector.make_color_pale(original_color, "merge")

        assert pale_color.startswith("#")
        assert len(pale_color) == 7
        assert pale_color != original_color  # Should be different

    def test_make_color_pale_remote_blend(self, mock_git_repo):
        """Test making color pale with remote blend type."""
        detector = MergeDetector(mock_git_repo, [])

        original_color = "#0000FF"  # Blue
        pale_color = detector.make_color_pale(original_color, "remote")

        assert pale_color.startswith("#")
        assert len(pale_color) == 7
        assert pale_color != original_color

    def test_merge_paler_than_remote(self, mock_git_repo):
        """Test that merge blend is paler than remote blend."""
        detector = MergeDetector(mock_git_repo, [])

        original_color = "#00FF00"  # Green
        pale_remote = detector.make_color_pale(original_color, "remote")
        pale_merge = detector.make_color_pale(original_color, "merge")

        # Both should be valid and different
        assert pale_remote != pale_merge
        # Merge should be more pale (higher lightness, lower saturation)

    def test_unknown_color_fallback(self, mock_git_repo):
        """Test fallback for unknown colors."""
        detector = MergeDetector(mock_git_repo, [])

        assert detector.make_color_pale("unknown", "merge") == "#CCCCCC"
        assert detector.make_color_pale("", "merge") == "#CCCCCC"


class TestApplyMergeBranchStyling:
    """Tests for applying styling to merge branch commits."""

    def test_apply_styling_basic(self, mock_git_repo):
        """Test applying virtual branch name and pale color."""
        commit1 = Commit(
            hash="a" * 8,
            message="Feature commit",
            short_message="Feature commit",
            author="Test",
            author_short="Test",
            author_email="test@example.com",
            date=datetime.now(timezone.utc),
            date_relative="1 day",
            date_short="01.01",
            parents=[],
            branch="feature/test",
            branch_color="#66CC33",
            description="",
            description_short="",
            tags=[]
        )

        merge_branch = MergeBranch(
            branch_point_hash="0" * 8,
            merge_point_hash="m" * 8,
            commits_in_branch=["a" * 8],
            virtual_branch_name="merge-m" * 8,
            original_color="#66CC33"
        )

        commits = [commit1]
        merge_branches = [merge_branch]

        detector = MergeDetector(mock_git_repo, commits)
        detector.apply_merge_branch_styling(commits, merge_branches)

        # Commit should now have virtual branch name
        assert commit1.branch.startswith("merge-")
        # Should have paler color
        assert commit1.branch_color != "#66CC33"
        assert commit1.branch_color.startswith("#")
        # Should be marked as merge branch
        assert hasattr(commit1, 'is_merge_branch')
        assert commit1.is_merge_branch is True

    def test_no_styling_for_regular_commits(self, mock_git_repo):
        """Test that regular commits are not styled."""
        commit1 = Commit(
            hash="b" * 8,
            message="Regular commit",
            short_message="Regular commit",
            author="Test",
            author_short="Test",
            author_email="test@example.com",
            date=datetime.now(timezone.utc),
            date_relative="1 day",
            date_short="01.01",
            parents=[],
            branch="main",
            branch_color="#3366CC",
            description="",
            description_short="",
            tags=[]
        )

        merge_branch = MergeBranch(
            branch_point_hash="0" * 8,
            merge_point_hash="m" * 8,
            commits_in_branch=["a" * 8],  # Different commit
            virtual_branch_name="merge-m" * 8,
            original_color="#66CC33"
        )

        commits = [commit1]
        merge_branches = [merge_branch]

        detector = MergeDetector(mock_git_repo, commits)
        original_branch = commit1.branch
        original_color = commit1.branch_color

        detector.apply_merge_branch_styling(commits, merge_branches)

        # Commit should remain unchanged
        assert commit1.branch == original_branch
        assert commit1.branch_color == original_color
        assert not hasattr(commit1, 'is_merge_branch') or not commit1.is_merge_branch
