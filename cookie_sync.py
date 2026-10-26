"""
Cookie Synchronization and Chrome Profile Manager for Universal-Web-MCP.
Handles automatic detection of Chrome profiles, DPAPI/AES-GCM decryption,
Playwright CDP cookie export, and secure masking of credentials.
"""

import os
import sys
import json
import base64
import sqlite3
import tempfile
import shutil
import logging
from typing import Dict, List, Optional, Any
from pathlib import Path

logger = logging.getLogger("UniversalWebMCP.CookieSync")


def mask_secret(value: str, visible_prefix: int = 4, visible_suffix: int = 4) -> str:
    """Masks secret values like tokens and cookies for safe logging."""
    if not value or not isinstance(value, str):
        return "****"
    if len(value) <= visible_prefix + visible_suffix:
        return "****"
    return f"{value[:visible_prefix]}...{value[-visible_suffix:]}"


def mask_headers(headers: Dict[str, Any]) -> Dict[str, Any]:
    """Returns a copy of headers with sensitive authorization/cookies masked."""
    masked = {}
    sensitive_keys = {
        "cookie", "authorization", "x-api-key", "x-goog-api-key",
        "proxy-authorization", "set-cookie", "token", "x-auth-token"
    }
    for k, v in headers.items():
        if k.lower() in sensitive_keys:
            masked[k] = mask_secret(str(v))
        else:
            masked[k] = v
    return masked


class ChromeProfileManager:
    """Manages Chrome profile detection, cookie retrieval, and persistent session state."""

    def __init__(self, storage_path: str = "session_cookies.json"):
        self.storage_path = Path(storage_path)
        self.user_data_dir = self._detect_chrome_user_data_dir()
        self.cached_cookies: Dict[str, str] = {}
        self.load_stored_cookies()

    def _detect_chrome_user_data_dir(self) -> Path:
        """Locates the default Chrome User Data directory for the host OS."""
        if sys.platform == "win32":
            local_appdata = os.getenv("LOCALAPPDATA", "")
            return Path(local_appdata) / "Google" / "Chrome" / "User Data"
        elif sys.platform == "darwin":
            return Path.home() / "Library" / "Application Support" / "Google" / "Chrome"
        else:
            return Path.home() / ".config" / "google-chrome"

    def find_profile_by_email(self, email_or_name: str) -> Optional[str]:
        """
        Parses Chrome's Local State file to find the profile directory matching
        an email address or username (e.g. 'arq5020@gmail.com' -> 'Profile 1').
        """
        local_state_path = self.user_data_dir / "Local State"
        if not local_state_path.exists():
            logger.warning(f"Chrome Local State not found at {local_state_path}")
            return None

        try:
            with open(local_state_path, "r", encoding="utf-8") as f:
                data = json.load(f)
            profiles = data.get("profile", {}).get("info_cache", {})
            
            target = email_or_name.lower().strip()
            # 1. Exact match on username or gaia email
            for profile_name, info in profiles.items():
                user_name = info.get("user_name", "").lower()
                gaia_name = info.get("gaia_name", "").lower()
                name = info.get("name", "").lower()
                if target in (user_name, gaia_name, name):
                    logger.info(f"Matched profile '{profile_name}' for target '{email_or_name}'")
                    return profile_name

            # 2. Close match (handles typos like are5020 vs arq5020)
            import difflib
            all_emails = {
                info.get("user_name", "").lower(): p
                for p, info in profiles.items() if info.get("user_name")
            }
            matches = difflib.get_close_matches(target, list(all_emails.keys()), n=1, cutoff=0.6)
            if matches:
                matched_profile = all_emails[matches[0]]
                logger.info(f"Fuzzy matched profile '{matched_profile}' ({matches[0]}) for '{email_or_name}'")
                return matched_profile

            # 3. Default if profile exists
            if "Default" in profiles:
                return "Default"
            elif profiles:
                return list(profiles.keys())[0]

        except Exception as e:
            logger.error(f"Error reading Chrome Local State: {e}")
        return None

    def get_windows_aes_key(self) -> Optional[bytes]:
        """Extracts and decrypts Chrome's master AES-GCM key from Local State using DPAPI."""
        if sys.platform != "win32":
            return None
        local_state_path = self.user_data_dir / "Local State"
        if not local_state_path.exists():
            return None

        try:
            import win32crypt
            with open(local_state_path, "r", encoding="utf-8") as f:
                data = json.load(f)
            enc_key_b64 = data.get("os_crypt", {}).get("encrypted_key")
            if not enc_key_b64:
                return None
            enc_key = base64.b64decode(enc_key_b64)[5:]  # Strip 'DPAPI' prefix
            master_key = win32crypt.CryptUnprotectData(enc_key, None, None, None, 0)[1]
            return master_key
        except Exception as e:
            logger.debug(f"Could not extract Chrome AES key: {e}")
            return None

    def extract_cookies_from_sqlite(self, profile_name: str, domain_filter: Optional[str] = None) -> Dict[str, str]:
        """
        Attempts to read and decrypt cookies from SQLite file when Chrome is idle.
        Falls back gracefully if the database is locked by active browser processes.
        """
        cookie_path = self.user_data_dir / profile_name / "Network" / "Cookies"
        if not cookie_path.exists():
            cookie_path = self.user_data_dir / profile_name / "Cookies"
        if not cookie_path.exists():
            logger.warning(f"Cookie database not found at {cookie_path}")
            return {}

        master_key = self.get_windows_aes_key()
        cookies = {}

        # Copy to temp file to minimize lock collisions
        tmp_db = None
        try:
            tmp_db = tempfile.mktemp(suffix=".sqlite")
            shutil.copy2(cookie_path, tmp_db)

            from cryptography.hazmat.primitives.ciphers.aead import AESGCM
            conn = sqlite3.connect(tmp_db)
            cursor = conn.cursor()

            query = "SELECT host_key, name, encrypted_value, value FROM cookies"
            params = []
            if domain_filter:
                query += " WHERE host_key LIKE ?"
                params.append(f"%{domain_filter}%")

            cursor.execute(query, params)
            rows = cursor.fetchall()

            for host_key, name, enc_val, plain_val in rows:
                if plain_val:
                    cookies[name] = plain_val
                    continue
                if not enc_val:
                    continue

                try:
                    if enc_val[:3] in (b"v10", b"v11") and master_key:
                        nonce = enc_val[3:15]
                        ciphertext_tag = enc_val[15:]
                        aes = AESGCM(master_key)
                        val = aes.decrypt(nonce, ciphertext_tag, None).decode("utf-8", errors="ignore")
                        cookies[name] = val
                    elif sys.platform == "win32":
                        import win32crypt
                        val = win32crypt.CryptUnprotectData(enc_val, None, None, None, 0)[1].decode("utf-8", errors="ignore")
                        cookies[name] = val
                except Exception:
                    # Ignore un-decryptable or v20 app-bound cookies
                    continue

            conn.close()
            logger.info(f"Extracted {len(cookies)} cookies directly from {profile_name} SQLite DB")
        except Exception as e:
            logger.debug(f"Direct SQLite cookie extraction bypassed ({e}). Using CDP/Playwright sync.")
        finally:
            if tmp_db and os.path.exists(tmp_db):
                try:
                    os.remove(tmp_db)
                except Exception:
                    pass

        return cookies

    def sync_from_playwright_cookies(self, playwright_cookies: List[Dict[str, Any]]):
        """Syncs cookies received from Playwright context or CDP session."""
        for c in playwright_cookies:
            name = c.get("name")
            value = c.get("value")
            if name and value:
                self.cached_cookies[name] = value
        self.save_stored_cookies()

    def get_cookie_header(self, domain: Optional[str] = None) -> str:
        """Formats the cached cookies into a standard HTTP 'Cookie: a=1; b=2' string."""
        if not self.cached_cookies:
            return ""
        return "; ".join(f"{k}={v}" for k, v in self.cached_cookies.items())

    def get_cookies_dict(self) -> Dict[str, str]:
        """Returns the dictionary of currently cached cookies."""
        return dict(self.cached_cookies)

    def save_stored_cookies(self):
        """Persists the session cookies to a local JSON file."""
        try:
            with open(self.storage_path, "w", encoding="utf-8") as f:
                json.dump(self.cached_cookies, f, indent=2)
            logger.info(f"Saved {len(self.cached_cookies)} cookies to {self.storage_path}")
        except Exception as e:
            logger.error(f"Failed to save cookies to {self.storage_path}: {e}")

    def load_stored_cookies(self):
        """Loads cached cookies from the local JSON file if present."""
        if self.storage_path.exists():
            try:
                with open(self.storage_path, "r", encoding="utf-8") as f:
                    self.cached_cookies = json.load(f)
                logger.info(f"Loaded {len(self.cached_cookies)} cached cookies from {self.storage_path}")
            except Exception as e:
                logger.warning(f"Could not load cookies from {self.storage_path}: {e}")
