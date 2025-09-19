import os
from datetime import datetime, timezone
from typing import List, Dict, Optional
import git
from git import Repo, InvalidGitRepositoryError
from utils.data_structures import Commit, Branch
from visualization.colors import get_branch_color


class GitRepository:
    def __init__(self, repo_path: str):
        self.repo_path = repo_path
        self.repo: Optional[Repo] = None
        self.commits: List[Commit] = []
        self.branches: Dict[str, Branch] = {}

    def load_repository(self) -> bool:
        try:
            self.repo = Repo(self.repo_path)
            return True
        except InvalidGitRepositoryError:
            return False

    def parse_commits(self) -> List[Commit]:
        if not self.repo:
            return []

        # Předpočítání mapy commit -> větev pro optimalizaci
        commit_to_branch = self._build_commit_branch_map()

        commits = []
        used_colors = set()
        branch_colors = {}

        for commit in self.repo.iter_commits(all=True):
            branch_name = commit_to_branch.get(commit.hexsha, 'unknown')

            if branch_name not in branch_colors:
                branch_colors[branch_name] = get_branch_color(branch_name, used_colors)

            full_message = commit.message.strip()
            message_lines = full_message.split('\n', 1)
            subject = message_lines[0]
            description = message_lines[1].strip() if len(message_lines) > 1 else ""

            commit_obj = Commit(
                hash=commit.hexsha[:8],
                message=subject,
                short_message=self._truncate_message(subject, 50),
                author=commit.author.name,
                author_short=self._truncate_name(commit.author.name),
                author_email=commit.author.email,
                date=commit.committed_datetime,
                date_relative=self._get_relative_date(commit.committed_datetime),
                date_short=self._get_full_date(commit.committed_datetime),
                parents=[parent.hexsha[:8] for parent in commit.parents],
                branch=branch_name,
                branch_color=branch_colors[branch_name]
            )
            commit_obj.description = description
            commit_obj.description_short = self._truncate_description(description)
            commits.append(commit_obj)

        commits.sort(key=lambda c: c.date, reverse=True)
        self.commits = commits
        return commits

    def _build_commit_branch_map(self) -> Dict[str, str]:
        """Vytvořuje mapu commit_hash -> branch_name pro rychlé vyhledávání."""
        commit_to_branch = {}

        try:
            # Nejdříve zpracujeme hlavní větve s prioritou
            main_branches = ['main', 'master']
            other_branches = []

            for ref in self.repo.refs:
                if ref.name.startswith('refs/heads/'):
                    branch_name = ref.name.split('/')[-1]
                    if branch_name in main_branches:
                        # Okamžitě zpracujeme hlavní větve
                        try:
                            for commit in self.repo.iter_commits(ref):
                                commit_to_branch[commit.hexsha] = branch_name
                        except:
                            continue
                    else:
                        other_branches.append((ref, branch_name))

            # Poté zpracujeme ostatní větve, ale pouze commity co ještě nemají větev
            for ref, branch_name in other_branches:
                try:
                    for commit in self.repo.iter_commits(ref):
                        commit_hash = commit.hexsha
                        if commit_hash not in commit_to_branch:
                            commit_to_branch[commit_hash] = branch_name
                except:
                    continue

        except Exception:
            pass

        return commit_to_branch

    def _truncate_message(self, message: str, max_length: int) -> str:
        if len(message) <= max_length:
            return message
        return message[:max_length-3] + '...'

    def _truncate_name(self, name: str) -> str:
        if len(name) <= 15:
            return name
        parts = name.split()
        if len(parts) > 1:
            return f"{parts[0][0]}. {parts[-1]}"
        return name[:12] + '...'

    def _truncate_description(self, description: str, max_length: int = 80) -> str:
        """Zkrátí description na první řádek s maximální délkou."""
        if not description:
            return ""

        # Vzít jen první řádek
        first_line = description.split('\n')[0].strip()

        # Zkrátit na max délku
        if len(first_line) <= max_length:
            return first_line
        return first_line[:max_length-3] + '...'

    def _get_relative_date(self, date: datetime) -> str:
        now = datetime.now(timezone.utc)
        diff = now - date.replace(tzinfo=timezone.utc)

        if diff.days > 7:
            return f"{diff.days // 7} týdnů"
        elif diff.days > 0:
            return f"{diff.days} dní" if diff.days > 1 else "1 den"
        elif diff.seconds > 3600:
            hours = diff.seconds // 3600
            return f"{hours} hodin" if hours > 1 else "1 hodina"
        else:
            minutes = diff.seconds // 60
            return f"{minutes} minut" if minutes > 1 else "před chvílí"

    def _get_short_date(self, date: datetime) -> str:
        return date.strftime("%d.%m")

    def _get_full_date(self, date: datetime) -> str:
        return date.strftime("%d.%m.%Y @ %H:%M")

    def get_repository_stats(self) -> Dict[str, int]:
        if not self.repo or not self.commits:
            return {"authors": 0, "branches": 0, "commits": 0, "tags": 0}

        authors = set()
        branches = set()

        for commit in self.commits:
            authors.add(commit.author)
            branches.add(commit.branch)

        try:
            tags = list(self.repo.tags)
            tag_count = len(tags)
        except:
            tag_count = 0

        return {
            "authors": len(authors),
            "branches": len(branches),
            "commits": len(self.commits),
            "tags": tag_count
        }