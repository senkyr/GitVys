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
        'separator': '#888888',
        'separator_active': '#000000',
        'separator_bg': '#888888',
        'header_bg': '#f0f0f0',
        'header_text': '#333333',

        # Tooltip
        'tooltip_bg': '#ffffe0',
        'tooltip_fg': '#000000',

        # Progress bar
        'progress_bg': '#e0e0e0',
        'progress_border': '#aaaaaa',

        # Unknown/fallback colors
        'unknown_color': '#E0E0E0',

        # Graph elements (light mode)
        'commit_text': '#000000',
        'commit_text_wip': '#555555',
        'author_text': '#333333',
        'email_text': '#666666',
        'date_text': '#666666',
        'description_text': '#666666',
        'tag_text_local': '#333333',
        'tag_text_remote': '#666666',
        'tag_emoji_remote': '#888888',
        'tag_emoji_local': '#000000',
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
        'separator': '#555555',
        'separator_active': '#888888',
        'separator_bg': '#444444',
        'header_bg': '#2a2a2a',
        'header_text': '#cccccc',

        # Tooltip
        'tooltip_bg': '#3a3a3a',
        'tooltip_fg': '#e0e0e0',

        # Progress bar
        'progress_bg': '#3a3a3a',
        'progress_border': '#555555',

        # Unknown/fallback colors
        'unknown_color': '#4a4a4a',

        # Graph elements (dark mode)
        'commit_text': '#e0e0e0',
        'commit_text_wip': '#999999',
        'author_text': '#cccccc',
        'email_text': '#aaaaaa',
        'date_text': '#aaaaaa',
        'description_text': '#aaaaaa',
        'tag_text_local': '#cccccc',
        'tag_text_remote': '#aaaaaa',
        'tag_emoji_remote': '#888888',
        'tag_emoji_local': '#e0e0e0',
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

        # Notify callbacks
        for callback in self._callbacks:
            try:
                callback(theme)
            except Exception as e:
                logger.warning(f"Theme change callback error: {e}")

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


# Global instance
_theme_manager = ThemeManager()


def get_theme_manager() -> ThemeManager:
    """Get the global ThemeManager instance."""
    return _theme_manager
