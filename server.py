"""
Universal-Web-MCP: 3-Tier Hybrid Routing Web Bridge.
Allows AI agents (Claude Desktop, Cursor, etc.) to interact with ANY website at sub-second speeds.

Tier 1: Fast Path - Direct JSON/GraphQL replay using stored session cookies (<200ms).
Tier 2: Auto-Discovery Path - CDP network listener that learns APIs and schemas on the fly.
Tier 3: Universal Fallback - Clean Markdown and Accessibility Tree extraction from DOM (<1000 tokens).
"""

import os
import sys
import json
import time
import asyncio
import logging
from typing import Dict, List, Any, Optional
from pathlib import Path
from urllib.parse import urlparse

import httpx

# FastMCP compatibility across mcp 1.x and 2.x
try:
    from mcp.server.fastmcp import FastMCP
except (ImportError, ModuleNotFoundError):
    from mcp.server.mcpserver import MCPServer as FastMCP

from cookie_sync import ChromeProfileManager, mask_headers, mask_secret
from interceptor import NetworkInterceptor, LearnedRoute, infer_json_schema, summarize_payload
from fallback import FallbackDOMReader
from live_events import live_broadcaster
from auth_flow import run_interactive_login

# Configure Logging
logging.basicConfig(
    level=logging.INFO,
    stream=sys.stderr,  # stdout belongs to the MCP stdio protocol
    format="[%(asctime)s] [%(levelname)s] [%(name)s] %(message)s"
)
logger = logging.getLogger("UniversalWebMCP.Server")

# File paths
BASE_DIR = Path(__file__).resolve().parent
ROUTES_CACHE_FILE = BASE_DIR / "learned_routes.json"
SESSION_COOKIES_FILE = BASE_DIR / "session_cookies.json"

# Initialize FastMCP Server
mcp = FastMCP("Universal-Web-Bridge")

# In-chat cards (MCP Apps: Claude desktop/web, ChatGPT, VS Code, ...). Older MCP libraries: plain text only.
try:
    from mcp.server.apps import Apps, ResourceCsp
    _apps = Apps()
except Exception:  # mcp < 2.3
    Apps = ResourceCsp = None
    _apps = None
FLOW_CARD_URI = "ui://ashzo/flow-card.html"


def ui_tool(visibility=None):
    """A tool that also shows the live Flow card in chats that can display MCP Apps."""
    if _apps is None:
        return mcp.tool()
    return _apps.tool(resource_uri=FLOW_CARD_URI, visibility=visibility)


def activity(tool_name: str):
    """Publish every tool call to the dashboard's live feed (start, result, time taken)."""
    import functools
    import inspect
    from live_events import live_broadcaster

    def preview(kwargs: Dict[str, Any]) -> str:
        parts = []
        for k, v in kwargs.items():
            if v in (None, "", {}, []):
                continue
            text = str(v)
            if any(s in k.lower() for s in ("token", "cookie", "password", "secret", "body")):
                text = "•••"
            parts.append(f"{k}={text[:80]}")
        return ", ".join(parts)[:220]

    def deco(fn):
        if inspect.iscoroutinefunction(fn):
            @functools.wraps(fn)
            async def wrapper(*args, **kwargs):
                t0 = time.perf_counter()
                bound = inspect.signature(fn).bind_partial(*args, **kwargs).arguments
                await live_broadcaster.broadcast("agent", f"{tool_name}({preview(bound)})", data={"tool": tool_name, "phase": "start"})
                try:
                    res = await fn(*args, **kwargs)
                    ms = round((time.perf_counter() - t0) * 1000)
                    summary = ""
                    if isinstance(res, dict):
                        summary = str(res.get("tier") or res.get("status") or res.get("message") or "")[:120]
                    await live_broadcaster.broadcast("agent", f"{tool_name} finished in {ms} ms {('· ' + summary) if summary else ''}",
                                                     data={"tool": tool_name, "phase": "done", "ok": True, "ms": ms})
                    return res
                except Exception as e:
                    await live_broadcaster.broadcast("agent", f"{tool_name} failed: {e}", data={"tool": tool_name, "phase": "done", "ok": False})
                    raise
            return wrapper

        @functools.wraps(fn)
        def sync_wrapper(*args, **kwargs):
            t0 = time.perf_counter()
            res = fn(*args, **kwargs)
            live_broadcaster.emit("agent", f"{tool_name} finished in {round((time.perf_counter() - t0) * 1000)} ms",
                                  data={"tool": tool_name, "phase": "done", "ok": True})
            return res
        return sync_wrapper
    return deco

# Core state managers
cookie_manager = ChromeProfileManager(storage_path=str(SESSION_COOKIES_FILE))
interceptor = NetworkInterceptor(headless=True)
fallback_reader = FallbackDOMReader(headless=True)

# Shared HTTP client for Tier 1 fast-path keepalive
http_client: Optional[httpx.AsyncClient] = None


def get_http_client() -> httpx.AsyncClient:
    """Returns a shared httpx.AsyncClient with keepalive connection pooling."""
    global http_client
    if http_client is None or http_client.is_closed:
        http_client = httpx.AsyncClient(
            timeout=10.0,
            follow_redirects=True,
            limits=httpx.Limits(max_keepalive_connections=20, max_connections=50)
        )
    return http_client


class RouteCache:
    """Manages persistent caching of discovered API routes and schemas."""

    def __init__(self, cache_file: Path):
        self.cache_file = cache_file
        self.routes: Dict[str, Dict[str, Any]] = {}
        self.load()

    def _normalize_key(self, method: str, url: str) -> str:
        parsed = urlparse(url)
        return f"{method.upper()}:{parsed.netloc}{parsed.path}"

    def load(self):
        if self.cache_file.exists():
            try:
                with open(self.cache_file, "r", encoding="utf-8") as f:
                    self.routes = json.load(f)
                logger.info(f"Loaded {len(self.routes)} cached routes from {self.cache_file}")
            except Exception as e:
                logger.warning(f"Error loading routes cache: {e}")
                self.routes = {}

    def save(self):
        try:
            with open(self.cache_file, "w", encoding="utf-8") as f:
                json.dump(self.routes, f, indent=2)
            logger.info(f"Saved {len(self.routes)} routes to {self.cache_file}")
        except Exception as e:
            logger.error(f"Error saving routes cache: {e}")

    def get_route(self, method: str, url: str) -> Optional[Dict[str, Any]]:
        key = self._normalize_key(method, url)
        if key in self.routes:
            return self.routes[key]
        # Same site, same method, longest matching path prefix (only its headers are reused; the URL asked for is
        # always the one requested, so a near match can never return another page's data).
        parsed = urlparse(url)
        best, best_len = None, -1
        for route in self.routes.values():
            rpath = urlparse(route.get("url", "")).path or "/"
            if route.get("domain") == parsed.netloc and (route.get("method") or "GET").upper() == method.upper() \
                    and parsed.path.startswith(rpath) and len(rpath) > best_len:
                best, best_len = route, len(rpath)
        return best

    # Route health: a route that keeps being refused rests for a while, then is tried again.
    def mark_ok(self, route_id: Optional[str]) -> None:
        r = self.routes.get(route_id or "")
        if r and (r.get("fail_streak") or r.get("paused_until")):
            r.update({"fail_streak": 0, "paused_until": None, "paused_at": None, "last_error": None})
            r["last_ok_at"] = time.strftime("%Y-%m-%d %H:%M:%S")
            self.save()

    def mark_failed(self, route_id: Optional[str], reason: str, limit: int = 3, rest_seconds: int = 1800) -> Optional[float]:
        r = self.routes.get(route_id or "")
        if not r:
            return None
        r["fail_streak"] = int(r.get("fail_streak") or 0) + 1
        r["last_error"] = reason
        if r["fail_streak"] >= limit:
            r["paused_until"] = time.time() + rest_seconds
            r["paused_at"] = time.time()
            r["fail_streak"] = 0
        self.save()
        return r.get("paused_until") if (r.get("paused_until") or 0) > time.time() else None

    def paused_until(self, route: Optional[Dict[str, Any]]) -> Optional[float]:
        until = (route or {}).get("paused_until")
        if not until or until <= time.time():
            return None
        try:  # signing in again (Connect) ends the rest at once
            if (BASE_DIR / "flow_auth_state.json").stat().st_mtime > float(route.get("paused_at") or 0):
                return None
        except OSError:
            pass
        return until

    def _merge(self, route: LearnedRoute) -> bool:
        new = route.model_dump()
        if int(new.get("status_code") or 200) >= 400:
            return False  # a refused call is not a route worth replaying
        old = self.routes.get(route.id) or {}
        for keep in ("fail_streak", "paused_until", "paused_at", "last_error", "last_ok_at"):
            if old.get(keep) is not None:
                new[keep] = old[keep]
        # keep the real page the API was seen on (a sniff of the API address itself isn't a page)
        if old.get("page_url") and (not new.get("page_url") or new.get("page_url", "").split("?")[0] == new.get("url")):
            new["page_url"] = old["page_url"]
        self.routes[route.id] = new
        return True

    def add_route(self, route: LearnedRoute):
        if self._merge(route):
            self.save()

    def add_routes(self, routes: List[LearnedRoute]):
        if any([self._merge(r) for r in routes]):
            self.save()

    def list_routes(self, domain_filter: Optional[str] = None) -> List[Dict[str, Any]]:
        if not domain_filter:
            return list(self.routes.values())
        return [r for r in self.routes.values() if domain_filter.lower() in r.get("domain", "").lower()]

    def clear(self, domain_filter: Optional[str] = None):
        if domain_filter:
            self.routes = {k: v for k, v in self.routes.items() if domain_filter.lower() not in v.get("domain", "").lower()}
        else:
            self.routes = {}
        self.save()


route_cache = RouteCache(ROUTES_CACHE_FILE)


BROWSER_UA = "Mozilla/5.0 (Windows NT 10.0; Win64; x64) AppleWebKit/537.36 (KHTML, like Gecko) Chrome/126.0.0.0 Safari/537.36"
SECRET_HEADER_NAMES = ("cookie", "host", "content-length", "authorization", "proxy-authorization", "x-api-key",
                       "x-goog-api-key", "token", "x-auth-token")
FAST_PATH_MAX_TRIES = 5        # per call, all reasons together
FAST_PATH_MAX_REFRESHES = 2    # session renewals per call


def _fast_path_headers(url: str, method: str, learned: Optional[Dict[str, Any]]) -> Dict[str, str]:
    from session_refresh import fresh_headers
    headers = {"User-Agent": BROWSER_UA, "Accept": "application/json, text/plain, */*"}
    if learned and "headers" in learned:
        for hk, hv in learned["headers"].items():
            if hk.lower() in SECRET_HEADER_NAMES or hk.startswith(":") or "…" in str(hv) or "***" in str(hv):
                continue  # secrets were masked when saved
            headers[hk] = hv
    headers.update(fresh_headers(method, url))  # the site's own fresh headers, if a renewal caught them
    cookie_header = cookie_manager.get_cookie_header(urlparse(url).hostname)  # re-read: a renewal updates it
    if cookie_header:
        headers["Cookie"] = cookie_header
    return headers


def _wants_sign_in(resp: httpx.Response) -> bool:
    if resp.status_code in (401, 403, 419, 440):
        return True
    final = str(resp.url).lower()
    if any(k in final for k in ("/login", "/signin", "/sign-in", "accounts.google.com", "/auth/", "/session/new")):
        return True
    ctype = resp.headers.get("content-type", "").lower()
    if resp.is_success and "html" in ctype:
        head = resp.text[:4000].lower()
        return 'type="password"' in head or "sign in" in head or "log in" in head
    return False


async def _fast_path(url: str, method: str, params: Optional[Dict[str, Any]], body: Optional[Dict[str, Any]],
                     learned: Optional[Dict[str, Any]], notes: List[str], start_time: float) -> Optional[Dict[str, Any]]:
    """Tier 1 with retries. Returns the answer, or None to fall back (reasons are added to notes)."""
    from session_refresh import refresh_site_session
    client = get_http_client()
    refreshes = 0
    backoff = 0.6
    route_id = (learned or {}).get("id")
    gave_up = None
    for attempt in range(1, FAST_PATH_MAX_TRIES + 1):
        logger.info(f"[Tier 1 Fast Path] try {attempt} {method} {url}")
        try:
            resp = await client.request(method=method, url=url, params=params or None,
                                        json=body if method in ("POST", "PUT", "PATCH") else None,
                                        headers=_fast_path_headers(url, method, learned))
        except (httpx.TimeoutException, httpx.TransportError) as e:
            notes.append(f"try {attempt}: network problem ({e.__class__.__name__}), retrying")
            await asyncio.sleep(backoff)
            backoff = min(backoff * 2.5, 8)
            continue

        if resp.status_code == 429 or resp.status_code >= 500:
            try:
                wait = float(resp.headers.get("retry-after", backoff))
            except ValueError:
                wait = backoff
            notes.append(f"try {attempt}: site busy ({resp.status_code}), waiting {min(wait, 10):.1f}s")
            await asyncio.sleep(min(wait, 10))
            backoff = min(backoff * 2.5, 8)
            continue

        if _wants_sign_in(resp):
            if refreshes >= FAST_PATH_MAX_REFRESHES:
                gave_up = f"still refused ({resp.status_code}) after renewing the session {refreshes}x"
                break
            refreshes += 1
            notes.append(f"try {attempt}: session refused ({resp.status_code}), renewing it from the Ashzo Browser")
            r = await refresh_site_session(url, method, page_url=(learned or {}).get("page_url") or None,
                                           reason=f"answered {resp.status_code}")
            if r.get("needs_sign_in"):
                gave_up = "the site wants you to sign in again: press Connect in the dashboard"
                break
            if not r.get("refreshed"):
                gave_up = f"couldn't renew the session ({r.get('error', 'unknown reason')})"
                break
            continue

        if resp.is_success:
            try:
                data = resp.json()
            except Exception:
                gave_up = "this address doesn't return JSON (it's a web page), so it can't use the Fast Path"
                break
            elapsed_ms = round((time.perf_counter() - start_time) * 1000, 2)
            route_cache.mark_ok(route_id)
            out = {
                "tier": "Tier 1 (Fast Path)",
                "latency_ms": elapsed_ms,
                "status_code": resp.status_code,
                "url": str(resp.url),
                "data": summarize_payload(data),
                "message": f"Answered directly by the site's API in {elapsed_ms}ms",
            }
            if notes:
                out["recovered_after"] = notes
            if refreshes:
                out["session_renewed"] = True
            return out

        gave_up = f"the site answered {resp.status_code}, which retrying won't fix"
        break
    else:
        gave_up = f"no answer after {FAST_PATH_MAX_TRIES} tries"

    notes.append(f"gave up: {gave_up}")
    paused = route_cache.mark_failed(route_id, gave_up)
    if paused:
        notes.append(f"Fast Path for this API rests until {time.strftime('%H:%M', time.localtime(paused))}; the browser tiers answer meanwhile.")
    await live_broadcaster.broadcast("fast_path", f"Fast Path: {urlparse(url).netloc} {gave_up}. Using the browser instead.",
                                     data={"url": url, "phase": "fallback"})
    return None


# --- MCP Tools ---

@mcp.tool()
@activity("authenticate_session")
async def authenticate_session(
    target_url: str = "https://flow.google.com/",
    timeout_seconds: int = 300
) -> Dict[str, Any]:
    """
    Opens the site in the Ashzo Browser (a real, visible Chrome window) so the user can sign in once.
    Progress is shown live in the dashboard. The session is saved and set active, and the browser
    stays signed in for later jobs. Tell the user to sign in on the Chrome window that opens.

    Args:
        target_url: The URL to sign into (default: https://flow.google.com/).
        timeout_seconds: How long to wait for the user to finish signing in (default: 300).
    """
    res = await run_interactive_login(target_url=target_url, timeout_seconds=timeout_seconds)
    # Reload cookies into manager
    cookie_manager.load_stored_cookies()
    return res


@mcp.tool()
@activity("universal_request")
async def universal_request(
    url: str,
    method: str = "GET",
    params: Optional[Dict[str, Any]] = None,
    body: Optional[Dict[str, Any]] = None,
    force_tier: Optional[int] = None
) -> Dict[str, Any]:
    """
    Executes a web request using the 3-Tier Hybrid Routing Architecture:
    - Tier 1 (Fast Path): Calls the site's own JSON API directly with your saved session. Retries by itself:
      waits out busy/network errors, and if the session is refused it renews it from the Ashzo Browser
      (fresh cookies + the site's own fresh request headers) and tries again before falling back.
    - Tier 2 (Auto-Discovery): Uses Playwright CDP network sniffer to learn endpoints & schemas.
    - Tier 3 (Fallback): Extracts token-efficient Markdown / Accessibility tree (<1000 tokens).

    Args:
        url: Target website or API URL.
        method: HTTP method (GET, POST, etc.).
        params: Optional query parameters.
        body: Optional request JSON body.
        force_tier: Force execution tier: 1 (Fast Path), 2 (Auto-Discovery), or 3 (DOM Fallback).
    """
    start_time = time.perf_counter()
    target_method = method.upper()

    # -------------------------------------------------------------
    # TIER 1: FAST PATH (direct API call), self-repairing:
    #   network error / 429 / 5xx  -> wait and retry (backoff, Retry-After)
    #   401 / 403 / sign-in page   -> renew the site's session in the Ashzo Browser, retry
    #   still refused after that   -> fall back to Tier 2/3; after 3 such calls in a row the
    #                                 route rests for 30 minutes, then the Fast Path is tried again
    # -------------------------------------------------------------
    learned = route_cache.get_route(target_method, url)
    fast_path_notes: List[str] = []
    paused = route_cache.paused_until(learned)
    if paused and force_tier != 1:
        fast_path_notes.append(f"Fast Path resting until {time.strftime('%H:%M', time.localtime(paused))} after repeated refusals.")
    elif (learned or force_tier == 1) and force_tier not in (2, 3):
        result = await _fast_path(url, target_method, params, body, learned, fast_path_notes, start_time)
        if result is not None:
            return result

    # -------------------------------------------------------------
    # TIER 2: AUTO-DISCOVERY PATH (Playwright CDP Network Sniffer)
    # -------------------------------------------------------------
    if force_tier != 3:
        logger.info(f"[Tier 2 Auto-Discovery] Running CDP sniffer on {url}")
        try:
            sniff_res = await interceptor.sniff_url(url=url, timeout_ms=15000)
            
            # Sync any new cookies intercepted during navigation
            if sniff_res.get("cookies"):
                cookie_manager.sync_from_playwright_cookies(sniff_res["cookies"])

            routes = sniff_res.get("routes", [])
            if routes:
                route_cache.add_routes(routes)
                elapsed_ms = round((time.perf_counter() - start_time) * 1000, 2)
                best_route = routes[0]
                return {
                    "tier": "Tier 2 (Auto-Discovery Path)",
                    "latency_ms": elapsed_ms,
                    "url": sniff_res["final_url"],
                    "title": sniff_res["title"],
                    "discovered_routes_count": len(routes),
                    "compiled_route_id": best_route.id,
                    "schema": best_route.response_schema,
                    "data": best_route.sample_response,
                    "message": f"Learned {len(routes)} new API endpoint(s) and compiled into permanent MCP cache.",
                    **({"fast_path_attempts": fast_path_notes} if fast_path_notes else {}),
                }
        except Exception as e:
            logger.warning(f"[Tier 2 Discovery Error]: {e}. Falling back to Tier 3.")

    # -------------------------------------------------------------
    # TIER 3: UNIVERSAL FALLBACK (Clean Markdown & Accessibility Tree)
    # -------------------------------------------------------------
    logger.info(f"[Tier 3 Fallback] Extracting clean DOM & Accessibility Tree for {url}")
    elapsed_ms = round((time.perf_counter() - start_time) * 1000, 2)
    fallback_res = await fallback_reader.extract_content(url=url, mode="both")
    fallback_res["latency_ms"] = round((time.perf_counter() - start_time) * 1000, 2)
    fallback_res["message"] = "No clean first-party JSON API available. Fallback to clean Markdown & Accessibility tree (<1000 tokens)."
    if fast_path_notes:
        fallback_res["fast_path_attempts"] = fast_path_notes
    return fallback_res


@mcp.tool()
@activity("discover_routes")
async def discover_routes(url: str, interactive_action: Optional[str] = None) -> Dict[str, Any]:
    """
    Explicitly runs Tier 2 Auto-Discovery on a target URL using Playwright CDP sniffer.
    Captures background JSON traffic, generates schemas, updates session cookies,
    and caches endpoints to learned_routes.json.

    Args:
        url: The web page URL to inspect.
        interactive_action: Optional JavaScript string to evaluate on page (e.g., 'window.scrollTo(0, 1000)').
    """
    res = await interceptor.sniff_url(url=url, interactive_action=interactive_action)
    if res.get("cookies"):
        cookie_manager.sync_from_playwright_cookies(res["cookies"])
    routes = res.get("routes", [])
    if routes:
        route_cache.add_routes(routes)

    return {
        "status": "success",
        "url": res["final_url"],
        "title": res["title"],
        "discovered_endpoints": [
            {
                "id": r.id,
                "method": r.method,
                "url": r.url,
                "query_params": r.query_params,
                "schema": r.response_schema
            }
            for r in routes
        ],
        "count": len(routes)
    }


@mcp.tool()
@activity("get_page_content")
async def get_page_content(url: str, mode: str = "both") -> Dict[str, Any]:
    """
    Tier 3 Fallback: Extracts clean, token-efficient Markdown or Accessibility Tree snapshots.
    Guarantees <1,000 tokens output by filtering CSS, scripts, and tracking markup.

    Args:
        url: Web URL to extract.
        mode: Extraction format: 'markdown', 'accessibility', or 'both'.
    """
    return await fallback_reader.extract_content(url=url, mode=mode)


@mcp.tool()
def sync_chrome_session(profile_name_or_email: str = "Default") -> Dict[str, Any]:
    """
    Synchronizes session cookies from a local Google Chrome profile for Tier 1 Fast Path requests.

    Args:
        profile_name_or_email: Chrome profile folder (e.g. 'Default', 'Profile 1') or the account email of that profile.
    """
    # 1. Resolve profile directory
    resolved_profile = cookie_manager.find_profile_by_email(profile_name_or_email)
    if not resolved_profile:
        resolved_profile = profile_name_or_email

    # 2. Extract cookies from SQLite if browser is idle
    extracted = cookie_manager.extract_cookies_from_sqlite(resolved_profile)
    if extracted:
        cookie_manager.cached_cookies.update(extracted)
        cookie_manager.save_stored_cookies()

    return {
        "status": "success",
        "target": profile_name_or_email,
        "resolved_profile": resolved_profile,
        "total_cookies_cached": len(cookie_manager.cached_cookies),
        "masked_sample": {
            k: mask_secret(v) for k, v in list(cookie_manager.cached_cookies.items())[:5]
        }
    }


@mcp.tool()
def list_learned_routes(domain: Optional[str] = None) -> List[Dict[str, Any]]:
    """
    Lists all learned API routes currently cached in learned_routes.json.

    Args:
        domain: Optional domain filter (e.g., 'google.com').
    """
    return route_cache.list_routes(domain_filter=domain)


@mcp.tool()
def validate_flow_prompt(
    prompt: str,
    model: str = "omni_flash",
    duration: int = 8,
    has_start_frame: bool = False,
    has_end_frame: bool = False
) -> Dict[str, Any]:
    """
    Validates a Google Flow video prompt, educates the user on model constraints,
    and returns a refined 4K photorealistic prompt adhering to camera, lighting, and lens physics.
    Supports Gemini Omni Flash (4s, 6s, 8s, 10s) and Veo 3.1 (8s).
    """
    from flow_video_automator import validate_and_educate_prompt
    return validate_and_educate_prompt(
        prompt=prompt,
        model=model,
        duration=duration,
        has_start_frame=has_start_frame,
        has_end_frame=has_end_frame
    )


@mcp.tool()
@activity("get_flow_account_credits")
async def get_flow_account_credits() -> Dict[str, Any]:
    """
    Reads the real Google Flow credit balance of the signed-in account (opens Flow in a hidden browser
    with the same sign-in). Returns status 'signed_out' or 'unknown' instead of guessing a number.
    """
    from get_live_flow_credits import fetch_live_google_flow_credits
    return await fetch_live_google_flow_credits()


def _stage_reference(path: Optional[str]) -> Optional[str]:
    """Copy a reference image into downloads/references so the dashboard can show it."""
    if not path:
        return None
    import shutil
    src = Path(path).expanduser()
    if not src.exists():
        raise FileNotFoundError(f"Reference image not found: {src}")
    ref_dir = BASE_DIR / "downloads" / "references"
    ref_dir.mkdir(parents=True, exist_ok=True)
    dst = ref_dir / f"{int(time.time())}_{src.name}"
    shutil.copy2(src, dst)
    return str(dst)


@ui_tool()
@activity("flow_generate_video")
async def flow_generate_video(
    prompt: str,
    model: str = "omni_flash",
    duration: str = "8",
    aspect_ratio: str = "9:16",
    download_quality: str = "1080p",
    starting_frame: Optional[str] = None,
    ending_frame: Optional[str] = None,
    starting_frame_image: Optional[str] = None,
    ending_frame_image: Optional[str] = None,
    slug: str = "video",
    wait: bool = False
) -> Dict[str, Any]:
    """
    Generates a video in Google Flow inside the visible Ashzo Browser. The user can watch every step
    live in the dashboard (Live View + Flow chat) at http://127.0.0.1:8000.

    Args:
        prompt: What to generate. For recreations, write it with VIDEO_RECREATION_SKILL.md.
        model: 'omni_flash' (4, 6, 8 or 10 s), 'veo_3_1' (up to 8 s) or 'gemini_omni'.
        duration: '4', '6', '8', '10' or '30s_ad' (four scenes).
        aspect_ratio: '9:16', '16:9' or '1:1'.
        download_quality: '720p', '1080p' or '4k' (Flow's download menu; falls back to the original file).
        starting_frame / ending_frame: names of Flow assets to use as first / last frame.
        starting_frame_image / ending_frame_image: paths of image files on this computer to attach as
            first / last frame (they also show as reference thumbnails on the dashboard card).
        slug: short name for the saved file.
        wait: True to wait until the video is saved; False returns at once with the job id.
    """
    from flow_video_automator import flow_jobs
    started = await flow_jobs.start({
        "prompt": prompt, "model": model, "duration": duration, "aspect_ratio": aspect_ratio,
        "download_quality": download_quality, "starting_frame": starting_frame,
        "ending_frame": ending_frame, "slug": slug, "source": "mcp-agent",
        "starting_frame_path": _stage_reference(starting_frame_image),
        "ending_frame_path": _stage_reference(ending_frame_image),
    }, BASE_DIR / "downloads" / "flow_production")
    if wait and started.get("status") == "started":
        return _compact_job(await flow_jobs.wait())
    return {"status": started.get("status"), "message": started.get("message"),
            "job": _compact_job(started.get("job") or {}),
            "next": "Call flow_job_status(wait_seconds=45) until state is ready/error/cancelled. The user can watch live in the dashboard."}


def _compact_job(job: Dict[str, Any]) -> Dict[str, Any]:
    """Small status for the agent (a few hundred tokens): the full card with frames and chat goes to the dashboard."""
    if not job or job.get("state") == "idle":
        return {"state": "idle"}
    chat = [c.get("text", "")[:200] for c in (job.get("chat") or [])[-3:]]
    return {
        "id": job.get("id"), "title": job.get("title"), "state": job.get("state"),
        "progress": job.get("progress"), "message": job.get("message"),
        "flow_said_last": chat or None,
        "files": [{"name": f.get("name"), "path": f.get("path"), "size_mb": f.get("size_mb")} for f in job.get("files") or []] or None,
    }


@mcp.tool()
async def flow_job_status(wait_seconds: int = 0) -> Dict[str, Any]:
    """
    Status of the current or last Flow generation (compact, no images).

    Args:
        wait_seconds: wait up to this long (max 55) for the job to finish or change state before answering.
            Use 45 while a video renders: a whole render then costs a handful of small calls.
    """
    import asyncio as _asyncio
    from flow_video_automator import flow_jobs
    terminal = ("ready", "error", "cancelled", "idle")
    start_state = flow_jobs.status().get("state")
    deadline = time.time() + max(0, min(int(wait_seconds or 0), 55))
    while time.time() < deadline:
        st = flow_jobs.status().get("state")
        if st in terminal or st != start_state:
            break
        await _asyncio.sleep(1)
    return _compact_job(flow_jobs.status())


@mcp.tool()
@activity("flow_cancel_job")
async def flow_cancel_job() -> Dict[str, Any]:
    """Cancels the running Flow generation."""
    from flow_video_automator import flow_jobs
    return await flow_jobs.cancel()


@mcp.tool()
@activity("study_video")
async def study_video(path: str, out_dir: Optional[str] = None) -> Dict[str, Any]:
    """
    Steps 1-4 of VIDEO_RECREATION_SKILL.md in one call: video properties, scene cuts, 1 fps contact
    sheets with timestamps, 2 fps hook and ending sheets, spectrogram, loudness per second, silences.
    ALWAYS run this before writing a recreation kit, then LOOK at every image it lists.

    Args:
        path: Path to the source video on this computer.
        out_dir: Optional folder for the results (default downloads/studies/<name>_<time>).
    """
    import asyncio as _asyncio
    from video_study import study_video as _study
    return await _asyncio.to_thread(_study, path, out_dir)


@mcp.tool()
@activity("open_live_view")
async def open_live_view() -> Dict[str, Any]:
    """
    Starts the Ashzo Browser if needed and mirrors it into the dashboard's Live View, so the user
    can watch your work. Returns the dashboard address to give the user.
    """
    from browser_hub import hub
    await hub.ensure()
    await hub.peek(120)
    return {"status": "ok", "dashboard": "http://127.0.0.1:8000", "browser": await hub.status()}


@mcp.tool()
def clear_cache(domain: Optional[str] = None) -> Dict[str, str]:
    """
    Clears cached routes and session state.

    Args:
        domain: Specific domain to purge, or None to purge all.
    """
    route_cache.clear(domain_filter=domain)
    return {"status": "success", "message": f"Cache cleared for: {domain or 'ALL'}"}


# --- Live Flow card in the chat (MCP Apps) ---
DASHBOARD_PORT = int(os.environ.get("ASHZO_PORT") or 8000)
VIDEO_PART_BYTES = 768 * 1024


def _thumb(url: Optional[str]) -> Optional[str]:
    """Small reference images go into the card inline (the card can't load files from disk)."""
    if not url or not url.startswith("/downloads/"):
        return None
    from urllib.parse import unquote
    import base64 as _b64
    path = (BASE_DIR / "downloads" / unquote(url[len("/downloads/"):])).resolve()
    try:
        if (BASE_DIR / "downloads").resolve() not in path.parents or path.stat().st_size > 400_000:
            return None
        mime = {".png": "image/png", ".webp": "image/webp", ".gif": "image/gif"}.get(path.suffix.lower(), "image/jpeg")
        return f"data:{mime};base64," + _b64.b64encode(path.read_bytes()).decode()
    except OSError:
        return None


def _card(job: Dict[str, Any]) -> Dict[str, Any]:
    from flow_video_automator import downloads_url
    base = f"http://127.0.0.1:{DASHBOARD_PORT}"
    files = []
    for f in job.get("files") or []:
        u = f.get("url") or (downloads_url(Path(f["path"])) if f.get("path") else None)
        files.append({"name": f.get("name"), "path": f.get("path"), "size_mb": f.get("size_mb"), "url": (base + u) if u else None})
    return {
        "id": job.get("id"), "title": job.get("title"), "state": job.get("state"), "progress": job.get("progress"),
        "message": job.get("message"), "prompt": job.get("prompt"), "model_label": job.get("model_label"),
        "duration": job.get("duration"), "aspect_ratio": job.get("aspect_ratio"), "quality": job.get("quality"),
        "references": [{"role": r.get("role"), "thumb": _thumb(r.get("url"))} for r in job.get("references") or []],
        "chat": [c.get("text", "")[:300] for c in (job.get("chat") or [])[-3:]],
        "files": files, "started_at": job.get("started_at"), "finished_at": job.get("finished_at"),
        "dashboard_url": base + "/",
    }


if _apps is not None:
    @_apps.tool(resource_uri=FLOW_CARD_URI, visibility=["app"])
    def flow_card_status(job_id: Optional[str] = None) -> Dict[str, Any]:
        """Live state of one Flow job for the in-chat card."""
        from flow_video_automator import flow_jobs, load_generations
        current = flow_jobs.status()
        if current.get("id") and (not job_id or current["id"] == job_id):
            return _card(current)
        saved = next((g for g in load_generations() if g.get("id") == job_id), None)
        if saved:
            if saved.get("state") not in ("ready", "error", "cancelled"):
                saved = {**saved, "state": "error", "message": "This job stopped when Ashzo MCP restarted."}
            return _card(saved)
        return {"error": "unknown job"}

    @_apps.tool(resource_uri=FLOW_CARD_URI, visibility=["app"])
    async def flow_card_cancel() -> Dict[str, Any]:
        """Cancel button on the in-chat card."""
        from flow_video_automator import flow_jobs
        return await flow_jobs.cancel()

    @_apps.tool(resource_uri=FLOW_CARD_URI, visibility=["app"])
    def flow_card_video_part(path: str, index: int = 0) -> Dict[str, Any]:
        """One piece of a saved video, so the card can play it without network access."""
        import base64 as _b64
        import math
        root = (BASE_DIR / "downloads").resolve()
        target = Path(path).resolve()
        if root not in target.parents or target.suffix.lower() != ".mp4" or not target.exists():
            return {"error": "Only videos in the Ashzo downloads folder can be shown."}
        size = target.stat().st_size
        if size > 120 * 1024 * 1024:
            return {"error": "This video is too large to play inside the chat; open it from the dashboard."}
        total = max(1, math.ceil(size / VIDEO_PART_BYTES))
        index = max(0, min(int(index), total - 1))
        with open(target, "rb") as fh:
            fh.seek(index * VIDEO_PART_BYTES)
            data = fh.read(VIDEO_PART_BYTES)
        return {"total": total, "index": index, "data": _b64.b64encode(data).decode()}

    _apps.add_html_resource(
        FLOW_CARD_URI,
        (BASE_DIR / "web" / "chat_card.html").read_text(encoding="utf-8"),
        title="Google Flow (Ashzo MCP)",
        description="Live progress, prompt, references, Flow's replies and the finished video.",
        csp=ResourceCsp(resource_domains=[f"http://127.0.0.1:{DASHBOARD_PORT}", f"http://localhost:{DASHBOARD_PORT}"]),
        prefers_border=False,
    )
    mcp._apply_extension(_apps)  # extensions are normally passed to the constructor; tools above had to exist first


# Server entrypoint
if __name__ == "__main__":
    # Running as a stdio MCP server (Cursor, Claude Desktop, ...): stdout carries the protocol,
    # so nothing may print to it. Live events go to the dashboard over HTTP when it is running.
    from live_events import live_broadcaster
    live_broadcaster.configure_forwarding(os.environ.get("ASHZO_DASHBOARD_URL"), source="mcp-agent")
    logger.info("Starting Ashzo MCP server on stdio transport...")
    mcp.run(transport="stdio")
