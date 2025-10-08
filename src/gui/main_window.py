import tkinter as tk
from tkinter import ttk, messagebox
import threading
import os
try:
    from tkinterdnd2 import TkinterDnD
except ImportError:
    TkinterDnD = None
from repo.repository import GitRepository
from visualization.layout import GraphLayout
from gui.drag_drop import DragDropFrame
from gui.graph_canvas import GraphCanvas
from gui.auth_dialog import GitHubAuthDialog
from auth.token_storage import TokenStorage
from utils.logging_config import get_logger

logger = get_logger(__name__)


class CustomProgressBar(tk.Canvas):
    """Canvas-based progress bar s podporou změny barev"""

    def __init__(self, parent, **kwargs):
        # Extrahovat custom parametry
        self.mode = kwargs.pop('mode', 'determinate')
        self.value = kwargs.pop('value', 0)

        # Výchozí rozměry pro podobný vzhled jako ttk.Progressbar
        if 'height' not in kwargs:
            kwargs['height'] = 22
        if 'highlightthickness' not in kwargs:
            kwargs['highlightthickness'] = 1
        if 'highlightbackground' not in kwargs:
            kwargs['highlightbackground'] = '#aaaaaa'
        if 'bg' not in kwargs:
            kwargs['bg'] = '#e0e0e0'

        super().__init__(parent, **kwargs)

        self.color = '#4CAF50'  # Výchozí zelená
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

        # Defaultní hodnoty pro obnovení
        self.default_title = "Git Visualizer v1.3.0"
        self.default_width = 600
        self.default_height = 400

        self.root.title(self.default_title)
        self.root.geometry(f"{self.default_width}x{self.default_height}")
        self.root.minsize(400, 300)

        self._center_window(self.default_width, self.default_height)

        self.git_repo = None
        self.is_remote_loaded = False  # Sledování stavu remote načtení
        self.is_cloned_repo = False  # True pokud repo bylo načteno z URL (klonováno)
        self.temp_clones = []  # Seznam temp složek ke smazání při zavření
        self.current_temp_clone = None  # Cesta k aktuálně otevřenému temp klonu
        self.display_name = None  # Reálný název repozitáře (pro klonované repo)
        self.tooltip_window = None  # Window pro tooltip s cestou k repozitáři
        self.token_storage = TokenStorage()  # GitHub token storage

        # Vyčistit staré temp složky z předchozích sessions
        self._cleanup_old_temp_clones()

        self.setup_ui()

        # Cleanup handler pro temp složky
        import atexit
        atexit.register(self._cleanup_temp_clones)

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

        # Přidat tooltip pro zobrazení cesty k repozitáři
        self.repo_name_label.bind('<Enter>', self._show_repo_path_tooltip)
        self.repo_name_label.bind('<Leave>', self._hide_repo_path_tooltip)

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

        self.progress = CustomProgressBar(
            self.status_frame,
            mode='determinate',
            value=0
        )
        self.progress.grid(row=0, column=1, sticky='ew', padx=(10, 0))

        # Refresh tlačítko (vpravo dolů)
        self.refresh_button = ttk.Button(
            self.status_frame,
            text="Refresh",
            command=self.refresh_repository,
            width=15
        )
        # Tlačítko se zobrazí až po načtení repozitáře

        # Přidat F5 key binding
        self.root.bind('<F5>', lambda event: self.refresh_repository())
        self.root.focus_set()  # Zajistit focus pro key bindings

    def _show_repo_path_tooltip(self, event):
        """Zobrazí tooltip s cestou k repozitáři."""
        if not self.git_repo or not self.git_repo.repo_path:
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
        tooltip_text = self.git_repo.repo_path
        label = tk.Label(
            self.tooltip_window,
            text=tooltip_text,
            background="#ffffe0",
            foreground="black",
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

    def on_repository_selected(self, repo_path: str):
        # Detekce URL vs lokální cesta
        if self._is_git_url(repo_path):
            # Online repozitář - klonovat
            self.clone_repository(repo_path)
        else:
            # Lokální složka - načíst přímo

            # Zavřít GitPython repo před mazáním temp složky
            if self.git_repo and hasattr(self.git_repo, 'repo') and self.git_repo.repo:
                try:
                    self.git_repo.repo.close()
                except Exception as e:
                    logger.warning(f"Failed to close GitPython repo: {e}")
                    pass

            # Pokud byl předtím otevřený klonovaný repo → smazat temp
            if self.is_cloned_repo and self.current_temp_clone:
                self._cleanup_single_clone(self.current_temp_clone)
                self.current_temp_clone = None

            self.is_cloned_repo = False  # Lokální repo, ne klonované
            self.display_name = None  # Resetovat display name pro lokální repo
            self.update_status("Načítám repozitář...")
            self.progress.config(value=50, color='#4CAF50')
            self.progress.start()

            thread = threading.Thread(
                target=self.load_repository,
                args=(repo_path,),
                daemon=True
            )
            thread.start()

    def _is_git_url(self, text: str) -> bool:
        """Detekuje zda je text Git URL."""
        text = text.lower().strip()
        if text.startswith(('http://', 'https://', 'git@')):
            return True
        git_hosts = ['github.com', 'gitlab.com', 'bitbucket.org', 'gitea.']
        return any(host in text for host in git_hosts)

    def clone_repository(self, url: str):
        """Klonuje online repozitář do temp složky."""
        import tempfile

        # Smazat VŠECHNY staré temp klony (nejen current)
        # Řeší race conditions a failed clones
        if self.temp_clones:
            for old_clone in self.temp_clones[:]:  # Kopie listu pro bezpečnou iteraci
                self._cleanup_single_clone(old_clone)
        self.current_temp_clone = None

        # Vytvořit temp složku
        temp_dir = tempfile.mkdtemp(prefix='gitvys_clone_')
        self.temp_clones.append(temp_dir)

        # Extrahovat název repo z URL pro zobrazení
        repo_name = url.rstrip('/').split('/')[-1].replace('.git', '')
        self.display_name = repo_name  # Uložit reálný název pro pozdější zobrazení

        self.update_status(f"Klonuji {repo_name}...")
        self.progress.config(color='#4CAF50')
        self.progress.start()

        thread = threading.Thread(
            target=self._clone_worker,
            args=(url, temp_dir),
            daemon=True
        )
        thread.start()

    def _clone_worker(self, url: str, path: str):
        """Worker thread pro klonování repozitáře."""
        try:
            from git import Repo
            from git.exc import GitCommandError

            # Pokusit se klonovat bez autentizace
            try:
                Repo.clone_from(url, path)
                # Úspěch - načíst jako běžný repo
                self.root.after(0, self._on_clone_complete, path)
                return

            except GitCommandError as clone_error:
                # Zkontrolovat, zda je to chyba autentizace
                error_message = str(clone_error).lower()
                is_auth_error = any(keyword in error_message for keyword in [
                    'authentication', 'forbidden', '403', '401',
                    'could not read', 'repository not found'
                ])

                if not is_auth_error:
                    # Jiná chyba než autentizace - propagovat
                    raise

                # Chyba autentizace - zkusit s tokenem
                logger.info("Authentication required for cloning, attempting with token...")

                # Načíst uložený token
                token = self.token_storage.load_token()

                # Pokud token neexistuje, zobrazit auth dialog
                if not token:
                    logger.info("No saved token found, showing auth dialog...")
                    token = self.root.after(0, self._show_auth_dialog_sync)

                    # Počkat na výsledek z auth dialogu (v main threadu)
                    import time
                    timeout = 300  # 5 minut
                    start_time = time.time()
                    while not hasattr(self, '_auth_dialog_result') and time.time() - start_time < timeout:
                        time.sleep(0.1)

                    if hasattr(self, '_auth_dialog_result'):
                        token = self._auth_dialog_result
                        delattr(self, '_auth_dialog_result')
                    else:
                        raise Exception("Autentizace vypršela nebo byla zrušena")

                if not token:
                    raise Exception("Autentizace se nezdařila")

                # Uložit token pro příští použití
                self.token_storage.save_token(token)

                # Vytvořit autentizovanou URL
                # Formát: https://{token}@github.com/user/repo.git
                if url.startswith('https://'):
                    auth_url = url.replace('https://', f'https://{token}@')
                elif url.startswith('http://'):
                    auth_url = url.replace('http://', f'http://{token}@')
                else:
                    # SSH URL nebo jiný formát - nemůžeme použít token
                    raise Exception("Token autentizace funguje pouze s HTTPS URLs")

                # Retry klonování s autentizovanou URL
                logger.info("Retrying clone with authentication...")
                self.root.after(0, self.update_status, "Klonuji s autentizací...")
                Repo.clone_from(auth_url, path)

                # Úspěch
                self.root.after(0, self._on_clone_complete, path)

        except Exception as e:
            # Smazat temp složku při chybě klonování
            self.root.after(0, self._cleanup_single_clone, path)
            self.root.after(0, self.show_error, f"Chyba klonování:\n{str(e)}")
            self.root.after(0, self.progress.stop)

    def _show_auth_dialog_sync(self):
        """Zobrazí auth dialog v main threadu a uloží výsledek."""
        dialog = GitHubAuthDialog(self.root)
        token = dialog.show()
        self._auth_dialog_result = token
        return token

    def _on_clone_complete(self, path: str):
        """Callback po úspěšném klonování."""
        self.is_cloned_repo = True  # Označit že repo bylo klonováno z URL
        self.current_temp_clone = path  # Uložit cestu k aktuálnímu temp klonu
        self.update_status("Načítám naklonovaný repozitář...")

        thread = threading.Thread(
            target=self.load_repository,
            args=(path,),
            daemon=True
        )
        thread.start()

    def _cleanup_old_temp_clones(self):
        """Při startu smaže všechny temp složky z předchozích sessions."""
        import tempfile
        import glob
        import shutil
        import stat

        def handle_remove_readonly(func, path, exc):
            """Error handler pro Windows readonly files."""
            if func in (os.unlink, os.rmdir):
                # Změnit readonly flag a zkusit znovu
                os.chmod(path, stat.S_IWRITE)
                func(path)
            else:
                raise

        try:
            temp_dir = tempfile.gettempdir()
            pattern = os.path.join(temp_dir, 'gitvys_clone_*')

            for old_temp in glob.glob(pattern):
                try:
                    if os.path.exists(old_temp) and os.path.isdir(old_temp):
                        shutil.rmtree(old_temp, onerror=handle_remove_readonly)
                except Exception as e:
                    logger.warning(f"Failed to cleanup orphaned temp clone {old_temp}: {e}")
                    pass  # Ignorovat chyby u jednotlivých složek
        except Exception as e:
            logger.warning(f"Failed to cleanup temp clones: {e}")
            pass  # Ignorovat chyby celého cleaningu

    def _cleanup_single_clone(self, path: str):
        """Smaže jeden konkrétní temp klon."""
        import shutil
        import stat

        def handle_remove_readonly(func, path, exc):
            """Error handler pro Windows readonly files."""
            if func in (os.unlink, os.rmdir):
                # Změnit readonly flag a zkusit znovu
                os.chmod(path, stat.S_IWRITE)
                func(path)
            else:
                raise

        try:
            if os.path.exists(path):
                shutil.rmtree(path, onerror=handle_remove_readonly)
                # Odebrat z listu JEN pokud mazání skutečně uspělo
                if not os.path.exists(path) and path in self.temp_clones:
                    self.temp_clones.remove(path)
        except Exception as e:
            # Logovat ale nepadnout
            print(f"Warning: Nepodařilo se smazat temp klon: {e}")

    def _cleanup_temp_clones(self):
        """Smaže dočasné klonované repozitáře při zavření (fallback)."""
        import shutil
        import stat

        # Zavřít GitPython repo pokud je stále otevřený
        if hasattr(self, 'git_repo') and self.git_repo:
            if hasattr(self.git_repo, 'repo') and self.git_repo.repo:
                try:
                    self.git_repo.repo.close()
                except Exception as e:
                    logger.warning(f"Failed to close GitPython repo during cleanup: {e}")
                    pass

        def handle_remove_readonly(func, path, exc):
            """Error handler pro Windows readonly files."""
            if func in (os.unlink, os.rmdir):
                # Změnit readonly flag a zkusit znovu
                os.chmod(path, stat.S_IWRITE)
                func(path)
            else:
                raise

        for temp_dir in self.temp_clones:
            try:
                if os.path.exists(temp_dir):
                    shutil.rmtree(temp_dir, onerror=handle_remove_readonly)
            except Exception as e:
                logger.warning(f"Failed to cleanup temp clone {temp_dir}: {e}")
                pass  # Ignorovat chyby při cleanup

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

            merge_branches = self.git_repo.get_merge_branches()
            layout = GraphLayout(commits, merge_branches=merge_branches)
            positioned_commits = layout.calculate_positions()

            self.root.after(0, self.show_graph, positioned_commits)

        except Exception as e:
            self.root.after(0, self.show_error, f"Chyba při načítání repozitáře: {str(e)}")

    def refresh_repository(self):
        """Obnoví repozitář podle aktuálního stavu (lokální vs remote)."""
        if not self.git_repo:
            return

        if self.is_remote_loaded:
            # Obnovit s remote daty
            self.fetch_remote_data()
        else:
            # Obnovit jen lokálně
            self.update_status("Načítám repozitář...")
            self.progress.config(color='#4CAF50')
            self.progress.start()

            thread = threading.Thread(
                target=self.refresh_local_repository,
                daemon=True
            )
            thread.start()

    def refresh_local_repository(self):
        """Obnoví lokální repozitář data."""
        try:
            commits = self.git_repo.parse_commits()

            if not commits:
                self.root.after(0, self.show_error, "Repozitář neobsahuje žádné commity")
                return

            merge_branches = self.git_repo.get_merge_branches()
            layout = GraphLayout(commits, merge_branches=merge_branches)
            positioned_commits = layout.calculate_positions()

            self.root.after(0, self.show_graph, positioned_commits)

        except Exception as e:
            self.root.after(0, self.show_error, f"Chyba při obnovování: {str(e)}")

    def fetch_remote_data(self):
        if not self.git_repo:
            return

        self.fetch_button.config(text="Načítám...", state="disabled")
        self.update_status("Načítám remote větve...")
        self.progress.config(color='#4CAF50')
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

            merge_branches = self.git_repo.get_merge_branches()
            layout = GraphLayout(commits, merge_branches=merge_branches)
            positioned_commits = layout.calculate_positions()

            self.root.after(0, self.update_graph_with_remote, positioned_commits)

        except Exception as e:
            self.root.after(0, self.show_error, f"Chyba při načítání remote větví: {str(e)}")

    def update_graph_with_remote(self, commits):
        self.is_remote_loaded = True  # Označit že jsou načtená remote data
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

        # Zobrazit tagy jen pokud nějaké existují (včetně remote)
        if stats['tags'] > 0:
            if stats['remote_tags'] > 0:
                # Rozlišit lokální a remote tagy
                tags_text = f"{stats['local_tags']}+{stats['remote_tags']} tagů"
            else:
                # Jen lokální tagy
                tags_text = f"{stats['tags']} {get_czech_plural(stats['tags'], 'tag', 'tagy', 'tagů')}"
            stats_text = f"{authors_text}, {branches_text}, {tags_text}, {commits_text}"
        else:
            stats_text = f"{authors_text}, {branches_text}, {commits_text}"
        self.stats_label.config(text=stats_text)

        # Po načtení remote dat vrátit původní text tlačítka
        if self.is_cloned_repo:
            button_text = "Načíst větve"
        else:
            button_text = "Načíst remote"
        self.fetch_button.config(text=button_text, state="normal")

        self.progress.stop()
        self.progress.config(value=100, color='#2196F3')
        self.update_status(f"Načteno {len(commits)} commitů (včetně remote)")

        # Zobrazit Refresh tlačítko (pokud už není zobrazené)
        self.refresh_button.grid(row=0, column=2, sticky='e', padx=(10, 0))

        # Kratší delay pro rychlejší response, ale stále zajistit že je obsah vykreslen
        self.root.after(50, lambda: self._resize_window_for_content(commits))

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

        # Zobrazit tagy jen pokud nějaké existují
        if stats['tags'] > 0:
            if stats['remote_tags'] > 0:
                # Rozlišit lokální a remote tagy
                tags_text = f"{stats['local_tags']}+{stats['remote_tags']} tagů"
            else:
                # Jen lokální tagy
                tags_text = f"{stats['tags']} {get_czech_plural(stats['tags'], 'tag', 'tagy', 'tagů')}"
            stats_text = f"{authors_text}, {branches_text}, {tags_text}, {commits_text}"
        else:
            stats_text = f"{authors_text}, {branches_text}, {commits_text}"

        # Nastavit název repozitáře (tučně) a statistiky (normálně) vedle sebe
        if self.git_repo and self.git_repo.repo_path:
            import os
            # Pro klonované repo použít reálný název, jinak název složky
            repo_name = self.display_name if self.display_name else os.path.basename(self.git_repo.repo_path)
            self.repo_name_label.config(text=repo_name)
            self.stats_label.config(text=stats_text)
        else:
            self.repo_name_label.config(text="")
            self.stats_label.config(text=stats_text)

        # Kratší delay pro rychlejší response, ale stále zajistit že je obsah vykreslen
        self.root.after(50, lambda: self._resize_window_for_content(commits))

        self.progress.stop()
        self.progress.config(value=100, color='#2196F3')
        self.update_status(f"Načteno {len(commits)} commitů")

        # Nastavit text fetch tlačítka podle zdroje repozitáře
        if self.is_cloned_repo:
            self.fetch_button.config(text="Načíst větve")
        else:
            self.fetch_button.config(text="Načíst remote")

        # Zobrazit Refresh tlačítko
        self.refresh_button.grid(row=0, column=2, sticky='e', padx=(10, 0))

    def show_repository_selection(self):
        # Reset GraphDrawer state to clear column widths and cached data
        if hasattr(self, 'graph_canvas') and hasattr(self.graph_canvas, 'graph_drawer'):
            self.graph_canvas.graph_drawer.reset()

        # Zavřít GitPython repo aby uvolnil file handles
        if self.git_repo and hasattr(self.git_repo, 'repo') and self.git_repo.repo:
            try:
                self.git_repo.repo.close()
            except Exception as e:
                logger.warning(f"Failed to close GitPython repo: {e}")
                pass
        self.git_repo = None

        # Pokud je otevřený klonovaný repo → smazat temp klon
        if self.is_cloned_repo and self.current_temp_clone:
            self._cleanup_single_clone(self.current_temp_clone)
            self.current_temp_clone = None

        self.graph_canvas.grid_remove()
        self.drag_drop_frame.grid(row=0, column=0, sticky='nsew')

        # Skrýt celý header frame
        self.header_frame.grid_remove()
        self.repo_name_label.config(text="")
        self.stats_label.config(text="")

        # Skrýt Refresh tlačítko
        self.refresh_button.grid_remove()

        # Reset remote stavu
        self.is_remote_loaded = False
        self.is_cloned_repo = False
        self.display_name = None

        # Obnovit defaultní titul a velikost okna
        self.root.title(self.default_title)
        self.root.geometry(f"{self.default_width}x{self.default_height}")
        self._center_window(self.default_width, self.default_height)

        self.progress.config(value=0, color='#4CAF50')
        self.update_status("Připraven")

    def show_error(self, message: str):
        self.progress.stop()
        self.progress.config(value=0, color='#4CAF50')
        self.update_status("Chyba")
        messagebox.showerror("Chyba", message)

    def update_status(self, message: str):
        self.status_label.config(text=message)

    def run(self):
        self.root.mainloop()
