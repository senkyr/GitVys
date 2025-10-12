import tkinter as tk
from tkinter import ttk, messagebox
import threading
import os
try:
    from tkinterdnd2 import TkinterDnD
except ImportError:
    TkinterDnD = None
from gui.drag_drop import DragDropFrame
from gui.graph_canvas import GraphCanvas
from gui.ui_components.language_switcher import LanguageSwitcher
from gui.ui_components.theme_switcher import ThemeSwitcher
from gui.ui_components.stats_display import StatsDisplay
from gui.repo_manager import RepositoryManager
from utils.logging_config import get_logger
from utils.translations import get_translation_manager, t
from utils.theme_manager import get_theme_manager

logger = get_logger(__name__)


class CustomProgressBar(tk.Canvas):
    """Canvas-based progress bar s podporou změny barev"""

    def __init__(self, parent, **kwargs):
        # Extrahovat custom parametry
        self.mode = kwargs.pop('mode', 'determinate')
        self.value = kwargs.pop('value', 0)

        # Get theme manager for colors
        tm = get_theme_manager()

        # Výchozí rozměry pro podobný vzhled jako ttk.Progressbar
        if 'height' not in kwargs:
            kwargs['height'] = 22
        if 'highlightthickness' not in kwargs:
            kwargs['highlightthickness'] = 1
        if 'highlightbackground' not in kwargs:
            kwargs['highlightbackground'] = tm.get_color('progress_border')
        if 'bg' not in kwargs:
            kwargs['bg'] = tm.get_color('progress_bg')

        super().__init__(parent, **kwargs)

        self.color = tm.get_color('progress_color_success')  # Výchozí zelená
        self.is_running = False
        self.animation_position = 0
        self.animation_id = None

        self.bind('<Configure>', self._redraw)
        self._redraw()

    def config(self, **kwargs):
        """Konfigurace progress baru - podporuje value a color parametry"""
        if 'value' in kwargs:
            self.value = kwargs.pop('value')
        if 'color' in kwargs:
            self.color = kwargs.pop('color')
        if kwargs:  # Zbytek předat Canvas
            super().config(**kwargs)
        self._redraw()

    def start(self):
        """Spustit indeterminate mode (animace)"""
        self.is_running = True
        self._animate()

    def stop(self):
        """Zastavit indeterminate mode"""
        self.is_running = False
        if self.animation_id:
            self.after_cancel(self.animation_id)
            self.animation_id = None
        self._redraw()

    def _animate(self):
        """Animační smyčka pro indeterminate mode"""
        if not self.is_running:
            return
        self.animation_position = (self.animation_position + 2) % 100
        self._redraw()
        self.animation_id = self.after(20, self._animate)

    def _redraw(self, event=None):
        """Překreslit progress bar"""
        self.delete('all')
        width = self.winfo_width()
        height = self.winfo_height()

        if width <= 1:
            width = 400  # Fallback během inicializace

        if self.is_running:
            # Indeterminate mode - pohybující se blok
            block_width = width // 4
            x = (self.animation_position / 100) * (width - block_width)
            self.create_rectangle(x, 2, x + block_width, height - 2,
                                fill=self.color, outline='')
        else:
            # Determinate mode - fixed progress
            progress_width = (self.value / 100) * width
            if progress_width > 0:
                self.create_rectangle(2, 2, progress_width - 2, height - 2,
                                    fill=self.color, outline='')


class MainWindow:
    def __init__(self):
        if TkinterDnD is not None:
            self.root = TkinterDnD.Tk()
        else:
            self.root = tk.Tk()

        # Translation manager
        self.tm = get_translation_manager()
        self.tm.register_callback(self._on_language_changed)

        # Theme manager
        self.theme_manager = get_theme_manager()
        self.theme_manager.set_root(self.root)  # Set root for TTK styling
        self.theme_manager.register_callback(self._on_theme_changed)

        # Nastavit root window background podle tématu
        self.root.configure(bg=self.theme_manager.get_color('window_bg'))

        # Defaultní hodnoty pro obnovení
        self.default_title = t('app_title')
        self.default_width = 600
        self.default_height = 400

        self.root.title(self.default_title)
        self.root.geometry(f"{self.default_width}x{self.default_height}")
        self.root.minsize(400, 300)

        self._center_window(self.default_width, self.default_height)

        # UI Components
        self.language_switcher = None  # Vytvoří se v setup_ui()
        self.theme_switcher = None     # Vytvoří se v setup_ui()
        self.stats_display = None      # Vytvoří se v setup_ui()

        # Repository Manager - handles all repository operations
        self.repo_manager = RepositoryManager(self)

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

        # Redukovaný padding - pouze 50px místo 200px
        content_width = table_width + 50
        content_height = (commit_count * commit_height) + header_height + status_height + margins

        screen_width = self.root.winfo_screenwidth()
        screen_height = self.root.winfo_screenheight()

        # Menší margin pro Windows
        margin_horizontal = 80  # Sníženo ze 100
        margin_vertical = 120   # Sníženo ze 150

        window_width = min(content_width, screen_width - margin_horizontal)
        window_height = min(content_height, screen_height - margin_vertical)

        # Dynamické minimum podle obsahu místo pevných hodnot
        min_reasonable_width = min(600, table_width + 50)  # Alespoň obsah + malý buffer
        min_reasonable_height = min(400, max(300, commit_count * 25 + 200))  # Přizpůsobit počtu commitů

        window_width = max(window_width, min_reasonable_width)
        window_height = max(window_height, min_reasonable_height)

        self._center_window(window_width, window_height)

    def _get_accurate_content_width(self, canvas, commits):
        """Získá přesnou šířku obsahu canvas s fallback logikou."""
        # Nejprve zkusit získat skutečné rozměry z canvas
        try:
            canvas.update_idletasks()  # Zajistit že je vše vykresleno
            bbox = self.graph_canvas._get_content_bbox_without_header()
            if bbox and bbox[2] > bbox[0]:
                actual_width = bbox[2] - bbox[0]
                # Přidat rozumný buffer pro UI elementy
                return actual_width + 40
        except Exception as e:
            logger.warning(f"Failed to calculate optimal width: {e}")
            pass

        # Fallback: použít column_widths pokud jsou dostupné
        if hasattr(self.graph_canvas.graph_drawer, 'column_widths'):
            column_widths = self.graph_canvas.graph_drawer.column_widths
            if column_widths:
                table_width = sum(column_widths.values())
                # Přidat prostor pro graf větví
                max_branch_lanes = len(set(commit.branch for commit in commits)) if commits else 1
                branch_width = max_branch_lanes * 25 + 120  # Konzervativnější odhad
                return table_width + branch_width

        # Poslední fallback pro velmi malé repozitáře
        return 500

    def _calculate_table_width(self, canvas, commits):
        return self._get_accurate_content_width(canvas, commits)

    def setup_ui(self):
        self.root.columnconfigure(0, weight=1)
        self.root.rowconfigure(0, weight=1)

        self.main_frame = ttk.Frame(self.root)
        self.main_frame.grid(row=0, column=0, sticky='nsew', padx=10, pady=10)
        self.main_frame.columnconfigure(0, weight=1)
        self.main_frame.rowconfigure(2, weight=1)  # Content frame má váhu

        # Language switcher (vlevo nahoře, viditelný pouze v úvodním okně)
        self.language_switcher = LanguageSwitcher(self)
        self.language_switcher.create_switcher_ui()
        self.language_switcher.show()

        # Theme switcher (vpravo nahoře, viditelný pouze v úvodním okně)
        self.theme_switcher = ThemeSwitcher(self)
        self.theme_switcher.create_switcher_ui()
        self.theme_switcher.show()

        self.header_frame = ttk.Frame(self.main_frame)
        # Header frame bude na row=1, zobrazí se až po načtení repozitáře

        # Fetch remote tlačítko (vlevo)
        self.fetch_button = ttk.Button(
            self.header_frame,
            text=t('fetch_remote'),
            command=self.repo_manager.fetch_remote_data,
            width=15
        )
        self.fetch_button.grid(row=0, column=0, sticky='w')

        # Stats display (název repozitáře a statistiky na středu)
        self.stats_display = StatsDisplay(self)
        self.info_frame, self.repo_name_label, self.stats_label = self.stats_display.create_stats_ui(self.header_frame)

        self.close_button = ttk.Button(
            self.header_frame,
            text=t('close_repo'),
            command=self.show_repository_selection,
            width=15
        )
        self.close_button.grid(row=0, column=2, sticky='e', padx=(10, 0))

        self.content_frame = ttk.Frame(self.main_frame)
        self.content_frame.grid(row=2, column=0, sticky='nsew')
        self.content_frame.columnconfigure(0, weight=1)
        self.content_frame.rowconfigure(0, weight=1)

        self.drag_drop_frame = DragDropFrame(
            self.content_frame,
            on_drop_callback=self.repo_manager.on_repository_selected
        )
        self.drag_drop_frame.grid(row=0, column=0, sticky='nsew')

        self.graph_canvas = GraphCanvas(self.content_frame, on_drop_callback=self.repo_manager.on_repository_selected)

        self.status_frame = ttk.Frame(self.main_frame)
        self.status_frame.grid(row=3, column=0, sticky='ew', pady=(25, 0))
        self.status_frame.columnconfigure(1, weight=1)

        self.status_label = ttk.Label(self.status_frame, text=t('ready'))
        self.status_label.grid(row=0, column=0, sticky='w')

        self.progress = CustomProgressBar(
            self.status_frame,
            mode='determinate',
            value=0
        )
        self.progress.grid(row=0, column=1, sticky='ew', padx=(10, 0))

        # Refresh tlačítko (vpravo dolů)
        self.refresh_button = ttk.Button(
            self.status_frame,
            text=t('refresh'),
            command=self.repo_manager.refresh_repository,
            width=15
        )
        # Tlačítko se zobrazí až po načtení repozitáře

        # Přidat F5 key binding
        self.root.bind('<F5>', lambda event: self.repo_manager.refresh_repository())
        self.root.focus_set()  # Zajistit focus pro key bindings

    def _on_theme_changed(self, theme: str):
        """Called when theme is changed - updates all UI colors."""
        # Update theme icon appearance
        if self.theme_switcher:
            self.theme_switcher.update_theme_icon_appearance()

        # Apply theme colors
        tm = self.theme_manager

        # Update root window background
        self.root.configure(bg=tm.get_color('window_bg'))

        # Update CustomProgressBar colors
        if hasattr(self, 'progress'):
            self.progress.config(
                bg=tm.get_color('progress_bg'),
                highlightbackground=tm.get_color('progress_border')
            )

        # Update drag-drop frame if exists
        if hasattr(self, 'drag_drop_frame'):
            self.drag_drop_frame.apply_theme()

        # Update graph canvas if exists
        if hasattr(self, 'graph_canvas'):
            self.graph_canvas.apply_theme()

        logger.info(f"Theme changed to: {theme}")

    def _on_language_changed(self, language: str):
        """Called when language is changed - updates all UI texts."""
        # Update flag appearance
        if self.language_switcher:
            self.language_switcher.update_flag_appearance()

        # Update window title
        self.default_title = t('app_title')
        self.root.title(self.default_title)

        # Update buttons
        if self.repo_manager.is_cloned_repo:
            self.fetch_button.config(text=t('fetch_branches'))
        else:
            self.fetch_button.config(text=t('fetch_remote'))
        self.close_button.config(text=t('close_repo'))
        self.refresh_button.config(text=t('refresh'))

        # Update status
        if not self.repo_manager.git_repo:
            self.status_label.config(text=t('ready'))

        # Update statistics if repo is loaded
        if self.repo_manager.git_repo and self.stats_display:
            self.stats_display.update_stats(self.repo_manager.git_repo, self.repo_manager.display_name)

        # Update drag/drop frame
        self.drag_drop_frame.update_language()

        # Redraw graph canvas if visible (to update column headers)
        if self.graph_canvas.winfo_viewable() and hasattr(self.graph_canvas, 'graph_drawer'):
            commits = getattr(self.graph_canvas.graph_drawer, '_current_commits', None)
            if commits:
                self.graph_canvas.update_graph(commits)

    def update_graph_with_remote(self, commits):
        self.repo_manager.is_remote_loaded = True  # Označit že jsou načtená remote data
        self.graph_canvas.update_graph(commits)

        # Aktualizovat statistiky pomocí centralizované metody
        if self.stats_display:
            self.stats_display.update_stats(self.repo_manager.git_repo, self.repo_manager.display_name)

        # Po načtení remote dat vrátit původní text tlačítka
        if self.repo_manager.is_cloned_repo:
            button_text = t('fetch_branches')
        else:
            button_text = t('fetch_remote')
        self.fetch_button.config(text=button_text, state="normal")

        self.progress.stop()
        tm = self.theme_manager
        self.progress.config(value=100, color=tm.get_color('progress_color_info'))
        self.update_status(t('loaded_commits_remote', len(commits)))

        # Zobrazit Refresh tlačítko (pokud už není zobrazené)
        self.refresh_button.grid(row=0, column=2, sticky='e', padx=(10, 0))

        # Kratší delay pro rychlejší response, ale stále zajistit že je obsah vykreslen
        self.root.after(50, lambda: self._resize_window_for_content(commits))

    def show_graph(self, commits):
        # Skrýt přepínač jazyka a přepínač tématu
        if self.language_switcher:
            self.language_switcher.hide()
        if self.theme_switcher:
            self.theme_switcher.hide()

        self.drag_drop_frame.grid_remove()
        self.graph_canvas.grid(row=0, column=0, sticky='nsew')
        self.graph_canvas.update_graph(commits)

        # Zobrazit název repozitáře s statistikami na jednom řádku a zachovat původní titul okna
        if self.repo_manager.git_repo and self.repo_manager.git_repo.repo_path:
            import os
            repo_name = os.path.basename(self.repo_manager.git_repo.repo_path)
            # Titul okna zůstává jako název aplikace
            self.root.title(self.default_title)

        # Zobrazit header frame a nastavit padding
        self.header_frame.grid(row=1, column=0, sticky='ew', pady=(0, 10))

        # Nastavit název repozitáře (tučně) a statistiky (normálně) vedle sebe
        if self.stats_display:
            self.stats_display.update_stats(self.repo_manager.git_repo, self.repo_manager.display_name)

        # Kratší delay pro rychlejší response, ale stále zajistit že je obsah vykreslen
        self.root.after(50, lambda: self._resize_window_for_content(commits))

        self.progress.stop()
        tm = self.theme_manager
        self.progress.config(value=100, color=tm.get_color('progress_color_info'))
        self.update_status(t('loaded_commits', len(commits)))

        # Nastavit text fetch tlačítka podle zdroje repozitáře
        if self.repo_manager.is_cloned_repo:
            self.fetch_button.config(text=t('fetch_branches'))
        else:
            self.fetch_button.config(text=t('fetch_remote'))

        # Zobrazit Refresh tlačítko
        self.refresh_button.grid(row=0, column=2, sticky='e', padx=(10, 0))

    def show_repository_selection(self):
        # Reset GraphDrawer state to clear column widths and cached data
        if hasattr(self, 'graph_canvas') and hasattr(self.graph_canvas, 'graph_drawer'):
            self.graph_canvas.graph_drawer.reset()

        # Close repository and cleanup temp files
        self.repo_manager.close_repository()

        # Zobrazit přepínač jazyka a tématu zpět
        if self.language_switcher:
            self.language_switcher.show()
        if self.theme_switcher:
            self.theme_switcher.show()

        self.graph_canvas.grid_remove()
        self.drag_drop_frame.grid(row=0, column=0, sticky='nsew')

        # Skrýt celý header frame
        self.header_frame.grid_remove()
        self.repo_name_label.config(text="")
        self.stats_label.config(text="")

        # Skrýt Refresh tlačítko
        self.refresh_button.grid_remove()

        # Obnovit defaultní titul a velikost okna
        self.root.title(self.default_title)
        self.root.geometry(f"{self.default_width}x{self.default_height}")
        self._center_window(self.default_width, self.default_height)

        # Aktualizovat pozici theme switcher po resize
        if self.theme_switcher:
            self.theme_switcher.update_position()

        tm = self.theme_manager
        self.progress.config(value=0, color=tm.get_color('progress_color_success'))
        self.update_status(t('ready'))

    def show_error(self, message: str):
        self.progress.stop()
        tm = self.theme_manager
        self.progress.config(value=0, color=tm.get_color('progress_color_success'))
        self.update_status(t('error'))
        messagebox.showerror(t('error'), message)

    def update_status(self, message: str):
        self.status_label.config(text=message)

    def run(self):
        self.root.mainloop()
