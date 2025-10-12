"""
Tests for GitHub OAuth Device Flow authentication.

SECURITY CRITICAL: These tests verify OAuth authentication flow for private repositories.
"""

# MUST BE FIRST - initialize TCL/TK before any other imports
import tests.setup_tcl  # noqa: F401

import pytest
from unittest.mock import MagicMock, patch, call
import requests

from auth.github_auth import GitHubAuth, GITHUB_CLIENT_ID


class TestGitHubAuthInitialization:
    """Tests for GitHubAuth initialization."""

    def test_initialization_sets_client_id(self):
        """Test that initialization sets client ID."""
        auth = GitHubAuth()
        assert auth.client_id == GITHUB_CLIENT_ID


class TestRequestDeviceCode:
    """Tests for request_device_code() method."""

    @patch('auth.github_auth.requests.post')
    def test_request_device_code_success(self, mock_post):
        """Test successful device code request."""
        # Mock successful response
        mock_response = MagicMock()
        mock_response.status_code = 200
        mock_response.json.return_value = {
            'device_code': 'test_device_code_123',
            'user_code': 'ABCD-1234',
            'verification_uri': 'https://github.com/login/device',
            'expires_in': 900,
            'interval': 5
        }
        mock_post.return_value = mock_response

        auth = GitHubAuth()
        result = auth.request_device_code()

        # Verify result
        assert result is not None
        assert result['device_code'] == 'test_device_code_123'
        assert result['user_code'] == 'ABCD-1234'
        assert result['verification_uri'] == 'https://github.com/login/device'
        assert result['interval'] == 5

        # Verify API call
        mock_post.assert_called_once()
        call_args = mock_post.call_args
        assert call_args[0][0] == 'https://github.com/login/device/code'
        assert call_args[1]['data']['client_id'] == GITHUB_CLIENT_ID
        assert call_args[1]['data']['scope'] == 'repo'

    @pytest.mark.parametrize("error_type,mock_setup,description", [
        ("http_error", lambda m: (
            setattr(m.return_value, 'status_code', 403),
        ), "HTTP 403 error"),
        ("missing_fields", lambda m: (
            setattr(m.return_value, 'status_code', 200),
            m.return_value.json.return_value.__setitem__('device_code', 'test_device_code_123'),
        ), "Missing required fields (user_code, verification_uri, interval)"),
        ("network_error", lambda m: setattr(m, 'side_effect', requests.RequestException("Network error")), "Network connection error"),
        ("json_error", lambda m: (
            setattr(m.return_value, 'status_code', 200),
            setattr(m.return_value.json, 'side_effect', ValueError("Invalid JSON")),
        ), "JSON parsing error"),
        ("timeout", lambda m: setattr(m, 'side_effect', requests.Timeout("Request timed out")), "Request timeout"),
    ])
    @patch('auth.github_auth.requests.post')
    def test_request_device_code_errors(self, mock_post, error_type, mock_setup, description):
        """Test device code request error handling (SECURITY CRITICAL).

        Verifies that all error conditions return None gracefully:
        - HTTP errors (4xx, 5xx)
        - Missing required fields
        - Network errors
        - JSON parsing errors
        - Timeouts
        """
        # Setup mock according to error type
        if error_type == "missing_fields":
            mock_post.return_value = MagicMock()
            mock_post.return_value.status_code = 200
            mock_post.return_value.json.return_value = {'device_code': 'test_device_code_123'}
        elif error_type == "http_error":
            mock_post.return_value = MagicMock()
            mock_post.return_value.status_code = 403
        elif error_type == "json_error":
            mock_post.return_value = MagicMock()
            mock_post.return_value.status_code = 200
            mock_post.return_value.json.side_effect = ValueError("Invalid JSON")
        elif error_type == "network_error":
            mock_post.side_effect = requests.RequestException("Network error")
        elif error_type == "timeout":
            mock_post.side_effect = requests.Timeout("Request timed out")

        auth = GitHubAuth()
        result = auth.request_device_code()

        # All error conditions should return None
        assert result is None, f"Failed for: {description}"


class TestPollForToken:
    """Tests for poll_for_token() method."""

    @patch('auth.github_auth.requests.post')
    @patch('auth.github_auth.time.sleep')
    def test_poll_for_token_success(self, mock_sleep, mock_post):
        """Test successful token polling."""
        # Mock successful response
        mock_response = MagicMock()
        mock_response.status_code = 200
        mock_response.json.return_value = {
            'access_token': 'gho_test_token_123',
            'token_type': 'bearer',
            'scope': 'repo'
        }
        mock_post.return_value = mock_response

        auth = GitHubAuth()
        token, status = auth.poll_for_token('test_device_code', interval=1, timeout=10)

        # Verify result
        assert token == 'gho_test_token_123'
        assert status == 'success'

    @patch('auth.github_auth.requests.post')
    @patch('auth.github_auth.time.sleep')
    @patch('auth.github_auth.time.time')
    def test_poll_for_token_authorization_pending_then_success(self, mock_time, mock_sleep, mock_post):
        """Test polling with authorization_pending followed by success."""
        # Mock time to avoid actual timeout
        mock_time.side_effect = [0, 1, 2, 3]  # Start time, then increments

        # Mock responses: first authorization_pending, then success
        pending_response = MagicMock()
        pending_response.status_code = 200
        pending_response.json.return_value = {'error': 'authorization_pending'}

        success_response = MagicMock()
        success_response.status_code = 200
        success_response.json.return_value = {'access_token': 'gho_test_token_123'}

        mock_post.side_effect = [pending_response, success_response]

        auth = GitHubAuth()
        token, status = auth.poll_for_token('test_device_code', interval=1, timeout=10)

        # Verify result
        assert token == 'gho_test_token_123'
        assert status == 'success'
        assert mock_post.call_count == 2

    @patch('auth.github_auth.requests.post')
    @patch('auth.github_auth.time.sleep')
    @patch('auth.github_auth.time.time')
    def test_poll_for_token_slow_down(self, mock_time, mock_sleep, mock_post):
        """Test polling with slow_down error."""
        # Mock time
        mock_time.side_effect = [0, 1, 2, 3]

        # Mock responses: slow_down, then success
        slow_down_response = MagicMock()
        slow_down_response.status_code = 200
        slow_down_response.json.return_value = {'error': 'slow_down'}

        success_response = MagicMock()
        success_response.status_code = 200
        success_response.json.return_value = {'access_token': 'gho_test_token_123'}

        mock_post.side_effect = [slow_down_response, success_response]

        auth = GitHubAuth()
        token, status = auth.poll_for_token('test_device_code', interval=1, timeout=10)

        # Verify result
        assert token == 'gho_test_token_123'
        assert status == 'success'
        # Verify slow_down caused longer sleep (interval + 5)
        mock_sleep.assert_any_call(6)  # 1 + 5

    @patch('auth.github_auth.requests.post')
    @patch('auth.github_auth.time.sleep')
    def test_poll_for_token_expired_token(self, mock_sleep, mock_post):
        """Test polling with expired_token error."""
        # Mock expired_token response
        mock_response = MagicMock()
        mock_response.status_code = 200
        mock_response.json.return_value = {'error': 'expired_token'}
        mock_post.return_value = mock_response

        auth = GitHubAuth()
        token, status = auth.poll_for_token('test_device_code', interval=1, timeout=10)

        # Verify result
        assert token is None
        assert status == 'timeout'

    @patch('auth.github_auth.requests.post')
    @patch('auth.github_auth.time.sleep')
    def test_poll_for_token_access_denied(self, mock_sleep, mock_post):
        """Test polling with access_denied error (user cancelled)."""
        # Mock access_denied response
        mock_response = MagicMock()
        mock_response.status_code = 200
        mock_response.json.return_value = {'error': 'access_denied'}
        mock_post.return_value = mock_response

        auth = GitHubAuth()
        token, status = auth.poll_for_token('test_device_code', interval=1, timeout=10)

        # Verify result
        assert token is None
        assert status == 'cancelled'

    @patch('auth.github_auth.requests.post')
    @patch('auth.github_auth.time.sleep')
    def test_poll_for_token_unknown_error(self, mock_sleep, mock_post):
        """Test polling with unknown error."""
        # Mock unknown error response
        mock_response = MagicMock()
        mock_response.status_code = 200
        mock_response.json.return_value = {'error': 'unknown_error'}
        mock_post.return_value = mock_response

        auth = GitHubAuth()
        token, status = auth.poll_for_token('test_device_code', interval=1, timeout=10)

        # Verify result
        assert token is None
        assert status == 'error'

    @patch('auth.github_auth.requests.post')
    @patch('auth.github_auth.time.sleep')
    @patch('auth.github_auth.time.time')
    def test_poll_for_token_timeout(self, mock_time, mock_sleep, mock_post):
        """Test polling timeout."""
        # Mock time to simulate timeout (logger also calls time.time())
        mock_time.side_effect = [0, 11, 11, 11]  # Start, then past timeout (10s), extra calls for logger

        # Mock authorization_pending response (never succeeds)
        mock_response = MagicMock()
        mock_response.status_code = 200
        mock_response.json.return_value = {'error': 'authorization_pending'}
        mock_post.return_value = mock_response

        auth = GitHubAuth()
        token, status = auth.poll_for_token('test_device_code', interval=1, timeout=10)

        # Verify timeout
        assert token is None
        assert status == 'timeout'

    @patch('auth.github_auth.requests.post')
    @patch('auth.github_auth.time.sleep')
    @patch('auth.github_auth.time.time')
    def test_poll_for_token_http_error_retries(self, mock_time, mock_sleep, mock_post):
        """Test polling retries on HTTP errors."""
        # Mock time
        mock_time.side_effect = [0, 1, 2, 3]

        # Mock responses: HTTP error, then success
        error_response = MagicMock()
        error_response.status_code = 500

        success_response = MagicMock()
        success_response.status_code = 200
        success_response.json.return_value = {'access_token': 'gho_test_token_123'}

        mock_post.side_effect = [error_response, success_response]

        auth = GitHubAuth()
        token, status = auth.poll_for_token('test_device_code', interval=1, timeout=10)

        # Verify result
        assert token == 'gho_test_token_123'
        assert status == 'success'
        assert mock_post.call_count == 2

    @patch('auth.github_auth.requests.post')
    @patch('auth.github_auth.time.sleep')
    @patch('auth.github_auth.time.time')
    def test_poll_for_token_network_error_retries(self, mock_time, mock_sleep, mock_post):
        """Test polling retries on network errors."""
        # Mock time
        mock_time.side_effect = [0, 1, 2, 3]

        # Mock responses: network error, then success
        success_response = MagicMock()
        success_response.status_code = 200
        success_response.json.return_value = {'access_token': 'gho_test_token_123'}

        mock_post.side_effect = [
            requests.RequestException("Network error"),
            success_response
        ]

        auth = GitHubAuth()
        token, status = auth.poll_for_token('test_device_code', interval=1, timeout=10)

        # Verify result
        assert token == 'gho_test_token_123'
        assert status == 'success'
        assert mock_post.call_count == 2

    @patch('auth.github_auth.requests.post')
    @patch('auth.github_auth.time.sleep')
    def test_poll_for_token_unexpected_exception(self, mock_sleep, mock_post):
        """Test polling with unexpected exception."""
        # Mock unexpected exception
        mock_post.side_effect = Exception("Unexpected error")

        auth = GitHubAuth()
        token, status = auth.poll_for_token('test_device_code', interval=1, timeout=10)

        # Verify error handling
        assert token is None
        assert status == 'error'


class TestVerifyToken:
    """Tests for verify_token() method."""

    @patch('auth.github_auth.requests.get')
    def test_verify_token_success(self, mock_get):
        """Test successful token verification."""
        # Mock successful response
        mock_response = MagicMock()
        mock_response.status_code = 200
        mock_response.json.return_value = {
            'login': 'testuser',
            'id': 12345,
            'name': 'Test User'
        }
        mock_get.return_value = mock_response

        auth = GitHubAuth()
        username = auth.verify_token('gho_test_token_123')

        # Verify result
        assert username == 'testuser'

        # Verify API call
        mock_get.assert_called_once()
        call_args = mock_get.call_args
        assert call_args[0][0] == 'https://api.github.com/user'
        assert call_args[1]['headers']['Authorization'] == 'token gho_test_token_123'

    @pytest.mark.parametrize("error_type,description", [
        ("http_error", "HTTP 401 unauthorized (invalid token)"),
        ("missing_username", "Missing 'login' field in response"),
        ("network_error", "Network connection error"),
        ("json_error", "JSON parsing error"),
        ("timeout", "Request timeout"),
    ])
    @patch('auth.github_auth.requests.get')
    def test_verify_token_errors(self, mock_get, error_type, description):
        """Test token verification error handling (SECURITY CRITICAL).

        Verifies that all error conditions return None gracefully:
        - HTTP errors (401 unauthorized)
        - Missing username in response
        - Network errors
        - JSON parsing errors
        - Timeouts
        """
        # Setup mock according to error type
        if error_type == "http_error":
            mock_get.return_value = MagicMock()
            mock_get.return_value.status_code = 401
        elif error_type == "missing_username":
            mock_get.return_value = MagicMock()
            mock_get.return_value.status_code = 200
            mock_get.return_value.json.return_value = {'id': 12345}  # Missing 'login'
        elif error_type == "json_error":
            mock_get.return_value = MagicMock()
            mock_get.return_value.status_code = 200
            mock_get.return_value.json.side_effect = ValueError("Invalid JSON")
        elif error_type == "network_error":
            mock_get.side_effect = requests.RequestException("Network error")
        elif error_type == "timeout":
            mock_get.side_effect = requests.Timeout("Request timed out")

        auth = GitHubAuth()
        username = auth.verify_token('gho_test_token_123')

        # All error conditions should return None
        assert username is None, f"Failed for: {description}"


class TestGitHubAuthIntegration:
    """Integration tests for full OAuth flow."""

    @patch('auth.github_auth.requests.post')
    @patch('auth.github_auth.requests.get')
    @patch('auth.github_auth.time.sleep')
    @patch('auth.github_auth.time.time')
    def test_full_oauth_flow_success(self, mock_time, mock_sleep, mock_get, mock_post):
        """Test complete OAuth flow: device code → poll → verify."""
        # Mock time
        mock_time.side_effect = [0, 1, 2]

        # Mock device code response
        device_code_response = MagicMock()
        device_code_response.status_code = 200
        device_code_response.json.return_value = {
            'device_code': 'test_device_code_123',
            'user_code': 'ABCD-1234',
            'verification_uri': 'https://github.com/login/device',
            'interval': 1
        }

        # Mock token response (immediate success)
        token_response = MagicMock()
        token_response.status_code = 200
        token_response.json.return_value = {'access_token': 'gho_test_token_123'}

        mock_post.side_effect = [device_code_response, token_response]

        # Mock verify response
        verify_response = MagicMock()
        verify_response.status_code = 200
        verify_response.json.return_value = {'login': 'testuser'}
        mock_get.return_value = verify_response

        # Execute full flow
        auth = GitHubAuth()

        # Step 1: Request device code
        device_data = auth.request_device_code()
        assert device_data is not None
        assert device_data['user_code'] == 'ABCD-1234'

        # Step 2: Poll for token
        token, status = auth.poll_for_token(device_data['device_code'], interval=1, timeout=10)
        assert token == 'gho_test_token_123'
        assert status == 'success'

        # Step 3: Verify token
        username = auth.verify_token(token)
        assert username == 'testuser'
