"""
Ashzo Browser: one real Chrome window that every Ashzo MCP job runs in.

Why a real Chrome (and not a hidden Playwright browser):
  * You can watch the agent work in it, live, and step in if needed.
  * Google sign-in works there. Google refuses many robot-controlled browsers
    ("This browser or app may not be secure"); a normal Chrome window that
    Ashzo connects to over the DevTools port is treated like your own Chrome.
  * Logins stay. The window uses its own profile folder (.ashzo_browser/), so
    you sign in once and every later job is already signed in. Your everyday
    Chrome profile is never touched.

Everything the window shows can also be mirrored into the dashboard's Live View
(Chrome's screencast, streamed through live_events).
"""

from __future__ import annotations

import asyncio
import base64
import logging
import os
import platform
import shutil
import subprocess
import sys
import time
from pathlib import Path
from typing import Any, Dict, Optional
from urllib.parse import urlparse

from ashzo_settings import load_settings
from live_events import live_broadcaster

logger = logging.getLogger("AshzoMCP.BrowserHub")

BASE_DIR = Path(__file__).resolve().parent
PROFILE_DIR = BASE_DIR / ".ashzo_browser"


class BrowserLaunchError(RuntimeError):
    pass


def find_chrome() -> Optional[str]:
    """Locate Google Chrome (or Edge / Chromium as a fallback) on this computer."""
    env = os.environ.get("ASHZO_CHROME_PATH")
    if env and Path(env).exists():
        return env
    system = platform.system()
    candidates = []
    if system == "Windows":
        for base in (os.environ.get("PROGRAMFILES"), os.environ.get("PROGRAMFILES(X86)"), os.environ.get("LOCALAPPDATA")):
            if base:
                candidates.append(Path(base) / "Google/Chrome/Application/chrome.exe")
        for base in (os.environ.get("PROGRAMFILES(X86)"), os.environ.get("PROGRAMFILES")):
            if base:
                candidates.append(Path(base) / "Microsoft/Edge/Application/msedge.exe")
    elif system == "Darwin":
        candidates += [
            Path("/Applications/Google Chrome.app/Contents/MacOS/Google Chrome"),
            Path.home() / "Applications/Google Chrome.app/Contents/MacOS/Google Chrome",
            Path("/Applications/Microsoft Edge.app/Contents/MacOS/Microsoft Edge"),
        ]
    else:
        for name in ("google-chrome", "google-chrome-stable", "chromium", "chromium-browser", "microsoft-edge"):
            found = shutil.which(name)
            if found:
                candidates.append(Path(found))
    for c in candidates:
        if c and c.exists():
            return str(c)
    return None


def _clear_stale_profile_lock() -> None:
    """Remove Chrome's profile lock when the process named in it is gone (Linux/macOS).

    A killed or crashed Chrome leaves SingletonLock behind. In a container Chrome then
    refuses to start ("profile in use by another computer"), even on the same hostname.
    """
    if platform.system() == "Windows":  # Chrome uses a mutex there, and os.kill(pid, 0) would terminate the process
        return
    lock = PROFILE_DIR / "SingletonLock"
    try:
        host, _, pid = os.readlink(lock).rpartition("-")  # "<hostname>-<pid>"
    except OSError:
        return
    if host == platform.node() and pid.isdigit():
        try:
            os.kill(int(pid), 0)
            cmdline_file = Path(f"/proc/{pid}/cmdline")  # a reused PID may belong to some other program
            if not cmdline_file.exists() or b"chrom" in cmdline_file.read_bytes():
                return  # a real Chrome still holds the profile
        except OSError:
            pass
    for name in ("SingletonLock", "SingletonCookie", "SingletonSocket"):
        try:
            (PROFILE_DIR / name).unlink()
        except OSError:
            pass
    logger.info("Removed a stale Chrome profile lock (%s)", lock)


def _raise_window(title: str, window_class: str = "Chrome_WidgetWin_1") -> bool:
    """Windows only: bring the window whose title starts with `title` to the front.

    Playwright's bring_to_front only activates the tab. Windows blocks a background
    process from taking focus, so this attaches to the foreground thread first.
    """
    if platform.system() != "Windows" or not title:
        return False
    import ctypes
    from ctypes import wintypes

    user32 = ctypes.WinDLL("user32", use_last_error=True)
    kernel32 = ctypes.WinDLL("kernel32", use_last_error=True)
    user32.GetForegroundWindow.restype = wintypes.HWND
    user32.SetForegroundWindow.argtypes = [wintypes.HWND]
    user32.BringWindowToTop.argtypes = [wintypes.HWND]
    user32.ShowWindow.argtypes = [wintypes.HWND, ctypes.c_int]
    user32.IsWindowVisible.argtypes = [wintypes.HWND]
    user32.GetWindowThreadProcessId.argtypes = [wintypes.HWND, ctypes.c_void_p]
    user32.AttachThreadInput.argtypes = [wintypes.DWORD, wintypes.DWORD, wintypes.BOOL]
    user32.GetWindowTextLengthW.argtypes = [wintypes.HWND]
    user32.GetWindowTextW.argtypes = [wintypes.HWND, wintypes.LPWSTR, ctypes.c_int]
    user32.GetClassNameW.argtypes = [wintypes.HWND, wintypes.LPWSTR, ctypes.c_int]
    enum_proc_type = ctypes.WINFUNCTYPE(wintypes.BOOL, wintypes.HWND, wintypes.LPARAM)
    user32.EnumWindows.argtypes = [enum_proc_type, wintypes.LPARAM]

    found: list = []

    def visit(hwnd, _):
        if not user32.IsWindowVisible(hwnd):
            return True
        length = user32.GetWindowTextLengthW(hwnd)
        text = ctypes.create_unicode_buffer(length + 1)
        user32.GetWindowTextW(hwnd, text, length + 1)
        cls = ctypes.create_unicode_buffer(256)
        user32.GetClassNameW(hwnd, cls, 256)
        if cls.value == window_class and text.value.startswith(title):
            found.append(hwnd)
            return False  # stop at the first match
        return True

    user32.EnumWindows(enum_proc_type(visit), 0)
    if not found:
        return False
    hwnd = found[0]
    fg = user32.GetForegroundWindow()
    fg_thread = user32.GetWindowThreadProcessId(fg, None)
    this_thread = kernel32.GetCurrentThreadId()
    attached = bool(fg_thread) and fg_thread != this_thread and user32.AttachThreadInput(this_thread, fg_thread, True)
    try:
        user32.ShowWindow(hwnd, 9)  # SW_RESTORE: also un-minimises it
        user32.BringWindowToTop(hwnd)
        user32.SetForegroundWindow(hwnd)
    finally:
        if attached:
            user32.AttachThreadInput(this_thread, fg_thread, False)
    return user32.GetForegroundWindow() == hwnd


class BrowserHub:
    def __init__(self) -> None:
        self._pw = None
        self._browser = None
        self._context = None
        self._proc: Optional[subprocess.Popen] = None
        self._lock = asyncio.Lock()
        self._casts: Dict[Any, Any] = {}
        self._cast_until: Dict[Any, float] = {}
        self._last_frame_at = 0.0
        self.visible = True
        self.executable: Optional[str] = None

    # ---------------------------------------------------------------- helpers
    @property
    def port(self) -> int:
        return int(load_settings().get("browser_port", 9333))

    async def _port_alive(self) -> bool:
        try:
            import httpx
            async with httpx.AsyncClient(timeout=1.0) as c:
                r = await c.get(f"http://127.0.0.1:{self.port}/json/version")
                return r.status_code == 200
        except Exception:
            return False

    async def _playwright(self):
        if self._pw is None:
            from playwright.async_api import async_playwright
            self._pw = await async_playwright().start()
        return self._pw

    def is_connected(self) -> bool:
        return bool(self._browser is not None and self._browser.is_connected())

    # ----------------------------------------------------------------- launch
    async def _launch(self, visible: bool) -> None:
        pw = await self._playwright()
        exe = find_chrome()
        if not exe:
            try:
                exe = pw.chromium.executable_path  # Playwright's own Chromium
            except Exception:
                exe = None
        if not exe or not Path(exe).exists():
            raise BrowserLaunchError(
                "Google Chrome was not found. Install Chrome from google.com/chrome, "
                "or set ASHZO_CHROME_PATH to its chrome.exe, then try again."
            )
        self.executable = exe
        PROFILE_DIR.mkdir(parents=True, exist_ok=True)
        _clear_stale_profile_lock()
        args = [
            exe,
            f"--remote-debugging-port={self.port}",
            f"--user-data-dir={PROFILE_DIR}",
            "--no-first-run",
            "--no-default-browser-check",
            "--disable-features=Translate,OptimizationHints",
            "--window-size=1360,900",
        ]
        if not visible:
            args.append("--headless=new")
        if platform.system() == "Linux" and hasattr(os, "geteuid") and os.geteuid() == 0:
            args.append("--no-sandbox")
        args.append("about:blank")
        # Chrome's own errors go to logs/chrome.log, so a failed start can be explained.
        (BASE_DIR / "logs").mkdir(exist_ok=True)
        chrome_log = open(BASE_DIR / "logs" / "chrome.log", "ab")
        kwargs: Dict[str, Any] = {"stdout": chrome_log, "stderr": chrome_log, "stdin": subprocess.DEVNULL}
        if platform.system() == "Windows":
            kwargs["creationflags"] = getattr(subprocess, "CREATE_NEW_PROCESS_GROUP", 0)
        logger.info("Launching Ashzo Browser: %s (port %s, visible=%s)", exe, self.port, visible)
        self._proc = subprocess.Popen(args, **kwargs)
        chrome_log.close()  # the child keeps its own copy
        deadline = time.time() + 25
        while time.time() < deadline:
            if await self._port_alive():
                return
            if self._proc.poll() is not None:
                break
            await asyncio.sleep(0.4)
        raise BrowserLaunchError(
            "Chrome started but did not open its control port. Close every Chrome window "
            "that uses the Ashzo profile, then try again."
        )

    async def ensure(self, visible: Optional[bool] = None):
        """Return the Ashzo Browser's context, starting Chrome if needed."""
        if visible is None:
            visible = bool(load_settings().get("browser_visible", True))
        async with self._lock:
            if self.is_connected() and self._context is not None:
                return self._context
            if not await self._port_alive():
                await self._launch(visible)
                self.visible = visible
            pw = await self._playwright()
            self._browser = await pw.chromium.connect_over_cdp(f"http://127.0.0.1:{self.port}", timeout=15000)
            self._browser.on("disconnected", lambda *_: self._on_disconnect())
            self._context = self._browser.contexts[0] if self._browser.contexts else await self._browser.new_context()
            return self._context

    def _on_disconnect(self) -> None:
        self._browser = None
        self._context = None
        self._casts.clear()
        live_broadcaster.emit("browser", "Ashzo Browser was closed.", data={"running": False})

    # ------------------------------------------------------------------ pages
    async def open_page(self, url: str, reuse_host: bool = True, front: bool = True):
        ctx = await self.ensure()
        host = urlparse(url).netloc
        page = None
        if reuse_host and host:
            for p in reversed(ctx.pages):
                try:
                    if urlparse(p.url).netloc == host and not p.is_closed():
                        page = p
                        break
                except Exception:
                    continue
        if page is None:
            blank = [p for p in ctx.pages if p.url in ("about:blank", "chrome://newtab/") and not p.is_closed()]
            page = blank[0] if blank else await ctx.new_page()
            await page.goto(url, wait_until="domcontentloaded", timeout=45000)
        elif page.url.rstrip("/") != url.rstrip("/"):
            await page.goto(url, wait_until="domcontentloaded", timeout=45000)
        if front:
            await self.bring_to_front(page)
        return page

    async def bring_to_front(self, page=None) -> None:
        try:
            if page is None:
                ctx = await self.ensure()
                pages = [p for p in ctx.pages if not p.is_closed()]
                page = pages[-1] if pages else await ctx.new_page()
            await page.bring_to_front()
            if platform.system() == "Windows":
                # Playwright only switches the tab; this raises the actual Chrome window on the desktop.
                title = await page.title()
                if not await asyncio.to_thread(_raise_window, title):
                    logger.warning("Could not bring the Ashzo Browser window to front (title %r)", title)
        except Exception as e:
            logger.warning("bring_to_front: %s", e)

    async def current_page(self):
        if not self.is_connected():
            return None
        pages = [p for p in self._context.pages if not p.is_closed()]
        return pages[-1] if pages else None

    # ------------------------------------------------------------- live view
    async def start_screencast(self, page, seconds: Optional[float] = None) -> None:
        """Mirror this page into the dashboard's Live View. seconds=None: until stop."""
        if page is None or page.is_closed():
            return
        if seconds:
            self._cast_until[page] = time.time() + seconds
        else:
            self._cast_until[page] = float("inf")
        if page in self._casts:
            return
        try:
            cdp = await page.context.new_cdp_session(page)
        except Exception as e:
            logger.debug("screencast unavailable: %s", e)
            return
        self._casts[page] = cdp

        def on_frame(params: Dict[str, Any]) -> None:
            asyncio.ensure_future(self._on_frame(page, cdp, params))

        cdp.on("Page.screencastFrame", on_frame)
        page.on("close", lambda *_: self._casts.pop(page, None))
        await cdp.send("Page.startScreencast", {"format": "jpeg", "quality": 62, "maxWidth": 1280, "maxHeight": 800, "everyNthFrame": 1})
        await self.snapshot(page)

    async def _on_frame(self, page, cdp, params: Dict[str, Any]) -> None:
        try:
            await cdp.send("Page.screencastFrameAck", {"sessionId": params.get("sessionId")})
        except Exception:
            return
        if time.time() > self._cast_until.get(page, 0):
            await self.stop_screencast(page)
            return
        now = time.time()
        if now - self._last_frame_at < 0.18:  # ~5 fps is plenty to follow along
            return
        self._last_frame_at = now
        meta = {"url": page.url}
        try:
            meta["title"] = await page.title()
        except Exception:
            pass
        await live_broadcaster.push_frame(params.get("data", ""), meta)

    async def stop_screencast(self, page) -> None:
        cdp = self._casts.pop(page, None)
        self._cast_until.pop(page, None)
        if cdp is not None:
            try:
                await cdp.send("Page.stopScreencast")
                await cdp.detach()
            except Exception:
                pass

    async def snapshot(self, page=None) -> bool:
        """Push one still frame (screencast only sends frames when the page changes)."""
        try:
            page = page or await self.current_page()
            if page is None or page.is_closed():
                return False
            raw = await page.screenshot(type="jpeg", quality=60, timeout=8000)
            meta = {"url": page.url}
            try:
                meta["title"] = await page.title()
            except Exception:
                pass
            await live_broadcaster.push_frame(base64.b64encode(raw).decode("ascii"), meta)
            return True
        except Exception as e:
            logger.debug("snapshot: %s", e)
            return False

    async def peek(self, seconds: float = 90) -> Dict[str, Any]:
        """Let the user look at whatever the Ashzo Browser shows right now."""
        if not self.is_connected():
            if not await self._port_alive():
                return {"running": False}
            await self.ensure()
        page = await self.current_page()
        if page is None:
            return {"running": True, "page": None}
        await self.start_screencast(page, seconds=seconds)
        return {"running": True, "page": page.url}

    async def status(self) -> Dict[str, Any]:
        running = self.is_connected() or await self._port_alive()
        page = await self.current_page() if self.is_connected() else None
        return {
            "running": running,
            "visible": self.visible,
            "port": self.port,
            "page": page.url if page else None,
            "chrome": self.executable or find_chrome(),
            # Set in the Docker image: the browser runs on a virtual screen, viewable here (noVNC).
            "viewer_url": os.environ.get("ASHZO_VIEWER_URL") or None,
        }

    async def storage_state(self) -> Dict[str, Any]:
        ctx = await self.ensure()
        return await ctx.storage_state()


hub = BrowserHub()
