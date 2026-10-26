"""
User settings for Ashzo MCP, stored in ashzo_settings.json next to the code
(git-ignored). Every value has a safe default, so the file is optional.
"""

from __future__ import annotations

import json
import logging
from pathlib import Path
from typing import Any, Dict

logger = logging.getLogger("AshzoMCP.Settings")

BASE_DIR = Path(__file__).resolve().parent
SETTINGS_FILE = BASE_DIR / "ashzo_settings.json"

DEFAULTS: Dict[str, Any] = {
    # The Google Flow project the generator works in. Paste your own project link in Settings.
    "flow_project_url": "https://flow.google.com/",
    # Show the Ashzo Browser window while the agent works (you can watch it), or run it hidden.
    "browser_visible": True,
    # Chrome DevTools port of the Ashzo Browser (a separate Chrome window with its own profile).
    "browser_port": 9333,
    # How long to wait for you to finish signing in.
    "login_timeout_seconds": 300,
    # How long a Flow generation may take before it is reported as stuck.
    "render_timeout_seconds": 900,
    # Default output shape for generations.
    "aspect_ratio": "9:16",
}

_KEYS_TYPES = {k: type(v) for k, v in DEFAULTS.items()}


def load_settings() -> Dict[str, Any]:
    data = dict(DEFAULTS)
    if SETTINGS_FILE.exists():
        try:
            saved = json.loads(SETTINGS_FILE.read_text(encoding="utf-8"))
            for k, v in saved.items():
                if k in DEFAULTS and isinstance(v, _KEYS_TYPES[k]):
                    data[k] = v
        except Exception as e:  # corrupt file: keep defaults
            logger.warning("Could not read %s: %s", SETTINGS_FILE, e)
    return data


def save_settings(changes: Dict[str, Any]) -> Dict[str, Any]:
    data = load_settings()
    for k, v in (changes or {}).items():
        if k not in DEFAULTS:
            continue
        want = _KEYS_TYPES[k]
        try:
            if want is bool and not isinstance(v, bool):
                v = str(v).lower() in ("1", "true", "yes", "on")
            elif want is int:
                v = int(v)
            elif want is str:
                v = str(v).strip()
        except (TypeError, ValueError):
            continue
        data[k] = v
    SETTINGS_FILE.write_text(json.dumps(data, indent=2), encoding="utf-8")
    return data


def get_setting(key: str) -> Any:
    return load_settings().get(key, DEFAULTS.get(key))
