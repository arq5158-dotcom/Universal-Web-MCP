"""
Ashzo MCP · Studio (dashboard server).

Serves the dashboard in web/ and everything it needs:
  - /api/live/stream   live events (job progress, Flow chat, sign-in steps, accounts, vault, credits, agent activity)
  - /api/live/screen   live pictures of the Ashzo Browser (Live View)
  - /api/live/ingest   where the MCP process (Cursor, Claude Desktop, ...) forwards its events, so an agent's
                       work shows up here as it happens
  - /mcp               the MCP server over SSE
Runs on 127.0.0.1 only. Start it with `python app.py` or the desktop icon (see README).
"""

from __future__ import annotations

import asyncio
import base64
import json
import logging
import os
import re
import sys
import time
import uuid
from contextlib import asynccontextmanager
from pathlib import Path
from typing import Any, Dict, Optional
from urllib.parse import urlparse

import uvicorn
from fastapi import FastAPI, HTTPException, Request
from fastapi.middleware.cors import CORSMiddleware
from fastapi.responses import FileResponse, JSONResponse, StreamingResponse
from fastapi.staticfiles import StaticFiles

from ashzo_settings import load_settings, save_settings
from auth_flow import cancel_login, login_status, start_login
from browser_hub import BrowserLaunchError, hub
from flow_api_recorder import flow_recorder
from flow_video_automator import FlowVideoAutomator, downloads_url, flow_jobs, load_generations
from live_events import live_broadcaster
from platform_learner import platform_learner
from server import list_learned_routes, mcp, universal_request
from session_manager import session_manager

logging.basicConfig(level=logging.INFO, stream=sys.stderr, format="%(asctime)s %(name)s %(levelname)s %(message)s")
logger = logging.getLogger("AshzoMCP.Studio")

VERSION = "5.0.0"
BASE_DIR = Path(__file__).resolve().parent
WEB_DIR = BASE_DIR / "web"
DOWNLOADS_DIR = BASE_DIR / "downloads"
REFERENCES_DIR = DOWNLOADS_DIR / "references"
DOWNLOADS_DIR.mkdir(parents=True, exist_ok=True)

HOST = os.environ.get("ASHZO_HOST", "127.0.0.1")
PORT = int(os.environ.get("ASHZO_PORT") or os.environ.get("PORT") or 8000)
LOCAL_HOSTS = {"127.0.0.1", "::1", "localhost"}
MODELS = {"omni_flash", "gemini_omni", "veo_3_1"}
DURATIONS = {"4", "6", "8", "10", "30s_ad"}
ASPECTS = {"9:16", "16:9", "1:1"}
QUALITIES = {"720p", "1080p", "4k"}


# ───────────────────────────────────────────────────────────── vault watcher
def _vault_signature() -> tuple:
    sig = []
    for p in DOWNLOADS_DIR.glob("**/*.mp4"):
        try:
            st = p.stat()
            sig.append((str(p), st.st_size, int(st.st_mtime)))
        except OSError:
            pass
    return tuple(sorted(sig))


async def _watch_vault() -> None:
    """Tell the dashboard when videos appear, change or disappear (any source: agent, you, Explorer)."""
    last = await asyncio.to_thread(_vault_signature)
    while True:
        await asyncio.sleep(2)
        try:
            now = await asyncio.to_thread(_vault_signature)
            if now != last:
                last = now
                await live_broadcaster.broadcast("vault_changed", "", data={"count": len(now)})
        except Exception as e:  # never let the watcher die
            logger.debug("vault watcher: %s", e)


@asynccontextmanager
async def lifespan(_: FastAPI):
    live_broadcaster.attach_loop(asyncio.get_running_loop())
    watcher = asyncio.create_task(_watch_vault())
    logger.info("Ashzo MCP Studio on http://%s:%s", "localhost" if HOST in LOCAL_HOSTS else HOST, PORT)
    try:
        yield
    finally:
        watcher.cancel()


web_app = FastAPI(title="Ashzo MCP Studio", version=VERSION, lifespan=lifespan)
app = web_app  # `uvicorn app:app` works too

web_app.add_middleware(
    CORSMiddleware,
    allow_origin_regex=r"^https?://(localhost|127\.0\.0\.1)(:\d+)?$",
    allow_methods=["*"],
    allow_headers=["*"],
)


@web_app.middleware("http")
async def local_only_guard(request: Request, call_next):
    """Block other websites from driving the app through your browser (CSRF / DNS rebinding)."""
    host = (request.headers.get("host") or "").rsplit(":", 1)[0].strip("[]")
    if HOST in LOCAL_HOSTS and host and host not in LOCAL_HOSTS:
        return JSONResponse(status_code=403, content={"detail": "Ashzo MCP only answers on localhost."})
    if request.method not in ("GET", "HEAD", "OPTIONS"):
        origin = request.headers.get("origin")
        if origin and urlparse(origin).hostname not in LOCAL_HOSTS:
            return JSONResponse(status_code=403, content={"detail": "Cross-site request blocked."})
    return await call_next(request)


def _require_local(request: Request) -> None:
    client = request.client.host if request.client else ""
    if client not in LOCAL_HOSTS:
        raise HTTPException(status_code=403, detail="Only this computer can send live events.")


web_app.mount("/static", StaticFiles(directory=str(WEB_DIR)), name="static")
web_app.mount("/downloads", StaticFiles(directory=str(DOWNLOADS_DIR)), name="downloads")
try:
    web_app.mount("/mcp", mcp.sse_app())
except Exception as e:  # older/newer MCP SDKs
    logger.warning("MCP SSE endpoint not mounted: %s", e)

NO_CACHE = {"Cache-Control": "no-cache"}


@web_app.get("/", include_in_schema=False)
async def dashboard():
    return FileResponse(WEB_DIR / "index.html", headers=NO_CACHE)


@web_app.get("/favicon.ico", include_in_schema=False)
async def favicon():
    return FileResponse(WEB_DIR / "favicon.svg", media_type="image/svg+xml")


@web_app.get("/api/health")
async def health():
    return {"status": "ok", "app": "ashzo-mcp", "version": VERSION}


# ───────────────────────────────────────────────────────────── live
SSE_HEADERS = {"Cache-Control": "no-cache", "Connection": "keep-alive", "X-Accel-Buffering": "no"}


@web_app.get("/api/live/stream")
async def live_stream(request: Request):
    async def gen():
        q = live_broadcaster.subscribe()
        try:
            yield "retry: 2000\n"
            yield f"data: {json.dumps({'type': 'init', 'data': live_broadcaster.get_initial_state()})}\n\n"
            while True:
                if await request.is_disconnected():
                    break
                try:
                    evt = await asyncio.wait_for(q.get(), timeout=15)
                    yield f"id: {evt.get('id', '')}\ndata: {json.dumps(evt, default=str)}\n\n"
                except asyncio.TimeoutError:
                    yield ": ping\n\n"
        finally:
            live_broadcaster.unsubscribe(q)
    return StreamingResponse(gen(), media_type="text/event-stream", headers=SSE_HEADERS)


@web_app.get("/api/live/screen")
async def live_screen(request: Request):
    async def gen():
        q = live_broadcaster.subscribe_screen()
        try:
            last = live_broadcaster.last_frame()
            if last:
                yield f"data: {json.dumps(last)}\n\n"
            while True:
                if await request.is_disconnected():
                    break
                try:
                    frame = await asyncio.wait_for(q.get(), timeout=15)
                    yield f"data: {json.dumps(frame)}\n\n"
                except asyncio.TimeoutError:
                    yield ": ping\n\n"
        finally:
            live_broadcaster.unsubscribe_screen(q)
    return StreamingResponse(gen(), media_type="text/event-stream", headers=SSE_HEADERS)


@web_app.post("/api/live/ingest", include_in_schema=False)
async def live_ingest(payload: Dict[str, Any], request: Request):
    """Events and frames forwarded by the MCP process an agent is using."""
    _require_local(request)
    kind = payload.get("kind")
    body = payload.get("payload") or {}
    if kind == "frame":
        live_broadcaster.ingest_frame(body)
    elif kind == "event":
        live_broadcaster.ingest(body)
    else:
        raise HTTPException(status_code=400, detail="kind must be 'event' or 'frame'")
    return {"ok": True}


@web_app.post("/api/live/broadcast", include_in_schema=False)
async def live_broadcast(payload: Dict[str, Any], request: Request):
    _require_local(request)
    await live_broadcaster.broadcast(payload.get("type", "log"), payload.get("message", ""), data=payload.get("data"),
                                     stage=payload.get("stage"), progress=payload.get("progress"),
                                     source=payload.get("source"))
    return {"status": "broadcasted"}


@web_app.get("/api/live/status")
async def live_status():
    return live_broadcaster.get_initial_state()


# ───────────────────────────────────────────────────────────── Ashzo Browser
@web_app.get("/api/browser/status")
async def browser_status():
    return await hub.status()


@web_app.post("/api/browser/open")
async def browser_open():
    """Show the Ashzo Browser window (starts it if needed) and mirror it in Live View."""
    try:
        await hub.ensure(visible=True)
        page = await hub.current_page()
        if page is None:
            page = await hub.open_page(load_settings().get("flow_project_url") or "https://flow.google.com/")
        await hub.bring_to_front(page)
        await hub.start_screencast(page, seconds=120)
        return await hub.status()
    except BrowserLaunchError as e:
        raise HTTPException(status_code=500, detail=str(e))


@web_app.post("/api/browser/peek")
async def browser_peek():
    return await hub.peek(seconds=90)


# ───────────────────────────────────────────────────────────── sign-in
@web_app.post("/api/auth/start")
async def auth_start(payload: Dict[str, Any]):
    url = (payload.get("target_url") or "https://flow.google.com/").strip()
    return await start_login(target_url=url, expected_email=payload.get("expected_email") or None,
                             session_name=payload.get("session_name") or None)


@web_app.post("/api/auth/cancel")
async def auth_cancel(payload: Optional[Dict[str, Any]] = None):
    return await cancel_login((payload or {}).get("job_id"))


@web_app.get("/api/auth/status")
async def auth_status(job_id: Optional[str] = None):
    return login_status(job_id)


@web_app.post("/api/authenticate")
async def api_authenticate_legacy(target_url: str = "https://flow.google.com/", expected_email: Optional[str] = None):
    """Old endpoint, kept for scripts. Returns at once; progress arrives on /api/live/stream."""
    return await start_login(target_url=target_url, expected_email=expected_email)


# ───────────────────────────────────────────────────────────── Google Flow
@web_app.post("/api/flow/generate")
async def flow_generate(payload: Dict[str, Any]):
    prompt = (payload.get("prompt") or "").strip()
    if not prompt:
        raise HTTPException(status_code=400, detail="Write a prompt first.")
    model = payload.get("model") or "omni_flash"
    duration = str(payload.get("duration") or "8")
    aspect = payload.get("aspect_ratio") or load_settings().get("aspect_ratio", "9:16")
    quality = payload.get("download_quality") or "1080p"
    if model not in MODELS or duration not in DURATIONS or aspect not in ASPECTS or quality not in QUALITIES:
        raise HTTPException(status_code=400, detail="Unknown model, length, aspect ratio or quality.")
    for key in ("starting_frame_path", "ending_frame_path"):
        p = payload.get(key)
        if p:
            rp = Path(p).resolve()
            if REFERENCES_DIR.resolve() not in rp.parents or not rp.exists():
                raise HTTPException(status_code=400, detail="Reference images must be uploaded through the app.")
    request = {
        "prompt": prompt, "model": model, "duration": duration, "aspect_ratio": aspect, "download_quality": quality,
        "starting_frame": payload.get("starting_frame"), "ending_frame": payload.get("ending_frame"),
        "starting_frame_path": payload.get("starting_frame_path"), "ending_frame_path": payload.get("ending_frame_path"),
        "slug": payload.get("slug") or "video", "source": "dashboard",
    }
    return await flow_jobs.start(request, DOWNLOADS_DIR)


@web_app.post("/api/flow/cancel")
async def flow_cancel():
    return await flow_jobs.cancel()


@web_app.get("/api/flow/job")
async def flow_job():
    return flow_jobs.status()


@web_app.get("/api/flow/generations")
async def flow_generations(limit: int = 40):
    items = load_generations()[: max(1, min(limit, 200))]
    current = flow_jobs.status()
    if current.get("id"):
        items = [current] + [g for g in items if g.get("id") != current["id"]]
    for g in items:  # a job that was running when the app closed can't still be running
        if g.get("state") in ("queued", "connecting", "initializing", "submitting", "waiting", "rendering", "downloading") \
                and g.get("id") != current.get("id"):
            g["state"], g["message"] = "error", "Stopped when the app closed."
    return items


IMAGE_MAGIC = {b"\x89PNG": ".png", b"\xff\xd8\xff": ".jpg", b"RIFF": ".webp", b"GIF8": ".gif"}


@web_app.post("/api/flow/reference")
async def flow_reference(payload: Dict[str, Any]):
    """Store a reference image (sent as base64) so Flow can be given it as a first/last frame."""
    try:
        data = base64.b64decode(payload.get("data_b64") or "", validate=True)
    except Exception:
        raise HTTPException(status_code=400, detail="That file couldn't be read.")
    if not data or len(data) > 15 * 1024 * 1024:
        raise HTTPException(status_code=400, detail="Images must be under 15 MB.")
    ext = next((e for m, e in IMAGE_MAGIC.items() if data.startswith(m)), None)
    if not ext or (ext == ".webp" and data[8:12] != b"WEBP"):
        raise HTTPException(status_code=400, detail="Use a PNG, JPG, WEBP or GIF image.")
    stem = re.sub(r"[^A-Za-z0-9_-]+", "_", Path(payload.get("filename") or "reference").stem)[:40] or "reference"
    REFERENCES_DIR.mkdir(parents=True, exist_ok=True)
    out = REFERENCES_DIR / f"{time.strftime('%Y%m%d_%H%M%S')}_{uuid.uuid4().hex[:6]}_{stem}{ext}"
    out.write_bytes(data)
    return {"path": str(out), "url": downloads_url(out), "name": out.name}


@web_app.get("/api/flow/credits")
async def flow_credits(refresh: bool = False):
    """Real Flow balance. Without refresh, the last value read (no browser is opened)."""
    if refresh:
        from get_live_flow_credits import fetch_live_google_flow_credits
        result = await fetch_live_google_flow_credits()
        if result.get("status") == "success":
            result.setdefault("checked_at", int(time.time() * 1000))
            await live_broadcaster.broadcast("credits", f"Flow credits: {result['live_credits']}", data=result)
        return result
    active = session_manager.get_active_session() or {}
    # Only trust values this version read (they carry a timestamp); older files held a made-up number.
    if isinstance(active.get("live_credits"), int) and active.get("credits_checked_at"):
        return {"status": "success", "live_credits": active["live_credits"], "tier": active.get("tier"),
                "account": active.get("email") or None, "checked_at": active.get("credits_checked_at"), "cached": True}
    return {"status": "unknown", "message": "Press refresh to read your Flow credits."}


@web_app.get("/api/flow/downloads")
async def flow_downloads():
    files = []
    for p in DOWNLOADS_DIR.glob("**/*.mp4"):
        try:
            st = p.stat()
        except OSError:
            continue
        files.append({
            "name": p.name,
            "rel": p.relative_to(DOWNLOADS_DIR).as_posix(),
            "url": downloads_url(p),
            "size_mb": round(st.st_size / (1024 * 1024), 2),
            "modified": time.strftime("%Y-%m-%d %H:%M", time.localtime(st.st_mtime)),
            "mtime": st.st_mtime,
        })
    files.sort(key=lambda f: f["mtime"], reverse=True)
    return files


@web_app.post("/api/flow/rename")
async def flow_rename(payload: Dict[str, Any]):
    rel = payload.get("rel")
    target = (DOWNLOADS_DIR / rel) if rel else (Path(payload["current_path"]) if payload.get("current_path") else None)
    if target is None or not payload.get("new_name"):
        raise HTTPException(status_code=400, detail="Missing file or new name.")
    try:
        result = FlowVideoAutomator.rename_downloaded_video(str(target), payload["new_name"], root=DOWNLOADS_DIR)
    except (PermissionError, FileNotFoundError, FileExistsError, ValueError) as e:
        raise HTTPException(status_code=400, detail=str(e))
    await live_broadcaster.broadcast("vault_changed", f"Renamed to {result['new_name']}", data={})
    return result


@web_app.post("/api/flow/recorder/start")
async def recorder_start():
    try:
        return await flow_recorder.start()
    except BrowserLaunchError as e:
        raise HTTPException(status_code=500, detail=str(e))


@web_app.post("/api/flow/recorder/stop")
async def recorder_stop():
    return await flow_recorder.stop()


@web_app.get("/api/flow/recorder/status")
async def recorder_status():
    return flow_recorder.status()


# ───────────────────────────────────────────────────────────── accounts
@web_app.get("/api/sessions")
async def sessions_list():
    return {"status": "success", "active_session": session_manager.get_active_session(),
            "sessions": session_manager.list_sessions()}


@web_app.post("/api/sessions/{session_id}/select")
async def sessions_select(session_id: str):
    rec = session_manager.select_session(session_id)
    if not rec:
        raise HTTPException(status_code=404, detail="Account not found.")
    return {"status": "success", "active_session": rec}


@web_app.delete("/api/sessions/{session_id}")
async def sessions_delete(session_id: str):
    return {"status": "success" if session_manager.remove_session(session_id) else "not_found"}


# ───────────────────────────────────────────────────────────── settings
@web_app.get("/api/settings")
async def settings_get():
    return load_settings()


@web_app.post("/api/settings")
async def settings_post(payload: Dict[str, Any]):
    url = payload.get("flow_project_url")
    if url and not re.match(r"^https://(flow\.google\.com|labs\.google)/", url):
        raise HTTPException(status_code=400, detail="Use a Google Flow link (https://flow.google.com/...).")
    saved = save_settings(payload)
    await live_broadcaster.broadcast("settings", "Settings saved.", data=saved)
    return saved


# ───────────────────────────────────────────────────────────── explorer, fast path, study
@web_app.post("/api/learn-platform")
async def learn_platform(payload: Dict[str, Any]):
    url = (payload.get("url") or "").strip()
    if not url.startswith(("http://", "https://")):
        raise HTTPException(status_code=400, detail="Enter a full address starting with https://")
    if platform_learner.get_status().get("state") not in ("IDLE", "READY", "ERROR"):
        raise HTTPException(status_code=409, detail="An exploration is already running.")
    asyncio.create_task(platform_learner.learn_platform(url))
    return {"status": "started", "url": url}


@web_app.get("/api/learn-platform/status")
async def learn_platform_status():
    return platform_learner.get_status()


@web_app.post("/api/request")
async def fast_path_request(payload: Dict[str, Any]):
    url = (payload.get("url") or "").strip()
    if not url.startswith(("http://", "https://")):
        raise HTTPException(status_code=400, detail="Enter a full address starting with https://")
    tier = payload.get("force_tier")
    return await universal_request(url=url, method=payload.get("method", "GET"),
                                   force_tier=int(tier) if tier else None)


@web_app.get("/api/routes")
async def routes(domain: Optional[str] = None):
    return list_learned_routes(domain=domain)


@web_app.post("/api/study")
async def study(payload: Dict[str, Any]):
    from video_study import FfmpegMissing, study_video
    try:
        return await asyncio.to_thread(study_video, payload.get("path", ""), payload.get("out_dir"))
    except FfmpegMissing as e:
        raise HTTPException(status_code=500, detail=str(e))
    except FileNotFoundError as e:
        raise HTTPException(status_code=404, detail=str(e))


def main() -> None:
    sys.stderr.write(f"\n  Ashzo MCP Studio  ->  http://localhost:{PORT}\n\n")
    uvicorn.run(web_app, host=HOST, port=PORT, log_level="warning")


if __name__ == "__main__":
    main()
