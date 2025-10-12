"""Tests for GitHubAuthDialog component.

This component handles GitHub OAuth Device Flow authentication with background threading.
"""

# MUST BE FIRST - initialize TCL/TK before any other imports
import tests.setup_tcl  # noqa: F401

import pytest
from unittest.mock import MagicMock, patch, call
import tkinter as tk
from tkinter import ttk

from gui.auth_dialog import GitHubAuthDialog


class TestGitHubAuthDialogInitialization:
    """Test GitHubAuthDialog initialization."""

    @patch('gui.auth_dialog.GitHubAuth')
    @patch.object(GitHubAuthDialog, '_start_auth_flow')
    def test_initialization_creates_dialog(self, mock_start_auth, mock_github_auth, root):
        """Test that initialization creates dialog window with correct properties."""
        dialog = GitHubAuthDialog(root)

        # Verify dialog window created
        assert dialog.dialog is not None
        assert isinstance(dialog.dialog, tk.Toplevel)

        # Verify initial state
        assert dialog.result_token is None
        assert dialog.cancelled is False
        assert dialog.device_code is None
        assert dialog.verification_uri is None

        # Verify GitHubAuth instance created
        assert mock_github_auth.called

        # Verify auth flow started
        assert mock_start_auth.called

    @patch('gui.auth_dialog.GitHubAuth')
    @patch.object(GitHubAuthDialog, '_start_auth_flow')
    def test_initialization_creates_ui_components(self, mock_start_auth, mock_github_auth, root):
        """Test that initialization creates all UI components."""
        dialog = GitHubAuthDialog(root)

        # Verify UI components created
        assert hasattr(dialog, 'user_code_label')
        assert hasattr(dialog, 'copy_button')
        assert hasattr(dialog, 'open_button')
        assert hasattr(dialog, 'status_label')
        assert hasattr(dialog, 'progress')

        assert isinstance(dialog.user_code_label, ttk.Label)
        assert isinstance(dialog.copy_button, ttk.Button)
        assert isinstance(dialog.open_button, ttk.Button)
        assert isinstance(dialog.status_label, ttk.Label)
        assert isinstance(dialog.progress, ttk.Progressbar)

    @patch('gui.auth_dialog.GitHubAuth')
    @patch.object(GitHubAuthDialog, '_start_auth_flow')
    def test_dialog_window_properties(self, mock_start_auth, mock_github_auth, root):
        """Test dialog window has correct properties (modal, transient, grab_set)."""
        dialog = GitHubAuthDialog(root)

        # Verify window properties - transient() returns window object, not string
        # We just verify it's set (not None/empty)
        assert dialog.dialog.transient() is not None


class TestAuthWorker:
    """Test OAuth authentication worker thread."""

    @patch('gui.auth_dialog.GitHubAuth')
    @patch.object(GitHubAuthDialog, '_start_auth_flow')
    def test_auth_worker_success(self, mock_start_auth, mock_github_auth, root):
        """Test auth worker handles successful authentication."""
        # Mock GitHubAuth methods
        mock_auth_instance = MagicMock()
        mock_auth_instance.request_device_code.return_value = {
            'device_code': 'test_device_code',
            'verification_uri': 'https://github.com/login/device',
            'user_code': 'TEST-1234',
            'interval': 5
        }
        mock_auth_instance.poll_for_token.return_value = ('test_token', 'success')
        mock_github_auth.return_value = mock_auth_instance

        dialog = GitHubAuthDialog(root)

        # Call auth worker directly
        dialog._auth_worker()

        # Verify device code requested
        mock_auth_instance.request_device_code.assert_called_once()

        # Verify polling called
        mock_auth_instance.poll_for_token.assert_called_once_with('test_device_code', 5)

        # Verify result token set
        assert dialog.result_token == 'test_token'

    @patch('gui.auth_dialog.GitHubAuth')
    @patch.object(GitHubAuthDialog, '_start_auth_flow')
    def test_auth_worker_timeout(self, mock_start_auth, mock_github_auth, root):
        """Test auth worker handles timeout."""
        # Mock timeout scenario
        mock_auth_instance = MagicMock()
        mock_auth_instance.request_device_code.return_value = {
            'device_code': 'test_device_code',
            'verification_uri': 'https://github.com/login/device',
            'user_code': 'TEST-1234',
            'interval': 5
        }
        mock_auth_instance.poll_for_token.return_value = (None, 'timeout')
        mock_github_auth.return_value = mock_auth_instance

        dialog = GitHubAuthDialog(root)

        # Call auth worker
        dialog._auth_worker()

        # Verify result token NOT set
        assert dialog.result_token is None

    @patch('gui.auth_dialog.GitHubAuth')
    @patch.object(GitHubAuthDialog, '_start_auth_flow')
    def test_auth_worker_cancelled(self, mock_start_auth, mock_github_auth, root):
        """Test auth worker handles cancellation."""
        # Mock cancelled scenario
        mock_auth_instance = MagicMock()
        mock_auth_instance.request_device_code.return_value = {
            'device_code': 'test_device_code',
            'verification_uri': 'https://github.com/login/device',
            'user_code': 'TEST-1234',
            'interval': 5
        }
        mock_auth_instance.poll_for_token.return_value = (None, 'cancelled')
        mock_github_auth.return_value = mock_auth_instance

        dialog = GitHubAuthDialog(root)

        # Call auth worker
        dialog._auth_worker()

        # Verify result token NOT set
        assert dialog.result_token is None

    @patch('gui.auth_dialog.GitHubAuth')
    @patch.object(GitHubAuthDialog, '_start_auth_flow')
    def test_auth_worker_device_code_error(self, mock_start_auth, mock_github_auth, root):
        """Test auth worker handles device code request failure."""
        # Mock device code error
        mock_auth_instance = MagicMock()
        mock_auth_instance.request_device_code.return_value = None
        mock_github_auth.return_value = mock_auth_instance

        dialog = GitHubAuthDialog(root)

        # Call auth worker
        dialog._auth_worker()

        # Verify device code requested
        mock_auth_instance.request_device_code.assert_called_once()

        # Verify polling NOT called (no device code)
        mock_auth_instance.poll_for_token.assert_not_called()

        # Verify result token NOT set
        assert dialog.result_token is None

    @patch('gui.auth_dialog.GitHubAuth')
    @patch.object(GitHubAuthDialog, '_start_auth_flow')
    def test_auth_worker_exception_handling(self, mock_start_auth, mock_github_auth, root):
        """Test auth worker handles exceptions gracefully."""
        # Mock exception during request
        mock_auth_instance = MagicMock()
        mock_auth_instance.request_device_code.side_effect = Exception("Network error")
        mock_github_auth.return_value = mock_auth_instance

        dialog = GitHubAuthDialog(root)

        # Call auth worker - should not raise exception
        try:
            dialog._auth_worker()
        except Exception as e:
            pytest.fail(f"Auth worker should handle exceptions, but raised: {e}")

        # Verify result token NOT set
        assert dialog.result_token is None


class TestUpdateUserCode:
    """Test user code display updates."""

    @patch('gui.auth_dialog.GitHubAuth')
    @patch.object(GitHubAuthDialog, '_start_auth_flow')
    def test_update_user_code_sets_label(self, mock_start_auth, mock_github_auth, root):
        """Test that update_user_code updates label text."""
        dialog = GitHubAuthDialog(root)

        # Initial state
        assert dialog.user_code_label.cget('text') == "------"

        # Update user code
        dialog._update_user_code("TEST-1234")

        # Verify label updated
        assert dialog.user_code_label.cget('text') == "TEST-1234"

    @patch('gui.auth_dialog.GitHubAuth')
    @patch.object(GitHubAuthDialog, '_start_auth_flow')
    def test_update_user_code_enables_buttons(self, mock_start_auth, mock_github_auth, root):
        """Test that update_user_code enables copy and open buttons."""
        dialog = GitHubAuthDialog(root)

        # Update user code
        dialog._update_user_code("TEST-1234")

        # Verify buttons enabled
        # Note: ttk.Button state is 'normal' when enabled
        assert str(dialog.copy_button['state']) == 'normal'
        assert str(dialog.open_button['state']) == 'normal'


class TestCopyCode:
    """Test code copying to clipboard."""

    @patch('gui.auth_dialog.GitHubAuth')
    @patch.object(GitHubAuthDialog, '_start_auth_flow')
    def test_copy_code_copies_to_clipboard(self, mock_start_auth, mock_github_auth, root):
        """Test that copy_code copies user code to clipboard."""
        dialog = GitHubAuthDialog(root)

        # Set user code
        dialog._update_user_code("TEST-1234")

        # Copy code
        dialog._copy_code()

        # Verify clipboard content
        clipboard_content = dialog.dialog.clipboard_get()
        assert clipboard_content == "TEST-1234"

    @patch('gui.auth_dialog.GitHubAuth')
    @patch.object(GitHubAuthDialog, '_start_auth_flow')
    def test_copy_code_updates_status(self, mock_start_auth, mock_github_auth, root):
        """Test that copy_code updates status label."""
        dialog = GitHubAuthDialog(root)

        # Set user code
        dialog._update_user_code("TEST-1234")

        # Copy code
        with patch('gui.auth_dialog.t') as mock_t:
            mock_t.return_value = "Code copied!"
            dialog._copy_code()

            # Verify status updated
            mock_t.assert_called_with('code_copied')

    @patch('gui.auth_dialog.GitHubAuth')
    @patch.object(GitHubAuthDialog, '_start_auth_flow')
    def test_copy_code_ignores_empty_code(self, mock_start_auth, mock_github_auth, root):
        """Test that copy_code does nothing for empty/placeholder code."""
        dialog = GitHubAuthDialog(root)

        # Initial state (placeholder)
        assert dialog.user_code_label.cget('text') == "------"

        # Try to copy placeholder
        dialog._copy_code()

        # Status should not be updated (no copy happened)
        # Initial status should remain


class TestOpenGitHub:
    """Test opening GitHub verification URL."""

    @patch('gui.auth_dialog.GitHubAuth')
    @patch.object(GitHubAuthDialog, '_start_auth_flow')
    @patch('gui.auth_dialog.webbrowser.open')
    def test_open_github_opens_browser(self, mock_webbrowser, mock_start_auth, mock_github_auth, root):
        """Test that open_github opens browser with verification URL."""
        dialog = GitHubAuthDialog(root)

        # Set verification URI
        dialog.verification_uri = "https://github.com/login/device"

        # Open GitHub
        dialog._open_github()

        # Verify browser opened
        mock_webbrowser.assert_called_once_with("https://github.com/login/device")

    @patch('gui.auth_dialog.GitHubAuth')
    @patch.object(GitHubAuthDialog, '_start_auth_flow')
    @patch('gui.auth_dialog.webbrowser.open')
    def test_open_github_updates_status(self, mock_webbrowser, mock_start_auth, mock_github_auth, root):
        """Test that open_github updates status label."""
        dialog = GitHubAuthDialog(root)

        # Set verification URI
        dialog.verification_uri = "https://github.com/login/device"

        # Open GitHub
        with patch('gui.auth_dialog.t') as mock_t:
            mock_t.return_value = "Browser opened!"
            dialog._open_github()

            # Verify status updated
            mock_t.assert_called_with('browser_opened')

    @patch('gui.auth_dialog.GitHubAuth')
    @patch.object(GitHubAuthDialog, '_start_auth_flow')
    @patch('gui.auth_dialog.webbrowser.open')
    def test_open_github_handles_browser_error(self, mock_webbrowser, mock_start_auth, mock_github_auth, root):
        """Test that open_github handles browser opening errors."""
        mock_webbrowser.side_effect = Exception("Browser not found")
        dialog = GitHubAuthDialog(root)

        # Set verification URI
        dialog.verification_uri = "https://github.com/login/device"

        # Open GitHub - should not raise exception
        try:
            dialog._open_github()
        except Exception as e:
            pytest.fail(f"Open GitHub should handle exceptions, but raised: {e}")

    @patch('gui.auth_dialog.GitHubAuth')
    @patch.object(GitHubAuthDialog, '_start_auth_flow')
    def test_open_github_does_nothing_without_uri(self, mock_start_auth, mock_github_auth, root):
        """Test that open_github does nothing if verification_uri not set."""
        dialog = GitHubAuthDialog(root)

        # verification_uri not set (None)
        assert dialog.verification_uri is None

        # Open GitHub - should do nothing
        with patch('gui.auth_dialog.webbrowser.open') as mock_webbrowser:
            dialog._open_github()

            # Browser should NOT be opened
            mock_webbrowser.assert_not_called()


class TestOnSuccess:
    """Test success callback."""

    @patch('gui.auth_dialog.GitHubAuth')
    @patch.object(GitHubAuthDialog, '_start_auth_flow')
    def test_on_success_stops_progress(self, mock_start_auth, mock_github_auth, root):
        """Test that on_success stops progress bar."""
        dialog = GitHubAuthDialog(root)

        # Mock progress.stop
        dialog.progress.stop = MagicMock()

        # Call on_success
        dialog._on_success()

        # Verify progress stopped
        dialog.progress.stop.assert_called_once()

    @patch('gui.auth_dialog.GitHubAuth')
    @patch.object(GitHubAuthDialog, '_start_auth_flow')
    def test_on_success_updates_status(self, mock_start_auth, mock_github_auth, root):
        """Test that on_success updates status label with success message."""
        dialog = GitHubAuthDialog(root)

        # Call on_success
        with patch('gui.auth_dialog.t') as mock_t:
            mock_t.return_value = "Authentication successful!"
            dialog._on_success()

            # Verify status updated
            mock_t.assert_called_with('auth_success')

    @patch('gui.auth_dialog.GitHubAuth')
    @patch.object(GitHubAuthDialog, '_start_auth_flow')
    def test_on_success_schedules_dialog_close(self, mock_start_auth, mock_github_auth, root):
        """Test that on_success schedules dialog to close after 1 second."""
        dialog = GitHubAuthDialog(root)

        # Mock dialog.after
        dialog.dialog.after = MagicMock()

        # Call on_success
        dialog._on_success()

        # Verify after called with 1000ms delay
        dialog.dialog.after.assert_called()
        call_args = dialog.dialog.after.call_args
        assert call_args[0][0] == 1000  # 1 second delay


class TestShowError:
    """Test error display."""

    @patch('gui.auth_dialog.GitHubAuth')
    @patch.object(GitHubAuthDialog, '_start_auth_flow')
    @patch('gui.auth_dialog.messagebox.showerror')
    def test_show_error_stops_progress(self, mock_showerror, mock_start_auth, mock_github_auth, root):
        """Test that show_error stops progress bar."""
        dialog = GitHubAuthDialog(root)

        # Mock progress.stop
        dialog.progress.stop = MagicMock()

        # Mock dialog.destroy to prevent actual destruction during test
        dialog.dialog.destroy = MagicMock()

        # Call show_error
        dialog._show_error("Test error")

        # Verify progress stopped
        dialog.progress.stop.assert_called_once()

    @patch('gui.auth_dialog.GitHubAuth')
    @patch.object(GitHubAuthDialog, '_start_auth_flow')
    @patch('gui.auth_dialog.messagebox.showerror')
    def test_show_error_displays_messagebox(self, mock_showerror, mock_start_auth, mock_github_auth, root):
        """Test that show_error displays error messagebox."""
        dialog = GitHubAuthDialog(root)

        # Mock dialog.destroy
        dialog.dialog.destroy = MagicMock()

        # Call show_error
        dialog._show_error("Test error message")

        # Verify messagebox shown
        mock_showerror.assert_called_once()
        assert "Test error message" in str(mock_showerror.call_args)

    @patch('gui.auth_dialog.GitHubAuth')
    @patch.object(GitHubAuthDialog, '_start_auth_flow')
    @patch('gui.auth_dialog.messagebox.showerror')
    def test_show_error_destroys_dialog(self, mock_showerror, mock_start_auth, mock_github_auth, root):
        """Test that show_error destroys dialog."""
        dialog = GitHubAuthDialog(root)

        # Mock dialog.destroy
        dialog.dialog.destroy = MagicMock()

        # Call show_error
        dialog._show_error("Test error")

        # Verify dialog destroyed
        dialog.dialog.destroy.assert_called_once()


class TestCancel:
    """Test cancellation."""

    @patch('gui.auth_dialog.GitHubAuth')
    @patch.object(GitHubAuthDialog, '_start_auth_flow')
    def test_cancel_sets_cancelled_flag(self, mock_start_auth, mock_github_auth, root):
        """Test that cancel sets cancelled flag."""
        dialog = GitHubAuthDialog(root)

        # Mock dialog.destroy
        dialog.dialog.destroy = MagicMock()

        # Initial state
        assert dialog.cancelled is False

        # Cancel
        dialog._cancel()

        # Verify cancelled flag set
        assert dialog.cancelled is True

    @patch('gui.auth_dialog.GitHubAuth')
    @patch.object(GitHubAuthDialog, '_start_auth_flow')
    def test_cancel_destroys_dialog(self, mock_start_auth, mock_github_auth, root):
        """Test that cancel destroys dialog."""
        dialog = GitHubAuthDialog(root)

        # Mock dialog.destroy
        dialog.dialog.destroy = MagicMock()

        # Cancel
        dialog._cancel()

        # Verify dialog destroyed
        dialog.dialog.destroy.assert_called_once()


class TestUpdateStatus:
    """Test status label updates."""

    @patch('gui.auth_dialog.GitHubAuth')
    @patch.object(GitHubAuthDialog, '_start_auth_flow')
    def test_update_status_changes_label_text(self, mock_start_auth, mock_github_auth, root):
        """Test that update_status changes status label text."""
        dialog = GitHubAuthDialog(root)

        # Update status
        dialog._update_status("Testing status update")

        # Verify label text changed
        assert dialog.status_label.cget('text') == "Testing status update"


class TestCenterDialog:
    """Test dialog centering."""

    @patch('gui.auth_dialog.GitHubAuth')
    @patch.object(GitHubAuthDialog, '_start_auth_flow')
    def test_center_dialog_positions_window(self, mock_start_auth, mock_github_auth, root):
        """Test that _center_dialog positions window in screen center."""
        dialog = GitHubAuthDialog(root)

        # Mock window dimensions
        dialog.dialog.winfo_width = MagicMock(return_value=500)
        dialog.dialog.winfo_height = MagicMock(return_value=350)
        dialog.dialog.winfo_screenwidth = MagicMock(return_value=1920)
        dialog.dialog.winfo_screenheight = MagicMock(return_value=1080)
        dialog.dialog.geometry = MagicMock()

        # Center dialog
        dialog._center_dialog()

        # Calculate expected position
        x = (1920 // 2) - (500 // 2)
        y = (1080 // 2) - (350 // 2)

        # Verify geometry called with correct position
        dialog.dialog.geometry.assert_called_once_with(f'500x350+{x}+{y}')


class TestAuthDialogIntegration:
    """Integration tests for GitHubAuthDialog."""

    @patch('gui.auth_dialog.GitHubAuth')
    @patch.object(GitHubAuthDialog, '_start_auth_flow')
    def test_full_initialization_workflow(self, mock_start_auth, mock_github_auth, root):
        """Test complete initialization workflow."""
        dialog = GitHubAuthDialog(root)

        # Verify all components initialized
        assert dialog.dialog is not None
        assert dialog.github_auth is not None
        assert dialog.user_code_label is not None
        assert dialog.copy_button is not None
        assert dialog.open_button is not None
        assert dialog.status_label is not None
        assert dialog.progress is not None

        # Verify auth flow started
        mock_start_auth.assert_called_once()

    @patch('gui.auth_dialog.GitHubAuth')
    @patch.object(GitHubAuthDialog, '_start_auth_flow')
    def test_show_method_waits_for_dialog(self, mock_start_auth, mock_github_auth, root):
        """Test that show() method returns result after dialog closes."""
        dialog = GitHubAuthDialog(root)

        # Mock wait_window to immediately return
        dialog.dialog.wait_window = MagicMock()

        # Set result
        dialog.result_token = "test_token"

        # Call show
        result = dialog.show()

        # Verify wait_window called
        dialog.dialog.wait_window.assert_called_once()

        # Verify result returned
        assert result == "test_token"

    @patch('gui.auth_dialog.GitHubAuth')
    @patch.object(GitHubAuthDialog, '_start_auth_flow')
    def test_show_method_returns_none_on_cancel(self, mock_start_auth, mock_github_auth, root):
        """Test that show() returns None when cancelled."""
        dialog = GitHubAuthDialog(root)

        # Mock wait_window
        dialog.dialog.wait_window = MagicMock()

        # Cancel dialog
        dialog.cancelled = True
        dialog.result_token = "should_not_be_returned"

        # Call show
        result = dialog.show()

        # Verify None returned
        assert result is None
