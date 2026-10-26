# Google Flow Skill: The Complete Platform Knowledge Base 🎬🧠

> **Skill Purpose:** The operating manual for Google Flow (`flow.google.com`) inside Ashzo MCP: how an agent must run Flow (visibly, with live progress), which models and lengths exist, how first/last frames work, file naming, and how to talk to the user. Read sections 0 and 0.5 before doing anything in Flow.

---

## 🚦 0. How agents must run Flow (mandatory)

1. **Always through Ashzo MCP's tools, never a hidden browser of your own.** Use `flow_generate_video` (then `flow_job_status` / `flow_cancel_job`). It drives Flow in the **Ashzo Browser**, a real Chrome window on the user's PC, and streams everything to the dashboard (http://localhost:8000): the prompt you sent, reference frames, Flow agent's replies, a progress bar, Live View pictures of the browser, and the finished video. The user must be able to watch your work without refreshing anything.
2. **Tell the user where to watch** the first time in a session: "Open Ashzo MCP (desktop icon or http://localhost:8000). Your generation shows up live under Google Flow." If the dashboard is not running, call `open_live_view` or ask them to double-click the **Ashzo MCP** desktop icon.
3. **Signed out?** `flow_generate_video` stops with a clear message. Ask the user to press **Connect** in the dashboard and sign in once in the Ashzo Browser window. Never type the user's password yourself.
4. **Credits:** call `get_flow_account_credits`. Show the number it returns. If it says the balance couldn't be read, say so. Never invent a balance, a plan name or an email.
5. **One job at a time.** If `flow_generate_video` says another video is being made, wait (`flow_job_status`) or ask before cancelling.
6. **Report honestly:** file path, size, and what Flow's agent said. If a step failed (prompt box not found, no new video before the timeout, download failed), quote the error and point the user to Live View. Don't report success you didn't see.
7. **No anti-bot workarounds.** Flow has no public API. Don't bypass reCAPTCHA or other checks; the "Learn Flow's API" recorder only records what Flow's own site sends, for a person to review.

## 🎯 0.5. Recreating or adapting an existing video (mandatory)

When the user sends a video (or a link) and wants it recreated, remixed, split into clips or turned into prompts, follow **[VIDEO_RECREATION_SKILL.md](VIDEO_RECREATION_SKILL.md) step by step**. Every time, no shortcuts:

1. Call `study_video(path)`. It writes contact sheets (1 frame per second), the hook and ending sheets, scene cuts, loudness and a spectrogram.
2. **Look at every sheet** before writing a single prompt. The cut list is a hint, not the truth.
3. Write the shot log and story map, decide clip lengths that fit the models below (Omni Flash ≤10 s, Veo 3.1 ≤8 s), then write the kit as the skill describes: first/last frame image prompts, video prompts with the "everything rendered correctly" clauses, and the user's own character (e.g. Lia) where they asked for it.
4. Generate with `flow_generate_video` (attach the first/last frames via `starting_frame_image` / `ending_frame_image`) so the user watches each clip being made.
5. When a clip comes out wrong, use Step 8 of the skill (fix the prompt for that clip only), not a full restart.

---

## 🏛️ 1. Platform Architecture & Core Modes

Google Flow operates in two primary execution modes:

### A. Agent Mode (Creative Co-Pilot)
- **Role:** Interactive creative partner powered by Gemini's multimodal assistant.
- **Capabilities:**
  - Suggests scene breakdowns and storyboard scripts based on project context.
  - Assembles complex 30-second commercials scene-by-scene.
  - Suggests character backstories, lighting styles, camera motions, and audio pacing.
- **Trigger:** Active in the project chat/storyboard canvas.

### B. Direct Mode (Raw Generative Pipeline)
- **Role:** Direct model prompting without assistant dialogue.
- **Capabilities:**
  - Bypasses conversational confirmation dialogs.
  - Sends direct generation tokens straight to the rendering queue.
  - Ideal for high-speed programmatic batch processing via Universal-Web-MCP.

---

## 🎥 2. Generative Models, Clip Durations & Aspect Ratios

| Model (as named in Flow) | Video lengths | Strength | Good for |
| :--- | :--- | :--- | :--- |
| **Gemini Omni Flash 1.1** | **4, 6, 8, 10 s** (video-to-video: up to 10 s) | Fast, follows prompts closely, lively motion | Most clips, batches, quick iterations |
| **Gemini Omni** | **4, 6, 8, 10 s** | Strong world understanding, multimodal input, conversational edits | First/last-frame clips, edits |
| **Veo 3.1** (Lite / Fast / Quality) | **4, 6, 8 s** | Realism, physics, native audio | Hero shots, photoreal scenes |

Image models in Flow (for first/last frames, characters) are separate from these and make **stills, not video**. Nano Banana Pro is an image model.
Model names and limits change: if Flow's model menu shows something different, trust Flow and tell the user.

### Supported Aspect Ratios:
- `16:9` (Standard Landscape — YouTube, Commercials, Desktop)
- `9:16` (Vertical — Shorts, TikTok, Instagram Reels)
- `1:1` (Square — Social feeds)
- `4:3` & `3:4` (Retro / Academy frame)

---

## 🎞️ 3. Starting Frames, Ending Frames & Keyframe Interpolation

Google Flow and Gemini Omni excel in **Keyframe-to-Video Interpolation**:

### A. First Frame (Starting Frame — `t = 0.0s`)
- **Function:** Establishes the exact initial composition, lighting, subject position, and style.
- **How to provide:** 
  - Upload an image or generate one via Imagen 3.
  - Attach as `@FirstFrame` or drag into the Starting Frame dropzone in the Storyboard node.
  - The model treats pixel coordinates from this image as the ground truth start of the motion clip.

### B. Last Frame (Ending Frame — `t = 4s / 6s / 8s / 10s`)
- **Function:** Defines the exact destination pose, scene resolution, or closing shot.
- **How to provide:**
  - Attach as `@LastFrame` or select an existing asset in the Storyboard.
  - **Temporal Interpolation:** Gemini Omni computes physically plausible in-between motion and morphing from the Starting Frame to the Ending Frame across the selected duration.

### C. Ingredient Conditioning (`@` Tag Syntax)
- `@FirstFrame:AssetID` — Locks clip start to specific keyframe.
- `@LastFrame:AssetID` — Locks clip end to destination keyframe.
- `@Character:Name` — Maintains character facial and structural identity.
- `@Ingredient:StyleName` — Applies persistent color palettes or visual textures.
- `@Scene:Number` — Links lighting and background continuity from previous scenes.

---

## 🏷️ 4. Asset Naming & Local File Renaming Pipeline

### A. Inside Google Flow Canvas:
- Every generation card or storyboard scene has a title field:
  - Format: `[Scene_Number] - [Descriptive_Title]`
  - Example: `Scene 01 - Cyberpunk Terminal Opening`

### B. Local Disk Download Naming Standard:
When Universal-Web-MCP downloads completed video clips, it enforces a structured naming convention:
```text
[ProjectName]_[Model]_[Duration]s_[Keyframes]_[PromptSlug]_[YYYYMMDD_HHMMSS].[ext]
```
- **Example 1 (Omni Flash with Start & End frames):**
  `UniversalWeb_OmniFlash_6s_Start-End_ai_terminal_data_streams_20261026_154512.mp4`
- **Example 2 (Veo 3.1 8s Cinematic):**
  `UniversalWeb_Veo31_8s_Prompt_futuristic_hologram_breakthrough_20261026_154800.mp4`

---

## 💎 5. Google Flow Credit & Quota System

Rough guide only: Google changes plans, allowances and per-clip costs. The real balance always comes from `get_flow_account_credits` (or Flow's account menu).

| Subscription Plan | Daily Credits (Refreshes Every 24h) | Monthly Flow Credits | AI Top-Ups Available | Typical Cost per Clip |
| :--- | :--- | :--- | :--- | :--- |
| **Free Plan** | **50 Daily Credits** | None | No | ~5–10 credits |
| **Google AI Pro** | **50 Daily Credits** | **1,000 Monthly Credits** | Yes | ~5 credits (Omni Flash) / ~10 credits (Veo 3.1) |
| **Ultra / Studio** | **50 Daily Credits** | **10,000 – 25,000 Monthly** | Yes | Highest priority rendering queue |

### Generation Credit Costs:
- **Gemini Omni Flash (4s–10s):** ~5 credits per generation
- **Veo 3.1 (8s 4K):** ~10 credits per generation
- **Upscaling (1080p / 4K):** ~2 to 5 credits per upscale

---

## 🤖 6. AI Agent Conversational Protocol & Prompt Education

When an AI agent interacts with a user to generate videos in Google Flow, the agent **MUST** follow this structured, intelligent protocol:

### Step 1: Real credits first
Call `get_flow_account_credits` and show what it returns, for example:
```text
🎬 Google Flow: 1,240 credits (checked just now)
```
If the status is `signed_out`, `unknown` or `error`, say that instead (e.g. "I couldn't read your Flow balance; it's shown in Flow's account menu"). Never show a made-up balance, plan or email address.

### Step 2: One-Time Preferences Inquiry
**IMPORTANT:** Ask the user for their global preferences **ONCE ONLY** at the start of the project session — **never** interrupt them after each video:
- **Default Export Quality:** Default to `1080p Upscaled` unless they specify 720p (for raw speed) or 4K Ultra HD.
- **Dynamic Clip Duration:** Ask for their duration preference (e.g., 4s, 6s, 8s, 10s, or 30s commercial ad) based on their project needs.

### Step 3: Prompt Analysis, Validation & User Education
The agent must inspect the user's prompt concept:
1. **If the prompt is vague or underspecified:**  
   *Educate the user on the 5-point photorealism formula.*  
   *Example critique:*  
   > "Your prompt 'make a tech ad' is too generic for generative video models. In Google Flow (Veo 3.1 & Omni Flash), the diffusion engine requires concrete camera motion, lens characteristics, lighting physics, and subject action.  
   > **Refined 4K Prompt:** *'Cinematic 35mm close-up of a futuristic developer terminal with glowing cyan data streams. Smooth slow-dolly push-in, volumetric light rays, shallow depth of field, 4K crisp photorealism.'*"
2. **If the user requests an invalid single-clip duration (e.g., 15s or 20s):**  
   *Educate the user on model physical limits:*  
   > "Google Flow limits single clips: **Gemini Omni Flash 1.1** makes **4, 6, 8 or 10 s** clips, while **Veo 3.1** makes **4, 6 or 8 s**. For durations beyond 10s, we automatically split your concept into a 4-scene storyboard (e.g. 8s + 8s + 8s + 6s = 30s commercial) and download each scene locally."
3. **If the user wants seamless visual transitions or character consistency:**  
   *Educate on Keyframe Interpolation & Tags:*  
   > "Use `@FirstFrame:AssetID` (starting frame at 0.0s) and `@LastFrame:AssetID` (ending frame at 4s–10s). Gemini Omni will compute physics-based in-between motion to seamlessly morph between the two images."

### Step 4: Autonomous Execution & Asset Naming
Once the prompt and duration are verified, the agent executes the generation, waits for the render, and downloads the file using the standardized naming syntax:
`[Project]_[Model]_[Duration]s_[Keyframes]_[Slug]_[Timestamp].mp4`
And reports:
- Final file path on local disk
- File size (in MB)
- Remaining credits, only if `get_flow_account_credits` could read them

---

## 🎛️ 7. Creative Tools in Flow

Tools seen in Flow's tools panel (names and availability change; check the panel in the user's project before relying on one):
- `Storyboard Studio`: Multi-scene scriptwriting and card generation.
- `Type Overlays`: Animated kinetic typography, title cards, lower-thirds.
- `Video Resizer`: Aspect ratio converter (16:9, 9:16, 1:1, 4:3).
- `Character X-ray`: Multi-angle character consistency sheets.
- `Image Editor`: Layer-based graphics editor, inpainting, object removal.
- `Shader Effects`: Bloom, chromatic aberration, retro grade filters.
- `Mockup`: Compositing 2D graphics onto 3D devices and environments.
- `Ribbit`: Audio-reactive video syncing to musical beats.
- `Converge`: Sketch-to-3D photorealistic rendering.
- `pixelBento`: Lo-fi, 8-bit, VHS, and glitch art processing.
- `Grid Architect`: Multi-panel image grid splitter.
- `Scout360`: 360-degree panoramic VR skybox generator.

---

## 📥 8. Export Qualities & DOM Selectors

These are what `flow_video_automator.py` uses. Flow changes its page often: if a step fails, look at Live View (or `open_live_view`) and update the selectors there.

```python
# Prompt Box:
prompt_box = page.locator("div.ProseMirror[aria-label='What do you want to create?']").first

# Submit Button:
send_btn = page.locator("button:has-text('arrow_forward')").first

# Model Switcher:
model_btn = page.locator("button:has-text('chevron_left'), button:has-text('chevron_right')").first

# Video Card Download Menu:
download_icon = page.locator("button:has-text('download'), button[aria-label*='Download']").first

# Export Quality Dropdown Item:
quality_720p = page.locator("[role='menuitem']:has-text('720p'), button:has-text('720p')").first
quality_1080p = page.locator("[role='menuitem']:has-text('1080p'), button:has-text('1080p')").first
quality_4k = page.locator("[role='menuitem']:has-text('4K'), button:has-text('4K')").first
```
