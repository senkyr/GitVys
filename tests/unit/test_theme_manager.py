"""Unit tests for utils.theme_manager module."""

import pytest
import os
import json
import tempfile
from unittest.mock import MagicMock, patch, mock_open
from utils.theme_manager import ThemeManager, get_theme_manager, THEMES


@pytest.fixture
def reset_theme_manager():
    """Reset ThemeManager singleton between tests."""
    # Save original state
    original_instance = ThemeManager._instance
    original_initialized = ThemeManager._initialized

    # Reset singleton
    ThemeManager._instance = None
    ThemeManager._initialized = False

    yield

    # Restore original state
    ThemeManager._instance = original_instance
    ThemeManager._initialized = original_initialized


@pytest.fixture
def temp_settings_dir(tmp_path):
    """Create temporary ~/.gitvys/ directory for testing."""
    settings_dir = tmp_path / ".gitvys"
    settings_dir.mkdir()

    # Mock os.path.expanduser to return temp directory
    with patch('os.path.expanduser') as mock_expand:
        mock_expand.return_value = str(tmp_path)
        yield settings_dir


class TestThemeManagerSingleton:
    """Tests for ThemeManager singleton pattern."""

    def test_singleton_returns_same_instance(self, reset_theme_manager):
        """Test that ThemeManager returns the same instance."""
        manager1 = ThemeManager()
        manager2 = ThemeManager()

        assert manager1 is manager2

    def test_get_theme_manager_returns_singleton(self, reset_theme_manager):
        """Test that get_theme_manager() returns singleton instance."""
        manager1 = get_theme_manager()
        manager2 = get_theme_manager()

        assert manager1 is manager2
        assert isinstance(manager1, ThemeManager)

    def test_singleton_initialized_once(self, reset_theme_manager):
        """Test that singleton is only initialized once."""
        with patch.object(ThemeManager, '_load_theme_preference') as mock_load:
            manager1 = ThemeManager()
            manager2 = ThemeManager()

            # _load_theme_preference should only be called once
            assert mock_load.call_count == 1


class TestThemeManagerInitialization:
    """Tests for ThemeManager initialization."""

    def test_initialization_defaults_to_light_theme(self, reset_theme_manager):
        """Test that ThemeManager initializes with light theme by default."""
        with patch.object(ThemeManager, '_load_theme_preference'):
            manager = ThemeManager()

            assert manager._current_theme == 'light'

    def test_initialization_loads_theme_preference(self, reset_theme_manager):
        """Test that initialization loads theme preference from file."""
        with patch.object(ThemeManager, '_load_theme_preference') as mock_load:
            manager = ThemeManager()

            mock_load.assert_called_once()

    def test_initialization_creates_empty_callback_list(self, reset_theme_manager):
        """Test that initialization creates empty callback list."""
        with patch.object(ThemeManager, '_load_theme_preference'):
            manager = ThemeManager()

            assert manager._callbacks == []

    def test_initialization_sets_root_to_none(self, reset_theme_manager):
        """Test that initialization sets root to None."""
        with patch.object(ThemeManager, '_load_theme_preference'):
            manager = ThemeManager()

            assert manager._root is None


class TestThemeGetterSetter:
    """Tests for theme getter/setter methods."""

    def test_get_current_theme_returns_light_by_default(self, reset_theme_manager):
        """Test that get_current_theme returns 'light' by default."""
        with patch.object(ThemeManager, '_load_theme_preference'):
            manager = ThemeManager()

            assert manager.get_current_theme() == 'light'

    def test_set_theme_changes_current_theme(self, reset_theme_manager):
        """Test that set_theme changes current theme."""
        with patch.object(ThemeManager, '_load_theme_preference'):
            with patch.object(ThemeManager, '_save_theme_preference'):
                manager = ThemeManager()

                manager.set_theme('dark')

                assert manager.get_current_theme() == 'dark'

    def test_set_theme_saves_preference(self, reset_theme_manager):
        """Test that set_theme saves preference to file."""
        with patch.object(ThemeManager, '_load_theme_preference'):
            with patch.object(ThemeManager, '_save_theme_preference') as mock_save:
                manager = ThemeManager()

                manager.set_theme('dark')

                mock_save.assert_called_once()

    def test_set_theme_rejects_invalid_theme(self, reset_theme_manager):
        """Test that set_theme rejects invalid theme names."""
        with patch.object(ThemeManager, '_load_theme_preference'):
            with patch.object(ThemeManager, '_save_theme_preference') as mock_save:
                manager = ThemeManager()
                original_theme = manager.get_current_theme()

                manager.set_theme('invalid_theme')

                # Theme should not change
                assert manager.get_current_theme() == original_theme
                # Save should not be called
                mock_save.assert_not_called()

    def test_is_dark_mode_returns_true_for_dark_theme(self, reset_theme_manager):
        """Test that is_dark_mode returns True for dark theme."""
        with patch.object(ThemeManager, '_load_theme_preference'):
            with patch.object(ThemeManager, '_save_theme_preference'):
                manager = ThemeManager()
                manager.set_theme('dark')

                assert manager.is_dark_mode() is True

    def test_is_dark_mode_returns_false_for_light_theme(self, reset_theme_manager):
        """Test that is_dark_mode returns False for light theme."""
        with patch.object(ThemeManager, '_load_theme_preference'):
            manager = ThemeManager()

            assert manager.is_dark_mode() is False


class TestThemePersistence:
    """Tests for theme persistence to settings file."""

    def test_load_theme_from_existing_settings_file(self, reset_theme_manager, temp_settings_dir):
        """Test loading theme from existing settings.json."""
        settings_file = temp_settings_dir / "settings.json"
        settings_file.write_text(json.dumps({'theme': 'dark', 'language': 'en'}))

        manager = ThemeManager()

        assert manager.get_current_theme() == 'dark'

    def test_load_theme_defaults_to_light_if_file_missing(self, reset_theme_manager, temp_settings_dir):
        """Test that theme defaults to light if settings.json doesn't exist."""
        # Don't create settings.json
        manager = ThemeManager()

        assert manager.get_current_theme() == 'light'

    def test_load_theme_handles_corrupt_settings_file(self, reset_theme_manager, temp_settings_dir):
        """Test that corrupt settings.json is handled gracefully."""
        settings_file = temp_settings_dir / "settings.json"
        settings_file.write_text("{ invalid json }")

        manager = ThemeManager()

        # Should default to light on error
        assert manager.get_current_theme() == 'light'

    def test_save_theme_creates_settings_file(self, reset_theme_manager, temp_settings_dir):
        """Test that save_theme_preference creates settings.json."""
        manager = ThemeManager()
        manager.set_theme('dark')

        settings_file = temp_settings_dir / "settings.json"
        assert settings_file.exists()

        with open(settings_file, 'r', encoding='utf-8') as f:
            settings = json.load(f)
            assert settings['theme'] == 'dark'

    def test_save_theme_preserves_other_settings(self, reset_theme_manager, temp_settings_dir):
        """Test that saving theme preserves other settings in file."""
        settings_file = temp_settings_dir / "settings.json"
        settings_file.write_text(json.dumps({'theme': 'light', 'language': 'cs', 'custom': 'value'}))

        manager = ThemeManager()
        manager.set_theme('dark')

        with open(settings_file, 'r', encoding='utf-8') as f:
            settings = json.load(f)
            assert settings['theme'] == 'dark'
            assert settings['language'] == 'cs'  # Preserved
            assert settings['custom'] == 'value'  # Preserved


class TestThemeColors:
    """Tests for theme color retrieval."""

    def test_get_color_returns_light_theme_color(self, reset_theme_manager):
        """Test that get_color returns correct color for light theme."""
        with patch.object(ThemeManager, '_load_theme_preference'):
            manager = ThemeManager()

            color = manager.get_color('window_bg')

            assert color == THEMES['light']['window_bg']
            assert color == '#f0f0f0'

    def test_get_color_returns_dark_theme_color(self, reset_theme_manager):
        """Test that get_color returns correct color for dark theme."""
        with patch.object(ThemeManager, '_load_theme_preference'):
            with patch.object(ThemeManager, '_save_theme_preference'):
                manager = ThemeManager()
                manager.set_theme('dark')

                color = manager.get_color('window_bg')

                assert color == THEMES['dark']['window_bg']
                assert color == '#2b2b2b'

    def test_get_color_returns_fallback_for_missing_key(self, reset_theme_manager):
        """Test that get_color returns fallback color for missing key."""
        with patch.object(ThemeManager, '_load_theme_preference'):
            manager = ThemeManager()

            color = manager.get_color('nonexistent_key')

            # Should return black as fallback
            assert color == '#000000'


class TestCallbackSystem:
    """Tests for theme change callback system."""

    def test_register_callback_adds_callback(self, reset_theme_manager):
        """Test that register_callback adds callback to list."""
        with patch.object(ThemeManager, '_load_theme_preference'):
            manager = ThemeManager()
            callback = MagicMock()

            manager.register_callback(callback)

            assert callback in manager._callbacks

    def test_register_callback_prevents_duplicates(self, reset_theme_manager):
        """Test that register_callback prevents duplicate callbacks."""
        with patch.object(ThemeManager, '_load_theme_preference'):
            manager = ThemeManager()
            callback = MagicMock()

            manager.register_callback(callback)
            manager.register_callback(callback)

            # Callback should only be added once
            assert manager._callbacks.count(callback) == 1

    def test_unregister_callback_removes_callback(self, reset_theme_manager):
        """Test that unregister_callback removes callback from list."""
        with patch.object(ThemeManager, '_load_theme_preference'):
            manager = ThemeManager()
            callback = MagicMock()

            manager.register_callback(callback)
            manager.unregister_callback(callback)

            assert callback not in manager._callbacks

    def test_set_theme_notifies_callbacks(self, reset_theme_manager):
        """Test that set_theme notifies all registered callbacks."""
        with patch.object(ThemeManager, '_load_theme_preference'):
            with patch.object(ThemeManager, '_save_theme_preference'):
                manager = ThemeManager()
                callback1 = MagicMock()
                callback2 = MagicMock()

                manager.register_callback(callback1)
                manager.register_callback(callback2)

                manager.set_theme('dark')

                callback1.assert_called_once_with('dark')
                callback2.assert_called_once_with('dark')

    def test_set_theme_handles_callback_errors_gracefully(self, reset_theme_manager):
        """Test that callback errors don't break theme switching."""
        with patch.object(ThemeManager, '_load_theme_preference'):
            with patch.object(ThemeManager, '_save_theme_preference'):
                manager = ThemeManager()
                failing_callback = MagicMock(side_effect=Exception("Callback error"))
                success_callback = MagicMock()

                manager.register_callback(failing_callback)
                manager.register_callback(success_callback)

                # Should not raise exception
                manager.set_theme('dark')

                # Theme should still change
                assert manager.get_current_theme() == 'dark'
                # Other callbacks should still be called
                success_callback.assert_called_once_with('dark')


class TestTTKStyling:
    """Tests for TTK widget styling."""

    def test_set_root_stores_root_reference(self, reset_theme_manager):
        """Test that set_root stores root window reference."""
        with patch.object(ThemeManager, '_load_theme_preference'):
            with patch.object(ThemeManager, '_configure_ttk_style'):
                manager = ThemeManager()
                mock_root = MagicMock()

                manager.set_root(mock_root)

                assert manager._root is mock_root

    def test_set_root_configures_ttk_style(self, reset_theme_manager):
        """Test that set_root triggers TTK style configuration."""
        with patch.object(ThemeManager, '_load_theme_preference'):
            with patch.object(ThemeManager, '_configure_ttk_style') as mock_configure:
                manager = ThemeManager()
                mock_root = MagicMock()

                manager.set_root(mock_root)

                mock_configure.assert_called()

    def test_set_theme_applies_ttk_style_when_root_set(self, reset_theme_manager):
        """Test that set_theme applies TTK style when root is set."""
        with patch.object(ThemeManager, '_load_theme_preference'):
            with patch.object(ThemeManager, '_save_theme_preference'):
                with patch.object(ThemeManager, '_configure_ttk_style') as mock_configure:
                    manager = ThemeManager()
                    manager._root = MagicMock()

                    manager.set_theme('dark')

                    # Should be called during set_theme
                    mock_configure.assert_called()

    def test_configure_ttk_style_skips_when_no_root(self, reset_theme_manager):
        """Test that _configure_ttk_style skips when root is None."""
        with patch.object(ThemeManager, '_load_theme_preference'):
            manager = ThemeManager()
            manager._root = None

            # Should not raise exception
            manager._configure_ttk_style()


class TestLuminanceCalculation:
    """Tests for luminance and contrast calculation."""

    def test_calculate_luminance_for_black(self):
        """Test luminance calculation for black color."""
        luminance = ThemeManager.calculate_luminance('#000000')

        assert luminance == pytest.approx(0.0, abs=0.01)

    def test_calculate_luminance_for_white(self):
        """Test luminance calculation for white color."""
        luminance = ThemeManager.calculate_luminance('#ffffff')

        assert luminance == pytest.approx(1.0, abs=0.01)

    def test_calculate_luminance_for_medium_gray(self):
        """Test luminance calculation for medium gray."""
        luminance = ThemeManager.calculate_luminance('#808080')

        # Medium gray should be around 0.2-0.3 luminance due to gamma correction
        assert 0.15 < luminance < 0.35

    def test_calculate_luminance_handles_invalid_hex(self):
        """Test that calculate_luminance handles invalid hex colors."""
        luminance = ThemeManager.calculate_luminance('invalid')

        # Should return 0.5 as fallback
        assert luminance == 0.5

    def test_get_contrasting_text_color_for_light_background(self):
        """Test that light backgrounds get dark text."""
        text_color = ThemeManager.get_contrasting_text_color('#ffffff')

        # White background should get black text
        assert text_color == '#000000'

    def test_get_contrasting_text_color_for_dark_background(self):
        """Test that dark backgrounds get light text."""
        text_color = ThemeManager.get_contrasting_text_color('#000000')

        # Black background should get white text
        assert text_color == '#ffffff'

    def test_get_contrasting_text_color_custom_colors(self):
        """Test get_contrasting_text_color with custom colors."""
        text_color = ThemeManager.get_contrasting_text_color(
            '#ffffff',
            dark_color='#333333',
            light_color='#eeeeee'
        )

        # Light background should use custom dark color
        assert text_color == '#333333'


class TestSettingsDirectory:
    """Tests for settings directory management."""

    def test_get_settings_dir_creates_directory(self, reset_theme_manager, temp_settings_dir):
        """Test that _get_settings_dir creates ~/.gitvys/ if it doesn't exist."""
        # Remove directory
        import shutil
        shutil.rmtree(temp_settings_dir)

        manager = ThemeManager()
        settings_dir = manager._get_settings_dir()

        assert os.path.exists(settings_dir)

    def test_get_settings_file_returns_correct_path(self, reset_theme_manager, temp_settings_dir):
        """Test that _get_settings_file returns correct path."""
        manager = ThemeManager()
        settings_file = manager._get_settings_file()

        # Use os.path.sep for cross-platform compatibility
        expected_ending = os.path.join('.gitvys', 'settings.json')
        assert settings_file.endswith(expected_ending)
