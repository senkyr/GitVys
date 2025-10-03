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
            text="Přetáhni sem složku repozitáře nebo ji vyhledej tlačítkem...",
            font=('Arial', 12),
            background='#F0F8FF'  # Alice blue - shodná s plochou
        )

        self.browse_button = ttk.Button(
            self.drop_canvas,
            text="Najít na disku...",
            command=self.browse_folder
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

        # Umístit label a button
        self.drop_canvas.create_window(
            center_x, center_y - 30,
            window=self.drop_label,
            anchor='center'
        )
        self.drop_canvas.create_window(
            center_x, center_y + 30,
            window=self.browse_button,
            anchor='center'
        )

    def bind_drop_events(self):
        # Pouze drag & drop binding, žádný click binding
        if TkinterDnD is not None:
            self.drop_canvas.drop_target_register(DND_FILES)
            self.drop_canvas.dnd_bind('<<Drop>>', self.on_drop)

    def on_drop(self, event):
        files = self.drop_canvas.tk.splitlist(event.data)
        if files:
            folder_path = files[0]
            self.process_folder(folder_path)

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
