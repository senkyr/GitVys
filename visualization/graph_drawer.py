import tkinter as tk
from typing import List, Dict, Tuple
from utils.data_structures import Commit


class GraphDrawer:
    def __init__(self):
        self.node_radius = 8
        self.line_width = 2
        self.font_size = 10

    def draw_graph(self, canvas: tk.Canvas, commits: List[Commit]):
        if not commits:
            return

        self._draw_connections(canvas, commits)
        self._draw_commits(canvas, commits)

    def _draw_connections(self, canvas: tk.Canvas, commits: List[Commit]):
        commit_positions = {commit.hash: (commit.x, commit.y) for commit in commits}

        for commit in commits:
            if commit.parents:
                start_pos = commit_positions.get(commit.hash)
                if start_pos:
                    for parent_hash in commit.parents:
                        end_pos = commit_positions.get(parent_hash)
                        if end_pos:
                            self._draw_line(canvas, start_pos, end_pos, commit.branch_color)

    def _draw_line(self, canvas: tk.Canvas, start: Tuple[int, int], end: Tuple[int, int], color: str):
        canvas.create_line(
            start[0], start[1], end[0], end[1],
            fill=color,
            width=self.line_width,
            smooth=True
        )

    def _draw_commits(self, canvas: tk.Canvas, commits: List[Commit]):
        for commit in commits:
            x, y = commit.x, commit.y

            canvas.create_oval(
                x - self.node_radius, y - self.node_radius,
                x + self.node_radius, y + self.node_radius,
                fill=commit.branch_color,
                outline='black',
                width=1
            )

            canvas.create_text(
                x + 20, y,
                text=f"{commit.hash} {commit.short_message}",
                anchor='w',
                font=('Arial', self.font_size),
                fill='black'
            )

            canvas.create_text(
                x + 20, y + 15,
                text=f"{commit.author_short} • {commit.date_short}",
                anchor='w',
                font=('Arial', self.font_size - 1),
                fill='gray'
            )