"""Rozmístění commitů do řádků (osa Y) a větví do sloupců/lanes (osa X)."""

import heapq
from datetime import datetime, timezone
from typing import List, Dict, Set

from utils.data_structures import Commit, MergeBranch
from utils.constants import BRANCH_LANE_SPACING, COMMIT_START_X, COMMIT_VERTICAL_SPACING, COMMIT_START_Y

MAIN_BRANCHES = ('main', 'master')


def _timestamp(commit: Commit) -> float:
    """Čas commitu jako číslo (zvládne aware i naive datetime bez TypeError při porovnání)."""
    try:
        return commit.date.timestamp()
    except Exception:
        return 0.0


def order_commits(commits: List[Commit]) -> List[Commit]:
    """Seřadí commity od nejnovějšího, ale vždy potomka NAD jeho rodiče.

    Odpovídá `git log --date-order`: primárně podle času commitu, ale
    commit se vypíše až po všech svých potomcích. Čisté řazení podle data
    selže, když má autor rozjeté hodiny (běžné u školních PC) nebo když
    commity vzniknou ve stejné sekundě - rodič se pak ocitne nad potomkem
    a hrana grafu vede nahoru.
    """
    by_hash = {commit.hash: commit for commit in commits}
    pending_children = {commit.hash: 0 for commit in commits}
    for commit in commits:
        for parent_hash in set(commit.parents):
            if parent_hash in pending_children:
                pending_children[parent_hash] += 1

    # Halda podle (nejnovější první, původní pořadí jako tiebreak)
    heap = [(-_timestamp(commit), index, commit.hash)
            for index, commit in enumerate(commits) if pending_children[commit.hash] == 0]
    heapq.heapify(heap)
    index_of = {commit.hash: index for index, commit in enumerate(commits)}

    ordered = []
    while heap:
        _, _, commit_hash = heapq.heappop(heap)
        commit = by_hash[commit_hash]
        ordered.append(commit)
        for parent_hash in set(commit.parents):
            if parent_hash not in pending_children:
                continue
            pending_children[parent_hash] -= 1
            if pending_children[parent_hash] == 0:
                parent = by_hash[parent_hash]
                heapq.heappush(heap, (-_timestamp(parent), index_of[parent_hash], parent_hash))

    if len(ordered) != len(commits):
        # Cyklus v datech (duplicitní hash apod.) - nic neztratit, zbytek podle data
        seen = {id(commit) for commit in ordered}
        rest = [commit for commit in commits if id(commit) not in seen]
        ordered.extend(sorted(rest, key=_timestamp, reverse=True))
    return ordered


class GraphLayout:
    def __init__(self, commits: List[Commit], branch_spacing: int = BRANCH_LANE_SPACING, commit_start_x: int = COMMIT_START_X, merge_branches: List[MergeBranch] = None):
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

        # Pořadí řádků: podle času, ale potomek vždy nad rodičem
        all_commits = order_commits(self.commits)

        # Přiřadit lanes větvím s recyklací
        self._assign_lanes_with_recycling(all_commits)

        # Každý commit dostane Y pozici podle svého pořadí, X pozici podle své větve
        for i, commit in enumerate(all_commits):
            branch_lane = self.branch_lanes[commit.branch]
            commit.x = branch_lane * self.branch_spacing + self.commit_start_x
            commit.y = i * COMMIT_VERTICAL_SPACING + COMMIT_START_Y
            commit.table_row = i

        return all_commits

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

    def _add_merge_branches_to_relationships(self, branch_relationships: Dict[str, Dict]):
        """Přidá merge větve do branch relationships pro správné lane assignment."""
        commit_map = {commit.hash: commit for commit in self.commits}

        for merge_branch in self.merge_branches:
            virtual_name = merge_branch.virtual_branch_name

            # Nejstarší commit merge větve (commits_in_branch je od nejnovějšího)
            creation_time = None
            if merge_branch.commits_in_branch:
                oldest_commit_hash = merge_branch.commits_in_branch[-1]
                if oldest_commit_hash in commit_map:
                    creation_time = commit_map[oldest_commit_hash].date
            if creation_time is None:
                creation_time = datetime.now(timezone.utc)

            # Parent branch (větev, kde se merge branch odbočil)
            parent_branches = set()
            if merge_branch.branch_point_hash in commit_map:
                parent_branches.add(commit_map[merge_branch.branch_point_hash].branch)

            branch_relationships[virtual_name] = {
                'first_commit': commit_map.get(merge_branch.commits_in_branch[0]) if merge_branch.commits_in_branch else None,
                'parent_branches': parent_branches,
                'child_branches': set(),  # Merge větve nemají child větve
                'creation_time': creation_time
            }

            for parent_branch in parent_branches:
                if parent_branch in branch_relationships:
                    branch_relationships[parent_branch]['child_branches'].add(virtual_name)

    def get_branch_lane(self, branch_name: str) -> int:
        return self.branch_lanes.get(branch_name, 0)

    @staticmethod
    def _branch_row_spans(commits: List[Commit]) -> Dict[str, List[int]]:
        """Pro každou větev vrátí [první řádek, poslední řádek], které zabírá její lane.

        Nestačí řádky vlastních commitů: spojnice se kreslí jako "L"
        (viz ConnectionDrawer) a svislá část leží v lane jedné z větví:
        - odbočení (běžná hrana potomek -> rodič z jiné větve): svislá čára
          v lane POTOMKA od řádku potomka dolů až k řádku rodiče;
        - merge hrana (2.+ rodič merge commitu): svislá čára v lane RODIČE
          od řádku rodiče nahoru až k řádku merge commitu.
        Kdyby se lane uvolnila hned po posledním commitu větve, jiná větev by
        ji obsadila a její commity by ležely přímo na této čáře.
        """
        row = {commit.hash: i for i, commit in enumerate(commits)}
        by_hash = {commit.hash: commit for commit in commits}
        spans: Dict[str, List[int]] = {}

        def extend(branch: str, first: int, last: int):
            span = spans.setdefault(branch, [first, last])
            span[0] = min(span[0], first)
            span[1] = max(span[1], last)

        for i, commit in enumerate(commits):
            extend(commit.branch, i, i)

        for i, commit in enumerate(commits):
            is_merge_commit = len(commit.parents) >= 2
            for parent_index, parent_hash in enumerate(commit.parents):
                parent = by_hash.get(parent_hash)
                if parent is None or parent.branch == commit.branch:
                    continue
                parent_row = row[parent_hash]
                owner = parent.branch if (is_merge_commit and parent_index > 0) else commit.branch
                extend(owner, min(i, parent_row), max(i, parent_row))

        return spans

    def _assign_lanes_with_recycling(self, commits: List[Commit]):
        """Přiřadí lanes větvím s recyklací - lane se uvolní, až skončí vše, co v ní vede.

        Args:
            commits: Commity v pořadí řádků (výstup order_commits)
        """
        branch_relationships = self._analyze_branch_relationships(commits)
        self._add_merge_branches_to_relationships(branch_relationships)
        spans = self._branch_row_spans(commits)

        # Main/master má vždy lane 0 po celé výšce grafu
        main_branch = None
        for commit in commits:
            if commit.branch.lower() in MAIN_BRANCHES:
                main_branch = commit.branch
                break

        lane_busy_until: Dict[int, int] = {}  # lane -> poslední řádek, který je v ní obsazený
        if main_branch:
            self.branch_lanes[main_branch] = 0
            lane_busy_until[0] = float('inf')

        # Větve v pořadí, v jakém se v grafu shora objeví
        branches_by_start = sorted(spans, key=lambda name: spans[name][0])

        for branch in branches_by_start:
            if branch in self.branch_lanes:
                continue
            first_row, last_row = spans[branch]

            # Odbočka musí být vpravo od větví, ze kterých vychází
            min_lane = 0
            for parent_branch in branch_relationships.get(branch, {}).get('parent_branches', ()):
                if parent_branch in self.branch_lanes:
                    min_lane = max(min_lane, self.branch_lanes[parent_branch] + 1)

            lane = min_lane
            while lane_busy_until.get(lane, -1) >= first_row:
                lane += 1

            self.branch_lanes[branch] = lane
            lane_busy_until[lane] = last_row

        self.used_lanes = set(self.branch_lanes.values())
