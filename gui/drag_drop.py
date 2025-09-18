import tkinter as tk
from tkinter import ttk, filedialog, messagebox
import os
try:
    from tkinterdnd2 import DND_FILES, TkinterDnD
except ImportError:
    TkinterDnD = None
    DND_FILES = None


class DragDropFrame(ttk.Frame):
    def __init__(self, parent, on_drop_callback=None):
        super().__init__(parent)
        self.on_drop_callback = on_drop_callback
        self.setup_ui()

    def setup_ui(self):
        self.columnconfigure(0, weight=1)
        self.rowconfigure(0, weight=1)

        self.drop_frame = ttk.Frame(self, relief='ridge', borderwidth=2)
        self.drop_frame.grid(row=0, column=0, padx=20, pady=20, sticky='nsew')
        self.drop_frame.columnconfigure(0, weight=1)
        self.drop_frame.rowconfigure(0, weight=1)

        self.drop_label = ttk.Label(
            self.drop_frame,
            text="Přetáhni složku Git repozitáře sem\nnebo",
            font=('Arial', 12),
            anchor='center'
        )
        self.drop_label.grid(row=0, column=0, pady=(20, 10))

        self.browse_button = ttk.Button(
            self.drop_frame,
            text="Procházet...",
            command=self.browse_folder
        )
        self.browse_button.grid(row=1, column=0, pady=(10, 20))

        self.bind_drop_events()

    def bind_drop_events(self):
        self.drop_frame.bind('<Button-1>', self.on_click)
        self.drop_label.bind('<Button-1>', self.on_click)

        if TkinterDnD is not None:
            self.drop_frame.drop_target_register(DND_FILES)
            self.drop_frame.dnd_bind('<<Drop>>', self.on_drop)
            self.drop_label.drop_target_register(DND_FILES)
            self.drop_label.dnd_bind('<<Drop>>', self.on_drop)

    def on_drop(self, event):
        files = self.drop_frame.tk.splitlist(event.data)
        if files:
            folder_path = files[0]
            self.process_folder(folder_path)

    def on_click(self, event):
        self.browse_folder()

    def browse_folder(self):
        folder_path = filedialog.askdirectory(
            title="Vyber složku Git repozitáře"
        )
        if folder_path:
            self.process_folder(folder_path)

    def process_folder(self, folder_path):
        if not os.path.isdir(folder_path):
            messagebox.showerror("Chyba", "Vybraná cesta není platná složka")
            return

        git_folder = os.path.join(folder_path, '.git')
        if not os.path.exists(git_folder):
            messagebox.showerror("Chyba", "Vybraná složka neobsahuje Git repozitář")
            return

        if self.on_drop_callback:
            self.on_drop_callback(folder_path)