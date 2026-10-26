"""
Ashzo MCP launcher (what the desktop icon runs).

1. If the dashboard is already running, just opens it.
2. Otherwise starts it in the background (no console window) and waits until it answers.
3. Opens it in your default browser (Chrome, Edge, Firefox, ...).

Usage: python launch_ashzo.py            (or double-click the "Ashzo MCP" desktop icon)
       python launch_ashzo.py --no-browser
Server output goes to logs/ashzo_server.log.
"""

from __future__ import annotations

import json
import os
import platform
import subprocess
import sys
import time
import urllib.request
import webbrowser
from pathlib import Path

BASE_DIR = Path(__file__).resolve().parent
LOG_DIR = BASE_DIR / "logs"
HOST = "127.0.0.1"
FIRST_PORT = int(os.environ.get("ASHZO_PORT") or 8000)
IS_WIN = platform.system() == "Windows"


def _health(port: int, timeout: float = 1.5):
    try:
        with urllib.request.urlopen(f"http://{HOST}:{port}/api/health", timeout=timeout) as r:
            return json.loads(r.read().decode("utf-8"))
    except Exception:
        return None


def _port_free(port: int) -> bool:
    import socket
    with socket.socket(socket.AF_INET, socket.SOCK_STREAM) as s:
        s.settimeout(0.5)
        return s.connect_ex((HOST, port)) != 0


def _python() -> str:
    """The project's own Python if there is one (.venv), without a console window on Windows."""
    candidates = []
    if IS_WIN:
        candidates += [BASE_DIR / ".venv" / "Scripts" / "pythonw.exe", BASE_DIR / ".venv" / "Scripts" / "python.exe"]
        exe = Path(sys.executable)
        candidates += [exe.with_name("pythonw.exe"), exe]
    else:
        candidates += [BASE_DIR / ".venv" / "bin" / "python", Path(sys.executable)]
    for c in candidates:
        if c.exists():
            return str(c)
    return sys.executable


def _notify(message: str) -> None:
    """Show a message even when there is no console (desktop icon)."""
    sys.stderr.write(message + "\n")
    try:
        if IS_WIN:
            import ctypes
            ctypes.windll.user32.MessageBoxW(0, message, "Ashzo MCP", 0x40)
        elif platform.system() == "Darwin":
            subprocess.run(["osascript", "-e", f'display dialog "{message}" with title "Ashzo MCP" buttons {{"OK"}}'],
                           check=False, capture_output=True)
    except Exception:
        pass


def _start_server(port: int) -> subprocess.Popen:
    LOG_DIR.mkdir(exist_ok=True)
    log = open(LOG_DIR / "ashzo_server.log", "a", encoding="utf-8")
    log.write(f"\n===== {time.strftime('%Y-%m-%d %H:%M:%S')} starting on port {port} =====\n")
    log.flush()
    env = dict(os.environ, ASHZO_PORT=str(port), PYTHONUNBUFFERED="1")
    kwargs = {"cwd": str(BASE_DIR), "stdout": log, "stderr": log, "stdin": subprocess.DEVNULL, "env": env}
    if IS_WIN:
        kwargs["creationflags"] = 0x00000008 | 0x00000200 | 0x08000000  # DETACHED | NEW_GROUP | NO_WINDOW
    else:
        kwargs["start_new_session"] = True
    return subprocess.Popen([_python(), str(BASE_DIR / "app.py")], **kwargs)


def main() -> int:
    open_browser = "--no-browser" not in sys.argv

    # Already running?
    for port in range(FIRST_PORT, FIRST_PORT + 10):
        h = _health(port)
        if h and h.get("app") == "ashzo-mcp":
            url = f"http://localhost:{port}/"
            if open_browser:
                webbrowser.open(url)
            print(f"Ashzo MCP is already running: {url}")
            return 0

    port = next((p for p in range(FIRST_PORT, FIRST_PORT + 10) if _port_free(p)), None)
    if port is None:
        _notify(f"Ports {FIRST_PORT}-{FIRST_PORT + 9} are all in use. Close the program using them and try again.")
        return 1

    proc = _start_server(port)
    deadline = time.time() + 60
    while time.time() < deadline:
        if proc.poll() is not None:
            _notify("Ashzo MCP stopped while starting. Details are in logs/ashzo_server.log.\n\n"
                    "If this is the first run, double-click CREATE_DESKTOP_ICON.bat once to install what it needs.")
            return 1
        h = _health(port)
        if h and h.get("app") == "ashzo-mcp":
            url = f"http://localhost:{port}/"
            if open_browser:
                webbrowser.open(url)
            print(f"Ashzo MCP is running: {url}")
            return 0
        time.sleep(0.5)
    _notify("Ashzo MCP is taking too long to start. Details are in logs/ashzo_server.log.")
    return 1


if __name__ == "__main__":
    sys.exit(main())
