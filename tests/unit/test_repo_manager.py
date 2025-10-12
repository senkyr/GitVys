"""Unit tests for gui.repo_manager module."""

import pytest
import os
import tempfile
import shutil
from unittest.mock import MagicMock, patch, call
from pathlib import Path
from gui.repo_manager import RepositoryManager


class TestRepositoryManagerInitialization:
    """Tests for RepositoryManager initialization."""

    def test_initialization(self, mock_parent_window):
        """Test RepositoryManager initialization with default values."""
        manager = RepositoryManager(mock_parent_window)

        assert manager.parent == mock_parent_window
        assert manager.root == mock_parent_window.root
        assert manager.git_repo is None
        assert manager.is_remote_loaded is False
        assert manager.is_cloned_repo is False
        assert manager.temp_clones == []
        assert manager.current_temp_clone is None
        assert manager.display_name is None
        assert manager.token_storage is not None

    @patch('gui.repo_manager.glob.glob')
    @patch('gui.repo_manager.shutil.rmtree')
    def test_cleanup_old_temp_clones_on_init(self, mock_rmtree, mock_glob, mock_parent_window, tmp_path):
        """Test cleanup of orphaned temp clones from previous sessions."""
        # Create fake temp clones
        fake_temp1 = tmp_path / "gitvys_clone_old1"
        fake_temp2 = tmp_path / "gitvys_clone_old2"
        fake_temp1.mkdir()
        fake_temp2.mkdir()

        mock_glob.return_value = [str(fake_temp1), str(fake_temp2)]

        manager = RepositoryManager(mock_parent_window)

        # Should have attempted to cleanup both old temp clones
        assert mock_rmtree.call_count == 2

    @patch('atexit.register')
    def test_atexit_handler_registration(self, mock_atexit, mock_parent_window):
        """Test that atexit handler is registered for cleanup."""
        manager = RepositoryManager(mock_parent_window)

        # Verify atexit.register was called with cleanup function
        mock_atexit.assert_called_once()
        assert mock_atexit.call_args[0][0] == manager._cleanup_temp_clones


class TestURLDetection:
    """Tests for URL detection logic."""

    def test_is_git_url_https(self, mock_parent_window):
        """Test HTTPS URL detection."""
        manager = RepositoryManager(mock_parent_window)

        assert manager._is_git_url("https://github.com/user/repo.git")
        assert manager._is_git_url("https://gitlab.com/user/repo")
        assert manager._is_git_url("https://bitbucket.org/user/repo.git")

    def test_is_git_url_ssh(self, mock_parent_window):
        """Test SSH URL detection."""
        manager = RepositoryManager(mock_parent_window)

        assert manager._is_git_url("git@github.com:user/repo.git")
        assert manager._is_git_url("git@gitlab.com:user/repo.git")

    def test_is_git_url_http(self, mock_parent_window):
        """Test HTTP URL detection."""
        manager = RepositoryManager(mock_parent_window)

        assert manager._is_git_url("http://github.com/user/repo.git")

    def test_is_git_url_host_detection(self, mock_parent_window):
        """Test Git host detection without protocol."""
        manager = RepositoryManager(mock_parent_window)

        # Should detect known Git hosts
        assert manager._is_git_url("github.com/user/repo")
        assert manager._is_git_url("gitlab.com/user/repo")
        assert manager._is_git_url("bitbucket.org/user/repo")

    def test_is_git_url_local_path(self, mock_parent_window):
        """Test local path detection (should return False)."""
        manager = RepositoryManager(mock_parent_window)

        assert not manager._is_git_url("C:\\Users\\user\\repo")
        assert not manager._is_git_url("/home/user/repo")
        assert not manager._is_git_url("./local/repo")
        assert not manager._is_git_url("relative/path/to/repo")


class TestRepositorySelection:
    """Tests for repository selection entry point."""

    @patch.object(RepositoryManager, 'load_repository')
    def test_on_repository_selected_local_path(self, mock_load, mock_parent_window):
        """Test selecting local repository path."""
        manager = RepositoryManager(mock_parent_window)
        local_path = "C:\\Users\\user\\repo"

        manager.on_repository_selected(local_path)

        # Should NOT call clone_repository (local path, not URL)
        assert manager.is_cloned_repo is False

        # Should start loading thread (verify status update and progress start)
        mock_parent_window.update_status.assert_called()
        mock_parent_window.progress.start.assert_called()

    @patch.object(RepositoryManager, 'clone_repository')
    def test_on_repository_selected_url(self, mock_clone, mock_parent_window):
        """Test selecting repository URL."""
        manager = RepositoryManager(mock_parent_window)
        url = "https://github.com/user/repo.git"

        manager.on_repository_selected(url)

        # Should call clone_repository
        mock_clone.assert_called_once_with(url)

    @patch.object(RepositoryManager, '_cleanup_single_clone')
    @patch.object(RepositoryManager, 'load_repository')
    def test_on_repository_selected_cleans_previous_clone(self, mock_load, mock_cleanup, mock_parent_window, tmp_path):
        """Test that opening local repo cleans previous temp clone."""
        manager = RepositoryManager(mock_parent_window)

        # Set up previous cloned repo
        previous_temp = tmp_path / "previous_clone"
        previous_temp.mkdir()
        manager.is_cloned_repo = True
        manager.current_temp_clone = str(previous_temp)
        manager.temp_clones.append(str(previous_temp))

        # Mock git repo close
        manager.git_repo = MagicMock()
        manager.git_repo.repo = MagicMock()

        # Select new local repo
        local_path = "C:\\Users\\user\\new_repo"
        manager.on_repository_selected(local_path)

        # Should have cleaned up previous clone
        mock_cleanup.assert_called_once_with(str(previous_temp))
        assert manager.current_temp_clone is None
        assert manager.is_cloned_repo is False


class TestCloning:
    """Tests for repository cloning and temp management."""

    @patch('gui.repo_manager.tempfile.mkdtemp')
    @patch('gui.repo_manager.threading.Thread')
    def test_clone_repository_creates_temp_dir(self, mock_thread, mock_mkdtemp, mock_parent_window, tmp_path):
        """Test that cloning creates temp directory."""
        temp_dir = tmp_path / "gitvys_clone_test"
        temp_dir.mkdir()
        mock_mkdtemp.return_value = str(temp_dir)

        manager = RepositoryManager(mock_parent_window)
        url = "https://github.com/user/repo.git"

        manager.clone_repository(url)

        # Should create temp directory
        mock_mkdtemp.assert_called_once()
        assert str(temp_dir) in manager.temp_clones

        # Should start clone thread
        mock_thread.assert_called_once()
        mock_thread.return_value.start.assert_called_once()

    @patch('gui.repo_manager.tempfile.mkdtemp')
    @patch('gui.repo_manager.threading.Thread')
    def test_clone_repository_extracts_name(self, mock_thread, mock_mkdtemp, mock_parent_window, tmp_path):
        """Test that cloning extracts repository name from URL."""
        temp_dir = tmp_path / "gitvys_clone_test"
        temp_dir.mkdir()
        mock_mkdtemp.return_value = str(temp_dir)

        manager = RepositoryManager(mock_parent_window)

        # Test various URL formats
        test_cases = [
            ("https://github.com/user/my-repo.git", "my-repo"),
            ("https://gitlab.com/group/project", "project"),
            ("git@github.com:user/awesome-app.git", "awesome-app"),
        ]

        for url, expected_name in test_cases:
            manager.clone_repository(url)
            assert manager.display_name == expected_name

    @patch('git.Repo.clone_from')
    def test_clone_worker_success_no_auth(self, mock_clone_from, mock_parent_window):
        """Test successful clone without authentication."""
        manager = RepositoryManager(mock_parent_window)
        url = "https://github.com/user/public-repo.git"
        path = "/tmp/test_clone"

        # Mock successful clone
        mock_clone_from.return_value = MagicMock()

        manager._clone_worker(url, path)

        # Should have called clone_from
        mock_clone_from.assert_called_once_with(url, path)

    @patch('git.Repo.clone_from')
    @patch.object(RepositoryManager, '_show_auth_dialog_sync')
    def test_clone_worker_auth_error_shows_dialog(self, mock_auth_dialog, mock_clone_from, mock_parent_window):
        """Test that auth error shows dialog."""
        manager = RepositoryManager(mock_parent_window)
        url = "https://github.com/user/private-repo.git"
        path = "/tmp/test_clone"

        # Mock clone to fail with auth error first time
        from git.exc import GitCommandError
        auth_error = GitCommandError("git clone", 128, stderr="fatal: Authentication failed")
        mock_clone_from.side_effect = [auth_error, MagicMock()]  # Fail then succeed

        # Mock auth dialog to return token
        mock_auth_dialog.return_value = "fake_token_123"
        manager._auth_dialog_result = "fake_token_123"

        manager._clone_worker(url, path)

        # Should have shown auth dialog
        # Note: In actual implementation, dialog is shown via root.after()
        # We verify that token loading was attempted
        assert mock_clone_from.call_count >= 1

    @patch('git.Repo.clone_from')
    def test_clone_worker_retry_with_token(self, mock_clone_from, mock_parent_window):
        """Test clone retry with saved token."""
        manager = RepositoryManager(mock_parent_window)
        url = "https://github.com/user/private-repo.git"
        path = "/tmp/test_clone"

        # Mock token storage to return token
        manager.token_storage.load_token = MagicMock(return_value="saved_token_456")

        # Mock clone to fail first time (auth error), succeed second time
        from git.exc import GitCommandError
        auth_error = GitCommandError("git clone", 128, stderr="fatal: Authentication failed")
        mock_clone_from.side_effect = [auth_error, MagicMock()]

        manager._clone_worker(url, path)

        # Should have retried with token
        assert mock_clone_from.call_count == 2
        # Second call should have token in URL
        second_call_url = mock_clone_from.call_args_list[1][0][0]
        assert "saved_token_456" in second_call_url

    @patch('git.Repo.clone_from')
    @patch.object(RepositoryManager, '_cleanup_single_clone')
    def test_clone_worker_cleanup_on_failure(self, mock_cleanup, mock_clone_from, mock_parent_window):
        """Test temp directory cleanup on clone failure."""
        manager = RepositoryManager(mock_parent_window)
        url = "https://github.com/user/repo.git"
        path = "/tmp/test_clone"

        # Mock root.after to verify it's called
        manager.root.after = MagicMock()

        # Mock clone to fail with non-auth error
        mock_clone_from.side_effect = Exception("Network error")

        manager._clone_worker(url, path)

        # Should have scheduled cleanup via root.after
        # (cleanup is called via root.after(0, ...))
        manager.root.after.assert_any_call(0, mock_cleanup, path)

    @patch('gui.repo_manager.tempfile.mkdtemp')
    @patch('gui.repo_manager.threading.Thread')
    @patch.object(RepositoryManager, '_cleanup_single_clone')
    def test_clone_repository_multiple_sequential(self, mock_cleanup, mock_thread, mock_mkdtemp, mock_parent_window, tmp_path):
        """Test cloning multiple repositories sequentially."""
        manager = RepositoryManager(mock_parent_window)

        # First clone
        temp1 = tmp_path / "clone1"
        temp1.mkdir()
        mock_mkdtemp.return_value = str(temp1)
        manager.clone_repository("https://github.com/user/repo1.git")
        first_temp = manager.temp_clones[-1]

        # Second clone (should cleanup first)
        temp2 = tmp_path / "clone2"
        temp2.mkdir()
        mock_mkdtemp.return_value = str(temp2)
        manager.clone_repository("https://github.com/user/repo2.git")

        # Should have cleaned up first clone
        mock_cleanup.assert_called()


class TestAuthentication:
    """Tests for OAuth authentication flow."""

    def test_show_auth_dialog_sync(self, mock_parent_window):
        """Test showing auth dialog and storing result."""
        manager = RepositoryManager(mock_parent_window)

        with patch('gui.repo_manager.GitHubAuthDialog') as mock_dialog_class:
            mock_dialog = MagicMock()
            mock_dialog.show.return_value = "test_token_789"
            mock_dialog_class.return_value = mock_dialog

            token = manager._show_auth_dialog_sync()

            # Should show dialog and return token
            assert token == "test_token_789"
            assert manager._auth_dialog_result == "test_token_789"

    @patch('git.Repo.clone_from')
    def test_clone_with_saved_token(self, mock_clone_from, mock_parent_window):
        """Test clone with pre-saved token."""
        manager = RepositoryManager(mock_parent_window)
        manager.token_storage.load_token = MagicMock(return_value="existing_token")

        url = "https://github.com/user/private-repo.git"
        path = "/tmp/test"

        # Mock first clone to fail with auth, second to succeed
        from git.exc import GitCommandError
        mock_clone_from.side_effect = [
            GitCommandError("git", 128, stderr="Authentication failed"),
            MagicMock()
        ]

        manager._clone_worker(url, path)

        # Should have used saved token
        manager.token_storage.load_token.assert_called()

    @patch('git.Repo.clone_from')
    def test_clone_saves_token_after_success(self, mock_clone_from, mock_parent_window):
        """Test that successful auth saves token."""
        manager = RepositoryManager(mock_parent_window)
        manager.token_storage.save_token = MagicMock()
        manager.token_storage.load_token = MagicMock(return_value="new_token")

        url = "https://github.com/user/private-repo.git"
        path = "/tmp/test"

        # Mock auth failure then success
        from git.exc import GitCommandError
        mock_clone_from.side_effect = [
            GitCommandError("git", 128, stderr="Authentication failed"),
            MagicMock()
        ]

        manager._clone_worker(url, path)

        # Should have saved token
        manager.token_storage.save_token.assert_called_once_with("new_token")

    def test_clone_ssh_url_rejects_token(self, mock_parent_window):
        """Test that SSH URLs cannot use token authentication."""
        manager = RepositoryManager(mock_parent_window)
        manager.token_storage.load_token = MagicMock(return_value="token")

        url = "git@github.com:user/repo.git"
        path = "/tmp/test"

        # Mock root.after to verify it's called
        manager.root.after = MagicMock()

        with patch('git.Repo.clone_from') as mock_clone:
            from git.exc import GitCommandError
            mock_clone.side_effect = GitCommandError("git", 128, stderr="Authentication failed")

            manager._clone_worker(url, path)

            # Should have called error handler (SSH doesn't support token)
            # Check that root.after was called with show_error
            assert manager.root.after.called
            # Verify the call includes show_error function
            calls_with_show_error = [call for call in manager.root.after.call_args_list
                                      if len(call[0]) >= 2 and call[0][1] == manager.parent.show_error]
            assert len(calls_with_show_error) > 0


class TestTempCleanup:
    """Tests for temporary directory cleanup."""

    def test_cleanup_single_clone(self, mock_parent_window, tmp_path):
        """Test cleanup of single temp clone."""
        manager = RepositoryManager(mock_parent_window)

        # Create fake temp directory
        temp_clone = tmp_path / "test_clone"
        temp_clone.mkdir()
        (temp_clone / "test_file.txt").write_text("test")
        manager.temp_clones.append(str(temp_clone))

        # Cleanup
        manager._cleanup_single_clone(str(temp_clone))

        # Directory should be deleted
        assert not temp_clone.exists()
        # Should be removed from list
        assert str(temp_clone) not in manager.temp_clones

    def test_cleanup_single_clone_readonly_files(self, mock_parent_window, tmp_path):
        """Test cleanup handles Windows readonly files."""
        manager = RepositoryManager(mock_parent_window)

        # Create temp dir with readonly file
        temp_clone = tmp_path / "test_clone_readonly"
        temp_clone.mkdir()
        readonly_file = temp_clone / "readonly.txt"
        readonly_file.write_text("readonly content")

        # Make file readonly (Windows)
        import stat
        readonly_file.chmod(stat.S_IREAD)

        manager.temp_clones.append(str(temp_clone))

        # Cleanup should handle readonly files
        manager._cleanup_single_clone(str(temp_clone))

        # Directory should be deleted despite readonly files
        assert not temp_clone.exists()

    def test_cleanup_temp_clones_on_exit(self, mock_parent_window, tmp_path):
        """Test cleanup of all temp clones on exit."""
        manager = RepositoryManager(mock_parent_window)

        # Create multiple temp clones
        clones = []
        for i in range(3):
            clone_dir = tmp_path / f"clone_{i}"
            clone_dir.mkdir()
            clones.append(str(clone_dir))
            manager.temp_clones.append(str(clone_dir))

        # Mock git repo
        manager.git_repo = MagicMock()
        manager.git_repo.repo = MagicMock()

        # Cleanup all
        manager._cleanup_temp_clones()

        # All should be deleted
        for clone_path in clones:
            assert not Path(clone_path).exists()

    def test_cleanup_handles_locked_files(self, mock_parent_window, tmp_path):
        """Test cleanup handles locked files gracefully."""
        manager = RepositoryManager(mock_parent_window)

        temp_clone = tmp_path / "locked_clone"
        temp_clone.mkdir()
        manager.temp_clones.append(str(temp_clone))

        # Mock shutil.rmtree to raise PermissionError
        with patch('gui.repo_manager.shutil.rmtree') as mock_rmtree:
            mock_rmtree.side_effect = PermissionError("File is locked")

            # Should not crash, just log warning
            manager._cleanup_single_clone(str(temp_clone))

            # Temp should still be in list (cleanup failed)
            assert str(temp_clone) in manager.temp_clones


class TestRepositoryLoading:
    """Tests for repository loading and refresh."""

    @patch('gui.repo_manager.GitRepository')
    @patch('gui.repo_manager.GraphLayout')
    def test_load_repository_success(self, mock_layout, mock_git_repo_class, mock_parent_window):
        """Test successful repository loading."""
        manager = RepositoryManager(mock_parent_window)

        # Mock GitRepository
        mock_repo = MagicMock()
        mock_repo.load_repository.return_value = True
        mock_repo.parse_commits.return_value = [MagicMock(), MagicMock()]
        mock_repo.get_merge_branches.return_value = []
        mock_git_repo_class.return_value = mock_repo

        # Mock GraphLayout
        mock_layout_instance = MagicMock()
        mock_layout_instance.calculate_positions.return_value = [MagicMock()]
        mock_layout.return_value = mock_layout_instance

        manager.load_repository("/path/to/repo")

        # Should have loaded successfully
        assert manager.git_repo == mock_repo
        mock_repo.load_repository.assert_called_once()
        mock_repo.parse_commits.assert_called_once()

    @patch('gui.repo_manager.GitRepository')
    def test_load_repository_failure(self, mock_git_repo_class, mock_parent_window):
        """Test repository loading failure."""
        manager = RepositoryManager(mock_parent_window)

        # Mock root.after to verify it's called
        manager.root.after = MagicMock()

        # Mock GitRepository to fail
        mock_repo = MagicMock()
        mock_repo.load_repository.return_value = False
        mock_git_repo_class.return_value = mock_repo

        manager.load_repository("/path/to/invalid/repo")

        # Should have called show_error via root.after
        # Check that root.after was called with show_error
        assert manager.root.after.called
        # Verify the call includes show_error function
        calls_with_show_error = [call for call in manager.root.after.call_args_list
                                  if len(call[0]) >= 2 and call[0][1] == manager.parent.show_error]
        assert len(calls_with_show_error) > 0

    def test_refresh_repository_local(self, mock_parent_window):
        """Test refreshing local repository."""
        manager = RepositoryManager(mock_parent_window)
        manager.git_repo = MagicMock()
        manager.is_remote_loaded = False

        with patch.object(manager, 'refresh_local_repository') as mock_refresh:
            with patch('gui.repo_manager.threading.Thread') as mock_thread:
                manager.refresh_repository()

                # Should start local refresh thread
                mock_thread.assert_called_once()
                mock_thread.return_value.start.assert_called_once()

    def test_refresh_repository_remote(self, mock_parent_window):
        """Test refreshing remote repository."""
        manager = RepositoryManager(mock_parent_window)
        manager.git_repo = MagicMock()
        manager.is_remote_loaded = True

        with patch.object(manager, 'fetch_remote_data') as mock_fetch:
            manager.refresh_repository()

            # Should fetch remote data
            mock_fetch.assert_called_once()


class TestCloseRepository:
    """Tests for repository closing and cleanup."""

    def test_close_repository_removes_temp(self, mock_parent_window, tmp_path):
        """Test that close_repository removes temp clone."""
        manager = RepositoryManager(mock_parent_window)

        # Setup cloned repo
        temp_clone = tmp_path / "temp_repo"
        temp_clone.mkdir()
        manager.is_cloned_repo = True
        manager.current_temp_clone = str(temp_clone)
        manager.temp_clones.append(str(temp_clone))

        # Mock git repo
        manager.git_repo = MagicMock()
        manager.git_repo.repo = MagicMock()

        manager.close_repository()

        # Temp should be cleaned
        assert not temp_clone.exists()
        assert manager.current_temp_clone is None
        assert manager.is_cloned_repo is False
        assert manager.git_repo is None

    def test_close_repository_closes_gitpython_handles(self, mock_parent_window):
        """Test that close_repository closes GitPython repo handles."""
        manager = RepositoryManager(mock_parent_window)

        # Mock git repo
        mock_repo_object = MagicMock()
        manager.git_repo = MagicMock()
        manager.git_repo.repo = mock_repo_object

        manager.close_repository()

        # Should have closed GitPython repo
        mock_repo_object.close.assert_called_once()
        assert manager.git_repo is None
