import tkinter as tk
from tkinter import ttk
from typing import List, Dict, Callable
try:
    from tkinterdnd2 import DND_FILES, DND_TEXT
except ImportError:
    DND_FILES = None
    DND_TEXT = None
from utils.data_structures import Commit
from visualization.graph_drawer import GraphDrawer
from utils.theme_manager import get_theme_manager


class GraphCanvas(ttk.Frame):
    def __init__(self, parent, on_drop_callback: Callable[[str], None] = None):
        super().__init__(parent)
        self.commits: List[Commit] = []
        self.graph_drawer = GraphDrawer()
        self.on_drop_callback = on_drop_callback

        # Smooth scrolling state with momentum
        self.scroll_animation_id = None
        self.scroll_velocity = 0  # Aktuální rychlost scrollování
        self.last_scroll_time = 0  # Čas posledního scroll eventu
        self.scroll_timeout_id = None  # ID timeoutu pro reset velocity

        # Virtualizace: po změně pohledu se (jednou za idle) dokreslí viditelné řádky
        self._render_pending = None

        self.setup_ui()

    def setup_ui(self):
        self.columnconfigure(0, weight=1)
        self.rowconfigure(0, weight=1)

        self.canvas_frame = ttk.Frame(self)
        self.canvas_frame.grid(row=0, column=0, sticky='nsew')
        self.canvas_frame.columnconfigure(0, weight=1)
        self.canvas_frame.rowconfigure(0, weight=1)

        tm = get_theme_manager()
        self.canvas = tk.Canvas(
            self.canvas_frame,
            bg=tm.get_color('canvas_bg'),
            scrollregion=(0, 0, 1000, 1000)
        )
        self.canvas.grid(row=0, column=0, sticky='nsew')

        self.v_scrollbar = ttk.Scrollbar(
            self.canvas_frame,
            orient='vertical',
            command=self._on_v_scroll
        )
        self.v_scrollbar.grid(row=0, column=1, sticky='ns')
        self.canvas.configure(yscrollcommand=self._on_yview_changed)

        self.h_scrollbar = ttk.Scrollbar(
            self.canvas_frame,
            orient='horizontal',
            command=self._on_h_scroll
        )
        self.h_scrollbar.grid(row=1, column=0, sticky='ew')
        self.canvas.configure(xscrollcommand=self.h_scrollbar.set)

        # Hide scrollbars initially (will be shown when needed)
        self.v_scrollbar.grid_remove()
        self.h_scrollbar.grid_remove()

        self.canvas.bind('<MouseWheel>', self.on_mousewheel)
        self.canvas.bind('<Button-4>', self.on_mousewheel)
        self.canvas.bind('<Button-5>', self.on_mousewheel)
        self.canvas.bind('<Configure>', self.on_canvas_resize)

        if DND_FILES is not None and self.on_drop_callback:
            # Registrovat jak soubory tak textové URL
            if DND_TEXT is not None:
                self.canvas.drop_target_register(DND_FILES, DND_TEXT)
            else:
                self.canvas.drop_target_register(DND_FILES)
            self.canvas.dnd_bind('<<Drop>>', self.on_drop)

        # Schedule initial scrollbar visibility check
        self.after(100, self._update_scrollbars_visibility)

    def _can_scroll_vertically(self) -> bool:
        """Check if vertical scrolling is needed"""
        # Použít scrollregion místo bbox pro konzistenci s bounds checking
        scrollregion = self.canvas.cget('scrollregion')
        if not scrollregion:
            return False

        try:
            # Parse scrollregion string "x1 y1 x2 y2"
            coords = [float(x) for x in scrollregion.split()]
            if len(coords) != 4:
                return False

            content_height = coords[3] - coords[1]
            canvas_height = self.canvas.winfo_height()
            # Přidat threshold 10px - scrollbar se zobrazí jen když je rozdíl výrazný
            return content_height > canvas_height + 10
        except (ValueError, IndexError):
            # Fallback na bbox pokud parsing selže
            bbox = self.canvas.bbox('all')
            if not bbox:
                return False
            content_height = bbox[3] - bbox[1]
            canvas_height = self.canvas.winfo_height()
            # Přidat threshold 10px - scrollbar se zobrazí jen když je rozdíl výrazný
            return content_height > canvas_height + 10

    def _can_scroll_horizontally(self) -> bool:
        """Check if horizontal scrolling is needed"""
        # Použít scrollregion místo bbox pro konzistenci s bounds checking
        scrollregion = self.canvas.cget('scrollregion')
        if not scrollregion:
            return False

        try:
            # Parse scrollregion string "x1 y1 x2 y2"
            coords = [float(x) for x in scrollregion.split()]
            if len(coords) != 4:
                return False

            content_width = coords[2] - coords[0]
            canvas_width = self.canvas.winfo_width()
            # Přidat threshold 10px - scrollbar se zobrazí jen když je rozdíl výrazný
            return content_width > canvas_width + 10
        except (ValueError, IndexError):
            # Fallback na bbox pokud parsing selže
            bbox = self.canvas.bbox('all')
            if not bbox:
                return False
            content_width = bbox[2] - bbox[0]
            canvas_width = self.canvas.winfo_width()
            # Přidat threshold 10px - scrollbar se zobrazí jen když je rozdíl výrazný
            return content_width > canvas_width + 10

    def _update_scrollbars_visibility(self):
        """Show/hide scrollbars based on content size"""
        # Wait for the canvas to be properly sized
        if self.canvas.winfo_width() <= 1 or self.canvas.winfo_height() <= 1:
            self.canvas.after(10, self._update_scrollbars_visibility)
            return

        if self._can_scroll_vertically():
            self.v_scrollbar.grid(row=0, column=1, sticky='ns')
        else:
            self.v_scrollbar.grid_remove()

        if self._can_scroll_horizontally():
            self.h_scrollbar.grid(row=1, column=0, sticky='ew')
        else:
            self.h_scrollbar.grid_remove()

    def _on_v_scroll(self, *args):
        """Handle vertical scrollbar with bounds checking"""
        if not self._can_scroll_vertically():
            return

        if args[0] == 'moveto':
            position = float(args[1])
            # Ensure position is within bounds [0, 1]
            position = max(0, min(1, position))
            self.canvas.yview_moveto(position)
            self._update_column_separators()
        elif args[0] == 'scroll':
            delta = int(args[1])
            units = args[2]

            current_top, current_bottom = self.canvas.yview()

            if units == 'units':
                scroll_amount = delta * 0.005  # 0.5% per unit for very smooth scrolling
            else:  # pages
                scroll_amount = delta * (current_bottom - current_top)

            new_top = current_top + scroll_amount
            new_top = max(0, min(1 - (current_bottom - current_top), new_top))

            self.canvas.yview_moveto(new_top)
            self._update_column_separators()

    def _on_h_scroll(self, *args):
        """Handle horizontal scrollbar with bounds checking"""
        if not self._can_scroll_horizontally():
            return

        if args[0] == 'moveto':
            position = float(args[1])
            # Ensure position is within bounds [0, 1]
            position = max(0, min(1, position))
            self.canvas.xview_moveto(position)
        elif args[0] == 'scroll':
            delta = int(args[1])
            units = args[2]

            current_left, current_right = self.canvas.xview()

            if units == 'units':
                scroll_amount = delta * 0.005  # 0.5% per unit for very smooth scrolling
            else:  # pages
                scroll_amount = delta * (current_right - current_left)

            new_left = current_left + scroll_amount
            new_left = max(0, min(1 - (current_right - current_left), new_left))

            self.canvas.xview_moveto(new_left)

    def _on_yview_changed(self, first, last):
        """yscrollcommand: Tk ho volá po každé změně pohledu (scroll, resize, moveto)."""
        self.v_scrollbar.set(first, last)
        if self._render_pending is None:
            self._render_pending = self.after_idle(self._render_visible_rows)

    def _render_visible_rows(self):
        """Dokreslí řádky kolem viditelné oblasti (graf se kreslí virtualizovaně)."""
        self._render_pending = None
        if self.graph_drawer.render_visible(self.canvas):
            # Po překreslení posadit plovoucí záhlaví na aktuální pozici
            self._update_column_separators()

    def _apply_scrollregion(self):
        """Scrollregion podle rozměrů celého grafu, ne jen vykreslených položek."""
        bounds = self._get_content_bbox_without_header()
        if bounds:
            buffer = 20
            self.canvas.configure(scrollregion=(
                max(0, bounds[0] - buffer), max(0, bounds[1] - buffer),
                bounds[2] + buffer, bounds[3] + buffer
            ))
        elif self.commits:
            # Fallback pro případ prázdného obsahu
            max_x = max(commit.x for commit in self.commits) + 100
            max_y = max(commit.y for commit in self.commits) + 100
            self.canvas.configure(scrollregion=(0, 0, max_x, max_y))

    def update_graph(self, commits: List[Commit]):
        self.commits = commits
        self.canvas.delete('all')

        if not commits:
            self._update_scrollbars_visibility()
            return

        # Auto-scroll to top when loading new repository content
        # (před kreslením - vykresluje se výřez podle aktuální pozice)
        self.canvas.yview_moveto(0)
        self.canvas.xview_moveto(0)

        self.graph_drawer.draw_graph(self.canvas, commits)

        # Nastavit event handlery pro změnu velikosti sloupců
        self.graph_drawer.setup_column_resize_events(
            self.canvas,
            on_resize_callback=self.update_scrollregion_and_scrollbars
        )

        self._apply_scrollregion()

        # Update scrollbars visibility after setting content
        self.canvas.update_idletasks()
        self._update_scrollbars_visibility()

        # Update column headers to reflect new scroll position
        self._update_column_separators()

    def _get_content_bbox_without_header(self):
        """Vrátí rozměry obsahu grafu bez plovoucího záhlaví.

        Graf se kreslí virtualizovaně, takže bbox položek canvasu pokrývá jen
        vykreslený výřez; rozměry celého grafu zná GraphDrawer. Bez něj (graf
        nenakreslen) bbox položek bez záhlaví jedním voláním Tcl.
        """
        bounds = self.graph_drawer.get_content_bounds()
        if bounds:
            return bounds
        return self.canvas.bbox("!column_header") or None

    def update_scrollregion_and_scrollbars(self):
        """Aktualizuje scrollregion a viditelnost scrollbarů po změně obsahu."""
        self.canvas.update_idletasks()
        self._apply_scrollregion()
        self._update_scrollbars_visibility()

    def on_drop(self, event):
        files = self.canvas.tk.splitlist(event.data)
        if files and self.on_drop_callback:
            folder_path = files[0]
            self.on_drop_callback(folder_path)

    def on_mousewheel(self, event):
        if event.delta:
            delta = -1 * (event.delta / 120)
        else:
            delta = -1 if event.num == 4 else 1

        # Only scroll if content is larger than visible area
        if self._can_scroll_vertically():
            import time
            current_time = time.time()
            time_since_last_scroll = current_time - self.last_scroll_time

            # Základní scroll krok - začíná pomalu
            base_scroll_amount = 0.005  # 0.5% per wheel notch - jemnější scrollování

            # Detekce nepřetržitého scrollování - pokud je interval kratší než 100ms, považujeme to za nepřetržité scrollování
            if time_since_last_scroll < 0.1 and self.scroll_velocity != 0:
                # Uživatel nepřetržitě scrolluje - postupně zrychlovat
                # Čím rychleji scrolluje (kratší interval), tím více momentu přidáme
                acceleration_factor = max(1.2, 2.0 - time_since_last_scroll * 8)  # 1.2 až ~2.0x
                scroll_increment = int(delta) * base_scroll_amount * acceleration_factor

                # Přidat k existující velocity (s omezením max rychlosti)
                self.scroll_velocity += scroll_increment
                # Omezit maximální rychlost na rozumnou hodnotu
                max_velocity = 0.2  # Max 20% viewportu za krok pro rychlé scrollování
                self.scroll_velocity = max(-max_velocity, min(max_velocity, self.scroll_velocity))
            else:
                # Pomalé scrollování nebo první scroll po pauze - začít pomalu
                self.scroll_velocity = int(delta) * base_scroll_amount

            self.last_scroll_time = current_time

            # Zrušit předchozí timeout pro reset velocity
            if self.scroll_timeout_id is not None:
                self.after_cancel(self.scroll_timeout_id)

            # Naplánovat reset velocity pokud uživatel přestane scrollovat
            self.scroll_timeout_id = self.after(200, self._reset_scroll_velocity)

            # Spustit/restartovat animaci s momentum
            self._start_momentum_scroll()

    def _reset_scroll_velocity(self):
        """Resetuje scroll velocity po pauze."""
        self.scroll_velocity = 0
        self.scroll_timeout_id = None

    def _start_momentum_scroll(self):
        """Spustí nebo restartuje momentum-based scrollování."""
        # Pokud už animace běží, nezačínat novou
        if self.scroll_animation_id is not None:
            return

        self._perform_momentum_step()

    def _perform_momentum_step(self):
        """Provede jeden krok momentum-based scrollování."""
        # Pokud je velocity téměř nulová, zastavit animaci
        if abs(self.scroll_velocity) < 0.0005:
            self.scroll_velocity = 0
            self.scroll_animation_id = None
            return

        current_top, current_bottom = self.canvas.yview()

        # Aplikovat velocity
        new_position = current_top + self.scroll_velocity

        # Bounds checking
        viewport_height = current_bottom - current_top
        if new_position < 0:
            new_position = 0
            self.scroll_velocity = 0  # Zastavit při dosažení konce
        elif new_position > 1 - viewport_height:
            new_position = 1 - viewport_height
            self.scroll_velocity = 0  # Zastavit při dosažení konce

        # Aplikovat novou pozici
        self.canvas.yview_moveto(new_position)
        self._update_column_separators()

        # Deceleration - postupné zpomalování (lehký efekt dojezdu)
        # Použít slabší deceleration (15%) pro rychlejší zastavení a lepší kontrolu
        deceleration = 0.85  # Ponechat 85% rychlosti = 15% útlum
        self.scroll_velocity *= deceleration

        # Naplánovat další krok animace (přibližně 60 FPS)
        self.scroll_animation_id = self.after(16, self._perform_momentum_step)

    def on_canvas_resize(self, event):
        """Handler pro změnu velikosti canvasu - aktualizuje záhlaví a scrollbary."""
        # Překreslit záhlaví při změně šířky okna
        self._update_column_separators()
        # Aktualizovat scrollbary při změně velikosti
        self._update_scrollbars_visibility()

    def apply_theme(self):
        """Apply current theme colors to canvas."""
        tm = get_theme_manager()
        self.canvas.config(bg=tm.get_color('canvas_bg'))

        # Redraw graph if loaded
        if hasattr(self.graph_drawer, '_current_commits') and self.graph_drawer._current_commits:
            self.update_graph(self.graph_drawer._current_commits)

    def _update_column_separators(self):
        """Aktualizuje pozici separátorů sloupců po scrollování."""
        if hasattr(self.graph_drawer, '_current_commits') and self.graph_drawer._current_commits:
            self.graph_drawer._draw_column_separators(self.canvas)
