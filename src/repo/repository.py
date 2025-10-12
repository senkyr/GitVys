from datetime import datetime, timezone
from typing import List, Dict, Optional
from git import Repo, InvalidGitRepositoryError
from utils.data_structures import Commit, Branch, Tag, MergeBranch
from utils.logging_config import get_logger
from repo.parsers import CommitParser, BranchAnalyzer, TagParser
from repo.analyzers import MergeDetector

logger = get_logger(__name__)


class GitRepository:
    """Facade for Git repository operations that delegates to specialized components."""

    def __init__(self, repo_path: str):
        self.repo_path = repo_path
        self.repo: Optional[Repo] = None
        self.commits: List[Commit] = []
        self.branches: Dict[str, Branch] = {}
        self.merge_branches: List[MergeBranch] = []  # Posledně detekované merge větve

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

        # Delegate to components
        commit_to_branch = self.branch_analyzer.build_commit_branch_map()
        commit_to_tags = self.tag_parser.build_commit_tag_map()
        branch_availability = self.branch_analyzer.build_branch_availability_map(include_remote=False)

        # Prepare color tracking
        used_colors = set()
        branch_colors = {}

        # Delegate commit parsing to CommitParser
        commits = self.commit_parser.parse_commits(
            commit_to_branch, commit_to_tags, branch_availability, branch_colors, used_colors
        )

        # Add uncommitted changes
        uncommitted_info = self.get_uncommitted_changes()
        uncommitted_commits = self._create_uncommitted_commits(uncommitted_info, commits)
        all_commits = uncommitted_commits + commits

        # Delegate merge detection to MergeDetector
        self.merge_detector = MergeDetector(self.repo, commits)
        merge_branches = self.merge_detector.detect_merge_branches()
        self.merge_branches = merge_branches
        self.merge_detector.apply_merge_branch_styling(all_commits, merge_branches)

        all_commits.sort(key=lambda c: c.date, reverse=True)

        self.commits = all_commits
        return all_commits

    def parse_commits_with_remote(self) -> List[Commit]:
        """Parse commits including remote branches with divergence support."""
        if not self.repo:
            return []

        # Delegate to components
        local_commit_map, remote_commit_map = self.branch_analyzer.build_commit_branch_map_with_remote()
        commit_to_tags = self.tag_parser.build_commit_tag_map_with_remote()
        branch_availability = self.branch_analyzer.build_branch_availability_map()

        # Detect divergences for all branches
        all_branch_names = self.branch_analyzer.get_all_branch_names()
        branch_divergences = {}
        for branch_name in all_branch_names:
            branch_divergences[branch_name] = self.branch_analyzer.detect_branch_divergence(branch_name)

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
        uncommitted_commits = self._create_uncommitted_commits(uncommitted_info, commits)
        all_commits = uncommitted_commits + commits

        # Delegate merge detection to MergeDetector
        self.merge_detector = MergeDetector(self.repo, commits)
        merge_branches = self.merge_detector.detect_merge_branches()
        self.merge_branches = merge_branches
        self.merge_detector.apply_merge_branch_styling(all_commits, merge_branches)

        all_commits.sort(key=lambda c: c.date, reverse=True)

        self.commits = all_commits
        return all_commits


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

            for line in status.strip().split('\n'):
                if len(line) >= 3:
                    staged_status = line[0]
                    working_status = line[1]
                    filename = line[3:]

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


    def _create_uncommitted_commits(self, uncommitted_info: Dict[str, any], existing_commits: List[Commit] = None) -> List[Commit]:
        """Vytvoří pseudo-commity pro uncommitted změny pro každou větev."""
        if not uncommitted_info.get("has_changes", False):
            return []

        uncommitted_commits = []
        try:
            # Získat aktuální větev
            current_branch = self.repo.active_branch.name if self.repo.active_branch else "HEAD"

            # Zjistit který typ změn máme
            uncommitted_type = uncommitted_info["uncommitted_type"]
            staged_files = uncommitted_info.get("staged_files", [])
            working_files = uncommitted_info.get("working_files", [])

            # Spočítat celkový počet dotčených souborů (bez duplikátů)
            all_files = set(staged_files + working_files)
            file_count = len(all_files)

            # Vytvořit description podle počtu souborů
            if file_count == 1:
                description = "1 soubor"
            elif file_count < 5:
                description = f"{file_count} soubory"
            else:
                description = f"{file_count} souborů"

            # Vytvořit pseudo-commit pro aktuální větev
            now = datetime.now(timezone.utc)

            # Hash pro uncommitted změny - použijeme speciální prefix
            full_hash = f"uncommit_{current_branch}_{int(now.timestamp())}"
            uncommitted_hash = full_hash[:8]

            # Najít HEAD commit aktuální větve pro parent a barvu
            head_commit = None
            branch_color = '#CCCCCC'  # Defaultní šedá fallback

            # Najít nejnovější commit v aktuální větvi (ne uncommitted)
            commits_to_search = existing_commits if existing_commits else self.commits
            for commit in sorted(commits_to_search, key=lambda c: c.date, reverse=True):
                if commit.branch == current_branch and not getattr(commit, 'is_uncommitted', False):
                    head_commit = commit
                    branch_color = commit.branch_color
                    break

            uncommitted_commit = Commit(
                hash=uncommitted_hash,
                message="WIP (Work In Progress)",
                short_message="WIP (Work In Progress)",
                author="",  # Prázdné pole
                author_short="",  # Prázdné pole
                author_email="",  # Prázdné pole
                date=now,
                date_relative="",  # Prázdné pole
                date_short="",  # Prázdné pole
                parents=[head_commit.hash] if head_commit else [],  # Parent je HEAD commit větve
                branch=current_branch,
                branch_color=branch_color,
                is_uncommitted=True,
                uncommitted_type=uncommitted_type,
                description=description,
                description_short=description
            )

            uncommitted_commits.append(uncommitted_commit)

        except Exception as e:
            # V případě chyby vrátit prázdný seznam
            pass

        return uncommitted_commits

    def get_merge_branches(self) -> List[MergeBranch]:
        """Vrátí posledně detekované merge větve."""
        return self.merge_branches

    def get_repository_stats(self) -> Dict[str, int]:
        if not self.repo or not self.commits:
            return {"authors": 0, "branches": 0, "commits": 0, "tags": 0, "local_tags": 0, "remote_tags": 0}

        authors = set()
        branches = set()
        all_tags = set()
        local_tags = set()
        remote_tags = set()

        for commit in self.commits:
            authors.add(commit.author)
            branches.add(commit.branch)

            # Spočítat tagy z commitů
            for tag in commit.tags:
                all_tags.add(tag.name)
                if tag.is_remote:
                    remote_tags.add(tag.name)
                else:
                    local_tags.add(tag.name)

        return {
            "authors": len(authors),
            "branches": len(branches),
            "commits": len(self.commits),
            "tags": len(all_tags),
            "local_tags": len(local_tags),
            "remote_tags": len(remote_tags)
        }
