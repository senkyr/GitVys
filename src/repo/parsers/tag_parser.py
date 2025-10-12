"""TagParser - handles parsing of Git tags."""

from typing import Dict, List
from git import Repo
from utils.data_structures import Tag
from utils.logging_config import get_logger

logger = get_logger(__name__)


class TagParser:
    """Handles parsing of Git tags from repository."""

    def __init__(self, repo: Repo):
        """Initialize TagParser.

        Args:
            repo: GitPython Repo object
        """
        self.repo = repo

    def build_commit_tag_map(self) -> Dict[str, List[Tag]]:
        """Build map of commit_hash -> List[Tag] for local tags.

        Returns:
            Dictionary mapping commit hash to list of tags
        """
        commit_to_tags = {}

        try:
            for tag in self.repo.tags:
                try:
                    # Get commit that tag points to
                    tag_commit = tag.commit
                    tag_obj = Tag(
                        name=tag.name,
                        is_remote=False,
                        message=tag.tag.message if hasattr(tag, 'tag') and tag.tag else ""
                    )

                    if tag_commit.hexsha not in commit_to_tags:
                        commit_to_tags[tag_commit.hexsha] = []
                    commit_to_tags[tag_commit.hexsha].append(tag_obj)
                except Exception as e:
                    logger.warning(f"Failed to process tag {tag.name}: {e}")
                    continue
        except Exception as e:
            logger.warning(f"Failed to iterate tags: {e}")
            pass

        return commit_to_tags

    def build_commit_tag_map_with_remote(self) -> Dict[str, List[Tag]]:
        """Build map of commit_hash -> List[Tag] for local and remote tags.

        Returns:
            Dictionary mapping commit hash to list of tags
        """
        commit_to_tags = {}

        # First local tags (they have priority)
        local_tags = self.build_commit_tag_map()
        commit_to_tags.update(local_tags)

        # Then remote tags (only if commit doesn't have local tag yet)
        try:
            # Remote tags are in refs/remotes/origin/tags/* or loaded via remote
            # For simplicity, we use GitPython API which can distinguish remote tags
            remote_refs = []
            try:
                remote_refs = list(self.repo.remote().refs)
            except:
                pass

            for remote_ref in remote_refs:
                # Skip branch refs, look only for tags
                if not remote_ref.name.endswith('/tags/') and '/tags/' not in remote_ref.name:
                    continue

                try:
                    # Extract tag name from remote ref
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

                    # Add only if there isn't already a local tag with same name
                    existing_names = [t.name for t in commit_to_tags[tag_commit.hexsha]]
                    if tag_name not in existing_names:
                        commit_to_tags[tag_commit.hexsha].append(tag_obj)
                except Exception as e:
                    logger.warning(f"Failed to process remote tag {remote_ref.name}: {e}")
                    continue
        except Exception as e:
            logger.debug(f"Failed to iterate remote tags: {e}")
            pass

        return commit_to_tags
