from dataclasses import dataclass
from datetime import datetime
from typing import List


@dataclass
class Tag:
    name: str
    is_remote: bool = False
    message: str = ""  # Pro anotované tagy


@dataclass
class Commit:
    hash: str
    message: str
    short_message: str
    author: str
    author_short: str
    author_email: str
    date: datetime
    date_relative: str
    date_short: str
    parents: List[str]
    branch: str
    branch_color: str
    x: int = 0
    y: int = 0
    table_row: int = 0
    description: str = ""
    description_short: str = ""
    is_remote: bool = False
    tags: List[Tag] = None
    branch_availability: str = "local_only"  # local_only/remote_only/both

    # Pro handling divergence - commit může být součástí více větví (local + remote)
    additional_branches: List[str] = None  # Další větve, do kterých tento commit patří
    is_branch_head: bool = False  # Je toto HEAD nějaké větve (pro vykreslení vlaječky)
    branch_head_type: str = "none"  # "local", "remote", "both"

    # Pro handling uncommitted changes
    is_uncommitted: bool = False  # Je toto uncommitted change ("almost commit")
    uncommitted_type: str = "none"  # "staged", "working", "both" - typ uncommitted změn

    # Pro handling merge branches
    is_merge_branch: bool = False  # Je toto commit z virtuální merge větve

    def __post_init__(self):
        if self.tags is None:
            self.tags = []
        if self.additional_branches is None:
            self.additional_branches = []


@dataclass
class MergeBranch:
    """Reprezentuje virtuální větev pro merge pattern - odbočku a návrat."""
    branch_point_hash: str      # Commit odkud se větev odbočila
    merge_point_hash: str       # Commit kde se větev sloučila (merge commit)
    commits_in_branch: List[str] # Hashes commitů v merge větvi (bez branch/merge pointů)
    virtual_branch_name: str    # Generovaný název pro layout (např. "merge-abc123")
    original_color: str         # Barva hlavní větve (pro světlejší variantu)


@dataclass
class Branch:
    name: str
    color: str
    commits: List[Commit]
    start_commit: str
    end_commit: str