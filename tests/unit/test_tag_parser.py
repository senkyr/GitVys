"""Unit tests for repo.parsers.tag_parser module."""

import pytest
from unittest.mock import MagicMock
from repo.parsers.tag_parser import TagParser
from utils.data_structures import Tag


class TestTagParserInitialization:
    """Tests for TagParser initialization."""

    def test_initialization(self, mock_git_repo):
        """Test TagParser initialization with GitPython Repo."""
        parser = TagParser(mock_git_repo)
        assert parser.repo is not None
        assert parser.repo == mock_git_repo


class TestBuildCommitTagMap:
    """Tests for building commit-tag mappings (local tags)."""

    def test_build_basic_tag_map(self, mock_git_repo):
        """Test building commit-tag map for local tags."""
        parser = TagParser(mock_git_repo)
        commit_tag_map = parser.build_commit_tag_map()

        # Should have tags from mock (2 tags)
        assert isinstance(commit_tag_map, dict)
        assert len(commit_tag_map) > 0

        # Check tag at commit "a" * 40 (v1.0.0)
        commit_a = "a" * 40
        assert commit_a in commit_tag_map
        assert len(commit_tag_map[commit_a]) == 1
        assert commit_tag_map[commit_a][0].name == "v1.0.0"
        assert commit_tag_map[commit_a][0].is_remote is False

    def test_annotated_tag_with_message(self, mock_git_repo):
        """Test parsing annotated tag with message."""
        parser = TagParser(mock_git_repo)
        commit_tag_map = parser.build_commit_tag_map()

        # Check tag at commit "b" * 40 (release-2.0 with message)
        commit_b = "b" * 40
        assert commit_b in commit_tag_map
        tag = commit_tag_map[commit_b][0]
        assert tag.name == "release-2.0"
        assert tag.message == "Release 2.0\n\nBug fixes and improvements"

    def test_lightweight_tag_no_message(self, mock_git_repo):
        """Test parsing lightweight tag without message."""
        parser = TagParser(mock_git_repo)
        commit_tag_map = parser.build_commit_tag_map()

        # v1.0.0 is a lightweight tag (no message)
        commit_a = "a" * 40
        tag = commit_tag_map[commit_a][0]
        assert tag.message == ""

    def test_multiple_tags_per_commit(self, mock_git_repo):
        """Test handling multiple tags on same commit."""
        # Add another tag to same commit
        tag3 = MagicMock()
        tag3.name = "v1.0.1"
        tag3.commit.hexsha = "a" * 40
        tag3.tag = None

        mock_git_repo.tags = mock_git_repo.tags + [tag3]

        parser = TagParser(mock_git_repo)
        commit_tag_map = parser.build_commit_tag_map()

        commit_a = "a" * 40
        assert len(commit_tag_map[commit_a]) == 2
        tag_names = [t.name for t in commit_tag_map[commit_a]]
        assert "v1.0.0" in tag_names
        assert "v1.0.1" in tag_names


class TestBuildCommitTagMapWithRemote:
    """Tests for building commit-tag map with remote tags."""

    def test_build_with_remote_tags(self, mock_git_repo):
        """Test building map including remote tags."""
        # Setup remote tags
        remote_tag_ref = MagicMock()
        remote_tag_ref.name = "origin/tags/v2.0.0"
        remote_tag_ref.commit.hexsha = "c" * 40

        mock_git_repo.remote.return_value.refs = [remote_tag_ref]

        parser = TagParser(mock_git_repo)
        commit_tag_map = parser.build_commit_tag_map_with_remote()

        # Should have both local and remote tags
        assert "a" * 40 in commit_tag_map  # Local tag v1.0.0
        assert "c" * 40 in commit_tag_map  # Remote tag v2.0.0

        # Check remote tag has origin/ prefix
        remote_tags = commit_tag_map["c" * 40]
        assert any("origin/" in t.name for t in remote_tags)
        assert remote_tags[0].is_remote is True

    def test_local_tag_priority_over_remote(self, mock_git_repo):
        """Test that local tags have priority over remote with same name."""
        # Setup: same tag name exists locally and remotely
        remote_tag_ref = MagicMock()
        remote_tag_ref.name = "origin/tags/v1.0.0"
        remote_tag_ref.commit.hexsha = "a" * 40  # Same commit as local

        mock_git_repo.remote.return_value.refs = [remote_tag_ref]

        parser = TagParser(mock_git_repo)
        commit_tag_map = parser.build_commit_tag_map_with_remote()

        commit_a = "a" * 40
        # Should have local tag, but not duplicate remote tag
        tag_names = [t.name for t in commit_tag_map[commit_a]]
        assert "v1.0.0" in tag_names
        # Should not have "origin/v1.0.0" since local already exists
        assert not any(t.name == "origin/v1.0.0" for t in commit_tag_map[commit_a])

    def test_remote_tag_naming_convention(self, mock_git_repo):
        """Test that remote tags get origin/ prefix."""
        remote_tag_ref = MagicMock()
        remote_tag_ref.name = "origin/tags/beta-1"
        remote_tag_ref.commit.hexsha = "d" * 40

        mock_git_repo.remote.return_value.refs = [remote_tag_ref]

        parser = TagParser(mock_git_repo)
        commit_tag_map = parser.build_commit_tag_map_with_remote()

        commit_d = "d" * 40
        assert commit_d in commit_tag_map
        tag = commit_tag_map[commit_d][0]
        assert tag.name.startswith("origin/")
        assert "beta-1" in tag.name
