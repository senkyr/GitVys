from typing import List, Dict, Set
from utils.data_structures import Commit


class GraphLayout:
    def __init__(self, commits: List[Commit]):
        self.commits = commits
        self.branch_lanes: Dict[str, int] = {}
        self.used_lanes: Set[int] = set()

    def calculate_positions(self) -> List[Commit]:
        if not self.commits:
            return []

        sorted_commits = sorted(self.commits, key=lambda c: c.date, reverse=True)

        self._assign_lanes(sorted_commits)

        for i, commit in enumerate(sorted_commits):
            commit.x = i * 60
            commit.y = self.branch_lanes.get(commit.branch, 0) * 40
            commit.table_row = i

        return sorted_commits

    def _assign_lanes(self, commits: List[Commit]):
        lane_counter = 0

        for commit in commits:
            if commit.branch not in self.branch_lanes:
                self.branch_lanes[commit.branch] = lane_counter
                self.used_lanes.add(lane_counter)
                lane_counter += 1

    def get_branch_lane(self, branch_name: str) -> int:
        return self.branch_lanes.get(branch_name, 0)