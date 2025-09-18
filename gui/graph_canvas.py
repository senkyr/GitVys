import tkinter as tk
from tkinter import ttk
from typing import List, Dict
from utils.data_structures import Commit
from visualization.graph_drawer import GraphDrawer


class GraphCanvas(ttk.Frame):
    def __init__(self, parent):
        super().__init__(parent)
        self.commits: List[Commit] = []
        self.graph_drawer = GraphDrawer()
        self.setup_ui()

    def setup_ui(self):
        self.columnconfigure(0, weight=1)
        self.rowconfigure(0, weight=1)

        self.canvas_frame = ttk.Frame(self)
        self.canvas_frame.grid(row=0, column=0, sticky='nsew')
        self.canvas_frame.columnconfigure(0, weight=1)
        self.canvas_frame.rowconfigure(0, weight=1)

        self.canvas = tk.Canvas(
            self.canvas_frame,
            bg='white',
            scrollregion=(0, 0, 1000, 1000)
        )
        self.canvas.grid(row=0, column=0, sticky='nsew')

        self.v_scrollbar = ttk.Scrollbar(
            self.canvas_frame,
            orient='vertical',
            command=self.canvas.yview
        )
        self.v_scrollbar.grid(row=0, column=1, sticky='ns')
        self.canvas.configure(yscrollcommand=self.v_scrollbar.set)

        self.h_scrollbar = ttk.Scrollbar(
            self.canvas_frame,
            orient='horizontal',
            command=self.canvas.xview
        )
        self.h_scrollbar.grid(row=1, column=0, sticky='ew')
        self.canvas.configure(xscrollcommand=self.h_scrollbar.set)

        self.canvas.bind('<MouseWheel>', self.on_mousewheel)
        self.canvas.bind('<Button-4>', self.on_mousewheel)
        self.canvas.bind('<Button-5>', self.on_mousewheel)

    def update_graph(self, commits: List[Commit]):
        self.commits = commits
        self.canvas.delete('all')

        if not commits:
            return

        self.graph_drawer.draw_graph(self.canvas, commits)

        max_x = max(commit.x for commit in commits) + 100
        max_y = max(commit.y for commit in commits) + 100
        self.canvas.configure(scrollregion=(0, 0, max_x, max_y))

    def on_mousewheel(self, event):
        if event.delta:
            delta = -1 * (event.delta / 120)
        else:
            delta = -1 if event.num == 4 else 1

        self.canvas.yview_scroll(int(delta), "units")