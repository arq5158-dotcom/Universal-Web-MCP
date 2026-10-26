"""
Live event hub for Ashzo MCP.

Everything the agent does is published here and streamed to the dashboard over
Server-Sent Events, so the page updates by itself (no refresh):

  * main channel   - job progress, logs, Flow agent chat lines, login steps,
                     account / vault / credit changes, MCP tool activity
  * screen channel - JPEG frames mirrored from the Ashzo Browser (Live View)

The dashboard process (app.py) is the hub. Any other process that imports this
module (for example server.py running as a stdio MCP server for Cursor or Claude
Desktop) forwards its events to the hub over HTTP, so the user sees an agent's
work live no matter how the agent is connected.
"""

from __future__ import annotations

import asyncio
import itertools
import logging
import os
import threading
import time
from collections import deque
from typing import Any, Deque, Dict, List, Optional, Set

logger = logging.getLogger("AshzoMCP.LiveEvents")

ACTIVE_STAGES = {"queued", "initializing", "connecting", "submitting", "waiting", "rendering", "downloading", "login"}
TERMINAL_STAGES = {"ready", "idle", "error", "cancelled"}

DEFAULT_HUB_URL = os.environ.get("ASHZO_DASHBOARD_URL", "http://127.0.0.1:8000")


class LiveEventBroadcaster:
    def __init__(self, max_history: int = 300):
        self._subs: Set[asyncio.Queue] = set()
        self._screen_subs: Set[asyncio.Queue] = set()
        self._history: Deque[Dict[str, Any]] = deque(maxlen=max_history)
        self._chat: Deque[Dict[str, Any]] = deque(maxlen=200)
        self._active_job: Optional[Dict[str, Any]] = None
        self._last_frame: Optional[Dict[str, Any]] = None
        self._loop: Optional[asyncio.AbstractEventLoop] = None
        self._ids = itertools.count(1)
        self._lock = threading.Lock()
        self.is_hub = False
        self.hub_url = DEFAULT_HUB_URL
        self.source = "dashboard"
        self._fwd_client = None
        self._last_fwd_frame = 0.0

    # ------------------------------------------------------------------ setup
    def attach_loop(self, loop: asyncio.AbstractEventLoop) -> None:
        """Called once by the dashboard at startup: this process becomes the hub."""
        self._loop = loop
        self.is_hub = True
        self.source = "dashboard"

    def configure_forwarding(self, hub_url: Optional[str] = None, source: str = "mcp-agent") -> None:
        """Used by processes that are not the dashboard (stdio MCP server)."""
        self.is_hub = False
        self.source = source
        if hub_url:
            self.hub_url = hub_url

    # ------------------------------------------------------------ subscribers
    def subscribe(self) -> asyncio.Queue:
        q: asyncio.Queue = asyncio.Queue(maxsize=1000)
        self._subs.add(q)
        return q

    def unsubscribe(self, q: asyncio.Queue) -> None:
        self._subs.discard(q)

    def subscribe_screen(self) -> asyncio.Queue:
        q: asyncio.Queue = asyncio.Queue(maxsize=3)
        self._screen_subs.add(q)
        return q

    def unsubscribe_screen(self, q: asyncio.Queue) -> None:
        self._screen_subs.discard(q)

    @staticmethod
    def _put_latest(q: asyncio.Queue, item: Dict[str, Any]) -> None:
        """Put without blocking; when the queue is full, drop its oldest item."""
        try:
            q.put_nowait(item)
        except asyncio.QueueFull:
            try:
                q.get_nowait()
            except asyncio.QueueEmpty:
                pass
            try:
                q.put_nowait(item)
            except asyncio.QueueFull:
                pass

    # ---------------------------------------------------------------- publish
    def _make_event(self, event_type: str, message: str, data: Optional[Dict[str, Any]],
                    stage: Optional[str], progress: Optional[int], source: Optional[str]) -> Dict[str, Any]:
        return {
            "id": next(self._ids),
            "type": event_type,
            "message": message or "",
            "timestamp": time.strftime("%H:%M:%S"),
            "ts": int(time.time() * 1000),
            "stage": stage,
            "progress": progress,
            "data": data or {},
            "source": source or self.source,
        }

    def _apply_state(self, evt: Dict[str, Any]) -> None:
        stage = evt.get("stage")
        data = evt.get("data") or {}
        if evt["type"] == "flow_chat":
            self._chat.append(evt)
        if stage in ACTIVE_STAGES:
            prev = self._active_job or {}
            started = prev.get("started_at") if prev.get("active") else None
            self._active_job = {
                "active": True,
                "stage": stage,
                "progress": evt.get("progress") if evt.get("progress") is not None else prev.get("progress", 0),
                "message": evt["message"],
                "timestamp": evt["timestamp"],
                "started_at": data.get("started_at") or started or evt["ts"],
                "job_id": data.get("job_id") or prev.get("job_id"),
                "title": data.get("title") or prev.get("title"),
                "kind": data.get("kind") or prev.get("kind", "flow"),
                "data": data,
            }
        elif stage in TERMINAL_STAGES:
            prev = self._active_job or {}
            self._active_job = {
                "active": False,
                "stage": stage,
                "progress": 100 if stage == "ready" else (prev.get("progress", 0) if stage in ("error", "cancelled") else 0),
                "message": evt["message"],
                "timestamp": evt["timestamp"],
                "started_at": prev.get("started_at"),
                "job_id": data.get("job_id") or prev.get("job_id"),
                "title": data.get("title") or prev.get("title"),
                "kind": data.get("kind") or prev.get("kind", "flow"),
                "data": data,
            }

    def _deliver(self, evt: Dict[str, Any]) -> None:
        """Runs on the hub loop thread."""
        self._apply_state(evt)
        self._history.append(evt)
        for q in list(self._subs):
            self._put_latest(q, evt)

    async def broadcast(self, event_type: str, message: str = "", data: Optional[Dict[str, Any]] = None,
                        stage: Optional[str] = None, progress: Optional[int] = None,
                        source: Optional[str] = None) -> Dict[str, Any]:
        evt = self._make_event(event_type, message, data, stage, progress, source)
        if self.is_hub:
            self._deliver(evt)
        else:
            self._apply_state(evt)
            self._history.append(evt)
            await self._forward("event", evt)
        return evt

    def emit(self, event_type: str, message: str = "", data: Optional[Dict[str, Any]] = None,
             stage: Optional[str] = None, progress: Optional[int] = None) -> None:
        """Thread-safe, non-async publish (usable from any thread or sync code)."""
        evt = self._make_event(event_type, message, data, stage, progress, None)
        if self.is_hub and self._loop is not None:
            try:
                running = asyncio.get_running_loop()
            except RuntimeError:
                running = None
            if running is self._loop:
                self._deliver(evt)
            else:
                self._loop.call_soon_threadsafe(self._deliver, evt)
            return
        try:
            loop = asyncio.get_running_loop()
            loop.create_task(self._forward("event", evt))
        except RuntimeError:
            pass

    def ingest(self, evt: Dict[str, Any]) -> None:
        """Hub side: accept an event forwarded by another process."""
        evt = dict(evt)
        evt["id"] = next(self._ids)
        evt.setdefault("timestamp", time.strftime("%H:%M:%S"))
        evt.setdefault("ts", int(time.time() * 1000))
        evt.setdefault("data", {})
        self._deliver(evt)

    # ----------------------------------------------------------------- screen
    async def push_frame(self, jpeg_b64: str, meta: Optional[Dict[str, Any]] = None) -> None:
        frame = {"type": "frame", "image": jpeg_b64, "ts": int(time.time() * 1000), "meta": meta or {}}
        if self.is_hub:
            self.ingest_frame(frame)
        else:
            now = time.time()
            if now - self._last_fwd_frame < 0.33:  # ~3 fps across processes
                return
            self._last_fwd_frame = now
            await self._forward("frame", frame)

    def ingest_frame(self, frame: Dict[str, Any]) -> None:
        self._last_frame = frame
        for q in list(self._screen_subs):
            self._put_latest(q, frame)

    def last_frame(self) -> Optional[Dict[str, Any]]:
        return self._last_frame

    # ------------------------------------------------------------- forwarding
    async def _forward(self, kind: str, payload: Dict[str, Any]) -> None:
        try:
            import httpx
            if self._fwd_client is None or self._fwd_client.is_closed:
                self._fwd_client = httpx.AsyncClient(timeout=1.5)
            await self._fwd_client.post(f"{self.hub_url}/api/live/ingest", json={"kind": kind, "payload": payload})
        except Exception:
            # Dashboard not running: nothing to show the events on. Never fail the agent's work.
            pass

    # ------------------------------------------------------------------ state
    def active_job(self) -> Dict[str, Any]:
        return self._active_job or {"active": False, "stage": "idle", "progress": 0, "message": "Agent standby"}

    def get_initial_state(self) -> Dict[str, Any]:
        return {
            "active_job": self.active_job(),
            "recent_logs": list(self._history)[-60:],
            "flow_chat": list(self._chat)[-60:],
            "has_frame": self._last_frame is not None,
        }


# Global singleton
live_broadcaster = LiveEventBroadcaster()
