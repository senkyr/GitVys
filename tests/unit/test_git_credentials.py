"""Unit tests for auth.git_credentials (URL whitelist, token handoff, redaction)."""

import base64
import threading
from unittest.mock import MagicMock, patch

import pytest

from auth.git_credentials import (
    build_git_auth_env, can_use_github_token, is_trusted_git_url,
    looks_like_url, redact_secrets,
)
from auth.github_auth import GitHubAuth


class TestTrustedUrls:

    @pytest.mark.parametrize("url", [
        "https://github.com/user/repo.git",
        "https://github.com/user/repo",
        "https://gitlab.com/group/sub/project",
        "https://git.sr.ht/~user/repo",
        "http://github.com/user/repo.git",
        "git@github.com:user/repo.git",
        "git@gitlab.com:group/project.git",
    ])
    def test_trusted(self, url):
        assert is_trusted_git_url(url)

    @pytest.mark.parametrize("url", [
        "https://evil.example.com/user/repo.git",
        "https://github.com.evil.example/user/repo.git",
        "https://evilgithub.com/user/repo.git",
        "https://user:pass@github.com/user/repo.git",   # údaje v URL
        "https://token@github.com/user/repo.git",
        "git@evil.example.com:user/repo.git",
        "ftp://github.com/user/repo.git",
        "file:///C:/repo",
        "",
    ])
    def test_untrusted(self, url):
        assert not is_trusted_git_url(url)

    def test_looks_like_url(self):
        assert looks_like_url("https://example.com/x")
        assert looks_like_url("git@host:x.git")
        assert not looks_like_url("C:\\Users\\student\\repo")
        assert not looks_like_url("/home/student/repo")


class TestTokenScope:

    def test_token_only_for_https_github(self):
        assert can_use_github_token("https://github.com/user/repo.git")
        assert not can_use_github_token("http://github.com/user/repo.git")    # plaintext HTTP
        assert not can_use_github_token("git@github.com:user/repo.git")       # SSH
        assert not can_use_github_token("https://gitlab.com/user/repo.git")   # cizí host
        assert not can_use_github_token("https://gist.github.com/abc.git")

    def test_auth_env_carries_token_only_in_header(self):
        env = build_git_auth_env("gho_secret")
        assert env['GIT_TERMINAL_PROMPT'] == '0'
        assert env['GIT_CONFIG_COUNT'] == '2'
        # Hlavička je omezená na github.com, ne na všechny hosty
        assert env['GIT_CONFIG_KEY_0'] == 'http.https://github.com/.extraHeader'
        encoded = env['GIT_CONFIG_VALUE_0'].split('Basic ', 1)[1]
        assert base64.b64decode(encoded).decode() == 'gho_secret:x-oauth-basic'
        # Credential helper vypnutý, aby Git neotevíral vlastní přihlášení
        assert env['GIT_CONFIG_KEY_1'] == 'credential.helper'
        assert env['GIT_CONFIG_VALUE_1'] == ''


class TestRedaction:

    def test_redacts_tokens_and_url_credentials(self):
        text = ("Cmd('git') failed: git clone https://gho_ABCDEFGHIJKLMNOPQRSTUVWXYZ012345@github.com/u/r "
                "https://user:hunter2@gitlab.com/u/r Authorization: Basic Zm9vOmJhcg==")
        redacted = redact_secrets(text)
        assert "gho_ABCDEFGHIJKLMNOPQRSTUVWXYZ012345" not in redacted
        assert "hunter2" not in redacted
        assert "Zm9vOmJhcg==" not in redacted
        assert "github.com/u/r" in redacted

    def test_plain_text_unchanged(self):
        assert redact_secrets("fatal: repository not found") == "fatal: repository not found"
        assert redact_secrets("") == ""


class TestPollCancellation:

    @patch('auth.github_auth.requests.post')
    def test_cancel_event_stops_polling_immediately(self, mock_post):
        pending = MagicMock(status_code=200)
        pending.json.return_value = {'error': 'authorization_pending'}
        mock_post.return_value = pending

        cancel = threading.Event()
        cancel.set()

        token, status = GitHubAuth().poll_for_token('code', interval=60, timeout=600, cancel_event=cancel)

        assert (token, status) == (None, 'cancelled')
        mock_post.assert_not_called()

    @patch('auth.github_auth.requests.post')
    def test_slow_down_increases_interval_permanently(self, mock_post):
        responses = [{'error': 'slow_down'}, {'error': 'authorization_pending'}, {'access_token': 'gho_x'}]
        mock_post.side_effect = [MagicMock(status_code=200, json=MagicMock(return_value=r)) for r in responses]

        waits = []

        class RecordingEvent:
            def is_set(self):
                return False

            def wait(self, seconds):
                waits.append(seconds)
                return False

        token, status = GitHubAuth().poll_for_token('code', interval=1, timeout=600,
                                                    cancel_event=RecordingEvent())

        assert (token, status) == ('gho_x', 'success')
        # RFC 8628: po slow_down platí zvýšený interval i pro další pokusy
        assert waits == [6, 6]
