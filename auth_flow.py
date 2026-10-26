"""
Account sign-in for Ashzo MCP (Google, Google Flow, GitHub, X, or any site).

How it works now:
  1. The dashboard calls start_login(); it returns at once with a job id.
  2. The site opens in the Ashzo Browser (a real Chrome window, see browser_hub),
     so Google sign-in is allowed and you can see exactly what is happening.
  3. Each step is published live (event type "auth"): opening, waiting for you,
     signed in, saved, or timed out / cancelled / failed with the reason.
  4. When the sign-in is detected, the session (cookies + storage) is saved as an
     account in sessions.json and set active. The browser keeps you signed in too.

run_interactive_login() is kept for the MCP tool: it starts a job and waits for it.
"""

from __future__ import annotations

import asyncio
import json
import logging
import os
import sys
import time
import uuid
from pathlib import Path
from typing import Any, Dict, Optional
from urllib.parse import urlparse

from ashzo_settings import load_settings
from browser_hub import BrowserLaunchError, hub
from live_events import live_broadcaster
from session_manager import session_manager

logger = logging.getLogger("AshzoMCP.AuthFlow")

BASE_DIR = Path(__file__).resolve().parent
AUTH_STATE_FILE = BASE_DIR / "flow_auth_state.json"
SESSION_COOKIES_FILE = BASE_DIR / "session_cookies.json"

GOOGLE_AUTH_COOKIES = {"SID", "__Secure-1PSID", "__Secure-3PSID", "HSID", "SSID"}

_jobs: Dict[str, Dict[str, Any]] = {}
_current: Optional[str] = None


def _host_matches(cookie_domain: str, host: str) -> bool:
    d = (cookie_domain or "").lstrip(".").lower()
    h = (host or "").lower().split(":")[0]  # cookies ignore ports
    return bool(d) and (h == d or h.endswith("." + d) or d.endswith("." + h))


def _is_signed_in(domain: str, url: str, cookies: list) -> bool:
    url_l = (url or "").lower()
    if "google" in domain or "google.com" in url_l:
        google = [c for c in cookies if c.get("name") in GOOGLE_AUTH_COOKIES and len(c.get("value", "")) > 15
                  and "google" in (c.get("domain") or "")]
        on_signin = "accounts.google.com" in url_l and ("signin" in url_l or "/v3/" in url_l or "challenge" in url_l)
        on_landing = "flow.google.com/about" in url_l
        return len(google) >= 2 and not on_signin and not on_landing
    if "github.com" in domain:
        return any(c.get("name") == "user_session" for c in cookies) and "/login" not in url_l
    host = urlparse(url).netloc or domain
    own = [c for c in cookies if _host_matches(c.get("domain", ""), host) or _host_matches(c.get("domain", ""), domain)]
    auth_like = [c for c in own if any(t in c.get("name", "").lower() for t in ("session", "auth", "token", "jwt", "sid"))]
    on_login = any(k in url_l for k in ("/login", "/signin", "/sign-in", "/auth/"))
    return bool(auth_like) and not on_login


async def _detect_email(page) -> Optional[str]:
    try:
        return await page.evaluate(r"""() => {
            const rx = /([a-zA-Z0-9._%+-]+@[a-zA-Z0-9.-]+\.[a-zA-Z]{2,})/;
            for (const el of document.querySelectorAll('[aria-label],[title],[data-email]')) {
                const s = (el.getAttribute('aria-label') || '') + ' ' + (el.getAttribute('title') || '') + ' ' + (el.getAttribute('data-email') || '');
                const m = s.match(rx);
                if (m) return m[1];
            }
            return null;
        }""")
    except Exception:
        return None


def _status(job: Dict[str, Any]) -> Dict[str, Any]:
    return {k: v for k, v in job.items() if not k.startswith("_")}


async def _publish(job: Dict[str, Any], phase: str, message: str, **extra: Any) -> None:
    job["phase"] = phase
    job["message"] = message
    job.update(extra)
    # Sign-in has its own live panel (the Connect dialog); it never takes over the generation HUD.
    await live_broadcaster.broadcast("auth", message, data={"kind": "login", **_status(job)})


async def _run(job: Dict[str, Any]) -> None:
    global _current
    domain = job["domain"]
    page = None
    try:
        await _publish(job, "opening", f"Opening {domain} in the Ashzo Browser…")
        try:
            page = await hub.open_page(job["target_url"], reuse_host=False, front=True)
        except BrowserLaunchError as e:
            await _publish(job, "error", str(e))
            return
        await hub.start_screencast(page)
        timeout = int(job["timeout"])
        deadline = time.time() + timeout
        job["deadline"] = int(deadline * 1000)
        where = ("the browser view tab (press \"Open browser view\" if it did not open)"
                 if os.environ.get("ASHZO_VIEWER_URL") else "the Chrome window that just opened")
        await _publish(job, "waiting", f"Sign in on {where}. This updates by itself.")

        signed_in = False
        while time.time() < deadline:
            if job.get("_cancel"):
                await _publish(job, "cancelled", "Sign-in cancelled.")
                return
            if page.is_closed():
                cookies = await page.context.cookies()
                signed_in = _is_signed_in(domain, job["target_url"], cookies)
                if not signed_in:
                    await _publish(job, "cancelled", "The sign-in tab was closed before you finished.")
                    return
                break
            cookies = await page.context.cookies()
            if _is_signed_in(domain, page.url, cookies):
                signed_in = True
                break
            await asyncio.sleep(1.5)

        if not signed_in:
            await _publish(job, "timeout", f"No sign-in after {timeout // 60} minutes. Press Try again when you're ready.")
            return

        await _publish(job, "saving", "Signed in. Saving your session…")
        await asyncio.sleep(1.5)  # let the site finish setting its cookies
        email = (await _detect_email(page)) if not page.is_closed() else None
        email = email or job.get("expected_email") or ""
        state = await page.context.storage_state()
        cookies_dict = {c["name"]: c["value"] for c in state.get("cookies", [])
                        if _host_matches(c.get("domain", ""), domain) or ("google" in domain and "google" in c.get("domain", ""))}
        AUTH_STATE_FILE.write_text(json.dumps(state, indent=2), encoding="utf-8")
        SESSION_COOKIES_FILE.write_text(json.dumps(cookies_dict, indent=2), encoding="utf-8")
        label = email or domain
        record = session_manager.add_session(
            name=job.get("session_name") or f"{domain} ({label})",
            email=email,
            domain=domain,
            cookies_dict=cookies_dict,
            storage_state_data=state,
            set_active=True,
        )
        await _publish(job, "success", f"Connected {label}.", session_id=record["id"], email=email,
                       cookies_captured=len(cookies_dict))
    except asyncio.CancelledError:
        await _publish(job, "cancelled", "Sign-in cancelled.")
    except Exception as e:  # never leave the dashboard spinning
        logger.exception("Login failed")
        await _publish(job, "error", f"Sign-in failed: {e}")
    finally:
        if page is not None:
            try:
                await hub.stop_screencast(page)
            except Exception:
                pass
        job["finished_at"] = int(time.time() * 1000)
        if _current == job["id"]:
            _current = None


async def start_login(target_url: str = "https://accounts.google.com/", expected_email: Optional[str] = None,
                      timeout_seconds: Optional[int] = None, session_name: Optional[str] = None) -> Dict[str, Any]:
    """Start a sign-in and return immediately. Progress arrives as live "auth" events."""
    global _current
    if _current and _jobs.get(_current, {}).get("phase") in ("opening", "waiting", "saving"):
        return {"status": "busy", "message": "A sign-in is already open in the Ashzo Browser.", "job": _status(_jobs[_current])}
    if not target_url.startswith(("http://", "https://")):
        target_url = "https://" + target_url
    domain = urlparse(target_url).netloc or "web"
    job = {
        "id": uuid.uuid4().hex[:10],
        "target_url": target_url,
        "domain": domain,
        "expected_email": (expected_email or "").strip(),
        "session_name": session_name,
        "timeout": int(timeout_seconds or load_settings().get("login_timeout_seconds", 300)),
        "phase": "starting",
        "message": "Starting…",
        "started_at": int(time.time() * 1000),
    }
    _jobs[job["id"]] = job
    _current = job["id"]
    job["_task"] = asyncio.create_task(_run(job))
    return {"status": "started", "job": _status(job)}


async def cancel_login(job_id: Optional[str] = None) -> Dict[str, Any]:
    jid = job_id or _current
    job = _jobs.get(jid or "")
    if not job:
        return {"status": "none"}
    job["_cancel"] = True
    return {"status": "cancelling", "job": _status(job)}


def login_status(job_id: Optional[str] = None) -> Dict[str, Any]:
    jid = job_id or _current
    if jid and jid in _jobs:
        return _status(_jobs[jid])
    if _jobs:
        return _status(list(_jobs.values())[-1])
    return {"phase": "idle"}


async def run_interactive_login(target_url: str = "https://accounts.google.com/", timeout_seconds: int = 300,
                                session_name: Optional[str] = None, expected_email: Optional[str] = None) -> Dict[str, Any]:
    """Blocking variant for MCP tools and the command line: start a sign-in and wait for its result."""
    started = await start_login(target_url, expected_email, timeout_seconds, session_name)
    if started.get("status") == "busy":
        return started
    job = _jobs[started["job"]["id"]]
    await job["_task"]
    result = _status(job)
    result["status"] = {"success": "success", "timeout": "timeout", "cancelled": "cancelled"}.get(job["phase"], "error")
    return result


def main() -> None:
    target = sys.argv[1] if len(sys.argv) > 1 else "https://accounts.google.com/"
    email = sys.argv[2] if len(sys.argv) > 2 else None
    res = asyncio.run(run_interactive_login(target_url=target, expected_email=email))
    sys.stderr.write(json.dumps(res, indent=2) + "\n")


if __name__ == "__main__":
    main()
