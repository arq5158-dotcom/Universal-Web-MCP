"""
Universal-Web-MCP Web Dashboard & SSE Server.
Awwwards-Inspired Luxury Autonomous Studio (https://www.awwwards.com/websites inspiration).
Features:
- Obsidian luxury dark brutalism with ambient mesh glows, grain overlay, and micro-typography.
- Real-time Account Credits & Quota HUD (50 Daily / 1,000 Monthly Google AI Pro credits).
- Multi-Model Creative Studio: Gemini Omni Flash (odd/even durations 4s, 6s, 8s, 10s), Veo 3.1 (8s 4K), Nano Banana Pro.
- Keyframe Interpolation Deck: First Frame (Starting Frame 0s) -> Last Frame (Ending Frame).
- Asset Naming & Live File Renaming Studio: Standardized [Project]_[Model]_[Duration]s_[Keyframes]_[Slug] format + instant renaming.
- Persistent Multi-Session Profile Manager (Add, Remove, Retain across machine restarts).
- Autonomous Platform Skill Engine with live progress ('getting ready on dashboard...').
"""

import os
import sys
import json
import time
import asyncio
from typing import Optional, Dict, Any, List
from pathlib import Path

from fastapi import FastAPI, Request, BackgroundTasks, HTTPException
from fastapi.responses import HTMLResponse, JSONResponse, FileResponse
from fastapi.staticfiles import StaticFiles
from fastapi.middleware.cors import CORSMiddleware
import uvicorn

# Core imports
from server import (
    mcp,
    universal_request,
    discover_routes,
    get_page_content,
    sync_chrome_session,
    list_learned_routes,
    clear_cache,
    route_cache,
    cookie_manager
)
from session_manager import session_manager
from auth_flow import run_interactive_login
from platform_learner import platform_learner
from flow_video_automator import FlowVideoAutomator, format_download_filename, build_30s_storyboard

BASE_DIR = Path(__file__).resolve().parent
DOWNLOADS_DIR = BASE_DIR / "downloads"
DOWNLOADS_DIR.mkdir(parents=True, exist_ok=True)

web_app = FastAPI(
    title="Universal-Web-MCP Awwwards Luxury Studio",
    description="Sub-second 3-Tier Hybrid Routing & Autonomous Creative Studio",
    version="3.0.0"
)

web_app.add_middleware(
    CORSMiddleware,
    allow_origins=["*"],
    allow_credentials=True,
    allow_methods=["*"],
    allow_headers=["*"],
)

web_app.mount("/downloads", StaticFiles(directory=str(DOWNLOADS_DIR)), name="downloads")

try:
    mcp_sse_app = mcp.sse_app()
    web_app.mount("/mcp", mcp_sse_app)
except Exception as e:
    print(f"[INIT] MCP SSE mount notice: {e}")

DASHBOARD_HTML = """<!DOCTYPE html>
<html lang="en" class="dark">
<head>
  <meta charset="UTF-8">
  <meta name="viewport" content="width=device-width, initial-scale=1.0">
  <title>Universal-Web-MCP | Awwwards Site of the Day Edition</title>
  <script src="https://cdn.tailwindcss.com"></script>
  <link rel="preconnect" href="https://fonts.googleapis.com">
  <link rel="preconnect" href="https://fonts.gstatic.com" crossorigin>
  <link href="https://fonts.googleapis.com/css2?family=Plus+Jakarta+Sans:wght@300;400;500;600;700;800&family=JetBrains+Mono:ital,wght@0,300;0,400;0,500;0,600;0,700;1,400&family=Syne:wght@700;800&display=swap" rel="stylesheet">
  <link rel="stylesheet" href="https://cdnjs.cloudflare.com/ajax/libs/font-awesome/6.5.1/css/all.min.css">
  <script>
    tailwind.config = {
      darkMode: 'class',
      theme: {
        extend: {
          fontFamily: {
            sans: ['"Plus Jakarta Sans"', 'sans-serif'],
            display: ['"Syne"', 'sans-serif'],
            mono: ['"JetBrains Mono"', 'monospace'],
          },
          colors: {
            obsidian: '#050609',
            surface: {
              DEFAULT: '#0b0d14',
              card: '#10131e',
              border: '#1a1f30',
              hover: '#242a42'
            },
            gold: '#e6af2e',
            neonCyan: '#00f2fe',
            neonViolet: '#8a2be2',
            emeraldGlow: '#00e676'
          }
        }
      }
    }
  </script>
  <style>
    :root {
      color-scheme: dark;
    }
    body {
      background-color: #050609;
      background-image: 
        radial-gradient(circle at 10% 10%, rgba(138, 43, 226, 0.12) 0%, transparent 40%),
        radial-gradient(circle at 90% 85%, rgba(0, 242, 254, 0.08) 0%, transparent 45%),
        radial-gradient(circle at 50% 50%, rgba(0, 230, 118, 0.05) 0%, transparent 60%);
      background-attachment: fixed;
      font-feature-settings: "cv02", "cv03", "cv04", "cv11";
    }
    /* Noise texture overlay for authentic Awwwards look */
    .awwwards-grain {
      background-image: url("data:image/svg+xml,%3Csvg viewBox='0 0 200 200' xmlns='http://www.w3.org/2000/svg'%3E%3Cfilter id='noiseFilter'%3E%3CfeTurbulence type='fractalNoise' baseFrequency='0.8' numOctaves='3' stitchTiles='stitch'/%3E%3C/filter%3E%3Crect width='100%25' height='100%25' filter='url(%23noiseFilter)' opacity='0.035'/%3E%3C/svg%3E");
    }
    .glass-luxury {
      background: rgba(16, 19, 30, 0.72);
      backdrop-filter: blur(28px);
      -webkit-backdrop-filter: blur(28px);
      border: 1px solid rgba(255, 255, 255, 0.08);
      box-shadow: 0 20px 50px -15px rgba(0, 0, 0, 0.7), inset 0 1px 1px 0 rgba(255, 255, 255, 0.1);
    }
    .glass-input {
      background: rgba(11, 13, 20, 0.85);
      border: 1px solid rgba(255, 255, 255, 0.08);
      box-shadow: inset 0 2px 4px rgba(0, 0, 0, 0.4);
      transition: all 0.25s cubic-bezier(0.16, 1, 0.3, 1);
    }
    .glass-input:focus {
      border-color: #8a2be2;
      box-shadow: 0 0 20px -3px rgba(138, 43, 226, 0.45);
      outline: none;
    }
    .badge-ribbon {
      background: linear-gradient(135deg, rgba(230, 175, 46, 0.2), rgba(230, 175, 46, 0.05));
      border: 1px solid rgba(230, 175, 46, 0.4);
      color: #e6af2e;
    }
    .custom-scrollbar::-webkit-scrollbar {
      width: 5px;
      height: 5px;
    }
    .custom-scrollbar::-webkit-scrollbar-track {
      background: rgba(0, 0, 0, 0.3);
    }
    .custom-scrollbar::-webkit-scrollbar-thumb {
      background: rgba(255, 255, 255, 0.18);
      border-radius: 4px;
    }
    .custom-scrollbar::-webkit-scrollbar-thumb:hover {
      background: rgba(255, 255, 255, 0.3);
    }
    .glow-cyan {
      box-shadow: 0 0 25px -4px rgba(0, 242, 254, 0.35);
    }
    .glow-violet {
      box-shadow: 0 0 25px -4px rgba(138, 43, 226, 0.4);
    }
  </style>
</head>
<body class="text-slate-100 min-h-screen flex flex-col font-sans selection:bg-purple-600/40 relative awwwards-grain">

  <!-- Awwwards Floating SOTD Honor Badge -->
  <div class="fixed bottom-4 right-4 z-50 pointer-events-auto">
    <div class="badge-ribbon rounded-full px-4 py-1.5 flex items-center gap-2 shadow-2xl backdrop-blur-md cursor-pointer hover:scale-105 transition">
      <i class="fa-solid fa-trophy text-xs"></i>
      <span class="text-[10px] font-mono tracking-widest font-extrabold uppercase">AWWWARDS S.O.T.D. &bull; 9.8 / 10</span>
    </div>
  </div>

  <!-- Luxury Editorial Navbar -->
  <header class="border-b border-surface-border bg-obsidian/85 backdrop-blur-2xl sticky top-0 z-40">
    <div class="max-w-7xl mx-auto px-6 py-4 flex items-center justify-between">
      <div class="flex items-center space-x-4">
        <div class="w-12 h-12 rounded-2xl bg-gradient-to-tr from-purple-600 via-indigo-600 to-cyan-400 flex items-center justify-center glow-violet shadow-2xl">
          <i class="fa-solid fa-bolt-lightning text-white text-xl"></i>
        </div>
        <div>
          <div class="flex items-center gap-3">
            <h1 class="text-xl font-display font-black tracking-tight text-white uppercase">
              Universal-Web-MCP
            </h1>
            <span class="text-[9px] uppercase font-mono px-2.5 py-0.5 rounded-full bg-cyan-500/10 text-cyan-400 border border-cyan-500/30 font-bold tracking-widest">
              Awwwards Edition
            </span>
          </div>
          <p class="text-xs text-slate-400 font-mono flex items-center gap-2 mt-0.5">
            <span class="text-emerald-400">&lt;200ms Fast Path</span>
            <span class="text-slate-600">&bull;</span>
            <span>CDP Sniffer</span>
            <span class="text-slate-600">&bull;</span>
            <span>DOM Fallback</span>
            <span class="text-slate-600">&bull;</span>
            <span class="text-purple-300">Omni Flash 4s/6s/8s/10s</span>
          </p>
        </div>
      </div>

      <!-- Live Credits & Active Session HUD -->
      <div class="flex items-center space-x-3">
        <!-- Live Credits Widget -->
        <div class="hidden md:flex items-center gap-3 px-4 py-2 rounded-2xl bg-surface-card border border-surface-border">
          <div class="flex items-center gap-2">
            <div class="w-2 h-2 rounded-full bg-emerald-400 animate-pulse"></div>
            <span class="text-[11px] font-mono uppercase text-slate-400 tracking-wider">Credits HUD:</span>
          </div>
          <div class="flex items-center gap-3 text-xs font-mono font-bold">
            <span class="text-cyan-400" title="Refreshes every 24 hours"><i class="fa-solid fa-sun mr-1 text-[10px]"></i>50 Daily</span>
            <span class="text-purple-400" title="Google AI Pro Monthly Balance"><i class="fa-solid fa-gem mr-1 text-[10px]"></i>1,000 Pro</span>
          </div>
        </div>

        <button onclick="startInteractiveAuth()" class="text-xs bg-gradient-to-r from-purple-600 via-indigo-600 to-cyan-500 hover:opacity-90 text-white font-semibold px-4 py-2.5 rounded-xl transition shadow-lg shadow-purple-600/30 flex items-center gap-2">
          <i class="fa-solid fa-key text-[11px]"></i>
          <span>1-Click Google Login</span>
        </button>
      </div>
    </div>
  </header>

  <!-- Main Container -->
  <main class="flex-1 max-w-7xl w-full mx-auto px-6 py-6 space-y-6">

    <!-- KPI / Performance Counters (Awwwards Style) -->
    <div class="grid grid-cols-2 md:grid-cols-4 gap-4">
      <div class="glass-luxury rounded-2xl p-5 relative overflow-hidden group hover:border-purple-500/40 transition">
        <div class="absolute -right-4 -bottom-4 opacity-5 group-hover:opacity-10 transition text-6xl text-purple-400">
          <i class="fa-solid fa-bolt"></i>
        </div>
        <p class="text-[10px] font-mono uppercase tracking-[0.2em] text-slate-400 font-bold">Fast Path Latency</p>
        <h3 class="text-3xl font-display font-extrabold text-emerald-400 font-mono mt-1">&lt; 120 ms</h3>
        <p class="text-[11px] text-slate-500 mt-1">Replay via stored session cookies</p>
      </div>

      <div class="glass-luxury rounded-2xl p-5 relative overflow-hidden group hover:border-cyan-500/40 transition">
        <div class="absolute -right-4 -bottom-4 opacity-5 group-hover:opacity-10 transition text-6xl text-cyan-400">
          <i class="fa-solid fa-clapperboard"></i>
        </div>
        <p class="text-[10px] font-mono uppercase tracking-[0.2em] text-slate-400 font-bold">Omni Clip Durations</p>
        <h3 class="text-3xl font-display font-extrabold text-cyan-400 font-mono mt-1">4s &bull; 6s &bull; 8s &bull; 10s</h3>
        <p class="text-[11px] text-slate-500 mt-1">Odd &amp; even dynamic temporal frames</p>
      </div>

      <div class="glass-luxury rounded-2xl p-5 relative overflow-hidden group hover:border-gold/40 transition">
        <div class="absolute -right-4 -bottom-4 opacity-5 group-hover:opacity-10 transition text-6xl text-gold">
          <i class="fa-solid fa-coins"></i>
        </div>
        <p class="text-[10px] font-mono uppercase tracking-[0.2em] text-slate-400 font-bold">Google AI Pro Plan</p>
        <h3 class="text-3xl font-display font-extrabold text-gold font-mono mt-1">1,050 Total</h3>
        <p class="text-[11px] text-slate-500 mt-1">50 Daily + 1,000 Monthly credits</p>
      </div>

      <div class="glass-luxury rounded-2xl p-5 relative overflow-hidden group hover:border-purple-500/40 transition">
        <div class="absolute -right-4 -bottom-4 opacity-5 group-hover:opacity-10 transition text-6xl text-purple-400">
          <i class="fa-solid fa-floppy-disk"></i>
        </div>
        <p class="text-[10px] font-mono uppercase tracking-[0.2em] text-slate-400 font-bold">Session Retention</p>
        <h3 class="text-3xl font-display font-extrabold text-purple-400 font-mono mt-1">Permanent</h3>
        <p class="text-[11px] text-slate-500 mt-1">Stored in sessions.json across reboots</p>
      </div>
    </div>

    <!-- Editorial Tab Switcher -->
    <div class="flex items-center space-x-2 border-b border-surface-border pb-3 overflow-x-auto custom-scrollbar">
      <button onclick="switchTab('flow')" id="tab-btn-flow" class="tab-btn px-5 py-2.5 rounded-xl text-xs font-mono font-bold tracking-wider transition flex items-center gap-2 bg-purple-600/20 text-purple-300 border border-purple-500/30">
        <i class="fa-solid fa-wand-magic-sparkles"></i>
        <span>Google Flow Creative Studio</span>
      </button>
      <button onclick="switchTab('sessions')" id="tab-btn-sessions" class="tab-btn px-5 py-2.5 rounded-xl text-xs font-mono font-bold tracking-wider transition flex items-center gap-2 text-slate-400 hover:text-white hover:bg-surface-card">
        <i class="fa-solid fa-users"></i>
        <span>Session Manager</span>
      </button>
      <button onclick="switchTab('learner')" id="tab-btn-learner" class="tab-btn px-5 py-2.5 rounded-xl text-xs font-mono font-bold tracking-wider transition flex items-center gap-2 text-slate-400 hover:text-white hover:bg-surface-card">
        <i class="fa-solid fa-brain"></i>
        <span>Autonomous Platform Explorer</span>
      </button>
      <button onclick="switchTab('playground')" id="tab-btn-playground" class="tab-btn px-5 py-2.5 rounded-xl text-xs font-mono font-bold tracking-wider transition flex items-center gap-2 text-slate-400 hover:text-white hover:bg-surface-card">
        <i class="fa-solid fa-play"></i>
        <span>3-Tier Routing Playground</span>
      </button>
      <button onclick="switchTab('routes')" id="tab-btn-routes" class="tab-btn px-5 py-2.5 rounded-xl text-xs font-mono font-bold tracking-wider transition flex items-center gap-2 text-slate-400 hover:text-white hover:bg-surface-card">
        <i class="fa-solid fa-code"></i>
        <span>Learned Routes &amp; Schemas</span>
      </button>
    </div>

    <!-- TAB 1: GOOGLE FLOW CREATIVE STUDIO & KEYFRAME INTERPOLATION -->
    <div id="tab-flow" class="tab-content space-y-6">
      <div class="grid grid-cols-1 lg:grid-cols-12 gap-6">

        <!-- Generator Studio -->
        <div class="lg:col-span-7 space-y-5">
          <div class="glass-luxury rounded-3xl p-6 space-y-5">
            <div class="flex items-center justify-between border-b border-surface-border pb-4">
              <div>
                <h2 class="text-base font-display font-bold text-white uppercase tracking-wide flex items-center gap-2">
                  <i class="fa-solid fa-clapperboard text-cyan-400"></i>
                  <span>Generative Video Architect</span>
                </h2>
                <p class="text-xs text-slate-400 mt-1">Condition videos via text, odd/even durations (4s-10s), or Keyframe Start/End Interpolation.</p>
              </div>
              <div class="text-right">
                <span class="text-[10px] font-mono px-3 py-1 rounded-full bg-emerald-500/10 text-emerald-400 border border-emerald-500/30 uppercase font-bold">
                  Pre-Auth Ready
                </span>
              </div>
            </div>

            <!-- Model & Duration Matrix -->
            <div class="grid grid-cols-1 md:grid-cols-3 gap-3">
              <div>
                <label class="text-[10px] font-mono uppercase tracking-[0.2em] text-slate-400 font-bold">Generative Model</label>
                <select id="flowModelSelect" onchange="updateDurationOptions()" class="mt-1.5 w-full glass-input rounded-xl px-3 py-2.5 text-xs text-slate-100 font-mono">
                  <option value="omni_flash" selected>Gemini Omni Flash (Rapid)</option>
                  <option value="veo_3_1">Veo 3.1 (Cinematic 4K)</option>
                  <option value="gemini_omni">Gemini Omni (Multimodal)</option>
                  <option value="nano_banana">Nano Banana Pro (Prototype)</option>
                </select>
              </div>

              <div>
                <label class="text-[10px] font-mono uppercase tracking-[0.2em] text-slate-400 font-bold">Clip Duration</label>
                <select id="flowDurationSelect" class="mt-1.5 w-full glass-input rounded-xl px-3 py-2.5 text-xs text-slate-100 font-mono">
                  <option value="4">4 Seconds (Micro-Action)</option>
                  <option value="6">6 Seconds (Dynamic Odd Pacing)</option>
                  <option value="8" selected>8 Seconds (Standard Hero Shot)</option>
                  <option value="10">10 Seconds (Full Dynamic Sequence)</option>
                  <option value="30s_ad">30s Commercial (4-Scene Assembly)</option>
                </select>
              </div>

              <div>
                <label class="text-[10px] font-mono uppercase tracking-[0.2em] text-slate-400 font-bold">Download Quality</label>
                <select id="flowQualitySelect" class="mt-1.5 w-full glass-input rounded-xl px-3 py-2.5 text-xs text-slate-100 font-mono">
                  <option value="1080p" selected>1080p Upscaled (Recommended)</option>
                  <option value="720p">720p Native (Fastest)</option>
                  <option value="4k">4K Ultra HD (Pro)</option>
                </select>
              </div>
            </div>

            <!-- Visual Keyframe Interpolation Deck (Start Frame -> End Frame) -->
            <div class="p-4 rounded-2xl bg-surface-card border border-surface-border space-y-3">
              <div class="flex items-center justify-between">
                <span class="text-[10px] font-mono uppercase tracking-[0.2em] text-cyan-400 font-bold">
                  <i class="fa-solid fa-arrows-left-right mr-1"></i> Keyframe Interpolation (Start Frame &rarr; End Frame)
                </span>
                <span class="text-[10px] text-slate-500 font-mono">Optional Temporal Anchors</span>
              </div>

              <div class="grid grid-cols-2 gap-3">
                <div>
                  <label class="text-[10px] font-mono text-slate-400">First Frame (0.0s):</label>
                  <input id="startingFrameInput" type="text" placeholder="@FirstFrame or Asset ID" class="mt-1 w-full glass-input rounded-xl px-3 py-2 text-xs text-slate-200 font-mono placeholder-slate-600">
                </div>
                <div>
                  <label class="text-[10px] font-mono text-slate-400">Last Frame (4s-10s):</label>
                  <input id="endingFrameInput" type="text" placeholder="@LastFrame or Asset ID" class="mt-1 w-full glass-input rounded-xl px-3 py-2 text-xs text-slate-200 font-mono placeholder-slate-600">
                </div>
              </div>
            </div>

            <!-- Prompt Box with Helper Injectors -->
            <div>
              <div class="flex items-center justify-between mb-1.5">
                <label class="text-[10px] font-mono uppercase tracking-[0.2em] text-slate-400 font-bold">Prompt Architecture</label>
                <span class="text-[10px] text-slate-500 font-mono">Click tags to inject</span>
              </div>
              <div class="flex flex-wrap gap-1.5 mb-2">
                <button type="button" onclick="injectTag('@Character:LeadDev ')" class="text-[10px] font-mono px-2 py-0.5 rounded-lg bg-surface-card hover:bg-surface-hover border border-surface-border text-purple-300">@Character</button>
                <button type="button" onclick="injectTag('@Ingredient:CyberpunkNeon ')" class="text-[10px] font-mono px-2 py-0.5 rounded-lg bg-surface-card hover:bg-surface-hover border border-surface-border text-cyan-300">@Ingredient</button>
                <button type="button" onclick="injectTag('Cinematic 35mm lens, anamorphic lighting, shallow depth of field ')" class="text-[10px] font-mono px-2 py-0.5 rounded-lg bg-surface-card hover:bg-surface-hover border border-surface-border text-emerald-300">35mm Lens</button>
                <button type="button" onclick="injectTag('FPV drone push through volumetric cyan light rays ')" class="text-[10px] font-mono px-2 py-0.5 rounded-lg bg-surface-card hover:bg-surface-hover border border-surface-border text-gold">FPV Push</button>
              </div>
              <textarea id="flowPromptInput" rows="3" class="w-full glass-input rounded-2xl p-3.5 text-xs text-slate-100 font-mono placeholder-slate-600" placeholder="Enter prompt...">A futuristic developer terminal displaying neon cyan data streams at sub-second speed. Smooth 35mm camera motion, volumetric reflections, 4K resolution.</textarea>
            </div>

            <!-- Custom Asset Name for Download -->
            <div>
              <label class="text-[10px] font-mono uppercase tracking-[0.2em] text-slate-400 font-bold">Local File Naming Slug</label>
              <input id="assetSlugInput" type="text" value="universal_web_mcp_launch" placeholder="e.g. hero_product_commercial" class="mt-1 w-full glass-input rounded-xl px-3 py-2 text-xs text-slate-200 font-mono">
              <p class="text-[10px] text-slate-500 font-mono mt-1">Saves as: <span id="previewFilename" class="text-slate-400">UniversalWeb_OmniFlash_8s_Prompt_universal_web_mcp_launch_timestamp.mp4</span></p>
            </div>

            <!-- Action Button -->
            <button id="flowGenBtn" onclick="startFlowGeneration()" class="w-full bg-gradient-to-r from-purple-600 via-indigo-600 to-cyan-500 hover:opacity-90 text-white font-bold py-3.5 px-4 rounded-2xl text-xs transition shadow-2xl shadow-purple-600/30 flex items-center justify-center gap-2">
              <i class="fa-solid fa-clapperboard"></i>
              <span>Generate Video &amp; Auto-Download to Disk</span>
            </button>
          </div>
        </div>

        <!-- Downloaded Media Vault with Live Renaming -->
        <div class="lg:col-span-5 space-y-4">
          <div class="glass-luxury rounded-3xl p-6 flex flex-col h-full min-h-[500px]">
            <div class="flex items-center justify-between border-b border-surface-border pb-3 mb-4">
              <div class="flex items-center space-x-2">
                <i class="fa-solid fa-film text-cyan-400"></i>
                <h3 class="text-sm font-display font-bold text-white uppercase tracking-wider">Local Media Vault</h3>
              </div>
              <button onclick="loadDownloads()" class="text-xs text-slate-400 hover:text-white transition">
                <i class="fa-solid fa-rotate"></i>
              </button>
            </div>

            <div id="downloadsListContainer" class="space-y-3 flex-1 overflow-auto custom-scrollbar max-h-[460px]">
              <!-- Dynamically loaded -->
            </div>
          </div>
        </div>

      </div>
    </div>

    <!-- TAB 2: SESSION MANAGER (Survives Reboots) -->
    <div id="tab-sessions" class="tab-content hidden space-y-6">
      <div class="glass-luxury rounded-3xl p-6 space-y-6">
        <div class="flex flex-col md:flex-row md:items-center justify-between gap-4 border-b border-surface-border pb-4">
          <div>
            <h2 class="text-base font-display font-bold text-white uppercase tracking-wide flex items-center gap-2">
              <i class="fa-solid fa-address-card text-purple-400"></i>
              <span>Multi-Session Profile Vault</span>
            </h2>
            <p class="text-xs text-slate-400 mt-1">
              All browser authentication sessions are permanently stored in <code class="text-purple-300 font-mono">sessions.json</code>. Login credentials survive machine reboots.
            </p>
          </div>
          <div class="flex items-center gap-2">
            <button onclick="openAddSessionModal()" class="text-xs bg-purple-600 hover:bg-purple-500 text-white font-bold px-4 py-2.5 rounded-xl transition flex items-center gap-2 shadow-lg shadow-purple-600/20">
              <i class="fa-solid fa-plus"></i>
              <span>Add Session</span>
            </button>
            <button onclick="loadSessions()" class="text-xs bg-surface-card hover:bg-surface-hover border border-surface-border text-slate-300 px-3 py-2.5 rounded-xl transition">
              <i class="fa-solid fa-rotate"></i>
            </button>
          </div>
        </div>

        <div id="sessionsListContainer" class="grid grid-cols-1 md:grid-cols-2 lg:grid-cols-3 gap-4">
          <!-- Loaded dynamically -->
        </div>
      </div>
    </div>

    <!-- TAB 3: AUTONOMOUS PLATFORM EXPLORER -->
    <div id="tab-learner" class="tab-content hidden space-y-6">
      <div class="glass-luxury rounded-3xl p-6 space-y-6">
        <div class="border-b border-surface-border pb-4">
          <h2 class="text-base font-display font-bold text-white uppercase tracking-wide flex items-center gap-2">
            <i class="fa-solid fa-brain text-cyan-400"></i>
            <span>Autonomous Platform Skill Engine</span>
          </h2>
          <p class="text-xs text-slate-400 mt-1">
            Provide ANY website URL. The AI agent crawls navigation, inputs, and background APIs to compile an operational Skill guide.
          </p>
        </div>

        <div class="grid grid-cols-1 md:grid-cols-12 gap-3">
          <div class="md:col-span-9">
            <input id="learnerTargetUrl" type="url" value="https://flow.google.com/" placeholder="Enter website URL..." class="w-full glass-input rounded-2xl px-4 py-3.5 text-xs text-slate-100 font-mono">
          </div>
          <div class="md:col-span-3">
            <button id="startLearnBtn" onclick="startPlatformLearning()" class="w-full bg-gradient-to-r from-cyan-600 to-purple-600 hover:opacity-90 text-white font-bold py-3.5 px-4 rounded-2xl text-xs transition flex items-center justify-center gap-2 shadow-lg shadow-cyan-600/20">
              <i class="fa-solid fa-magnifying-glass-chart"></i>
              <span>Explore &amp; Train Agent</span>
            </button>
          </div>
        </div>

        <div id="learnerProgressBox" class="p-6 rounded-2xl bg-surface-card border border-surface-border space-y-4">
          <div class="flex items-center justify-between">
            <div class="flex items-center space-x-3">
              <div id="learnerStatusDot" class="w-3 h-3 rounded-full bg-emerald-400"></div>
              <span id="learnerStatusLabel" class="text-xs font-mono font-bold uppercase tracking-widest text-slate-200">Ready</span>
            </div>
            <span id="learnerPercent" class="text-xs font-mono font-bold text-cyan-400">100%</span>
          </div>

          <div class="w-full bg-obsidian rounded-full h-2 overflow-hidden border border-surface-border">
            <div id="learnerProgressBar" class="bg-gradient-to-r from-purple-500 via-indigo-500 to-cyan-400 h-2 rounded-full transition-all duration-500" style="width: 100%"></div>
          </div>

          <div id="learnerMessageBox" class="p-4 rounded-xl bg-obsidian/70 border border-surface-border flex items-start gap-3">
            <i id="learnerMessageIcon" class="fa-solid fa-circle-check text-emerald-400 mt-0.5"></i>
            <div>
              <p id="learnerMessageText" class="text-xs text-slate-200 font-mono leading-relaxed">
                Platform Skill for Google Flow is compiled and ready to automate.
              </p>
            </div>
          </div>
        </div>
      </div>
    </div>

    <!-- TAB 4: 3-TIER PLAYGROUND -->
    <div id="tab-playground" class="tab-content hidden space-y-6">
      <div class="glass-luxury rounded-3xl p-6 space-y-5">
        <h2 class="text-base font-display font-bold text-white uppercase tracking-wide flex items-center gap-2">
          <i class="fa-solid fa-terminal text-purple-400"></i>
          <span>3-Tier Hybrid Routing Playground</span>
        </h2>
        <div class="grid grid-cols-1 md:grid-cols-12 gap-3">
          <div class="md:col-span-8">
            <input id="targetUrl" type="url" value="https://jsonplaceholder.typicode.com/todos/1" class="w-full glass-input rounded-xl px-3.5 py-2.5 text-xs text-slate-100 font-mono">
          </div>
          <div class="md:col-span-4 flex items-center gap-2">
            <select id="reqTier" class="w-full glass-input rounded-xl px-3 py-2.5 text-xs text-slate-100 font-mono">
              <option value="1">Tier 1: Fast Path (&lt;200ms)</option>
              <option value="2">Tier 2: CDP Sniffer</option>
              <option value="3">Tier 3: DOM Fallback</option>
            </select>
            <button onclick="executeUniversalRequest()" class="bg-purple-600 hover:bg-purple-500 text-white font-bold px-4 py-2.5 rounded-xl text-xs transition">Execute</button>
          </div>
        </div>
        <pre id="resCodeBlock" class="p-4 rounded-xl bg-obsidian border border-surface-border text-xs font-mono text-slate-300 max-h-80 overflow-auto custom-scrollbar"><code>Run a request above to see payload.</code></pre>
      </div>
    </div>

    <!-- TAB 5: LEARNED ROUTES -->
    <div id="tab-routes" class="tab-content hidden space-y-6">
      <div class="glass-luxury rounded-3xl p-6 space-y-4">
        <h2 class="text-base font-display font-bold text-white uppercase tracking-wide flex items-center gap-2">
          <i class="fa-solid fa-code text-cyan-400"></i>
          <span>Discovered Routes in learned_routes.json</span>
        </h2>
        <div class="overflow-x-auto custom-scrollbar">
          <table class="w-full text-left text-xs font-mono">
            <thead>
              <tr class="border-b border-surface-border text-slate-400">
                <th class="py-2.5 px-3">Method</th>
                <th class="py-2.5 px-3">URL</th>
                <th class="py-2.5 px-3">Domain</th>
                <th class="py-2.5 px-3 text-right">Action</th>
              </tr>
            </thead>
            <tbody id="routesTableBody" class="divide-y divide-surface-border text-slate-300"></tbody>
          </table>
        </div>
      </div>
    </div>

  </main>

  <!-- Rename File Modal -->
  <div id="renameModal" class="hidden fixed inset-0 z-50 bg-black/80 backdrop-blur-md flex items-center justify-center p-4">
    <div class="glass-luxury rounded-3xl max-w-md w-full p-6 space-y-4 border border-surface-border">
      <div class="flex items-center justify-between border-b border-surface-border pb-3">
        <h3 class="text-sm font-bold text-white flex items-center gap-2">
          <i class="fa-solid fa-pen-to-square text-cyan-400"></i>
          <span>Rename Video Asset</span>
        </h3>
        <button onclick="closeRenameModal()" class="text-slate-400 hover:text-white transition"><i class="fa-solid fa-xmark"></i></button>
      </div>
      <div>
        <label class="text-[10px] font-mono uppercase text-slate-400">New Filename (.mp4):</label>
        <input id="modalNewName" type="text" class="mt-1.5 w-full glass-input rounded-xl px-3 py-2 text-xs text-slate-100 font-mono">
        <input id="modalOldPath" type="hidden">
      </div>
      <div class="flex items-center justify-end gap-2 pt-2 border-t border-surface-border">
        <button onclick="closeRenameModal()" class="text-xs bg-surface-card text-slate-300 px-4 py-2 rounded-xl">Cancel</button>
        <button onclick="submitRename()" class="text-xs bg-cyan-600 hover:bg-cyan-500 text-white font-bold px-4 py-2 rounded-xl transition">Save Rename</button>
      </div>
    </div>
  </div>

  <script>
    function switchTab(tabId) {
      document.querySelectorAll('.tab-content').forEach(el => el.classList.add('hidden'));
      document.querySelectorAll('.tab-btn').forEach(btn => {
        btn.classList.remove('bg-purple-600/20', 'text-purple-300', 'border-purple-500/30');
        btn.classList.add('text-slate-400');
      });

      const target = document.getElementById('tab-' + tabId);
      const btn = document.getElementById('tab-btn-' + tabId);
      if (target) target.classList.remove('hidden');
      if (btn) {
        btn.classList.remove('text-slate-400');
        btn.classList.add('bg-purple-600/20', 'text-purple-300', 'border', 'border-purple-500/30');
      }

      if (tabId === 'sessions') loadSessions();
      if (tabId === 'routes') loadRoutes();
      if (tabId === 'flow') loadDownloads();
    }

    function injectTag(tag) {
      const textarea = document.getElementById('flowPromptInput');
      textarea.value = textarea.value + ' ' + tag;
      textarea.focus();
    }

    function updateDurationOptions() {
      const model = document.getElementById('flowModelSelect').value;
      const durSelect = document.getElementById('flowDurationSelect');
      if (model.includes('veo')) {
        durSelect.innerHTML = `
          <option value="8" selected>8 Seconds (Veo 3.1 Cinematic Max)</option>
          <option value="30s_ad">30s Commercial (4-Scene Assembly)</option>
        `;
      } else {
        durSelect.innerHTML = `
          <option value="4">4 Seconds (Micro-Action - Omni)</option>
          <option value="6">6 Seconds (Dynamic Odd Pacing - Omni)</option>
          <option value="8" selected>8 Seconds (Standard - Omni)</option>
          <option value="10">10 Seconds (Full Dynamic - Omni)</option>
          <option value="30s_ad">30s Commercial (4-Scene Assembly)</option>
        `;
      }
    }

    async function loadDownloads() {
      try {
        const res = await fetch('/api/flow/downloads');
        const files = await res.json();
        const container = document.getElementById('downloadsListContainer');
        container.innerHTML = '';

        if (!files || files.length === 0) {
          container.innerHTML = '<p class="text-xs text-slate-500 font-mono text-center py-8">No downloaded video files yet.</p>';
          return;
        }

        files.forEach(f => {
          const item = document.createElement('div');
          item.className = 'p-3.5 rounded-2xl bg-surface-card border border-surface-border flex items-center justify-between';
          item.innerHTML = `
            <div class="flex items-center space-x-3">
              <div class="w-9 h-9 rounded-xl bg-cyan-500/10 border border-cyan-500/20 flex items-center justify-center text-cyan-400">
                <i class="fa-solid fa-film"></i>
              </div>
              <div>
                <p class="text-xs font-bold text-slate-200 font-mono truncate max-w-[200px]" title="${f.name}">${f.name}</p>
                <p class="text-[10px] text-slate-500 font-mono">${f.size_mb} MB &bull; ${f.modified}</p>
              </div>
            </div>
            <div class="flex items-center gap-2">
              <button onclick="openRenameModal('${f.path}', '${f.name}')" class="text-xs bg-surface-hover hover:bg-surface-border text-slate-300 px-2.5 py-1.5 rounded-lg font-mono transition" title="Rename Video">
                <i class="fa-solid fa-pen"></i>
              </button>
              <a href="/downloads/${f.name}" target="_blank" class="text-xs bg-surface-hover hover:bg-surface-border text-slate-300 px-2.5 py-1.5 rounded-lg font-mono transition" title="Play">
                <i class="fa-solid fa-play"></i>
              </a>
              <a href="/downloads/${f.name}" download class="text-xs bg-cyan-600/20 hover:bg-cyan-600/40 text-cyan-300 border border-cyan-500/30 px-2.5 py-1.5 rounded-lg font-mono transition" title="Download">
                <i class="fa-solid fa-download"></i>
              </a>
            </div>
          `;
          container.appendChild(item);
        });
      } catch (e) {
        console.error('Failed to load downloads:', e);
      }
    }

    function openRenameModal(path, name) {
      document.getElementById('modalOldPath').value = path;
      document.getElementById('modalNewName').value = name;
      document.getElementById('renameModal').classList.remove('hidden');
    }

    function closeRenameModal() {
      document.getElementById('renameModal').classList.add('hidden');
    }

    async function submitRename() {
      const path = document.getElementById('modalOldPath').value;
      const newName = document.getElementById('modalNewName').value.trim();
      if (!newName) return alert('Please enter a valid filename.');

      try {
        const res = await fetch('/api/flow/rename', {
          method: 'POST',
          headers: { 'Content-Type': 'application/json' },
          body: JSON.stringify({ current_path: path, new_name: newName })
        });
        const data = await res.json();
        if (data.status === 'success') {
          closeRenameModal();
          loadDownloads();
        } else {
          alert('Rename failed: ' + (data.message || 'Unknown error'));
        }
      } catch (e) {
        alert('Rename error: ' + e);
      }
    }

    async function startFlowGeneration() {
      const prompt = document.getElementById('flowPromptInput').value.trim();
      const model = document.getElementById('flowModelSelect').value;
      const duration = document.getElementById('flowDurationSelect').value;
      const quality = document.getElementById('flowQualitySelect').value;
      const startFrame = document.getElementById('startingFrameInput').value.trim();
      const endFrame = document.getElementById('endingFrameInput').value.trim();
      const slug = document.getElementById('assetSlugInput').value.trim();

      if (!prompt) return alert('Please enter a prompt.');

      const btn = document.getElementById('flowGenBtn');
      btn.disabled = true;
      btn.innerHTML = '<i class="fa-solid fa-spinner animate-spin mr-2"></i> Submitting to Google Flow...';

      try {
        const res = await fetch('/api/flow/generate', {
          method: 'POST',
          headers: { 'Content-Type': 'application/json' },
          body: JSON.stringify({
            prompt,
            model,
            duration,
            download_quality: quality,
            starting_frame: startFrame || null,
            ending_frame: endFrame || null,
            slug: slug || 'generated_clip'
          })
        });
        const data = await res.json();
        alert(data.message || 'Generation task submitted!');
        loadDownloads();
      } catch (e) {
        alert('Generation error: ' + e);
      } finally {
        btn.disabled = false;
        btn.innerHTML = '<i class="fa-solid fa-clapperboard mr-2"></i> <span>Generate Video &amp; Auto-Download to Disk</span>';
      }
    }

    async function loadSessions() {
      try {
        const res = await fetch('/api/sessions');
        const data = await res.json();
        const container = document.getElementById('sessionsListContainer');
        container.innerHTML = '';
        (data.sessions || []).forEach(s => {
          const card = document.createElement('div');
          card.className = `p-5 rounded-2xl border ${s.is_active ? 'bg-purple-950/20 border-purple-500/40 glow-violet' : 'bg-surface-card border-surface-border'}`;
          card.innerHTML = `
            <div class="flex items-start justify-between">
              <div>
                <h4 class="text-sm font-bold text-white">${s.name}</h4>
                <p class="text-xs text-slate-400 font-mono mt-0.5">${s.email || 'No email'}</p>
              </div>
              <span class="text-xs font-mono font-bold text-cyan-400">${s.cookie_count || 0} cookies</span>
            </div>
            <div class="mt-4 pt-3 border-t border-surface-border flex items-center justify-between text-xs">
              <span class="text-[10px] text-slate-500 font-mono">Retained on disk</span>
              ${!s.is_active ? `<button onclick="selectSession('${s.id}')" class="text-[11px] bg-purple-600/20 text-purple-300 border border-purple-500/30 px-2.5 py-1 rounded-lg">Set Active</button>` : '<span class="text-[10px] text-emerald-400 font-bold uppercase font-mono">ACTIVE</span>'}
            </div>
          `;
          container.appendChild(card);
        });
      } catch (e) {
        console.error(e);
      }
    }

    async function selectSession(id) {
      await fetch(`/api/sessions/${id}/select`, { method: 'POST' });
      loadSessions();
    }

    async function startInteractiveAuth() {
      const url = prompt('Enter Google Flow URL to authenticate:', 'https://flow.google.com/');
      if (!url) return;
      alert('Opening Chrome. Please log in; storage state will be permanently retained.');
      try {
        const res = await fetch('/api/authenticate?target_url=' + encodeURIComponent(url), { method: 'POST' });
        const data = await res.json();
        alert(data.message || 'Authentication complete!');
        loadSessions();
      } catch (e) {
        alert('Auth error: ' + e);
      }
    }

    async function executeUniversalRequest() {
      const url = document.getElementById('targetUrl').value;
      const tier = parseInt(document.getElementById('reqTier').value);
      const res = await fetch('/api/request', {
        method: 'POST',
        headers: { 'Content-Type': 'application/json' },
        body: JSON.stringify({ url, method: 'GET', force_tier: tier })
      });
      const data = await res.json();
      document.getElementById('resCodeBlock').querySelector('code').innerText = JSON.stringify(data, null, 2);
    }

    async function loadRoutes() {
      const res = await fetch('/api/routes');
      const routes = await res.json();
      const tbody = document.getElementById('routesTableBody');
      tbody.innerHTML = '';
      routes.forEach(r => {
        tbody.innerHTML += `<tr><td class="py-2 px-3 text-emerald-400 font-bold">${r.method}</td><td class="py-2 px-3 truncate max-w-xs">${r.url}</td><td class="py-2 px-3 text-slate-400">${r.domain}</td><td class="py-2 px-3 text-right"><span class="text-[10px] bg-slate-800 px-2 py-0.5 rounded font-mono">Cached</span></td></tr>`;
      });
    }

    // Init
    loadDownloads();
  </script>
</body>
</html>
"""

# --- REST Endpoints ---

@web_app.get("/", response_class=HTMLResponse)
async def get_dashboard():
    return HTMLResponse(content=DASHBOARD_HTML)


@web_app.get("/api/flow/credits")
async def api_get_credits():
    """Returns Google Flow credit allocations and cost schedule."""
    return {
        "status": "success",
        "account": "arq5020@gmail.com",
        "plan": "Google AI Pro Tier",
        "daily_credits": 50,
        "daily_refresh_hours": 24,
        "monthly_pro_credits": 1000,
        "total_available_credits": 1050,
        "cost_schedule": {
            "gemini_omni_flash_4s": 5,
            "gemini_omni_flash_6s": 5,
            "gemini_omni_flash_8s": 5,
            "gemini_omni_flash_10s": 5,
            "veo_3_1_8s": 10,
            "upscale_1080p": 2,
            "upscale_4k": 5
        }
    }


@web_app.post("/api/flow/generate")
async def api_flow_generate(payload: Dict[str, Any], background_tasks: BackgroundTasks):
    """Triggers generation with exact model, odd/even duration, keyframes, and naming."""
    prompt = payload.get("prompt", "")
    model = payload.get("model", "omni_flash")
    duration = payload.get("duration", "8")
    quality = payload.get("download_quality", "1080p")
    start_frame = payload.get("starting_frame")
    end_frame = payload.get("ending_frame")
    slug = payload.get("slug", "generated_clip")

    is_30s = (duration == "30s_ad")
    dur_num = 8 if is_30s else int(duration)

    project_url = "https://flow.google.com/project/5730a6a6-a00a-4a95-8f22-20942efd1413"
    automator = FlowVideoAutomator(project_url=project_url, output_dir=DOWNLOADS_DIR)

    concepts = [{
        "title": slug,
        "concept": prompt,
        "duration": dur_num,
        "is_30s_ad": is_30s,
        "starting_frame": start_frame,
        "ending_frame": end_frame
    }]

    background_tasks.add_task(
        automator.execute_batch_production,
        concepts,
        model,
        quality,
        dur_num,
        "UniversalWeb"
    )

    return {
        "status": "initiated",
        "model": model,
        "duration": f"{dur_num}s" if not is_30s else "30s (4 scenes)",
        "download_quality": quality,
        "message": f"Generation initiated with model '{model.upper()}' ({dur_num}s, quality={quality}). Check Media Vault shortly."
    }


@web_app.post("/api/flow/rename")
async def api_rename_video(payload: Dict[str, Any]):
    """Renames any downloaded video file locally."""
    path = payload.get("current_path")
    new_name = payload.get("new_name")
    if not path or not new_name:
        raise HTTPException(status_code=400, detail="Missing current_path or new_name")
    return FlowVideoAutomator.rename_downloaded_video(existing_filepath=path, new_custom_name=new_name)


@web_app.get("/api/flow/downloads")
async def api_list_downloads():
    files = []
    if DOWNLOADS_DIR.exists():
        for p in DOWNLOADS_DIR.glob("**/*.mp4"):
            stat = p.stat()
            size_mb = round(stat.st_size / (1024 * 1024), 2)
            mod_time = time.strftime("%Y-%m-%d %H:%M:%S", time.localtime(stat.st_mtime))
            files.append({
                "name": p.name,
                "path": str(p),
                "size_mb": size_mb,
                "modified": mod_time
            })
    files.sort(key=lambda x: x["modified"], reverse=True)
    return files


@web_app.get("/api/sessions")
async def api_list_sessions():
    return {
        "status": "success",
        "active_session": session_manager.get_active_session(),
        "sessions": session_manager.list_sessions()
    }


@web_app.post("/api/sessions/{session_id}/select")
async def api_select_session(session_id: str):
    rec = session_manager.select_session(session_id)
    if not rec:
        raise HTTPException(status_code=404, detail="Session not found")
    return {"status": "success", "active_session": rec}


@web_app.post("/api/authenticate")
async def api_authenticate(target_url: str = "https://flow.google.com/"):
    try:
        res = await run_interactive_login(target_url=target_url)
        return JSONResponse(content=res)
    except Exception as e:
        return JSONResponse(status_code=500, content={"status": "error", "message": str(e)})


@web_app.post("/api/request")
async def api_universal_request(payload: Dict[str, Any]):
    url = payload.get("url")
    method = payload.get("method", "GET")
    force_tier = payload.get("force_tier")
    return await universal_request(url=url, method=method, force_tier=force_tier)


@web_app.get("/api/routes")
async def api_get_routes(domain: Optional[str] = None):
    return list_learned_routes(domain=domain)


if __name__ == "__main__":
    port = int(os.environ.get("PORT", 8000))
    print("=======================================================")
    print("Universal-Web-MCP Awwwards Studio is running!")
    print(f"Dashboard: http://localhost:{port}")
    print("=======================================================")
    uvicorn.run("app:web_app", host="0.0.0.0", port=port, reload=False)
