"""
Live Event Broadcaster for Ashzo MCP.
Provides real-time SSE streaming for live agent progress, active video generation,
live console feed, download vault auto-updates, and live credit updates.
"""

import asyncio
import json
import time
from typing import Dict, Any, List, Optional
from collections import deque

class LiveEventBroadcaster:
    def __init__(self, max_history: int = 100):
        self._subscribers: List[asyncio.Queue] = []
        self._history: deque = deque(maxlen=max_history)
        self._active_job: Optional[Dict[str, Any]] = None
        self._loop: Optional[asyncio.AbstractEventLoop] = None

    def get_loop(self) -> asyncio.AbstractEventLoop:
        try:
            return asyncio.get_running_loop()
        except RuntimeError:
            if self._loop is None or self._loop.is_closed():
                self._loop = asyncio.new_event_loop()
                asyncio.set_event_loop(self._loop)
            return self._loop

    def subscribe(self) -> asyncio.Queue:
        q = asyncio.Queue()
        self._subscribers.append(q)
        return q

    def unsubscribe(self, q: asyncio.Queue):
        if q in self._subscribers:
            self._subscribers.remove(q)

    async def broadcast(self, event_type: str, message: str, data: Optional[Dict[str, Any]] = None, stage: Optional[str] = None, progress: Optional[int] = None):
        ts = time.strftime("%H:%M:%S")
        payload = {
            "type": event_type,
            "message": message,
            "timestamp": ts,
            "stage": stage,
            "progress": progress,
            "data": data or {}
        }

        # Update active job state if it's a generation or progress event
        if stage in ["queued", "initializing", "submitting", "rendering", "downloading"]:
            self._active_job = {
                "active": True,
                "stage": stage,
                "progress": progress or 0,
                "message": message,
                "timestamp": ts,
                "data": data or {}
            }
        elif stage in ["ready", "idle", "error"]:
            self._active_job = {
                "active": False,
                "stage": stage,
                "progress": 100 if stage == "ready" else 0,
                "message": message,
                "timestamp": ts,
                "data": data or {}
            }

        self._history.append(payload)

        # Distribute to all connected subscribers
        dead_queues = []
        for q in self._subscribers:
            try:
                q.put_nowait(payload)
            except asyncio.QueueFull:
                dead_queues.append(q)

        for dq in dead_queues:
            self.unsubscribe(dq)

    def broadcast_sync(self, event_type: str, message: str, data: Optional[Dict[str, Any]] = None, stage: Optional[str] = None, progress: Optional[int] = None):
        """Thread-safe synchronous wrapper for background tasks."""
        try:
            loop = self.get_loop()
            if loop.is_running():
                asyncio.run_coroutine_threadsafe(
                    self.broadcast(event_type, message, data, stage, progress),
                    loop
                )
            else:
                loop.run_until_complete(
                    self.broadcast(event_type, message, data, stage, progress)
                )
        except Exception as e:
            print(f"[LiveBroadcaster] Error: {e}")

    def get_initial_state(self) -> Dict[str, Any]:
        return {
            "active_job": self._active_job or {"active": False, "stage": "idle", "progress": 0, "message": "Agent standby"},
            "recent_logs": list(self._history)[-25:]
        }

# Global singleton
live_broadcaster = LiveEventBroadcaster()
