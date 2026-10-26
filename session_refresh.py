"""
Fast Path self-repair: renew a site's session from the Ashzo Browser.

When a direct API call (Tier 1) is refused because the session went stale, this opens the site's
page in a background tab of the Ashzo Browser (your signed-in Chrome profile). The site renews
its own cookies the way it normally does. While the page loads, the headers the site itself sends
to that API (for example a fresh `Authorization` token) are noted. Then:

- the renewed cookies are saved to flow_auth_state.json (and the active account);
- the headers are kept in memory only (15 minutes), never written to disk;
- the Fast Path retries with them.

This only reuses your own signed-in browser session. It never solves CAPTCHAs or gets around
anti-bot checks: if the site wants a person, the call falls back to the browser tiers and says so.
"""

from __future__ import annotations

import asyncio
import json
import logging
import time
from pathlib import Path
from typing import Any, Dict, Optional
from urllib.parse import urlparse

from live_events import live_broadcaster

logger = logging.getLogger("AshzoMCP.SessionRefresh")

BASE_DIR = Path(__file__).resolve().parent
AUTH_STATE_FILE = BASE_DIR / "flow_auth_state.json"
HEADER_TTL = 15 * 60
SKIP_HEADERS = {"cookie", "host", "content-length", "accept-encoding", "connection", "content-type"}

_route_headers: Dict[str, Dict[str, Any]] = {}   # "METHOD:host/path" -> {"headers", "at"}
_host_headers: Dict[str, Dict[str, Any]] = {}    # host -> auth-like headers seen most recently
_locks: Dict[str, asyncio.Lock] = {}


def route_key(method: str, url: str) -> str:
    u = urlparse(url)
    return f"{method.upper()}:{u.netloc}{u.path}"


def fresh_headers(method: str, url: str) -> Dict[str, str]:
    """Headers captured from the site's own recent request to this API (memory only)."""
    now = time.time()
    hit = _route_headers.get(route_key(method, url))
    if hit and now - hit["at"] < HEADER_TTL:
        return dict(hit["headers"])
    host = _host_headers.get(urlparse(url).netloc)
    if host and now - host["at"] < HEADER_TTL:
        return dict(host["headers"])
    return {}


def _auth_like(name: str) -> bool:
    n = name.lower()
    return n == "authorization" or any(t in n for t in ("token", "csrf", "xsrf", "api-key", "auth", "session", "x-goog"))


def guess_page_url(api_url: str) -> str:
    """Where to open the site when the route doesn't say (api.example.com -> https://example.com/)."""
    u = urlparse(api_url)
    host = u.netloc
    for prefix in ("api.", "apis.", "graphql.", "gql."):
        if host.startswith(prefix) and host.count(".") >= 2:
            host = host[len(prefix):]
            break
    return f"{u.scheme or 'https'}://{host}/"


def _save_state(state: Dict[str, Any]) -> int:
    AUTH_STATE_FILE.write_text(json.dumps(state, indent=2), encoding="utf-8")
    try:
        from session_manager import session_manager
        active = session_manager.get_active_session() or {}
        auth_file = active.get("auth_file")
        if auth_file:
            Path(auth_file).parent.mkdir(parents=True, exist_ok=True)
            Path(auth_file).write_text(json.dumps(state, indent=2), encoding="utf-8")
    except Exception as e:
        logger.debug("active session not updated: %s", e)
    return len(state.get("cookies", []))


async def refresh_site_session(api_url: str, method: str = "GET", page_url: Optional[str] = None,
                               reason: str = "") -> Dict[str, Any]:
    """Renew cookies (and note fresh request headers) for the site behind api_url."""
    host = urlparse(api_url).netloc
    lock = _locks.setdefault(host, asyncio.Lock())
    async with lock:
        target = page_url or guess_page_url(api_url)
        want = route_key(method, api_url)
        await live_broadcaster.broadcast(
            "fast_path", f"Fast Path: {host} {reason or 'refused the saved session'}. Renewing it in the Ashzo Browser…",
            data={"host": host, "phase": "refreshing"})
        page = None
        captured = {"route": False}
        try:
            from browser_hub import hub
            ctx = await hub.ensure()

            async def on_request(request) -> None:
                try:
                    if urlparse(request.url).netloc != host:
                        return
                    hdrs = await request.all_headers()
                    keep = {k: v for k, v in hdrs.items() if k.lower() not in SKIP_HEADERS and not k.startswith(":")}
                    now = time.time()
                    auth = {k: v for k, v in keep.items() if _auth_like(k)}
                    if auth:
                        _host_headers[host] = {"headers": auth, "at": now}
                    if route_key(request.method, request.url) == want:
                        _route_headers[want] = {"headers": keep, "at": now}
                        captured["route"] = True
                except Exception:
                    pass

            page = await ctx.new_page()
            page.on("request", on_request)
            await page.goto(target, wait_until="domcontentloaded", timeout=30000)
            deadline = time.time() + 8
            while time.time() < deadline and not captured["route"]:
                await asyncio.sleep(0.5)
            try:
                await page.wait_for_load_state("networkidle", timeout=3000)
            except Exception:
                pass
            final_url = page.url
            state = await ctx.storage_state()
            count = _save_state(state)
            on_login = any(k in final_url.lower() for k in ("/login", "/signin", "/sign-in", "accounts.google.com", "/auth/"))
            result = {"refreshed": not on_login, "cookies": count, "captured_headers": bool(fresh_headers(method, api_url)),
                      "page": final_url, "needs_sign_in": on_login}
            msg = (f"Fast Path: {host} needs you to sign in again (press Connect)." if on_login
                   else f"Fast Path: renewed the session for {host}" + (" and picked up its fresh request headers." if result["captured_headers"] else "."))
            await live_broadcaster.broadcast("fast_path", msg, data={"host": host, "phase": "needs_sign_in" if on_login else "refreshed"})
            return result
        except Exception as e:
            logger.warning("session refresh for %s failed: %s", host, e)
            await live_broadcaster.broadcast("fast_path", f"Fast Path: couldn't renew the session for {host} ({e}).",
                                             data={"host": host, "phase": "error"})
            return {"refreshed": False, "error": str(e)}
        finally:
            if page is not None:
                try:
                    others = [p for p in page.context.pages if p is not page and not p.is_closed()]
                    if others:
                        await page.close()
                    else:  # never close the last tab: that would close the Ashzo Browser window
                        await page.goto("about:blank")
                except Exception:
                    pass
