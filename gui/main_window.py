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
        self.root.geometry("1200x800")
        self.root.minsize(800, 600)

        self.git_repo = None
        self.setup_ui()

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