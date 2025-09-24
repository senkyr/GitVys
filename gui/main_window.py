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

        # Defaultní hodnoty pro obnovení
        self.default_title = "Git Visualizer"
        self.default_width = 600
        self.default_height = 400

        self.root.title(self.default_title)
        self.root.geometry(f"{self.default_width}x{self.default_height}")
        self.root.minsize(400, 300)

        self._center_window(self.default_width, self.default_height)

        self.git_repo = None
        self.setup_ui()

    def _center_window(self, width: int, height: int):
        screen_width = self.root.winfo_screenwidth()
        screen_height = self.root.winfo_screenheight()

        # Na Windows je potřeba počítat s taskbarem (obvykle 40-50 pixelů)
        taskbar_height = 50
        usable_height = screen_height - taskbar_height

        x = max(0, (screen_width - width) // 2)
        y = max(0, (usable_height - height) // 2)

        if x + width > screen_width:
            x = screen_width - width
        if y + height > usable_height:
            y = usable_height - height

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

        # Větší margin pro Windows (taskbar + bezpečnostní mezera)
        margin_horizontal = 100
        margin_vertical = 150  # 50 taskbar + 100 bezpečnostní mezera

        window_width = min(content_width, screen_width - margin_horizontal)
        window_height = min(content_height, screen_height - margin_vertical)

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
        # Header frame se nezobrazuje v úvodním stavu

        # Fetch remote tlačítko (vlevo)
        self.fetch_button = ttk.Button(
            self.header_frame,
            text="Načíst remote",
            command=self.fetch_remote_data,
            width=15
        )
        self.fetch_button.grid(row=0, column=0, sticky='w')

        # Frame pro název repozitáře a statistiky na středu
        self.info_frame = ttk.Frame(self.header_frame)
        self.info_frame.grid(row=0, column=1, sticky='')
        self.header_frame.columnconfigure(1, weight=1)  # Střední sloupec se rozšiřuje

        self.repo_name_label = ttk.Label(
            self.info_frame,
            text="",
            font=('Arial', 12, 'bold')
        )
        self.repo_name_label.grid(row=0, column=0, sticky='w')

        self.stats_label = ttk.Label(
            self.info_frame,
            text="",
            font=('Arial', 10)
        )
        self.stats_label.grid(row=0, column=1, sticky='w', padx=(10, 0))

        self.close_button = ttk.Button(
            self.header_frame,
            text="Zavřít repo",
            command=self.show_repository_selection,
            width=15
        )
        self.close_button.grid(row=0, column=2, sticky='e', padx=(10, 0))

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
            mode='determinate',
            value=0
        )
        self.progress.grid(row=0, column=1, sticky='ew', padx=(10, 0))

    def on_repository_selected(self, repo_path: str):
        self.update_status("Načítám repozitář...")
        self.progress.config(value=50)
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

    def fetch_remote_data(self):
        if not self.git_repo:
            return

        self.fetch_button.config(text="Načítám...", state="disabled")
        self.update_status("Načítám remote větve...")
        self.progress.start()

        thread = threading.Thread(
            target=self.load_remote_repository,
            daemon=True
        )
        thread.start()

    def load_remote_repository(self):
        try:
            commits = self.git_repo.parse_commits_with_remote()

            if not commits:
                self.root.after(0, self.show_error, "Repozitář neobsahuje žádné commity")
                return

            layout = GraphLayout(commits)
            positioned_commits = layout.calculate_positions()

            self.root.after(0, self.update_graph_with_remote, positioned_commits)

        except Exception as e:
            self.root.after(0, self.show_error, f"Chyba při načítání remote větví: {str(e)}")

    def update_graph_with_remote(self, commits):
        self.graph_canvas.update_graph(commits)

        # Aktualizovat statistiky
        stats = self.git_repo.get_repository_stats()

        def get_czech_plural(count, singular, plural2_4, plural5):
            if count == 1:
                return singular
            elif count in [2, 3, 4]:
                return plural2_4
            else:
                return plural5

        authors_text = f"{stats['authors']} {get_czech_plural(stats['authors'], 'autor', 'autoři', 'autorů')}"
        branches_text = f"{stats['branches']} {get_czech_plural(stats['branches'], 'větev', 'větve', 'větví')}"
        commits_text = f"{stats['commits']} {get_czech_plural(stats['commits'], 'commit', 'commity', 'commitů')}"
        tags_text = f"{stats['tags']} {get_czech_plural(stats['tags'], 'tag', 'tagy', 'tagů')}"

        stats_text = f"{authors_text}, {branches_text}, {commits_text}, {tags_text}"
        self.stats_label.config(text=stats_text)

        self.fetch_button.config(text="Načíst remote", state="normal")
        self.progress.stop()
        self.progress.config(value=100)
        self.update_status(f"Načteno {len(commits)} commitů (včetně remote)")

        self.root.after(100, lambda: self._resize_window_for_content(commits))

    def show_graph(self, commits):
        self.drag_drop_frame.grid_remove()
        self.graph_canvas.grid(row=0, column=0, sticky='nsew')
        self.graph_canvas.update_graph(commits)

        # Zobrazit název repozitáře s statistikami na jednom řádku a zachovat původní titul okna
        if self.git_repo and self.git_repo.repo_path:
            import os
            repo_name = os.path.basename(self.git_repo.repo_path)
            # Titul okna zůstává jako název aplikace
            self.root.title(self.default_title)

        # Zobrazit header frame a nastavit padding
        self.header_frame.grid(row=0, column=0, sticky='ew', pady=(0, 10))
        stats = self.git_repo.get_repository_stats()

        # Czech pluralization
        def get_czech_plural(count, singular, plural2_4, plural5):
            if count == 1:
                return singular
            elif count in [2, 3, 4]:
                return plural2_4
            else:
                return plural5

        authors_text = f"{stats['authors']} {get_czech_plural(stats['authors'], 'autor', 'autoři', 'autorů')}"
        branches_text = f"{stats['branches']} {get_czech_plural(stats['branches'], 'větev', 'větve', 'větví')}"
        commits_text = f"{stats['commits']} {get_czech_plural(stats['commits'], 'commit', 'commity', 'commitů')}"
        tags_text = f"{stats['tags']} {get_czech_plural(stats['tags'], 'tag', 'tagy', 'tagů')}"

        stats_text = f"{authors_text}, {branches_text}, {commits_text}, {tags_text}"

        # Nastavit název repozitáře (tučně) a statistiky (normálně) vedle sebe
        if self.git_repo and self.git_repo.repo_path:
            import os
            repo_name = os.path.basename(self.git_repo.repo_path)
            self.repo_name_label.config(text=repo_name)
            self.stats_label.config(text=stats_text)
        else:
            self.repo_name_label.config(text="")
            self.stats_label.config(text=stats_text)

        self.root.after(100, lambda: self._resize_window_for_content(commits))

        self.progress.stop()
        self.progress.config(value=100)
        self.update_status(f"Načteno {len(commits)} commitů")

    def show_repository_selection(self):
        self.graph_canvas.grid_remove()
        self.drag_drop_frame.grid(row=0, column=0, sticky='nsew')

        # Skrýt celý header frame
        self.header_frame.grid_remove()
        self.repo_name_label.config(text="")
        self.stats_label.config(text="")

        # Obnovit defaultní titul a velikost okna
        self.root.title(self.default_title)
        self.root.geometry(f"{self.default_width}x{self.default_height}")
        self._center_window(self.default_width, self.default_height)

        self.progress.config(value=0)
        self.update_status("Připraven")

    def show_error(self, message: str):
        self.progress.stop()
        self.progress.config(value=0)
        self.update_status("Chyba")
        messagebox.showerror("Chyba", message)

    def update_status(self, message: str):
        self.status_label.config(text=message)

    def run(self):
        self.root.mainloop()