"""Theme switcher component with sun/moon icons."""

import tkinter as tk
from tkinter import ttk
import math
from utils.theme_manager import get_theme_manager


class ThemeSwitcher:
    """Component for switching between light and dark themes."""

    def __init__(self, parent_window):
        """
        Initialize ThemeSwitcher.

        Args:
            parent_window: MainWindow instance
        """
        self.parent = parent_window
        self.root = parent_window.root
        self.theme_manager = get_theme_manager()

        # UI elements
        self.theme_frame = None
        self.icon_sun = None
        self.icon_moon = None

    def create_switcher_ui(self):
        """Create the theme switcher UI with sun/moon icons."""
        # Theme switcher frame (vpravo nahoře, viditelný pouze v úvodním okně)
        # Parent je root aby byl nezávislý na main_frame grid layoutu
        self.theme_frame = ttk.Frame(self.root)

        # Ikony slunce a měsíce jako přepínač tématu - vytvořit Canvas widgety
        self.icon_sun = self._create_sun_icon(self.theme_frame, width=30, height=20)
        self.icon_sun.pack(side='left', padx=2)
        self.icon_sun.bind('<Button-1>', lambda e: self.switch_to_theme('light'))

        self.icon_moon = self._create_moon_icon(self.theme_frame, width=30, height=20)
        self.icon_moon.pack(side='left', padx=2)
        self.icon_moon.bind('<Button-1>', lambda e: self.switch_to_theme('dark'))

        # Nastavit počáteční stav ikon
        self.update_theme_icon_appearance()

    def _create_sun_icon(self, parent, width=30, height=20):
        """Vytvoří Canvas se sluníčkem (light mode ikona)."""
        canvas = tk.Canvas(parent, width=width, height=height, highlightthickness=0, cursor='hand2')

        # Pozadí - světle modré (obloha)
        canvas.create_rectangle(0, 0, width, height, fill='#87CEEB', outline='')

        # Střed ikony
        center_x = width // 2
        center_y = height // 2

        # Menší sluníčko uprostřed - žlutá výplň s černým okrajem
        sun_radius = 4
        canvas.create_oval(
            center_x - sun_radius, center_y - sun_radius,
            center_x + sun_radius, center_y + sun_radius,
            fill='#FFD700',  # Jasně žlutá
            outline='#000000',  # Černý okraj
            width=1
        )

        # 8 paprsků kolem slunce
        ray_length = 4
        ray_distance = sun_radius + 2  # Vzdálenost od středu slunce

        for i in range(8):
            angle = i * (2 * math.pi / 8)
            start_x = center_x + ray_distance * math.cos(angle)
            start_y = center_y + ray_distance * math.sin(angle)
            end_x = center_x + (ray_distance + ray_length) * math.cos(angle)
            end_y = center_y + (ray_distance + ray_length) * math.sin(angle)

            canvas.create_line(
                start_x, start_y, end_x, end_y,
                fill='#FFD700',  # Jasně žlutá
                width=2
            )

        # Černý rámeček
        canvas.create_rectangle(0, 0, width-1, height-1, outline='#000000', width=1)

        return canvas

    def _create_moon_icon(self, parent, width=30, height=20):
        """Vytvoří Canvas s měsíčkem (dark mode ikona)."""
        canvas = tk.Canvas(parent, width=width, height=height, highlightthickness=0, cursor='hand2')

        # Pozadí - černé (noční obloha)
        canvas.create_rectangle(0, 0, width, height, fill='#000000', outline='')

        # Střed ikony
        center_x = width // 2
        center_y = height // 2

        # Půlměsíc - vytvořen pomocí dvou kruhů
        moon_radius = 5

        # Velký bílý kruh (celý měsíc)
        canvas.create_oval(
            center_x - moon_radius - 2, center_y - moon_radius,
            center_x + moon_radius - 2, center_y + moon_radius,
            fill='#FFFFFF',  # Bílá
            outline=''
        )

        # Menší černý kruh (vytvoří výřez pro půlměsíc)
        canvas.create_oval(
            center_x - moon_radius + 2, center_y - moon_radius,
            center_x + moon_radius + 2, center_y + moon_radius,
            fill='#000000',  # Černá - stejná jako pozadí
            outline=''
        )

        # Přidat bílé hvězdy (malé body) - méně hvězd, dál od měsíce
        stars = [
            (4, 4),    # levý horní roh
            (25, 6),   # pravý horní roh
            (22, 16),  # pravý dolní roh
        ]

        for star_x, star_y in stars:
            # Malý kroužek jako hvězda
            canvas.create_oval(
                star_x - 1, star_y - 1,
                star_x + 1, star_y + 1,
                fill='#FFFFFF',
                outline=''
            )

        # Černý rámeček
        canvas.create_rectangle(0, 0, width-1, height-1, outline='#000000', width=1)

        return canvas

    def switch_to_theme(self, theme: str):
        """
        Switch to selected theme when icon is clicked.

        Args:
            theme: Theme name ('light' or 'dark')
        """
        if theme != self.theme_manager.get_current_theme():
            self.theme_manager.set_theme(theme)

    def update_theme_icon_appearance(self):
        """Update theme icon appearance based on current theme (highlight active, dim inactive)."""
        if not self.icon_sun or not self.icon_moon:
            return

        current_theme = self.theme_manager.get_current_theme()
        overlay_color = self.theme_manager.get_color('overlay_inactive')

        # Odstranit overlay z obou ikon
        self.icon_sun.delete('overlay')
        self.icon_moon.delete('overlay')

        # Přidat šedý overlay na neaktivní ikonu (bez 3D efektu)
        if current_theme == 'light':
            # Sluníčko aktivní, měsíček ztmavený
            width = self.icon_moon.winfo_reqwidth()
            height = self.icon_moon.winfo_reqheight()
            self.icon_moon.create_rectangle(
                0, 0, width, height,
                fill=overlay_color,
                stipple='gray75',  # Lehčí průhlednost pro jemnější ztmavení
                tags='overlay'
            )
        else:
            # Měsíček aktivní, sluníčko ztmavené
            width = self.icon_sun.winfo_reqwidth()
            height = self.icon_sun.winfo_reqheight()
            self.icon_sun.create_rectangle(
                0, 0, width, height,
                fill=overlay_color,
                stipple='gray75',  # Lehčí průhlednost pro jemnější ztmavení
                tags='overlay'
            )

    def show(self):
        """Show the theme switcher at the correct position."""
        if self.theme_frame:
            # Robustnější výpočet pozice s retry logikou
            self._update_position_with_retry()

    def _update_position_with_retry(self, retry_count=0):
        """Update position with retry logic for proper window initialization."""
        if not self.theme_frame:
            return

        # Dynamický výpočet pozice (vpravo nahoře)
        self.root.update_idletasks()
        window_width = self.root.winfo_width()

        # Pokud okno ještě nemá správnou šířku a jsme pod max retry, zkusit znovu
        if window_width <= 1 and retry_count < 10:
            self.root.after(50, lambda: self._update_position_with_retry(retry_count + 1))
            return

        # Použít aktuální šířku okna, nebo fallback pokud stále není dostupná
        if window_width <= 1:
            window_width = 600  # Fallback width

        theme_x = window_width - 85  # 10px main_frame padding + 75px pro ikony
        self.theme_frame.place(x=theme_x, y=15)
        self.theme_frame.tkraise()  # Zajistit že jsou ikony viditelné

    def hide(self):
        """Hide the theme switcher."""
        if self.theme_frame:
            self.theme_frame.place_forget()

    def update_position(self):
        """Update position after window resize."""
        if self.theme_frame and self.theme_frame.winfo_ismapped():
            # Okamžitá aktualizace pozice (bez retry, protože okno už je inicializované)
            self.root.update_idletasks()
            window_width = self.root.winfo_width()
            if window_width > 1:  # Pouze pokud máme validní šířku
                theme_x = window_width - 85  # 10px main_frame padding + 75px pro ikony
                self.theme_frame.place(x=theme_x, y=15)
                self.theme_frame.tkraise()
