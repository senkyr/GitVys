from datetime import datetime, timezone
from typing import List, Dict, Optional
from git import Repo, InvalidGitRepositoryError
from utils.data_structures import Commit, Branch, BranchFlag, Tag, MergeBranch
from utils.logging_config import get_logger
from utils.translations import get_translation_manager
from repo.head import HeadState, read_head_state
from repo.parsers import CommitParser, BranchAnalyzer, TagParser
from repo.analyzers import MergeDetector
from visualization.colors import get_branch_color

logger = get_logger(__name__)


class GitRepository:
    """Facade for Git repository operations that delegates to specialized components."""

    def __init__(self, repo_path: str):
        self.repo_path = repo_path
        self.repo: Optional[Repo] = None
        self.commits: List[Commit] = []
        self.branches: Dict[str, Branch] = {}
        self.merge_branches: List[MergeBranch] = []  # Posledně detekované merge větve
        self.branch_names: set = set()  # Skutečné větve (bez virtuálních merge-*) pro statistiky
        self.head: HeadState = HeadState()  # Stav HEAD při posledním načtení commitů
        self.flag_columns: int = 1  # Nejvíc vlaječek větví na jednom řádku grafu (pro šířku sloupce)

        # Component instances (initialized in load_repository)
        self.commit_parser: Optional[CommitParser] = None
        self.branch_analyzer: Optional[BranchAnalyzer] = None
        self.tag_parser: Optional[TagParser] = None
        self.merge_detector: Optional[MergeDetector] = None

    def load_repository(self) -> bool:
        try:
            self.repo = Repo(self.repo_path)

            # Initialize components
            self.commit_parser = CommitParser(self.repo)
            self.branch_analyzer = BranchAnalyzer(self.repo)
            self.tag_parser = TagParser(self.repo)

            return True
        except InvalidGitRepositoryError:
            return False

    def parse_commits(self) -> List[Commit]:
        """Parse commits from local branches only."""
        if not self.repo:
            return []

        self.head = read_head_state(self.repo)

        # Delegate to components
        commit_to_branch = self.branch_analyzer.build_commit_branch_map()
        commit_to_tags = self.tag_parser.build_commit_tag_map()
        branch_availability = self.branch_analyzer.build_branch_availability_map(include_remote=False)
        self.branch_names = set(branch_availability)

        # Prepare color tracking
        used_colors = set()
        branch_colors = {}

        # Delegate commit parsing to CommitParser
        commits = self.commit_parser.parse_commits(
            commit_to_branch, commit_to_tags, branch_availability, branch_colors, used_colors
        )

        # Add uncommitted changes
        uncommitted_info = self.get_uncommitted_changes()
        uncommitted_commits = self._create_uncommitted_commits(
            uncommitted_info, commits, branch_colors, used_colors
        )
        all_commits = uncommitted_commits + commits

        # Delegate merge detection to MergeDetector
        self.merge_detector = MergeDetector(self.repo, commits)
        merge_branches = self.merge_detector.detect_merge_branches()
        self.merge_branches = merge_branches
        self.merge_detector.apply_merge_branch_styling(all_commits, merge_branches)
        self._attach_ref_flags(all_commits, branch_colors, used_colors, include_remote=False)

        all_commits.sort(key=lambda c: c.date.timestamp(), reverse=True)

        self.commits = all_commits
        return all_commits

    def parse_commits_with_remote(self) -> List[Commit]:
        """Parse commits including remote branches with divergence support."""
        if not self.repo:
            return []

        self.head = read_head_state(self.repo)

        # Delegate to components
        local_commit_map, remote_commit_map = self.branch_analyzer.build_commit_branch_map_with_remote()
        commit_to_tags = self.tag_parser.build_commit_tag_map_with_remote()
        branch_availability = self.branch_analyzer.build_branch_availability_map()

        # Detect divergences for all branches
        all_branch_names = self.branch_analyzer.get_all_branch_names()
        self.branch_names = set(all_branch_names)
        branch_divergences = {}
        for branch_name in all_branch_names:
            branch_divergences[branch_name] = self.branch_analyzer.detect_branch_divergence(branch_name)
        if self.head.is_detached:
            # Odpojený HEAD se v grafu vede jako místní "větev" bez protějšku na remote
            branch_divergences[self.head.branch_label] = {
                'diverged': False,
                'local_head': self.repo.head.commit,
                'remote_head': None,
                'merge_base': None,
            }

        # Prepare color tracking
        used_colors = set()
        branch_colors = {}

        # Delegate commit parsing to CommitParser
        commits = self.commit_parser.parse_commits_with_remote(
            local_commit_map, remote_commit_map, commit_to_tags,
            branch_availability, branch_divergences, branch_colors, used_colors
        )

        # Add uncommitted changes
        uncommitted_info = self.get_uncommitted_changes()
        uncommitted_commits = self._create_uncommitted_commits(
            uncommitted_info, commits, branch_colors, used_colors
        )
        all_commits = uncommitted_commits + commits

        # Delegate merge detection to MergeDetector
        self.merge_detector = MergeDetector(self.repo, commits)
        merge_branches = self.merge_detector.detect_merge_branches()
        self.merge_branches = merge_branches
        self.merge_detector.apply_merge_branch_styling(all_commits, merge_branches)
        self._attach_ref_flags(all_commits, branch_colors, used_colors, include_remote=True)

        all_commits.sort(key=lambda c: c.date.timestamp(), reverse=True)

        self.commits = all_commits
        return all_commits

    @staticmethod
    def _clean_branch_name(branch_name: str) -> str:
        return branch_name[7:] if branch_name.startswith('origin/') else branch_name

    def _ref_tips(self, include_remote: bool):
        """Vrátí (místní, vzdálené) větve jako mapy jméno -> hash commitu, na který ukazují."""
        local_tips: Dict[str, str] = {}
        remote_tips: Dict[str, str] = {}

        for head in self.repo.heads:
            try:
                local_tips[head.name] = head.commit.hexsha
            except Exception as e:
                logger.warning(f"Failed to resolve branch {getattr(head, 'name', '?')}: {e}")
        if self.head.is_detached:
            local_tips[self.head.branch_label] = self.head.commit

        if include_remote:
            try:
                remote_refs = list(self.repo.remote().refs)
            except Exception as e:
                logger.debug(f"Failed to access remote refs: {e}")
                remote_refs = []
            for ref in remote_refs:
                if ref.name.endswith('/HEAD'):
                    continue
                try:
                    remote_tips[self._clean_branch_name(ref.name)] = ref.commit.hexsha
                except Exception as e:
                    logger.warning(f"Failed to resolve remote branch {ref.name}: {e}")

        return local_tips, remote_tips

    def _attach_ref_flags(self, commits: List[Commit], branch_colors: Dict[str, str],
                          used_colors: set, include_remote: bool) -> None:
        """Doplní vlaječky větví, které by v grafu jinak nebyly vidět, a označí commit pod HEAD.

        Commit patří v grafu jedné větvi a vlaječku větve nese její poslední
        commit. Větev, jejíž poslední commit patří jiné větvi (čerstvě založená,
        sloučená fast-forwardem, pozadu za main), tak žádnou vlaječku neměla
        a v grafu nebyla vidět. Takové větve dostanou vlaječku navíc
        (``Commit.extra_flags``) u commitu, na který ukazují.

        Volat až po detekci mergů: ta commitům sloučených větví mění ``branch``
        na virtuální ``merge-*``, a ty vlastní vlaječku nekreslí.
        """
        self.flag_columns = 1
        try:
            by_hash = {commit.hash: commit for commit in commits if not commit.is_uncommitted}

            if self.head.commit in by_hash:
                by_hash[self.head.commit].head_branch = self.head.branch_label

            local_tips, remote_tips = self._ref_tips(include_remote)

            # (hash, jméno větve) -> kde na commit ukazuje ("local", "remote")
            uncovered: Dict[tuple, set] = {}
            commits_with_own_flag = set()
            for kind, tips in (("local", local_tips), ("remote", remote_tips)):
                for name, tip in tips.items():
                    commit = by_hash.get(tip)
                    if commit is None:
                        continue
                    if self._clean_branch_name(commit.branch) == name:
                        commits_with_own_flag.add(tip)  # Vlaječku nese commit sám
                    else:
                        uncovered.setdefault((tip, name), set()).add(kind)

            # Místní větve napřed (podle abecedy), pak jen vzdálené
            for (tip, name), kinds in sorted(uncovered.items(), key=lambda item: ("local" not in item[1], item[0][1])):
                color = branch_colors.get(name) or branch_colors.get(f"origin/{name}")
                if color is None:
                    color = branch_colors[name] = get_branch_color(name, used_colors)
                availability = "both" if len(kinds) == 2 else ("local_only" if "local" in kinds else "remote_only")
                by_hash[tip].extra_flags.append(BranchFlag(name=name, color=color, availability=availability))

            self.flag_columns = max(
                [1] + [(commit.hash in commits_with_own_flag) + len(commit.extra_flags) for commit in by_hash.values()]
            )
        except Exception as e:
            logger.warning(f"Failed to attach branch flags: {e}")

    def get_uncommitted_changes(self) -> Dict[str, any]:
        """Detekuje uncommitted změny (staged a working directory)."""
        if not self.repo:
            return {"has_changes": False}

        try:
            # Získat status repozitáře
            status = self.repo.git.status(porcelain=True)

            if not status.strip():
                return {"has_changes": False}

            # Analyzovat status výstup
            staged_files = []
            working_files = []

            # Ne status.strip(): porcelain řádek začíná mezerou (" M soubor"),
            # strip by u prvního řádku posunul sloupce a změnu vydával za staged
            for line in status.splitlines():
                if len(line) >= 3:
                    staged_status = line[0]
                    working_status = line[1]
                    filename = line[3:]

                    if line.startswith('??'):
                        # Nesledovaný soubor - není ve stage, jen v pracovní složce
                        working_files.append(filename)
                        continue

                    if staged_status != ' ':
                        staged_files.append(filename)
                    if working_status != ' ':
                        working_files.append(filename)

            has_staged = len(staged_files) > 0
            has_working = len(working_files) > 0

            if not has_staged and not has_working:
                return {"has_changes": False}

            # Určit typ změn
            if has_staged and has_working:
                uncommitted_type = "both"
                change_desc = f"{len(staged_files)} staged, {len(working_files)} working"
            elif has_staged:
                uncommitted_type = "staged"
                change_desc = f"{len(staged_files)} staged"
            else:
                uncommitted_type = "working"
                change_desc = f"{len(working_files)} working"

            return {
                "has_changes": True,
                "uncommitted_type": uncommitted_type,
                "staged_files": staged_files,
                "working_files": working_files,
                "change_description": change_desc
            }

        except Exception as e:
            return {"has_changes": False, "error": str(e)}


    def _create_uncommitted_commits(self, uncommitted_info: Dict[str, any], existing_commits: List[Commit] = None,
                                    branch_colors: Dict[str, str] = None, used_colors: set = None) -> List[Commit]:
        """Vytvoří pseudo-commit (WIP) pro rozpracované změny nad commitem, na kterém stojí HEAD.

        Rodičem je commit pod HEAD, ne "nejnovější commit se jménem aktuální
        větve": čerstvě založená větev žádný vlastní commit nemá (její poslední
        commit patří v grafu větvi, ze které vznikla) a WIP by zůstal viset bez
        spojnice. Při odpojeném HEAD se WIP vede pod jménem ``DETACHED_HEAD``.

        Args:
            uncommitted_info: Výsledek get_uncommitted_changes()
            existing_commits: Načtené commity (výchozí self.commits)
            branch_colors: Barvy větví přidělené při načítání (doplní se o novou větev)
            used_colors: Už použité barvy (doplní se)
        """
        if not uncommitted_info.get("has_changes", False):
            return []

        try:
            head = read_head_state(self.repo)
            current_branch = head.branch_label

            commits_to_search = existing_commits if existing_commits is not None else self.commits
            head_commit = None
            branch_color = None
            for commit in commits_to_search:
                if commit.is_uncommitted:
                    continue
                if commit.hash == head.commit:
                    head_commit = commit
                if branch_color is None and commit.branch == current_branch:
                    branch_color = commit.branch_color

            if branch_color is None:
                # Větev bez vlastního commitu: dostane svou barvu, jako ji dostane po prvním commitu
                branch_colors = {} if branch_colors is None else branch_colors
                if current_branch not in branch_colors:
                    if used_colors is None:
                        used_colors = {commit.branch_color for commit in commits_to_search}
                    branch_colors[current_branch] = get_branch_color(current_branch, used_colors)
                branch_color = branch_colors[current_branch]

            uncommitted_type = uncommitted_info["uncommitted_type"]
            staged_files = uncommitted_info.get("staged_files", [])
            working_files = uncommitted_info.get("working_files", [])

            # Počet dotčených souborů (bez duplikátů) v jazyce rozhraní
            file_count = len(set(staged_files + working_files))
            description = f"{file_count} {get_translation_manager().get_plural(file_count, 'file')}"

            now = datetime.now(timezone.utc)

            return [Commit(
                # Zvláštní hash: nesmí se splést s hashem skutečného commitu
                hash=f"uncommit_{current_branch}_{int(now.timestamp())}"[:8],
                message="WIP (Work In Progress)",
                short_message="WIP (Work In Progress)",
                author="",
                author_short="",
                author_email="",
                date=now,
                date_relative="",
                date_short="",
                parents=[head_commit.hash] if head_commit else [],
                branch=current_branch,
                branch_color=branch_color,
                is_uncommitted=True,
                uncommitted_type=uncommitted_type,
                description=description,
                description_short=description
            )]

        except Exception as e:
            # Graf bez WIP je lepší než žádný graf, ale chyba nesmí zmizet beze stopy
            logger.warning(f"Failed to create WIP commit: {e}")
            return []

    def get_merge_branches(self) -> List[MergeBranch]:
        """Vrátí posledně detekované merge větve."""
        return self.merge_branches

    def get_repository_stats(self) -> Dict[str, int]:
        if not self.repo or not self.commits:
            return {"authors": 0, "branches": 0, "commits": 0, "tags": 0, "local_tags": 0, "remote_tags": 0}

        # WIP pseudo-commit není commit a nemá autora
        real_commits = [commit for commit in self.commits if not commit.is_uncommitted]

        authors = set()
        all_tags = set()
        local_tags = set()
        remote_tags = set()

        for commit in real_commits:
            authors.add(commit.author)
            for tag in commit.tags:
                all_tags.add(tag.name)
                if tag.is_remote:
                    remote_tags.add(tag.name)
                else:
                    local_tags.add(tag.name)

        # Větve počítat z refů, ne z commit.branch: ten po detekci mergů obsahuje
        # i virtuální větve "merge-<hash>" a sloučené větve v něm naopak chybí.
        branches = self.branch_names or {commit.branch for commit in real_commits}

        return {
            "authors": len(authors),
            "branches": len(branches),
            "commits": len(real_commits),
            "tags": len(all_tags),
            "local_tags": len(local_tags),
            "remote_tags": len(remote_tags)
        }
