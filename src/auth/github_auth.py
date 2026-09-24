"""
GitHub OAuth Device Flow autentizace.
"""

import threading
import requests
import time
from typing import Optional, Dict, Tuple
from utils.logging_config import get_logger

logger = get_logger(__name__)

# GitHub OAuth App Client ID
GITHUB_CLIENT_ID = "Ov23liTGzNaizqEpgyu1"

# GitHub API endpoints
DEVICE_CODE_URL = "https://github.com/login/device/code"
ACCESS_TOKEN_URL = "https://github.com/login/oauth/access_token"
USER_API_URL = "https://api.github.com/user"


class GitHubAuth:
    """Spravuje GitHub OAuth Device Flow autentizaci."""

    def __init__(self):
        self.client_id = GITHUB_CLIENT_ID

    def request_device_code(self) -> Optional[Dict[str, any]]:
        """
        Požádá GitHub o device code a user code.

        Returns:
            Dict s klíči:
                - device_code: Kód pro polling
                - user_code: Kód pro zobrazení uživateli
                - verification_uri: URL kam uživatel jde
                - expires_in: Platnost v sekundách
                - interval: Interval pro polling v sekundách
            Nebo None při chybě
        """
        try:
            response = requests.post(
                DEVICE_CODE_URL,
                headers={"Accept": "application/json"},
                data={
                    "client_id": self.client_id,
                    "scope": "repo"  # Přístup k soukromým repozitářům
                },
                timeout=10
            )

            if response.status_code != 200:
                logger.warning(f"Failed to request device code: {response.status_code}")
                return None

            data = response.json()

            # Kontrola povinných polí
            required_fields = ['device_code', 'user_code', 'verification_uri', 'interval']
            if not all(field in data for field in required_fields):
                logger.warning(f"Missing required fields in device code response, keys: {sorted(data.keys())}")
                return None

            logger.info("Device code obtained")
            return data

        except requests.RequestException as e:
            logger.warning(f"Network error requesting device code: {e}")
            return None
        except Exception as e:
            logger.warning(f"Error requesting device code: {e}")
            return None

    def poll_for_token(self, device_code: str, interval: int = 5, timeout: int = 300,
                       cancel_event: Optional[threading.Event] = None) -> Tuple[Optional[str], str]:
        """
        Polluje GitHub API pro access token (RFC 8628, kap. 3.4–3.5).

        Args:
            device_code: Device code z request_device_code()
            interval: Interval mezi pokusy v sekundách (GitHub ho může zvýšit přes slow_down)
            timeout: Maximální čas čekání v sekundách (typicky expires_in z device code)
            cancel_event: Nastavením eventu se polling okamžitě ukončí (zavřený dialog)

        Returns:
            Tuple (access_token, status):
                - access_token: Token pokud úspěch, None jinak
                - status: "success", "timeout", "cancelled", "error"
        """
        start_time = time.time()
        attempts = 0

        def wait(seconds: float) -> bool:
            """Počká; vrátí True, pokud mezitím uživatel polling zrušil."""
            if cancel_event is None:
                time.sleep(seconds)
                return False
            return cancel_event.wait(seconds)

        while time.time() - start_time < timeout:
            if cancel_event is not None and cancel_event.is_set():
                return None, "cancelled"

            attempts += 1

            try:
                response = requests.post(
                    ACCESS_TOKEN_URL,
                    headers={"Accept": "application/json"},
                    data={
                        "client_id": self.client_id,
                        "device_code": device_code,
                        "grant_type": "urn:ietf:params:oauth:grant-type:device_code"
                    },
                    timeout=10
                )

                if response.status_code != 200:
                    logger.debug(f"Token polling attempt {attempts}: HTTP {response.status_code}")
                    if wait(interval):
                        return None, "cancelled"
                    continue

                data = response.json()

                # Kontrola chyb
                if "error" in data:
                    error = data["error"]

                    if error == "authorization_pending":
                        # Normální stav - uživatel ještě neautorizoval
                        logger.debug(f"Waiting for authorization (attempt {attempts})...")
                        if wait(interval):
                            return None, "cancelled"
                        continue

                    elif error == "slow_down":
                        # RFC 8628: interval se TRVALE zvyšuje o 5 s (GitHub posílá i nový interval)
                        interval = max(interval + 5, int(data.get("interval", 0) or 0))
                        logger.debug(f"Slowing down polling interval to {interval}s")
                        if wait(interval):
                            return None, "cancelled"
                        continue

                    elif error == "expired_token":
                        # Device code vypršel
                        logger.warning("Device code expired")
                        return None, "timeout"

                    elif error == "access_denied":
                        # Uživatel odmítl autorizaci
                        logger.info("User denied authorization")
                        return None, "cancelled"

                    else:
                        # Jiná chyba
                        logger.warning(f"OAuth error: {error}")
                        return None, "error"

                # Úspěch - máme token
                if "access_token" in data:
                    token = data["access_token"]
                    logger.info("Access token obtained successfully")
                    return token, "success"

                # Neočekávaná odpověď (bez obsahu - mohla by nést citlivá data)
                logger.warning(f"Unexpected token response, keys: {sorted(data.keys())}")
                if wait(interval):
                    return None, "cancelled"

            except requests.RequestException as e:
                logger.debug(f"Network error during polling (attempt {attempts}): {e}")
                if wait(interval):
                    return None, "cancelled"
                continue

            except Exception as e:
                logger.warning(f"Error during polling: {e}")
                return None, "error"

        # Timeout
        logger.warning(f"Token polling timed out after {timeout}s")
        return None, "timeout"

    def verify_token(self, token: str) -> Optional[str]:
        """
        Ověří platnost tokenu a vrátí username.

        Args:
            token: GitHub access token

        Returns:
            GitHub username pokud je token platný, None jinak
        """
        try:
            response = requests.get(
                USER_API_URL,
                headers={
                    "Authorization": f"token {token}",
                    "Accept": "application/json"
                },
                timeout=10
            )

            if response.status_code != 200:
                logger.warning(f"Token verification failed: HTTP {response.status_code}")
                return None

            data = response.json()
            username = data.get("login")

            if username:
                logger.info(f"Token verified for user: {username}")
            else:
                logger.warning("Token verification: no username in response")

            return username

        except requests.RequestException as e:
            logger.warning(f"Network error verifying token: {e}")
            return None
        except Exception as e:
            logger.warning(f"Error verifying token: {e}")
            return None
