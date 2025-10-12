"""
Tests for main.py entry point.

Tests application startup, Git detection, and logging setup.
"""

# MUST BE FIRST - initialize TCL/TK before any other imports
import tests.setup_tcl  # noqa: F401

import pytest
from unittest.mock import MagicMock, patch, call
import sys
import os
import subprocess

# Import module under test
import main


class TestCheckGitInstalled:
    """Tests for check_git_installed() function."""

    @patch('subprocess.run')
    def test_check_git_installed_success(self, mock_run):
        """Test successful Git detection."""
        # Arrange
        mock_run.return_value = MagicMock(returncode=0)

        # Act
        result = main.check_git_installed()

        # Assert
        assert result is True
        mock_run.assert_called_once_with(
            ['git', '--version'],
            capture_output=True,
            check=True,
            timeout=5
        )

    @patch('subprocess.run')
    def test_check_git_installed_not_found(self, mock_run):
        """Test Git not found (FileNotFoundError)."""
        # Arrange
        mock_run.side_effect = FileNotFoundError("git not found")

        # Act
        result = main.check_git_installed()

        # Assert
        assert result is False

    @patch('subprocess.run')
    def test_check_git_installed_called_process_error(self, mock_run):
        """Test Git command failed (CalledProcessError)."""
        # Arrange
        mock_run.side_effect = subprocess.CalledProcessError(1, 'git')

        # Act
        result = main.check_git_installed()

        # Assert
        assert result is False

    @patch('subprocess.run')
    def test_check_git_installed_timeout(self, mock_run):
        """Test Git command timeout (TimeoutExpired)."""
        # Arrange
        mock_run.side_effect = subprocess.TimeoutExpired('git', 5)

        # Act
        result = main.check_git_installed()

        # Assert
        assert result is False


class TestShowGitMissingDialog:
    """Tests for show_git_missing_dialog() function."""

    @patch('tkinter.messagebox.showerror')
    @patch('tkinter.Tk')
    def test_show_git_missing_dialog_success(self, mock_tk, mock_showerror):
        """Test successful dialog display."""
        # Arrange
        mock_root = MagicMock()
        mock_tk.return_value = mock_root

        # Act
        main.show_git_missing_dialog()

        # Assert
        mock_tk.assert_called_once()
        mock_root.withdraw.assert_called_once()
        mock_showerror.assert_called_once()
        mock_root.destroy.assert_called_once()

    @patch('tkinter.messagebox.showerror')
    @patch('tkinter.Tk')
    def test_show_git_missing_dialog_messagebox_content(self, mock_tk, mock_showerror):
        """Test that messagebox shows correct content."""
        # Arrange
        mock_root = MagicMock()
        mock_tk.return_value = mock_root

        # Act
        main.show_git_missing_dialog()

        # Assert
        call_args = mock_showerror.call_args
        assert call_args[0][0] == "Git není nainstalován"
        assert "https://git-scm.com/downloads" in call_args[0][1]
        assert "Git Visualizer" in call_args[0][1]

    @patch('builtins.print')
    @patch('tkinter.Tk', side_effect=ImportError("tkinter not available"))
    def test_show_git_missing_dialog_fallback_no_tkinter(self, mock_tk, mock_print):
        """Test fallback to print when tkinter fails."""
        # Act
        main.show_git_missing_dialog()

        # Assert
        # Should print error messages
        print_calls = [str(call) for call in mock_print.call_args_list]
        assert any("CHYBA" in str(call) or "Git" in str(call) for call in print_calls)

    @patch('tkinter.Tk')
    @patch('builtins.print')
    def test_show_git_missing_dialog_exception_handling(self, mock_print, mock_tk):
        """Test exception handling during dialog display."""
        # Arrange
        mock_tk.side_effect = Exception("Tkinter error")

        # Act - should not raise
        main.show_git_missing_dialog()

        # Assert - should print fallback message
        assert mock_print.called


class TestMain:
    """Tests for main() function."""

    @patch('main.check_git_installed')
    @patch('main.show_git_missing_dialog')
    @patch('sys.exit', side_effect=SystemExit(1))
    def test_main_git_not_installed_exits(self, mock_exit, mock_dialog, mock_check_git):
        """Test that main() exits if Git is not installed."""
        # Arrange
        mock_check_git.return_value = False

        # Act & Assert - should raise SystemExit
        with pytest.raises(SystemExit) as exc_info:
            main.main()

        assert exc_info.value.code == 1
        mock_check_git.assert_called_once()
        mock_dialog.assert_called_once()
        mock_exit.assert_called_once_with(1)

    @patch('main.check_git_installed', return_value=True)
    @patch('main.setup_logging')
    @patch('main.MainWindow')
    def test_main_logging_enabled_dev_mode(self, mock_window, mock_setup_logging, mock_check_git):
        """Test that logging is enabled in dev mode (not frozen)."""
        # Arrange
        mock_app = MagicMock()
        mock_window.return_value = mock_app

        # Ensure sys.frozen doesn't exist (dev mode default)
        if hasattr(sys, 'frozen'):
            delattr(sys, 'frozen')

        # Act
        main.main()

        # Assert
        mock_setup_logging.assert_called_once()
        mock_window.assert_called_once()
        mock_app.run.assert_called_once()

    @patch('main.check_git_installed', return_value=True)
    @patch('main.setup_logging')
    @patch('main.MainWindow')
    def test_main_logging_disabled_frozen_no_debug(self, mock_window, mock_setup_logging, mock_check_git):
        """Test that logging is disabled in frozen .exe without GITVIS_DEBUG."""
        # Arrange
        mock_app = MagicMock()
        mock_window.return_value = mock_app

        with patch.object(sys, 'frozen', True, create=True):
            with patch.dict(os.environ, {}, clear=True):  # No GITVIS_DEBUG
                # Act
                main.main()

        # Assert
        mock_setup_logging.assert_not_called()
        mock_window.assert_called_once()
        mock_app.run.assert_called_once()

    @patch('main.check_git_installed', return_value=True)
    @patch('main.setup_logging')
    @patch('main.MainWindow')
    def test_main_logging_enabled_frozen_with_debug(self, mock_window, mock_setup_logging, mock_check_git):
        """Test that logging is enabled in frozen .exe with GITVIS_DEBUG=1."""
        # Arrange
        mock_app = MagicMock()
        mock_window.return_value = mock_app

        with patch.object(sys, 'frozen', True, create=True):
            with patch.dict(os.environ, {'GITVIS_DEBUG': '1'}):
                # Act
                main.main()

        # Assert
        mock_setup_logging.assert_called_once()
        mock_window.assert_called_once()
        mock_app.run.assert_called_once()

    @patch('main.check_git_installed', return_value=True)
    @patch('main.setup_logging')
    @patch('main.MainWindow')
    @patch('builtins.print')
    def test_main_keyboard_interrupt(self, mock_print, mock_window, mock_setup_logging, mock_check_git):
        """Test graceful exit on KeyboardInterrupt (Ctrl+C)."""
        # Arrange
        mock_app = MagicMock()
        mock_app.run.side_effect = KeyboardInterrupt()
        mock_window.return_value = mock_app

        # Act
        main.main()

        # Assert
        mock_print.assert_called_once()
        assert "ukončena uživatelem" in str(mock_print.call_args)

    @patch('main.check_git_installed', return_value=True)
    @patch('main.setup_logging')
    @patch('main.MainWindow')
    @patch('builtins.print')
    def test_main_unexpected_exception(self, mock_print, mock_window, mock_setup_logging, mock_check_git):
        """Test handling of unexpected exceptions."""
        # Arrange
        mock_app = MagicMock()
        mock_app.run.side_effect = RuntimeError("Unexpected error")
        mock_window.return_value = mock_app

        # Act
        main.main()

        # Assert
        mock_print.assert_called_once()
        assert "Neočekávaná chyba" in str(mock_print.call_args)
        assert "Unexpected error" in str(mock_print.call_args)
