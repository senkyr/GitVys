import tkinter as tk
from tkinter import ttk, messagebox
import threading
try:
    from tkinterdnd2 import TkinterDnD
except ImportError:
    TkinterDnD = None
from repo.repository import GitRepository
from visualization.layout import GraphLayout
from gui.drag_drop import DragDropFrame
from gui.graph_canvas import GraphCanvas


class MainWindow:
    def __init__(self):
        if TkinterDnD is not None:
            self.root = TkinterDnD.Tk()
        else:
            self.root = tk.Tk()
        self.root.title("Git Visualizer")

        initial_width = 600
        initial_height = 400
        self.root.geometry(f"{initial_width}x{initial_height}")
        self.root.minsize(400, 300)

        self._center_window(initial_width, initial_height)

        self.git_repo = None
        self.setup_ui()

    def _center_window(self, width: int, height: int):
        screen_width = self.root.winfo_screenwidth()
        screen_height = self.root.winfo_screenheight()

        x = max(0, (screen_width - width) // 2)
        y = max(0, (screen_height - height) // 2)

        if x + width > screen_width:
            x = screen_width - width
        if y + height > screen_height:
            y = screen_height - height

        x = max(0, x)
        y = max(0, y)

        self.root.geometry(f"{width}x{height}+{x}+{y}")

    def _resize_window_for_content(self, commits):
        if not commits:
            return

        self.root.update_idletasks()

        canvas = self.graph_canvas.canvas
        table_width = self._calculate_table_width(canvas, commits)

        commit_count = len(commits)
        commit_height = 30
        header_height = 80
        status_height = 40
        margins = 60

        content_width = table_width + 200
        content_height = (commit_count * commit_height) + header_height + status_height + margins

        screen_width = self.root.winfo_screenwidth()
        screen_height = self.root.winfo_screenheight()
        margin = 100

        window_width = min(content_width, screen_width - margin)
        window_height = min(content_height, screen_height - margin)

        window_width = max(window_width, 800)
        window_height = max(window_height, 600)

        self._center_window(window_width, window_height)

    def _calculate_table_width(self, canvas, commits):
        if not hasattr(self.graph_canvas.graph_drawer, 'column_widths'):
            return 1000

        column_widths = self.graph_canvas.graph_drawer.column_widths
        total_width = sum(column_widths.values()) if column_widths else 1000

        max_branch_lanes = len(set(commit.branch for commit in commits))
        branch_width = max_branch_lanes * 150

        return total_width + branch_width

    def setup_ui(self):
        self.root.columnconfigure(0, weight=1)
        self.root.rowconfigure(0, weight=1)

        self.main_frame = ttk.Frame(self.root)
        self.main_frame.grid(row=0, column=0, sticky='nsew', padx=10, pady=10)
        self.main_frame.columnconfigure(0, weight=1)
        self.main_frame.rowconfigure(1, weight=1)

        self.header_frame = ttk.Frame(self.main_frame)
        self.header_frame.grid(row=0, column=0, sticky='ew', pady=(0, 10))
        self.header_frame.columnconfigure(1, weight=1)

        self.back_button = ttk.Button(
            self.header_frame,
            text="← Zpět",
            command=self.show_repository_selection
        )

        self.title_label = ttk.Label(
            self.header_frame,
            text="Git Visualizer - Přetáhni složku repozitáře",
            font=('Arial', 16, 'bold')
        )
        self.title_label.grid(row=0, column=1, sticky='w')

        self.content_frame = ttk.Frame(self.main_frame)
        self.content_frame.grid(row=1, column=0, sticky='nsew')
        self.content_frame.columnconfigure(0, weight=1)
        self.content_frame.rowconfigure(0, weight=1)

        self.drag_drop_frame = DragDropFrame(
            self.content_frame,
            on_drop_callback=self.on_repository_selected
        )
        self.drag_drop_frame.grid(row=0, column=0, sticky='nsew')

        self.graph_canvas = GraphCanvas(self.content_frame, on_drop_callback=self.on_repository_selected)

        self.status_frame = ttk.Frame(self.main_frame)
        self.status_frame.grid(row=2, column=0, sticky='ew', pady=(10, 0))
        self.status_frame.columnconfigure(1, weight=1)

        self.status_label = ttk.Label(self.status_frame, text="Připraven")
        self.status_label.grid(row=0, column=0, sticky='w')

        self.progress = ttk.Progressbar(
            self.status_frame,
            mode='indeterminate'
        )
        self.progress.grid(row=0, column=1, sticky='ew', padx=(10, 0))

    def on_repository_selected(self, repo_path: str):
        self.update_status("Načítám repozitář...")
        self.progress.start()

        thread = threading.Thread(
            target=self.load_repository,
            args=(repo_path,),
            daemon=True
        )
        thread.start()

    def load_repository(self, repo_path: str):
        try:
            self.git_repo = GitRepository(repo_path)

            if not self.git_repo.load_repository():
                self.root.after(0, self.show_error, "Nepodařilo se načíst Git repozitář")
                return

            commits = self.git_repo.parse_commits()

            if not commits:
                self.root.after(0, self.show_error, "Repozitář neobsahuje žádné commity")
                return

            layout = GraphLayout(commits)
            positioned_commits = layout.calculate_positions()

            self.root.after(0, self.show_graph, positioned_commits)

        except Exception as e:
            self.root.after(0, self.show_error, f"Chyba při načítání repozitáře: {str(e)}")

    def show_graph(self, commits):
        self.drag_drop_frame.grid_remove()
        self.graph_canvas.grid(row=0, column=0, sticky='nsew')
        self.graph_canvas.update_graph(commits)

        self.back_button.grid(row=0, column=0, sticky='w', padx=(0, 10))
        self.title_label.config(text=f"Git Visualizer - {len(commits)} commitů")

        self.root.after(100, lambda: self._resize_window_for_content(commits))

        self.progress.stop()
        self.update_status(f"Načteno {len(commits)} commitů")

    def show_repository_selection(self):
        self.graph_canvas.grid_remove()
        self.drag_drop_frame.grid(row=0, column=0, sticky='nsew')

        self.back_button.grid_remove()
        self.title_label.config(text="Git Visualizer - Přetáhni složku repozitáře")

        self.update_status("Připraven")

    def show_error(self, message: str):
        self.progress.stop()
        self.update_status("Chyba")
        messagebox.showerror("Chyba", message)

    def update_status(self, message: str):
        self.status_label.config(text=message)

    def run(self):
        self.root.mainloop()