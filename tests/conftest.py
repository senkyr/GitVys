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
