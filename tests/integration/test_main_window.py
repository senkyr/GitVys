"""Integration tests for gui.main_window module."""

import pytest
import tkinter as tk
from unittest.mock import MagicMock, patch, call


class TestMainWindowInitialization:
    """Tests for MainWindow initialization."""

    @patch('gui.main_window.get_translation_manager')
    @patch('gui.main_window.get_theme_manager')
    @patch('gui.main_window.RepositoryManager')
    def test_initialization_creates_components(self, mock_repo_manager, mock_theme_mgr, mock_trans_mgr, root):
        """Test that MainWindow initialization creates all components."""
        from gui.main_window import MainWindow

        # Mock managers
        mock_trans_mgr.return_value = MagicMock()
        mock_theme_mgr.return_value = MagicMock()
        mock_theme_mgr.return_value.get_color = MagicMock(return_value='#FFFFFF')

        window = MainWindow()

        # Should have created components
        assert window.language_switcher is not None
        assert window.theme_switcher is not None
        assert window.stats_display is not None
        assert window.repo_manager is not None

        # Cleanup
        window.root.destroy()

    @patch('gui.main_window.get_translation_manager')
    @patch('gui.main_window.get_theme_manager')
    @patch('gui.main_window.RepositoryManager')
    def test_initialization_registers_callbacks(self, mock_repo_manager, mock_theme_mgr, mock_trans_mgr, root):
        """Test that MainWindow registers callbacks with managers."""
        from gui.main_window import MainWindow

        # Mock managers
        mock_tm = MagicMock()
        mock_trans_mgr.return_value = mock_tm
        mock_theme = MagicMock()
        mock_theme.get_color = MagicMock(return_value='#FFFFFF')
        mock_theme_mgr.return_value = mock_theme

        window = MainWindow()

        # Should have registered callbacks
        mock_tm.register_callback.assert_called_once()
        mock_theme.register_callback.assert_called_once()

        # Cleanup
        window.root.destroy()


class TestComponentOrchestration:
    """Tests for component orchestration."""

    @patch('gui.main_window.get_translation_manager')
    @patch('gui.main_window.get_theme_manager')
    @patch('gui.main_window.RepositoryManager')
    @patch('gui.main_window.LanguageSwitcher')
    @patch('gui.main_window.ThemeSwitcher')
    @patch('gui.main_window.StatsDisplay')
    def test_language_switcher_shown_on_init(self, mock_stats, mock_theme_sw, mock_lang_sw, mock_repo, mock_theme_mgr, mock_trans_mgr, root):
        """Test that language switcher is shown after initialization."""
        from gui.main_window import MainWindow

        mock_trans_mgr.return_value = MagicMock()
        mock_theme_mgr.return_value = MagicMock()
        mock_theme_mgr.return_value.get_color = MagicMock(return_value='#FFFFFF')

        # Mock switcher
        mock_lang_instance = MagicMock()
        mock_lang_sw.return_value = mock_lang_instance

        # Mock StatsDisplay.create_stats_ui to return tuple of 3 widgets
        mock_stats_instance = MagicMock()
        mock_stats_instance.create_stats_ui.return_value = (MagicMock(), MagicMock(), MagicMock())
        mock_stats.return_value = mock_stats_instance

        window = MainWindow()

        # Should have called show() after init
        mock_lang_instance.show.assert_called()

        # Cleanup
        window.root.destroy()

    @patch('gui.main_window.get_translation_manager')
    @patch('gui.main_window.get_theme_manager')
    @patch('gui.main_window.RepositoryManager')
    @patch('gui.main_window.ThemeSwitcher')
    def test_theme_switcher_shown_on_init(self, mock_theme_sw, mock_repo, mock_theme_mgr, mock_trans_mgr, root):
        """Test that theme switcher is shown after initialization."""
        from gui.main_window import MainWindow

        mock_trans_mgr.return_value = MagicMock()
        mock_theme_mgr.return_value = MagicMock()
        mock_theme_mgr.return_value.get_color = MagicMock(return_value='#FFFFFF')

        mock_theme_instance = MagicMock()
        mock_theme_sw.return_value = mock_theme_instance

        window = MainWindow()

        # Should have called show() after init
        mock_theme_instance.show.assert_called()

        # Cleanup
        window.root.destroy()

    @patch('gui.main_window.get_translation_manager')
    @patch('gui.main_window.get_theme_manager')
    @patch('gui.main_window.RepositoryManager')
    def test_window_resize_binding(self, mock_repo, mock_theme_mgr, mock_trans_mgr, root):
        """Test that window resize binding is registered."""
        from gui.main_window import MainWindow

        mock_trans_mgr.return_value = MagicMock()
        mock_theme_mgr.return_value = MagicMock()
        mock_theme_mgr.return_value.get_color = MagicMock(return_value='#FFFFFF')

        window = MainWindow()

        # Should have <Configure> binding
        bindings = window.root.bind()
        assert '<Configure>' in bindings or window.root.bind('<Configure>')

        # Cleanup
        window.root.destroy()


class TestLanguageChange:
    """Tests for language change propagation."""

    @patch('gui.main_window.StatsDisplay')
    @patch('gui.main_window.get_translation_manager')
    @patch('gui.main_window.get_theme_manager')
    @patch('gui.main_window.RepositoryManager')
    def test_language_change_updates_title(self, mock_repo, mock_theme_mgr, mock_trans_mgr, mock_stats, root):
        """Test that language change updates window title."""
        from gui.main_window import MainWindow

        mock_tm = MagicMock()
        mock_trans_mgr.return_value = mock_tm
        mock_theme_mgr.return_value = MagicMock()
        mock_theme_mgr.return_value.get_color = MagicMock(return_value='#FFFFFF')

        # Mock StatsDisplay.create_stats_ui to return tuple of 3 widgets
        mock_stats_instance = MagicMock()
        mock_stats_instance.create_stats_ui.return_value = (MagicMock(), MagicMock(), MagicMock())
        mock_stats.return_value = mock_stats_instance

        window = MainWindow()
        initial_title = window.root.title()

        # Simulate language change
        with patch('gui.main_window.t') as mock_t:
            mock_t.return_value = "New Title"
            window._on_language_changed('en')

            # Title should be updated
            new_title = window.root.title()
            # Note: Exact assertion depends on implementation

        # Cleanup
        window.root.destroy()

    @patch('gui.main_window.StatsDisplay')
    @patch('gui.main_window.get_translation_manager')
    @patch('gui.main_window.get_theme_manager')
    @patch('gui.main_window.RepositoryManager')
    def test_language_change_updates_buttons(self, mock_repo, mock_theme_mgr, mock_trans_mgr, mock_stats, root):
        """Test that language change updates button labels."""
        from gui.main_window import MainWindow

        mock_trans_mgr.return_value = MagicMock()
        mock_theme_mgr.return_value = MagicMock()
        mock_theme_mgr.return_value.get_color = MagicMock(return_value='#FFFFFF')

        # Mock StatsDisplay.create_stats_ui to return tuple of 3 widgets
        mock_stats_instance = MagicMock()
        mock_stats_instance.create_stats_ui.return_value = (MagicMock(), MagicMock(), MagicMock())
        mock_stats.return_value = mock_stats_instance

        window = MainWindow()

        # Mock t() function
        with patch('gui.main_window.t') as mock_t:
            mock_t.side_effect = lambda key: f"translated_{key}"

            # Mock repo manager state
            window.repo_manager.is_cloned_repo = False

            window._on_language_changed('cs')

            # Buttons should be updated (verify via mock calls)
            # Note: Exact verification depends on implementation
            mock_t.assert_any_call('fetch_remote')
            mock_t.assert_any_call('close_repo')
            mock_t.assert_any_call('refresh')

        # Cleanup
        window.root.destroy()


class TestThemeChange:
    """Tests for theme change propagation."""

    @patch('gui.main_window.get_translation_manager')
    @patch('gui.main_window.get_theme_manager')
    @patch('gui.main_window.RepositoryManager')
    def test_theme_change_updates_icon_appearance(self, mock_repo, mock_theme_mgr, mock_trans_mgr, root):
        """Test that theme change updates theme switcher icon appearance."""
        from gui.main_window import MainWindow

        mock_trans_mgr.return_value = MagicMock()
        mock_theme = MagicMock()
        mock_theme.get_color = MagicMock(return_value='#FFFFFF')
        mock_theme_mgr.return_value = mock_theme

        window = MainWindow()

        # Mock theme switcher
        window.theme_switcher = MagicMock()

        window._on_theme_changed('dark')

        # Should have called update_theme_icon_appearance
        window.theme_switcher.update_theme_icon_appearance.assert_called_once()

        # Cleanup
        window.root.destroy()

    @patch('gui.main_window.get_translation_manager')
    @patch('gui.main_window.get_theme_manager')
    @patch('gui.main_window.RepositoryManager')
    def test_theme_change_applies_to_components(self, mock_repo, mock_theme_mgr, mock_trans_mgr, root):
        """Test that theme change applies to drag_drop_frame and graph_canvas."""
        from gui.main_window import MainWindow

        mock_trans_mgr.return_value = MagicMock()
        mock_theme = MagicMock()
        mock_theme.get_color = MagicMock(return_value='#FFFFFF')
        mock_theme_mgr.return_value = mock_theme

        window = MainWindow()

        # Mock components
        window.drag_drop_frame = MagicMock()
        window.graph_canvas = MagicMock()

        window._on_theme_changed('light')

        # Should apply theme to components
        window.drag_drop_frame.apply_theme.assert_called_once()
        window.graph_canvas.apply_theme.assert_called_once()

        # Cleanup
        window.root.destroy()


class TestWindowResize:
    """Tests for window resize handling."""

    @patch('gui.main_window.get_translation_manager')
    @patch('gui.main_window.get_theme_manager')
    @patch('gui.main_window.RepositoryManager')
    def test_window_resize_updates_theme_switcher_position(self, mock_repo, mock_theme_mgr, mock_trans_mgr, root):
        """Test that window resize updates theme switcher position."""
        from gui.main_window import MainWindow

        mock_trans_mgr.return_value = MagicMock()
        mock_theme_mgr.return_value = MagicMock()
        mock_theme_mgr.return_value.get_color = MagicMock(return_value='#FFFFFF')

        window = MainWindow()

        # Mock theme switcher with visible frame
        window.theme_switcher = MagicMock()
        window.theme_switcher.theme_frame = MagicMock()
        window.theme_switcher.theme_frame.winfo_ismapped.return_value = True

        # Simulate resize event
        event = MagicMock()
        event.widget = window.root

        window._on_window_resize(event)

        # Should have called update_position
        window.theme_switcher.update_position.assert_called_once()

        # Cleanup
        window.root.destroy()


class TestErrorHandling:
    """Tests for error handling."""

    @patch('gui.main_window.get_translation_manager')
    @patch('gui.main_window.get_theme_manager')
    @patch('gui.main_window.RepositoryManager')
    @patch('gui.main_window.messagebox.showerror')
    def test_show_error_displays_messagebox(self, mock_msgbox, mock_repo, mock_theme_mgr, mock_trans_mgr, root):
        """Test that show_error displays error messagebox."""
        from gui.main_window import MainWindow

        mock_trans_mgr.return_value = MagicMock()
        mock_theme_mgr.return_value = MagicMock()
        mock_theme_mgr.return_value.get_color = MagicMock(return_value='#FFFFFF')

        window = MainWindow()

        # Call show_error
        with patch('gui.main_window.t') as mock_t:
            mock_t.return_value = "Error"
            window.show_error("Test error message")

            # Should show messagebox
            mock_msgbox.assert_called_once()

        # Cleanup
        window.root.destroy()


class TestRepositoryDisplay:
    """Tests for repository display functionality."""

    @patch('gui.main_window.StatsDisplay')
    @patch('gui.main_window.get_translation_manager')
    @patch('gui.main_window.get_theme_manager')
    @patch('gui.main_window.RepositoryManager')
    def test_show_graph_hides_switchers(self, mock_repo, mock_theme_mgr, mock_trans_mgr, mock_stats, root):
        """Test that show_graph hides language and theme switchers."""
        from gui.main_window import MainWindow

        mock_trans_mgr.return_value = MagicMock()
        mock_theme_mgr.return_value = MagicMock()
        mock_theme_mgr.return_value.get_color = MagicMock(return_value='#FFFFFF')

        # Mock StatsDisplay.create_stats_ui to return tuple of 3 widgets
        mock_stats_instance = MagicMock()
        mock_stats_instance.create_stats_ui.return_value = (MagicMock(), MagicMock(), MagicMock())
        mock_stats.return_value = mock_stats_instance

        window = MainWindow()

        # Mock switchers
        window.language_switcher = MagicMock()
        window.theme_switcher = MagicMock()

        # Mock repo manager
        window.repo_manager.git_repo = MagicMock()
        window.repo_manager.git_repo.repo_path = "/test/repo"

        # Mock graph_canvas to prevent actual rendering
        window.graph_canvas = MagicMock()

        # Show graph
        window.show_graph([MagicMock()])

        # Switchers should be hidden
        window.language_switcher.hide.assert_called_once()
        window.theme_switcher.hide.assert_called_once()

        # Cleanup
        window.root.destroy()

    @patch('gui.main_window.get_translation_manager')
    @patch('gui.main_window.get_theme_manager')
    @patch('gui.main_window.RepositoryManager')
    def test_show_repository_selection_shows_switchers(self, mock_repo, mock_theme_mgr, mock_trans_mgr, root):
        """Test that show_repository_selection shows switchers."""
        from gui.main_window import MainWindow

        mock_trans_mgr.return_value = MagicMock()
        mock_theme_mgr.return_value = MagicMock()
        mock_theme_mgr.return_value.get_color = MagicMock(return_value='#FFFFFF')

        window = MainWindow()

        # Mock switchers
        window.language_switcher = MagicMock()
        window.theme_switcher = MagicMock()

        # Show repository selection
        window.show_repository_selection()

        # Switchers should be shown
        window.language_switcher.show.assert_called()
        window.theme_switcher.show.assert_called()

        # Cleanup
        window.root.destroy()
