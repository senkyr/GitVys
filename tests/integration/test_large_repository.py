"""Výkon a virtualizované kreslení na syntetickém repozitáři s desetitisíci commitů.

Repozitář se vyrobí přes `git fast-import` (sekundy), pak se projde celá
cesta: načtení historie, layout a vykreslení na skrytý canvas. Ověřuje se,
že na canvasu je jen výřez kolem viditelné oblasti (ne statisíce položek)
a že se po posunu pohledu dokreslí správné řádky včetně dlouhých spojnic.
"""

import os
import subprocess
import time

import pytest

from repo.repository import GitRepository
from visualization.layout import GraphLayout
from visualization.graph_drawer import GraphDrawer
from utils.constants import COMMIT_VERTICAL_SPACING

MAIN_COMMITS = 12_000
FEATURE_EVERY = 400      # každých N commitů na main jedna sloučená feature větev
FEATURE_LENGTH = 5
BASE_TIME = 1_600_000_000


def _fast_import_stream() -> bytes:
    """Historie: main + krátké sloučené feature větve + jedna dlouhá větev přes celý graf."""
    lines = []
    mark = 0
    clock = BASE_TIME

    def commit(ref, message, parent=None, merge=None):
        nonlocal mark, clock
        mark += 1
        clock += 60
        data = message.encode('utf-8')
        lines.append(f"commit {ref}")
        lines.append(f"mark :{mark}")
        lines.append(f"committer Student <student@example.com> {clock} +0000")
        lines.append(f"data {len(data)}")
        lines.append(message)
        if parent:
            lines.append(f"from :{parent}")
        if merge:
            lines.append(f"merge :{merge}")
        lines.append(f"M 644 inline file{mark % 50}.txt")
        lines.append(f"data {len(data)}")
        lines.append(message)
        lines.append("")
        return mark

    main_tip = commit("refs/heads/main", "initial commit")
    long_tip = commit("refs/heads/long-lived", "long-lived branch start", parent=main_tip)

    for i in range(1, MAIN_COMMITS):
        main_tip = commit("refs/heads/main", f"main commit {i}", parent=main_tip)
        if i % FEATURE_EVERY == 0:
            feature_tip = main_tip
            for j in range(FEATURE_LENGTH):
                feature_tip = commit("refs/heads/topic", f"feature {i} step {j}", parent=feature_tip)
            main_tip = commit("refs/heads/main", f"Merge branch 'feature-{i}'",
                              parent=main_tip, merge=feature_tip)

    # Dlouhá větev se slučuje až úplně nahoře -> svislá čára přes celý graf
    commit("refs/heads/main", "Merge branch 'long-lived'", parent=main_tip, merge=long_tip)
    lines.append("reset refs/heads/topic")  # topic zmizí -> vzniknou virtuální merge větve
    lines.append("from 0000000000000000000000000000000000000000")
    lines.append("")
    return ("\n".join(lines) + "\n").encode('utf-8')


@pytest.fixture(scope="module")
def large_repo(tmp_path_factory):
    path = tmp_path_factory.mktemp("large") / "repo"
    path.mkdir()
    env = dict(os.environ, GIT_CONFIG_NOSYSTEM="1")
    subprocess.run(["git", "init", "-q", "-b", "main"], cwd=path, check=True, env=env)
    subprocess.run(["git", "fast-import", "--quiet"], cwd=path, check=True, env=env,
                   input=_fast_import_stream(), capture_output=True)
    # fast-import nevyplní pracovní složku - bez checkoutu by se vše jevilo jako smazané (WIP)
    subprocess.run(["git", "checkout", "-q", "-f", "main"], cwd=path, check=True, env=env)
    return path


@pytest.fixture(scope="module")
def positioned_commits(large_repo):
    git_repo = GitRepository(str(large_repo))
    assert git_repo.load_repository()
    commits = git_repo.parse_commits()
    layout = GraphLayout(commits, merge_branches=git_repo.get_merge_branches())
    positioned = layout.calculate_positions()
    git_repo.repo.close()
    return positioned


def test_history_is_loaded_completely(positioned_commits):
    merged_features = (MAIN_COMMITS - 1) // FEATURE_EVERY
    expected = 1 + 1 + (MAIN_COMMITS - 1) + merged_features * (FEATURE_LENGTH + 1) + 1
    assert not any(c.is_uncommitted for c in positioned_commits)
    assert len(positioned_commits) == expected
    # Potomek je vždy nad rodičem
    row = {c.hash: c.table_row for c in positioned_commits}
    assert all(row[c.hash] < row[p] for c in positioned_commits for p in c.parents if p in row)


def test_only_visible_rows_are_drawn(root, positioned_commits):
    import tkinter as tk
    canvas = tk.Canvas(root, width=1000, height=600)
    drawer = GraphDrawer()

    started = time.perf_counter()
    drawer.draw_graph(canvas, positioned_commits)
    draw_seconds = time.perf_counter() - started

    items_top = len(canvas.find_all())
    # Při kreslení všeho by to bylo ~10 položek na každý z ~12 000 řádků
    assert 0 < items_top < 4000, items_top
    assert draw_seconds < 30, draw_seconds

    x1, y1, x2, y2 = drawer.get_content_bounds()
    assert y2 >= len(positioned_commits) * COMMIT_VERTICAL_SPACING
    canvas.configure(scrollregion=(x1, y1, x2, y2))

    # Posun doprostřed grafu: vykreslí se tamější řádky a dlouhá spojnice větve long-lived
    canvas.yview_moveto(0.5)
    assert drawer.render_visible(canvas)
    middle_top = canvas.canvasy(0)
    items_middle = len(canvas.find_all())
    assert items_middle < 4000, items_middle

    row_ys = {c.y for c in positioned_commits}
    drawn_rows = {round(canvas.coords(item)[1]) for item in canvas.find_withtag("commit_text")}
    assert any(abs(y - middle_top) < 600 for y in drawn_rows & row_ys)
    assert min(drawn_rows) > 100  # horní řádky už na canvasu nejsou

    long_lived = [c for c in positioned_commits if c.message == "long-lived branch start"][0]
    crossing = canvas.find_overlapping(long_lived.x - 1, middle_top + 100, long_lived.x + 1, middle_top + 110)
    assert any(canvas.type(item) == "line" for item in crossing), \
        "dlouhá spojnice procházející výřezem musí být vykreslená"

    # Malý posun uvnitř vykresleného výřezu nepřekresluje
    canvas.yview_scroll(1, "units")
    assert not drawer.render_visible(canvas)

    # Konec grafu
    canvas.yview_moveto(1.0)
    assert drawer.render_visible(canvas)
    drawn_messages = {canvas.itemcget(item, "text") for item in canvas.find_withtag("commit_text")}
    assert "initial commit" in drawn_messages


def test_graph_canvas_rerenders_on_scroll(root, positioned_commits):
    """Cesta přes GraphCanvas: změna pohledu -> yscrollcommand -> dokreslení výřezu."""
    from gui.graph_canvas import GraphCanvas

    graph_canvas = GraphCanvas(root)
    graph_canvas.update_graph(positioned_commits)
    root.update()
    canvas = graph_canvas.canvas
    assert len(canvas.find_all()) < 4000

    canvas.yview_moveto(0.5)
    root.update()  # idle callback z yscrollcommand dokreslí výřez

    view_top = canvas.canvasy(0)
    drawn_ys = [canvas.coords(item)[1] for item in canvas.find_withtag("commit_text")]
    assert drawn_ys and min(drawn_ys) <= view_top + 50 <= max(drawn_ys)
    assert len(canvas.find_all()) < 4000
    graph_canvas.destroy()
