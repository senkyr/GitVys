"""MergeDetector - handles detection and analysis of merge branches."""

import re
import colorsys
from typing import List, Dict, Set, Optional
from git import Repo
from utils.data_structures import Commit, MergeBranch
from utils.logging_config import get_logger
from visualization.colors import get_branch_color

logger = get_logger(__name__)


class MergeDetector:
    """Handles detection and analysis of merge branches."""

    def __init__(self, repo: Repo, commits: List[Commit]):
        """Initialize MergeDetector.

        Args:
            repo: GitPython Repo object
            commits: List of all commits
        """
        self.repo = repo
        self.commits = commits

    def detect_merge_branches(self) -> List[MergeBranch]:
        """Detect merge patterns and create virtual merge branches.

        Returns:
            List of detected MergeBranch objects
        """
        if not self.commits:
            return []

        merge_branches = []
        commit_map = {commit.hash: commit for commit in self.commits}

        # Create used_colors set from existing commits
        used_colors = set()
        for commit in self.commits:
            if commit.branch_color:
                used_colors.add(commit.branch_color)

        # Extended commit map for full hashes
        full_hash_map = self.build_full_hash_map()

        # Find merge commits (more than 1 parent)
        merge_commits = [commit for commit in self.commits if len(commit.parents) >= 2]

        for merge_commit in merge_commits:
            try:
                if len(merge_commit.parents) < 2:
                    continue

                # First parent = main branch, second parent = merged branch
                main_parent_hash = merge_commit.parents[0]
                merge_parent_hash = merge_commit.parents[1]

                # Find branch point (common ancestor) using GitPython
                if self.repo and merge_parent_hash in full_hash_map and main_parent_hash in full_hash_map:
                    try:
                        full_merge_parent = full_hash_map[merge_parent_hash]
                        full_main_parent = full_hash_map[main_parent_hash]

                        # Find merge base (common ancestor)
                        merge_base = self.repo.merge_base(full_merge_parent, full_main_parent)
                        if merge_base:
                            branch_point_hash = merge_base[0].hexsha[:8]

                            # Trace commits in merge branch
                            merge_branch_commits = self.trace_merge_branch_commits(
                                merge_parent_hash, branch_point_hash, commit_map
                            )

                            # If we found commits in merge branch
                            if merge_branch_commits:
                                # Get commits in main line of branches with HEAD
                                commits_in_branches_with_head = self.get_commits_in_branches_with_head()

                                # Filter commits - remove those in path to HEAD
                                filtered_commits = [c for c in merge_branch_commits
                                                   if c not in commits_in_branches_with_head]

                                # If no commits left after filtering, skip
                                if not filtered_commits:
                                    continue

                                merge_branch_commits = filtered_commits

                                # Create virtual branch name
                                virtual_name = f"merge-{merge_commit.hash}"

                                # Determine original color (from merged branch name in commit message)
                                original_color = '#666666'  # Default fallback

                                # Try to extract branch name from merge commit message
                                branch_name = self.extract_branch_name_from_merge(merge_commit, full_hash_map)
                                if branch_name:
                                    original_color = get_branch_color(branch_name, used_colors)

                                # Fallback: neutral gray if couldn't detect branch name
                                if original_color == '#666666':
                                    original_color = '#999999'  # Neutral light gray for unknown branches

                                merge_branch = MergeBranch(
                                    branch_point_hash=branch_point_hash,
                                    merge_point_hash=merge_commit.hash,
                                    commits_in_branch=merge_branch_commits,
                                    virtual_branch_name=virtual_name,
                                    original_color=original_color
                                )

                                merge_branches.append(merge_branch)
                    except Exception as e:
                        # If GitPython approach fails, skip this merge
                        continue

            except Exception as e:
                # If processing this merge commit fails, continue
                continue

        return merge_branches

    def apply_merge_branch_styling(self, commits: List[Commit], merge_branches: List[MergeBranch]):
        """Apply styling to commits in merge branches - paler colors, virtual branch names.

        Args:
            commits: List of all commits to style
            merge_branches: List of detected merge branches
        """
        if not merge_branches:
            return

        # Create map commit hash -> merge branch for fast lookup
        # If commit belongs to multiple merge branches, first wins (don't override)
        commit_to_merge_branch = {}
        for merge_branch in merge_branches:
            for commit_hash in merge_branch.commits_in_branch:
                if commit_hash not in commit_to_merge_branch:
                    commit_to_merge_branch[commit_hash] = merge_branch

        # Apply styling to commits in merge branches
        styled_count = 0
        for commit in commits:
            # Don't recolor commit if already remapped to merge branch (first merge wins)
            if commit.hash in commit_to_merge_branch and not getattr(commit, 'is_merge_branch', False):
                merge_branch = commit_to_merge_branch[commit.hash]

                # Change branch to virtual name
                old_branch = commit.branch
                commit.branch = merge_branch.virtual_branch_name

                # Apply paler color (similar to _make_color_pale in graph_drawer)
                old_color = commit.branch_color
                commit.branch_color = self.make_color_pale(merge_branch.original_color, blend_type="merge")

                # Mark as merge branch commit (for potential future features)
                commit.is_merge_branch = True
                styled_count += 1

    def build_full_hash_map(self) -> Dict[str, str]:
        """Build map of short hashes to full hashes for GitPython.

        Returns:
            Dictionary mapping short hash to full hash
        """
        full_hash_map = {}
        if self.repo:
            try:
                seen_commits = set()

                # 1. First local branches
                try:
                    for head in self.repo.heads:
                        try:
                            for commit in self.repo.iter_commits(head):
                                if commit.hexsha not in seen_commits:
                                    seen_commits.add(commit.hexsha)
                                    short_hash = commit.hexsha[:8]
                                    full_hash_map[short_hash] = commit.hexsha
                        except Exception as e:
                            logger.warning(f"Failed to iterate commits for local branch {head.name}: {e}")
                            continue
                except Exception as e:
                    logger.warning(f"Failed to access local branches: {e}")

                # 2. Then remote branches (except /HEAD)
                try:
                    if hasattr(self.repo, 'remotes') and self.repo.remotes:
                        remote_refs = list(self.repo.remote().refs)
                        for remote_ref in remote_refs:
                            # Skip HEAD reference
                            if remote_ref.name.endswith('/HEAD'):
                                continue

                            try:
                                for commit in self.repo.iter_commits(remote_ref):
                                    if commit.hexsha not in seen_commits:
                                        seen_commits.add(commit.hexsha)
                                        short_hash = commit.hexsha[:8]
                                        full_hash_map[short_hash] = commit.hexsha
                            except Exception as e:
                                logger.warning(f"Failed to iterate commits for remote ref {remote_ref.name}: {e}")
                                continue
                except Exception as e:
                    logger.debug(f"Failed to access remote refs: {e}")

            except Exception as e:
                logger.warning(f"Failed to build full hash map: {e}")
        return full_hash_map

    def trace_merge_branch_commits(self, merge_parent_hash: str, branch_point_hash: str,
                                    commit_map: Dict[str, Commit]) -> List[str]:
        """Trace backwards commits in merge branch from merge parent to branch point.

        Args:
            merge_parent_hash: Hash of merge parent commit
            branch_point_hash: Hash of branch point commit
            commit_map: Map of commit hash to Commit object

        Returns:
            List of commit hashes in merge branch
        """
        merge_branch_commits = []
        current = merge_parent_hash
        visited = set()

        while current and current != branch_point_hash and current not in visited:
            visited.add(current)
            if current in commit_map:
                commit = commit_map[current]
                merge_branch_commits.append(current)
                # Continue to first parent (linear path)
                if commit.parents:
                    current = commit.parents[0]
                else:
                    break
            else:
                break

        return merge_branch_commits

    def get_commits_in_branches_with_head(self) -> Set[str]:
        """Get all commits in main line (first-parent path) of branches with HEAD.

        Returns:
            Set of commit hashes in main line
        """
        commits_in_branches_with_head = set()
        if self.repo:
            try:
                for branch_head in self.repo.heads:
                    try:
                        commit = branch_head.commit
                        while commit:
                            commits_in_branches_with_head.add(commit.hexsha[:8])
                            if commit.parents:
                                commit = commit.parents[0]  # Only first parent
                            else:
                                break
                    except Exception as e:
                        logger.warning(f"Failed to traverse branch {branch_head.name}: {e}")
                        continue
            except Exception as e:
                logger.warning(f"Failed to get branches with HEAD: {e}")
        return commits_in_branches_with_head

    def extract_branch_name_from_merge(self, merge_commit: Commit, full_hash_map: Dict[str, str]) -> Optional[str]:
        """Extract branch name from merge commit message.

        Args:
            merge_commit: Merge commit to extract from
            full_hash_map: Map of short to full hashes

        Returns:
            Extracted branch name or None
        """
        try:
            merge_commit_full_hash = full_hash_map.get(merge_commit.hash)
            if merge_commit_full_hash and self.repo:
                merge_commit_obj = self.repo.commit(merge_commit_full_hash)
                merge_message = merge_commit_obj.message

                # Various merge message formats
                patterns = [
                    r"Merge branch ['\"]([^'\"]+)['\"]",           # Git standard
                    r"Merge branch ['\"]([^'\"]+)['\"] into",      # With target
                    r"Merge pull request #\d+ from [^/]+/([^\s]+)", # GitHub
                    r"Merged in ([^\s\(]+)",                       # Bitbucket
                    r"Merge remote-tracking branch ['\"]origin/([^'\"]+)['\"]", # Remote merge
                ]

                for pattern in patterns:
                    match = re.search(pattern, merge_message)
                    if match:
                        return match.group(1)
        except Exception as e:
            logger.debug(f"Failed to extract branch name from merge commit {merge_commit.hash}: {e}")
        return None

    def make_color_pale(self, color: str, blend_type: str = "merge") -> str:
        """Create paler variant of color for merge branches using HSL manipulation.

        Args:
            color: Color to make pale (hex format)
            blend_type: Type of blending ("remote" or "merge")

        Returns:
            Paler color in hex format
        """
        if not color or color == 'unknown':
            return '#CCCCCC'

        if color.startswith('#'):
            try:
                # Convert hex to RGB
                hex_color = color.lstrip('#')
                if len(hex_color) == 6:
                    r = int(hex_color[0:2], 16) / 255.0
                    g = int(hex_color[2:4], 16) / 255.0
                    b = int(hex_color[4:6], 16) / 255.0

                    # Convert RGB to HSL
                    h, l, s = colorsys.rgb_to_hls(r, g, b)

                    # Apply fading according to type
                    if blend_type == "remote":
                        # Remote: milder fading to preserve distinguishability
                        s = s * 0.8  # Reduce saturation to 80% of original
                        l = min(0.9, l + 0.15)  # Increase lightness by 15%
                    elif blend_type == "merge":
                        # Merge: strong fading - least saturated of all
                        s = s * 0.6  # Reduce saturation to 60% of original (less than remote)
                        l = min(0.85, l + 0.20)  # Significantly increase lightness by 20%
                    else:
                        # Fallback to merge behavior
                        s = s * 0.6
                        l = min(0.85, l + 0.20)

                    # Convert back to RGB
                    r, g, b = colorsys.hls_to_rgb(h, l, s)

                    # Convert to hex
                    r = int(r * 255)
                    g = int(g * 255)
                    b = int(b * 255)

                    return f'#{r:02x}{g:02x}{b:02x}'
            except Exception as e:
                logger.warning(f"Failed to convert color {color} to pale variant: {e}")
                pass

        # Fallback to light gray
        return "#CCCCCC"
