"""Stats display component with repository information."""

import tkinter as tk
from tkinter import ttk
import os
from utils.translations import get_translation_manager
from utils.theme_manager import get_theme_manager


class StatsDisplay:
    """Component for displaying repository statistics and path tooltip."""

    def __init__(self, parent_window):
        """
        Initialize StatsDisplay.

        Args:
            parent_window: MainWindow instance
        """
        self.parent = parent_window
        self.root = parent_window.root
        self.tm = get_translation_manager()
        self.theme_manager = get_theme_manager()

        # UI elements
        self.info_frame = None
        self.repo_name_label = None
        self.stats_label = None
        self.tooltip_window = None

    def create_stats_ui(self, parent_frame):
        """
        Create the stats display UI.

        Args:
            parent_frame: Parent frame (header_frame) to place stats in

        Returns:
            tuple: (info_frame, repo_name_label, stats_label)
        """
        # Frame pro název repozitáře a statistiky na středu
        self.info_frame = ttk.Frame(parent_frame)
        self.info_frame.grid(row=0, column=1, sticky='')
        parent_frame.columnconfigure(1, weight=1)  # Střední sloupec se rozšiřuje

        self.repo_name_label = ttk.Label(
            self.info_frame,
            text="",
            font=('Arial', 12, 'bold')
        )
        self.repo_name_label.grid(row=0, column=0, sticky='w')

        # Přidat tooltip pro zobrazení cesty k repozitáři
        self.repo_name_label.bind('<Enter>', self._show_repo_path_tooltip)
        self.repo_name_label.bind('<Leave>', self._hide_repo_path_tooltip)

        self.stats_label = ttk.Label(
            self.info_frame,
            text="",
            font=('Arial', 10)
        )
        self.stats_label.grid(row=0, column=1, sticky='w', padx=(10, 0))

        return self.info_frame, self.repo_name_label, self.stats_label

    def update_stats(self, git_repo, display_name=None):
        """
        Update repository statistics display with current language.

        Args:
            git_repo: GitRepository instance
            display_name: Optional display name for cloned repos
        """
        if not git_repo:
            self.repo_name_label.config(text="")
            self.stats_label.config(text="")
            return

        # Nastavit název repozitáře (tučně)
        repo_name = display_name if display_name else os.path.basename(git_repo.repo_path)
        self.repo_name_label.config(text=repo_name)

        # Získat statistiky
        stats = git_repo.get_repository_stats()

        authors_text = f"{stats['authors']} {self.tm.get_plural(stats['authors'], 'author')}"
        branches_text = f"{stats['branches']} {self.tm.get_plural(stats['branches'], 'branch')}"
        commits_text = f"{stats['commits']} {self.tm.get_plural(stats['commits'], 'commit')}"

        # Zobrazit tagy jen pokud nějaké existují
        if stats['tags'] > 0:
            from utils.translations import t
            if stats['remote_tags'] > 0:
                tags_text = t('tags_format', stats['local_tags'], stats['remote_tags'])
            else:
                tags_text = f"{stats['tags']} {self.tm.get_plural(stats['tags'], 'tag')}"
            stats_text = f"{authors_text}, {branches_text}, {tags_text}, {commits_text}"
        else:
            stats_text = f"{authors_text}, {branches_text}, {commits_text}"

        self.stats_label.config(text=stats_text)

    def _show_repo_path_tooltip(self, event):
        """Zobrazí tooltip s cestou k repozitáři."""
        # Potřebujeme git_repo z parent window
        if not hasattr(self.parent, 'git_repo') or not self.parent.git_repo or not self.parent.git_repo.repo_path:
            return

        # Skrýt existující tooltip pokud existuje
        self._hide_repo_path_tooltip()

        # Vytvořit tooltip window
        self.tooltip_window = tk.Toplevel(self.root)
        self.tooltip_window.wm_overrideredirect(True)
        self.tooltip_window.wm_attributes("-topmost", True)

        # Nastavit pozici tooltip okna pod labelem
        x = event.widget.winfo_rootx() + 10
        y = event.widget.winfo_rooty() + event.widget.winfo_height() + 5
        self.tooltip_window.wm_geometry(f"+{x}+{y}")

        # Vytvořit label s cestou
        tooltip_text = self.parent.git_repo.repo_path
        label = tk.Label(
            self.tooltip_window,
            text=tooltip_text,
            background=self.theme_manager.get_color('tooltip_bg'),
            foreground=self.theme_manager.get_color('tooltip_fg'),
            font=('Arial', 9),
            relief="solid",
            borderwidth=1,
            padx=8,
            pady=4
        )
        label.pack()

    def _hide_repo_path_tooltip(self, event=None):
        """Skryje tooltip okno."""
        if self.tooltip_window:
            self.tooltip_window.destroy()
            self.tooltip_window = None
