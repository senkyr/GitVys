"""Integrační testy nad skutečnými Git repozitáři (žádné mocky GitPythonu).

Ostatní "integrační" testy GitPython mockují, takže neověří, že aplikace
správně čte skutečnou historii. Tady se repozitáře staví přes `git` CLI
v dočasné složce s pevnými časy commitů.
"""

import os
import subprocess
from datetime import datetime, timezone

from unittest.mock import MagicMock

import pytest

from gui.repo_manager import RepositoryManager
from repo.head import DETACHED_HEAD, HeadState
from repo.repository import GitRepository
from repo.parsers.branch_analyzer import BranchAnalyzer
from utils.data_structures import Commit
from utils.constants import COMMIT_START_X, FLAG_SLOT_WIDTH
from utils.translations import get_translation_manager
from visualization.drawing.commit_drawer import CommitDrawer
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

    def test_uncommitted_changes_are_classified(self, tmp_path):
        """Neuložená změna sledovaného souboru a nový soubor = 'working', ne 'staged'."""
        repo = GitRepoBuilder(tmp_path / "wip")
        repo.commit("first", 1)
        (repo.path / "file1.txt").write_text("changed but not staged\n")
        (repo.path / "new.txt").write_text("untracked\n")

        git_repo = GitRepository(str(repo.path))
        git_repo.load_repository()
        info = git_repo.get_uncommitted_changes()

        assert info["uncommitted_type"] == "working"
        assert info["staged_files"] == []
        assert sorted(info["working_files"]) == ["file1.txt", "new.txt"]

        repo.git("add", "new.txt")
        info = git_repo.get_uncommitted_changes()
        assert info["uncommitted_type"] == "both"
        assert info["staged_files"] == ["new.txt"]

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


def _load(repo, with_remote=False):
    git_repo = GitRepository(str(repo.path))
    assert git_repo.load_repository()
    commits = git_repo.parse_commits_with_remote() if with_remote else git_repo.parse_commits()
    return git_repo, commits


class TestHeadStateOnRealRepo:
    """Graf musí vycházet z toho, kde uživatel opravdu stojí (HEAD)."""

    def test_wip_on_new_branch_hangs_on_head_commit(self, tmp_path):
        """Nová větev bez vlastního commitu: WIP navazuje na commit pod HEAD."""
        repo = GitRepoBuilder(tmp_path / "new_branch")
        repo.commit("c1", 1)
        c2 = repo.commit("c2", 2)
        repo.git("switch", "-q", "-c", "feature")
        (repo.path / "file1.txt").write_text("rozpracováno\n")

        git_repo, commits = _load(repo)
        wip = next(c for c in commits if c.is_uncommitted)

        assert git_repo.head == HeadState(branch="feature", commit=c2)
        assert wip.branch == "feature"
        assert wip.parents == [c2]
        # Commit pod HEAD patří v grafu větvi main, WIP má vlastní sloupec
        positioned = GraphLayout(commits, merge_branches=git_repo.get_merge_branches()).calculate_positions()
        by_hash = {c.hash: c for c in positioned}
        assert by_hash[c2].branch == "main"
        assert by_hash[wip.hash].x != by_hash[c2].x
        assert_graph_is_consistent(positioned)

    def test_wip_follows_head_not_newest_commit_of_branch(self, tmp_path):
        """Větev stojí na starším commitu jiné větve: WIP patří pod HEAD, ne jinam."""
        repo = GitRepoBuilder(tmp_path / "behind")
        c1 = repo.commit("c1", 1)
        repo.commit("c2", 2)
        repo.git("switch", "-q", "-c", "old", c1)
        (repo.path / "file1.txt").write_text("rozpracováno\n")

        _, commits = _load(repo)
        wip = next(c for c in commits if c.is_uncommitted)

        assert wip.branch == "old"
        assert wip.parents == [c1]

    def test_detached_head_commits_are_visible(self, tmp_path):
        """Commit vytvořený při odpojeném HEAD nepatří žádné větvi, ale v grafu být musí."""
        repo = GitRepoBuilder(tmp_path / "detached")
        repo.commit("c1", 1)
        c2 = repo.commit("c2", 2)
        repo.git("checkout", "-q", "--detach")
        lost = repo.commit("mimo větve", 3)
        (repo.path / "file1.txt").write_text("rozpracováno\n")

        git_repo, commits = _load(repo)
        by_hash = {c.hash: c for c in commits}
        wip = next(c for c in commits if c.is_uncommitted)

        assert git_repo.head.is_detached
        assert by_hash[lost].branch == DETACHED_HEAD
        assert by_hash[lost].parents == [c2]
        assert by_hash[c2].branch == "main"
        assert wip.branch == DETACHED_HEAD
        assert wip.parents == [lost]
        # Odpojený HEAD není větev
        assert git_repo.get_repository_stats()["branches"] == 1
        positioned = GraphLayout(commits, merge_branches=git_repo.get_merge_branches()).calculate_positions()
        assert_graph_is_consistent(positioned)

    def test_detached_head_is_flagged_in_remote_view(self, tmp_path):
        """V pohledu s remote větvemi se vlaječky řídí is_branch_head - i u odpojeného HEAD."""
        repo = GitRepoBuilder(tmp_path / "detached_remote")
        repo.commit("c1", 1)
        repo.git("checkout", "-q", "--detach")
        lost = repo.commit("mimo větve", 2)

        _, commits = _load(repo, with_remote=True)
        by_hash = {c.hash: c for c in commits}

        assert by_hash[lost].branch == DETACHED_HEAD
        assert by_hash[lost].is_branch_head
        assert by_hash[lost].branch_head_type == "local"

    def test_detached_head_on_branch_commit_adds_nothing(self, tmp_path):
        """Odpojený HEAD na commitu větve: žádný commit navíc, nic se nepřejmenuje."""
        repo = GitRepoBuilder(tmp_path / "detached_clean")
        c1 = repo.commit("c1", 1)
        repo.commit("c2", 2)
        repo.git("checkout", "-q", c1)

        git_repo, commits = _load(repo)

        assert git_repo.head == HeadState(branch=None, commit=c1)
        assert [c.branch for c in commits] == ["main", "main"]

    def test_wip_in_repository_without_commits(self, tmp_path):
        """Čerstvý `git init` s prvními soubory: jen WIP na budoucí větvi."""
        repo = GitRepoBuilder(tmp_path / "unborn")
        (repo.path / "prvni.txt").write_text("první soubor\n")

        git_repo, commits = _load(repo)

        assert git_repo.head == HeadState(branch="main", commit=None)
        assert len(commits) == 1
        assert commits[0].is_uncommitted
        assert commits[0].branch == "main"
        assert commits[0].parents == []

    @pytest.mark.parametrize("language, expected", [("cs", "2 soubory"), ("en", "2 files")])
    def test_wip_description_follows_interface_language(self, tmp_path, monkeypatch, language, expected):
        repo = GitRepoBuilder(tmp_path / "wip_language")
        repo.commit("c1", 1)
        (repo.path / "file1.txt").write_text("změna\n")
        (repo.path / "novy.txt").write_text("nový\n")
        monkeypatch.setattr(get_translation_manager(), "_current_language", language)

        _, commits = _load(repo)
        wip = next(c for c in commits if c.is_uncommitted)

        assert wip.description == expected


def _flags(commit):
    return [(flag.name, flag.availability) for flag in commit.extra_flags]


class TestBranchFlagsOnRealRepo:
    """Každá větev má v grafu vlaječku, i když její poslední commit patří jiné větvi."""

    def test_branch_on_tip_of_main_gets_extra_flag(self, tmp_path):
        repo = GitRepoBuilder(tmp_path / "same_tip")
        repo.commit("c1", 1)
        c2 = repo.commit("c2", 2)
        repo.git("branch", "feature")
        repo.git("branch", "bugfix")

        git_repo, commits = _load(repo)
        by_hash = {c.hash: c for c in commits}

        assert by_hash[c2].branch == "main"
        assert _flags(by_hash[c2]) == [("bugfix", "local_only"), ("feature", "local_only")]
        assert by_hash[c2].head_branch == "main"
        assert git_repo.flag_columns == 3  # main + bugfix + feature na jednom řádku

    def test_branch_behind_main_gets_flag_without_widening_graph(self, tmp_path):
        repo = GitRepoBuilder(tmp_path / "behind_main")
        c1 = repo.commit("c1", 1)
        repo.commit("c2", 2)
        repo.git("branch", "backup", c1)

        git_repo, commits = _load(repo)
        by_hash = {c.hash: c for c in commits}

        assert _flags(by_hash[c1]) == [("backup", "local_only")]
        assert by_hash[c1].head_branch == ""
        # c1 nemá vlastní vlaječku, takže na žádném řádku nejsou dvě
        assert git_repo.flag_columns == 1

    def test_current_branch_is_marked_on_head_commit(self, tmp_path):
        """Aktuální větev bez vlastního commitu: vlaječka i značka HEAD jsou u commitu pod ní."""
        repo = GitRepoBuilder(tmp_path / "current")
        repo.commit("c1", 1)
        c2 = repo.commit("c2", 2)
        repo.git("switch", "-q", "-c", "feature")
        (repo.path / "file1.txt").write_text("rozpracováno\n")

        _, commits = _load(repo)
        by_hash = {c.hash: c for c in commits}
        wip = next(c for c in commits if c.is_uncommitted)

        assert by_hash[c2].head_branch == "feature"
        assert _flags(by_hash[c2]) == [("feature", "local_only")]
        # Vlaječku větve nese commit, na který ukazuje, ne WIP uzel
        assert CommitDrawer(MagicMock())._analyze(commits)["wip_flag_ids"] == set()
        assert wip.extra_flags == []

    def test_wip_in_empty_repository_carries_the_flag(self, tmp_path):
        repo = GitRepoBuilder(tmp_path / "empty")
        (repo.path / "prvni.txt").write_text("první soubor\n")

        _, commits = _load(repo)

        assert CommitDrawer(MagicMock())._analyze(commits)["wip_flag_ids"] == {id(commits[0])}

    def test_detached_head_on_branch_commit_is_flagged(self, tmp_path):
        """Odpojený HEAD na starším commitu větve musí být v grafu vidět i bez změn."""
        repo = GitRepoBuilder(tmp_path / "detached_flag")
        c1 = repo.commit("c1", 1)
        repo.commit("c2", 2)
        repo.git("checkout", "-q", c1)

        _, commits = _load(repo)
        by_hash = {c.hash: c for c in commits}

        assert _flags(by_hash[c1]) == [(DETACHED_HEAD, "local_only")]
        assert by_hash[c1].head_branch == DETACHED_HEAD

    def test_remote_branches_without_own_commits_are_flagged(self, tmp_path):
        """Větev na serveru sloučená fast-forwardem a místní větev se stejným protějškem."""
        repo = GitRepoBuilder(tmp_path / "remote_flags")
        c1 = repo.commit("c1", 1)
        c2 = repo.commit("c2", 2)
        repo.git("branch", "shared", c1)
        repo.git("remote", "add", "origin", "https://example.invalid/repo.git")
        repo.git("update-ref", "refs/remotes/origin/main", c2)
        repo.git("update-ref", "refs/remotes/origin/merged", c2)
        repo.git("update-ref", "refs/remotes/origin/shared", c1)

        _, local_commits = _load(repo)
        local = {c.hash: c for c in local_commits}
        # Místní pohled vzdálené větve neukazuje
        assert _flags(local[c2]) == []
        assert _flags(local[c1]) == [("shared", "local_only")]

        git_repo, commits = _load(repo, with_remote=True)
        by_hash = {c.hash: c for c in commits}

        assert by_hash[c2].branch_head_type == "both"  # main místně i na serveru
        assert _flags(by_hash[c2]) == [("merged", "remote_only")]
        assert _flags(by_hash[c1]) == [("shared", "both")]
        assert git_repo.flag_columns == 2

    def test_graph_moves_right_to_make_room_for_flags(self, tmp_path):
        repo = GitRepoBuilder(tmp_path / "layout")
        repo.commit("c1", 1)
        repo.git("branch", "feature")

        git_repo, commits = _load(repo)
        positioned = RepositoryManager._build_layout(git_repo, commits)

        assert git_repo.flag_columns == 2
        assert positioned[0].x == COMMIT_START_X + FLAG_SLOT_WIDTH


class TestFetchOnRealRepo:
    """`git fetch` spuštěný aplikací nad skutečným vzdáleným repozitářem (na disku)."""

    @pytest.fixture
    def cloned(self, tmp_path):
        upstream = GitRepoBuilder(tmp_path / "upstream")
        upstream.commit("u1", 1)
        upstream.git("branch", "old-topic")
        clone_path = tmp_path / "clone"
        subprocess.run(["git", "clone", "-q", str(upstream.path), str(clone_path)],
                       check=True, capture_output=True, env=upstream.env)
        return upstream, clone_path

    def test_fetch_updates_and_prunes_remote_tracking_branches(self, cloned):
        upstream, clone_path = cloned
        new_commit = upstream.commit("u2", 2)
        upstream.git("branch", "-q", "-D", "old-topic")

        git_repo = GitRepository(str(clone_path))
        assert git_repo.load_repository()
        try:
            before = {c.hash for c in git_repo.parse_commits_with_remote()}
            RepositoryManager._fetch(git_repo.repo, str(upstream.path))
            after = git_repo.parse_commits_with_remote()
            remote_branches = {ref.name for ref in git_repo.repo.remote().refs}
        finally:
            git_repo.repo.close()

        assert new_commit not in before
        by_hash = {c.hash: c for c in after}
        assert by_hash[new_commit].branch == "origin/main"
        assert "origin/old-topic" not in remote_branches

    def test_fetch_leaves_local_branches_and_work_tree_alone(self, cloned):
        upstream, clone_path = cloned
        upstream.commit("u2", 2)
        (clone_path / "file1.txt").write_text("rozpracováno\n")

        git_repo = GitRepository(str(clone_path))
        assert git_repo.load_repository()
        try:
            local_before = git_repo.repo.heads["main"].commit.hexsha
            RepositoryManager._fetch(git_repo.repo, str(upstream.path))
            local_after = git_repo.repo.heads["main"].commit.hexsha
        finally:
            git_repo.repo.close()

        assert local_after == local_before
        assert (clone_path / "file1.txt").read_text() == "rozpracováno\n"
