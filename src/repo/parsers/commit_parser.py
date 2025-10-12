"""CommitParser - handles parsing of commits from Git repository."""

from datetime import datetime, timezone
from typing import List, Dict, Optional
from git import Repo
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
        seen_commits = set()

        # Iterate only over local branches
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

                    # Get tags for this commit
                    commit_tags = commit_to_tags.get(commit.hexsha, [])

                    # Determine branch availability
                    branch_avail = branch_availability.get(branch_name, 'local_only')

                    commit_obj = Commit(
                        hash=commit.hexsha[:8],
                        message=subject,
                        short_message=self.truncate_message(subject, MESSAGE_MAX_LENGTH),
                        author=commit.author.name,
                        author_short=self.truncate_name(commit.author.name),
                        author_email=commit.author.email,
                        date=commit.committed_datetime,
                        date_relative=self.get_relative_date(commit.committed_datetime),
                        date_short=self.get_full_date(commit.committed_datetime),
                        parents=[parent.hexsha[:8] for parent in commit.parents],
                        branch=branch_name,
                        branch_color=branch_colors[branch_name],
                        tags=commit_tags,
                        branch_availability=branch_avail
                    )
                    commit_obj.description = description
                    commit_obj.description_short = self.truncate_description(description)
                    commits.append(commit_obj)
            except Exception as e:
                logger.warning(f"Failed to process commit from branch {head.name}: {e}")
                continue

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
        commits = []

        # Collect all branch heads for identification
        branch_heads = {}  # branch_name -> {'local': commit_hash, 'remote': commit_hash}
        for branch_name, div_info in branch_divergences.items():
            branch_heads[branch_name] = {
                'local': div_info.get('local_head'),
                'remote': div_info.get('remote_head')
            }

        # Safely iterate over all commits (local + remote, without broken refs)
        seen_commits = set()
        all_commits_to_process = []

        # 1. First local branches
        try:
            for head in self.repo.heads:
                try:
                    for commit in self.repo.iter_commits(head):
                        if commit.hexsha not in seen_commits:
                            seen_commits.add(commit.hexsha)
                            all_commits_to_process.append(commit)
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
                                all_commits_to_process.append(commit)
                    except Exception as e:
                        logger.warning(f"Failed to iterate commits for remote ref {remote_ref.name}: {e}")
                        continue
        except Exception as e:
            logger.debug(f"Failed to access remote refs: {e}")

        # 3. Process all found commits
        for commit in all_commits_to_process:
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

            if branch_name not in branch_colors:
                branch_colors[branch_name] = get_branch_color(branch_name, used_colors)

            full_message = commit.message.strip()
            message_lines = full_message.split('\n', 1)
            subject = message_lines[0]
            description = message_lines[1].strip() if len(message_lines) > 1 else ""

            # Get tags for this commit
            commit_tags = commit_to_tags.get(commit.hexsha, [])

            # Determine branch availability (for remote branches may have origin/ prefix)
            clean_branch_name = branch_name
            if branch_name.startswith('origin/'):
                clean_branch_name = branch_name[7:]  # Remove "origin/"

            branch_avail = branch_availability.get(clean_branch_name, 'local_only')

            # Determine if this commit is HEAD of some branch
            is_branch_head = False
            branch_head_type = "none"

            if clean_branch_name in branch_heads:
                heads = branch_heads[clean_branch_name]
                local_head = heads.get('local')
                remote_head = heads.get('remote')

                is_local_head = local_head and commit.hexsha == local_head.hexsha
                is_remote_head = remote_head and commit.hexsha == remote_head.hexsha

                if is_local_head and is_remote_head:
                    is_branch_head = True
                    branch_head_type = "both"
                elif is_local_head:
                    is_branch_head = True
                    branch_head_type = "local"
                elif is_remote_head:
                    is_branch_head = True
                    branch_head_type = "remote"

            commit_obj = Commit(
                hash=commit.hexsha[:8],
                message=subject,
                short_message=self.truncate_message(subject, MESSAGE_MAX_LENGTH),
                author=commit.author.name,
                author_short=self.truncate_name(commit.author.name),
                author_email=commit.author.email,
                date=commit.committed_datetime,
                date_relative=self.get_relative_date(commit.committed_datetime),
                date_short=self.get_full_date(commit.committed_datetime),
                parents=[parent.hexsha[:8] for parent in commit.parents],
                branch=branch_name,
                branch_color=branch_colors[branch_name],
                is_remote=is_remote,
                tags=commit_tags,
                branch_availability=branch_avail,
                is_branch_head=is_branch_head,
                branch_head_type=branch_head_type
            )
            commit_obj.description = description
            commit_obj.description_short = self.truncate_description(description)
            commits.append(commit_obj)

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
        return date.strftime("%d.%m.%Y @ %H:%M")
