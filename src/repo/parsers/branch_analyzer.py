"""BranchAnalyzer - handles branch analysis and relationship detection."""

import tempfile
from typing import Dict, Set, Tuple
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

    MAIN_BRANCHES = ('main', 'master')

    def _rev_list_new_commits(self, tip: str, exclude) -> list:
        """Vrátí hashe commitů dosažitelných z `tip`, ale ne z žádného refu v `exclude`.

        Odpovídá `git rev-list tip --not exclude...`; revize se předávají přes
        stdin, aby příkazová řádka nepřetekla ani u stovek větví.
        """
        spec = "".join(f"{line}\n" for line in [tip] + [f"^{ref}" for ref in exclude])
        with tempfile.TemporaryFile() as stdin:
            stdin.write(spec.encode('utf-8'))
            stdin.seek(0)
            output = self.repo.git.rev_list('--stdin', istream=stdin)
        return output.split() if output else []

    def _assign_commits_to_refs(self, refs, exclude=(), commit_map=None) -> Dict[str, str]:
        """Přiřadí commity refům: každý commit dostane první ref (v daném pořadí), ze kterého je dosažitelný.

        Místo průchodu celou historií pro každou větev (N větví × celá historie
        přes GitPython objekty) se pro každou větev vyžádají jen commity, které
        ještě nepokrývá žádná dříve zpracovaná větev. Celkový objem dat je tak
        úměrný počtu commitů, ne počtu větví × commitů.

        Args:
            refs: Seznam (ref_pro_git, jméno_větve) v pořadí priority
            exclude: Refy, jejichž commity se nepřiřazují vůbec (např. lokální větve při mapování remote)
            commit_map: Mapa, do které se přidává (výchozí nová)
        """
        commit_map = {} if commit_map is None else commit_map
        processed = list(exclude)
        for ref, branch_name in refs:
            try:
                for sha in self._rev_list_new_commits(ref, processed):
                    commit_map.setdefault(sha, branch_name)
                processed.append(ref)
            except Exception as e:
                logger.warning(f"Failed to list commits for branch {branch_name}: {e}")
        return commit_map

    def _local_refs(self):
        refs = []
        for head in self.repo.heads:
            refs.append((head.path, head.name))
        # Jen přesná jména main/master mají přednost (ne feature/main)
        main = [r for r in refs if r[1] in self.MAIN_BRANCHES]
        return main + [r for r in refs if r[1] not in self.MAIN_BRANCHES]

    def _remote_refs(self):
        refs = []
        for remote_ref in self.repo.remote().refs:
            if remote_ref.name.endswith('/HEAD'):
                continue
            refs.append((remote_ref.path, remote_ref.name))
        main = [r for r in refs if r[1].split('/', 1)[-1] in self.MAIN_BRANCHES]
        return main + [r for r in refs if r not in main]

    def build_commit_branch_map(self) -> Dict[str, str]:
        """Build map of commit_hash -> branch_name for fast lookup.

        Commit patří první větvi, ze které je dosažitelný; main/master mají přednost.

        Returns:
            Dictionary mapping full commit hash to branch name
        """
        try:
            return self._assign_commits_to_refs(self._local_refs())
        except Exception as e:
            logger.warning(f"Failed to build commit-branch map: {e}")
            return {}

    def build_commit_branch_map_with_remote(self) -> Tuple[Dict[str, str], Dict[str, str]]:
        """Build maps of commit_hash -> branch_name for local and remote branches.

        Lokální větve mají přednost; do remote mapy jdou jen commity, které
        nejsou v žádné lokální větvi (u remote refů má přednost origin/main|master).

        Returns:
            Tuple of (local_commit_map, remote_commit_map)
        """
        local_commit_map = {}
        remote_commit_map = {}

        try:
            local_refs = self._local_refs()
            local_commit_map = self._assign_commits_to_refs(local_refs)

            try:
                remote_refs = self._remote_refs()
            except Exception as e:
                # If remote doesn't exist, continue with local branches only
                logger.debug(f"Failed to access remote refs: {e}")
                remote_refs = []

            remote_commit_map = self._assign_commits_to_refs(
                remote_refs, exclude=[ref for ref, _ in local_refs]
            )
        except Exception as e:
            logger.warning(f"Failed to build commit-branch map with remote: {e}")

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
