from dataclasses import dataclass
from datetime import datetime
from typing import List


@dataclass
class Commit:
    hash: str
    message: str
    short_message: str
    author: str
    author_short: str
    date: datetime
    date_relative: str
    date_short: str
    parents: List[str]
    branch: str
    branch_color: str
    x: int = 0
    y: int = 0
    table_row: int = 0


@dataclass
class Branch:
    name: str
    color: str
    commits: List[Commit]
    start_commit: str
    end_commit: str