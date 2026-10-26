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

# Configure Logging
logging.basicConfig(
    level=logging.INFO,
    format="[%(asctime)s] [%(levelname)s] [%(name)s] %(message)s"
)
logger = logging.getLogger("UniversalWebMCP.Server")

# File paths
BASE_DIR = Path(__file__).resolve().parent
ROUTES_CACHE_FILE = BASE_DIR / "learned_routes.json"
SESSION_COOKIES_FILE = BASE_DIR / "session_cookies.json"

# Initialize FastMCP Server
mcp = FastMCP("Universal-Web-Bridge")

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
        # Domain fallback: check if any route matches the domain & prefix
        parsed = urlparse(url)
        for k, route in self.routes.items():
            if route.get("domain") == parsed.netloc and parsed.path.startswith(urlparse(route.get("url", "")).path):
                return route
        return None

    def add_route(self, route: LearnedRoute):
        self.routes[route.id] = route.model_dump()
        self.save()

    def add_routes(self, routes: List[LearnedRoute]):
        for r in routes:
            self.routes[r.id] = r.model_dump()
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


# --- MCP Tools ---

@mcp.tool()
async def universal_request(
    url: str,
    method: str = "GET",
    params: Optional[Dict[str, Any]] = None,
    body: Optional[Dict[str, Any]] = None,
    force_tier: Optional[int] = None
) -> Dict[str, Any]:
    """
    Executes a web request using the 3-Tier Hybrid Routing Architecture:
    - Tier 1 (Fast Path): Replays learned JSON/GraphQL API requests using session cookies (<200ms).
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
    # TIER 1: FAST PATH (Replay learned first-party JSON/GraphQL API)
    # -------------------------------------------------------------
    learned = route_cache.get_route(target_method, url)
    if (learned or force_tier == 1) and force_tier not in (2, 3):
        logger.info(f"[Tier 1 Fast Path] Attempting direct replay for {target_method} {url}")
        client = get_http_client()
        headers = {
            "User-Agent": "Mozilla/5.0 (Windows NT 10.0; Win64; x64) AppleWebKit/537.36 (KHTML, like Gecko) Chrome/126.0.0.0 Safari/537.36",
            "Accept": "application/json, text/plain, */*",
        }
        cookie_header = cookie_manager.get_cookie_header()
        if cookie_header:
            headers["Cookie"] = cookie_header

        # Merge cached request headers if present
        if learned and "headers" in learned:
            for hk, hv in learned["headers"].items():
                if hk.lower() not in ("cookie", "host", "content-length"):
                    headers[hk] = hv

        try:
            req_url = learned["url"] if (learned and force_tier != 1) else url
            req_params = params or (learned.get("query_params") if learned else None)
            
            resp = await client.request(
                method=target_method,
                url=req_url,
                params=req_params,
                json=body if target_method in ("POST", "PUT", "PATCH") else None,
                headers=headers
            )
            elapsed_ms = round((time.perf_counter() - start_time) * 1000, 2)

            # Check for expired session / authentication challenge
            if resp.status_code in (401, 403):
                logger.warning(f"[Tier 1] Authentication failed ({resp.status_code}). Triggering session re-sync...")
                # Escalate to Tier 2 to refresh session via browser
            elif resp.is_success:
                try:
                    data = resp.json()
                    summary = summarize_payload(data)
                    return {
                        "tier": "Tier 1 (Fast Path)",
                        "latency_ms": elapsed_ms,
                        "status_code": resp.status_code,
                        "url": str(resp.url),
                        "data": summary,
                        "message": f"Successfully replayed learned API in {elapsed_ms}ms"
                    }
                except Exception:
                    # Non-JSON response on learned route; fall through to Tier 2/3
                    pass
        except Exception as e:
            logger.warning(f"[Tier 1 Fast Path Error]: {e}. Falling back to Tier 2.")

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
                    "message": f"Learned {len(routes)} new API endpoint(s) and compiled into permanent MCP cache."
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
    return fallback_res


@mcp.tool()
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
def sync_chrome_session(profile_name_or_email: str = "arq5020@gmail.com") -> Dict[str, Any]:
    """
    Synchronizes session cookies from the local Google Chrome profile (e.g. arq5020@gmail.com).
    Bypasses login walls and bot detection for Tier 1 Fast Path requests.

    Args:
        profile_name_or_email: Chrome profile folder (e.g. 'Profile 1') or account email ('arq5020@gmail.com').
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
def clear_cache(domain: Optional[str] = None) -> Dict[str, str]:
    """
    Clears cached routes and session state.

    Args:
        domain: Specific domain to purge, or None to purge all.
    """
    route_cache.clear(domain_filter=domain)
    return {"status": "success", "message": f"Cache cleared for: {domain or 'ALL'}"}


# Server entrypoint
if __name__ == "__main__":
    logger.info("Starting Universal-Web-MCP server on stdio transport...")
    # Pre-sync cookies for user profile
    try:
        sync_chrome_session("arq5020@gmail.com")
    except Exception as e:
        logger.debug(f"Initial cookie pre-sync notice: {e}")

    mcp.run(transport="stdio")
