"""BranchAnalyzer - handles branch analysis and relationship detection."""

from typing import Dict, Set
from git import Repo
from utils.logging_config import get_logger

logger = get_logger(__name__)


class BranchAnalyzer:
    """Handles analysis of branches and their relationships."""

    def __init__(self, repo: Repo):
        """Initialize BranchAnalyzer.

        Args:
            repo: GitPython Repo object
        """
        self.repo = repo

    def build_commit_branch_map(self) -> Dict[str, str]:
        """Build map of commit_hash -> branch_name for fast lookup.

        Returns:
            Dictionary mapping commit hash to branch name
        """
        commit_to_branch = {}

        try:
            # First process main branches with priority
            main_branches = ['main', 'master']
            other_branches = []

            # Work with local heads (branches)
            for head in self.repo.heads:
                branch_name = head.name
                if branch_name in main_branches:
                    # Process main branches immediately
                    try:
                        for commit in self.repo.iter_commits(head):
                            commit_to_branch[commit.hexsha] = branch_name
                    except Exception as e:
                        logger.warning(f"Failed to iterate commits for branch {branch_name}: {e}")
                        continue
                else:
                    other_branches.append((head, branch_name))

            # Then process other branches, but only commits that don't have a branch yet
            for head, branch_name in other_branches:
                try:
                    for commit in self.repo.iter_commits(head):
                        commit_hash = commit.hexsha
                        if commit_hash not in commit_to_branch:
                            commit_to_branch[commit_hash] = branch_name
                except Exception as e:
                    logger.warning(f"Failed to iterate commits for branch {branch_name}: {e}")
                    continue

        except Exception:
            pass

        return commit_to_branch

    def build_commit_branch_map_with_remote(self) -> tuple[Dict[str, str], Dict[str, str]]:
        """Build maps of commit_hash -> branch_name for local and remote branches.

        Returns:
            Tuple of (local_commit_map, remote_commit_map)
        """
        local_commit_map = {}
        remote_commit_map = {}

        try:
            # 1. Prioritize local branches
            main_branches = ['main', 'master']
            other_local_branches = []

            for head in self.repo.heads:
                branch_name = head.name
                if branch_name in main_branches:
                    try:
                        for commit in self.repo.iter_commits(head):
                            local_commit_map[commit.hexsha] = branch_name
                    except Exception as e:
                        logger.warning(f"Failed to iterate commits for main branch {branch_name}: {e}")
                        continue
                else:
                    other_local_branches.append((head, branch_name))

            for head, branch_name in other_local_branches:
                try:
                    for commit in self.repo.iter_commits(head):
                        if commit.hexsha not in local_commit_map:
                            local_commit_map[commit.hexsha] = branch_name
                except Exception as e:
                    logger.warning(f"Failed to iterate commits for local branch {branch_name}: {e}")
                    continue

            # 2. Remote branches - only for commits without local branch
            try:
                remote_refs = list(self.repo.remote().refs)
                for remote_ref in remote_refs:
                    # Skip HEAD ref
                    if remote_ref.name.endswith('/HEAD'):
                        continue

                    try:
                        for commit in self.repo.iter_commits(remote_ref):
                            if commit.hexsha not in local_commit_map:
                                remote_commit_map[commit.hexsha] = remote_ref.name
                    except Exception as e:
                        logger.warning(f"Failed to iterate commits for remote ref {remote_ref.name}: {e}")
                        continue
            except Exception as e:
                # If remote doesn't exist, continue with local branches only
                logger.debug(f"Failed to access remote refs: {e}")
                pass

        except Exception as e:
            logger.warning(f"Failed to build commit-branch map with remote: {e}")
            pass

        return local_commit_map, remote_commit_map

    def build_branch_availability_map(self, include_remote: bool = True) -> Dict[str, str]:
        """Build map of branch_name -> availability (local_only/remote_only/both).

        Args:
            include_remote: Whether to include remote branches

        Returns:
            Dictionary mapping branch name to availability status
        """
        local_branches = set()
        remote_branches = set()

        # Get local branches
        try:
            for head in self.repo.heads:
                local_branches.add(head.name)
        except Exception as e:
            logger.warning(f"Failed to get local branches: {e}")
            pass

        # Get remote branches only if requested
        if include_remote:
            try:
                remote_refs = list(self.repo.remote().refs)
                for remote_ref in remote_refs:
                    if remote_ref.name.endswith('/HEAD'):
                        continue
                    # Extract branch name from origin/branch_name
                    if remote_ref.name.startswith('origin/'):
                        branch_name = remote_ref.name[7:]  # Remove "origin/"
                        remote_branches.add(branch_name)
            except Exception as e:
                logger.debug(f"Failed to get remote branches: {e}")
                pass

        # Create availability map
        availability_map = {}
        all_branches = local_branches | remote_branches

        for branch in all_branches:
            if branch in local_branches and branch in remote_branches:
                availability_map[branch] = 'both'
            elif branch in local_branches:
                availability_map[branch] = 'local_only'
            elif branch in remote_branches:
                availability_map[branch] = 'remote_only'

        return availability_map

    def detect_branch_divergence(self, branch_name: str) -> Dict:
        """Detect divergence between local and remote branch.

        Args:
            branch_name: Name of branch to check

        Returns:
            Dictionary with divergence information
        """
        try:
            # Get local and remote references
            local_head = None
            remote_head = None

            # Local branch
            try:
                local_head = self.repo.heads[branch_name].commit
            except Exception as e:
                logger.debug(f"Failed to get local head for branch {branch_name}: {e}")
                pass

            # Remote branch
            try:
                remote_head = self.repo.remotes.origin.refs[branch_name].commit
            except Exception as e:
                logger.debug(f"Failed to get remote head for branch {branch_name}: {e}")
                pass

            # If one doesn't exist, no divergence
            if not local_head or not remote_head:
                return {
                    'diverged': False,
                    'local_head': local_head,
                    'remote_head': remote_head,
                    'merge_base': None
                }

            # If they point to same commit, no divergence
            if local_head == remote_head:
                return {
                    'diverged': False,
                    'local_head': local_head,
                    'remote_head': remote_head,
                    'merge_base': local_head
                }

            # Find merge base
            merge_bases = self.repo.merge_base(local_head, remote_head)
            if not merge_bases:
                # No common ancestor - divergence definitely exists
                return {
                    'diverged': True,
                    'local_head': local_head,
                    'remote_head': remote_head,
                    'merge_base': None
                }

            merge_base = merge_bases[0]

            # Check if they actually diverged (both are ahead of merge base)
            local_is_ahead = local_head != merge_base
            remote_is_ahead = remote_head != merge_base

            return {
                'diverged': local_is_ahead and remote_is_ahead,
                'local_head': local_head,
                'remote_head': remote_head,
                'merge_base': merge_base,
                'local_ahead': local_is_ahead,
                'remote_ahead': remote_is_ahead
            }

        except Exception as e:
            return {
                'diverged': False,
                'local_head': None,
                'remote_head': None,
                'merge_base': None,
                'error': str(e)
            }

    def get_all_branch_names(self) -> Set[str]:
        """Get all branch names (local and remote).

        Returns:
            Set of all branch names
        """
        all_branch_names = set()

        # Get local branches
        if hasattr(self.repo, 'heads'):
            for head in self.repo.heads:
                all_branch_names.add(head.name)

        # Get remote branches
        if hasattr(self.repo, 'remotes') and self.repo.remotes:
            try:
                for ref in self.repo.remotes.origin.refs:
                    if not ref.name.endswith('/HEAD'):
                        branch_name = ref.name.replace('origin/', '')
                        all_branch_names.add(branch_name)
            except Exception as e:
                logger.debug(f"Failed to fetch remote refs: {e}")
                pass

        return all_branch_names
