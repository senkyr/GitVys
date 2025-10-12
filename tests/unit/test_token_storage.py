"""
Tests for GitHub token storage.

SECURITY CRITICAL: These tests verify secure token persistence to ~/.gitvys/github_token.
"""

# MUST BE FIRST - initialize TCL/TK before any other imports
import tests.setup_tcl  # noqa: F401

import pytest
from unittest.mock import MagicMock, patch, mock_open
import os
import stat
from pathlib import Path

from auth.token_storage import TokenStorage


@pytest.fixture
def temp_token_storage(tmp_path):
    """Create TokenStorage with temporary directory."""
    with patch('auth.token_storage.Path.home', return_value=tmp_path):
        with patch('os.environ.get', return_value=str(tmp_path)):
            storage = TokenStorage()
            # Override paths to use tmp_path
            storage.config_dir = tmp_path / '.gitvys'
            storage.token_file = storage.config_dir / 'github_token'
            yield storage


class TestTokenStorageInitialization:
    """Tests for TokenStorage initialization."""

    @patch('os.name', 'nt')  # Windows
    @patch('os.environ.get', return_value='C:\\Users\\TestUser')
    def test_initialization_windows(self, mock_env_get):
        """Test initialization on Windows uses USERPROFILE."""
        storage = TokenStorage()

        # Verify Windows path
        assert 'USERPROFILE' in str(storage.config_dir) or 'TestUser' in str(storage.config_dir)
        assert storage.token_file.name == 'github_token'

    @patch('os.name', 'posix')  # Linux/Mac
    @patch('pathlib.Path.home', return_value=Path('/home/testuser'))
    def test_initialization_linux(self, mock_home):
        """Test initialization on Linux uses Path.home()."""
        storage = TokenStorage()

        # Verify Linux path
        assert '.gitvys' in str(storage.config_dir)
        assert storage.token_file.name == 'github_token'


class TestSaveToken:
    """Tests for save_token() method."""

    def test_save_token_success(self, temp_token_storage):
        """Test successful token save."""
        storage = temp_token_storage
        token = 'gho_test_token_123456789'

        # Save token
        result = storage.save_token(token)

        # Verify success
        assert result is True
        assert storage.token_file.exists()
        assert storage.token_file.read_text() == token

    def test_save_token_creates_directory(self, temp_token_storage):
        """Test that save_token creates config directory if missing."""
        storage = temp_token_storage

        # Ensure directory doesn't exist
        if storage.config_dir.exists():
            storage.config_dir.rmdir()

        # Save token
        token = 'gho_test_token_123456789'
        result = storage.save_token(token)

        # Verify directory was created
        assert result is True
        assert storage.config_dir.exists()
        assert storage.token_file.exists()

    def test_save_token_overwrites_existing(self, temp_token_storage):
        """Test that save_token overwrites existing token."""
        storage = temp_token_storage

        # Save first token
        storage.save_token('gho_old_token')

        # Save new token
        new_token = 'gho_new_token'
        result = storage.save_token(new_token)

        # Verify new token overwrote old
        assert result is True
        assert storage.token_file.read_text() == new_token

    @pytest.mark.skipif(os.name == 'nt', reason="File permissions not enforced on Windows")
    def test_save_token_sets_permissions_linux(self, temp_token_storage):
        """Test that save_token sets restrictive permissions (Linux only)."""
        storage = temp_token_storage
        token = 'gho_test_token_123456789'

        # Save token
        storage.save_token(token)

        # Verify permissions (600 = read/write owner only)
        file_stat = storage.token_file.stat()
        file_mode = stat.S_IMODE(file_stat.st_mode)
        expected_mode = stat.S_IRUSR | stat.S_IWUSR  # 0o600

        assert file_mode == expected_mode

    def test_save_token_permission_error_non_critical(self, temp_token_storage):
        """Test that permission errors are non-critical (Windows compatibility)."""
        storage = temp_token_storage
        token = 'gho_test_token_123456789'

        # Mock chmod to raise exception (simulates Windows)
        with patch('os.chmod', side_effect=OSError("Permission denied")):
            result = storage.save_token(token)

        # Should still succeed despite chmod failure
        assert result is True
        assert storage.token_file.exists()

    def test_save_token_write_error(self, temp_token_storage):
        """Test save_token with write error."""
        storage = temp_token_storage

        # Make config_dir a file (not directory) to cause write error
        storage.config_dir.parent.mkdir(parents=True, exist_ok=True)
        storage.config_dir.touch()  # Create as file, not directory

        # Try to save token (should fail)
        result = storage.save_token('gho_test_token')

        # Verify failure
        assert result is False

    def test_save_token_empty_string(self, temp_token_storage):
        """Test saving empty token string."""
        storage = temp_token_storage

        # Save empty token
        result = storage.save_token('')

        # Should succeed (validation is caller's responsibility)
        assert result is True
        assert storage.token_file.read_text() == ''


class TestLoadToken:
    """Tests for load_token() method."""

    def test_load_token_success(self, temp_token_storage):
        """Test successful token load."""
        storage = temp_token_storage
        token = 'gho_test_token_123456789'

        # Save token first
        storage.save_token(token)

        # Load token
        loaded_token = storage.load_token()

        # Verify loaded token
        assert loaded_token == token

    def test_load_token_strips_whitespace(self, temp_token_storage):
        """Test that load_token strips whitespace."""
        storage = temp_token_storage
        token = 'gho_test_token_123456789'

        # Save token with extra whitespace
        storage.config_dir.mkdir(parents=True, exist_ok=True)
        storage.token_file.write_text(f'  {token}\n\n  ', encoding='utf-8')

        # Load token
        loaded_token = storage.load_token()

        # Verify whitespace stripped
        assert loaded_token == token

    @pytest.mark.parametrize("scenario,setup_action,description", [
        ("file_not_exists", lambda s: (
            s.token_file.unlink() if s.token_file.exists() else None
        ), "file doesn't exist"),
        ("empty_file", lambda s: (
            s.config_dir.mkdir(parents=True, exist_ok=True),
            s.token_file.write_text('', encoding='utf-8')
        ), "empty file"),
        ("whitespace_only", lambda s: (
            s.config_dir.mkdir(parents=True, exist_ok=True),
            s.token_file.write_text('   \n\n  ', encoding='utf-8')
        ), "file with only whitespace"),
    ])
    def test_load_token_returns_none_scenarios(self, temp_token_storage, scenario, setup_action, description):
        """Test that load_token returns None for various failure scenarios.

        Verifies graceful handling when:
        - File doesn't exist
        - File is empty
        - File contains only whitespace
        """
        storage = temp_token_storage

        # Setup scenario
        setup_action(storage)

        # Load token
        loaded_token = storage.load_token()

        # Should return None
        assert loaded_token is None, f"Failed for: {description}"

    def test_load_token_read_error(self, temp_token_storage):
        """Test loading token with read permission error."""
        storage = temp_token_storage

        # Mock read_text to raise exception
        with patch.object(Path, 'read_text', side_effect=PermissionError("Access denied")):
            with patch.object(Path, 'exists', return_value=True):
                loaded_token = storage.load_token()

        # Should return None on error
        assert loaded_token is None


class TestDeleteToken:
    """Tests for delete_token() method."""

    def test_delete_token_success(self, temp_token_storage):
        """Test successful token deletion."""
        storage = temp_token_storage

        # Save token first
        storage.save_token('gho_test_token_123456789')
        assert storage.token_file.exists()

        # Delete token
        result = storage.delete_token()

        # Verify deletion
        assert result is True
        assert not storage.token_file.exists()

    def test_delete_token_file_not_exists(self, temp_token_storage):
        """Test deleting token when file doesn't exist."""
        storage = temp_token_storage

        # Ensure file doesn't exist
        if storage.token_file.exists():
            storage.token_file.unlink()

        # Delete token (should succeed even if file doesn't exist)
        result = storage.delete_token()

        # Should succeed
        assert result is True

    def test_delete_token_permission_error(self, temp_token_storage):
        """Test deleting token with permission error."""
        storage = temp_token_storage

        # Save token first
        storage.save_token('gho_test_token_123456789')

        # Mock unlink to raise exception
        with patch.object(Path, 'unlink', side_effect=PermissionError("Access denied")):
            with patch.object(Path, 'exists', return_value=True):
                result = storage.delete_token()

        # Should return False on error
        assert result is False


class TestTokenExists:
    """Tests for token_exists() method."""

    def test_token_exists_true(self, temp_token_storage):
        """Test token_exists returns True when token exists."""
        storage = temp_token_storage

        # Save token
        storage.save_token('gho_test_token_123456789')

        # Check existence
        assert storage.token_exists() is True

    @pytest.mark.parametrize("scenario,setup_action,description", [
        ("not_exists", lambda s: (
            s.token_file.unlink() if s.token_file.exists() else None
        ), "file doesn't exist"),
        ("empty_file", lambda s: (
            s.config_dir.mkdir(parents=True, exist_ok=True),
            s.token_file.write_text('', encoding='utf-8')
        ), "empty file exists"),
    ])
    def test_token_exists_returns_false(self, temp_token_storage, scenario, setup_action, description):
        """Test that token_exists returns False for invalid token scenarios.

        Token is considered non-existent when:
        - File doesn't exist
        - File exists but is empty
        """
        storage = temp_token_storage

        # Setup scenario
        setup_action(storage)

        # Check existence
        assert storage.token_exists() is False, f"Failed for: {description}"


class TestTokenStorageIntegration:
    """Integration tests for full token storage lifecycle."""

    def test_full_lifecycle_save_load_delete(self, temp_token_storage):
        """Test complete lifecycle: save → load → delete."""
        storage = temp_token_storage
        token = 'gho_test_token_123456789'

        # Initially no token
        assert storage.token_exists() is False
        assert storage.load_token() is None

        # Save token
        assert storage.save_token(token) is True
        assert storage.token_exists() is True

        # Load token
        loaded_token = storage.load_token()
        assert loaded_token == token

        # Delete token
        assert storage.delete_token() is True
        assert storage.token_exists() is False
        assert storage.load_token() is None

    def test_multiple_saves_and_loads(self, temp_token_storage):
        """Test multiple save/load cycles."""
        storage = temp_token_storage

        # Save and load token 1
        token1 = 'gho_token_1'
        storage.save_token(token1)
        assert storage.load_token() == token1

        # Overwrite with token 2
        token2 = 'gho_token_2'
        storage.save_token(token2)
        assert storage.load_token() == token2

        # Overwrite with token 3
        token3 = 'gho_token_3'
        storage.save_token(token3)
        assert storage.load_token() == token3
