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


# Mapování commit -> větev (build_commit_branch_map*) testuje nad skutečnými
# repozitáři tests/integration/test_real_repository.py::TestBranchAnalyzerOnRealRepo.
# Implementace volá `git rev-list --stdin`, což mock iter_commits nepokryje.


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
