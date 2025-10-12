"""Unit tests for repo.parsers.branch_analyzer module."""

import pytest
import sys
from pathlib import Path
from unittest.mock import MagicMock, patch

# Import mock helpers from conftest
sys.path.insert(0, str(Path(__file__).parent.parent))
from conftest import MockHeadsDict, MockRefsDict

from repo.parsers.branch_analyzer import BranchAnalyzer


class TestBranchAnalyzerInitialization:
    """Tests for BranchAnalyzer initialization."""

    def test_initialization(self, mock_git_repo):
        """Test BranchAnalyzer initialization with GitPython Repo."""
        analyzer = BranchAnalyzer(mock_git_repo)
        assert analyzer.repo is not None
        assert analyzer.repo == mock_git_repo


class TestBuildCommitBranchMap:
    """Tests for building commit-to-branch mappings."""

    def test_build_basic_map(self, mock_git_repo, mock_git_commits):
        """Test building commit-branch map for local branches."""
        # Setup mock to return commits for main branch
        mock_git_repo.iter_commits.return_value = mock_git_commits[:3]

        analyzer = BranchAnalyzer(mock_git_repo)
        commit_map = analyzer.build_commit_branch_map()

        # Should map all commits to their branches
        assert len(commit_map) > 0
        for commit in mock_git_commits[:3]:
            assert commit.hexsha in commit_map

    def test_main_branch_priority(self, mock_git_repo, mock_git_commits):
        """Test that main/master branches have priority."""
        # Setup two branches - main and feature
        def iter_commits_side_effect(branch):
            if branch.name == "main":
                return [mock_git_commits[0]]
            elif branch.name == "feature/test":
                return [mock_git_commits[0]]  # Same commit in both branches
            return []

        mock_git_repo.iter_commits.side_effect = iter_commits_side_effect

        analyzer = BranchAnalyzer(mock_git_repo)
        commit_map = analyzer.build_commit_branch_map()

        # The commit should be mapped to "main" (higher priority)
        assert commit_map[mock_git_commits[0].hexsha] == "main"

    def test_other_branches(self, mock_git_repo, mock_git_commits):
        """Test mapping non-main branches."""
        # Setup feature branch only
        feature_head = MagicMock()
        feature_head.name = "feature/test"

        mock_git_repo.heads = MockHeadsDict([feature_head])
        mock_git_repo.iter_commits.return_value = [mock_git_commits[0]]

        analyzer = BranchAnalyzer(mock_git_repo)
        commit_map = analyzer.build_commit_branch_map()

        assert commit_map[mock_git_commits[0].hexsha] == "feature/test"


class TestBuildCommitBranchMapWithRemote:
    """Tests for building commit-branch maps with remote branches."""

    def test_build_with_remote_maps(self, mock_git_repo, mock_git_commits):
        """Test building separate local and remote maps."""
        # Setup local branches
        mock_git_repo.iter_commits.side_effect = lambda branch: (
            [mock_git_commits[0]] if branch.name == "main" else []
        )

        analyzer = BranchAnalyzer(mock_git_repo)
        local_map, remote_map = analyzer.build_commit_branch_map_with_remote()

        # Should return tuple of two maps
        assert isinstance(local_map, dict)
        assert isinstance(remote_map, dict)

        # Local map should have main commit
        assert mock_git_commits[0].hexsha in local_map
        assert local_map[mock_git_commits[0].hexsha] == "main"

    def test_remote_only_commits(self, mock_git_repo, mock_git_commits):
        """Test commits that only exist in remote."""
        # Setup: local has commit 0, remote has commits 1 and 2
        def iter_commits_side_effect(branch_or_ref):
            if hasattr(branch_or_ref, 'name'):
                if branch_or_ref.name == "main":
                    return [mock_git_commits[0]]
                elif branch_or_ref.name == "origin/feature/test":
                    return [mock_git_commits[1], mock_git_commits[2]]
            return []

        mock_git_repo.iter_commits.side_effect = iter_commits_side_effect

        analyzer = BranchAnalyzer(mock_git_repo)
        local_map, remote_map = analyzer.build_commit_branch_map_with_remote()

        # Commit 0 should be in local only
        assert mock_git_commits[0].hexsha in local_map
        assert mock_git_commits[0].hexsha not in remote_map

        # Commits 1 and 2 should be in remote only
        assert mock_git_commits[1].hexsha in remote_map
        assert mock_git_commits[2].hexsha in remote_map
        assert mock_git_commits[1].hexsha not in local_map


class TestBuildBranchAvailabilityMap:
    """Tests for branch availability detection."""

    def test_local_only_branch(self, mock_git_repo):
        """Test detection of local-only branches."""
        # Setup: main branch exists locally but not on remote
        mock_git_repo.remotes.origin.refs = MockRefsDict([])

        analyzer = BranchAnalyzer(mock_git_repo)
        availability = analyzer.build_branch_availability_map(include_remote=True)

        assert "main" in availability
        assert availability["main"] == "local_only"

    def test_remote_only_branch(self, mock_git_repo):
        """Test detection of remote-only branches."""
        # Setup: remote branch that doesn't exist locally
        mock_git_repo.heads = MockHeadsDict([])

        remote_ref = MagicMock()
        remote_ref.name = "origin/feature/remote-only"

        mock_git_repo.remotes.origin.refs = MockRefsDict([remote_ref])
        mock_git_repo.remote.return_value.refs = MockRefsDict([remote_ref])

        analyzer = BranchAnalyzer(mock_git_repo)
        availability = analyzer.build_branch_availability_map(include_remote=True)

        assert "feature/remote-only" in availability
        assert availability["feature/remote-only"] == "remote_only"

    def test_both_local_and_remote(self, mock_git_repo):
        """Test detection of branches that exist in both locations."""
        # Default mock_git_repo has main in both local and remote
        analyzer = BranchAnalyzer(mock_git_repo)
        availability = analyzer.build_branch_availability_map(include_remote=True)

        assert "main" in availability
        assert availability["main"] == "both"


class TestDetectBranchDivergence:
    """Tests for branch divergence detection."""

    def test_no_divergence_same_commit(self, mock_git_repo):
        """Test when local and remote point to same commit."""
        # Setup: both heads point to same commit
        same_commit = MagicMock()
        same_commit.hexsha = "a" * 40

        mock_git_repo.heads["main"].commit = same_commit
        mock_git_repo.remotes.origin.refs["main"].commit = same_commit

        analyzer = BranchAnalyzer(mock_git_repo)
        result = analyzer.detect_branch_divergence("main")

        assert result["diverged"] is False
        assert result["local_head"] == same_commit
        assert result["remote_head"] == same_commit

    def test_local_ahead(self, mock_git_repo):
        """Test when local is ahead of remote."""
        local_commit = MagicMock()
        local_commit.hexsha = "b" * 40

        merge_base_commit = MagicMock()
        merge_base_commit.hexsha = "a" * 40

        mock_git_repo.heads["main"].commit = local_commit
        mock_git_repo.remotes.origin.refs["main"].commit = merge_base_commit
        mock_git_repo.merge_base.return_value = [merge_base_commit]

        analyzer = BranchAnalyzer(mock_git_repo)
        result = analyzer.detect_branch_divergence("main")

        assert result["local_ahead"] is True
        assert result["remote_ahead"] is False
        assert result["diverged"] is False  # Only one side ahead

    def test_remote_ahead(self, mock_git_repo):
        """Test when remote is ahead of local."""
        merge_base_commit = MagicMock()
        merge_base_commit.hexsha = "a" * 40

        remote_commit = MagicMock()
        remote_commit.hexsha = "c" * 40

        mock_git_repo.heads["main"].commit = merge_base_commit
        mock_git_repo.remotes.origin.refs["main"].commit = remote_commit
        mock_git_repo.merge_base.return_value = [merge_base_commit]

        analyzer = BranchAnalyzer(mock_git_repo)
        result = analyzer.detect_branch_divergence("main")

        assert result["local_ahead"] is False
        assert result["remote_ahead"] is True
        assert result["diverged"] is False

    def test_true_divergence(self, mock_git_repo):
        """Test when branches have truly diverged (both ahead)."""
        local_commit = MagicMock()
        local_commit.hexsha = "b" * 40

        remote_commit = MagicMock()
        remote_commit.hexsha = "c" * 40

        merge_base_commit = MagicMock()
        merge_base_commit.hexsha = "a" * 40

        mock_git_repo.heads["main"].commit = local_commit
        mock_git_repo.remotes.origin.refs["main"].commit = remote_commit
        mock_git_repo.merge_base.return_value = [merge_base_commit]

        analyzer = BranchAnalyzer(mock_git_repo)
        result = analyzer.detect_branch_divergence("main")

        assert result["local_ahead"] is True
        assert result["remote_ahead"] is True
        assert result["diverged"] is True


class TestGetAllBranchNames:
    """Tests for getting all branch names."""

    def test_get_all_branches(self, mock_git_repo):
        """Test getting all local and remote branch names."""
        analyzer = BranchAnalyzer(mock_git_repo)
        all_branches = analyzer.get_all_branch_names()

        assert isinstance(all_branches, set)
        # Should include both local branches from mock
        assert "main" in all_branches
        assert "feature/test" in all_branches

    def test_deduplicate_branches(self, mock_git_repo):
        """Test that branches are deduplicated (local + remote with same name)."""
        # Default mock has main in both local and remote
        analyzer = BranchAnalyzer(mock_git_repo)
        all_branches = analyzer.get_all_branch_names()

        # Should only appear once even though it's in both locations
        branch_list = list(all_branches)
        assert branch_list.count("main") == 1
