import tkinter as tk
from tkinter import ttk, filedialog, messagebox
import os
try:
    from tkinterdnd2 import DND_FILES, TkinterDnD
except ImportError:
    TkinterDnD = None
    DND_FILES = None
from utils.logging_config import get_logger
from utils.translations import t

logger = get_logger(__name__)


class DragDropFrame(ttk.Frame):
    def __init__(self, parent, on_drop_callback=None):
        super().__init__(parent)
        self.on_drop_callback = on_drop_callback
        self.setup_ui()

    def setup_ui(self):
        self.columnconfigure(0, weight=1)
        self.rowconfigure(0, weight=1)

        # Získat systémovou barvu ttk.Frame pro pozadí
        style = ttk.Style()
        bg_color = style.lookup('TFrame', 'background')

        # Použít Canvas pro možnost nastavit background color
        self.drop_canvas = tk.Canvas(
            self,
            bg=bg_color,  # Systémová šedá barva
            highlightthickness=0
        )
        self.drop_canvas.grid(row=0, column=0, padx=40, pady=40, sticky='nsew')

        # Vytvořit label a button
        self.drop_label = ttk.Label(
            self.drop_canvas,
            text=t('drag_drop_text'),
            font=('Arial', 11),
            background='#F0F8FF',  # Alice blue - shodná s plochou
            justify='center'
        )

        self.browse_button = ttk.Button(
            self.drop_canvas,
            text=t('open_folder'),
            command=self.browse_folder,
            width=15
        )

        self.url_button = ttk.Button(
            self.drop_canvas,
            text=t('open_url'),
            command=self.open_url_dialog,
            width=15
        )

        # Bind pro resize aby se prvky centrovaly
        self.drop_canvas.bind('<Configure>', self._center_widgets)

        self.bind_drop_events()

    def _center_widgets(self, event=None):
        """Vycentruje widgety na canvas při resize."""
        canvas_width = self.drop_canvas.winfo_width()
        canvas_height = self.drop_canvas.winfo_height()

        center_x = canvas_width // 2
        center_y = canvas_height // 2

        # Vymazat vše
        self.drop_canvas.delete('all')

        # Modrá varianta - interaktivní accent
        padding = 5

        # Světle modrá plocha s čárkovaným modrým rámečkem
        self.drop_canvas.create_rectangle(
            padding, padding,
            canvas_width - padding, canvas_height - padding,
            fill='#F0F8FF',  # Alice blue - velmi světle modrá
            outline='#4A90E2',  # Modrá - interaktivní barva
            width=2,
            dash=(5, 3)  # Čárkovaná čára (5px čárka, 3px mezera)
        )

        # Symetrické rozložení:
        # Vzdálenost od horní hrany k labelu = vzdálenost mezi labelem a tlačítky
        padding_inner = 5  # Padding rámečku
        top_margin = (canvas_height - padding_inner * 2) / 3  # 1/3 dostupné výšky

        label_y = padding_inner + top_margin
        button_y = label_y + top_margin

        # Umístit label
        self.drop_canvas.create_window(
            center_x, int(label_y),
            window=self.drop_label,
            anchor='center'
        )

        # Umístit tlačítka vedle sebe
        button_spacing = 20  # Mezera mezi tlačítky

        self.drop_canvas.create_window(
            center_x - 75 - button_spacing // 2, int(button_y),
            window=self.browse_button,
            anchor='center'
        )
        self.drop_canvas.create_window(
            center_x + 75 + button_spacing // 2, int(button_y),
            window=self.url_button,
            anchor='center'
        )

    def bind_drop_events(self):
        # Pouze drag & drop binding, žádný click binding
        if TkinterDnD is not None:
            # Registrovat jak soubory tak textové URL
            try:
                from tkinterdnd2 import DND_TEXT
                self.drop_canvas.drop_target_register(DND_FILES, DND_TEXT)
            except Exception as e:
                # Fallback pokud DND_TEXT není dostupný
                logger.debug(f"DND_TEXT not available, using DND_FILES only: {e}")
                self.drop_canvas.drop_target_register(DND_FILES)
            self.drop_canvas.dnd_bind('<<Drop>>', self.on_drop)

    def on_drop(self, event):
        data_list = self.drop_canvas.tk.splitlist(event.data)
        if data_list:
            data = data_list[0].strip()

            # Auto-detect: URL nebo folder path
            if self._is_git_url(data):
                self.process_url(data)
            else:
                self.process_folder(data)

    def _is_git_url(self, text: str) -> bool:
        """
        Detekuje zda je text Git URL s bezpečnostní validací.

        Podporuje:
        - HTTP(S) URL z důvěryhodných hostů (GitHub, GitLab, Bitbucket)
        - Git SSH format (git@host:user/repo.git)
        """
        from urllib.parse import urlparse
        import re

        text = text.strip()

        # Git SSH format: git@github.com:user/repo.git
        ssh_pattern = r'^git@([\w\.-]+):([\w\-/]+)(\.git)?$'
        ssh_match = re.match(ssh_pattern, text, re.IGNORECASE)
        if ssh_match:
            host = ssh_match.group(1).lower()
            # Whitelist důvěryhodných SSH hostů
            trusted_ssh_hosts = {'github.com', 'gitlab.com', 'bitbucket.org'}
            if host in trusted_ssh_hosts or any(host.endswith(f'.{trusted}') for trusted in trusted_ssh_hosts):
                return True
            logger.warning(f"Untrusted SSH host: {host}")
            return False

        # HTTP(S) URL format s whitelist důvěryhodných hostů
        try:
            parsed = urlparse(text)

            # Povolit pouze http a https schéma
            if parsed.scheme not in ('http', 'https'):
                logger.debug(f"Invalid URL scheme: {parsed.scheme}")
                return False

            # Whitelist důvěryhodných hostů
            trusted_hosts = {
                'github.com', 'gitlab.com', 'bitbucket.org',
                'gitea.io', 'codeberg.org', 'sr.ht'  # Další známé Git hosty
            }

            netloc = parsed.netloc.lower()

            # Exact match nebo subdoména důvěryhodného hostu
            for trusted_host in trusted_hosts:
                if netloc == trusted_host or netloc.endswith(f'.{trusted_host}'):
                    return True

            logger.warning(f"Untrusted Git host: {netloc}")
            return False

        except Exception as e:
            logger.warning(f"Failed to parse URL: {e}")
            return False

    def update_language(self):
        """Update all UI texts when language changes."""
        self.drop_label.config(text=t('drag_drop_text'))
        self.browse_button.config(text=t('open_folder'))
        self.url_button.config(text=t('open_url'))

    def browse_folder(self):
        folder_path = filedialog.askdirectory(
            title=t('select_folder')
        )
        if folder_path:
            self.process_folder(folder_path)

    def _create_tooltip(self, widget, text):
        """Vytvoří tooltip pro widget."""
        tooltip = None

        def show_tooltip(event):
            nonlocal tooltip
            if tooltip:
                return

            # Vytvořit tooltip okno
            tooltip = tk.Toplevel()
            tooltip.wm_overrideredirect(True)
            tooltip.wm_attributes("-topmost", True)

            # Pozice tooltip okna
            x = event.x_root + 10
            y = event.y_root + 10
            tooltip.wm_geometry(f"+{x}+{y}")

            # Label s textem
            label = tk.Label(
                tooltip,
                text=text,
                background="#ffffe0",
                foreground="black",
                font=('Arial', 9),
                relief="solid",
                borderwidth=1,
                padx=5,
                pady=3
            )
            label.pack()

        def hide_tooltip(event):
            nonlocal tooltip
            if tooltip:
                tooltip.destroy()
                tooltip = None

        widget.bind('<Enter>', show_tooltip)
        widget.bind('<Leave>', hide_tooltip)

    def _paste_from_clipboard(self, entry_widget):
        """Vloží obsah schránky do entry pole."""
        try:
            # Získat obsah schránky
            clipboard_content = entry_widget.clipboard_get()

            # Vymazat současný obsah a vložit ze schránky
            entry_widget.delete(0, tk.END)
            entry_widget.insert(0, clipboard_content.strip())

        except tk.TclError:
            # Schránka je prázdná nebo nedostupná
            logger.debug("Clipboard is empty or unavailable")
            pass
        except Exception as e:
            logger.warning(f"Failed to paste from clipboard: {e}")
            pass

    def open_url_dialog(self):
        """Otevře dialog pro zadání URL repozitáře."""
        dialog = tk.Toplevel(self)
        dialog.title(t('enter_url_title'))
        dialog.resizable(False, False)

        # Konzistentní margin pro celý dialog
        MARGIN = 20

        # Label
        label = ttk.Label(
            dialog,
            text=t('enter_url_text'),
            justify='center'
        )
        label.pack(pady=MARGIN)

        # Frame pro Entry a Paste tlačítko
        entry_frame = ttk.Frame(dialog)
        entry_frame.pack(padx=MARGIN, pady=(0, MARGIN))

        # Entry pro URL
        entry = ttk.Entry(entry_frame, width=80)
        entry.pack(side='left', padx=(0, 5))

        # Paste tlačítko s clipboard emoji - ttk.Button s custom stylem pro větší font
        style = ttk.Style()
        style.configure('Emoji.TButton', font=('Segoe UI Emoji', 14))

        paste_button = ttk.Button(
            entry_frame,
            text="📋",
            width=3,
            style='Emoji.TButton',
            command=lambda: self._paste_from_clipboard(entry)
        )
        paste_button.pack(side='left')

        # Tooltip pro paste tlačítko
        self._create_tooltip(paste_button, t('paste_tooltip'))

        result = [None]

        # Setup "soft modal" behavior
        parent = self.winfo_toplevel()

        # Zachytit kliknutí na parent → vrátit focus na dialog
        def on_parent_interaction(event):
            if dialog.winfo_exists():
                dialog.focus_force()
                dialog.lift()

        parent.bind('<Button-1>', on_parent_interaction, add='+')

        # Focus monitoring - udržet focus v rámci dialogu
        # Také kontrolovat jestli parent ještě existuje
        def maintain_focus():
            if not dialog.winfo_exists():
                return

            # Kontrola: žije ještě parent?
            try:
                if not parent.winfo_exists():
                    dialog.destroy()
                    return
            except Exception as e:
                logger.debug(f"Parent window check failed: {e}")
                dialog.destroy()
                return

            # Získat aktuální widget s focusem
            current_focus = dialog.focus_displayof()

            # Pokud focus není v rámci dialogu (je None nebo mimo dialog),
            # vrátit ho na entry pole (ne na dialog jako takový)
            if current_focus is None or not str(current_focus).startswith(str(dialog)):
                entry.focus_set()

            dialog.after(100, maintain_focus)

        # Nastavit iniciální focus na entry po zobrazení dialogu
        dialog.after(50, lambda: entry.focus_set())
        maintain_focus()

        # Cleanup
        def cleanup_and_close():
            parent.unbind('<Button-1>')
            dialog.destroy()

        def on_ok():
            result[0] = entry.get()
            cleanup_and_close()

        def on_cancel():
            cleanup_and_close()

        # Enter a Escape key binding
        entry.bind('<Return>', lambda e: on_ok())
        dialog.bind('<Escape>', lambda e: on_cancel())

        # Tlačítka
        button_frame = ttk.Frame(dialog)
        button_frame.pack(pady=(0, MARGIN))

        ok_button = ttk.Button(button_frame, text=t('ok'), command=on_ok, width=10)
        ok_button.pack(side='left', padx=5)

        cancel_button = ttk.Button(button_frame, text=t('cancel'), command=on_cancel, width=10)
        cancel_button.pack(side='left', padx=5)

        # Nastavit soft modal dialog (bez grab_set)
        # transient zajistí že dialog je nad parent oknem, ale ne systémově topmost
        dialog.transient(self.master)

        # Nastavit close handler na dialogu
        dialog.protocol("WM_DELETE_WINDOW", on_cancel)

        # Nechat tkinter vypočítat velikost
        dialog.update_idletasks()

        # Vycentrovat dialog v hlavním okně
        parent = self.winfo_toplevel()
        parent_x = parent.winfo_x()
        parent_y = parent.winfo_y()
        parent_width = parent.winfo_width()
        parent_height = parent.winfo_height()

        dialog_width = dialog.winfo_width()
        dialog_height = dialog.winfo_height()

        x = parent_x + (parent_width - dialog_width) // 2
        y = parent_y + (parent_height - dialog_height) // 2

        dialog.geometry(f"+{x}+{y}")

        # Počkat na zavření dialogu
        dialog.wait_window()

        if result[0] and result[0].strip():
            self.process_url(result[0].strip())

    def process_url(self, url: str):
        """Zpracuje URL repozitáře - klonuje do temp složky."""
        if not self._is_git_url(url):
            messagebox.showerror(t('error'), t('invalid_url'))
            return

        if self.on_drop_callback:
            # Callback dostane URL místo cesty - main_window to rozpozná
            self.on_drop_callback(url)

    def process_folder(self, folder_path):
        if not os.path.isdir(folder_path):
            messagebox.showerror(t('error'), t('invalid_folder'))
            return

        git_folder = os.path.join(folder_path, '.git')
        if not os.path.exists(git_folder):
            messagebox.showerror(t('error'), t('not_git_repo'))
            return

        if self.on_drop_callback:
            self.on_drop_callback(folder_path)
