from typing import List, Dict, Set
from utils.data_structures import Commit, MergeBranch


class GraphLayout:
    def __init__(self, commits: List[Commit], branch_spacing: int = 20, commit_start_x: int = 160, merge_branches: List[MergeBranch] = None):
        self.commits = commits
        self.branch_lanes: Dict[str, int] = {}
        self.used_lanes: Set[int] = set()
        self.merge_branches = merge_branches or []

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

        # Přidat merge větve do branch relationships
        self._add_merge_branches_to_relationships(branch_relationships)

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
        # Rozdělit větve na normální a merge větve
        normal_branches = []
        merge_branches = []

        for branch_name, info in branch_info.items():
            if branch_name.startswith('merge-'):
                merge_branches.append((branch_name, info))
            else:
                normal_branches.append((branch_name, info))

        # Seřadit normální větve podle času vytvoření
        normal_branches_by_time = sorted(normal_branches,
                                       key=lambda x: x[1]['creation_time'], reverse=True)

        # FÁZE 1: Přiřadit lanes normálním větvím
        # Začít s main/master větví na pozici 0
        main_branches = ['main', 'master']
        main_branch = None
        for branch_name, _ in normal_branches_by_time:
            if branch_name.lower() in main_branches:
                main_branch = branch_name
                break

        if main_branch:
            self.branch_lanes[main_branch] = 0
            self.used_lanes.add(0)

        # Přiřadit lanes postupně normálním větvím
        for branch_name, info in normal_branches_by_time:
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

        # FÁZE 2: Přiřadit lanes merge větvím (vždy vpravo od parent)
        merge_branches_by_time = sorted(merge_branches,
                                      key=lambda x: x[1]['creation_time'], reverse=True)

        for branch_name, info in merge_branches_by_time:
            # Najít parent větev a nastavit min_lane vpravo od ní
            min_lane = 1  # Minimálně lane 1 (vpravo od main)

            for parent_branch in info['parent_branches']:
                if parent_branch in self.branch_lanes:
                    # Merge větev musí být vpravo od parent větve
                    min_lane = max(min_lane, self.branch_lanes[parent_branch] + 1)

            # Najít první volnou pozici od min_lane
            while min_lane in self.used_lanes:
                min_lane += 1

            self.branch_lanes[branch_name] = min_lane
            self.used_lanes.add(min_lane)

    def _add_merge_branches_to_relationships(self, branch_relationships: Dict[str, Dict]):
        """Přidá merge větve do branch relationships pro správné lane assignment."""
        commit_map = {commit.hash: commit for commit in self.commits}

        for merge_branch in self.merge_branches:
            virtual_name = merge_branch.virtual_branch_name

            # Najít nejstarší commit v merge branch pro creation_time
            creation_time = None
            if merge_branch.commits_in_branch:
                # Vzít nejstarší commit v merge branch
                oldest_commit_hash = merge_branch.commits_in_branch[-1]  # Předpokládám že jsou seřazené
                if oldest_commit_hash in commit_map:
                    creation_time = commit_map[oldest_commit_hash].date

            if creation_time is None:
                # Fallback - použít aktuální čas
                from datetime import datetime, timezone
                creation_time = datetime.now(timezone.utc)

            # Najít parent branch (větev kde se merge branch odbočil)
            parent_branches = set()
            if merge_branch.branch_point_hash in commit_map:
                branch_point_commit = commit_map[merge_branch.branch_point_hash]
                parent_branches.add(branch_point_commit.branch)

            # Přidat merge branch do relationships
            branch_relationships[virtual_name] = {
                'first_commit': commit_map.get(merge_branch.commits_in_branch[0]) if merge_branch.commits_in_branch else None,
                'parent_branches': parent_branches,
                'child_branches': set(),  # Merge větve nemají child větve
                'creation_time': creation_time
            }

            # Aktualizovat parent branch aby věděl o child merge branch
            for parent_branch in parent_branches:
                if parent_branch in branch_relationships:
                    branch_relationships[parent_branch]['child_branches'].add(virtual_name)

    def get_branch_lane(self, branch_name: str) -> int:
        return self.branch_lanes.get(branch_name, 0)
