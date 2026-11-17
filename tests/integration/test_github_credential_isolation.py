"""Klon z GitHubu nesmí použít přihlášení, které si pamatuje sám Git.

Na sdíleném účtu Windows by jinak soukromý repozitář předchozího uživatele šel
naklonovat i po odhlášení v aplikaci: první pokus o klon běžel s credential
helperem Gitu (Git Credential Manager) a ten aplikace nespravuje.

Testy pouštějí skutečný ``git`` produkční cestou ``RepositoryManager._clone``.
Nic přitom neopouští stroj: Git má jako HTTP proxy místní server na 127.0.0.1,
který na každý dotaz odpoví sám (401 bez přihlášení, jinak 404). ``HOME`` míří
do dočasné složky a systémová konfigurace Gitu je vypnutá, takže se nečte
skutečné nastavení ani uložené přihlašovací údaje; ty v testu jsou smyšlené.
"""

import base64
import http.server
import os
import re
import stat
import subprocess
import threading

import pytest
from git.exc import GitCommandError

from auth.git_credentials import build_git_clone_env
from gui.repo_manager import RepositoryManager

GITHUB_URL = "http://github.com/user/private.git"
OTHER_HOST_URL = "http://gitlab.com/user/private.git"

HELPER_CONFIG = '[credential]\n\thelper = "!f() { echo username=fakehelper; echo password=fakepass; }; f"\n'


def _basic(user, password):
    return "Basic " + base64.b64encode(f"{user}:{password}".encode()).decode()


def _git_version():
    try:
        out = subprocess.run(['git', '--version'], capture_output=True, text=True, timeout=10).stdout
    except (OSError, subprocess.SubprocessError):
        return (0, 0)
    match = re.search(r'(\d+)\.(\d+)', out)
    return (int(match.group(1)), int(match.group(2))) if match else (0, 0)


pytestmark = pytest.mark.skipif(_git_version() < (2, 31),
                                reason="GIT_CONFIG_COUNT potřebuje Git 2.31+")


@pytest.fixture
def local_proxy():
    """Místní server v roli HTTP proxy; pamatuje si hlavičku Authorization každého dotazu."""
    seen = []

    class Handler(http.server.BaseHTTPRequestHandler):
        def do_GET(self):
            authorization = self.headers.get('Authorization')
            seen.append(authorization)
            if authorization is None:
                self.send_response(401)
                self.send_header('WWW-Authenticate', 'Basic realm="test"')
            else:
                self.send_response(404)
            self.send_header('Content-Length', '0')
            self.end_headers()

        do_POST = do_GET

        def do_CONNECT(self):
            seen.append('CONNECT')
            self.send_response(403)
            self.send_header('Content-Length', '0')
            self.end_headers()

        def log_message(self, *args):
            pass

    server = http.server.ThreadingHTTPServer(('127.0.0.1', 0), Handler)
    thread = threading.Thread(target=server.serve_forever, daemon=True)
    thread.start()
    try:
        yield f"http://127.0.0.1:{server.server_address[1]}", seen
    finally:
        server.shutdown()
        server.server_close()
        thread.join(timeout=10)


@pytest.fixture
def git_home(tmp_path, monkeypatch, local_proxy):
    """Izolované nastavení Gitu: vlastní HOME, žádná systémová konfigurace, vše přes místní proxy."""
    proxy_url, _ = local_proxy
    home = tmp_path / "home"
    home.mkdir()
    for name in ('GIT_ASKPASS', 'SSH_ASKPASS', 'GIT_CONFIG_COUNT', 'GIT_CONFIG_GLOBAL',
                 'GIT_CONFIG_PARAMETERS', 'XDG_CONFIG_HOME'):
        monkeypatch.delenv(name, raising=False)
    monkeypatch.setenv('HOME', str(home))
    monkeypatch.setenv('GIT_CONFIG_NOSYSTEM', '1')
    for name in ('http_proxy', 'HTTP_PROXY', 'https_proxy', 'HTTPS_PROXY', 'all_proxy', 'ALL_PROXY'):
        monkeypatch.setenv(name, proxy_url)
    monkeypatch.setenv('no_proxy', '')
    monkeypatch.setenv('NO_PROXY', '')

    def write_config(extra=''):
        (home / '.gitconfig').write_text(f'[http]\n\tproxy = {proxy_url}\n{extra}', encoding='utf-8')

    write_config()
    return home, write_config


def _clone_and_expect_failure(url, tmp_path):
    with pytest.raises(GitCommandError) as error:
        RepositoryManager._clone(url, str(tmp_path / "clone"))
    return error.value


class TestGitHubCloneUsesOnlyApplicationLogin:

    def test_github_clone_ignores_git_credential_helper(self, tmp_path, local_proxy, git_home):
        """Přihlášení uložené v credential helperu Gitu se ke GitHubu nepošle."""
        _, seen = local_proxy
        _, write_config = git_home
        write_config(HELPER_CONFIG)

        error = _clone_and_expect_failure(GITHUB_URL, tmp_path)

        assert seen, "Git se na místní proxy vůbec nezeptal - test nic neověřil"
        assert seen == [None] * len(seen), "Git poslal ke GitHubu přihlášení, které nepochází z aplikace"
        # Aplikace chybu pozná jako chybějící přihlášení a otevře vlastní dialog
        assert RepositoryManager._is_auth_error(error)

    def test_other_hosts_still_use_git_credential_helper(self, tmp_path, local_proxy, git_home):
        """Mimo GitHub se nic nemění: tam aplikace přihlášení nenabízí, takže helper Gitu zůstává."""
        _, seen = local_proxy
        _, write_config = git_home
        write_config(HELPER_CONFIG)

        _clone_and_expect_failure(OTHER_HOST_URL, tmp_path)

        assert _basic('fakehelper', 'fakepass') in seen

    def test_github_clone_ignores_askpass_program(self, tmp_path, local_proxy, git_home):
        """Ani program askpass (core.askPass, GIT_ASKPASS) nesmí dodat přihlášení ke GitHubu."""
        _, seen = local_proxy
        home, write_config = git_home
        askpass = home / "askpass.sh"
        askpass.write_text("#!/bin/sh\necho fakeask\n", encoding='utf-8', newline='\n')
        askpass.chmod(askpass.stat().st_mode | stat.S_IEXEC)
        write_config(f'[core]\n\taskPass = {askpass.as_posix()}\n')

        _clone_and_expect_failure(GITHUB_URL, tmp_path)

        assert seen
        assert seen == [None] * len(seen)

    @pytest.mark.parametrize("url, expected_helpers", [
        ("https://github.com/user/private.git", ""),
        ("http://github.com/user/private.git", ""),
        ("https://gitlab.com/user/private.git", "fake-helper"),
    ])
    def test_helper_list_is_emptied_only_for_github(self, git_home, url, expected_helpers):
        """Skutečný git: prostředí klonu vyprázdní seznam helperů pro GitHub (https i http), jinde ne."""
        _, write_config = git_home
        write_config('[credential]\n\thelper = fake-helper\n')
        env = dict(os.environ)
        env.update(build_git_clone_env(url))

        result = subprocess.run(['git', 'config', '--get-urlmatch', 'credential.helper', url],
                                env=env, capture_output=True, text=True, timeout=30)

        assert result.stdout.strip() == expected_helpers
