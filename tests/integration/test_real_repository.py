"""Integrační testy nad skutečnými Git repozitáři (žádné mocky GitPythonu).

Ostatní "integrační" testy GitPython mockují, takže neověří, že aplikace
správně čte skutečnou historii. Tady se repozitáře staví přes `git` CLI
v dočasné složce s pevnými časy commitů.
"""

import os
import subprocess
from datetime import datetime, timezone

import pytest

from repo.repository import GitRepository
from repo.parsers.branch_analyzer import BranchAnalyzer
from utils.data_structures import Commit
from visualization.layout import GraphLayout, order_commits

BASE_TIME = 1_700_000_000  # 2023-11-14, pevný základ pro časy commitů


class GitRepoBuilder:
    """Tenký wrapper nad `git` CLI pro stavbu testovacích repozitářů."""

    def __init__(self, path):
        self.path = path
        self._counter = 0
        empty_config = path.parent / f"{path.name}-empty-gitconfig"
        empty_config.write_text("")
        # Izolace od konfigurace uživatele (hooky, šablony, podepisování...)
        self.env = dict(os.environ, GIT_CONFIG_NOSYSTEM="1", GIT_CONFIG_GLOBAL=str(empty_config))
        path.mkdir()
        self.git("init", "-q", "-b", "main")
        self.git("config", "user.name", "Student")
        self.git("config", "user.email", "student@example.com")
        self.git("config", "commit.gpgsign", "false")

    def git(self, *args, env=None) -> str:
        result = subprocess.run(
            ["git", *args], cwd=self.path, check=True, capture_output=True, text=True,
            env=dict(self.env, **(env or {})),
        )
        return result.stdout.strip()

    @staticmethod
    def _date_env(minute: int) -> dict:
        stamp = f"@{BASE_TIME + minute * 60} +0000"
        return {"GIT_AUTHOR_DATE": stamp, "GIT_COMMITTER_DATE": stamp}

    def commit(self, message: str, minute: int) -> str:
        self._counter += 1
        (self.path / f"file{self._counter}.txt").write_text(message + "\n")
        self.git("add", ".")
        self.git("commit", "-q", "-m", message, env=self._date_env(minute))
        return self.git("rev-parse", "HEAD")

    def merge(self, branch: str, minute: int) -> str:
        self.git("merge", "-q", "--no-ff", "-m", f"Merge branch '{branch}'", branch,
                 env=self._date_env(minute))
        return self.git("rev-parse", "HEAD")


def assert_graph_is_consistent(commits):
    """Obecné invarianty vykresleného grafu."""
    row = {c.hash: c.table_row for c in commits}
    # 1) Potomek je vždy nad rodičem (hrany vedou jen dolů)
    for commit in commits:
        for parent in commit.parents:
            if parent in row:
                assert row[commit.hash] < row[parent], f"{commit.message} není nad rodičem"
    # 2) Dvě větve ve stejné lane se nepřekrývají (včetně svislých částí spojnic)
    spans = GraphLayout._branch_row_spans(commits)
    lanes = {}
    for commit in commits:
        lanes.setdefault(commit.x, set()).add(commit.branch)
    for x, branches in lanes.items():
        intervals = sorted(spans[b] for b in branches)
        for (a_start, a_end), (b_start, b_end) in zip(intervals, intervals[1:]):
            assert a_end < b_start, f"větve v lane x={x} se překrývají: {intervals}"


@pytest.fixture
def feature_repo(tmp_path):
    """main: c1 - c2 - c3 - M, feature: c2 - f1 - f2 (sloučeno do M), větev aaa-old na c1."""
    repo = GitRepoBuilder(tmp_path / "feature_repo")
    shas = {}
    shas["c1"] = repo.commit("c1", 1)
    shas["c2"] = repo.commit("c2", 2)
    repo.git("tag", "-a", "v1.0", "-m", "Release 1.0")
    repo.git("switch", "-q", "-c", "feature")
    shas["f1"] = repo.commit("f1", 3)
    shas["f2"] = repo.commit("f2", 4)
    repo.git("switch", "-q", "main")
    shas["c3"] = repo.commit("c3", 5)
    shas["M"] = repo.merge("feature", 6)
    repo.git("branch", "aaa-old", shas["c1"])  # abecedně před main
    return repo, shas


class TestBranchAnalyzerOnRealRepo:

    def test_main_has_priority_and_feature_gets_its_commits(self, feature_repo):
        repo, shas = feature_repo
        git_repo = GitRepository(str(repo.path))
        assert git_repo.load_repository()

        commit_map = BranchAnalyzer(git_repo.repo).build_commit_branch_map()

        assert commit_map[shas["c1"]] == "main"  # ne aaa-old, i když je abecedně dřív
        assert commit_map[shas["M"]] == "main"
        # f1, f2 jsou dosažitelné i z main (přes merge) - main má přednost
        assert commit_map[shas["f1"]] == "main"
        assert len(commit_map) == 6

    def test_unmerged_branch_keeps_its_commits(self, tmp_path):
        repo = GitRepoBuilder(tmp_path / "r")
        base = repo.commit("base", 1)
        repo.git("switch", "-q", "-c", "topic")
        topic = repo.commit("topic work", 2)
        repo.git("switch", "-q", "main")
        tip = repo.commit("main work", 3)

        git_repo = GitRepository(str(repo.path))
        git_repo.load_repository()
        commit_map = BranchAnalyzer(git_repo.repo).build_commit_branch_map()

        assert commit_map == {base: "main", tip: "main", topic: "topic"}

    def test_remote_only_commits(self, tmp_path):
        repo = GitRepoBuilder(tmp_path / "r")
        base = repo.commit("base", 1)
        repo.git("switch", "-q", "-c", "tmp")
        remote_only = repo.commit("pushed by classmate", 2)
        repo.git("switch", "-q", "main")
        repo.git("remote", "add", "origin", "https://example.invalid/repo.git")
        repo.git("update-ref", "refs/remotes/origin/main", base)
        repo.git("update-ref", "refs/remotes/origin/feature-x", remote_only)
        repo.git("branch", "-q", "-D", "tmp")

        git_repo = GitRepository(str(repo.path))
        git_repo.load_repository()
        local_map, remote_map = BranchAnalyzer(git_repo.repo).build_commit_branch_map_with_remote()

        assert local_map == {base: "main"}
        assert remote_map == {remote_only: "origin/feature-x"}

        local_commits = git_repo.parse_commits()
        assert [c.hash for c in local_commits] == [base]

        all_commits = git_repo.parse_commits_with_remote()
        by_hash = {c.hash: c for c in all_commits}
        assert by_hash[remote_only].is_remote
        assert by_hash[remote_only].branch == "origin/feature-x"
        assert not by_hash[base].is_remote


class TestFullPipelineOnRealRepo:

    def test_commits_have_full_hashes_and_tags(self, feature_repo):
        repo, shas = feature_repo
        git_repo = GitRepository(str(repo.path))
        git_repo.load_repository()

        commits = git_repo.parse_commits()
        by_hash = {c.hash: c for c in commits}

        assert set(by_hash) == set(shas.values())
        assert by_hash[shas["M"]].parents == [shas["c3"], shas["f2"]]
        assert [t.name for t in by_hash[shas["c2"]].tags] == ["v1.0"]
        assert "Release 1.0" in by_hash[shas["c2"]].tags[0].message

    def test_merge_branch_detected_after_feature_deleted(self, feature_repo):
        repo, shas = feature_repo
        repo.git("branch", "-q", "-d", "feature")

        git_repo = GitRepository(str(repo.path))
        git_repo.load_repository()
        commits = git_repo.parse_commits()
        merge_branches = git_repo.get_merge_branches()

        assert len(merge_branches) == 1
        merge_branch = merge_branches[0]
        assert merge_branch.branch_point_hash == shas["c2"]
        assert merge_branch.merge_point_hash == shas["M"]
        assert merge_branch.commits_in_branch == [shas["f2"], shas["f1"]]

        by_hash = {c.hash: c for c in commits}
        assert by_hash[shas["f1"]].branch == f"merge-{shas['M']}"
        assert by_hash[shas["f1"]].is_merge_branch

        positioned = GraphLayout(commits, merge_branches=merge_branches).calculate_positions()
        assert_graph_is_consistent(positioned)

    def test_stats_ignore_wip_and_virtual_branches(self, feature_repo):
        repo, shas = feature_repo
        repo.git("branch", "-q", "-d", "feature")
        (repo.path / "untracked.txt").write_text("work in progress\n")

        git_repo = GitRepository(str(repo.path))
        git_repo.load_repository()
        commits = git_repo.parse_commits()

        assert any(c.is_uncommitted for c in commits)
        stats = git_repo.get_repository_stats()
        assert stats["commits"] == 6        # bez WIP pseudo-commitu
        assert stats["authors"] == 1        # WIP nemá autora
        assert stats["branches"] == 2       # main + aaa-old, ne merge-<hash>
        assert stats["tags"] == 1

    def test_layout_of_real_repo_is_consistent(self, feature_repo):
        repo, _ = feature_repo
        git_repo = GitRepository(str(repo.path))
        git_repo.load_repository()
        commits = git_repo.parse_commits()

        positioned = GraphLayout(commits, merge_branches=git_repo.get_merge_branches()).calculate_positions()

        assert len(positioned) == 6
        assert_graph_is_consistent(positioned)

    def test_clock_skew_keeps_child_above_parent(self, tmp_path):
        """Autor s rozjetými hodinami: potomek má starší datum než rodič."""
        repo = GitRepoBuilder(tmp_path / "skew")
        parent = repo.commit("parent (clock in the future)", 100)
        child = repo.commit("child", 50)

        git_repo = GitRepository(str(repo.path))
        git_repo.load_repository()
        positioned = GraphLayout(git_repo.parse_commits()).calculate_positions()

        assert [c.hash for c in positioned] == [child, parent]
        assert_graph_is_consistent(positioned)


def _c(hash_, branch, parents, minute):
    return Commit(hash=hash_, message=hash_, short_message=hash_, author="T", author_short="T",
                  author_email="t@e", date=datetime(2025, 1, 1, 12, minute, tzinfo=timezone.utc),
                  date_relative="", date_short="", parents=parents, branch=branch, branch_color="#000000")


class TestLaneRecycling:

    def test_lane_is_not_reused_while_branch_line_still_runs(self):
        """Větev X končí commitem X1, ale její spojnice vede až k m1 - lane nesmí převzít Y."""
        commits = [
            _c("m2", "main", ["m1"], 11),
            _c("X2", "X", ["X1"], 10),
            _c("X1", "X", ["m1"], 9),
            _c("Y2", "Y", ["Y1"], 8),
            _c("Y1", "Y", ["m1"], 7),
            _c("m1", "main", [], 1),
        ]
        layout = GraphLayout(commits)
        positioned = layout.calculate_positions()

        assert layout.branch_lanes["X"] != layout.branch_lanes["Y"]
        assert_graph_is_consistent(positioned)

    def test_lane_is_reused_after_branch_really_ends(self):
        """Když spojnice X skončí dřív, než Y začne, Y smí lane recyklovat."""
        commits = [
            _c("m3", "main", ["m2"], 11),
            _c("X1", "X", ["m2"], 10),
            _c("m2", "main", ["m1"], 9),
            _c("Y1", "Y", ["m1"], 8),
            _c("m1", "main", [], 1),
        ]
        layout = GraphLayout(commits)
        layout.calculate_positions()

        assert layout.branch_lanes["X"] == layout.branch_lanes["Y"] == 1

    def test_merge_line_reserves_lane_up_to_merge_commit(self):
        """Merge hrana vede v lane slučované větve nahoru až k merge commitu."""
        commits = [
            _c("M", "main", ["m1", "F1"], 10),
            _c("Z1", "Z", ["m1"], 9),       # krátká větev mezi merge commitem a F1
            _c("F1", "F", ["m1"], 8),
            _c("m1", "main", [], 1),
        ]
        layout = GraphLayout(commits)
        positioned = layout.calculate_positions()

        assert layout.branch_lanes["Z"] != layout.branch_lanes["F"]
        assert_graph_is_consistent(positioned)

    def test_order_commits_same_timestamp_keeps_topology(self):
        parent = _c("P", "main", [], 5)
        child = _c("C", "main", ["P"], 5)
        # Stejný čas, rodič na vstupu první - výstup musí mít potomka nahoře
        assert [c.hash for c in order_commits([parent, child])] == ["C", "P"]
