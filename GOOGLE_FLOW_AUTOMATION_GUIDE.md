# Google Flow Video Automation Guide 🎬⚡

This guide explains how **Universal-Web-MCP** automates batch video generation on **Google Flow**, generates 30-second multi-scene commercials, enforces specific model choices (**Google Veo** vs **Omni 1.1 Flash**), and automatically downloads all generated `.mp4` video files directly to your local PC.

---

## 🧠 1. Model Capabilities & Selection Guide

Google Flow exposes two primary generative video models:

| Model | Code / Name | Max Duration | Strengths & Visual Character | Best For |
| :--- | :--- | :--- | :--- | :--- |
| **Google Veo** | `veo_1` | **8 Seconds** | Ultra-high cinematic realism, accurate lighting, complex fluid/particle dynamics, 35mm lens depth of field | Hero commercials, cinematic storytelling, brand ads |
| **Omni 1.1 Flash** | `abra_t2v_10s` | **10 Seconds** | High-speed generation, rapid throughput, energetic motion, prompt responsiveness | High-volume batch generation (10-20 videos), social media shorts, rapid iteration |
| **Imagen 3** | `imagen_3` | Still Image | 4K visual keyframing and character consistency | Pre-generating reference images before video animation |

> **Model Adherence Rule:**  
> When the user specifies `model="veo"` or `model="omni_flash"`, the automator **strictly enforces** model-specific camera instructions and clip duration limits (8s for Veo, 10s for Omni Flash).

---

## ⏱️ 2. The 30-Second Video Formula

Current state-of-the-art video AI models cannot generate a full 30-second clip in a single prompt (the limit is 8 to 10 seconds per generation).  
The pipeline automatically decomposes any 30-second commercial idea into **4 cohesive scenes**:

```
[00:00 - 00:08] Scene 1: The Hook & Tension (8 seconds)
↳ Extreme close-up, dramatic lighting, establishes the problem/frustration.

[00:08 - 00:16] Scene 2: The Breakthrough (8 seconds)
↳ Dynamic tracking shot, particle acceleration, reveals the solution.

[00:16 - 00:24] Scene 3: The Feature Demonstration (8 seconds)
↳ Orbiting camera shot, sleek workstation, technology running in real-time.

[00:24 - 00:30] Scene 4: Climax & Call To Action (6 seconds)
↳ Pull-back camera reveal, glowing holographic logo and URL.
```

---

## 🚀 3. How to Batch Generate 10–20 Videos Automatically

Run the batch automation engine using [`flow_video_automator.py`](flow_video_automator.py):

```python
import asyncio
from flow_video_automator import FlowVideoAutomator

# Define your project URL
PROJECT_URL = "https://flow.google.com/project/5730a6a6-a00a-4a95-8f22-20942efd1413"

automator = FlowVideoAutomator(project_url=PROJECT_URL)

# List 10 to 20 video ideas
batch_concepts = [
    {
        "title": "Universal-Web-MCP Launch",
        "concept": "AI agents bypassing slow browser automation with sub-second JSON streams"
    },
    {
        "title": "Sub-200ms Fast Path",
        "concept": "Visualizing requests bypassing DOM reflow and executing directly on APIs"
    },
    {
        "title": "Chrome Cookie Sync",
        "concept": "Bypassing login walls and bot detection using pre-authenticated local sessions"
    },
    # ... Add up to 20 video concepts here
]

# Run batch generation with chosen model ("veo" or "omni_flash")
asyncio.run(
    automator.execute_batch_production(
        video_concepts=batch_concepts,
        model="veo",            # Or "omni_flash"
        download_quality="720p" # Or "1080p"
    )
)
```

---

## 💾 4. Local File Organization (Downloaded to PC)

The pipeline automatically monitors rendering progress, clicks the download button, chooses the quality (`720p` or `1080p`), and organizes all files on your local drive:

```text
Universal-Web-MCP/
└── downloads/
    └── flow_production/
        ├── batch_manifest.json          # Master log of all generated videos
        ├── 01_universal_web_mcp_launch/
        │   ├── metadata.json            # Exact prompts, timestamps, model used
        │   └── universal_web_mcp_scene_1.mp4
        ├── 02_sub_200ms_fast_path/
        │   ├── metadata.json
        │   └── sub_200ms_fast_path_scene_1.mp4
        └── ...
```

---

## 🔑 5. One-Time Setup & Authentication

Anyone running this engine **never wastes time configuring auth**:

1. **If already logged in:**  
   The authenticated session is permanently stored in `flow_auth_state.json` and `session_cookies.json`. The pipeline runs headlessly and automatically.
2. **If setting up a new account or machine:**  
   Run:
   ```bash
   python auth_flow.py
   ```
   Or click **"1-Click Google Login"** on the Web Dashboard (`http://localhost:8000`). Sign in once, and the session is captured for all future batch runs!
