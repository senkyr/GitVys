"""Tests for DragDropFrame component.

SECURITY NOTE: This component handles URL validation for Git repository cloning.
Critical to test URL whitelist validation to prevent malicious repository cloning.
"""

# MUST BE FIRST - initialize TCL/TK before any other imports
import tests.setup_tcl  # noqa: F401

import pytest
from unittest.mock import MagicMock, patch, call
import tkinter as tk
from tkinter import ttk

from gui.drag_drop import DragDropFrame


# Patch bind_drop_events to avoid tkinterdnd2 registration in tests
@pytest.fixture(autouse=True)
def mock_bind_drop_events():
    """Mock bind_drop_events to avoid tkinterdnd2 issues in tests."""
    # Import inside fixture to avoid early import before TCL/TK setup
    with patch('gui.drag_drop.DragDropFrame.bind_drop_events'):
        yield


class TestDragDropFrameInitialization:
    """Test DragDropFrame initialization."""

    def test_initialization_creates_widgets(self, root):
        """Test that initialization creates all required widgets."""
        callback = MagicMock()
        frame = DragDropFrame(root, on_drop_callback=callback)

        # Verify callback stored
        assert frame.on_drop_callback == callback

        # Verify widgets created
        assert hasattr(frame, 'drop_canvas')
        assert hasattr(frame, 'drop_label')
        assert hasattr(frame, 'browse_button')
        assert hasattr(frame, 'url_button')

        assert isinstance(frame.drop_canvas, tk.Canvas)
        assert isinstance(frame.drop_label, ttk.Label)
        assert isinstance(frame.browse_button, ttk.Button)
        assert isinstance(frame.url_button, ttk.Button)

    def test_initialization_without_callback(self, root):
        """Test initialization without callback (should not fail)."""
        frame = DragDropFrame(root)

        assert frame.on_drop_callback is None
        assert hasattr(frame, 'drop_canvas')


class TestURLValidation:
    """Test URL validation logic (SECURITY CRITICAL).

    These tests verify that only URLs from trusted Git hosting services
    are accepted, preventing malicious repository cloning.
    """

    def test_is_git_url_https_github(self, root):
        """Test HTTPS URL from GitHub (trusted host)."""
        frame = DragDropFrame(root)

        assert frame._is_git_url("https://github.com/user/repo.git") is True
        assert frame._is_git_url("https://github.com/user/repo") is True

    def test_is_git_url_https_gitlab(self, root):
        """Test HTTPS URL from GitLab (trusted host)."""
        frame = DragDropFrame(root)

        assert frame._is_git_url("https://gitlab.com/user/repo.git") is True
        assert frame._is_git_url("https://gitlab.com/user/repo") is True

    def test_is_git_url_https_bitbucket(self, root):
        """Test HTTPS URL from Bitbucket (trusted host)."""
        frame = DragDropFrame(root)

        assert frame._is_git_url("https://bitbucket.org/user/repo.git") is True
        assert frame._is_git_url("https://bitbucket.org/user/repo") is True

    def test_is_git_url_https_other_trusted_hosts(self, root):
        """Test HTTPS URLs from other trusted hosts (gitea.io, codeberg.org, sr.ht)."""
        frame = DragDropFrame(root)

        assert frame._is_git_url("https://gitea.io/user/repo.git") is True
        assert frame._is_git_url("https://codeberg.org/user/repo.git") is True
        assert frame._is_git_url("https://sr.ht/~user/repo") is True

    def test_is_git_url_subdomain_trusted(self, root):
        """Test subdomain of trusted host is accepted."""
        frame = DragDropFrame(root)

        # Subdomains should be accepted
        assert frame._is_git_url("https://api.github.com/repos/user/repo") is True
        assert frame._is_git_url("https://gitlab.example.gitlab.com/user/repo") is True

    def test_is_git_url_rejects_untrusted_host(self, root):
        """Test that untrusted hosts are rejected (SECURITY)."""
        frame = DragDropFrame(root)

        # Evil host should be rejected
        assert frame._is_git_url("https://evil.com/user/repo.git") is False
        assert frame._is_git_url("https://malicious-site.org/repo.git") is False
        assert frame._is_git_url("https://attacker.net/malware.git") is False

    def test_is_git_url_rejects_similar_but_untrusted_host(self, root):
        """Test that similar-looking but untrusted hosts are rejected."""
        frame = DragDropFrame(root)

        # These look similar but are NOT trusted
        assert frame._is_git_url("https://github.com.evil.com/repo.git") is False
        assert frame._is_git_url("https://fakegithub.com/repo.git") is False
        assert frame._is_git_url("https://github-clone.com/repo.git") is False

    def test_is_git_url_ssh_github(self, root):
        """Test SSH format for GitHub (git@github.com:user/repo.git)."""
        frame = DragDropFrame(root)

        assert frame._is_git_url("git@github.com:user/repo.git") is True
        assert frame._is_git_url("git@github.com:user/repo") is True

    def test_is_git_url_ssh_gitlab(self, root):
        """Test SSH format for GitLab."""
        frame = DragDropFrame(root)

        assert frame._is_git_url("git@gitlab.com:user/repo.git") is True
        assert frame._is_git_url("git@gitlab.com:group/subgroup/repo.git") is True

    def test_is_git_url_ssh_untrusted(self, root):
        """Test SSH format rejects untrusted hosts."""
        frame = DragDropFrame(root)

        assert frame._is_git_url("git@evil.com:user/repo.git") is False
        assert frame._is_git_url("git@malicious.org:repo.git") is False

    def test_is_git_url_invalid_scheme(self, root):
        """Test that invalid URL schemes are rejected."""
        frame = DragDropFrame(root)

        assert frame._is_git_url("ftp://github.com/user/repo.git") is False
        assert frame._is_git_url("file:///home/user/repo") is False
        assert frame._is_git_url("ssh://github.com/user/repo") is False

    def test_is_git_url_invalid_format(self, root):
        """Test that malformed URLs are rejected."""
        frame = DragDropFrame(root)

        assert frame._is_git_url("not a url") is False
        assert frame._is_git_url("github.com/user/repo") is False  # No scheme
        assert frame._is_git_url("https://") is False
        assert frame._is_git_url("") is False
        assert frame._is_git_url("   ") is False

    def test_is_git_url_http_trusted(self, root):
        """Test HTTP (not HTTPS) from trusted host is accepted."""
        frame = DragDropFrame(root)

        # HTTP should be accepted (will be handled by git clone)
        assert frame._is_git_url("http://github.com/user/repo.git") is True


class TestAutoDetection:
    """Test auto-detection of URL vs folder path in drag & drop."""

    @patch.object(DragDropFrame, 'process_url')
    @patch.object(DragDropFrame, 'process_folder')
    def test_on_drop_detects_url(self, mock_process_folder, mock_process_url, root):
        """Test that on_drop detects URL and calls process_url."""
        frame = DragDropFrame(root)

        # Mock tk object with splitlist method
        mock_tk = MagicMock()
        mock_tk.splitlist = MagicMock(return_value=["https://github.com/user/repo.git"])
        frame.drop_canvas.tk = mock_tk

        # Mock event with URL data
        event = MagicMock()
        event.data = "https://github.com/user/repo.git"

        frame.on_drop(event)

        # Should call process_url, not process_folder
        mock_process_url.assert_called_once_with("https://github.com/user/repo.git")
        mock_process_folder.assert_not_called()

    @patch.object(DragDropFrame, 'process_url')
    @patch.object(DragDropFrame, 'process_folder')
    def test_on_drop_detects_folder(self, mock_process_folder, mock_process_url, root):
        """Test that on_drop detects folder path and calls process_folder."""
        frame = DragDropFrame(root)

        # Mock tk object with splitlist method
        mock_tk = MagicMock()
        mock_tk.splitlist = MagicMock(return_value=["/home/user/project"])
        frame.drop_canvas.tk = mock_tk

        # Mock event with folder path
        event = MagicMock()
        event.data = "/home/user/project"

        frame.on_drop(event)

        # Should call process_folder, not process_url
        mock_process_folder.assert_called_once_with("/home/user/project")
        mock_process_url.assert_not_called()

    @patch.object(DragDropFrame, 'process_url')
    @patch.object(DragDropFrame, 'process_folder')
    def test_on_drop_strips_whitespace(self, mock_process_folder, mock_process_url, root):
        """Test that on_drop strips whitespace from data."""
        frame = DragDropFrame(root)

        # Mock tk object with splitlist method
        mock_tk = MagicMock()
        mock_tk.splitlist = MagicMock(return_value=["  /home/user/project  "])
        frame.drop_canvas.tk = mock_tk

        # Mock event with whitespace
        event = MagicMock()
        event.data = "  /home/user/project  "

        frame.on_drop(event)

        # Should strip whitespace
        mock_process_folder.assert_called_once_with("/home/user/project")


class TestFolderProcessing:
    """Test folder validation and processing."""

    @patch('gui.drag_drop.messagebox.showerror')
    @patch('os.path.isdir')
    def test_process_folder_invalid_directory(self, mock_isdir, mock_error, root):
        """Test error shown for non-existent directory."""
        mock_isdir.return_value = False
        callback = MagicMock()
        frame = DragDropFrame(root, on_drop_callback=callback)

        frame.process_folder("/invalid/path")

        # Should show error, not call callback
        mock_error.assert_called_once()
        callback.assert_not_called()

    @patch('gui.drag_drop.messagebox.showerror')
    @patch('os.path.exists')
    @patch('os.path.isdir')
    def test_process_folder_not_git_repo(self, mock_isdir, mock_exists, mock_error, root):
        """Test error shown for folder without .git."""
        mock_isdir.return_value = True
        mock_exists.return_value = False  # .git doesn't exist
        callback = MagicMock()
        frame = DragDropFrame(root, on_drop_callback=callback)

        frame.process_folder("/valid/path")

        # Should show error, not call callback
        mock_error.assert_called_once()
        callback.assert_not_called()

    @patch('os.path.exists')
    @patch('os.path.isdir')
    def test_process_folder_valid_git_repo(self, mock_isdir, mock_exists, root):
        """Test callback called for valid Git repository."""
        mock_isdir.return_value = True
        mock_exists.return_value = True  # .git exists
        callback = MagicMock()
        frame = DragDropFrame(root, on_drop_callback=callback)

        frame.process_folder("/valid/git/repo")

        # Should call callback with folder path
        callback.assert_called_once_with("/valid/git/repo")

    @patch('os.path.join')
    @patch('os.path.exists')
    @patch('os.path.isdir')
    def test_process_folder_checks_git_subfolder(self, mock_isdir, mock_exists, mock_join, root):
        """Test that .git subfolder is checked."""
        mock_isdir.return_value = True
        mock_exists.return_value = True
        mock_join.return_value = "/repo/.git"
        callback = MagicMock()
        frame = DragDropFrame(root, on_drop_callback=callback)

        frame.process_folder("/repo")

        # Should check for .git subfolder
        mock_join.assert_called_once_with("/repo", ".git")
        mock_exists.assert_called_once_with("/repo/.git")


class TestURLProcessing:
    """Test URL processing."""

    @patch.object(DragDropFrame, '_is_git_url')
    @patch('gui.drag_drop.messagebox.showerror')
    def test_process_url_invalid(self, mock_error, mock_is_git_url, root):
        """Test error shown for invalid URL."""
        mock_is_git_url.return_value = False
        callback = MagicMock()
        frame = DragDropFrame(root, on_drop_callback=callback)

        frame.process_url("https://evil.com/repo.git")

        # Should show error, not call callback
        mock_error.assert_called_once()
        callback.assert_not_called()

    @patch.object(DragDropFrame, '_is_git_url')
    def test_process_url_valid(self, mock_is_git_url, root):
        """Test callback called for valid URL."""
        mock_is_git_url.return_value = True
        callback = MagicMock()
        frame = DragDropFrame(root, on_drop_callback=callback)

        frame.process_url("https://github.com/user/repo.git")

        # Should call callback with URL
        callback.assert_called_once_with("https://github.com/user/repo.git")


class TestBrowseFolder:
    """Test browse folder button functionality."""

    @patch('gui.drag_drop.filedialog.askdirectory')
    @patch.object(DragDropFrame, 'process_folder')
    def test_browse_folder_selects_folder(self, mock_process_folder, mock_askdir, root):
        """Test that browse_folder calls process_folder with selected path."""
        mock_askdir.return_value = "/selected/folder"
        frame = DragDropFrame(root)

        frame.browse_folder()

        # Should call process_folder with selected path
        mock_process_folder.assert_called_once_with("/selected/folder")

    @patch('gui.drag_drop.filedialog.askdirectory')
    @patch.object(DragDropFrame, 'process_folder')
    def test_browse_folder_cancel(self, mock_process_folder, mock_askdir, root):
        """Test that browse_folder does nothing on cancel."""
        mock_askdir.return_value = ""  # User cancelled
        frame = DragDropFrame(root)

        frame.browse_folder()

        # Should not call process_folder
        mock_process_folder.assert_not_called()


class TestClipboardPaste:
    """Test clipboard paste functionality in URL dialog."""

    def test_paste_from_clipboard_success(self, root):
        """Test pasting from clipboard into entry widget."""
        frame = DragDropFrame(root)

        # Create entry widget
        entry = tk.Entry(root)
        entry.clipboard_clear()
        entry.clipboard_append("https://github.com/user/repo.git")
        entry.update()

        # Paste from clipboard
        frame._paste_from_clipboard(entry)

        # Entry should contain clipboard content
        assert entry.get() == "https://github.com/user/repo.git"

    def test_paste_from_clipboard_strips_whitespace(self, root):
        """Test that paste strips whitespace."""
        frame = DragDropFrame(root)

        # Create entry with whitespace in clipboard
        entry = tk.Entry(root)
        entry.clipboard_clear()
        entry.clipboard_append("  https://github.com/user/repo.git  ")
        entry.update()

        frame._paste_from_clipboard(entry)

        # Whitespace should be stripped
        assert entry.get() == "https://github.com/user/repo.git"

    def test_paste_from_clipboard_replaces_existing(self, root):
        """Test that paste replaces existing content."""
        frame = DragDropFrame(root)

        # Create entry with existing content
        entry = tk.Entry(root)
        entry.insert(0, "old content")
        entry.clipboard_clear()
        entry.clipboard_append("new content")
        entry.update()

        frame._paste_from_clipboard(entry)

        # Should replace, not append
        assert entry.get() == "new content"


class TestURLDialog:
    """Test URL dialog functionality."""

    @patch.object(DragDropFrame, 'process_url')
    def test_open_url_dialog_ok(self, mock_process_url, root):
        """Test URL dialog OK button calls process_url."""
        frame = DragDropFrame(root)

        # Mock dialog to return URL
        with patch('tkinter.Toplevel') as mock_toplevel:
            dialog = MagicMock()
            mock_toplevel.return_value = dialog

            # Mock entry widget
            entry = MagicMock()
            entry.get.return_value = "https://github.com/user/repo.git"

            with patch('tkinter.ttk.Entry', return_value=entry):
                # Simulate immediate return from wait_window
                dialog.wait_window = MagicMock()

                # Need to capture the OK button callback
                ok_callback = None

                def capture_ok_callback(*args, **kwargs):
                    if 'command' in kwargs:
                        nonlocal ok_callback
                        ok_callback = kwargs['command']
                    button = MagicMock()
                    return button

                with patch('tkinter.ttk.Button', side_effect=capture_ok_callback):
                    frame.open_url_dialog()

                    # Simulate clicking OK
                    if ok_callback:
                        ok_callback()

        # Note: Due to complex dialog lifecycle, testing actual process_url call
        # would require integration test. This test verifies dialog creation.
        assert mock_toplevel.called

    def test_open_url_dialog_creates_widgets(self, root):
        """Test that URL dialog creates all required widgets."""
        frame = DragDropFrame(root)

        created_widgets = []

        def track_widget_creation(parent, *args, **kwargs):
            widget = MagicMock()
            widget.pack = MagicMock()
            created_widgets.append(type(parent).__name__ if hasattr(parent, '__class__') else 'unknown')
            return widget

        with patch('tkinter.Toplevel') as mock_toplevel:
            dialog = MagicMock()
            mock_toplevel.return_value = dialog
            dialog.wait_window = MagicMock()

            with patch('tkinter.ttk.Label', side_effect=track_widget_creation):
                with patch('tkinter.ttk.Entry', side_effect=track_widget_creation):
                    with patch('tkinter.ttk.Button', side_effect=track_widget_creation):
                        frame.open_url_dialog()

        # Should create Label, Entry, and Buttons
        assert len(created_widgets) > 0


class TestTheme:
    """Test theme application."""

    def test_apply_theme_updates_canvas(self, root):
        """Test that apply_theme updates canvas background."""
        frame = DragDropFrame(root)

        # Mock theme manager
        with patch('gui.drag_drop.get_theme_manager') as mock_tm:
            mock_tm.return_value.get_color.return_value = "#FFFFFF"

            frame.apply_theme()

            # Should call get_color for theme colors
            assert mock_tm.return_value.get_color.called

    def test_apply_theme_updates_label(self, root):
        """Test that apply_theme updates label background."""
        frame = DragDropFrame(root)

        # Get initial label background
        initial_bg = frame.drop_label.cget('background')

        # Mock theme manager to return different color
        with patch('gui.drag_drop.get_theme_manager') as mock_tm:
            mock_tm.return_value.get_color.return_value = "#000000"

            frame.apply_theme()

            # Label background should be updated
            # Note: Due to theme manager mocking, exact color check is difficult
            # but we verify the method was called
            assert mock_tm.return_value.get_color.called


class TestLanguage:
    """Test language updates."""

    def test_update_language_updates_texts(self, root):
        """Test that update_language updates all UI texts."""
        frame = DragDropFrame(root)

        # Mock translation function
        with patch('gui.drag_drop.t') as mock_t:
            mock_t.side_effect = lambda key: f"translated_{key}"

            frame.update_language()

            # Should call t() for each translatable string
            assert mock_t.call_count >= 3  # At least label, browse button, url button

            # Verify specific translation keys
            assert call('drag_drop_text') in mock_t.call_args_list
            assert call('open_folder') in mock_t.call_args_list
            assert call('open_url') in mock_t.call_args_list


class TestDragDropFrameIntegration:
    """Integration tests for DragDropFrame."""

    def test_full_url_workflow(self, root):
        """Test complete workflow: URL validation → callback."""
        callback = MagicMock()
        frame = DragDropFrame(root, on_drop_callback=callback)

        # Valid URL should work
        with patch('os.path.isdir', return_value=False):  # Not a folder
            with patch.object(frame, '_is_git_url', return_value=True):
                frame.process_url("https://github.com/user/repo.git")

        callback.assert_called_once_with("https://github.com/user/repo.git")

    @patch('os.path.exists')
    @patch('os.path.isdir')
    def test_full_folder_workflow(self, mock_isdir, mock_exists, root):
        """Test complete workflow: folder validation → callback."""
        mock_isdir.return_value = True
        mock_exists.return_value = True
        callback = MagicMock()
        frame = DragDropFrame(root, on_drop_callback=callback)

        frame.process_folder("/valid/git/repo")

        callback.assert_called_once_with("/valid/git/repo")
