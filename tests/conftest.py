"""Pytest configuration and shared fixtures."""

import pytest
import sys
import os
from pathlib import Path

# Add src directory to path for imports
src_path = Path(__file__).parent.parent / "src"
sys.path.insert(0, str(src_path))

# Import after path setup
import tkinter as tk
from utils.data_structures import Commit, Tag


@pytest.fixture
def root():
    """Create a tkinter root window for tests."""
    root = tk.Tk()
    root.withdraw()  # Don't show window during tests
    yield root
    try:
        root.destroy()
    except tk.TclError:
        pass  # Already destroyed


@pytest.fixture
def canvas(root):
    """Create a test canvas."""
    canvas = tk.Canvas(root, width=800, height=600)
    yield canvas


@pytest.fixture
def mock_commits():
    """Create mock commit data for testing."""
    from datetime import datetime
    commits = []
    for i in range(5):
        commit = Commit(
            hash=f"abc{i:03d}{'0' * 37}",  # 40-char hash
            message=f"Commit message {i}",
            short_message=f"Commit message {i}",
            author="Test User",
            author_short="Test User",
            author_email="test@example.com",
            date=datetime.strptime(f"2025-01-{i+1:02d} 10:00:00", "%Y-%m-%d %H:%M:%S"),
            date_relative=f"{i+1} days ago",
            date_short=f"2025-01-{i+1:02d}",
            parents=[f"abc{i-1:03d}{'0' * 37}"] if i > 0 else [],
            branch="main" if i < 3 else "feature/test",
            branch_color="#3366cc" if i < 3 else "#66cc33",
            x=50,
            y=50 + i * 60,
            description="",
            description_short="",
            tags=[]
        )
        commits.append(commit)

    # Apply layout to commits (required by GraphDrawer)
    from visualization.layout import GraphLayout
    layout = GraphLayout(commits, merge_branches=[])
    layout.calculate_positions()

    return commits


@pytest.fixture
def mock_commits_with_tags():
    """Create mock commits with tags."""
    from datetime import datetime
    commits = []
    for i in range(3):
        # Add tags
        tags_list = []
        if i == 0:
            tags_list = [Tag(name="v1.0.0")]
        elif i == 1:
            tags_list = [Tag(name="release-2.0")]

        commit = Commit(
            hash=f"abc{i:03d}{'0' * 37}",
            message=f"Release {i}.0",
            short_message=f"Release {i}.0",
            author="Test User",
            author_short="Test User",
            author_email="test@example.com",
            date=datetime.strptime(f"2025-01-{i+1:02d} 10:00:00", "%Y-%m-%d %H:%M:%S"),
            date_relative=f"{i+1} days ago",
            date_short=f"2025-01-{i+1:02d}",
            parents=[f"abc{i-1:03d}{'0' * 37}"] if i > 0 else [],
            branch="main",
            branch_color="#3366cc",
            x=50,
            y=50 + i * 60,
            description="",
            description_short="",
            tags=tags_list
        )
        commits.append(commit)

    # Apply layout to commits (required by GraphDrawer)
    from visualization.layout import GraphLayout
    layout = GraphLayout(commits, merge_branches=[])
    layout.calculate_positions()

    return commits


# === Git Mock Fixtures for Phase 2 Testing ===

class MockHeadsDict:
    """Mock for GitPython heads that supports both iteration and dictionary access."""

    def __init__(self, heads_list):
        self._heads = heads_list
        self._dict = {h.name: h for h in heads_list}

    def __iter__(self):
        return iter(self._heads)

    def __getitem__(self, name):
        return self._dict[name]

    def __len__(self):
        return len(self._heads)


class MockRefsDict:
    """Mock for GitPython refs that supports both iteration and dictionary access."""

    def __init__(self, refs_list):
        self._refs = refs_list
        # Build dict with branch names (without origin/ prefix for easier access)
        self._dict = {}
        for ref in refs_list:
            # Support both "origin/main" and "main" as keys
            if ref.name.startswith("origin/"):
                branch_name = ref.name.split("/", 1)[1]  # Get part after "origin/"
                self._dict[branch_name] = ref
            self._dict[ref.name] = ref

    def __iter__(self):
        return iter(self._refs)

    def __getitem__(self, name):
        return self._dict[name]

    def __len__(self):
        return len(self._refs)


@pytest.fixture
def mock_git_repo():
    """Create a mock GitPython Repo object."""
    from unittest.mock import MagicMock
    from datetime import datetime, timezone

    repo = MagicMock()

    # Mock commits for heads (with explicit parents to avoid infinite loops)
    main_commit = MagicMock()
    main_commit.hexsha = "a" * 40
    main_commit.parents = []  # Explicit empty list to stop traversal

    feature_commit = MagicMock()
    feature_commit.hexsha = "b" * 40
    feature_commit.parents = []  # Explicit empty list to stop traversal

    # Mock heads (local branches)
    main_head = MagicMock()
    main_head.name = "main"
    main_head.commit = main_commit

    feature_head = MagicMock()
    feature_head.name = "feature/test"
    feature_head.commit = feature_commit

    repo.heads = MockHeadsDict([main_head, feature_head])

    # Mock commits for remote refs (with explicit parents)
    remote_main_commit = MagicMock()
    remote_main_commit.hexsha = "a" * 40
    remote_main_commit.parents = []

    remote_feature_commit = MagicMock()
    remote_feature_commit.hexsha = "c" * 40
    remote_feature_commit.parents = []

    # Mock remote refs
    remote = MagicMock()
    remote_main_ref = MagicMock()
    remote_main_ref.name = "origin/main"
    remote_main_ref.commit = remote_main_commit

    remote_feature_ref = MagicMock()
    remote_feature_ref.name = "origin/feature/test"
    remote_feature_ref.commit = remote_feature_commit

    remote.refs = MockRefsDict([remote_main_ref, remote_feature_ref])
    repo.remotes = MagicMock()
    repo.remotes.origin = remote
    repo.remote.return_value = remote

    # Mock tags
    tag1 = MagicMock()
    tag1.name = "v1.0.0"
    tag1.commit.hexsha = "a" * 40
    tag1.tag = None  # Lightweight tag

    tag2 = MagicMock()
    tag2.name = "release-2.0"
    tag2.commit.hexsha = "b" * 40
    tag2.tag = MagicMock()
    tag2.tag.message = "Release 2.0\n\nBug fixes and improvements"

    repo.tags = [tag1, tag2]

    return repo


@pytest.fixture
def mock_git_commits():
    """Create mock GitPython commit objects."""
    from unittest.mock import MagicMock
    from datetime import datetime, timezone

    commits = []

    # Create 5 mock commits
    for i in range(5):
        commit = MagicMock()
        commit.hexsha = f"{'abc'[i % 3]}" * 40
        commit.message = f"Commit message {i}\n\nDetailed description for commit {i}"

        commit.author = MagicMock()
        commit.author.name = "Test User"
        commit.author.email = "test@example.com"

        commit.committed_datetime = datetime(2025, 1, i+1, 10, 0, 0, tzinfo=timezone.utc)

        # Add parents (first commit has no parent)
        if i > 0:
            parent = MagicMock()
            parent.hexsha = f"{'abc'[(i-1) % 3]}" * 40
            commit.parents = [parent]
        else:
            commit.parents = []

        commits.append(commit)

    return commits


@pytest.fixture
def mock_merge_commit():
    """Create a mock merge commit with 2 parents."""
    from unittest.mock import MagicMock
    from datetime import datetime, timezone

    merge_commit = MagicMock()
    merge_commit.hexsha = "m" * 40
    merge_commit.message = "Merge branch 'feature/login' into main"

    merge_commit.author = MagicMock()
    merge_commit.author.name = "Test User"
    merge_commit.author.email = "test@example.com"

    merge_commit.committed_datetime = datetime(2025, 1, 10, 12, 0, 0, tzinfo=timezone.utc)

    # Two parents for merge
    parent1 = MagicMock()
    parent1.hexsha = "a" * 40

    parent2 = MagicMock()
    parent2.hexsha = "b" * 40

    merge_commit.parents = [parent1, parent2]

    return merge_commit


# === Phase 3 GUI Component Fixtures ===

@pytest.fixture
def mock_parent_window(root):
    """Create a mock MainWindow instance for component tests."""
    from unittest.mock import MagicMock

    window = MagicMock()
    window.root = root
    window.theme_manager = MagicMock()
    window.theme_manager.get_color.return_value = "#FFFFFF"

    # Mock common methods
    window.update_status = MagicMock()
    window.show_error = MagicMock()
    window.show_graph = MagicMock()

    # Mock UI elements that components interact with
    window.progress = MagicMock()
    window.progress.config = MagicMock()
    window.progress.start = MagicMock()
    window.progress.stop = MagicMock()

    window.fetch_button = MagicMock()
    window.fetch_button.config = MagicMock()

    return window


@pytest.fixture
def temp_settings_dir(tmp_path):
    """Create temporary ~/.gitvys/ directory for testing."""
    settings_dir = tmp_path / ".gitvys"
    settings_dir.mkdir()

    # Patch os.path.expanduser to return test directory
    import os
    original_expanduser = os.path.expanduser

    def mock_expanduser(path):
        if path.startswith("~"):
            return str(tmp_path / path[2:])  # Replace ~ with tmp_path
        return original_expanduser(path)

    os.path.expanduser = mock_expanduser

    yield settings_dir

    # Restore original function
    os.path.expanduser = original_expanduser
