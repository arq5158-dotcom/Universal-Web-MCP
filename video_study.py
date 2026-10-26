"""
Video study (Steps 1-4 of VIDEO_RECREATION_SKILL.md), automated.

study_video(path) writes everything an agent needs to look at before writing a
recreation kit into one folder:

  study.json        duration, size, fps, audio, scene cuts, loudness per second, silences
  sheet_00.jpg ...  1 frame per second with timestamps, 24 per sheet (6x4)
  hook.jpg          the first 12 seconds at 2 fps
  ending.jpg        the last 10 seconds at 2 fps
  spectrogram.png   the whole soundtrack

The agent must still LOOK at every sheet (the skill's rule); this tool only makes
the pictures and numbers. Needs ffmpeg + ffprobe on PATH
(Windows: `winget install Gyan.FFmpeg`, macOS: `brew install ffmpeg`).
"""

from __future__ import annotations

import json
import math
import platform
import re
import shutil
import subprocess
import time
from pathlib import Path
from typing import Any, Dict, List, Optional

BASE_DIR = Path(__file__).resolve().parent
STUDIES_DIR = BASE_DIR / "downloads" / "studies"


class FfmpegMissing(RuntimeError):
    pass


def _tools() -> Dict[str, str]:
    ff, fp = shutil.which("ffmpeg"), shutil.which("ffprobe")
    if not ff or not fp:
        hint = {"Windows": "winget install Gyan.FFmpeg", "Darwin": "brew install ffmpeg"}.get(platform.system(), "sudo apt install ffmpeg")
        raise FfmpegMissing(f"ffmpeg is not installed. Install it ({hint}), restart the app, then try again.")
    return {"ffmpeg": ff, "ffprobe": fp}


def _run(args: List[str], timeout: int = 600) -> subprocess.CompletedProcess:
    return subprocess.run(args, capture_output=True, text=True, timeout=timeout)


def _timestamp_filter(size: int) -> str:
    """drawtext with a font that exists on this OS (Windows ffmpeg builds often have no default font)."""
    font = ""
    if platform.system() == "Windows":
        font = "fontfile='C\\:/Windows/Fonts/arial.ttf':"
    return (f"drawtext={font}text='%{{pts\\:hms}}':x=4:y=4:fontsize={size}:fontcolor=yellow:"
            f"box=1:boxcolor=black@0.6")


def _sheet(t: Dict[str, str], src: str, out: Path, fps: float, start: float, length: float, cols: int, rows: int,
           width: int = 192) -> bool:
    base = f"fps={fps},scale={width}:-2"
    for with_time in (True, False):
        vf = base + ("," + _timestamp_filter(14) if with_time else "") + f",tile={cols}x{rows}:padding=4:margin=4"
        r = _run([t["ffmpeg"], "-hide_banner", "-loglevel", "error", "-y", "-ss", f"{start:.2f}", "-t", f"{length:.2f}",
                  "-i", src, "-vf", vf, "-frames:v", "1", "-q:v", "3", str(out)])
        if r.returncode == 0 and out.exists():
            return True
    return False


def study_video(path: str, out_dir: Optional[str] = None) -> Dict[str, Any]:
    t = _tools()
    src = Path(path).expanduser().resolve()
    if not src.exists():
        raise FileNotFoundError(f"No video at {src}")
    out = Path(out_dir).expanduser().resolve() if out_dir else STUDIES_DIR / f"{src.stem}_{time.strftime('%Y%m%d_%H%M%S')}"
    out.mkdir(parents=True, exist_ok=True)

    # Step 1: properties
    probe = _run([t["ffprobe"], "-v", "error", "-show_entries",
                  "format=duration,size,bit_rate:stream=codec_type,codec_name,width,height,r_frame_rate,nb_frames,sample_rate,channels",
                  "-of", "json", str(src)])
    info = json.loads(probe.stdout or "{}")
    duration = float((info.get("format") or {}).get("duration") or 0)
    streams = info.get("streams", [])
    video = next((s for s in streams if s.get("codec_type") == "video"), {})
    has_audio = any(s.get("codec_type") == "audio" for s in streams)

    # Step 2: scene cuts at two thresholds + 1 fps contact sheets
    cuts: Dict[str, List[float]] = {}
    for thr in ("0.25", "0.22"):
        r = _run([t["ffmpeg"], "-hide_banner", "-i", str(src), "-vf", f"select='gt(scene,{thr})',showinfo", "-an", "-f", "null", "-"])
        cuts[thr] = [round(float(x), 2) for x in re.findall(r"pts_time:([0-9.]+)", r.stderr)]
    sheets = []
    per = 24
    for i in range(max(1, math.ceil(duration / per))):
        f = out / f"sheet_{i:02d}.jpg"
        if _sheet(t, str(src), f, 1, i * per, per, 6, 4):
            sheets.append({"file": f.name, "from_s": i * per, "to_s": min((i + 1) * per, duration)})

    # Step 3: hook and ending at 2 fps
    hook = out / "hook.jpg"
    _sheet(t, str(src), hook, 2, 0, min(12, duration), 6, 4)
    ending = out / "ending.jpg"
    _sheet(t, str(src), ending, 2, max(0.0, duration - 10), min(10, duration), 6, 4)

    # Step 4: sound
    loudness: List[int] = []
    silences: List[Dict[str, float]] = []
    spectrogram = None
    if has_audio:
        spec = out / "spectrogram.png"
        _run([t["ffmpeg"], "-hide_banner", "-loglevel", "error", "-y", "-i", str(src), "-lavfi",
              "showspectrumpic=s=1200x400:legend=0:color=intensity:scale=log", str(spec)])
        spectrogram = spec.name if spec.exists() else None
        r = _run([t["ffmpeg"], "-hide_banner", "-i", str(src), "-af",
                  "astats=metadata=1:reset=1,aresample=1,ametadata=print:key=lavfi.astats.Overall.RMS_level", "-f", "null", "-"])
        vals = re.findall(r"RMS_level=(-?[0-9.]+|-inf)", r.stderr)
        loudness = [(-120 if v == "-inf" else int(float(v))) for v in vals][: int(duration) + 2]
        r = _run([t["ffmpeg"], "-hide_banner", "-i", str(src), "-af", "silencedetect=n=-40dB:d=0.3", "-f", "null", "-"])
        starts = re.findall(r"silence_start: ([0-9.]+)", r.stderr)
        ends = re.findall(r"silence_end: ([0-9.]+)", r.stderr)
        silences = [{"start": round(float(a), 2), "end": round(float(b), 2)} for a, b in zip(starts, ends)]

    result = {
        "source": str(src),
        "folder": str(out),
        "duration_s": round(duration, 2),
        "resolution": f"{video.get('width')}x{video.get('height')}" if video else None,
        "fps": video.get("r_frame_rate"),
        "frames": video.get("nb_frames"),
        "has_audio": has_audio,
        "scene_cuts": cuts,
        "contact_sheets": sheets,
        "hook_sheet": hook.name if hook.exists() else None,
        "ending_sheet": ending.name if ending.exists() else None,
        "spectrogram": spectrogram,
        "loudness_db_per_second": loudness,
        "silences": silences,
        "next": ("Open and look at EVERY contact sheet, hook.jpg, ending.jpg and the spectrogram, keep a shot log, "
                 "then follow Steps 5-8 of VIDEO_RECREATION_SKILL.md. Scene cuts are hints, not truth."),
    }
    (out / "study.json").write_text(json.dumps(result, indent=2), encoding="utf-8")
    return result


if __name__ == "__main__":
    import sys
    print(json.dumps(study_video(sys.argv[1], sys.argv[2] if len(sys.argv) > 2 else None), indent=2))
