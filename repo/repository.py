import os
from datetime import datetime, timezone
from typing import List, Dict, Optional
import git
from git import Repo, InvalidGitRepositoryError
from utils.data_structures import Commit, Branch, Tag
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

        # Předpočítání map commit -> větev a commit -> tagy pro optimalizaci
        commit_to_branch = self._build_commit_branch_map()
        commit_to_tags = self._build_commit_tag_map()

        commits = []
        used_colors = set()
        branch_colors = {}
        seen_commits = set()

        # Iterovat pouze přes lokální větve, ne přes all=True
        for head in self.repo.heads:
            try:
                for commit in self.repo.iter_commits(head):
                    if commit.hexsha in seen_commits:
                        continue
                    seen_commits.add(commit.hexsha)

                    branch_name = commit_to_branch.get(commit.hexsha, 'unknown')

                    if branch_name not in branch_colors:
                        branch_colors[branch_name] = get_branch_color(branch_name, used_colors)

                    full_message = commit.message.strip()
                    message_lines = full_message.split('\n', 1)
                    subject = message_lines[0]
                    description = message_lines[1].strip() if len(message_lines) > 1 else ""

                    # Získat tagy pro tento commit
                    commit_tags = commit_to_tags.get(commit.hexsha, [])

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
                        branch_color=branch_colors[branch_name],
                        tags=commit_tags
                    )
                    commit_obj.description = description
                    commit_obj.description_short = self._truncate_description(description)
                    commits.append(commit_obj)
            except:
                continue

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

            # Pracovat s lokálními heads (větve)
            for head in self.repo.heads:
                branch_name = head.name
                if branch_name in main_branches:
                    # Okamžitě zpracujeme hlavní větve
                    try:
                        for commit in self.repo.iter_commits(head):
                            commit_to_branch[commit.hexsha] = branch_name
                    except:
                        continue
                else:
                    other_branches.append((head, branch_name))

            # Poté zpracujeme ostatní větve, ale pouze commity co ještě nemají větev
            for head, branch_name in other_branches:
                try:
                    for commit in self.repo.iter_commits(head):
                        commit_hash = commit.hexsha
                        if commit_hash not in commit_to_branch:
                            commit_to_branch[commit_hash] = branch_name
                except:
                    continue

        except Exception:
            pass

        return commit_to_branch

    def parse_commits_with_remote(self) -> List[Commit]:
        """Načte commity včetně remote větví z origin."""
        if not self.repo:
            return []

        # Předpočítání map pro lokální i remote větve a tagy
        local_commit_map, remote_commit_map = self._build_commit_branch_map_with_remote()
        commit_to_tags = self._build_commit_tag_map_with_remote()

        commits = []
        used_colors = set()
        branch_colors = {}

        for commit in self.repo.iter_commits(all=True):
            # Prioritně lokální větev
            if commit.hexsha in local_commit_map:
                branch_name = local_commit_map[commit.hexsha]
                is_remote = False
            elif commit.hexsha in remote_commit_map:
                branch_name = remote_commit_map[commit.hexsha]
                is_remote = True
            else:
                branch_name = 'unknown'
                is_remote = False

            if branch_name not in branch_colors:
                branch_colors[branch_name] = get_branch_color(branch_name, used_colors)

            full_message = commit.message.strip()
            message_lines = full_message.split('\n', 1)
            subject = message_lines[0]
            description = message_lines[1].strip() if len(message_lines) > 1 else ""

            # Získat tagy pro tento commit
            commit_tags = commit_to_tags.get(commit.hexsha, [])

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
                branch_color=branch_colors[branch_name],
                is_remote=is_remote,
                tags=commit_tags
            )
            commit_obj.description = description
            commit_obj.description_short = self._truncate_description(description)
            commits.append(commit_obj)

        commits.sort(key=lambda c: c.date, reverse=True)
        self.commits = commits
        return commits

    def _build_commit_branch_map_with_remote(self) -> tuple[Dict[str, str], Dict[str, str]]:
        """Vytvořuje mapy commit_hash -> branch_name pro lokální a remote větve."""
        local_commit_map = {}
        remote_commit_map = {}

        try:
            # 1. Prioritně lokální větve
            main_branches = ['main', 'master']
            other_local_branches = []

            for head in self.repo.heads:
                branch_name = head.name
                if branch_name in main_branches:
                    try:
                        for commit in self.repo.iter_commits(head):
                            local_commit_map[commit.hexsha] = branch_name
                    except:
                        continue
                else:
                    other_local_branches.append((head, branch_name))

            for head, branch_name in other_local_branches:
                try:
                    for commit in self.repo.iter_commits(head):
                        if commit.hexsha not in local_commit_map:
                            local_commit_map[commit.hexsha] = branch_name
                except:
                    continue

            # 2. Remote větve - jen pro commity bez lokální větve
            try:
                remote_refs = list(self.repo.remote().refs)
                for remote_ref in remote_refs:
                    # Přeskočit HEAD ref
                    if remote_ref.name.endswith('/HEAD'):
                        continue

                    try:
                        for commit in self.repo.iter_commits(remote_ref):
                            if commit.hexsha not in local_commit_map:
                                remote_commit_map[commit.hexsha] = remote_ref.name
                    except:
                        continue
            except:
                # Pokud remote neexistuje, pokračovat jen s lokálními větvemi
                pass

        except Exception:
            pass

        return local_commit_map, remote_commit_map

    def _build_commit_tag_map(self) -> Dict[str, List[Tag]]:
        """Vytvořuje mapu commit_hash -> List[Tag] pro lokální tagy."""
        commit_to_tags = {}

        try:
            for tag in self.repo.tags:
                try:
                    # Získat commit na který tag ukazuje
                    tag_commit = tag.commit
                    tag_obj = Tag(
                        name=tag.name,
                        is_remote=False,
                        message=tag.tag.message if hasattr(tag, 'tag') and tag.tag else ""
                    )

                    if tag_commit.hexsha not in commit_to_tags:
                        commit_to_tags[tag_commit.hexsha] = []
                    commit_to_tags[tag_commit.hexsha].append(tag_obj)
                except:
                    continue
        except:
            pass

        return commit_to_tags

    def _build_commit_tag_map_with_remote(self) -> Dict[str, List[Tag]]:
        """Vytvořuje mapu commit_hash -> List[Tag] pro lokální i remote tagy."""
        commit_to_tags = {}

        # Nejprve lokální tagy (mají prioritu)
        local_tags = self._build_commit_tag_map()
        commit_to_tags.update(local_tags)

        # Poté remote tagy (jen pokud commit ještě nemá lokální tag)
        try:
            # Remote tagy jsou v refs/remotes/origin/tags/* nebo se načítají přes remote
            # Pro zjednodušení použijeme GitPython API, který umí rozlišit remote tagy
            remote_refs = []
            try:
                remote_refs = list(self.repo.remote().refs)
            except:
                pass

            for remote_ref in remote_refs:
                # Přeskočit branch refs, hledáme jen tagy
                if not remote_ref.name.endswith('/tags/') and '/tags/' not in remote_ref.name:
                    continue

                try:
                    # Extrahovat název tagu z remote ref
                    tag_name = remote_ref.name.split('/')[-1]
                    if '/tags/' in remote_ref.name:
                        tag_name = remote_ref.name.split('/tags/')[-1]

                    tag_commit = remote_ref.commit
                    tag_obj = Tag(
                        name=f"origin/{tag_name}",
                        is_remote=True,
                        message=""
                    )

                    if tag_commit.hexsha not in commit_to_tags:
                        commit_to_tags[tag_commit.hexsha] = []

                    # Přidat jen pokud už není lokální tag se stejným názvem
                    existing_names = [t.name for t in commit_to_tags[tag_commit.hexsha]]
                    if tag_name not in existing_names:
                        commit_to_tags[tag_commit.hexsha].append(tag_obj)
                except:
                    continue
        except:
            pass

        return commit_to_tags

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
        """Zkrátí description na první řádek s maximální délkou a přidá vynechávku."""
        if not description:
            return ""

        # Vzít jen první řádek
        first_line = description.split('\n')[0].strip()
        has_more_lines = '\n' in description

        # Určit, jestli potřebujeme vynechávku
        needs_ellipsis = False

        if has_more_lines:
            # Pokud má více řádků, vždycky potřebujeme vynechávku
            needs_ellipsis = True
        elif len(first_line) > max_length:
            # Pokud je první řádek moc dlouhý
            needs_ellipsis = True

        # Zkrátit text pokud je potřeba
        if len(first_line) > max_length:
            first_line = first_line[:max_length-3]

        # Přidat vynechávku
        if needs_ellipsis:
            # Pokud končí dvojtečkou, nahradit ji vynechávkou
            if first_line.endswith(':'):
                first_line = first_line[:-1] + '...'
            else:
                first_line = first_line + '...'

        return first_line

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