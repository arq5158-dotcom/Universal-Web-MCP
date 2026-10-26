# Google Flow Skill: The Complete Platform Knowledge Base 🎬🧠

> **Skill Purpose:** This document is the definitive operational skill manual for Google Flow (`flow.google.com`). Any AI model, agent, or developer reading this file immediately understands all modes, models, durations, reference conditioning, `@` tag syntax, tools, and UI automation selectors without needing to explore or search.

---

## 🏛️ 1. Platform Architecture & Core Modes

Google Flow operates in two primary execution modes:

### A. Agent Mode (Creative Co-Pilot)
- **Role:** Interactive creative director powered by Google's multi-modal creative assistant.
- **Capabilities:**
  - Automatically recommends scene breakdowns and storyboard scripts.
  - Assembles complex 30-second commercials scene-by-scene.
  - Suggests character backstories, lighting styles, and audio-reactive pacing.
- **Trigger:** Selected by default when interacting in the main workspace chat interface.

### B. Direct Mode (Raw Generative Pipeline)
- **Role:** Direct model prompting without assistant conversation.
- **Capabilities:**
  - Bypasses conversational confirmation dialogues (`Agent Settings: Confirm before generating -> Never`).
  - Sends direct generation tokens straight to the rendering queue.
  - Ideal for high-speed programmatic batch processing via Universal-Web-MCP.

---

## 🎥 2. Generative Models, Clip Durations & Aspect Ratios

| Model Identifier | Internal Code | Max Duration | Primary Strength | Ideal Use Cases |
| :--- | :--- | :--- | :--- | :--- |
| **Google Veo** | `veo_1` | **8 Seconds** | Ultra-photorealistic 4K visual fidelity, rich physics, lighting nuance, 35mm shallow depth of field | Hero commercials, cinematic film scenes, brand ads |
| **Omni 1.1 Flash** | `abra_t2v_10s` | **10 Seconds** | Ultra-fast rendering speed, high prompt responsiveness, dynamic motion | High-volume batch generation (10–20 videos), rapid iterations, vertical social video |
| **Imagen 3** | `imagen_3` | **Still Image** | 4K crisp visual keyframing, text rendering in images, photorealistic portraits | Keyframing characters and scenes before animating |
| **Ingredient Model** | `flow_img2vid` | **8–10 Seconds**| Conditions video generation using input image/video references | Animating sketches, product mockups, or character stills |

### Supported Aspect Ratios:
- `16:9` (Standard Landscape — YouTube, Commercials, Desktop)
- `9:16` (Vertical — Shorts, TikTok, Instagram Reels)
- `1:1` (Square — Social feeds)
- `4:3` & `3:4` (Retro / Academy frame)

---

## 🧬 3. The "Ingredients" System & Reference Conditioning

Google Flow allows conditioning generations using external or existing project assets:

1. **Image-to-Video (Keyframe Conditioning):**  
   An existing still image (generated via Imagen 3 or uploaded) is passed as an ingredient. The model animates the visual elements while maintaining 100% aesthetic continuity.
2. **Video-to-Video (Style & Motion Transfer):**  
   Takes an input motion clip and applies generative shader filters (e.g. turning live-action into anime or cyberpunk render).
3. **Add Reference (Visual Anchors):**  
   Attaches reference photos of a real product or character to force facial and structural consistency across multiple generated scenes.

---

## 🏷️ 4. Special Tagging & Syntax Rules

When constructing prompts inside Google Flow, use these native platform tags:

- `@Character:Name` — Locks the generation to a persistent character defined in the **Characters** library (generated via Character X-ray).
- `@Scene:SceneNumber` — Links the visual background, camera angle, and color grading of a previous scene in the **Storyboard**.
- `@Tool:ToolName` — Dynamically invokes a specialized studio tool (e.g. `@Type Overlays`, `@Shader Effects`).
- `@Asset:AssetID` — References an existing media item in the project Library.

### 4K Prompt Formula for Veo:
```text
[Cinematic Shot Type] + [Subject & Action] + [Camera Motion] + [Lighting & Atmosphere] + [Lens & Style]
Example:
"Cinematic close-up of an AI terminal breaking through latency lag with neon blue data streams. Slow dolly forward push-in, anamorphic lens, 35mm shallow depth of field, 4K crisp photorealism."
```

---

## 🎛️ 5. The 12 Native Creative Tools in Flow

Every project workspace has access to 12 specialized creative tools:

| Tool Name | Tool ID / Route | Functionality |
| :--- | :--- | :--- |
| **Storyboard Studio** | `79c9d2e6-4ad6-4636-ad05-22022f8a5a74` | Writes scripts, generates cast characters, and visualizes scene-by-scene storyboard clips. |
| **Type Overlays** | `075ead65-520a-4f5e-88bd-f150caa24dc4` | Adds animated kinetic typography, title cards, and lower thirds to videos. |
| **Video Resizer** | `b78766c3-4cd7-4c1e-b597-769d4cfcf37a` | Crops and re-renders videos between 16:9, 9:16, and 1:1 aspect ratios. |
| **Character X-ray** | `32f2b8f8-a1a9-43ed-899f-c0fbff2e9599` | Builds consistent multi-angle character profiles, outfits, and facial geometry. |
| **Image Editor** | `1b12bbd4-51d7-4c76-8b62-24ac2473e07e` | Layer-based graphics editor, object removal, background adjustments. |
| **Shader Effects** | `63ca3af5-0058-4c7f-b104-dfc417db2e22` | Applies customizable post-processing filters (bloom, chromatic aberration, retro grade). |
| **Mockup** | `611fa902-797c-457d-92de-71a3dc714894` | Composites 2D images and logos into realistic 3D environments and devices. |
| **Ribbit** | `46270263-54a1-46fb-a68c-dae111f650fb` | Synchronizes video playback dynamically to musical beats and audio stems. |
| **Converge** | `f260ed2b-2a14-4ece-a8d3-88b8cf6e660f` | Converts rough hand-drawn sketches into photorealistic 3D renders. |
| **pixelBento** | `44b73cc0-ad82-49a6-b118-86c31ec49a71` | Applies retro, lo-fi, 8-bit, VHS, and glitch art effects to video clips. |
| **Grid Architect** | `52da09f1-1da1-4a40-96c6-41d36b3b2392` | Creates composite image grids and slices them into individual scene assets. |
| **Scout360** | `2102cb9f-a06e-4590-8a53-aa34bdcb0dff` | Generates 360-degree panoramic VR environments from an image prompt. |

---

## 📥 6. Export Qualities & Automated Download Selectors

When clicking the download icon on a completed video asset, the platform opens an export menu:

- **`720p Original size`** — Native model render output (fastest download, ~6MB per clip).
- **`1080p Upscaled`** — High-definition upscaled render.
- **`4K Upscaled`** — Full 4K ultra-resolution upscale (requires Google One AI Premium credits).
- **`270p Animated GIF`** — Lightweight preview format for web and email.

### DOM Automation Selectors (Verified):
```python
# 1. Prompt input field:
prompt_box = page.locator("div.ProseMirror[aria-label='What do you want to create?']").first

# 2. Submit / Generate button:
send_btn = page.locator("button:has-text('arrow_forward')").first

# 3. Open video asset modal:
video_card = page.locator("img[alt*='Generated video'], img[src*='video']").first

# 4. Trigger download menu:
download_icon = page.locator("button:has-text('download'), button[aria-label*='Download']").first

# 5. Quality selection:
quality_720p = page.locator("[role='menuitem']:has-text('720p'), button:has-text('720p')").first
quality_1080p = page.locator("[role='menuitem']:has-text('1080p'), button:has-text('1080p')").first
```

---

## ⚡ 7. 30-Second Commercial Production Formula

To produce a full 30-second video without hitting the 8–10s single-clip duration cap:

```
[Clip 1: Hook] (8s)  -> Generate via Veo/Omni -> Download to scene_1.mp4
[Clip 2: Solution] (8s) -> Generate via Veo/Omni -> Download to scene_2.mp4
[Clip 3: Feature] (8s)  -> Generate via Veo/Omni -> Download to scene_3.mp4
[Clip 4: CTA] (6s)      -> Generate via Veo/Omni -> Download to scene_4.mp4
```
All four clips are saved locally to `downloads/flow_production/<project_name>/`.
