"""
CDP Network Sniffer & Route Interceptor for Universal-Web-MCP.
Uses Playwright and Chrome DevTools Protocol (CDP) to sniff background
XHR/Fetch traffic, filter out tracking/analytics noise, extract clean JSON
schemas, and compile them into reusable API routes.
"""

import asyncio
import json
import logging
from typing import Dict, List, Any, Optional
from pathlib import Path
from urllib.parse import urlparse, parse_qs
from pydantic import BaseModel, Field
from playwright.async_api import async_playwright, Response, Page
from cookie_sync import mask_headers

logger = logging.getLogger("UniversalWebMCP.Interceptor")

# Common noise, tracking, and ad domains to filter out
NOISE_PATTERNS = [
    "google-analytics.com",
    "googletagmanager.com",
    "doubleclick.net",
    "adservice.google.com",
    "adservice",
    "pagead2",
    "analytics",
    "telemetry",
    "stats.g.doubleclick.net",
    "clarity.ms",
    "hotjar.com",
    "sentry.io",
    "datadoghq.com",
    "facebook.net",
    "bat.bing.com",
    "events.launchdarkly.com",
    "/metrics",
    "/telemetry",
    "/cspreport",
    "/csp-report",
    "/ping",
    "/collect",
]


AUTH_STATE_FILE = Path(__file__).resolve().parent / "flow_auth_state.json"

class LearnedRoute(BaseModel):
    """Structured representation of a learned API endpoint."""
    id: str
    domain: str
    url: str
    method: str = "GET"
    query_params: Dict[str, Any] = Field(default_factory=dict)
    headers: Dict[str, str] = Field(default_factory=dict)
    response_schema: Dict[str, Any] = Field(default_factory=dict)
    sample_response: Any = None
    discovered_at: str = ""
    status_code: int = 200
    page_url: str = ""  # the page this API was seen on (opened to renew the session when needed)


def is_noise_url(url: str) -> bool:
    """Checks whether a URL matches known advertising, telemetry, or analytics patterns."""
    url_lower = url.lower()
    for pattern in NOISE_PATTERNS:
        if pattern in url_lower:
            return True
    return False


def infer_json_schema(obj: Any, max_depth: int = 3, current_depth: int = 0) -> Dict[str, Any]:
    """
    Recursively infers a lightweight JSON Schema from a Python object.
    Prunes deeply nested data to prevent token bloat.
    """
    if current_depth > max_depth:
        return {"type": "..."}

    if obj is None:
        return {"type": "null"}
    elif isinstance(obj, bool):
        return {"type": "boolean"}
    elif isinstance(obj, int):
        return {"type": "integer"}
    elif isinstance(obj, float):
        return {"type": "number"}
    elif isinstance(obj, str):
        return {"type": "string", "example": obj[:40] if len(obj) > 40 else obj}
    elif isinstance(obj, list):
        if not obj:
            return {"type": "array", "items": {}}
        # Sample first element for array item schema
        return {
            "type": "array",
            "items": infer_json_schema(obj[0], max_depth, current_depth + 1),
            "sample_length": len(obj)
        }
    elif isinstance(obj, dict):
        props = {}
        for k, v in list(obj.items())[:20]:  # limit keys per object level
            props[str(k)] = infer_json_schema(v, max_depth, current_depth + 1)
        return {
            "type": "object",
            "properties": props
        }
    return {"type": "unknown"}


def summarize_payload(obj: Any, max_chars: int = 1500) -> Any:
    """Creates a concise summary of a JSON payload to enforce token efficiency."""
    if isinstance(obj, list):
        if len(obj) > 5:
            return {
                "_summary": f"List of {len(obj)} items (showing first 3)",
                "sample": [summarize_payload(item, max_chars // 3) for item in obj[:3]]
            }
        return [summarize_payload(item, max_chars // max(len(obj), 1)) for item in obj]
    elif isinstance(obj, dict):
        condensed = {}
        for k, v in list(obj.items())[:15]:
            if isinstance(v, (str, int, float, bool, type(None))):
                if isinstance(v, str) and len(v) > 100:
                    condensed[k] = v[:100] + "... [truncated]"
                else:
                    condensed[k] = v
            elif isinstance(v, list):
                condensed[k] = f"List[{len(v)} items]"
            elif isinstance(v, dict):
                condensed[k] = {sub_k: "..." for sub_k in list(v.keys())[:5]}
            else:
                condensed[k] = str(v)[:50]
        return condensed
    elif isinstance(obj, str) and len(obj) > max_chars:
        return obj[:max_chars] + "... [truncated]"
    return obj


class NetworkInterceptor:
    """
    Playwright CDP sniffer that loads a target URL, monitors network activity,
    filters noise, and captures clean JSON/REST/GraphQL APIs.
    """

    def __init__(self, headless: bool = True):
        self.headless = headless

    async def sniff_url(
        self,
        url: str,
        timeout_ms: int = 15000,
        wait_network_idle: bool = True,
        interactive_action: Optional[str] = None
    ) -> Dict[str, Any]:
        """
        Navigates to URL, captures background JSON traffic via CDP/response listeners,
        extracts schemas, and extracts active browser cookies.
        """
        captured_routes: List[LearnedRoute] = []
        captured_cookies: List[Dict[str, Any]] = []

        async with async_playwright() as p:
            browser = None
            context = None
            is_connected_cdp = False

            # Strategy 1: Attempt direct connection to existing Chrome running with CDP port 9222
            try:
                browser = await p.chromium.connect_over_cdp("http://127.0.0.1:9222", timeout=3000)
                if browser.contexts:
                    context = browser.contexts[0]
                else:
                    context = await browser.new_context()
                is_connected_cdp = True
                logger.info("Connected directly to live Chrome instance over CDP (port 9222)!")
            except Exception:
                # Strategy 2: Launch dedicated headless Chromium instance
                logger.debug("Port 9222 not reachable, launching headless browser")
                browser = await p.chromium.launch(
                    headless=self.headless,
                    args=[
                        "--disable-blink-features=AutomationControlled",
                        "--no-sandbox",
                        "--disable-dev-shm-usage"
                    ]
                )
                context_kwargs = {
                    "user_agent": "Mozilla/5.0 (Windows NT 10.0; Win64; x64) AppleWebKit/537.36 (KHTML, like Gecko) Chrome/126.0.0.0 Safari/537.36",
                    "viewport": {"width": 1280, "height": 800}
                }
                if AUTH_STATE_FILE.exists():
                    context_kwargs["storage_state"] = str(AUTH_STATE_FILE)
                    logger.info(f"Loaded persistent storage state from {AUTH_STATE_FILE}")

                context = await browser.new_context(**context_kwargs)

            page = await context.new_page()

            # Attach CDP session for low-level inspection
            try:
                cdp = await context.new_cdp_session(page)
                await cdp.send("Network.enable")
            except Exception as e:
                logger.debug(f"CDP session attach skipped: {e}")

            # Asynchronous response listener
            async def handle_response(response: Response):
                try:
                    req_url = response.url
                    # Skip noise
                    if is_noise_url(req_url):
                        return

                    content_type = response.headers.get("content-type", "").lower()
                    if "application/json" not in content_type and "application/json+protobuf" not in content_type:
                        return

                    # Parse JSON safely
                    try:
                        data = await response.json()
                    except Exception:
                        # Some endpoints might have text or partial streams
                        text_data = await response.text()
                        if text_data.strip().startswith("{") or text_data.strip().startswith("["):
                            data = json.loads(text_data)
                        else:
                            return

                    parsed = urlparse(req_url)
                    query_params = parse_qs(parsed.query)
                    # Flatten single query params
                    flat_params = {k: v[0] if len(v) == 1 else v for k, v in query_params.items()}

                    schema = infer_json_schema(data)
                    summary = summarize_payload(data)

                    route_id = f"{response.request.method.upper()}:{parsed.netloc}{parsed.path}"
                    route = LearnedRoute(
                        id=route_id,
                        domain=parsed.netloc,
                        url=req_url.split("?")[0],
                        method=response.request.method.upper(),
                        query_params=flat_params,
                        headers=mask_headers(dict(response.request.headers)),
                        response_schema=schema,
                        sample_response=summary,
                        discovered_at=asyncio.get_event_loop().time().__str__(),
                        status_code=response.status,
                        page_url=url,
                    )
                    captured_routes.append(route)
                    logger.info(f"Captured clean API route: {route.method} {route.url}")
                except Exception as e:
                    logger.debug(f"Error intercepting response from {response.url}: {e}")

            page.on("response", handle_response)

            try:
                wait_until = "networkidle" if wait_network_idle else "domcontentloaded"
                await page.goto(url, wait_until=wait_until, timeout=timeout_ms)
            except Exception as e:
                logger.warning(f"Page navigation warning for {url}: {e}")

            # Optional interactive action (e.g., clicking a button or scrolling to trigger lazy APIs)
            if interactive_action:
                try:
                    await page.evaluate(interactive_action)
                    await asyncio.sleep(1.5)
                except Exception as e:
                    logger.debug(f"Interactive action error: {e}")

            # Capture cookies
            try:
                captured_cookies = await context.cookies()
            except Exception as e:
                logger.debug(f"Could not read context cookies: {e}")

            # Also capture page title and final URL
            page_title = await page.title()
            final_url = page.url

            # Close page / browser safely
            if is_connected_cdp:
                await page.close()
            else:
                await browser.close()

        # Deduplicate routes by ID
        unique_routes = {}
        for r in captured_routes:
            if r.id not in unique_routes:
                unique_routes[r.id] = r

        return {
            "title": page_title,
            "final_url": final_url,
            "routes": list(unique_routes.values()),
            "cookies": captured_cookies,
            "route_count": len(unique_routes)
        }
