import tkinter as tk
from typing import List, Dict, Tuple
from utils.data_structures import Commit


class GraphDrawer:
    def __init__(self):
        self.node_radius = 8
        self.line_width = 2
        self.font_size = 10
        self.column_widths = {}

    def draw_graph(self, canvas: tk.Canvas, commits: List[Commit]):
        if not commits:
            return

        self._calculate_column_widths(canvas, commits)
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

    def _calculate_column_widths(self, canvas: tk.Canvas, commits: List[Commit]):
        font = ('Arial', self.font_size)

        max_message_width = 0
        max_description_width = 0
        max_author_width = 0
        max_email_width = 0
        max_date_width = 0

        for commit in commits:
            message_width = canvas.tk.call("font", "measure", font, commit.message)
            max_message_width = max(max_message_width, message_width)

            if commit.description:
                desc_width = canvas.tk.call("font", "measure", font, commit.description)
                max_description_width = max(max_description_width, desc_width)

            author_width = canvas.tk.call("font", "measure", font, commit.author)
            max_author_width = max(max_author_width, author_width)

            email_width = canvas.tk.call("font", "measure", font, commit.author_email)
            max_email_width = max(max_email_width, email_width)

            date_width = canvas.tk.call("font", "measure", font, commit.date_short)
            max_date_width = max(max_date_width, date_width)

        self.column_widths = {
            'message': max_message_width + 20,
            'description': max_description_width + 20,
            'author': max_author_width + 20,
            'email': max_email_width + 20,
            'date': max_date_width + 20
        }

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

            text_x = x + 20

            canvas.create_text(
                text_x, y,
                text=commit.message,
                anchor='w',
                font=('Arial', self.font_size),
                fill='black'
            )
            text_x += self.column_widths['message']

            if commit.description:
                canvas.create_text(
                    text_x, y,
                    text=commit.description,
                    anchor='w',
                    font=('Arial', self.font_size),
                    fill='#666666'
                )
            text_x += self.column_widths['description']

            canvas.create_text(
                text_x, y,
                text=commit.author,
                anchor='w',
                font=('Arial', self.font_size),
                fill='#333333'
            )
            text_x += self.column_widths['author']

            canvas.create_text(
                text_x, y,
                text=commit.author_email,
                anchor='w',
                font=('Arial', self.font_size),
                fill='#666666'
            )
            text_x += self.column_widths['email']

            canvas.create_text(
                text_x, y,
                text=commit.date_short,
                anchor='w',
                font=('Arial', self.font_size),
                fill='#666666'
            )