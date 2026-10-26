"""
"Learn Flow API" recorder.

Google Flow has no public API. To find out whether Flow can be driven through its
own web requests (instead of by operating the page), start the recorder, make one
video by hand in the Ashzo Browser, then stop it. Every request Flow's site sends
to Google (prompt, references, generate, status, listing) is saved with secrets
masked to platform_skills/flow_api_capture_<time>.json, and shown live in the
dashboard while it happens.

This module only RECORDS. Whether a recorded call can be replayed is decided
later, by a person, from the capture. Calls protected by reCAPTCHA or other
anti-bot tokens are not to be worked around.
"""

from __future__ import annotations

import json
import logging
import re
import time
from pathlib import Path
from typing import Any, Dict, List, Optional
from urllib.parse import urlparse

from browser_hub import hub
from live_events import live_broadcaster

logger = logging.getLogger("AshzoMCP.FlowApiRecorder")

BASE_DIR = Path(__file__).resolve().parent
OUT_DIR = BASE_DIR / "platform_skills"

WATCH_HOSTS = ("flow.google.com", "labs.google", "aisandbox-pa.googleapis.com", "googleapis.com", "clients6.google.com")
NOISE = ("google-analytics", "googletagmanager", "doubleclick", "/log?", "play.google.com/log", "ogads-pa",
         "fonts.g", "gstatic.com", "/collect", "csp.withgoogle", "recaptcha/api2/anchor")
SECRET_KEYS = re.compile(r"(token|recaptcha|auth|secret|session|password|key)", re.I)


def _mask(value: str) -> str:
    if not isinstance(value, str):
        return value
    return value[:6] + "…" + value[-4:] if len(value) > 14 else "•••"


def _scrub(obj: Any, depth: int = 0) -> Any:
    if depth > 8:
        return "…"
    if isinstance(obj, dict):
        out = {}
        for k, v in obj.items():
            if SECRET_KEYS.search(str(k)) and isinstance(v, str):
                out[k] = _mask(v)
            else:
                out[k] = _scrub(v, depth + 1)
        return out
    if isinstance(obj, list):
        return [_scrub(v, depth + 1) for v in obj[:50]]
    if isinstance(obj, str) and len(obj) > 400:
        return f"<{len(obj)} chars: {obj[:60]}…>"
    return obj


def _parse_body(text: Optional[str]) -> Any:
    if not text:
        return None
    try:
        return _scrub(json.loads(text))
    except Exception:
        return text[:500] + ("…" if len(text) > 500 else "")


class FlowApiRecorder:
    def __init__(self) -> None:
        self.recording = False
        self.calls: List[Dict[str, Any]] = []
        self.started_at: Optional[float] = None
        self._ctx = None
        self._pending: Dict[Any, Dict[str, Any]] = {}

    def _wanted(self, url: str, resource_type: str) -> bool:
        if resource_type not in ("xhr", "fetch", "other"):
            return False
        host = urlparse(url).netloc
        if not any(h in host for h in WATCH_HOSTS):
            return False
        return not any(n in url for n in NOISE)

    async def start(self) -> Dict[str, Any]:
        if self.recording:
            return self.status()
        ctx = await hub.ensure()
        self._ctx = ctx
        self.calls, self._pending = [], {}
        self.started_at = time.time()
        self.recording = True
        ctx.on("request", self._on_request)
        ctx.on("requestfinished", self._on_finished)
        page = await hub.open_page("https://flow.google.com/", reuse_host=True, front=True)
        await hub.start_screencast(page)
        await live_broadcaster.broadcast("recorder", "Recording Flow's requests. Make one video by hand in the Ashzo Browser, then press Stop.",
                                         data={"recording": True})
        return self.status()

    def _on_request(self, request) -> None:
        try:
            if not self.recording or not self._wanted(request.url, request.resource_type):
                return
            headers = request.headers
            entry = {
                "t": round(time.time() - (self.started_at or time.time()), 2),
                "method": request.method,
                "url": request.url.split("?")[0],
                "query": urlparse(request.url).query[:300],
                "request_headers": sorted(k for k in headers.keys() if k.lower() not in ("cookie",)),
                "has_bearer_token": "authorization" in {k.lower() for k in headers.keys()},
                "request_body": _parse_body(request.post_data),
            }
            self._pending[request] = entry
        except Exception as e:
            logger.debug("record request: %s", e)

    async def _on_finished(self, request) -> None:
        entry = self._pending.pop(request, None)
        if entry is None:
            return
        try:
            resp = await request.response()
            if resp is not None:
                entry["status"] = resp.status
                ctype = resp.headers.get("content-type", "")
                if "json" in ctype:
                    body = await resp.text()
                    entry["response_sample"] = _parse_body(body[:6000])
        except Exception:
            pass
        self.calls.append(entry)
        path = urlparse(entry["url"]).path
        await live_broadcaster.broadcast("recorder", f"{entry['method']} {urlparse(entry['url']).netloc}{path} → {entry.get('status', '…')}",
                                         data={"recording": True, "call": {"method": entry["method"], "url": entry["url"], "status": entry.get("status")}})

    async def stop(self) -> Dict[str, Any]:
        if not self.recording:
            return self.status()
        self.recording = False
        try:
            if self._ctx is not None:
                self._ctx.remove_listener("request", self._on_request)
                self._ctx.remove_listener("requestfinished", self._on_finished)
        except Exception:
            pass
        OUT_DIR.mkdir(parents=True, exist_ok=True)
        endpoints: Dict[str, int] = {}
        for c in self.calls:
            key = f"{c['method']} {c['url']}"
            endpoints[key] = endpoints.get(key, 0) + 1
        out = OUT_DIR / f"flow_api_capture_{time.strftime('%Y%m%d_%H%M%S')}.json"
        out.write_text(json.dumps({
            "recorded_at": time.strftime("%Y-%m-%d %H:%M:%S"),
            "seconds": round(time.time() - (self.started_at or time.time()), 1),
            "note": "Secrets are masked. Review before any replay; never work around reCAPTCHA or anti-bot tokens.",
            "endpoints": endpoints,
            "calls": self.calls,
        }, indent=2), encoding="utf-8")
        await live_broadcaster.broadcast("recorder", f"Saved {len(self.calls)} Flow requests ({len(endpoints)} endpoints) to {out.name}.",
                                         data={"recording": False, "file": out.name, "count": len(self.calls)})
        return {**self.status(), "file": str(out), "endpoints": endpoints}

    def status(self) -> Dict[str, Any]:
        return {"recording": self.recording, "count": len(self.calls),
                "seconds": round(time.time() - self.started_at, 1) if self.started_at and self.recording else None}


flow_recorder = FlowApiRecorder()
