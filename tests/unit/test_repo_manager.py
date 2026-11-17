"""Unit tests for gui.repo_manager module."""

# MUST BE FIRST - initialize TCL/TK before any other imports
import tests.setup_tcl  # noqa: F401

import pytest
import os
import tempfile
import shutil
from unittest.mock import MagicMock, patch, call
from pathlib import Path
from gui.repo_manager import RepositoryManager


@pytest.fixture(autouse=True)
def isolated_temp_dir(tmp_path, monkeypatch):
    """Dočasné klony testů do tmp_path, ne do systémového temp."""
    systemp = tmp_path / "systemp"
    systemp.mkdir()
    monkeypatch.setattr(tempfile, 'tempdir', str(systemp))
    return systemp


def run_posted_immediately(manager):
    """root.after(0, cb, *args) -> cb(*args) hned (simulace hlavni smycky)."""
    manager.root.after = MagicMock(side_effect=lambda delay, cb, *args: cb(*args))


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

    def test_cleanup_old_temp_clones_on_init(self, mock_parent_window, isolated_temp_dir):
        """Při startu se smažou jen osiřelé složky, ne klony jiné běžící instance."""
        from gui.temp_clones import TempCloneArea, LOCK_NAME

        # Běžící instance (drží zámek) se svým klonem
        other_instance = TempCloneArea(str(isolated_temp_dir))
        other_clone = other_instance.new_clone_dir()

        # Spadlá instance: zámek existuje, ale nikdo ho nedrží
        crashed = isolated_temp_dir / "gitvys_instance_crashed"
        (crashed / "clone_x").mkdir(parents=True)
        (crashed / LOCK_NAME).write_text("99999")

        # Klony staré verze: starý se smaže, čerstvý (možná běžící stará verze) zůstane
        old_legacy = isolated_temp_dir / "gitvys_clone_old"
        old_legacy.mkdir()
        os.utime(old_legacy, (0, 0))
        fresh_legacy = isolated_temp_dir / "gitvys_clone_fresh"
        fresh_legacy.mkdir()

        try:
            manager = RepositoryManager(mock_parent_window)

            assert not crashed.exists()
            assert not old_legacy.exists()
            assert fresh_legacy.exists()
            assert os.path.isdir(other_clone)
            assert manager.temp_area.instance_dir.exists()
        finally:
            other_instance.close()

    def test_exit_cleanup_removes_own_instance_dir(self, mock_parent_window):
        manager = RepositoryManager(mock_parent_window)
        clone_dir = manager.temp_area.new_clone_dir()
        manager.temp_clones.append(clone_dir)

        manager._cleanup_temp_clones()

        assert not manager.temp_area.instance_dir.exists()

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

    def test_is_git_url_without_scheme_is_path(self, mock_parent_window):
        """Text bez schematu je lokalni cesta (i kdyz obsahuje jmeno hostu)."""
        manager = RepositoryManager(mock_parent_window)

        assert not manager._is_git_url("github.com/user/repo")
        assert not manager._is_git_url("C:\\projects\\github.com-mirror")

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
    def test_on_repository_selected_local_path(self, mock_load, mock_parent_window, tmp_path):
        """Test selecting local repository path."""
        manager = RepositoryManager(mock_parent_window)
        local_path = str(tmp_path)

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

    @patch.object(RepositoryManager, 'clone_repository')
    def test_on_repository_selected_rejects_untrusted_url(self, mock_clone, mock_parent_window):
        """URL mimo whitelist se neklonuje (drop na graf obchazi DragDropFrame)."""
        manager = RepositoryManager(mock_parent_window)

        for url in ["https://evil.example.com/user/repo.git",
                    "https://github.com.evil.example/user/repo.git",
                    "https://user:secret@github.com/user/repo.git"]:
            manager.on_repository_selected(url)

        mock_clone.assert_not_called()
        assert mock_parent_window.show_error.call_count == 3

    @patch.object(RepositoryManager, 'load_repository')
    def test_on_repository_selected_rejects_missing_folder(self, mock_load, mock_parent_window, tmp_path):
        """Neexistujici cesta skonci chybou, nespusti nacitani."""
        manager = RepositoryManager(mock_parent_window)

        manager.on_repository_selected(str(tmp_path / "does-not-exist"))

        mock_parent_window.show_error.assert_called_once()
        mock_parent_window.progress.start.assert_not_called()

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
        local_path = tmp_path / "new_repo"
        local_path.mkdir()
        manager.on_repository_selected(str(local_path))

        # Should have cleaned up previous clone
        mock_cleanup.assert_called_once_with(str(previous_temp))
        assert manager.current_temp_clone is None
        assert manager.is_cloned_repo is False


class TestCloning:
    """Tests for repository cloning and temp management."""

    @patch('gui.repo_manager.threading.Thread')
    def test_clone_repository_creates_temp_dir(self, mock_thread, mock_parent_window):
        """Test that cloning creates temp directory inside this instance's area."""
        manager = RepositoryManager(mock_parent_window)
        url = "https://github.com/user/repo.git"

        manager.clone_repository(url)

        # Should create temp directory in the instance folder
        assert len(manager.temp_clones) == 1
        clone_dir = Path(manager.temp_clones[0])
        assert clone_dir.is_dir()
        assert clone_dir.parent == manager.temp_area.instance_dir

        # Should start clone thread
        mock_thread.assert_called_once()
        mock_thread.return_value.start.assert_called_once()

    @patch('gui.repo_manager.threading.Thread')
    def test_clone_repository_extracts_name(self, mock_thread, mock_parent_window):
        """Test that cloning extracts repository name from URL."""
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

        # Should have called clone_from without credentials
        mock_clone_from.assert_called_once()
        assert mock_clone_from.call_args[0] == (url, path)
        assert mock_clone_from.call_args[1]['env'] == {'GIT_TERMINAL_PROMPT': '0'}

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
        manager.token_storage.load_token = MagicMock(return_value=None)
        manager.token_storage.save_token = MagicMock()
        run_posted_immediately(manager)

        manager._clone_worker(url, path)

        # Dialog shown (in main thread via root.after), clone retried, token saved
        mock_auth_dialog.assert_called_once()
        assert mock_clone_from.call_count == 2
        manager.token_storage.save_token.assert_called_once_with("fake_token_123")

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
        second_call = mock_clone_from.call_args_list[1]
        # Token nesmi byt v URL (skoncil by v .git/config a v chybovych hlaskach)
        assert second_call[0][0] == url
        # ...ale predava se Gitu hlavickou pres promenne prostredi
        import base64
        env = second_call[1]['env']
        encoded = env['GIT_CONFIG_VALUE_0'].split("Basic ", 1)[1]
        assert base64.b64decode(encoded).decode().startswith("saved_token_456:")
        assert env['GIT_CONFIG_KEY_0'] == 'http.https://github.com/.extraHeader'

    @patch('git.Repo.clone_from')
    @patch.object(RepositoryManager, '_show_auth_dialog_sync')
    def test_clone_worker_invalid_saved_token_is_replaced(self, mock_auth_dialog, mock_clone_from, mock_parent_window):
        """Odvolany ulozeny token se smaze a uzivatel dostane OAuth dialog."""
        manager = RepositoryManager(mock_parent_window)
        manager.token_storage.load_token = MagicMock(return_value="revoked_token")
        manager.token_storage.delete_token = MagicMock()
        manager.token_storage.save_token = MagicMock()
        mock_auth_dialog.return_value = "fresh_token"
        run_posted_immediately(manager)

        from git.exc import GitCommandError
        auth_error = GitCommandError("git clone", 128, stderr="fatal: Authentication failed")
        mock_clone_from.side_effect = [auth_error, auth_error, MagicMock()]

        manager._clone_worker("https://github.com/user/private.git", "/tmp/test_clone")

        manager.token_storage.delete_token.assert_called_once()
        mock_auth_dialog.assert_called_once()
        manager.token_storage.save_token.assert_called_once_with("fresh_token")
        mock_parent_window.show_error.assert_not_called()

    @patch('git.Repo.clone_from')
    def test_clone_worker_never_sends_token_to_other_hosts(self, mock_clone_from, mock_parent_window):
        """Pri chybe autentizace na jinem hostu nez github.com se token nepouzije."""
        manager = RepositoryManager(mock_parent_window)
        manager.token_storage.load_token = MagicMock(return_value="github_token")
        run_posted_immediately(manager)

        from git.exc import GitCommandError
        mock_clone_from.side_effect = GitCommandError("git clone", 128, stderr="fatal: Authentication failed")

        manager._clone_worker("https://gitlab.com/user/private.git", "/tmp/test_clone")

        assert mock_clone_from.call_count == 1
        manager.token_storage.load_token.assert_not_called()
        mock_parent_window.show_error.assert_called_once()

    @patch('git.Repo.clone_from')
    def test_clone_error_message_is_redacted(self, mock_clone_from, mock_parent_window):
        """Chybova hlaska nesmi obsahovat token ani udaje z URL."""
        manager = RepositoryManager(mock_parent_window)
        run_posted_immediately(manager)
        mock_clone_from.side_effect = Exception(
            "Cmd('git') failed: git clone https://gho_abcdefghijklmnopqrstuvwxyz0123@github.com/u/r.git")

        manager._clone_worker("https://github.com/u/r.git", "/tmp/test_clone")

        message = mock_parent_window.show_error.call_args[0][0]
        assert "gho_abcdefghijklmnopqrstuvwxyz0123" not in message

    def test_stale_result_is_dropped(self, mock_parent_window):
        """Vysledek operace, kterou predbehla novejsi, se nezobrazi."""
        manager = RepositoryManager(mock_parent_window)
        run_posted_immediately(manager)
        stale = manager._next_generation()
        manager._next_generation()  # uzivatel mezitim otevrel jiny repozitar

        callback = MagicMock()
        manager._post(stale, callback, "old result")
        callback.assert_not_called()

        manager._post(manager._generation, callback, "new result")
        callback.assert_called_once_with("new result")

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

    @patch('gui.repo_manager.threading.Thread')
    @patch.object(RepositoryManager, '_cleanup_single_clone')
    def test_clone_repository_multiple_sequential(self, mock_cleanup, mock_thread, mock_parent_window):
        """Test cloning multiple repositories sequentially."""
        manager = RepositoryManager(mock_parent_window)

        manager.clone_repository("https://github.com/user/repo1.git")
        first_temp = manager.temp_clones[-1]

        # Second clone (should cleanup first)
        manager.clone_repository("https://github.com/user/repo2.git")

        # Should have cleaned up first clone
        mock_cleanup.assert_any_call(first_temp)


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
        """Test that successful auth with a NEW token saves it."""
        manager = RepositoryManager(mock_parent_window)
        manager.token_storage.save_token = MagicMock()
        manager.token_storage.load_token = MagicMock(return_value=None)
        manager._show_auth_dialog_sync = MagicMock(return_value="new_token")
        run_posted_immediately(manager)

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

        run_posted_immediately(manager)

        with patch('git.Repo.clone_from') as mock_clone:
            from git.exc import GitCommandError
            mock_clone.side_effect = GitCommandError("git", 128, stderr="Authentication failed")

            manager._clone_worker(url, path)

            # SSH doesn't support token -> error shown, token never loaded
            assert mock_clone.call_count == 1
            manager.token_storage.load_token.assert_not_called()
            manager.parent.show_error.assert_called_once()


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
        with patch('gui.temp_clones.shutil.rmtree') as mock_rmtree:
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

        run_posted_immediately(manager)
        manager.load_repository("/path/to/repo")

        # Should have loaded successfully (git_repo is set in the main thread callback)
        assert manager.git_repo == mock_repo
        mock_parent_window.show_graph.assert_called_once()
        mock_repo.load_repository.assert_called_once()
        mock_repo.parse_commits.assert_called_once()

    @patch('gui.repo_manager.GitRepository')
    def test_load_repository_failure(self, mock_git_repo_class, mock_parent_window):
        """Test repository loading failure."""
        manager = RepositoryManager(mock_parent_window)

        run_posted_immediately(manager)

        # Mock GitRepository to fail
        mock_repo = MagicMock()
        mock_repo.load_repository.return_value = False
        mock_git_repo_class.return_value = mock_repo

        manager.load_repository("/path/to/invalid/repo")

        # Should have shown error in the main thread, repo not taken over
        mock_parent_window.show_error.assert_called_once()
        assert manager.git_repo is None

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


@pytest.fixture
def fake_token_storage(tmp_path):
    """TokenStorage nad docasnou slozkou - testy nesmi sahnout na uloziste v profilu."""
    from auth.token_storage import TokenStorage

    storage = TokenStorage()
    storage.config_dir = tmp_path / '.gitvys'
    storage.token_file = storage.config_dir / 'github_token'
    return storage


class TestLogout:
    """Odhlaseni z GitHubu: token nesmi zustat ulozeny ani se vratit z rozpracovaneho klonu."""

    AUTH_ERROR_STDERR = "fatal: Authentication failed"

    @staticmethod
    def _token_sent_to_git(clone_call):
        import base64
        encoded = clone_call[1]['env']['GIT_CONFIG_VALUE_0'].split("Basic ", 1)[1]
        return base64.b64decode(encoded).decode().split(":", 1)[0]

    @patch('git.Repo.clone_from')
    @patch.object(RepositoryManager, '_show_auth_dialog_sync')
    def test_logout_deletes_token_and_next_clone_asks_for_login(
            self, mock_auth_dialog, mock_clone_from, mock_parent_window, fake_token_storage):
        """Po odhlaseni neni token na disku a soukromy klon si vyzada nove prihlaseni."""
        from git.exc import GitCommandError

        manager = RepositoryManager(mock_parent_window)
        manager.token_storage = fake_token_storage
        fake_token_storage.save_token("fake_token_previous_user")
        run_posted_immediately(manager)

        assert manager.logout() is True

        assert not fake_token_storage.token_file.exists()
        assert fake_token_storage.load_token() is None

        # Dalsi klon soukromeho repa: misto stareho tokenu prihlasovaci dialog
        mock_auth_dialog.return_value = "fake_token_next_user"
        mock_clone_from.side_effect = [
            GitCommandError("git clone", 128, stderr=self.AUTH_ERROR_STDERR), MagicMock()]

        manager._clone_worker("https://github.com/user/private.git", "/tmp/test_clone")

        mock_auth_dialog.assert_called_once()
        assert self._token_sent_to_git(mock_clone_from.call_args_list[1]) == "fake_token_next_user"

    @patch('git.Repo.clone_from')
    @patch.object(RepositoryManager, '_on_clone_complete')
    @patch.object(RepositoryManager, '_show_auth_dialog_sync')
    def test_logout_during_clone_does_not_save_new_token(
            self, mock_auth_dialog, mock_complete, mock_clone_from, mock_parent_window, fake_token_storage):
        """Odhlaseni behem klonu s cerstve ziskanym tokenem: token se neulozi, klon se zahodi."""
        from git.exc import GitCommandError

        manager = RepositoryManager(mock_parent_window)
        manager.token_storage = fake_token_storage
        mock_auth_dialog.return_value = "fake_token_fresh"
        run_posted_immediately(manager)

        logout_results = []

        def clone(url, path, env=None):
            if 'GIT_CONFIG_VALUE_0' not in env:
                raise GitCommandError("git clone", 128, stderr=self.AUTH_ERROR_STDERR)
            # uzivatel klikne na Odhlasit, zatimco git klonuje
            logout_results.append(manager.logout())

        mock_clone_from.side_effect = clone

        manager._clone_worker("https://github.com/user/private.git", "/tmp/test_clone")

        assert logout_results == [True]
        assert not fake_token_storage.token_file.exists()
        mock_complete.assert_not_called()
        mock_parent_window.show_error.assert_called_once()

    @patch('git.Repo.clone_from')
    @patch.object(RepositoryManager, '_on_clone_complete')
    def test_logout_during_clone_with_saved_token_discards_clone(
            self, mock_complete, mock_clone_from, mock_parent_window, fake_token_storage):
        """Odhlaseni behem klonu s ulozenym tokenem: klon se nezobrazi a token zustane smazany."""
        from git.exc import GitCommandError

        manager = RepositoryManager(mock_parent_window)
        manager.token_storage = fake_token_storage
        fake_token_storage.save_token("fake_token_saved")
        run_posted_immediately(manager)

        logout_results = []

        def clone(url, path, env=None):
            if 'GIT_CONFIG_VALUE_0' not in env:
                raise GitCommandError("git clone", 128, stderr=self.AUTH_ERROR_STDERR)
            logout_results.append(manager.logout())

        mock_clone_from.side_effect = clone

        manager._clone_worker("https://github.com/user/private.git", "/tmp/test_clone")

        assert logout_results == [True]
        assert not fake_token_storage.token_file.exists()
        mock_complete.assert_not_called()
        mock_parent_window.show_error.assert_called_once()

    @patch('git.Repo.clone_from')
    @patch.object(RepositoryManager, '_on_clone_complete')
    def test_logout_does_not_cancel_clone_without_token(
            self, mock_complete, mock_clone_from, mock_parent_window, fake_token_storage):
        """Klon verejneho repa token nepouziva, odhlaseni behem nej ho nezrusi."""
        manager = RepositoryManager(mock_parent_window)
        manager.token_storage = fake_token_storage
        run_posted_immediately(manager)
        mock_clone_from.side_effect = lambda url, path, env=None: manager.logout()

        manager._clone_worker("https://github.com/user/public.git", "/tmp/test_clone")

        mock_complete.assert_called_once_with("/tmp/test_clone")
        mock_parent_window.show_error.assert_not_called()

    def test_logout_reports_failure_when_token_cannot_be_deleted(self, mock_parent_window, fake_token_storage):
        """Kdyz token nejde smazat, odhlaseni se nesmi tvarit jako uspesne."""
        manager = RepositoryManager(mock_parent_window)
        manager.token_storage = fake_token_storage
        fake_token_storage.delete_token = MagicMock(return_value=False)

        assert manager.logout() is False
