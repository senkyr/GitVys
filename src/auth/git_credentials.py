"""
Bezpečné předání GitHub tokenu Gitu a čištění citlivých údajů z textů.

Proč ne ``https://TOKEN@github.com/...``: token v URL skončí v příkazové řádce
procesu, v ``.git/config`` klonu (``remote.origin.url``) i v textu výjimky
``GitCommandError``, který se ukazuje uživateli v chybovém dialogu. Místo toho
se token předá hlavičkou ``http.extraHeader`` přes proměnné prostředí
``GIT_CONFIG_COUNT/KEY/VALUE`` (Git 2.31+): neobjeví se v argv ani na disku.
"""

import base64
import re
from typing import Dict
from urllib.parse import urlparse

# Hosty, pro které smí aplikace klonovat (HTTPS i SSH, včetně subdomén).
TRUSTED_GIT_HOSTS = frozenset({
    'github.com', 'gitlab.com', 'bitbucket.org',
    'gitea.io', 'codeberg.org', 'sr.ht',
})

# Token z GitHub OAuth se smí posílat jen sem - nikdy na jiný host.
GITHUB_TOKEN_HOSTS = frozenset({'github.com'})

# Adresy, pro které Git nesmí použít vlastní uložené přihlášení (credential helper).
# I http://: taková adresa je povolená a GitHub ji přesměruje na https.
GITHUB_CREDENTIAL_URLS = ('https://github.com', 'http://github.com')

_SSH_URL = re.compile(r'^git@([\w.-]+):([\w.\-/]+?)(\.git)?/?$', re.IGNORECASE)


def _host_is_trusted(host: str) -> bool:
    host = (host or '').lower().rstrip('.')
    return any(host == trusted or host.endswith('.' + trusted) for trusted in TRUSTED_GIT_HOSTS)


def parse_git_url_host(text: str):
    """Vrátí (schéma, host) pro HTTP(S) URL nebo SSH ve tvaru git@host:cesta, jinak (None, None)."""
    text = (text or '').strip()
    ssh = _SSH_URL.match(text)
    if ssh:
        return 'ssh', ssh.group(1).lower()
    try:
        parsed = urlparse(text)
    except ValueError:
        return None, None
    if parsed.scheme in ('http', 'https') and parsed.hostname:
        return parsed.scheme, parsed.hostname.lower()
    return None, None


def looks_like_url(text: str) -> bool:
    """Rozliší URL od lokální cesty (bez ohledu na to, zda je URL povolená)."""
    text = (text or '').strip().lower()
    return text.startswith(('http://', 'https://', 'ssh://', 'git://', 'git@'))


def is_trusted_git_url(text: str) -> bool:
    """True pro HTTP(S)/SSH URL na povoleném hostu bez přihlašovacích údajů v URL."""
    scheme, host = parse_git_url_host(text)
    if not scheme or not _host_is_trusted(host):
        return False
    if scheme in ('http', 'https'):
        parsed = urlparse(text.strip())
        # Údaje v URL (user:heslo@host) nepovolujeme - skončily by v .git/config a v logu
        if parsed.username is not None or parsed.password is not None:
            return False
    return True


def can_use_github_token(url: str) -> bool:
    """Token GitHub OAuth se smí poslat jen přes HTTPS přímo na github.com."""
    scheme, host = parse_git_url_host(url)
    return scheme == 'https' and host in GITHUB_TOKEN_HOSTS


def _no_own_login_env() -> Dict[str, str]:
    """Git se na přihlášení nesmí ptát sám ani si ho brát odjinud než od aplikace.

    Bez terminálu (GIT_TERMINAL_PROMPT), bez programu askpass (prázdné
    GIT_ASKPASS má přednost i před core.askPass a SSH_ASKPASS) a bez okna
    Git Credential Manageru (GCM_INTERACTIVE; uplatní se jen tam, kde starý
    Git ignoruje vypnutí helperu přes GIT_CONFIG_*).
    """
    return {
        'GIT_TERMINAL_PROMPT': '0',
        'GIT_ASKPASS': '',
        'GCM_INTERACTIVE': 'never',
    }


def build_git_clone_env(url: str) -> Dict[str, str]:
    """Proměnné prostředí pro klon bez tokenu aplikace (první pokus).

    Pro GitHub se nepoužije přihlášení, které si pamatuje sám Git (credential
    helper, na Windows obvykle Git Credential Manager): o přístupu ke GitHubu
    má rozhodovat jen přihlášení a odhlášení v aplikaci. Prázdná hodnota
    ``credential.<url>.helper`` vyprázdní seznam helperů jen pro danou adresu
    (Git 2.31+), ostatní hosty se klonují jako dřív.
    """
    env = {'GIT_TERMINAL_PROMPT': '0'}
    for index, base in enumerate(GITHUB_CREDENTIAL_URLS):
        env[f'GIT_CONFIG_KEY_{index}'] = f'credential.{base}.helper'
        env[f'GIT_CONFIG_VALUE_{index}'] = ''
    env['GIT_CONFIG_COUNT'] = str(len(GITHUB_CREDENTIAL_URLS))

    scheme, host = parse_git_url_host(url)
    if scheme in ('http', 'https') and host in GITHUB_TOKEN_HOSTS:
        env.update(_no_own_login_env())
    return env


def build_git_auth_env(token: str) -> Dict[str, str]:
    """Proměnné prostředí, které Gitu předají token jako HTTP hlavičku.

    Zároveň vypínají interaktivní dotazy na heslo a credential helper, aby Git
    při neplatném tokenu neotevřel vlastní přihlašovací okno, nepoužil jiné
    uložené přihlášení a nečekal nekonečně na vstup v procesu bez konzole.
    """
    basic = base64.b64encode(f"{token}:x-oauth-basic".encode('utf-8')).decode('ascii')
    env = _no_own_login_env()
    env.update({
        'GIT_CONFIG_COUNT': '2',
        'GIT_CONFIG_KEY_0': 'http.https://github.com/.extraHeader',
        'GIT_CONFIG_VALUE_0': f'Authorization: Basic {basic}',
        'GIT_CONFIG_KEY_1': 'credential.helper',
        'GIT_CONFIG_VALUE_1': '',
    })
    return env


_SECRET_PATTERNS = [
    # GitHub tokeny (gho_, ghp_, ghu_, ghs_, ghr_, github_pat_)
    re.compile(r'\b(gh[opusr]_[A-Za-z0-9]{20,}|github_pat_[A-Za-z0-9_]{20,})\b'),
    # Přihlašovací údaje v URL: https://user:secret@host → https://***@host
    re.compile(r'(?<=://)[^/\s@]+@'),
    # Authorization hlavička
    re.compile(r'(Authorization:\s*\w+\s+)\S+', re.IGNORECASE),
]


def redact_secrets(text: str) -> str:
    """Odstraní z textu tokeny a přihlašovací údaje (pro log a chybové dialogy)."""
    if not text:
        return text
    text = _SECRET_PATTERNS[0].sub('***', text)
    text = _SECRET_PATTERNS[1].sub('***@', text)
    text = _SECRET_PATTERNS[2].sub(r'\1***', text)
    return text
