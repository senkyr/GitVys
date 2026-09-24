"""MergeDetector - handles detection and analysis of merge branches."""

import colorsys
import heapq
import re
from itertools import count
from typing import List, Dict, Set, Optional
from git import Repo
from utils.data_structures import Commit, MergeBranch
from utils.logging_config import get_logger
from visualization.colors import get_branch_color

logger = get_logger(__name__)


class MergeDetector:
    """Handles detection and analysis of merge branches.

    Vše se počítá v paměti nad už načtenými commity (graf rodičů + data).
    Dřív se pro každý merge commit spouštěl `git merge-base` a pro každý znovu
    procházela first-parent linie všech větví přes GitPython, takže repozitář
    se stovkami mergů se načítal desítky sekund.
    """

    # Formáty zpráv merge commitů, ze kterých jde vyčíst jméno slučované větve
    MERGE_MESSAGE_PATTERNS = [
        r"Merge branch ['\"]([^'\"]+)['\"]",                        # Git standard (i "... into X")
        r"Merge pull request #\d+ from [^/]+/(\S+)",                 # GitHub
        r"Merged in ([^\s(]+)",                                      # Bitbucket
        r"Merge remote-tracking branch ['\"]origin/([^'\"]+)['\"]",  # Remote merge
    ]

    def __init__(self, repo: Repo, commits: List[Commit]):
        """Initialize MergeDetector.

        Args:
            repo: GitPython Repo object (používá se jen pro seznam lokálních větví)
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
        used_colors = {commit.branch_color for commit in self.commits if commit.branch_color}

        # First-parent linie všech větví (jednou, ne pro každý merge zvlášť)
        commits_in_branches_with_head = self.get_commits_in_branches_with_head(commit_map)

        for merge_commit in self.commits:
            if len(merge_commit.parents) < 2:
                continue
            try:
                # First parent = main branch, second parent = merged branch
                main_parent_hash = merge_commit.parents[0]
                merge_parent_hash = merge_commit.parents[1]

                if merge_parent_hash not in commit_map or main_parent_hash not in commit_map:
                    continue

                # Find branch point (common ancestor)
                branch_point_hash = self.find_merge_base(merge_parent_hash, main_parent_hash, commit_map)
                if not branch_point_hash:
                    continue

                # Trace commits in merge branch and drop those on first-parent line of some branch
                merge_branch_commits = [
                    c for c in self.trace_merge_branch_commits(merge_parent_hash, branch_point_hash, commit_map)
                    if c not in commits_in_branches_with_head
                ]
                if not merge_branch_commits:
                    continue

                # Color from merged branch name in commit message; neutral light gray if unknown
                branch_name = self.extract_branch_name_from_merge(merge_commit)
                original_color = get_branch_color(branch_name, used_colors) if branch_name else '#999999'

                merge_branches.append(MergeBranch(
                    branch_point_hash=branch_point_hash,
                    merge_point_hash=merge_commit.hash,
                    commits_in_branch=merge_branch_commits,
                    virtual_branch_name=f"merge-{merge_commit.hash}",
                    original_color=original_color
                ))
            except Exception as e:
                logger.debug(f"Failed to analyze merge commit {merge_commit.hash}: {e}")
                continue

        return merge_branches

    @staticmethod
    def _timestamp(commit: Optional[Commit]) -> float:
        try:
            return commit.date.timestamp()
        except Exception:
            return 0.0

    def find_merge_base(self, hash_a: str, hash_b: str, commit_map: Dict[str, Commit]) -> Optional[str]:
        """Najde nejlepšího společného předka dvou commitů (jako `git merge-base`).

        Algoritmus "paint down to common" z Gitu: z obou commitů se jde po
        rodičích od nejnovějších, značí se dosažitelnost z A a z B; první commit
        dosažitelný z obou je merge base. Jakmile ve frontě zbývají jen commity
        pod nalezeným předkem, hledání končí - neprochází se celá historie.

        Returns:
            Hash společného předka nebo None (nesouvisející historie)
        """
        if hash_a == hash_b:
            return hash_a
        if hash_a not in commit_map or hash_b not in commit_map:
            return None

        FROM_A, FROM_B, STALE = 1, 2, 4
        flags = {hash_a: FROM_A, hash_b: FROM_B}
        order = count()
        heap = []
        nonstale_in_queue = 0

        def push(commit_hash: str):
            nonlocal nonstale_in_queue
            stale = bool(flags[commit_hash] & STALE)
            if not stale:
                nonstale_in_queue += 1
            timestamp = self._timestamp(commit_map.get(commit_hash))
            heapq.heappush(heap, (-timestamp, next(order), commit_hash, stale))

        push(hash_a)
        push(hash_b)
        result = None

        while heap and nonstale_in_queue > 0:
            _, _, commit_hash, pushed_stale = heapq.heappop(heap)
            if not pushed_stale:
                nonstale_in_queue -= 1

            current = flags[commit_hash]
            if current & (FROM_A | FROM_B) == (FROM_A | FROM_B) and not current & STALE:
                if result is None:
                    result = commit_hash
                current |= STALE
                flags[commit_hash] = current

            commit = commit_map.get(commit_hash)
            if not commit:
                continue
            for parent_hash in commit.parents:
                parent_flags = flags.get(parent_hash, 0)
                if parent_flags & current == current:
                    continue
                flags[parent_hash] = parent_flags | current
                push(parent_hash)

        return result

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

        for commit in commits:
            # Don't recolor commit if already remapped to merge branch (first merge wins)
            if commit.hash in commit_to_merge_branch and not getattr(commit, 'is_merge_branch', False):
                merge_branch = commit_to_merge_branch[commit.hash]
                commit.branch = merge_branch.virtual_branch_name
                commit.branch_color = self.make_color_pale(merge_branch.original_color, blend_type="merge")
                commit.is_merge_branch = True

    def trace_merge_branch_commits(self, merge_parent_hash: str, branch_point_hash: str,
                                   commit_map: Dict[str, Commit]) -> List[str]:
        """Trace backwards commits in merge branch from merge parent to branch point.

        Args:
            merge_parent_hash: Hash of merge parent commit
            branch_point_hash: Hash of branch point commit
            commit_map: Map of commit hash to Commit object

        Returns:
            List of commit hashes in merge branch (newest first)
        """
        merge_branch_commits = []
        current = merge_parent_hash
        visited = set()

        while current and current != branch_point_hash and current not in visited:
            visited.add(current)
            commit = commit_map.get(current)
            if not commit:
                break
            merge_branch_commits.append(current)
            # Continue to first parent (linear path)
            current = commit.parents[0] if commit.parents else None

        return merge_branch_commits

    def get_commits_in_branches_with_head(self, commit_map: Optional[Dict[str, Commit]] = None) -> Set[str]:
        """Get all commits in main line (first-parent path) of local branches.

        Args:
            commit_map: Map hash -> Commit (default: built from self.commits)

        Returns:
            Set of commit hashes on first-parent lines of local branch heads
        """
        if commit_map is None:
            commit_map = {commit.hash: commit for commit in self.commits}

        result = set()
        if not self.repo:
            return result
        try:
            heads = list(self.repo.heads)
        except Exception as e:
            logger.warning(f"Failed to get branches with HEAD: {e}")
            return result

        for branch_head in heads:
            try:
                current = branch_head.commit.hexsha
            except Exception as e:
                logger.warning(f"Failed to resolve branch {getattr(branch_head, 'name', '?')}: {e}")
                continue
            # Větve sdílí historii: jakmile narazíme na už viděný commit, zbytek je taky viděný
            while current and current not in result:
                result.add(current)
                commit = commit_map.get(current)
                current = commit.parents[0] if commit and commit.parents else None
        return result

    def extract_branch_name_from_merge(self, merge_commit: Commit, full_hash_map: Dict[str, str] = None) -> Optional[str]:
        """Extract branch name from merge commit message (first line).

        Args:
            merge_commit: Merge commit to extract from
            full_hash_map: Unused, kept for backward compatibility

        Returns:
            Extracted branch name or None
        """
        message = merge_commit.message or ""
        for pattern in self.MERGE_MESSAGE_PATTERNS:
            match = re.search(pattern, message)
            if match:
                return match.group(1)
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
                hex_color = color.lstrip('#')
                if len(hex_color) == 6:
                    r = int(hex_color[0:2], 16) / 255.0
                    g = int(hex_color[2:4], 16) / 255.0
                    b = int(hex_color[4:6], 16) / 255.0

                    h, l, s = colorsys.rgb_to_hls(r, g, b)

                    if blend_type == "remote":
                        # Remote: milder fading to preserve distinguishability
                        s = s * 0.8
                        l = min(0.9, l + 0.15)
                    else:
                        # Merge (and fallback): strong fading - least saturated of all
                        s = s * 0.6
                        l = min(0.85, l + 0.20)

                    r, g, b = colorsys.hls_to_rgb(h, l, s)
                    return f'#{int(r * 255):02x}{int(g * 255):02x}{int(b * 255):02x}'
            except Exception as e:
                logger.warning(f"Failed to convert color {color} to pale variant: {e}")

        # Fallback to light gray
        return "#CCCCCC"
