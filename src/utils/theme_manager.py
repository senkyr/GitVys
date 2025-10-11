"""
Theme management for light/dark mode support.
"""
import os
import json
from typing import Dict
from utils.logging_config import get_logger

logger = get_logger(__name__)


# Theme color definitions
THEMES = {
    'light': {
        # Window & frame colors
        'window_bg': '#f0f0f0',
        'frame_bg': '#f0f0f0',

        # Canvas colors
        'canvas_bg': '#ffffff',
        'drop_area_bg': '#F0F8FF',  # Alice blue
        'drop_area_outline': '#4A90E2',  # Blue accent

        # Text colors
        'text_primary': '#000000',
        'text_secondary': '#333333',
        'text_tertiary': '#666666',
        'text_disabled': '#999999',

        # UI elements
        'separator': '#333333',
        'separator_active': '#000000',
        'separator_bg': '#888888',
        'header_bg': '#f0f0f0',
        'header_text': '#333333',

        # Tooltip
        'tooltip_bg': '#ffffe0',
        'tooltip_fg': '#000000',
        'tag_tooltip_bg': '#FFFFCC',

        # Progress bar
        'progress_bg': '#e0e0e0',
        'progress_border': '#aaaaaa',
        'progress_color_success': '#4CAF50',  # Green
        'progress_color_info': '#2196F3',     # Blue

        # Unknown/fallback colors
        'unknown_color': '#E0E0E0',

        # Graph elements (light mode)
        'commit_text': '#000000',
        'commit_text_wip': '#555555',
        'commit_node_outline': '#000000',
        'author_text': '#333333',
        'email_text': '#666666',
        'date_text': '#666666',
        'description_text': '#666666',
        'tag_text_local': '#333333',
        'tag_text_remote': '#666666',
        'tag_emoji_remote': '#888888',
        'tag_emoji_local': '#000000',
        'flag_text_normal': '#ffffff',
        'flag_text_remote': '#E0E0E0',

        # Auth dialog
        'auth_code_text': '#0969da',
        'auth_status_text': '#666666',
        'auth_success_text': '#1a7f37',
        'auth_error_text': '#cf222e',

        # General UI
        'overlay_inactive': '#808080',
    },
    'dark': {
        # Window & frame colors
        'window_bg': '#2b2b2b',
        'frame_bg': '#2b2b2b',

        # Canvas colors
        'canvas_bg': '#1e1e1e',
        'drop_area_bg': '#1a2332',  # Dark blue
        'drop_area_outline': '#4A90E2',  # Blue accent (same as light)

        # Text colors
        'text_primary': '#e0e0e0',
        'text_secondary': '#cccccc',
        'text_tertiary': '#aaaaaa',
        'text_disabled': '#666666',

        # UI elements
        'separator': '#666666',
        'separator_active': '#aaaaaa',
        'separator_bg': '#555555',
        'header_bg': '#2a2a2a',
        'header_text': '#cccccc',

        # Tooltip
        'tooltip_bg': '#3a3a3a',
        'tooltip_fg': '#e0e0e0',
        'tag_tooltip_bg': '#4a4a4a',

        # Progress bar
        'progress_bg': '#3a3a3a',
        'progress_border': '#555555',
        'progress_color_success': '#66BB6A',  # Lighter green for dark mode
        'progress_color_info': '#42A5F5',     # Lighter blue for dark mode

        # Unknown/fallback colors
        'unknown_color': '#4a4a4a',

        # Graph elements (dark mode)
        'commit_text': '#e0e0e0',
        'commit_text_wip': '#999999',
        'commit_node_outline': '#ffffff',
        'author_text': '#cccccc',
        'email_text': '#aaaaaa',
        'date_text': '#aaaaaa',
        'description_text': '#aaaaaa',
        'tag_text_local': '#cccccc',
        'tag_text_remote': '#aaaaaa',
        'tag_emoji_remote': '#888888',
        'tag_emoji_local': '#e0e0e0',
        'flag_text_normal': '#f0f0f0',
        'flag_text_remote': '#cccccc',

        # Auth dialog
        'auth_code_text': '#64B5F6',
        'auth_status_text': '#aaaaaa',
        'auth_success_text': '#66BB6A',
        'auth_error_text': '#EF5350',

        # General UI
        'overlay_inactive': '#666666',
    }
}


class ThemeManager:
    """Singleton for managing application themes."""

    _instance = None
    _initialized = False

    def __new__(cls):
        if cls._instance is None:
            cls._instance = super().__new__(cls)
        return cls._instance

    def __init__(self):
        if not self._initialized:
            self._current_theme = 'light'  # Default to light theme
            self._callbacks = []  # Callbacks to notify when theme changes
            self._root = None  # Reference to root window for TTK styling
            self._load_theme_preference()
            ThemeManager._initialized = True

    def _get_settings_dir(self) -> str:
        """Get the settings directory path."""
        home = os.path.expanduser('~')
        settings_dir = os.path.join(home, '.gitvys')
        os.makedirs(settings_dir, exist_ok=True)
        return settings_dir

    def _get_settings_file(self) -> str:
        """Get the settings file path."""
        return os.path.join(self._get_settings_dir(), 'settings.json')

    def _load_theme_preference(self):
        """Load theme preference from settings file."""
        try:
            settings_file = self._get_settings_file()
            if os.path.exists(settings_file):
                with open(settings_file, 'r', encoding='utf-8') as f:
                    settings = json.load(f)
                    self._current_theme = settings.get('theme', 'light')
                    logger.info(f"Loaded theme preference: {self._current_theme}")
        except Exception as e:
            logger.warning(f"Failed to load theme preference: {e}")
            self._current_theme = 'light'

    def _save_theme_preference(self):
        """Save theme preference to settings file."""
        try:
            settings_file = self._get_settings_file()

            # Load existing settings if any
            settings = {}
            if os.path.exists(settings_file):
                try:
                    with open(settings_file, 'r', encoding='utf-8') as f:
                        settings = json.load(f)
                except Exception:
                    pass

            # Update theme
            settings['theme'] = self._current_theme

            # Save
            with open(settings_file, 'w', encoding='utf-8') as f:
                json.dump(settings, f, indent=2, ensure_ascii=False)

            logger.info(f"Saved theme preference: {self._current_theme}")
        except Exception as e:
            logger.warning(f"Failed to save theme preference: {e}")

    def get_color(self, key: str) -> str:
        """
        Get color value for the given key in current theme.

        Args:
            key: Color key (e.g. 'window_bg', 'text_primary')

        Returns:
            Color value (hex string)
        """
        try:
            theme = THEMES.get(self._current_theme, THEMES['light'])
            return theme.get(key, '#000000')
        except Exception as e:
            logger.warning(f"Theme color error for key '{key}': {e}")
            return '#000000'

    def get_current_theme(self) -> str:
        """Get current theme name ('light' or 'dark')."""
        return self._current_theme

    def set_theme(self, theme: str):
        """
        Set current theme.

        Args:
            theme: Theme name ('light' or 'dark')
        """
        if theme not in THEMES:
            logger.warning(f"Unsupported theme: {theme}")
            return

        self._current_theme = theme
        self._save_theme_preference()

        # Apply TTK styling if root is set
        if self._root:
            self._configure_ttk_style()

        # Notify callbacks
        for callback in self._callbacks:
            try:
                callback(theme)
            except Exception as e:
                logger.warning(f"Theme change callback error: {e}")

    def set_root(self, root):
        """
        Set root window reference for TTK styling.

        Args:
            root: Tk root window instance
        """
        self._root = root
        # Apply initial TTK styling
        self._configure_ttk_style()

    def _configure_ttk_style(self):
        """Configure TTK widget styles for current theme."""
        if not self._root:
            return

        try:
            from tkinter import ttk
            style = ttk.Style(self._root)

            # Use 'clam' theme as base (allows more customization than 'default')
            try:
                style.theme_use('clam')
            except Exception:
                pass  # If clam not available, use default

            # Get colors for current theme
            bg_color = self.get_color('window_bg')
            frame_bg = self.get_color('frame_bg')
            text_color = self.get_color('text_primary')
            disabled_color = self.get_color('text_disabled')

            # Button colors
            if self.is_dark_mode():
                button_bg = '#3a3a3a'
                button_hover = '#4a4a4a'
                button_pressed = '#2a2a2a'
                button_border = '#555555'
            else:
                button_bg = '#e0e0e0'
                button_hover = '#d0d0d0'
                button_pressed = '#c0c0c0'
                button_border = '#adadad'

            # Configure Frame
            style.configure('TFrame', background=frame_bg)

            # Configure Label
            style.configure('TLabel', background=frame_bg, foreground=text_color)

            # Configure Button
            style.configure('TButton',
                background=button_bg,
                foreground=text_color,
                bordercolor=button_border,
                darkcolor=button_bg,
                lightcolor=button_bg,
                borderwidth=1,
                focuscolor='none')

            style.map('TButton',
                background=[('active', button_hover), ('pressed', button_pressed)],
                foreground=[('disabled', disabled_color)],
                bordercolor=[('active', button_border)])

            # Configure Entry
            if self.is_dark_mode():
                entry_bg = '#3a3a3a'          # Tmavé pozadí
                entry_fg = '#e0e0e0'          # Světlý text
                entry_border = '#555555'      # Šedý border
                entry_select_bg = '#4a4a4a'   # Světlejší šedá pro výběr
                entry_select_fg = '#ffffff'   # Bílý text při výběru
            else:
                entry_bg = '#ffffff'          # Bílé pozadí
                entry_fg = '#000000'          # Černý text
                entry_border = '#adadad'      # Šedý border
                entry_select_bg = '#0078d7'   # Modrá pro výběr (Windows styl)
                entry_select_fg = '#ffffff'   # Bílý text při výběru

            style.configure('TEntry',
                fieldbackground=entry_bg,
                foreground=entry_fg,
                bordercolor=entry_border,
                selectbackground=entry_select_bg,
                selectforeground=entry_select_fg,
                insertcolor=entry_fg)  # Barva kurzoru

            # Configure Progressbar
            progress_color = self.get_color('progress_color_success')
            progress_bg = self.get_color('progress_bg')

            style.configure('TProgressbar',
                background=progress_color,
                troughcolor=progress_bg,
                borderwidth=0,
                thickness=22)

            logger.debug(f"TTK style configured for {self._current_theme} theme")

        except Exception as e:
            logger.warning(f"Failed to configure TTK style: {e}")

    def register_callback(self, callback):
        """Register a callback to be called when theme changes."""
        if callback not in self._callbacks:
            self._callbacks.append(callback)

    def unregister_callback(self, callback):
        """Unregister a theme change callback."""
        if callback in self._callbacks:
            self._callbacks.remove(callback)

    def is_dark_mode(self) -> bool:
        """Check if current theme is dark mode."""
        return self._current_theme == 'dark'

    @staticmethod
    def calculate_luminance(hex_color: str) -> float:
        """
        Calculate relative luminance of a color (0-1).
        Uses WCAG formula for luminance calculation.

        Args:
            hex_color: Color in hex format (#RRGGBB)

        Returns:
            Luminance value between 0 (darkest) and 1 (lightest)
        """
        try:
            # Remove '#' and convert to RGB
            hex_color = hex_color.lstrip('#')
            if len(hex_color) != 6:
                return 0.5  # Default to medium luminance

            r = int(hex_color[0:2], 16) / 255.0
            g = int(hex_color[2:4], 16) / 255.0
            b = int(hex_color[4:6], 16) / 255.0

            # Apply gamma correction
            def adjust(c):
                if c <= 0.03928:
                    return c / 12.92
                return ((c + 0.055) / 1.055) ** 2.4

            r, g, b = adjust(r), adjust(g), adjust(b)

            # Calculate luminance using WCAG formula
            return 0.2126 * r + 0.7152 * g + 0.0722 * b

        except Exception as e:
            logger.warning(f"Failed to calculate luminance for {hex_color}: {e}")
            return 0.5  # Default to medium luminance

    @staticmethod
    def get_contrasting_text_color(background_color: str, dark_color: str = '#000000', light_color: str = '#ffffff') -> str:
        """
        Get a contrasting text color for a given background.

        Args:
            background_color: Background color in hex format
            dark_color: Color to use for light backgrounds (default black)
            light_color: Color to use for dark backgrounds (default white)

        Returns:
            Either dark_color or light_color depending on background luminance
        """
        luminance = ThemeManager.calculate_luminance(background_color)
        # Use dark text on light backgrounds, light text on dark backgrounds
        return dark_color if luminance > 0.5 else light_color


# Global instance
_theme_manager = ThemeManager()


def get_theme_manager() -> ThemeManager:
    """Get the global ThemeManager instance."""
    return _theme_manager
