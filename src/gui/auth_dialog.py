"""
Dialog pro GitHub OAuth Device Flow autentizaci.
"""

import tkinter as tk
from tkinter import ttk, messagebox
import threading
import webbrowser
from auth.github_auth import GitHubAuth
from utils.logging_config import get_logger
from utils.translations import t

logger = get_logger(__name__)


class GitHubAuthDialog:
    """Tkinter dialog pro GitHub OAuth Device Flow."""

    def __init__(self, parent):
        self.parent = parent
        self.result_token = None  # Výsledný access token
        self.cancelled = False
        self.github_auth = GitHubAuth()

        # Vytvořit dialog window
        self.dialog = tk.Toplevel(parent)
        self.dialog.title(t('auth_title'))
        self.dialog.geometry("500x350")
        self.dialog.resizable(False, False)
        self.dialog.transient(parent)
        self.dialog.grab_set()

        # Centrovať dialog
        self._center_dialog()

        # Vytvořit UI
        self._create_ui()

        # Spustit OAuth flow
        self._start_auth_flow()

    def _center_dialog(self):
        """Vycentruje dialog na obrazovce."""
        self.dialog.update_idletasks()
        width = self.dialog.winfo_width()
        height = self.dialog.winfo_height()
        x = (self.dialog.winfo_screenwidth() // 2) - (width // 2)
        y = (self.dialog.winfo_screenheight() // 2) - (height // 2)
        self.dialog.geometry(f'{width}x{height}+{x}+{y}')

    def _create_ui(self):
        """Vytvoří UI komponenty dialogu."""
        # Hlavní frame s paddingem
        main_frame = ttk.Frame(self.dialog, padding="20")
        main_frame.pack(fill=tk.BOTH, expand=True)

        # Nadpis
        title_label = ttk.Label(
            main_frame,
            text=t('auth_title'),
            font=('Arial', 14, 'bold')
        )
        title_label.pack(pady=(0, 15))

        # Instrukce
        instruction_label = ttk.Label(
            main_frame,
            text=t('auth_instruction'),
            justify=tk.CENTER,
            font=('Arial', 10)
        )
        instruction_label.pack(pady=(0, 20))

        # Kroky
        steps_label = ttk.Label(
            main_frame,
            text=t('auth_steps'),
            justify=tk.CENTER,
            font=('Arial', 9)
        )
        steps_label.pack(pady=(0, 10))

        # User code frame
        code_frame = ttk.Frame(main_frame)
        code_frame.pack(pady=(0, 15))

        # User code (velký, výrazný)
        self.user_code_label = ttk.Label(
            code_frame,
            text="------",
            font=('Courier New', 18, 'bold'),
            foreground='#0969da'
        )
        self.user_code_label.pack(side=tk.LEFT, padx=(0, 10))

        # Tlačítko pro kopírování kódu
        self.copy_button = ttk.Button(
            code_frame,
            text=t('copy_code'),
            command=self._copy_code,
            width=12
        )
        self.copy_button.pack(side=tk.LEFT)

        # Tlačítko pro otevření GitHubu
        self.open_button = ttk.Button(
            main_frame,
            text=t('open_github'),
            command=self._open_github,
            width=30
        )
        self.open_button.pack(pady=(0, 20))

        # Status label
        self.status_label = ttk.Label(
            main_frame,
            text=t('auth_preparing'),
            font=('Arial', 9),
            foreground='#666666'
        )
        self.status_label.pack(pady=(0, 10))

        # Progress bar
        self.progress = ttk.Progressbar(
            main_frame,
            mode='indeterminate',
            length=400
        )
        self.progress.pack(pady=(0, 20))
        self.progress.start(10)

        # Tlačítko Zrušit
        cancel_button = ttk.Button(
            main_frame,
            text=t('cancel'),
            command=self._cancel,
            width=15
        )
        cancel_button.pack()

        # Uložit reference pro pozdější použití
        self.device_code = None
        self.verification_uri = None

    def _start_auth_flow(self):
        """Spustí OAuth Device Flow v background threadu."""
        thread = threading.Thread(target=self._auth_worker, daemon=True)
        thread.start()

    def _auth_worker(self):
        """Worker thread pro OAuth flow."""
        try:
            # 1. Request device code
            self.dialog.after(0, self._update_status, t('auth_requesting'))

            device_data = self.github_auth.request_device_code()

            if not device_data:
                self.dialog.after(0, self._show_error, t('auth_error_code'))
                return

            self.device_code = device_data['device_code']
            self.verification_uri = device_data['verification_uri']
            user_code = device_data['user_code']
            interval = device_data.get('interval', 5)

            # 2. Zobrazit user code
            self.dialog.after(0, self._update_user_code, user_code)
            self.dialog.after(0, self._update_status, t('auth_waiting'))

            # 3. Poll pro access token
            token, status = self.github_auth.poll_for_token(self.device_code, interval)

            # 4. Zpracovat výsledek
            if status == "success" and token:
                self.result_token = token
                self.dialog.after(0, self._on_success)
            elif status == "timeout":
                self.dialog.after(0, self._show_error, t('auth_error_timeout'))
            elif status == "cancelled":
                self.dialog.after(0, self._show_error, t('auth_error_cancelled'))
            else:
                self.dialog.after(0, self._show_error, t('auth_error_general'))

        except Exception as e:
            logger.warning(f"Auth worker error: {e}")
            self.dialog.after(0, self._show_error, t('error') + f": {str(e)}")

    def _update_user_code(self, code: str):
        """Aktualizuje zobrazený user code."""
        self.user_code_label.config(text=code)
        self.copy_button.config(state='normal')
        self.open_button.config(state='normal')

    def _update_status(self, message: str):
        """Aktualizuje status label."""
        self.status_label.config(text=message)

    def _copy_code(self):
        """Zkopíruje user code do schránky."""
        code = self.user_code_label.cget('text')
        if code and code != "------":
            self.dialog.clipboard_clear()
            self.dialog.clipboard_append(code)
            self.status_label.config(text=t('code_copied'))

    def _open_github(self):
        """Otevře GitHub verification URL v prohlížeči."""
        if self.verification_uri:
            try:
                webbrowser.open(self.verification_uri)
                self.status_label.config(text=t('browser_opened'))
            except Exception as e:
                logger.warning(f"Failed to open browser: {e}")
                self.status_label.config(text=t('open_manually', self.verification_uri))

    def _on_success(self):
        """Callback po úspěšné autentizaci."""
        self.progress.stop()
        self.status_label.config(text=t('auth_success'), foreground='#1a7f37')
        self.dialog.after(1000, self.dialog.destroy)

    def _show_error(self, message: str):
        """Zobrazí chybovou zprávu a zavře dialog."""
        self.progress.stop()
        self.status_label.config(text="✗ " + t('error'), foreground='#cf222e')
        messagebox.showerror(t('auth_error_title'), message, parent=self.dialog)
        self.dialog.destroy()

    def _cancel(self):
        """Zruší autentizaci."""
        self.cancelled = True
        self.dialog.destroy()

    def show(self) -> str:
        """
        Zobrazí dialog a počká na výsledek.

        Returns:
            GitHub access token pokud úspěch, None pokud zrušeno/chyba
        """
        # Počkat na zavření dialogu
        self.dialog.wait_window()
        return self.result_token if not self.cancelled else None
