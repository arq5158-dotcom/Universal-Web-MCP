"""
Persistent Session Manager for Universal-Web-MCP.
Manages multiple browser session profiles (Add, Remove, Switch, Retain).
Persists all sessions to sessions.json so login info survives server restarts and machine reboots.
"""

import os
import sys
import json
import logging
from typing import Dict, List, Any, Optional
from pathlib import Path
from datetime import datetime

logger = logging.getLogger("UniversalWebMCP.SessionManager")

BASE_DIR = Path(__file__).resolve().parent
SESSIONS_FILE = BASE_DIR / "sessions.json"
STORAGE_DIR = BASE_DIR / "saved_sessions"
STORAGE_DIR.mkdir(parents=True, exist_ok=True)


class SessionManager:
    """Manages persistent browser authentication sessions across multiple accounts."""

    def __init__(self, sessions_file: Path = SESSIONS_FILE):
        self.sessions_file = sessions_file
        self.sessions: Dict[str, Dict[str, Any]] = {}
        self.load()

    def load(self):
        """Loads sessions from sessions.json or initializes from existing cookies."""
        if self.sessions_file.exists():
            try:
                with open(self.sessions_file, "r", encoding="utf-8") as f:
                    self.sessions = json.load(f)
                logger.info(f"Loaded {len(self.sessions)} saved session profiles from {self.sessions_file}")
            except Exception as e:
                logger.warning(f"Error reading {self.sessions_file}: {e}")
                self.sessions = {}
        else:
            self.sessions = {}

        # Auto-seed existing session if available and none exist
        if not self.sessions:
            existing_auth = BASE_DIR / "flow_auth_state.json"
            existing_cookies = BASE_DIR / "session_cookies.json"
            if existing_auth.exists() or existing_cookies.exists():
                try:
                    c_count = 0
                    if existing_cookies.exists():
                        with open(existing_cookies, "r", encoding="utf-8") as f:
                            c_count = len(json.load(f))
                    default_id = "sess_google_flow_default"
                    self.sessions[default_id] = {
                        "id": default_id,
                        "name": "Google Flow",
                        "email": "",
                        "domain": "flow.google.com",
                        "is_active": True,
                        "created_at": datetime.now().isoformat(),
                        "cookie_count": c_count,
                        "auth_file": str(existing_auth) if existing_auth.exists() else None,
                        "cookies_file": str(existing_cookies) if existing_cookies.exists() else None
                    }
                    self.save()
                except Exception as e:
                    logger.debug(f"Auto-seed error: {e}")

    def save(self):
        """Saves session profiles to sessions.json permanently and tells the dashboard."""
        try:
            with open(self.sessions_file, "w", encoding="utf-8") as f:
                json.dump(self.sessions, f, indent=2)
            logger.info(f"Saved {len(self.sessions)} session profiles to {self.sessions_file}")
        except Exception as e:
            logger.error(f"Failed to save {self.sessions_file}: {e}")
        try:
            from live_events import live_broadcaster
            live_broadcaster.emit("sessions_changed", "Accounts updated.")
        except Exception:
            pass

    def reload_if_changed(self):
        """Pick up changes written by another Ashzo process (e.g. the MCP server)."""
        try:
            mtime = self.sessions_file.stat().st_mtime if self.sessions_file.exists() else 0
        except OSError:
            mtime = 0
        if mtime and mtime != getattr(self, "_mtime", None):
            self._mtime = mtime
            try:
                with open(self.sessions_file, "r", encoding="utf-8") as f:
                    self.sessions = json.load(f)
            except Exception:
                pass

    def list_sessions(self) -> List[Dict[str, Any]]:
        """Returns all configured sessions."""
        self.reload_if_changed()
        return list(self.sessions.values())

    def get_active_session(self) -> Optional[Dict[str, Any]]:
        """Returns the currently active session profile."""
        for s in self.sessions.values():
            if s.get("is_active"):
                return s
        if self.sessions:
            first = list(self.sessions.values())[0]
            first["is_active"] = True
            self.save()
            return first
        return None

    def add_session(
        self,
        name: str,
        email: str,
        domain: str = "google.com",
        cookies_dict: Optional[Dict[str, str]] = None,
        storage_state_data: Optional[Dict[str, Any]] = None,
        set_active: bool = True
    ) -> Dict[str, Any]:
        """Saves a session profile. Signing in again to the same site and account updates it instead of adding a copy."""
        existing = next((s for s in self.sessions.values()
                         if (s.get("domain") or "").lower() == (domain or "").lower()
                         and ((s.get("email") or "").lower() == (email or "").lower() or not s.get("email"))), None)
        session_id = existing["id"] if existing else f"sess_{int(datetime.now().timestamp())}_{len(self.sessions)}"
        sess_dir = STORAGE_DIR / session_id
        sess_dir.mkdir(parents=True, exist_ok=True)

        auth_path = sess_dir / "storage_state.json"
        cookies_path = sess_dir / "cookies.json"

        # Save cookies
        cookie_count = len(cookies_dict) if cookies_dict else 0
        if cookies_dict:
            with open(cookies_path, "w", encoding="utf-8") as f:
                json.dump(cookies_dict, f, indent=2)

        # Save storage state
        if storage_state_data:
            with open(auth_path, "w", encoding="utf-8") as f:
                json.dump(storage_state_data, f, indent=2)
            if not cookie_count:
                cookie_count = len(storage_state_data.get("cookies", []))
        elif cookies_dict:
            # Build storage state from cookies
            p_cookies = [
                {
                    "name": k,
                    "value": v,
                    "domain": f".{domain}" if not domain.startswith(".") else domain,
                    "path": "/",
                    "secure": True,
                    "sameSite": "Lax"
                }
                for k, v in cookies_dict.items()
            ]
            st_data = {"cookies": p_cookies, "origins": []}
            with open(auth_path, "w", encoding="utf-8") as f:
                json.dump(st_data, f, indent=2)

        if set_active:
            for s in self.sessions.values():
                s["is_active"] = False

        record = dict(existing or {})
        record.update({
            "id": session_id,
            "name": name,
            "email": email,
            "domain": domain,
            "is_active": set_active,
            "created_at": datetime.now().isoformat(),
            "cookie_count": cookie_count,
            "auth_file": str(auth_path),
            "cookies_file": str(cookies_path)
        })
        if existing:
            record["created_at"] = existing.get("created_at") or record["created_at"]
            record["updated_at"] = datetime.now().isoformat()
        self.sessions[session_id] = record
        self.save()

        # Update root active session files
        if set_active:
            self._sync_root_files(record)

        return record

    def remove_session(self, session_id: str) -> bool:
        """Permanently deletes a saved session profile."""
        if session_id in self.sessions:
            was_active = self.sessions[session_id].get("is_active", False)
            del self.sessions[session_id]
            if was_active and self.sessions:
                list(self.sessions.values())[0]["is_active"] = True
            self.save()
            return True
        return False

    def select_session(self, session_id: str) -> Optional[Dict[str, Any]]:
        """Sets a session profile as the active one."""
        if session_id in self.sessions:
            for s in self.sessions.values():
                s["is_active"] = False
            self.sessions[session_id]["is_active"] = True
            self.save()
            self._sync_root_files(self.sessions[session_id])
            return self.sessions[session_id]
        return None

    def _sync_root_files(self, record: Dict[str, Any]):
        """Syncs the active session files to root flow_auth_state.json and session_cookies.json."""
        try:
            if record.get("auth_file") and os.path.exists(record["auth_file"]):
                import shutil
                shutil.copy2(record["auth_file"], str(BASE_DIR / "flow_auth_state.json"))
            if record.get("cookies_file") and os.path.exists(record["cookies_file"]):
                import shutil
                shutil.copy2(record["cookies_file"], str(BASE_DIR / "session_cookies.json"))
        except Exception as e:
            logger.debug(f"Sync root files notice: {e}")


session_manager = SessionManager()
