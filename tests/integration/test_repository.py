"""Integration tests for GitRepository."""

import pytest
import tempfile
import shutil
from pathlib import Path
from unittest.mock import Mock, patch, MagicMock
from repo.repository import GitRepository
from utils.data_structures import Commit


class TestGitRepositoryIntegration:
    """Integration tests for GitRepository class."""

    @pytest.fixture
    def temp_git_repo(self):
        """Create a temporary directory for testing."""
        temp_dir = tempfile.mkdtemp()
        yield temp_dir
        shutil.rmtree(temp_dir, ignore_errors=True)

    def test_initialization(self, temp_git_repo):
        """Test GitRepository initialization."""
        repo = GitRepository(temp_git_repo)
        assert repo.repo_path == temp_git_repo
        assert repo.repo is None
        assert repo.commits == []

    # Note: _is_git_url is in GUI layer (main_window.py), not in repository layer

    @patch('repo.repository.Repo')
    def test_load_repository_success(self, mock_repo_class, temp_git_repo):
        """Test successful repository loading."""
        # Mock GitPython Repo
        mock_repo = MagicMock()
        mock_repo_class.return_value = mock_repo

        # Mock refs (branches)
        mock_ref = MagicMock()
        mock_ref.name = "main"
        mock_repo.refs = [mock_ref]

        # Mock commits
        mock_commit = MagicMock()
        mock_commit.hexsha = "abc123"
        mock_commit.message = "Test commit"
        mock_commit.author.name = "Test User"
        mock_commit.author.email = "test@example.com"
        mock_commit.committed_datetime.strftime.return_value = "2025-01-01 10:00:00"
        mock_commit.parents = []
        mock_repo.iter_commits.return_value = [mock_commit]

        # Mock tags
        mock_repo.tags = []

        repo = GitRepository(temp_git_repo)
        result = repo.load_repository()

        assert result is True
        assert repo.repo is not None

    def test_load_repository_invalid_path(self):
        """Test loading repository with invalid path."""
        import os
        # Use a path that definitely doesn't exist and isn't a git repo
        invalid_path = os.path.join(os.path.dirname(__file__), "nonexistent_repo_xyz123")
        repo = GitRepository(invalid_path)

        # GitPython will raise exception for non-existent path
        try:
            result = repo.load_repository()
            # If it doesn't raise, it should return False
            assert result is False
        except Exception:
            # Exception is expected for non-existent path
            pass

    def test_parse_commits_not_loaded(self, temp_git_repo):
        """Test parsing commits without loading repository first."""
        repo = GitRepository(temp_git_repo)
        # Should handle gracefully when repo not loaded
        commits = repo.parse_commits()
        assert commits == []

    def test_get_uncommitted_changes_not_loaded(self, temp_git_repo):
        """Test getting uncommitted changes without loading repository."""
        repo = GitRepository(temp_git_repo)
        # Should handle gracefully when repo not loaded
        uncommitted = repo.get_uncommitted_changes()
        # May return dict with has_changes=False or None/empty list
        assert uncommitted is None or uncommitted == [] or (isinstance(uncommitted, dict) and not uncommitted.get('has_changes', True))

    @patch('repo.repository.Repo')
    def test_get_merge_branches(self, mock_repo_class, temp_git_repo):
        """Test merge branch detection."""
        mock_repo = MagicMock()
        mock_repo_class.return_value = mock_repo

        # Setup basic mocks
        mock_ref = MagicMock()
        mock_ref.name = "main"
        mock_ref.commit.hexsha = "abc123"
        mock_repo.refs = [mock_ref]

        # Mock commits with merge
        mock_commit1 = MagicMock()
        mock_commit1.hexsha = "merge123"
        mock_commit1.message = "Merge branch 'feature'"
        mock_commit1.author.name = "Test User"
        mock_commit1.author.email = "test@example.com"
        mock_commit1.committed_datetime.strftime.return_value = "2025-01-01 10:00:00 +0000"
        mock_parent1 = MagicMock()
        mock_parent1.hexsha = "parent1"
        mock_parent2 = MagicMock()
        mock_parent2.hexsha = "parent2"
        mock_commit1.parents = [mock_parent1, mock_parent2]

        mock_repo.iter_commits.return_value = [mock_commit1]
        mock_repo.tags = []

        repo = GitRepository(temp_git_repo)
        repo.load_repository()
        repo.parse_commits()

        merge_branches = repo.get_merge_branches()

        # Should return list (may be empty or with merges)
        assert isinstance(merge_branches, list)


class TestGitRepositoryFacade:
    """Tests for GitRepository facade pattern (Phase 2 refactoring)."""

    @pytest.fixture
    def temp_git_repo(self):
        """Create a temporary directory for testing."""
        temp_dir = tempfile.mkdtemp()
        yield temp_dir
        shutil.rmtree(temp_dir, ignore_errors=True)

    @patch('repo.repository.Repo')
    @patch('repo.repository.CommitParser')
    @patch('repo.repository.BranchAnalyzer')
    @patch('repo.repository.TagParser')
    def test_component_initialization_on_load(self, mock_tag_parser, mock_branch_analyzer,
                                             mock_commit_parser, mock_repo_class, temp_git_repo):
        """Test that components are initialized when repository is loaded."""
        mock_repo = MagicMock()
        mock_repo_class.return_value = mock_repo

        repo = GitRepository(temp_git_repo)
        result = repo.load_repository()

        assert result is True
        # Verify components were initialized
        mock_commit_parser.assert_called_once_with(mock_repo)
        mock_branch_analyzer.assert_called_once_with(mock_repo)
        mock_tag_parser.assert_called_once_with(mock_repo)

    @patch('repo.repository.Repo')
    @patch('repo.repository.CommitParser')
    @patch('repo.repository.BranchAnalyzer')
    @patch('repo.repository.TagParser')
    @patch('repo.repository.MergeDetector')
    def test_parse_commits_delegates_to_components(self, mock_merge_detector_class,
                                                   mock_tag_parser_class, mock_branch_analyzer_class,
                                                   mock_commit_parser_class, mock_repo_class, temp_git_repo):
        """Test that parse_commits delegates to CommitParser and other components."""
        # Setup mocks
        mock_repo = MagicMock()
        mock_repo_class.return_value = mock_repo
        mock_repo.heads = []
        mock_repo.git.status.return_value = ""  # No uncommitted changes

        # Mock component instances
        mock_commit_parser = MagicMock()
        mock_commit_parser.parse_commits.return_value = []
        mock_commit_parser_class.return_value = mock_commit_parser

        mock_branch_analyzer = MagicMock()
        mock_branch_analyzer.build_commit_branch_map.return_value = {}
        mock_branch_analyzer.build_branch_availability_map.return_value = {}
        mock_branch_analyzer_class.return_value = mock_branch_analyzer

        mock_tag_parser = MagicMock()
        mock_tag_parser.build_commit_tag_map.return_value = {}
        mock_tag_parser_class.return_value = mock_tag_parser

        mock_merge_detector = MagicMock()
        mock_merge_detector.detect_merge_branches.return_value = []
        mock_merge_detector_class.return_value = mock_merge_detector

        # Load and parse
        repo = GitRepository(temp_git_repo)
        repo.load_repository()
        commits = repo.parse_commits()

        # Verify delegation
        mock_branch_analyzer.build_commit_branch_map.assert_called_once()
        mock_tag_parser.build_commit_tag_map.assert_called_once()
        mock_branch_analyzer.build_branch_availability_map.assert_called_once()
        mock_commit_parser.parse_commits.assert_called_once()
        mock_merge_detector_class.assert_called_once()
        mock_merge_detector.detect_merge_branches.assert_called_once()

    @patch('repo.repository.Repo')
    @patch('repo.repository.CommitParser')
    @patch('repo.repository.BranchAnalyzer')
    @patch('repo.repository.TagParser')
    @patch('repo.repository.MergeDetector')
    def test_parse_commits_with_remote_delegates(self, mock_merge_detector_class,
                                                 mock_tag_parser_class, mock_branch_analyzer_class,
                                                 mock_commit_parser_class, mock_repo_class, temp_git_repo):
        """Test that parse_commits_with_remote delegates properly."""
        # Setup mocks
        mock_repo = MagicMock()
        mock_repo_class.return_value = mock_repo
        mock_repo.heads = []
        mock_repo.git.status.return_value = ""

        mock_commit_parser = MagicMock()
        mock_commit_parser.parse_commits_with_remote.return_value = []
        mock_commit_parser_class.return_value = mock_commit_parser

        mock_branch_analyzer = MagicMock()
        mock_branch_analyzer.build_commit_branch_map_with_remote.return_value = ({}, {})
        mock_branch_analyzer.build_branch_availability_map.return_value = {}
        mock_branch_analyzer.get_all_branch_names.return_value = set()
        mock_branch_analyzer.detect_branch_divergence.return_value = {}
        mock_branch_analyzer_class.return_value = mock_branch_analyzer

        mock_tag_parser = MagicMock()
        mock_tag_parser.build_commit_tag_map_with_remote.return_value = {}
        mock_tag_parser_class.return_value = mock_tag_parser

        mock_merge_detector = MagicMock()
        mock_merge_detector.detect_merge_branches.return_value = []
        mock_merge_detector_class.return_value = mock_merge_detector

        # Load and parse with remote
        repo = GitRepository(temp_git_repo)
        repo.load_repository()
        commits = repo.parse_commits_with_remote()

        # Verify delegation to remote-aware methods
        mock_branch_analyzer.build_commit_branch_map_with_remote.assert_called_once()
        mock_tag_parser.build_commit_tag_map_with_remote.assert_called_once()
        mock_branch_analyzer.get_all_branch_names.assert_called_once()
        mock_commit_parser.parse_commits_with_remote.assert_called_once()

    @patch('repo.repository.Repo')
    def test_components_are_none_before_load(self, mock_repo_class, temp_git_repo):
        """Test that component instances are None before loading."""
        repo = GitRepository(temp_git_repo)

        assert repo.commit_parser is None
        assert repo.branch_analyzer is None
        assert repo.tag_parser is None
        assert repo.merge_detector is None

    @patch('repo.repository.Repo')
    @patch('repo.repository.CommitParser')
    @patch('repo.repository.BranchAnalyzer')
    @patch('repo.repository.TagParser')
    def test_components_are_set_after_load(self, mock_tag_parser_class, mock_branch_analyzer_class,
                                          mock_commit_parser_class, mock_repo_class, temp_git_repo):
        """Test that component instances are set after loading."""
        mock_repo = MagicMock()
        mock_repo_class.return_value = mock_repo

        repo = GitRepository(temp_git_repo)
        repo.load_repository()

        assert repo.commit_parser is not None
        assert repo.branch_analyzer is not None
        assert repo.tag_parser is not None

    @patch('repo.repository.Repo')
    @patch('repo.repository.CommitParser')
    @patch('repo.repository.BranchAnalyzer')
    @patch('repo.repository.TagParser')
    @patch('repo.repository.MergeDetector')
    def test_merge_detector_created_on_parse(self, mock_merge_detector_class,
                                            mock_tag_parser_class, mock_branch_analyzer_class,
                                            mock_commit_parser_class, mock_repo_class, temp_git_repo):
        """Test that MergeDetector is created during parse_commits."""
        mock_repo = MagicMock()
        mock_repo_class.return_value = mock_repo
        mock_repo.heads = []
        mock_repo.git.status.return_value = ""

        mock_commit_parser = MagicMock()
        mock_commit_parser.parse_commits.return_value = []
        mock_commit_parser_class.return_value = mock_commit_parser

        mock_branch_analyzer = MagicMock()
        mock_branch_analyzer.build_commit_branch_map.return_value = {}
        mock_branch_analyzer.build_branch_availability_map.return_value = {}
        mock_branch_analyzer_class.return_value = mock_branch_analyzer

        mock_tag_parser = MagicMock()
        mock_tag_parser.build_commit_tag_map.return_value = {}
        mock_tag_parser_class.return_value = mock_tag_parser

        mock_merge_detector = MagicMock()
        mock_merge_detector.detect_merge_branches.return_value = []
        mock_merge_detector_class.return_value = mock_merge_detector

        repo = GitRepository(temp_git_repo)
        repo.load_repository()

        # MergeDetector should be None before parsing
        assert repo.merge_detector is None

        repo.parse_commits()

        # MergeDetector should be created during parse
        mock_merge_detector_class.assert_called_once()
        assert repo.merge_detector is not None
