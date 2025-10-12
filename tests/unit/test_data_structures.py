"""
Tests for data_structures.py.

Tests dataclasses used throughout the application.
"""

# MUST BE FIRST - initialize TCL/TK before any other imports
import tests.setup_tcl  # noqa: F401

import pytest
from datetime import datetime, timezone

from utils.data_structures import Tag, Commit, MergeBranch, Branch


class TestTag:
    """Tests for Tag dataclass."""

    def test_tag_creation(self):
        """Test basic Tag creation."""
        # Act
        tag = Tag(name='v1.0.0')

        # Assert
        assert tag.name == 'v1.0.0'
        assert tag.is_remote is False  # Default
        assert tag.message == ""  # Default

    def test_tag_with_all_fields(self):
        """Test Tag creation with all fields."""
        # Act
        tag = Tag(
            name='v2.0.0',
            is_remote=True,
            message='Release 2.0.0'
        )

        # Assert
        assert tag.name == 'v2.0.0'
        assert tag.is_remote is True
        assert tag.message == 'Release 2.0.0'

    def test_tag_defaults(self):
        """Test that Tag has correct default values."""
        # Act
        tag = Tag(name='test')

        # Assert
        assert tag.is_remote is False
        assert tag.message == ""


class TestCommit:
    """Tests for Commit dataclass."""

    def test_commit_creation_required_fields(self):
        """Test Commit creation with required fields."""
        # Arrange
        now = datetime.now(timezone.utc)

        # Act
        commit = Commit(
            hash='abc123',
            message='Test commit',
            short_message='Test',
            author='Test Author',
            author_short='Test A',
            author_email='test@example.com',
            date=now,
            date_relative='now',
            date_short='2025-01-01',
            parents=['parent1'],
            branch='main',
            branch_color='#000000'
        )

        # Assert
        assert commit.hash == 'abc123'
        assert commit.message == 'Test commit'
        assert commit.author == 'Test Author'
        assert commit.branch == 'main'

    def test_commit_post_init_tags_default(self):
        """Test that Commit.__post_init__ initializes tags to empty list."""
        # Arrange
        now = datetime.now(timezone.utc)

        # Act
        commit = Commit(
            hash='abc123',
            message='Test',
            short_message='Test',
            author='Author',
            author_short='A',
            author_email='a@example.com',
            date=now,
            date_relative='now',
            date_short='2025-01-01',
            parents=[],
            branch='main',
            branch_color='#000000'
        )

        # Assert
        assert commit.tags == []
        assert isinstance(commit.tags, list)

    def test_commit_post_init_additional_branches_default(self):
        """Test that Commit.__post_init__ initializes additional_branches to empty list."""
        # Arrange
        now = datetime.now(timezone.utc)

        # Act
        commit = Commit(
            hash='abc123',
            message='Test',
            short_message='Test',
            author='Author',
            author_short='A',
            author_email='a@example.com',
            date=now,
            date_relative='now',
            date_short='2025-01-01',
            parents=[],
            branch='main',
            branch_color='#000000'
        )

        # Assert
        assert commit.additional_branches == []
        assert isinstance(commit.additional_branches, list)

    def test_commit_with_provided_tags(self):
        """Test Commit with explicitly provided tags list."""
        # Arrange
        now = datetime.now(timezone.utc)
        tags = [Tag(name='v1.0.0'), Tag(name='v2.0.0')]

        # Act
        commit = Commit(
            hash='abc123',
            message='Test',
            short_message='Test',
            author='Author',
            author_short='A',
            author_email='a@example.com',
            date=now,
            date_relative='now',
            date_short='2025-01-01',
            parents=[],
            branch='main',
            branch_color='#000000',
            tags=tags
        )

        # Assert
        assert commit.tags == tags
        assert len(commit.tags) == 2

    def test_commit_optional_fields_defaults(self):
        """Test that Commit has correct default values for optional fields."""
        # Arrange
        now = datetime.now(timezone.utc)

        # Act
        commit = Commit(
            hash='abc123',
            message='Test',
            short_message='Test',
            author='Author',
            author_short='A',
            author_email='a@example.com',
            date=now,
            date_relative='now',
            date_short='2025-01-01',
            parents=[],
            branch='main',
            branch_color='#000000'
        )

        # Assert
        assert commit.x == 0
        assert commit.y == 0
        assert commit.table_row == 0
        assert commit.description == ""
        assert commit.description_short == ""
        assert commit.is_remote is False
        assert commit.branch_availability == "local_only"
        assert commit.is_branch_head is False
        assert commit.branch_head_type == "none"
        assert commit.is_uncommitted is False
        assert commit.uncommitted_type == "none"
        assert commit.is_merge_branch is False


class TestMergeBranch:
    """Tests for MergeBranch dataclass."""

    def test_merge_branch_creation(self):
        """Test MergeBranch creation with all required fields."""
        # Act
        merge_branch = MergeBranch(
            branch_point_hash='abc123',
            merge_point_hash='def456',
            commits_in_branch=['commit1', 'commit2'],
            virtual_branch_name='merge-abc123',
            original_color='#ff0000'
        )

        # Assert
        assert merge_branch.branch_point_hash == 'abc123'
        assert merge_branch.merge_point_hash == 'def456'
        assert merge_branch.commits_in_branch == ['commit1', 'commit2']
        assert merge_branch.virtual_branch_name == 'merge-abc123'
        assert merge_branch.original_color == '#ff0000'

    def test_merge_branch_empty_commits_list(self):
        """Test MergeBranch with empty commits list."""
        # Act
        merge_branch = MergeBranch(
            branch_point_hash='abc123',
            merge_point_hash='def456',
            commits_in_branch=[],
            virtual_branch_name='merge-test',
            original_color='#00ff00'
        )

        # Assert
        assert merge_branch.commits_in_branch == []
        assert isinstance(merge_branch.commits_in_branch, list)


class TestBranch:
    """Tests for Branch dataclass."""

    def test_branch_creation(self):
        """Test Branch creation with all required fields."""
        # Arrange
        now = datetime.now(timezone.utc)
        commit1 = Commit(
            hash='c1',
            message='Commit 1',
            short_message='Commit 1',
            author='Author',
            author_short='A',
            author_email='a@example.com',
            date=now,
            date_relative='now',
            date_short='2025-01-01',
            parents=[],
            branch='main',
            branch_color='#000000'
        )

        # Act
        branch = Branch(
            name='main',
            color='#000000',
            commits=[commit1],
            start_commit='c1',
            end_commit='c1'
        )

        # Assert
        assert branch.name == 'main'
        assert branch.color == '#000000'
        assert len(branch.commits) == 1
        assert branch.start_commit == 'c1'
        assert branch.end_commit == 'c1'

    def test_branch_with_multiple_commits(self):
        """Test Branch with multiple commits."""
        # Arrange
        now = datetime.now(timezone.utc)
        commits = []
        for i in range(3):
            commit = Commit(
                hash=f'c{i}',
                message=f'Commit {i}',
                short_message=f'Commit {i}',
                author='Author',
                author_short='A',
                author_email='a@example.com',
                date=now,
                date_relative='now',
                date_short='2025-01-01',
                parents=[],
                branch='feature',
                branch_color='#ff0000'
            )
            commits.append(commit)

        # Act
        branch = Branch(
            name='feature',
            color='#ff0000',
            commits=commits,
            start_commit='c0',
            end_commit='c2'
        )

        # Assert
        assert branch.name == 'feature'
        assert len(branch.commits) == 3
        assert branch.commits[0].hash == 'c0'
        assert branch.commits[2].hash == 'c2'
