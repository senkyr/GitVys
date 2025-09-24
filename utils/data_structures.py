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

    def __post_init__(self):
        if self.tags is None:
            self.tags = []


@dataclass
class Branch:
    name: str
    color: str
    commits: List[Commit]
    start_commit: str
    end_commit: str