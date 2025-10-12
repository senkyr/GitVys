"""
Tests for logging_config.py.

Tests OS-specific path handling, logger setup, and error handling.
"""

# MUST BE FIRST - initialize TCL/TK before any other imports
import tests.setup_tcl  # noqa: F401

import pytest
from unittest.mock import MagicMock, patch, mock_open
import os
import logging
import sys
from pathlib import Path

from utils.logging_config import get_log_file_path, setup_logging, get_logger


class TestGetLogFilePath:
    """Tests for get_log_file_path() function."""

    @patch('os.name', 'nt')  # Windows
    @patch('os.environ.get', return_value='C:\\Users\\TestUser')
    @patch('pathlib.Path.mkdir')
    def test_get_log_file_path_windows(self, mock_mkdir, mock_env_get):
        """Test log file path on Windows uses USERPROFILE."""
        # Act
        log_path = get_log_file_path()

        # Assert
        assert '.gitvys' in str(log_path)
        assert 'gitvisualizer.log' in str(log_path)
        assert 'TestUser' in str(log_path) or 'Users' in str(log_path)
        # Verify USERPROFILE was accessed
        mock_env_get.assert_called_with('USERPROFILE', '~')
        # Verify directory creation was attempted
        mock_mkdir.assert_called_once_with(parents=True, exist_ok=True)

    @patch('os.name', 'posix')  # Linux/Mac
    @patch('pathlib.Path.home', return_value=Path('/home/testuser'))
    @patch('pathlib.Path.mkdir')
    def test_get_log_file_path_linux(self, mock_mkdir, mock_home):
        """Test log file path on Linux uses Path.home()."""
        # Act
        log_path = get_log_file_path()

        # Assert
        assert '.gitvys' in str(log_path)
        assert 'gitvisualizer.log' in str(log_path)
        assert 'testuser' in str(log_path)

    @patch('pathlib.Path.mkdir')
    def test_get_log_file_path_creates_directory(self, mock_mkdir):
        """Test that get_log_file_path creates ~/.gitvys/ directory."""
        # Act
        log_path = get_log_file_path()

        # Assert
        mock_mkdir.assert_called_once_with(parents=True, exist_ok=True)

    @patch('pathlib.Path.mkdir')
    def test_get_log_file_path_fallback_on_mkdir_error(self, mock_mkdir):
        """Test fallback to current directory when mkdir fails."""
        # Arrange
        mock_mkdir.side_effect = PermissionError("Cannot create directory")

        # Act
        log_path = get_log_file_path()

        # Assert
        assert log_path == Path('gitvisualizer.log')  # Fallback to current dir


class TestSetupLogging:
    """Tests for setup_logging() function."""

    def teardown_method(self):
        """Clean up logger handlers after each test."""
        logger = logging.getLogger('gitvisualizer')
        logger.handlers.clear()

    @patch('utils.logging_config.get_log_file_path')
    @patch('logging.FileHandler')
    def test_setup_logging_creates_file_handler(self, mock_file_handler, mock_get_path):
        """Test that setup_logging creates a FileHandler."""
        # Arrange
        mock_get_path.return_value = Path('/tmp/test.log')
        mock_handler = MagicMock()
        mock_file_handler.return_value = mock_handler

        # Act
        logger = setup_logging()

        # Assert
        mock_file_handler.assert_called_once()
        assert mock_handler in logger.handlers

    @patch('utils.logging_config.get_log_file_path')
    @patch('logging.StreamHandler')
    def test_setup_logging_creates_console_handler(self, mock_stream_handler, mock_get_path):
        """Test that setup_logging creates a StreamHandler for stderr."""
        # Arrange
        mock_get_path.return_value = Path('/tmp/test.log')
        mock_handler = MagicMock()
        mock_stream_handler.return_value = mock_handler

        # Act
        logger = setup_logging()

        # Assert
        mock_stream_handler.assert_called_once_with(sys.stderr)
        assert mock_handler in logger.handlers

    @patch('logging.FileHandler')
    def test_setup_logging_custom_log_file(self, mock_file_handler):
        """Test setup_logging with custom log_file argument."""
        # Arrange
        custom_path = '/custom/path/test.log'
        mock_handler = MagicMock()
        mock_file_handler.return_value = mock_handler

        # Act
        logger = setup_logging(log_file=custom_path)

        # Assert
        # Verify custom path was used (compare Path objects for OS-agnostic comparison)
        call_args = mock_file_handler.call_args
        actual_path = Path(call_args[0][0])
        expected_path = Path(custom_path)
        assert actual_path == expected_path

    @patch('utils.logging_config.get_log_file_path')
    def test_setup_logging_prevents_duplicate_handlers(self, mock_get_path):
        """Test that setup_logging doesn't add handlers twice."""
        # Arrange
        mock_get_path.return_value = Path('/tmp/test.log')

        # Act
        logger1 = setup_logging()
        handler_count_1 = len(logger1.handlers)

        logger2 = setup_logging()  # Call again
        handler_count_2 = len(logger2.handlers)

        # Assert
        assert logger1 is logger2  # Same logger instance
        assert handler_count_1 == handler_count_2  # No duplicate handlers

    @patch('utils.logging_config.get_log_file_path')
    @patch('logging.FileHandler')
    @patch('builtins.print')
    def test_setup_logging_file_handler_failure_non_critical(self, mock_print, mock_file_handler, mock_get_path):
        """Test that FileHandler creation failure is non-critical."""
        # Arrange
        mock_get_path.return_value = Path('/tmp/test.log')
        mock_file_handler.side_effect = PermissionError("Cannot write to file")

        # Act
        logger = setup_logging()

        # Assert
        # Should print warning to stderr but not crash
        mock_print.assert_called_once()
        assert "Warning" in str(mock_print.call_args)
        assert "Nelze vytvořit log soubor" in str(mock_print.call_args)

        # Should still have console handler
        assert len(logger.handlers) > 0

    @patch('utils.logging_config.get_log_file_path')
    def test_setup_logging_sets_log_level(self, mock_get_path):
        """Test that setup_logging sets the correct log level."""
        # Arrange
        mock_get_path.return_value = Path('/tmp/test.log')

        # Act
        logger = setup_logging(level=logging.DEBUG)

        # Assert
        assert logger.level == logging.DEBUG

    @patch('utils.logging_config.get_log_file_path')
    def test_setup_logging_console_handler_error_only(self, mock_get_path):
        """Test that console handler is set to ERROR level."""
        # Arrange
        mock_get_path.return_value = Path('/tmp/test.log')

        # Act
        logger = setup_logging()

        # Assert
        # Find console handler (StreamHandler)
        console_handlers = [h for h in logger.handlers if isinstance(h, logging.StreamHandler)]
        assert len(console_handlers) > 0
        # Console handler should be ERROR level (not same as logger level)
        assert console_handlers[0].level == logging.ERROR


class TestGetLogger:
    """Tests for get_logger() function."""

    def test_get_logger_returns_logger(self):
        """Test that get_logger returns a logger instance."""
        # Act
        logger = get_logger('test_module')

        # Assert
        assert isinstance(logger, logging.Logger)
        assert logger.name == 'gitvisualizer.test_module'

    def test_get_logger_different_names(self):
        """Test that get_logger creates different loggers for different names."""
        # Act
        logger1 = get_logger('module1')
        logger2 = get_logger('module2')

        # Assert
        assert logger1.name != logger2.name
        assert logger1.name == 'gitvisualizer.module1'
        assert logger2.name == 'gitvisualizer.module2'

    def test_get_logger_same_name_returns_same_logger(self):
        """Test that get_logger returns the same logger for the same name."""
        # Act
        logger1 = get_logger('test_module')
        logger2 = get_logger('test_module')

        # Assert
        assert logger1 is logger2  # Same instance
