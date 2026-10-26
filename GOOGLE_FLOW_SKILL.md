# Google Flow Skill: The Complete Platform Knowledge Base 🎬🧠

> **Skill Purpose:** This document is the definitive operational manual for Google Flow (`flow.google.com`). Any AI model, agent, or developer reading this file immediately understands all models, durations (4s, 6s, 8s, 10s), starting/ending keyframes, credit tiers, asset naming, tools, and UI automation selectors without needing to explore or search.

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

| Model Identifier | Internal Model Code | Supported Durations | Primary Strength | Ideal Use Cases |
| :--- | :--- | :--- | :--- | :--- |
| **Gemini Omni Flash** | `abra_t2v_flash` | **4s, 6s, 8s, 10s** (Flexible odd/even durations) | Rapid generation, high prompt responsiveness, dynamic motion | High-volume batch generation (10–20 videos), rapid iterations, flexible timing |
| **Gemini Omni** | `gemini_omni_v1` | **4s, 6s, 8s, 10s** | Deep world understanding, multimodality, conversational video editing | Multimodal conditioning, keyframe interpolation |
| **Veo 3.1** | `veo_3_1` | **8s Max Clip** | Expanded creative controls, native audio, physics & realism | Hero commercials, cinematic photorealism, 35mm shallow depth of field |
| **Nano Banana Pro** | `nano_banana_pro` | **4s, 6s, 8s** | Lightweight rapid prototyping | Conceptual testing, animatics |
| **Imagen 3** | `imagen_3` | **Still Image** | 4K crisp visual keyframing, text rendering in images | Starting frames, ending frames, character concepts |

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

Every Google Flow account operates under specific daily and monthly credit allocations:

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

## 🤖 6. AI Agent Conversational Protocol (Interactive Interview)

Whenever an AI agent assists a user in creating videos in Google Flow, the agent must:

1. **Display Account Credit Balance:**
   - Inform the user of their available daily allowance (50 credits) and active plan balance (e.g., Google AI Pro 1,000 monthly credits).
2. **Solicit Model Choice:**
   - **Gemini Omni Flash** (Fast, 4s/6s/8s/10s, rapid iteration)
   - **Veo 3.1** (Photorealistic 8s, 4K, native audio)
   - **Gemini Omni** (Multimodal editing, keyframe interpolation)
3. **Solicit Target Duration:**
   - **4s, 6s, 8s, 10s** (Single shot)
   - **30-Second Commercial Ad** (Automated 4-scene assembly)
4. **Solicit Download Quality:**
   - **1080p Upscaled** (Recommended for production)
   - **720p Native** (Fastest download)
   - **4K Cinematic** (Requires Pro tier credits)
5. **Frame Interpolation Confirmation:**
   - Ask if the user wants to specify a **Starting Frame** and/or **Ending Frame** or generate purely from text.

---

## 🎛️ 7. The 12 Native Creative Tools in Flow

Every project workspace has access to 12 specialized creative tools:
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

## 📥 8. Export Qualities & Verified DOM Selectors

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
