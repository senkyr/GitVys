"""
GitHub OAuth Device Flow autentizace.
"""

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
                logger.warning(f"Missing required fields in device code response: {data}")
                return None

            logger.info(f"Device code obtained: {data['user_code']}")
            return data

        except requests.RequestException as e:
            logger.warning(f"Network error requesting device code: {e}")
            return None
        except Exception as e:
            logger.warning(f"Error requesting device code: {e}")
            return None

    def poll_for_token(self, device_code: str, interval: int = 5, timeout: int = 300) -> Tuple[Optional[str], str]:
        """
        Polluje GitHub API pro access token.

        Args:
            device_code: Device code z request_device_code()
            interval: Interval mezi pokusy v sekundách
            timeout: Maximální čas čekání v sekundách

        Returns:
            Tuple (access_token, status):
                - access_token: Token pokud úspěch, None jinak
                - status: "success", "timeout", "cancelled", "error"
        """
        start_time = time.time()
        attempts = 0

        while time.time() - start_time < timeout:
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
                    time.sleep(interval)
                    continue

                data = response.json()

                # Kontrola chyb
                if "error" in data:
                    error = data["error"]

                    if error == "authorization_pending":
                        # Normální stav - uživatel ještě neautorizoval
                        logger.debug(f"Waiting for authorization (attempt {attempts})...")
                        time.sleep(interval)
                        continue

                    elif error == "slow_down":
                        # GitHub žádá o zpomalení pollingu
                        logger.debug("Slowing down polling interval")
                        time.sleep(interval + 5)
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

                # Neočekávaná odpověď
                logger.warning(f"Unexpected response: {data}")
                time.sleep(interval)

            except requests.RequestException as e:
                logger.debug(f"Network error during polling (attempt {attempts}): {e}")
                time.sleep(interval)
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
