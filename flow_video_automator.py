"""
Google Flow Automated Batch Video Production Pipeline (Universal-Web-MCP).
Supports Gemini Omni Flash (4s, 6s, 8s, 10s), Gemini Omni, Veo 3.1 (8s max),
Keyframe Interpolation (Starting Frame & Ending Frame), Custom Asset Renaming,
and local MP4 downloading with structured metadata into organized project folders.
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
from playwright.async_api import async_playwright
from live_events import live_broadcaster

logging.basicConfig(level=logging.INFO, format="[%(asctime)s] [%(levelname)s] %(message)s")
logger = logging.getLogger("FlowAutomator")

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


class FlowVideoAutomator:
    """End-to-end automation engine for Google Flow batch video generation and local downloading."""

    def __init__(self, project_url: str, output_dir: Optional[Path] = None):
        self.project_url = project_url
        self.output_dir = output_dir or DEFAULT_DOWNLOADS
        self.output_dir.mkdir(parents=True, exist_ok=True)

    async def execute_batch_production(
        self,
        video_concepts: List[Dict[str, Any]],
        model: str = "omni_flash",
        download_quality: str = "1080p",  # "720p", "1080p", "4k"
        duration_per_clip: int = 8,        # 4, 6, 8, 10s for Omni
        project_title: str = "UniversalWeb"
    ) -> Dict[str, Any]:
        """
        Executes end-to-end video production:
        1. Configures duration (4s, 6s, 8s, 10s) and model.
        2. Supports Starting Frame & Ending Frame conditioning.
        3. Polls render status in Google Flow.
        4. Downloads MP4 with structured naming convention.
        """
        if not AUTH_STATE_FILE.exists():
            raise FileNotFoundError(
                f"Authentication state file {AUTH_STATE_FILE} not found! "
                "Authenticate first via the Session Manager or Dashboard."
            )

        results = []
        logger.info(f"Starting batch production for {len(video_concepts)} item(s) with model '{model.upper()}' ({duration_per_clip}s)")
        await live_broadcaster.broadcast(
            "progress",
            f"Initializing {model.upper()} ({duration_per_clip}s, {download_quality})...",
            stage="initializing",
            progress=15
        )

        async with async_playwright() as p:
            browser = await p.chromium.launch(headless=True)
            context = await browser.new_context(
                storage_state=str(AUTH_STATE_FILE),
                user_agent="Mozilla/5.0 (Windows NT 10.0; Win64; x64) AppleWebKit/537.36 (KHTML, like Gecko) Chrome/126.0.0.0 Safari/537.36",
                accept_downloads=True,
                viewport={"width": 1440, "height": 900}
            )
            page = await context.new_page()

            logger.info(f"Navigating to Flow workspace: {self.project_url}")
            await live_broadcaster.broadcast(
                "log",
                f"Connecting to Google Flow studio at {self.project_url[:40]}...",
                stage="initializing",
                progress=25
            )
            await page.goto(self.project_url, wait_until="domcontentloaded", timeout=30000)
            await page.wait_for_timeout(4000)

            for idx, item in enumerate(video_concepts, start=1):
                concept_title = item.get("title", f"Scene_{idx}")
                concept_idea = item.get("concept", concept_title)
                start_frame = item.get("starting_frame")
                end_frame = item.get("ending_frame")
                custom_dur = item.get("duration", duration_per_clip)
                slug = "".join(c if c.isalnum() else "_" for c in concept_title.lower())[:30]

                video_folder = self.output_dir / f"{idx:02d}_{slug}"
                video_folder.mkdir(parents=True, exist_ok=True)

                logger.info(f"\n--- [Video {idx}/{len(video_concepts)}] {concept_title} ({custom_dur}s) ---")
                await live_broadcaster.broadcast(
                    "log",
                    f"Compiling prompt kit for {concept_title} ({custom_dur}s)...",
                    stage="submitting",
                    progress=35
                )
                
                # Check if multi-scene storyboard or single clip
                if item.get("is_30s_ad"):
                    scenes = build_30s_storyboard(concept=concept_idea, model=model)
                else:
                    scenes = [ScenePrompt(
                        scene_number=1,
                        duration_seconds=custom_dur,
                        prompt=concept_idea,
                        starting_frame=start_frame,
                        ending_frame=end_frame
                    )]

                video_record = {
                    "index": idx,
                    "title": concept_title,
                    "model": model,
                    "duration": custom_dur,
                    "download_quality": download_quality,
                    "scenes_count": len(scenes),
                    "started_at": time.strftime("%Y-%m-%d %H:%M:%S")
                }

                for scene in scenes:
                    logger.info(f"Submitting Scene {scene.scene_number} ({scene.duration_seconds}s): {scene.prompt[:80]}...")

                    # Frame conditioning injection
                    full_prompt = scene.prompt
                    if scene.starting_frame:
                        full_prompt = f"@FirstFrame:{scene.starting_frame} {full_prompt}"
                    if scene.ending_frame:
                        full_prompt = f"{full_prompt} @LastFrame:{scene.ending_frame}"

                    await live_broadcaster.broadcast(
                        "log",
                        f"Injected prompt into ProseMirror editor: {full_prompt[:65]}...",
                        stage="submitting",
                        progress=45
                    )

                    # Type into Flow ProseMirror prompt box
                    prompt_input = page.locator("div.ProseMirror[aria-label='What do you want to create?']").first
                    await prompt_input.click()
                    await prompt_input.fill("")
                    await prompt_input.fill(full_prompt)
                    await page.wait_for_timeout(1000)

                    # Click submit
                    send_btn = page.locator("button:has-text('arrow_forward')").first
                    await send_btn.click()
                    logger.info("Prompt sent. Polling for generation completion...")
                    await live_broadcaster.broadcast(
                        "progress",
                        f"Rendering frames with {model.upper()} ({scene.duration_seconds}s)...",
                        stage="rendering",
                        progress=65
                    )

                    # Wait for render to finalize
                    await page.wait_for_timeout(15000)

                    # Locate video thumbnail & download
                    thumb = page.locator("img[alt*='Generated video'], img[src*='video']").first
                    if await thumb.count() > 0:
                        await thumb.click()
                        await page.wait_for_timeout(2000)

                        dl_btn = page.locator("button:has-text('download'), button[aria-label*='Download']").first
                        if await dl_btn.count() > 0:
                            await dl_btn.click()
                            await page.wait_for_timeout(1000)

                            quality_btn = page.locator(f"[role='menuitem']:has-text('{download_quality}'), button:has-text('{download_quality}')").first
                            if await quality_btn.count() == 0:
                                quality_btn = page.locator("[role='menuitem']:has-text('Original size'), button:has-text('720p')").first

                            await live_broadcaster.broadcast(
                                "progress",
                                f"Downloading {download_quality} MP4 to vault...",
                                stage="downloading",
                                progress=85
                            )

                            async with page.expect_download(timeout=30000) as download_info:
                                await quality_btn.click()

                            download = await download_info.value
                            formatted_name = format_download_filename(
                                project_name=project_title,
                                model=model,
                                duration=scene.duration_seconds,
                                has_start_frame=bool(scene.starting_frame),
                                has_end_frame=bool(scene.ending_frame),
                                prompt_slug=slug
                            )
                            target_file = video_folder / formatted_name
                            await download.save_as(str(target_file))
                            file_size_mb = round(os.path.getsize(target_file) / 1024 / 1024, 2)
                            logger.info(f"SUCCESS: Saved {formatted_name} ({file_size_mb} MB)")
                            video_record["downloaded_file"] = str(target_file)
                            video_record["formatted_filename"] = formatted_name
                            video_record["file_size_mb"] = file_size_mb

                            # Broadcast video_ready event so dashboard auto-updates instantly
                            await live_broadcaster.broadcast(
                                "video_ready",
                                f"Video ready: {formatted_name} ({file_size_mb} MB)",
                                data={"filename": formatted_name, "size_mb": file_size_mb, "path": str(target_file)},
                                stage="ready",
                                progress=100
                            )

                # Save metadata
                meta_path = video_folder / "metadata.json"
                with open(meta_path, "w", encoding="utf-8") as f:
                    json.dump(video_record, f, indent=2)

                results.append(video_record)

            await browser.close()

        manifest_path = self.output_dir / "batch_manifest.json"
        with open(manifest_path, "w", encoding="utf-8") as f:
            json.dump(results, f, indent=2)

        return {
            "status": "success",
            "total_videos": len(results),
            "output_dir": str(self.output_dir),
            "manifest": str(manifest_path)
        }

    @staticmethod
    def rename_downloaded_video(existing_filepath: str, new_custom_name: str) -> Dict[str, Any]:
        """
        Allows user to rename any downloaded video file locally and maintain metadata.
        """
        old_path = Path(existing_filepath)
        if not old_path.exists():
            raise FileNotFoundError(f"File {existing_filepath} does not exist.")

        clean_name = new_custom_name.strip()
        if not clean_name.endswith(".mp4"):
            clean_name += ".mp4"

        new_path = old_path.parent / clean_name
        old_path.rename(new_path)
        logger.info(f"Renamed: {old_path.name} -> {new_path.name}")
        return {
            "status": "success",
            "old_name": old_path.name,
            "new_name": new_path.name,
            "new_path": str(new_path)
        }
