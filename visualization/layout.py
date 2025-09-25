from typing import List, Dict, Set
from utils.data_structures import Commit


class GraphLayout:
    def __init__(self, commits: List[Commit], branch_spacing: int = 20, commit_start_x: int = 160):
        self.commits = commits
        self.branch_lanes: Dict[str, int] = {}
        self.used_lanes: Set[int] = set()

        # Layout parametry
        self.branch_spacing = branch_spacing  # Vzdálenost mezi větvemi
        self.commit_start_x = commit_start_x  # X pozice pro první větev (lane 0)

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
            commit.x = branch_lane * self.branch_spacing + self.commit_start_x

            # Y pozice podle chronologického pořadí (řádek)
            commit.y = i * 30 + 50

            # table_row pro tabulku
            commit.table_row = i

        return all_commits

    def _assign_lanes(self, commits: List[Commit]):
        # Analyzovat parent-child vztahy pro inteligentní umístění větví
        branch_relationships = self._analyze_branch_relationships(commits)

        # Přiřadit lanes tak, aby odbočky vedly vždy doprava
        self._assign_lanes_intelligently(branch_relationships)

    def _analyze_branch_relationships(self, commits: List[Commit]) -> Dict[str, Dict]:
        """Analyzuje vztahy mezi větvemi pro optimální layout."""
        branch_info = {}
        commit_to_branch = {commit.hash: commit.branch for commit in commits}

        for commit in commits:
            branch = commit.branch
            if branch not in branch_info:
                branch_info[branch] = {
                    'first_commit': commit,
                    'parent_branches': set(),
                    'child_branches': set(),
                    'creation_time': commit.date
                }

            # Najít parent větve (větve, odkud tato větev odbočuje)
            for parent_hash in commit.parents:
                parent_branch = commit_to_branch.get(parent_hash)
                if parent_branch and parent_branch != branch:
                    branch_info[branch]['parent_branches'].add(parent_branch)
                    if parent_branch in branch_info:
                        branch_info[parent_branch]['child_branches'].add(branch)

        return branch_info

    def _assign_lanes_intelligently(self, branch_info: Dict[str, Dict]):
        """Přiřadí lanes tak, aby odbočky vedly vždy doprava."""
        # Seřadit větve podle času vytvoření
        branches_by_time = sorted(branch_info.items(),
                                key=lambda x: x[1]['creation_time'], reverse=True)

        # Začít s main/master větví na pozici 0
        main_branches = ['main', 'master']
        main_branch = None
        for branch_name, _ in branches_by_time:
            if branch_name.lower() in main_branches:
                main_branch = branch_name
                break

        if main_branch:
            self.branch_lanes[main_branch] = 0
            self.used_lanes.add(0)

        # Přiřadit lanes postupně, zajistit že child větve jsou vždy vpravo od parent větví
        for branch_name, info in branches_by_time:
            if branch_name in self.branch_lanes:
                continue

            # Najít nejvhodnější pozici pro tuto větev
            min_lane = 0

            # Pokud má parent větve, musí být vpravo od všech z nich
            for parent_branch in info['parent_branches']:
                if parent_branch in self.branch_lanes:
                    min_lane = max(min_lane, self.branch_lanes[parent_branch] + 1)

            # Najít první volnou pozici od min_lane
            while min_lane in self.used_lanes:
                min_lane += 1

            self.branch_lanes[branch_name] = min_lane
            self.used_lanes.add(min_lane)

    def get_branch_lane(self, branch_name: str) -> int:
        return self.branch_lanes.get(branch_name, 0)