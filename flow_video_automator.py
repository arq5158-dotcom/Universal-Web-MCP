"""
Google Flow video generation for Ashzo MCP.

A job runs in the Ashzo Browser (a real Chrome window you can watch, see
browser_hub) and reports every step live to the dashboard:

  queued -> connecting -> submitting -> waiting (Flow's agent replies are mirrored
  as "flow_chat" events) -> rendering (real elapsed time, Flow's own % when shown)
  -> downloading -> ready, or error / cancelled with the reason.

The request goes to Flow's agent chat ("What do you want to create?") in plain
words, including the model, length and aspect ratio, because that is how the
Flow agent takes instructions. A job finishes only when a NEW video appears in
the project, not after a fixed wait. One job runs at a time; it can be cancelled.
"""

import os
import sys
import json
import time
import asyncio
import logging
from pathlib import Path
from typing import List, Dict, Any, Optional
from pydantic import BaseModel, Field
from live_events import live_broadcaster

logger = logging.getLogger("AshzoMCP.FlowAutomator")

BASE_DIR = Path(__file__).resolve().parent
AUTH_STATE_FILE = BASE_DIR / "flow_auth_state.json"
DEFAULT_DOWNLOADS = BASE_DIR / "downloads" / "flow_production"


class ScenePrompt(BaseModel):
    scene_number: int
    duration_seconds: int = 8  # 4s, 6s, 8s, 10s for Omni; 8s for Veo
    prompt: str
    camera_movement: str = "Dolly forward, cinematic lighting"
    starting_frame: Optional[str] = None  # Asset ID or path to Start Frame (0s)
    ending_frame: Optional[str] = None    # Asset ID or path to End Frame (4s-10s)
    voiceover: Optional[str] = None


class VideoProject(BaseModel):
    id: str
    title: str
    target_duration: int = 30  # Standard 30s ad, or single shot 4s, 6s, 8s, 10s
    model: str = "omni_flash"  # "omni_flash" (4s, 6s, 8s, 10s), "veo_3_1" (8s), "gemini_omni"
    download_quality: str = "1080p"  # "720p", "1080p", "4k"
    aspect_ratio: str = "16:9"  # "16:9", "9:16", "1:1"
    scenes: List[ScenePrompt] = Field(default_factory=list)


def build_30s_storyboard(concept: str, model: str = "omni_flash") -> List[ScenePrompt]:
    """
    Splits any 30-second video concept into coherent scenes tailored
    specifically for Gemini Omni Flash (supports flexible 4s, 6s, 8s, 10s)
    or Google Veo 3.1 (8s).
    """
    is_omni = "omni" in model.lower()
    model_tag = "High-speed 4K Gemini Omni Flash dynamic motion" if is_omni else "Cinematic 4K Google Veo 3.1 photorealism"
    
    if is_omni:
        # Flexible 4-scene pacing: 8s + 8s + 8s + 6s = 30s (or 10s + 10s + 10s)
        return [
            ScenePrompt(
                scene_number=1,
                duration_seconds=8,
                camera_movement="Slow push-in with shallow depth of field",
                prompt=(
                    f"{model_tag}, Scene 1 (Hook): Extreme close-up establishing core tension: {concept}. "
                    "Cinematic lighting, crisp contrast."
                ),
                voiceover="The old way was slow, fragile, and bound to break."
            ),
            ScenePrompt(
                scene_number=2,
                duration_seconds=8,
                camera_movement="Dynamic lateral tracking shot",
                prompt=(
                    f"{model_tag}, Scene 2 (Breakthrough): High-speed visual transition showing "
                    f"instant acceleration and breakthrough technology: {concept}."
                ),
                voiceover="Until now. Meet the instant sub-second breakthrough."
            ),
            ScenePrompt(
                scene_number=3,
                duration_seconds=8,
                camera_movement="Orbiting camera shot, sleek holographic UI",
                prompt=(
                    f"{model_tag}, Scene 3 (Demonstration): Ultra-crisp live demonstration with vibrant "
                    f"cyan data streams and flawless autonomous execution: {concept}."
                ),
                voiceover="Automated at light speed. Pre-authenticated. Zero bloat."
            ),
            ScenePrompt(
                scene_number=4,
                duration_seconds=6,
                camera_movement="Pull-back crane shot revealing grand finale",
                prompt=(
                    f"{model_tag}, Scene 4 (Climax & CTA): Grand closing shot with glowing holographic "
                    "branding and satisfied developer smiling at instant speed."
                ),
                voiceover="Stop waiting. Build at light speed today."
            )
        ]
    else:
        # Veo 3.1: 4 scenes (8s + 8s + 8s + 6s)
        return [
            ScenePrompt(
                scene_number=1,
                duration_seconds=8,
                camera_movement="Dolly forward with anamorphic lens flare",
                prompt=f"{model_tag}, Scene 1 (Hook): Cinematic 35mm establishing shot of {concept}."
            ),
            ScenePrompt(
                scene_number=2,
                duration_seconds=8,
                camera_movement="Smooth panning shot",
                prompt=f"{model_tag}, Scene 2 (Tension): Dramatic moody shadows evolving into brilliant cyan illumination: {concept}."
            ),
            ScenePrompt(
                scene_number=3,
                duration_seconds=8,
                camera_movement="FPV push through holographic data",
                prompt=f"{model_tag}, Scene 3 (Execution): Particle acceleration and lightning speed flow: {concept}."
            ),
            ScenePrompt(
                scene_number=4,
                duration_seconds=6,
                camera_movement="Elevating camera with triumphant lighting",
                prompt=f"{model_tag}, Scene 4 (Closing): Cinematic final logo and tagline reveal for {concept}."
            )
        ]


def validate_and_educate_prompt(
    prompt: str,
    model: str = "omni_flash",
    duration: int = 8,
    has_start_frame: bool = False,
    has_end_frame: bool = False
) -> Dict[str, Any]:
    """
    Validates user video prompts against Google Flow constraints,
    educates the user if the prompt is suboptimal, and auto-refines it.
    """
    is_omni = "omni" in model.lower()
    valid_durations = [4, 6, 8, 10] if is_omni else [4, 6, 8]
    warnings = []
    tips = []
    refined = prompt.strip()

    # Duration Check
    if duration not in valid_durations and duration != 30:
        if is_omni:
            warnings.append(
                f"Requested duration {duration}s is invalid for Omni. "
                "Omni supports odd/even durations: 4s, 6s, 8s, or 10s. Defaulting to 8s."
            )
            duration = 8
        else:
            warnings.append(
                f"Requested duration {duration}s exceeds Veo 3.1 max of 8s. Capping at 8s."
            )
            duration = 8

    # Photorealism elements check
    prompt_lower = prompt.lower()
    has_camera = any(w in prompt_lower for w in ["dolly", "tracking", "pan", "push", "zoom", "fpv", "crane", "close-up", "shot"])
    has_lighting = any(w in prompt_lower for w in ["lighting", "light", "rays", "shadow", "neon", "golden hour", "contrast", "volumetric"])
    has_lens = any(w in prompt_lower for w in ["lens", "35mm", "anamorphic", "depth of field", "4k", "photorealism"])

    if not has_camera:
        tips.append("Consider adding camera motion (e.g. 'Slow dolly push-in', 'FPV drone acceleration') to avoid static video.")
        refined += ", slow cinematic dolly forward push-in"
    if not has_lighting:
        tips.append("Consider specifying lighting (e.g. 'volumetric light rays', 'dramatic high contrast moody lighting').")
        refined += ", dramatic cinematic lighting"
    if not has_lens:
        tips.append("Consider specifying lens characteristics (e.g. '35mm anamorphic lens, shallow depth of field, 4K resolution').")
        refined += ", 35mm lens, 4K crisp resolution"

    # Keyframe guidance
    if has_start_frame and not has_end_frame:
        tips.append("Tip: You provided a Starting Frame (0s). Adding an Ending Frame allows Gemini Omni to compute smooth temporal morphing.")

    return {
        "is_valid": len(warnings) == 0,
        "warnings": warnings,
        "education_tips": tips,
        "original_prompt": prompt,
        "refined_prompt": refined,
        "model": model,
        "duration": duration,
        "supported_durations": valid_durations
    }


def format_download_filename(
    project_name: str,
    model: str,
    duration: int,
    has_start_frame: bool,
    has_end_frame: bool,
    prompt_slug: str,
    extension: str = "mp4"
) -> str:
    """
    Constructs a structured, professional naming convention for downloaded assets:
    [Project]_[Model]_[Duration]s_[Keyframes]_[Slug]_[Timestamp].mp4
    """
    clean_proj = "".join(c if c.isalnum() else "_" for c in project_name.strip()).strip("_") or "FlowProject"
    clean_model = "OmniFlash" if "flash" in model.lower() else ("Veo31" if "veo" in model.lower() else "Omni")
    
    kf_tag = "StartEnd" if (has_start_frame and has_end_frame) else ("StartFrame" if has_start_frame else ("EndFrame" if has_end_frame else "Prompt"))
    clean_slug = "".join(c if c.isalnum() else "_" for c in prompt_slug.strip().lower())[:25].strip("_")
    ts = time.strftime("%Y%m%d_%H%M%S")
    
    return f"{clean_proj}_{clean_model}_{duration}s_{kf_tag}_{clean_slug}_{ts}.{extension}"


# ---------------------------------------------------------------------------
# Flow page helpers (best effort; the Flow UI changes often, so every step has
# fallbacks and failures are reported, never silently waited on).
# ---------------------------------------------------------------------------

EDITOR_SELECTORS = [
    "div.ProseMirror[aria-label='What do you want to create?']",
    "[contenteditable='true'][aria-label*='create' i]",
    "div.ProseMirror[contenteditable='true']",
    "textarea[placeholder*='create' i]",
    "[contenteditable='true']",
]
SEND_SELECTORS = [
    "button:has-text('arrow_forward')",
    "button[aria-label*='Send' i]",
    "button[aria-label*='Submit' i]",
    "button[aria-label*='Create' i]",
]

MODEL_LABELS = {
    "omni_flash": "Gemini Omni Flash 1.1",
    "gemini_omni": "Gemini Omni",
    "veo_3_1": "Veo 3.1",
}

MEDIA_JS = r"""() => {
  const out = [];
  let videos = 0;
  document.querySelectorAll('video').forEach(v => {
    const s = v.currentSrc || v.src || ((v.querySelector('source') || {}).src) || '';
    if (s) { out.push(s); videos++; }
  });
  document.querySelectorAll('img').forEach(i => {
    const a = (i.alt || '').toLowerCase();
    if (a.includes('video') || a.includes('generated')) out.push('img:' + (i.currentSrc || i.src));
  });
  const pct = ((document.body && document.body.innerText) || '').match(/\b(\d{1,3})\s?%/g) || [];
  return {media: out, videos: videos, pct: pct.slice(0, 20)};
}"""

CHAT_JS = r"""() => {
  const ed = document.querySelector("div.ProseMirror[contenteditable='true'], [contenteditable='true']");
  if (!ed) return '';
  let el = ed, best = null;
  for (let i = 0; i < 14 && el; i++) {
    el = el.parentElement;
    if (!el) break;
    const r = el.getBoundingClientRect();
    if (r.height > window.innerHeight * 0.45 && r.width < window.innerWidth * 0.7) { best = el; break; }
  }
  if (!best) return '';
  const clone = (best.innerText || '');
  return clone.slice(-8000);
}"""


def _norm(text: str) -> str:
    return " ".join((text or "").split()).lower()


def _chat_lines(text: str) -> List[str]:
    return [l.strip() for l in (text or "").splitlines() if len(l.strip()) >= 2]


def _new_chat_lines(prev: List[str], now: List[str], sent: str) -> List[str]:
    """Lines Flow's chat gained since the last look (repeats count; our own request is left out)."""
    import difflib
    out: List[str] = []
    sent_n = _norm(sent)
    sm = difflib.SequenceMatcher(a=prev, b=now, autojunk=False)
    for op, _a1, _a2, b1, b2 in sm.get_opcodes():
        if op not in ("insert", "replace"):
            continue
        for line in now[b1:b2]:
            n = _norm(line)
            if len(n) < 4 or n in sent_n or (len(n) > 40 and sent_n[:40] in n):
                continue
            out.append(line)
    return out


async def _first_visible(page, selectors, timeout_ms=20000):
    deadline = time.time() + timeout_ms / 1000
    while time.time() < deadline:
        for sel in selectors:
            loc = page.locator(sel).first
            try:
                if await loc.count() > 0 and await loc.is_visible():
                    return loc
            except Exception:
                continue
        await asyncio.sleep(0.5)
    return None


def compose_flow_request(prompt: str, model: str, duration: int, aspect: str,
                         start_frame: Optional[str] = None, end_frame: Optional[str] = None,
                         attached: Optional[List[str]] = None) -> str:
    """The plain-language request Flow's agent understands."""
    model_label = MODEL_LABELS.get(model, model)
    lines = [f"Generate 1 video with {model_label}, {duration} seconds long, aspect ratio {aspect}."]
    attached = attached or []
    if "first" in attached and "last" in attached:
        lines.append("Use the first attached image as the first frame and the second attached image as the last frame.")
    elif "first" in attached:
        lines.append("Use the attached image as the first frame.")
    elif "last" in attached:
        lines.append("Use the attached image as the last frame.")
    if start_frame and end_frame:
        lines.append(f"Use {start_frame} as the first frame and {end_frame} as the last frame.")
    elif start_frame:
        lines.append(f"Use {start_frame} as the first frame.")
    elif end_frame:
        lines.append(f"Use {end_frame} as the last frame.")
    lines.append("Do not add on-screen text.")
    lines.append("")
    lines.append(f"Prompt: {prompt.strip()}")
    return "\n".join(lines)


GENERATIONS_FILE = BASE_DIR / "downloads" / "generations.json"
DOWNLOADS_ROOT = BASE_DIR / "downloads"


def downloads_url(path: Path) -> Optional[str]:
    """URL the dashboard serves a file from (/downloads/...), or None if it's outside downloads."""
    try:
        rel = Path(path).resolve().relative_to(DOWNLOADS_ROOT.resolve())
    except Exception:
        return None
    from urllib.parse import quote
    return "/downloads/" + quote(rel.as_posix())


def load_generations() -> List[Dict[str, Any]]:
    try:
        return json.loads(GENERATIONS_FILE.read_text(encoding="utf-8"))
    except Exception:
        return []


def _save_generation(record: Dict[str, Any]) -> None:
    items = [g for g in load_generations() if g.get("id") != record.get("id")]
    items.insert(0, record)
    GENERATIONS_FILE.parent.mkdir(parents=True, exist_ok=True)
    GENERATIONS_FILE.write_text(json.dumps(items[:200], indent=2), encoding="utf-8")


async def _attach_references(page, paths: List[str]) -> bool:
    """Attach reference images to Flow's prompt (file input, or the add/upload button's file chooser)."""
    paths = [p for p in paths if p and Path(p).exists()]
    if not paths:
        return False
    inp = page.locator("input[type='file']")
    try:
        if await inp.count() > 0:
            await inp.first.set_input_files(paths)
            await page.wait_for_timeout(2500)
            return True
    except Exception:
        pass
    for sel in ("button[aria-label*='Add' i]", "button[aria-label*='Upload' i]", "button[aria-label*='Attach' i]",
                "button:has-text('add_2')", "button:has-text('add')"):
        btn = page.locator(sel).first
        try:
            if await btn.count() == 0 or not await btn.is_visible():
                continue
            async with page.expect_file_chooser(timeout=6000) as fc:
                await btn.click()
            chooser = await fc.value
            await chooser.set_files(paths)
            await page.wait_for_timeout(2500)
            return True
        except Exception:
            continue
    return False


class JobCancelled(Exception):
    pass


class FlowJobRunner:
    """Runs one Flow generation at a time in the Ashzo Browser, with live progress."""

    def __init__(self) -> None:
        self.job: Optional[Dict[str, Any]] = None
        self._task: Optional[asyncio.Task] = None

    def busy(self) -> bool:
        return bool(self._task and not self._task.done())

    def status(self) -> Dict[str, Any]:
        if not self.job:
            return {"state": "idle"}
        return {k: v for k, v in self.job.items() if not k.startswith("_")}

    async def start(self, request: Dict[str, Any], output_dir: Optional[Path] = None) -> Dict[str, Any]:
        if self.busy():
            return {"status": "busy", "message": "A video is already being generated. Cancel it or wait for it to finish.",
                    "job": self.status()}
        import uuid
        title = (request.get("slug") or "video").strip() or "video"
        refs = []
        for role, name_key, path_key in (("first", "starting_frame", "starting_frame_path"), ("last", "ending_frame", "ending_frame_path")):
            path = request.get(path_key)
            if path or request.get(name_key):
                refs.append({"role": role, "name": request.get(name_key) or (Path(path).name if path else None),
                             "url": downloads_url(Path(path)) if path else None})
        model = request.get("model") or "omni_flash"
        self.job = {
            "id": uuid.uuid4().hex[:10],
            "title": title,
            "prompt": (request.get("prompt") or "").strip(),
            "model": model,
            "model_label": MODEL_LABELS.get(model, model),
            "duration": str(request.get("duration") or "8"),
            "aspect_ratio": request.get("aspect_ratio") or "9:16",
            "quality": request.get("download_quality") or "1080p",
            "references": refs,
            "source": request.get("source") or "dashboard",
            "state": "queued",
            "progress": 0,
            "message": "Queued",
            "chat": [],
            "started_at": int(time.time() * 1000),
            "files": [],
            "_cancel": False,
        }
        await self._publish_card()
        self._task = asyncio.create_task(self._run(dict(request), output_dir or DEFAULT_DOWNLOADS))
        return {"status": "started", "job": self.status()}

    async def cancel(self) -> Dict[str, Any]:
        if not self.busy():
            return {"status": "idle"}
        self.job["_cancel"] = True
        return {"status": "cancelling", "job": self.status()}

    async def wait(self) -> Dict[str, Any]:
        if self._task:
            try:
                await self._task
            except Exception:
                pass
        return self.status()

    # ------------------------------------------------------------------
    def card(self) -> Dict[str, Any]:
        return {k: v for k, v in (self.job or {}).items() if not k.startswith("_")}

    async def _publish_card(self, save: bool = True) -> None:
        """One live 'generation' card per job: prompt, references, Flow chat, progress, finished files."""
        card = self.card()
        if save:
            try:
                _save_generation(card)
            except Exception as e:
                logger.debug("history save: %s", e)
        await live_broadcaster.broadcast("generation", card.get("message", ""), data=card)

    async def _emit(self, stage: str, message: str, progress: Optional[int] = None, event_type: str = "progress",
                    **data: Any) -> None:
        job = self.job or {}
        job["state"] = stage
        job["message"] = message
        if progress is not None:
            job["progress"] = progress
        payload = {"job_id": job.get("id"), "title": job.get("title"), "kind": "flow", "started_at": job.get("started_at")}
        payload.update(data)
        await live_broadcaster.broadcast(event_type, message, data=payload, stage=stage, progress=progress)
        await self._publish_card(save=stage in ("queued", "ready", "error", "cancelled", "submitting"))

    def _check_cancel(self) -> None:
        if self.job and self.job.get("_cancel"):
            raise JobCancelled()

    async def _run(self, req: Dict[str, Any], output_dir: Path) -> None:
        from ashzo_settings import load_settings
        from browser_hub import BrowserLaunchError, hub

        settings = load_settings()
        page = None
        try:
            prompt = (req.get("prompt") or "").strip()
            if not prompt:
                raise ValueError("The prompt is empty.")
            model = req.get("model") or "omni_flash"
            aspect = req.get("aspect_ratio") or settings.get("aspect_ratio", "9:16")
            quality = req.get("download_quality") or "1080p"
            dur_raw = str(req.get("duration") or "8")
            is_30s = dur_raw == "30s_ad"
            duration = 8 if is_30s else int(dur_raw)
            if "veo" in model and duration > 8:
                duration = 8
            project_url = req.get("project_url") or settings.get("flow_project_url") or "https://flow.google.com/"
            render_timeout = int(settings.get("render_timeout_seconds", 900))

            await self._emit("queued", f"Queued '{self.job['title']}': {MODEL_LABELS.get(model, model)}, {duration}s, {aspect}.", 5)
            await self._emit("connecting", "Opening Google Flow in the Ashzo Browser…", 10)
            try:
                page = await hub.open_page(project_url, reuse_host=True, front=False)
            except BrowserLaunchError as e:
                raise RuntimeError(str(e))
            await hub.start_screencast(page)
            await page.wait_for_timeout(2500)
            if "accounts.google.com" in page.url or "/about" in page.url:
                raise RuntimeError("Google Flow isn't signed in inside the Ashzo Browser. Click Connect, choose Google Flow and sign in once.")
            self._check_cancel()

            editor = await _first_visible(page, EDITOR_SELECTORS, 25000)
            if editor is None:
                raise RuntimeError("Couldn't find Flow's prompt box. Open your Flow project in Settings, or check Live View.")

            scenes = build_30s_storyboard(prompt, model) if is_30s else [
                ScenePrompt(scene_number=1, duration_seconds=duration, prompt=prompt,
                            starting_frame=req.get("starting_frame"), ending_frame=req.get("ending_frame"))]
            slug = "".join(c if c.isalnum() else "_" for c in self.job["title"].lower())[:30] or "video"
            folder = output_dir / f"{time.strftime('%Y%m%d_%H%M%S')}_{slug}"
            folder.mkdir(parents=True, exist_ok=True)

            for i, scene in enumerate(scenes, start=1):
                self._check_cancel()
                base = 15 + int(80 * (i - 1) / len(scenes))
                span = int(80 / len(scenes))
                label = f"scene {i}/{len(scenes)}" if len(scenes) > 1 else "your video"
                snap = await page.evaluate(MEDIA_JS)
                baseline = set(snap.get("media", []))
                baseline_count = int(snap.get("videos") or 0)
                chat_prev = _chat_lines(await page.evaluate(CHAT_JS) or "")

                attached: List[str] = []
                if i == 1:
                    paths = [req.get("starting_frame_path"), req.get("ending_frame_path")]
                    if any(paths):
                        await self._emit("submitting", "Adding your reference frames to Flow…", base + 1)
                        if await _attach_references(page, [p for p in paths if p]):
                            attached = [r for r, p in zip(("first", "last"), paths) if p]
                        else:
                            await live_broadcaster.broadcast("log", "Couldn't attach the reference images automatically; sending the prompt without them.",
                                                             data={"job_id": self.job["id"], "level": "warn"})
                message = compose_flow_request(scene.prompt, model, scene.duration_seconds, aspect,
                                               scene.starting_frame, scene.ending_frame, attached)
                self.job["sent_message"] = message
                await self._emit("submitting", f"Typing the request for {label} into Flow…", base + 2)
                await editor.click()
                try:
                    await editor.fill(message)
                except Exception:
                    await page.keyboard.press("Control+A")
                    await page.keyboard.press("Delete")
                    await page.keyboard.insert_text(message)
                await page.wait_for_timeout(600)
                sent = False
                for sel in SEND_SELECTORS:
                    btn = page.locator(sel).first
                    try:
                        if await btn.count() > 0 and await btn.is_enabled():
                            await btn.click()
                            sent = True
                            break
                    except Exception:
                        continue
                if not sent:
                    await page.keyboard.press("Enter")
                await self._emit("waiting", f"Sent to Flow's agent. Waiting for it to start {label}…", base + 5)

                start = time.time()
                found: Optional[str] = None
                last_pct = None
                while time.time() - start < render_timeout:
                    self._check_cancel()
                    await asyncio.sleep(2.5)
                    # Mirror Flow's agent chat
                    try:
                        chat_now = _chat_lines(await page.evaluate(CHAT_JS) or "")
                        for line in _new_chat_lines(chat_prev, chat_now, message):
                            self.job["chat"] = (self.job.get("chat") or [])[-40:] + [{"t": int(time.time() * 1000), "text": line}]
                            await live_broadcaster.broadcast("flow_chat", line, data={"job_id": self.job["id"], "role": "flow"})
                        chat_prev = chat_now
                    except Exception:
                        pass
                    snap = await page.evaluate(MEDIA_JS)
                    media = snap.get("media", [])
                    new = [m for m in media if m not in baseline]
                    videos = [m for m in new if not m.startswith("img:")]
                    all_videos = [m for m in media if not m.startswith("img:")]
                    if not videos and int(snap.get("videos") or 0) > baseline_count and all_videos:
                        videos = [all_videos[-1]]  # same address as an older clip, but there is one more video now
                    elapsed = int(time.time() - start)
                    pcts = [int(p.rstrip('% ').strip()) for p in snap.get("pct", []) if p.rstrip('% ').strip().isdigit()]
                    pcts = [p for p in pcts if 0 < p < 100]
                    if videos:
                        found = videos[0]
                        break
                    if pcts:
                        last_pct = max(pcts)
                    shown = f" · Flow shows {last_pct}%" if last_pct else ""
                    prog = base + 8 + int((span - 14) * (last_pct / 100 if last_pct else min(elapsed / max(render_timeout * 0.4, 1), 0.9)))
                    await self._emit("rendering", f"Rendering {label} · {elapsed // 60}:{elapsed % 60:02d}{shown}", prog)
                if not found:
                    raise TimeoutError(f"No new video appeared after {render_timeout // 60} minutes. Check Live View: Flow may be asking a question or out of credits.")

                await self._emit("downloading", f"Saving {label} to the vault…", base + span - 4)
                name = format_download_filename(self.job["title"], model, scene.duration_seconds,
                                                bool(scene.starting_frame), bool(scene.ending_frame), slug)
                target = folder / name
                saved_quality = await self._download(page, found, target, quality)
                size_mb = round(target.stat().st_size / 1024 / 1024, 2)
                self.job["files"].append({"name": name, "path": str(target), "url": downloads_url(target),
                                          "size_mb": size_mb, "scene": i})
                meta = {"title": self.job["title"], "scene": i, "model": model, "duration": scene.duration_seconds,
                        "aspect_ratio": aspect, "quality": saved_quality, "prompt": scene.prompt, "source": found[:300],
                        "saved_at": time.strftime("%Y-%m-%d %H:%M:%S")}
                (folder / (target.stem + ".json")).write_text(json.dumps(meta, indent=2), encoding="utf-8")
                await live_broadcaster.broadcast(
                    "video_ready", f"Saved {name} ({size_mb} MB)",
                    data={"job_id": self.job["id"], "filename": name, "size_mb": size_mb, "path": str(target), "kind": "flow"},
                    stage="ready" if i == len(scenes) else "rendering",
                    progress=100 if i == len(scenes) else base + span)
            n = len(self.job["files"])
            await self._emit("ready", f"Done · {n} video{'s' if n != 1 else ''} saved to the vault.", 100)
        except JobCancelled:
            await self._emit("cancelled", "Generation cancelled.", None)
        except Exception as e:
            logger.exception("Flow job failed")
            await self._emit("error", str(e) or e.__class__.__name__, None)
        finally:
            if page is not None:
                try:
                    await hub.snapshot(page)
                    await hub.stop_screencast(page)
                except Exception:
                    pass
            if self.job:
                self.job["finished_at"] = int(time.time() * 1000)

    async def _download(self, page, src: str, target: Path, quality: str) -> str:
        """Save the new video. Prefer the original file behind the player; fall back to Flow's Download menu."""
        if src.startswith("http"):
            resp = await page.context.request.get(src, timeout=120000)
            if resp.ok:
                target.write_bytes(await resp.body())
                return "original"
        if src.startswith("blob:"):
            b64 = await page.evaluate("""async (u) => {
                const b = await (await fetch(u)).blob();
                const buf = new Uint8Array(await b.arrayBuffer());
                let s = ''; const step = 0x8000;
                for (let i = 0; i < buf.length; i += step) s += String.fromCharCode.apply(null, buf.subarray(i, i + step));
                return btoa(s);
            }""", src)
            import base64 as _b64
            target.write_bytes(_b64.b64decode(b64))
            return "original"
        dl_btn = page.locator("button:has-text('download'), button[aria-label*='Download']").first
        if await dl_btn.count() == 0:
            raise RuntimeError("The new video appeared, but Ashzo couldn't download it. Download it from Flow by hand.")
        await dl_btn.click()
        await page.wait_for_timeout(800)
        option = page.locator(f"[role='menuitem']:has-text('{quality}'), button:has-text('{quality}')").first
        if await option.count() == 0:
            option = page.locator("[role='menuitem']:has-text('Original'), [role='menuitem']:has-text('720p')").first
        async with page.expect_download(timeout=180000) as info:
            await option.click()
        dl = await info.value
        await dl.save_as(str(target))
        return quality


flow_jobs = FlowJobRunner()


class FlowVideoAutomator:
    """Backwards-compatible wrapper: runs concepts one by one through the live job runner."""

    def __init__(self, project_url: Optional[str] = None, output_dir: Optional[Path] = None):
        self.project_url = project_url
        self.output_dir = output_dir or DEFAULT_DOWNLOADS
        self.output_dir.mkdir(parents=True, exist_ok=True)

    async def execute_batch_production(self, video_concepts: List[Dict[str, Any]], model: str = "omni_flash",
                                       download_quality: str = "1080p", duration_per_clip: int = 8,
                                       project_title: str = "UniversalWeb") -> Dict[str, Any]:
        results = []
        for item in video_concepts:
            req = {
                "prompt": item.get("concept") or item.get("title") or "",
                "model": model,
                "duration": "30s_ad" if item.get("is_30s_ad") else str(item.get("duration", duration_per_clip)),
                "download_quality": download_quality,
                "starting_frame": item.get("starting_frame"),
                "ending_frame": item.get("ending_frame"),
                "slug": item.get("title") or project_title,
                "project_url": self.project_url,
            }
            started = await flow_jobs.start(req, self.output_dir)
            if started.get("status") != "started":
                results.append(started)
                continue
            results.append(await flow_jobs.wait())
        return {"status": "done", "results": results}

    @staticmethod
    def rename_downloaded_video(existing_filepath: str, new_custom_name: str, root: Optional[Path] = None) -> Dict[str, Any]:
        """Rename a video inside the downloads folder (never outside it)."""
        root = (root or (BASE_DIR / "downloads")).resolve()
        old_path = Path(existing_filepath).resolve()
        if root not in old_path.parents:
            raise PermissionError("Only videos inside the downloads folder can be renamed.")
        if not old_path.exists():
            raise FileNotFoundError(f"File {old_path.name} does not exist.")
        clean = "".join(c for c in new_custom_name.strip() if c not in '\\/:*?"<>|').strip()
        if not clean:
            raise ValueError("The new name is empty.")
        if not clean.lower().endswith(".mp4"):
            clean += ".mp4"
        new_path = old_path.parent / clean
        if new_path.exists():
            raise FileExistsError(f"{clean} already exists.")
        old_path.rename(new_path)
        side = old_path.with_suffix(".json")
        if side.exists():
            side.rename(new_path.with_suffix(".json"))
        logger.info("Renamed %s -> %s", old_path.name, new_path.name)
        return {"status": "success", "old_name": old_path.name, "new_name": new_path.name, "new_path": str(new_path)}
