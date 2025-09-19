import tkinter as tk
from typing import List, Dict, Tuple
from utils.data_structures import Commit


class GraphDrawer:
    def __init__(self):
        self.node_radius = 8
        self.line_width = 2
        self.font_size = 10
        self.column_widths = {}
        self.tooltip = None

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
            # Kombinovaná šířka message + description s mezerou
            message_width = canvas.tk.call("font", "measure", font, commit.message)
            if commit.description_short:
                desc_width = canvas.tk.call("font", "measure", font, commit.description_short)
                combined_width = message_width + 20 + desc_width  # 20px mezera
            else:
                combined_width = message_width
            max_message_width = max(max_message_width, combined_width)

            author_width = canvas.tk.call("font", "measure", font, commit.author)
            max_author_width = max(max_author_width, author_width)

            email_width = canvas.tk.call("font", "measure", font, commit.author_email)
            max_email_width = max(max_email_width, email_width)

            date_width = canvas.tk.call("font", "measure", font, commit.date_short)
            max_date_width = max(max_date_width, date_width)

        self.column_widths = {
            'message': max_message_width + 20,
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

            # Vytvořit kombinovaný text message + description
            if commit.description_short:
                # Message v černé + description v šedé
                # Nejdříve vykreslit celý kombinovaný text v černé
                canvas.create_text(
                    text_x, y,
                    text=commit.message,
                    anchor='w',
                    font=('Arial', self.font_size),
                    fill='black'
                )

                # Změřit šířku message pro pozici description
                message_width = canvas.tk.call("font", "measure", ('Arial', self.font_size), commit.message)
                desc_x = text_x + message_width + 20  # 20px mezera pro lepší rozlišení

                # Vykreslit description v šedé s tooltip
                desc_item = canvas.create_text(
                    desc_x, y,
                    text=commit.description_short,
                    anchor='w',
                    font=('Arial', self.font_size),
                    fill='#666666',
                    tags=f"desc_{commit.hash}"
                )

                # Přidat event handlers pro tooltip pouze pokud má původní description více obsahu
                if commit.description and commit.description.strip() != commit.description_short:
                    canvas.tag_bind(f"desc_{commit.hash}", "<Enter>",
                        lambda e, desc=commit.description: self._show_tooltip(e, desc))
                    canvas.tag_bind(f"desc_{commit.hash}", "<Leave>",
                        lambda e: self._hide_tooltip())
            else:
                # Jen message bez description
                canvas.create_text(
                    text_x, y,
                    text=commit.message,
                    anchor='w',
                    font=('Arial', self.font_size),
                    fill='black'
                )

            text_x += self.column_widths['message']

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

    def _show_tooltip(self, event, description_text: str):
        """Zobrazí tooltip s kompletním description textem."""
        if not description_text or not description_text.strip():
            return

        self._hide_tooltip()

        # Vytvořit tooltip okno
        self.tooltip = tk.Toplevel()
        self.tooltip.wm_overrideredirect(True)
        self.tooltip.wm_attributes("-topmost", True)

        # Nastavit pozici tooltip okna
        x = event.x_root + 10
        y = event.y_root + 10
        self.tooltip.wm_geometry(f"+{x}+{y}")

        # Vytvořit label s textem
        label = tk.Label(
            self.tooltip,
            text=description_text,
            background="#ffffe0",
            foreground="black",
            font=('Arial', 9),
            wraplength=400,
            justify="left",
            relief="solid",
            borderwidth=1,
            padx=5,
            pady=3
        )
        label.pack()

    def _hide_tooltip(self):
        """Skryje tooltip okno."""
        if self.tooltip:
            self.tooltip.destroy()
            self.tooltip = None