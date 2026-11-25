"""CommitParser - handles parsing of commits from Git repository."""

from datetime import datetime, timezone
from typing import List, Dict, Optional
from git import Repo
from repo.head import read_head_state
from utils.data_structures import Commit, Tag
from utils.logging_config import get_logger
from utils.constants import MESSAGE_MAX_LENGTH, AUTHOR_NAME_MAX_LENGTH, DESCRIPTION_MAX_LENGTH
from visualization.colors import get_branch_color

logger = get_logger(__name__)


class CommitParser:
    """Handles parsing of commits from Git repository."""

    def __init__(self, repo: Repo):
        """Initialize CommitParser.

        Args:
            repo: GitPython Repo object
        """
        self.repo = repo

    # Refy pro `git rev-list`: všechny lokální větve, případně i větve remote "origin".
    LOCAL_REVS = ['--branches']
    LOCAL_AND_REMOTE_REVS = ['--branches', '--remotes=origin']

    def _iter_unique_commits(self, revs):
        """Projde commity dosažitelné z `revs` jedním během `git rev-list`.

        Dřív se historie procházela zvlášť pro každou větev (N větví = N-krát
        celá historie přes GitPython objekty). Jeden rev-list přes všechny
        větve vrátí každý commit právě jednou.

        Při odpojeném HEAD se přidá i HEAD: commity vytvořené v tomto stavu
        nejsou dosažitelné z žádné větve a v grafu by chyběly.
        """
        if read_head_state(self.repo).is_detached:
            revs = list(revs) + ['HEAD']
        seen = set()
        try:
            for commit in self.repo.iter_commits(revs):
                if commit.hexsha in seen:
                    continue
                seen.add(commit.hexsha)
                yield commit
        except Exception as e:
            logger.warning(f"Failed to iterate commits for {revs}: {e}")

    def _build_commit(self, commit, branch_name: str, branch_colors: Dict[str, str],
                      used_colors: set, commit_to_tags: Dict[str, List[Tag]],
                      branch_avail: str, **extra) -> Commit:
        """Vytvoří datový Commit z GitPython commitu (hash a rodiče jako plné SHA-1)."""
        if branch_name not in branch_colors:
            branch_colors[branch_name] = get_branch_color(branch_name, used_colors)

        full_message = commit.message.strip()
        message_lines = full_message.split('\n', 1)
        subject = message_lines[0]
        description = message_lines[1].strip() if len(message_lines) > 1 else ""

        commit_obj = Commit(
            # Plné hashe: zkrácené 8znakové kolidují u velkých repozitářů
            # (~50 % pravděpodobnost kolize už kolem 77 000 commitů) a kolize
            # by v mapách hash -> commit tiše pomíchala graf.
            hash=commit.hexsha,
            message=subject,
            short_message=self.truncate_message(subject, MESSAGE_MAX_LENGTH),
            author=commit.author.name,
            author_short=self.truncate_name(commit.author.name),
            author_email=commit.author.email,
            date=commit.committed_datetime,
            date_relative=self.get_relative_date(commit.committed_datetime),
            date_short=self.get_full_date(commit.committed_datetime),
            parents=[parent.hexsha for parent in commit.parents],
            branch=branch_name,
            branch_color=branch_colors[branch_name],
            tags=commit_to_tags.get(commit.hexsha, []),
            branch_availability=branch_avail,
            **extra
        )
        commit_obj.description = description
        commit_obj.description_short = self.truncate_description(description)
        return commit_obj

    def parse_commits(self, commit_to_branch: Dict[str, str], commit_to_tags: Dict[str, List[Tag]],
                      branch_availability: Dict[str, str], branch_colors: Dict[str, str],
                      used_colors: set) -> List[Commit]:
        """Parse commits from local branches.

        Args:
            commit_to_branch: Map of commit hash to branch name
            commit_to_tags: Map of commit hash to tags
            branch_availability: Map of branch name to availability status
            branch_colors: Map of branch name to color (will be updated)
            used_colors: Set of already used colors (will be updated)

        Returns:
            List of parsed Commit objects
        """
        commits = []
        for commit in self._iter_unique_commits(self.LOCAL_REVS):
            try:
                branch_name = commit_to_branch.get(commit.hexsha, 'unknown')
                commits.append(self._build_commit(
                    commit, branch_name, branch_colors, used_colors, commit_to_tags,
                    branch_availability.get(branch_name, 'local_only')
                ))
            except Exception as e:
                logger.warning(f"Failed to process commit {getattr(commit, 'hexsha', '?')}: {e}")
        return commits

    def parse_commits_with_remote(self, local_commit_map: Dict[str, str], remote_commit_map: Dict[str, str],
                                   commit_to_tags: Dict[str, List[Tag]], branch_availability: Dict[str, str],
                                   branch_divergences: Dict[str, Dict], branch_colors: Dict[str, str],
                                   used_colors: set) -> List[Commit]:
        """Parse commits including remote branches from origin.

        Args:
            local_commit_map: Map of commit hash to local branch name
            remote_commit_map: Map of commit hash to remote branch name
            commit_to_tags: Map of commit hash to tags
            branch_availability: Map of branch name to availability status
            branch_divergences: Map of branch name to divergence info
            branch_colors: Map of branch name to color (will be updated)
            used_colors: Set of already used colors (will be updated)

        Returns:
            List of parsed Commit objects
        """
        # branch_name -> (local head sha, remote head sha)
        branch_heads = {}
        for branch_name, div_info in branch_divergences.items():
            local_head = div_info.get('local_head')
            remote_head = div_info.get('remote_head')
            branch_heads[branch_name] = (
                local_head.hexsha if local_head else None,
                remote_head.hexsha if remote_head else None,
            )

        commits = []
        for commit in self._iter_unique_commits(self.LOCAL_AND_REMOTE_REVS):
            try:
                # Prioritize local branch
                if commit.hexsha in local_commit_map:
                    branch_name = local_commit_map[commit.hexsha]
                    is_remote = False
                elif commit.hexsha in remote_commit_map:
                    branch_name = remote_commit_map[commit.hexsha]
                    is_remote = True
                else:
                    branch_name = 'unknown'
                    is_remote = False

                # Remote větve mají prefix origin/
                clean_branch_name = branch_name[7:] if branch_name.startswith('origin/') else branch_name

                # Is this commit HEAD of some branch (local/remote/both)?
                local_sha, remote_sha = branch_heads.get(clean_branch_name, (None, None))
                is_local_head = local_sha is not None and commit.hexsha == local_sha
                is_remote_head = remote_sha is not None and commit.hexsha == remote_sha
                if is_local_head and is_remote_head:
                    branch_head_type = "both"
                elif is_local_head:
                    branch_head_type = "local"
                elif is_remote_head:
                    branch_head_type = "remote"
                else:
                    branch_head_type = "none"

                commits.append(self._build_commit(
                    commit, branch_name, branch_colors, used_colors, commit_to_tags,
                    branch_availability.get(clean_branch_name, 'local_only'),
                    is_remote=is_remote,
                    is_branch_head=branch_head_type != "none",
                    branch_head_type=branch_head_type,
                ))
            except Exception as e:
                logger.warning(f"Failed to process commit {getattr(commit, 'hexsha', '?')}: {e}")

        return commits

    def truncate_message(self, message: str, max_length: int) -> str:
        """Truncate message to max length.

        Args:
            message: Message to truncate
            max_length: Maximum length

        Returns:
            Truncated message
        """
        if len(message) <= max_length:
            return message
        return message[:max_length-3] + '...'

    def truncate_name(self, name: str) -> str:
        """Truncate author name to shorter form.

        Args:
            name: Author name

        Returns:
            Truncated name
        """
        if len(name) <= AUTHOR_NAME_MAX_LENGTH:
            return name
        parts = name.split()
        if len(parts) > 1:
            return f"{parts[0][0]}. {parts[-1]}"
        return name[:12] + '...'

    def truncate_description(self, description: str, max_length: int = DESCRIPTION_MAX_LENGTH) -> str:
        """Truncate description to first line with max length.

        Args:
            description: Description to truncate
            max_length: Maximum length

        Returns:
            Truncated description with ellipsis if needed
        """
        if not description:
            return ""

        # Take only first line
        first_line = description.split('\n')[0].strip()
        has_more_lines = '\n' in description

        # Determine if we need ellipsis
        needs_ellipsis = False

        if has_more_lines:
            # If has more lines, always need ellipsis
            needs_ellipsis = True
        elif len(first_line) > max_length:
            # If first line is too long
            needs_ellipsis = True

        # Truncate text if needed
        if len(first_line) > max_length:
            first_line = first_line[:max_length-3]

        # Add ellipsis
        if needs_ellipsis:
            # If ends with colon, replace it with ellipsis
            if first_line.endswith(':'):
                first_line = first_line[:-1] + '...'
            else:
                first_line = first_line + '...'

        return first_line

    def get_relative_date(self, date: datetime) -> str:
        """Get relative date string (e.g., '2 days ago').

        Args:
            date: Date to convert

        Returns:
            Relative date string
        """
        now = datetime.now(timezone.utc)
        # Commit má vlastní časové pásmo (např. +02:00). replace(tzinfo=utc) by
        # ho zahodilo a posunulo čas o offset; aware datum se jen odečte.
        if date.tzinfo is None:
            date = date.replace(tzinfo=timezone.utc)
        diff = now - date
        if diff.total_seconds() < 0:
            return "před chvílí"  # Commit z budoucnosti (rozjeté hodiny autora)

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

    def get_short_date(self, date: datetime) -> str:
        """Get short date string (DD.MM).

        Args:
            date: Date to convert

        Returns:
            Short date string
        """
        return date.strftime("%d.%m")

    def get_full_date(self, date: datetime) -> str:
        """Get full date string (DD.MM.YYYY @ HH:MM).

        Args:
            date: Date to convert

        Returns:
            Full date string
        """
        # Časy commitů ze strojů v různých pásmech převést na místní čas
        # prohlížejícího, jinak by sloupec data neodpovídal pořadí commitů.
        if date.tzinfo is not None:
            date = date.astimezone()
        return date.strftime("%d.%m.%Y @ %H:%M")
