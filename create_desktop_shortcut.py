"""
Creates the "Ashzo MCP" app icon on the desktop.

Double-clicking the icon starts the dashboard on this computer (http://localhost:8000)
and opens it in the default browser. Run once after setup:

    python create_desktop_shortcut.py        (Windows: or double-click CREATE_DESKTOP_ICON.bat)

Windows: Desktop\\Ashzo MCP.lnk (with the Ashzo icon, no console window)
macOS:   ~/Desktop/Ashzo MCP.command
Linux:   ~/Desktop/ashzo-mcp.desktop (also added to the app menu)
Prints the path it created, so an agent can tell the user where the icon is.
"""

from __future__ import annotations

import os
import platform
import stat
import subprocess
import sys
from pathlib import Path

BASE_DIR = Path(__file__).resolve().parent
LAUNCHER = BASE_DIR / "launch_ashzo.py"
NAME = "Ashzo MCP"


def _windows_desktop() -> Path:
    try:
        out = subprocess.run(["powershell", "-NoProfile", "-Command", "[Environment]::GetFolderPath('Desktop')"],
                             capture_output=True, text=True, timeout=20).stdout.strip()
        if out:
            return Path(out)
    except Exception:
        pass
    return Path(os.environ.get("USERPROFILE", str(Path.home()))) / "Desktop"


def _windows_python() -> Path:
    for c in (BASE_DIR / ".venv" / "Scripts" / "pythonw.exe", Path(sys.executable).with_name("pythonw.exe"),
              BASE_DIR / ".venv" / "Scripts" / "python.exe", Path(sys.executable)):
        if c.exists():
            return c
    return Path(sys.executable)


def _ps_quote(s: str) -> str:
    return "'" + s.replace("'", "''") + "'"


def create_windows() -> Path:
    desktop = _windows_desktop()
    desktop.mkdir(parents=True, exist_ok=True)
    lnk = desktop / f"{NAME}.lnk"
    script = (
        "$s = (New-Object -ComObject WScript.Shell).CreateShortcut(" + _ps_quote(str(lnk)) + ");"
        "$s.TargetPath = " + _ps_quote(str(_windows_python())) + ";"
        "$s.Arguments = " + _ps_quote(f'"{LAUNCHER}"') + ";"
        "$s.WorkingDirectory = " + _ps_quote(str(BASE_DIR)) + ";"
        "$s.IconLocation = " + _ps_quote(str(BASE_DIR / "assets" / "ashzo.ico")) + ";"
        "$s.Description = 'Start Ashzo MCP and open the dashboard';"
        "$s.Save()"
    )
    r = subprocess.run(["powershell", "-NoProfile", "-ExecutionPolicy", "Bypass", "-Command", script],
                       capture_output=True, text=True, timeout=60)
    if r.returncode != 0 or not lnk.exists():
        raise RuntimeError(f"Couldn't create the shortcut: {r.stderr.strip() or r.stdout.strip()}")
    return lnk


def create_macos() -> Path:
    target = Path.home() / "Desktop" / f"{NAME}.command"
    py = BASE_DIR / ".venv" / "bin" / "python"
    py = py if py.exists() else Path(sys.executable)
    target.write_text(f'#!/bin/bash\ncd "{BASE_DIR}"\n"{py}" "{LAUNCHER}"\n', encoding="utf-8")
    target.chmod(target.stat().st_mode | stat.S_IXUSR | stat.S_IXGRP | stat.S_IXOTH)
    return target


def create_linux() -> Path:
    py = BASE_DIR / ".venv" / "bin" / "python"
    py = py if py.exists() else Path(sys.executable)
    entry = (
        "[Desktop Entry]\nType=Application\nName=Ashzo MCP\nComment=Start Ashzo MCP and open the dashboard\n"
        f'Exec="{py}" "{LAUNCHER}"\nPath={BASE_DIR}\nIcon={BASE_DIR / "assets" / "ashzo.png"}\n'
        "Terminal=false\nCategories=Development;Utility;\n"
    )
    desktop_dir = Path.home() / "Desktop"
    if _has("xdg-user-dir"):
        out = subprocess.run(["xdg-user-dir", "DESKTOP"], capture_output=True, text=True).stdout.strip()
        if out:
            desktop_dir = Path(out)
    desktop_dir.mkdir(parents=True, exist_ok=True)
    target = desktop_dir / "ashzo-mcp.desktop"
    target.write_text(entry, encoding="utf-8")
    target.chmod(target.stat().st_mode | stat.S_IXUSR)
    if _has("gio"):
        subprocess.run(["gio", "set", str(target), "metadata::trusted", "true"], capture_output=True)
    apps = Path.home() / ".local" / "share" / "applications"
    apps.mkdir(parents=True, exist_ok=True)
    (apps / "ashzo-mcp.desktop").write_text(entry, encoding="utf-8")
    return target


def _has(cmd: str) -> bool:
    from shutil import which
    return which(cmd) is not None


def main() -> int:
    system = platform.system()
    try:
        path = {"Windows": create_windows, "Darwin": create_macos}.get(system, create_linux)()
    except Exception as e:
        print(f"Could not create the desktop icon: {e}")
        return 1
    print(f"Created the Ashzo MCP app icon: {path}")
    print("Double-click it to start Ashzo MCP and open the dashboard in your browser.")
    return 0


if __name__ == "__main__":
    sys.exit(main())
