"""Language switcher component with flag icons."""

import tkinter as tk
from tkinter import ttk
from utils.translations import get_translation_manager
from utils.theme_manager import get_theme_manager


class LanguageSwitcher:
    """Component for switching between Czech and English languages."""

    def __init__(self, parent_window):
        """
        Initialize LanguageSwitcher.

        Args:
            parent_window: MainWindow instance
        """
        self.parent = parent_window
        self.root = parent_window.root
        self.tm = get_translation_manager()
        self.theme_manager = get_theme_manager()

        # UI elements
        self.language_frame = None
        self.flag_cs = None
        self.flag_en = None

    def create_switcher_ui(self):
        """Create the language switcher UI with flag icons."""
        # Language switcher frame (vlevo nahoře, viditelný pouze v úvodním okně)
        # Parent je root aby byl nezávislý na main_frame grid layoutu
        self.language_frame = ttk.Frame(self.root)

        # Vlajky jako přepínač jazyka - vytvořit Canvas widgety
        self.flag_cs = self._create_czech_flag(self.language_frame, width=30, height=20)
        self.flag_cs.pack(side='left', padx=2)
        self.flag_cs.bind('<Button-1>', lambda e: self.switch_to_language('cs'))

        self.flag_en = self._create_uk_flag(self.language_frame, width=30, height=20)
        self.flag_en.pack(side='left', padx=2)
        self.flag_en.bind('<Button-1>', lambda e: self.switch_to_language('en'))

        # Nastavit počáteční stav vlajek
        self.update_flag_appearance()

    def _create_czech_flag(self, parent, width=30, height=20):
        """Vytvoří Canvas s českou vlajkou."""
        canvas = tk.Canvas(parent, width=width, height=height, highlightthickness=0, cursor='hand2')

        # Horní polovina - bílá
        canvas.create_rectangle(0, 0, width, height//2, fill='#FFFFFF', outline='')

        # Dolní polovina - červená
        canvas.create_rectangle(0, height//2, width, height, fill='#D7141A', outline='')

        # Levý modrý trojúhelník
        canvas.create_polygon(
            0, 0,           # levý horní roh
            width//2, height//2,  # střed pravého okraje
            0, height,      # levý dolní roh
            fill='#11457E',
            outline=''
        )

        # Černý rámeček
        canvas.create_rectangle(0, 0, width-1, height-1, outline='#000000', width=1)

        return canvas

    def _create_uk_flag(self, parent, width=30, height=20):
        """Vytvoří Canvas s britskou vlajkou."""
        canvas = tk.Canvas(parent, width=width, height=height, highlightthickness=0, cursor='hand2')

        # Pozadí - modré
        canvas.create_rectangle(0, 0, width, height, fill='#012169', outline='')

        # Bílé diagonály (St. Andrew)
        # Levá horní -> pravá dolní
        canvas.create_line(0, 0, width, height, fill='#FFFFFF', width=6)
        # Pravá horní -> levá dolní
        canvas.create_line(width, 0, 0, height, fill='#FFFFFF', width=6)

        # Červené diagonály (St. Patrick) - užší
        canvas.create_line(0, 0, width, height, fill='#C8102E', width=3)
        canvas.create_line(width, 0, 0, height, fill='#C8102E', width=3)

        # Bílý kříž (St. George) - horizontální a vertikální
        canvas.create_rectangle(0, height//2-3, width, height//2+3, fill='#FFFFFF', outline='')
        canvas.create_rectangle(width//2-3, 0, width//2+3, height, fill='#FFFFFF', outline='')

        # Červený kříž (St. George) - užší
        canvas.create_rectangle(0, height//2-2, width, height//2+2, fill='#C8102E', outline='')
        canvas.create_rectangle(width//2-2, 0, width//2+2, height, fill='#C8102E', outline='')

        # Černý rámeček
        canvas.create_rectangle(0, 0, width-1, height-1, outline='#000000', width=1)

        return canvas

    def switch_to_language(self, language: str):
        """
        Switch to selected language when flag is clicked.

        Args:
            language: Language code ('cs' or 'en')
        """
        if language != self.tm.get_current_language():
            self.tm.set_language(language)

    def update_flag_appearance(self):
        """Update flag appearance based on current language (highlight active, dim inactive)."""
        if not self.flag_cs or not self.flag_en:
            return

        current_lang = self.tm.get_current_language()

        # Odstranit overlay z obou vlajek
        self.flag_cs.delete('overlay')
        self.flag_en.delete('overlay')

        # Přidat šedý semi-transparentní overlay na neaktivní vlajku
        overlay_color = self.theme_manager.get_color('overlay_inactive')
        if current_lang == 'cs':
            # Česká vlajka aktivní, anglická ztmavená
            width = self.flag_en.winfo_reqwidth()
            height = self.flag_en.winfo_reqheight()
            self.flag_en.create_rectangle(
                0, 0, width, height,
                fill=overlay_color,
                stipple='gray50',  # 50% průhlednost
                tags='overlay'
            )
        else:
            # Anglická vlajka aktivní, česká ztmavená
            width = self.flag_cs.winfo_reqwidth()
            height = self.flag_cs.winfo_reqheight()
            self.flag_cs.create_rectangle(
                0, 0, width, height,
                fill=overlay_color,
                stipple='gray50',
                tags='overlay'
            )

    def show(self):
        """Show the language switcher."""
        if self.language_frame:
            self.language_frame.place(x=15, y=15)  # 10px main_frame padding + 5px offset
            self.language_frame.tkraise()  # Zajistit že jsou vlaječky viditelné

    def hide(self):
        """Hide the language switcher."""
        if self.language_frame:
            self.language_frame.place_forget()
