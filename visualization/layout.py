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

        # Seřadit podle času globálně - toto určuje Y pozice
        all_commits = sorted(self.commits, key=lambda c: c.date, reverse=True)

        # Přiřadit lanes větvím
        self._assign_lanes(all_commits)

        # Každý commit dostane Y pozici podle svého chronologického pořadí
        # X pozici podle své větve
        for i, commit in enumerate(all_commits):
            branch_lane = self.branch_lanes[commit.branch]

            # X pozice podle lane větve (sloupec) - začátek po vlaječkách, menší rozestupy
            commit.x = branch_lane * 20 + 100  # 20px mezi větvemi, začátek na 100px

            # Y pozice podle chronologického pořadí (řádek)
            commit.y = i * 30 + 50

            # table_row pro tabulku
            commit.table_row = i

        return all_commits

    def _assign_lanes(self, commits: List[Commit]):
        lane_counter = 0

        for commit in commits:
            if commit.branch not in self.branch_lanes:
                self.branch_lanes[commit.branch] = lane_counter
                self.used_lanes.add(lane_counter)
                lane_counter += 1

    def get_branch_lane(self, branch_name: str) -> int:
        return self.branch_lanes.get(branch_name, 0)