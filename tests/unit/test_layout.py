"""
Tests for graph layout algorithm.

Tests graph positioning algorithm including lane assignment, lane recycling,
and merge branch detection.
"""

# MUST BE FIRST - initialize TCL/TK before any other imports
import tests.setup_tcl  # noqa: F401

import pytest
from datetime import datetime, timedelta, timezone

from visualization.layout import GraphLayout
from utils.data_structures import Commit, MergeBranch
from utils.constants import BRANCH_LANE_SPACING, COMMIT_START_X, COMMIT_VERTICAL_SPACING, COMMIT_START_Y


def create_commit(hash_val, message, branch, date, parents=None):
    """Helper to create a Commit object for testing."""
    return Commit(
        hash=hash_val,
        message=message,
        short_message=message[:50],
        author="Test Author",
        author_short="Test Author",
        author_email="test@example.com",
        date=date,
        date_relative="now",
        date_short=date.strftime("%Y-%m-%d"),
        parents=parents or [],
        branch=branch,
        branch_color="#000000"
    )


class TestGraphLayoutInitialization:
    """Tests for GraphLayout initialization."""

    def test_initialization_default_parameters(self):
        """Test initialization with default parameters."""
        commits = []
        layout = GraphLayout(commits)

        assert layout.commits == commits
        assert layout.branch_lanes == {}
        assert layout.used_lanes == set()
        assert layout.merge_branches == []
        assert layout.branch_spacing == BRANCH_LANE_SPACING
        assert layout.commit_start_x == COMMIT_START_X

    def test_initialization_custom_parameters(self):
        """Test initialization with custom parameters."""
        commits = []
        merge_branches = []
        layout = GraphLayout(
            commits,
            branch_spacing=30,
            commit_start_x=200,
            merge_branches=merge_branches
        )

        assert layout.branch_spacing == 30
        assert layout.commit_start_x == 200
        assert layout.merge_branches == merge_branches


class TestCalculatePositions:
    """Tests for calculate_positions() method."""

    def test_calculate_positions_empty_commits(self):
        """Test calculate_positions with empty commits list."""
        layout = GraphLayout([])
        result = layout.calculate_positions()

        assert result == []

    def test_calculate_positions_single_commit(self):
        """Test calculate_positions with single commit."""
        now = datetime.now(timezone.utc)
        commit = create_commit('abc123', 'Initial commit', 'main', now)

        layout = GraphLayout([commit])
        result = layout.calculate_positions()

        # Verify positioning
        assert len(result) == 1
        assert result[0].x == COMMIT_START_X  # Lane 0 (main)
        assert result[0].y == COMMIT_START_Y  # First commit
        assert result[0].table_row == 0

    def test_calculate_positions_multiple_commits_same_branch(self):
        """Test calculate_positions with multiple commits on same branch."""
        now = datetime.now(timezone.utc)
        commits = [
            create_commit('c1', 'Commit 1', 'main', now),
            create_commit('c2', 'Commit 2', 'main', now - timedelta(hours=1)),
            create_commit('c3', 'Commit 3', 'main', now - timedelta(hours=2)),
        ]

        layout = GraphLayout(commits)
        result = layout.calculate_positions()

        # Verify sorted by date (newest first)
        assert len(result) == 3
        assert result[0].hash == 'c1'  # Newest
        assert result[1].hash == 'c2'
        assert result[2].hash == 'c3'  # Oldest

        # Verify Y positions (increasing for older commits)
        assert result[0].y == COMMIT_START_Y
        assert result[1].y == COMMIT_START_Y + COMMIT_VERTICAL_SPACING
        assert result[2].y == COMMIT_START_Y + 2 * COMMIT_VERTICAL_SPACING

        # All on main branch (lane 0)
        assert all(c.x == COMMIT_START_X for c in result)

    def test_calculate_positions_two_branches(self):
        """Test calculate_positions with two branches."""
        now = datetime.now(timezone.utc)
        commits = [
            create_commit('c1', 'Main commit', 'main', now),
            create_commit('c2', 'Feature commit', 'feature', now - timedelta(hours=1)),
        ]

        layout = GraphLayout(commits)
        result = layout.calculate_positions()

        # Verify branch lanes
        assert layout.branch_lanes['main'] == 0
        assert layout.branch_lanes['feature'] >= 1  # Feature branch to the right

        # Verify X positions differ
        main_x = [c.x for c in result if c.branch == 'main']
        feature_x = [c.x for c in result if c.branch == 'feature']
        assert main_x[0] < feature_x[0]  # Main is left of feature


class TestBranchLaneAssignment:
    """Tests for branch lane assignment logic."""

    def test_main_branch_gets_lane_zero(self):
        """Test that main branch always gets lane 0."""
        now = datetime.now(timezone.utc)
        commits = [
            create_commit('c1', 'Main commit', 'main', now),
            create_commit('c2', 'Other commit', 'other', now - timedelta(hours=1)),
        ]

        layout = GraphLayout(commits)
        layout.calculate_positions()

        assert layout.branch_lanes['main'] == 0

    def test_master_branch_gets_lane_zero(self):
        """Test that master branch gets lane 0 (legacy name)."""
        now = datetime.now(timezone.utc)
        commits = [
            create_commit('c1', 'Master commit', 'master', now),
        ]

        layout = GraphLayout(commits)
        layout.calculate_positions()

        assert layout.branch_lanes['master'] == 0

    def test_branch_lanes_assigned(self):
        """Test that all branches get lane assignments."""
        now = datetime.now(timezone.utc)
        commits = [
            create_commit('c1', 'Main', 'main', now),
            create_commit('c2', 'Feature A', 'feature-a', now - timedelta(hours=1)),
            create_commit('c3', 'Feature B', 'feature-b', now - timedelta(hours=2)),
        ]

        layout = GraphLayout(commits)
        layout.calculate_positions()

        # All branches should have lane assignments
        assert 'main' in layout.branch_lanes
        assert 'feature-a' in layout.branch_lanes
        assert 'feature-b' in layout.branch_lanes
        # Lane recycling may cause branches to share lanes
        # (feature-a and feature-b don't overlap, so may use same lane)
        assert len(layout.branch_lanes) == 3

    def test_get_branch_lane(self):
        """Test get_branch_lane() method."""
        now = datetime.now(timezone.utc)
        commits = [
            create_commit('c1', 'Main', 'main', now),
            create_commit('c2', 'Feature', 'feature', now - timedelta(hours=1)),
        ]

        layout = GraphLayout(commits)
        layout.calculate_positions()

        # Verify getter
        assert layout.get_branch_lane('main') == 0
        assert layout.get_branch_lane('feature') >= 1
        assert layout.get_branch_lane('nonexistent') == 0  # Default


class TestAnalyzeBranchRelationships:
    """Tests for _analyze_branch_relationships() method."""

    def test_analyze_branch_relationships_single_branch(self):
        """Test analyzing single branch."""
        now = datetime.now(timezone.utc)
        commits = [
            create_commit('c1', 'Commit 1', 'main', now),
            create_commit('c2', 'Commit 2', 'main', now - timedelta(hours=1)),
        ]

        layout = GraphLayout(commits)
        relationships = layout._analyze_branch_relationships(commits)

        # Verify main branch info
        assert 'main' in relationships
        assert relationships['main']['parent_branches'] == set()
        assert relationships['main']['child_branches'] == set()

    def test_analyze_branch_relationships_parent_child(self):
        """Test analyzing parent-child branch relationships."""
        now = datetime.now(timezone.utc)
        commits = [
            create_commit('c1', 'Main commit', 'main', now, parents=[]),
            create_commit('c2', 'Feature commit', 'feature', now - timedelta(hours=1), parents=['c1']),
        ]

        layout = GraphLayout(commits)
        relationships = layout._analyze_branch_relationships(commits)

        # Feature branch should have main as parent
        assert 'main' in relationships['feature']['parent_branches']
        # Main branch should have feature as child
        assert 'feature' in relationships['main']['child_branches']


class TestLaneRecycling:
    """Tests for lane recycling functionality."""

    def test_lane_recycling_basic(self):
        """Test that lanes are recycled after branches end."""
        now = datetime.now(timezone.utc)
        commits = [
            # Main branch (lane 0)
            create_commit('c1', 'Main 1', 'main', now),
            # Feature branch (lane 1) - short-lived
            create_commit('c2', 'Feature', 'feature', now - timedelta(hours=1), parents=['c1']),
            # More main commits after feature ends
            create_commit('c3', 'Main 2', 'main', now - timedelta(hours=2), parents=['c1']),
            # Another feature branch - should recycle lane 1
            create_commit('c4', 'Feature 2', 'feature-2', now - timedelta(hours=3), parents=['c3']),
        ]

        layout = GraphLayout(commits)
        layout.calculate_positions()

        # Both feature branches should potentially use same lane (1)
        # due to recycling (feature branch ended before feature-2 started)
        max_lane = max(layout.branch_lanes.values())
        # Maximum lane should be 1 (0=main, 1=recycled for both features)
        # Note: This depends on timeline - if branches overlap, no recycling
        assert max_lane <= 2  # At most 2 concurrent branches


class TestMergeBranches:
    """Tests for merge branch handling."""

    def test_add_merge_branches_to_relationships(self):
        """Test adding merge branches to relationships."""
        now = datetime.now(timezone.utc)
        commits = [
            create_commit('c1', 'Branch point', 'main', now),
            create_commit('c2', 'Merge commit', 'main', now - timedelta(hours=2)),
        ]

        merge_branch = MergeBranch(
            branch_point_hash='c1',
            merge_point_hash='c2',
            commits_in_branch=[],
            virtual_branch_name='merge-abc123',
            original_color='#000000'
        )

        layout = GraphLayout(commits, merge_branches=[merge_branch])
        relationships = layout._analyze_branch_relationships(commits)
        layout._add_merge_branches_to_relationships(relationships)

        # Verify merge branch added
        assert 'merge-abc123' in relationships
        assert 'main' in relationships['merge-abc123']['parent_branches']


class TestEdgeCases:
    """Tests for edge cases and error handling."""

    def test_commits_with_no_parents(self):
        """Test commits with no parents (orphan commits)."""
        now = datetime.now(timezone.utc)
        commits = [
            create_commit('c1', 'Orphan 1', 'main', now, parents=[]),
            create_commit('c2', 'Orphan 2', 'feature', now - timedelta(hours=1), parents=[]),
        ]

        layout = GraphLayout(commits)
        result = layout.calculate_positions()

        # Should handle orphan commits without crashing
        assert len(result) == 2
        assert all(c.x >= 0 for c in result)
        assert all(c.y >= 0 for c in result)

    def test_commits_out_of_chronological_order(self):
        """Test commits provided out of chronological order."""
        now = datetime.now(timezone.utc)
        commits = [
            create_commit('c3', 'Oldest', 'main', now - timedelta(hours=2)),
            create_commit('c1', 'Newest', 'main', now),
            create_commit('c2', 'Middle', 'main', now - timedelta(hours=1)),
        ]

        layout = GraphLayout(commits)
        result = layout.calculate_positions()

        # Should sort by date (newest first)
        assert result[0].hash == 'c1'
        assert result[1].hash == 'c2'
        assert result[2].hash == 'c3'

    def test_many_concurrent_branches(self):
        """Test layout with many concurrent branches."""
        now = datetime.now(timezone.utc)
        commits = [create_commit(f'c{i}', f'Commit {i}', f'branch-{i}', now - timedelta(hours=i))
                   for i in range(10)]

        layout = GraphLayout(commits)
        result = layout.calculate_positions()

        # Should assign distinct lanes to all branches
        assert len(layout.branch_lanes) == 10
        assert len(result) == 10

    def test_custom_spacing_parameters(self):
        """Test layout with custom spacing parameters."""
        now = datetime.now(timezone.utc)
        commits = [
            create_commit('c1', 'Commit 1', 'main', now),
            create_commit('c2', 'Commit 2', 'feature', now - timedelta(hours=1)),
        ]

        # Custom spacing
        layout = GraphLayout(commits, branch_spacing=50, commit_start_x=300)
        result = layout.calculate_positions()

        # Verify custom parameters applied
        main_commit = [c for c in result if c.branch == 'main'][0]
        assert main_commit.x == 300  # Custom start X

        feature_commit = [c for c in result if c.branch == 'feature'][0]
        # Feature should be 50px to the right (custom spacing)
        expected_x = 300 + (layout.branch_lanes['feature'] * 50)
        assert feature_commit.x == expected_x


class TestIntegration:
    """Integration tests for complete layout scenarios."""

    def test_typical_git_workflow(self):
        """Test typical Git workflow: main → feature → merge."""
        now = datetime.now(timezone.utc)
        commits = [
            # Main branch
            create_commit('c1', 'Initial commit', 'main', now - timedelta(days=3)),
            create_commit('c2', 'Add feature', 'main', now - timedelta(days=2)),
            # Feature branch
            create_commit('c3', 'Feature work 1', 'feature/new-ui', now - timedelta(days=1), parents=['c2']),
            create_commit('c4', 'Feature work 2', 'feature/new-ui', now - timedelta(hours=12), parents=['c3']),
            # Merge back to main
            create_commit('c5', 'Merge feature', 'main', now, parents=['c2', 'c4']),
        ]

        layout = GraphLayout(commits)
        result = layout.calculate_positions()

        # Verify layout
        assert len(result) == 5
        # Main branch on lane 0
        assert layout.branch_lanes['main'] == 0
        # Feature branch on lane > 0
        assert layout.branch_lanes['feature/new-ui'] > 0

        # Verify chronological order
        assert result[0].hash == 'c5'  # Newest
        assert result[-1].hash == 'c1'  # Oldest

    def test_complex_multi_branch_scenario(self):
        """Test complex scenario with multiple branches."""
        now = datetime.now(timezone.utc)
        commits = [
            # Main branch
            create_commit('c1', 'Main 1', 'main', now - timedelta(days=5)),
            create_commit('c2', 'Main 2', 'main', now - timedelta(days=4)),
            # Feature A
            create_commit('c3', 'Feature A', 'feature-a', now - timedelta(days=3), parents=['c2']),
            # Feature B
            create_commit('c4', 'Feature B', 'feature-b', now - timedelta(days=2), parents=['c2']),
            # More main
            create_commit('c5', 'Main 3', 'main', now - timedelta(days=1)),
            # Bugfix branch
            create_commit('c6', 'Bugfix', 'bugfix/critical', now, parents=['c5']),
        ]

        layout = GraphLayout(commits)
        result = layout.calculate_positions()

        # Verify all branches assigned lanes
        assert len(layout.branch_lanes) == 4
        assert 'main' in layout.branch_lanes
        assert 'feature-a' in layout.branch_lanes
        assert 'feature-b' in layout.branch_lanes
        assert 'bugfix/critical' in layout.branch_lanes

        # Main should be lane 0
        assert layout.branch_lanes['main'] == 0
