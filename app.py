"""
Universal-Web-MCP Minimalist Studio.
Inspired by top Awwwards minimal designs (Linear.app, Reflect.app, Vercel).
Features:
- Minimal text, zero clutter, ultra-clean aesthetic.
- Seamless Light / Dark theme toggle (persisted in localStorage).
- Persistent Session Manager with clear status (Connected vs Needs Login, 1-Click Connect).
- Generative Studio: Omni Flash (4s, 6s, 8s, 10s), Veo 3.1 (8s), Keyframe Interpolation, 1080p default.
- Download Vault with inline file renaming.
- 3-Tier Routing Playground (<200ms Fast Path).
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
from flow_video_automator import FlowVideoAutomator, format_download_filename, build_30s_storyboard, validate_and_educate_prompt

BASE_DIR = Path(__file__).resolve().parent
DOWNLOADS_DIR = BASE_DIR / "downloads"
DOWNLOADS_DIR.mkdir(parents=True, exist_ok=True)

web_app = FastAPI(
    title="Universal-Web-MCP Minimal Studio",
    description="Sub-second 3-Tier Hybrid Routing & Autonomous Creative Studio",
    version="4.0.0"
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
  <title>Universal-Web-MCP | Minimal Studio</title>
  <script src="https://cdn.tailwindcss.com"></script>
  <link rel="preconnect" href="https://fonts.googleapis.com">
  <link rel="preconnect" href="https://fonts.gstatic.com" crossorigin>
  <link href="https://fonts.googleapis.com/css2?family=Plus+Jakarta+Sans:wght@300;400;500;600;700&family=JetBrains+Mono:wght@400;500;600&display=swap" rel="stylesheet">
  <link rel="stylesheet" href="https://cdnjs.cloudflare.com/ajax/libs/font-awesome/6.5.1/css/all.min.css">
  <script>
    tailwind.config = {
      darkMode: 'class',
      theme: {
        extend: {
          fontFamily: {
            sans: ['"Plus Jakarta Sans"', 'sans-serif'],
            mono: ['"JetBrains Mono"', 'monospace'],
          },
          colors: {
            brand: '#6366f1',
          }
        }
      }
    }
  </script>
  <style>
    /* Dark Theme */
    html.dark {
      background-color: #090a0f;
      color: #f1f5f9;
    }
    html.dark .ui-bg { background-color: #090a0f; }
    html.dark .ui-panel {
      background: rgba(18, 20, 30, 0.75);
      border: 1px solid rgba(255, 255, 255, 0.08);
      box-shadow: 0 10px 30px -10px rgba(0, 0, 0, 0.5);
    }
    html.dark .ui-input {
      background: #0f111a;
      border: 1px solid rgba(255, 255, 255, 0.1);
      color: #f8fafc;
    }
    html.dark .ui-subpanel {
      background: #0f111a;
      border: 1px solid rgba(255, 255, 255, 0.06);
    }
    html.dark .ui-border { border-color: rgba(255, 255, 255, 0.08); }
    html.dark .ui-text-muted { color: #94a3b8; }
    html.dark .ui-text-dim { color: #64748b; }

    /* Light Theme (Linear / Vercel minimal aesthetic) */
    html:not(.dark) {
      background-color: #f8fafc;
      color: #0f172a;
    }
    html:not(.dark) .ui-bg { background-color: #f8fafc; }
    html:not(.dark) .ui-panel {
      background: rgba(255, 255, 255, 0.95);
      border: 1px solid rgba(0, 0, 0, 0.08);
      box-shadow: 0 4px 20px -2px rgba(0, 0, 0, 0.04);
    }
    html:not(.dark) .ui-input {
      background: #ffffff;
      border: 1px solid rgba(0, 0, 0, 0.12);
      color: #0f172a;
    }
    html:not(.dark) .ui-subpanel {
      background: #f1f5f9;
      border: 1px solid rgba(0, 0, 0, 0.06);
    }
    html:not(.dark) .ui-border { border-color: rgba(0, 0, 0, 0.08); }
    html:not(.dark) .ui-text-muted { color: #64748b; }
    html:not(.dark) .ui-text-dim { color: #94a3b8; }

    .custom-scrollbar::-webkit-scrollbar { width: 5px; height: 5px; }
    .custom-scrollbar::-webkit-scrollbar-track { background: transparent; }
    .custom-scrollbar::-webkit-scrollbar-thumb { background: rgba(150, 150, 150, 0.25); border-radius: 4px; }
  </style>
</head>
<body class="ui-bg min-h-screen flex flex-col font-sans transition-colors duration-200">

  <!-- Minimal Header -->
  <header class="ui-border border-b backdrop-blur-md sticky top-0 z-30">
    <div class="max-w-6xl mx-auto px-6 py-3.5 flex items-center justify-between">
      <div class="flex items-center space-x-3">
        <div class="w-8 h-8 rounded-lg bg-indigo-600 flex items-center justify-center text-white shadow-sm font-mono font-bold text-sm">
          UW
        </div>
        <div>
          <span class="font-semibold text-sm tracking-tight flex items-center gap-2">
            Universal-Web-MCP
            <span class="text-[10px] font-mono px-2 py-0.5 rounded-full bg-indigo-500/10 text-indigo-500 font-medium">FastMCP</span>
          </span>
        </div>
      </div>

      <!-- Right HUD & Theme Switch -->
      <div class="flex items-center space-x-3">
        <!-- Active Session Pill -->
        <div id="activeSessionBadge" class="flex items-center gap-2 px-3 py-1.5 rounded-lg ui-subpanel text-xs font-mono">
          <span class="w-2 h-2 rounded-full bg-emerald-500"></span>
          <span class="ui-text-dim">Active:</span>
          <span id="activeAccountName" class="font-medium text-indigo-500">None</span>
        </div>

        <!-- Credits Badge -->
        <div class="hidden sm:flex items-center gap-2 px-3 py-1.5 rounded-lg ui-subpanel text-xs font-mono">
          <span class="ui-text-dim">Credits:</span>
          <span class="text-emerald-500 font-semibold" title="50 Daily + 1,000 Monthly">1,050</span>
        </div>

        <!-- Light / Dark Theme Toggle Button -->
        <button onclick="toggleTheme()" id="themeToggleBtn" class="p-2 rounded-lg ui-subpanel ui-text-muted hover:text-indigo-500 transition text-xs" title="Toggle Light / Dark mode">
          <i class="fa-solid fa-moon"></i>
        </button>

        <button onclick="startInteractiveLogin()" class="bg-indigo-600 hover:bg-indigo-500 text-white font-medium text-xs px-3.5 py-1.5 rounded-lg transition shadow-sm flex items-center gap-2">
          <i class="fa-solid fa-plus text-[10px]"></i>
          <span>Login Account</span>
        </button>
      </div>
    </div>
  </header>

  <!-- Minimal Nav Tabs -->
  <div class="ui-border border-b">
    <div class="max-w-6xl mx-auto px-6 flex items-center space-x-1">
      <button onclick="switchTab('flow')" id="tab-btn-flow" class="tab-btn py-3 px-4 text-xs font-medium border-b-2 border-indigo-500 text-indigo-500 transition flex items-center gap-2">
        <i class="fa-solid fa-video"></i>
        <span>Video Studio</span>
      </button>
      <button onclick="switchTab('sessions')" id="tab-btn-sessions" class="tab-btn py-3 px-4 text-xs font-medium border-b-2 border-transparent ui-text-dim hover:text-indigo-500 transition flex items-center gap-2">
        <i class="fa-solid fa-users"></i>
        <span>Sessions</span>
      </button>
      <button onclick="switchTab('learner')" id="tab-btn-learner" class="tab-btn py-3 px-4 text-xs font-medium border-b-2 border-transparent ui-text-dim hover:text-indigo-500 transition flex items-center gap-2">
        <i class="fa-solid fa-compass"></i>
        <span>Explore Platform</span>
      </button>
      <button onclick="switchTab('playground')" id="tab-btn-playground" class="tab-btn py-3 px-4 text-xs font-medium border-b-2 border-transparent ui-text-dim hover:text-indigo-500 transition flex items-center gap-2">
        <i class="fa-solid fa-bolt"></i>
        <span>3-Tier Runner</span>
      </button>
    </div>
  </div>

  <!-- Main Content -->
  <main class="max-w-6xl w-full mx-auto px-6 py-6 flex-1 space-y-6">

    <!-- TAB 1: VIDEO STUDIO -->
    <div id="tab-flow" class="tab-content space-y-6">
      <div class="grid grid-cols-1 lg:grid-cols-12 gap-6">

        <!-- Controls Column -->
        <div class="lg:col-span-7 space-y-4">
          <div class="ui-panel rounded-2xl p-5 space-y-4">
            
            <!-- Model & Quality -->
            <div class="grid grid-cols-2 gap-3">
              <div>
                <label class="text-[11px] font-mono uppercase tracking-wider ui-text-dim font-medium">Model</label>
                <select id="modelSelect" onchange="onModelChange()" class="mt-1 w-full ui-input rounded-xl px-3 py-2 text-xs font-mono">
                  <option value="omni_flash" selected>Gemini Omni Flash</option>
                  <option value="veo_3_1">Google Veo 3.1</option>
                  <option value="gemini_omni">Gemini Omni</option>
                </select>
              </div>
              <div>
                <label class="text-[11px] font-mono uppercase tracking-wider ui-text-dim font-medium">Quality</label>
                <select id="qualitySelect" class="mt-1 w-full ui-input rounded-xl px-3 py-2 text-xs font-mono">
                  <option value="1080p" selected>1080p Upscaled</option>
                  <option value="720p">720p Native</option>
                  <option value="4k">4K Ultra HD</option>
                </select>
              </div>
            </div>

            <!-- Duration Pills -->
            <div>
              <label class="text-[11px] font-mono uppercase tracking-wider ui-text-dim font-medium">Duration</label>
              <div id="durationPills" class="flex flex-wrap gap-2 mt-1.5">
                <button type="button" onclick="setDuration('4')" class="dur-btn px-3 py-1.5 rounded-lg text-xs font-mono border ui-subpanel ui-border text-slate-300">4s</button>
                <button type="button" onclick="setDuration('6')" class="dur-btn px-3 py-1.5 rounded-lg text-xs font-mono border ui-subpanel ui-border text-slate-300">6s</button>
                <button type="button" onclick="setDuration('8')" class="dur-btn px-3 py-1.5 rounded-lg text-xs font-mono border border-indigo-500 bg-indigo-500/10 text-indigo-500 font-semibold">8s</button>
                <button type="button" onclick="setDuration('10')" class="dur-btn px-3 py-1.5 rounded-lg text-xs font-mono border ui-subpanel ui-border text-slate-300">10s</button>
                <button type="button" onclick="setDuration('30s_ad')" class="dur-btn px-3 py-1.5 rounded-lg text-xs font-mono border ui-subpanel ui-border text-slate-300">30s Ad (4-Scenes)</button>
              </div>
              <input type="hidden" id="selectedDuration" value="8">
            </div>

            <!-- Keyframes (Collapsible) -->
            <details class="ui-subpanel rounded-xl p-3 text-xs">
              <summary class="cursor-pointer font-mono text-[11px] ui-text-dim select-none hover:text-indigo-500">
                <i class="fa-solid fa-arrows-left-right mr-1.5"></i> Optional Keyframes (Start &amp; End Interpolation)
              </summary>
              <div class="grid grid-cols-2 gap-3 mt-3 pt-2 border-t ui-border">
                <div>
                  <label class="text-[10px] font-mono ui-text-dim">Start Frame (0s):</label>
                  <input id="startFrame" type="text" placeholder="@FirstFrame or Asset ID" class="mt-1 w-full ui-input rounded-lg px-2.5 py-1.5 text-xs font-mono">
                </div>
                <div>
                  <label class="text-[10px] font-mono ui-text-dim">End Frame (4s-10s):</label>
                  <input id="endFrame" type="text" placeholder="@LastFrame or Asset ID" class="mt-1 w-full ui-input rounded-lg px-2.5 py-1.5 text-xs font-mono">
                </div>
              </div>
            </details>

            <!-- Prompt -->
            <div>
              <div class="flex items-center justify-between mb-1">
                <label class="text-[11px] font-mono uppercase tracking-wider ui-text-dim font-medium">Prompt</label>
                <div class="flex gap-1.5">
                  <button type="button" onclick="appendTag('Cinematic 35mm lens, 4K ')" class="text-[10px] font-mono px-2 py-0.5 rounded ui-subpanel ui-text-dim hover:text-indigo-500">+ 35mm</button>
                  <button type="button" onclick="appendTag('FPV drone push-in, volumetric lighting ')" class="text-[10px] font-mono px-2 py-0.5 rounded ui-subpanel ui-text-dim hover:text-indigo-500">+ FPV</button>
                </div>
              </div>
              <textarea id="promptInput" rows="3" class="w-full ui-input rounded-xl p-3 text-xs font-mono placeholder:text-slate-500" placeholder="Describe the scene...">A futuristic developer terminal displaying neon cyan data streams at sub-second speed. Smooth 35mm camera motion, volumetric reflections, 4K resolution.</textarea>
            </div>

            <!-- Custom Slug & Action -->
            <div class="flex items-center gap-3 pt-1">
              <div class="flex-1">
                <input id="slugInput" type="text" value="universal_web_launch" placeholder="Video name slug" class="w-full ui-input rounded-xl px-3 py-2 text-xs font-mono">
              </div>
              <button id="genBtn" onclick="submitGeneration()" class="bg-indigo-600 hover:bg-indigo-500 text-white font-medium text-xs px-5 py-2.5 rounded-xl transition shadow-sm flex items-center gap-2 whitespace-nowrap">
                <i class="fa-solid fa-play text-[10px]"></i>
                <span>Generate Video</span>
              </button>
            </div>

          </div>
        </div>

        <!-- Download Vault Column -->
        <div class="lg:col-span-5">
          <div class="ui-panel rounded-2xl p-5 flex flex-col h-full min-h-[420px]">
            <div class="flex items-center justify-between border-b ui-border pb-3 mb-3">
              <span class="text-xs font-mono uppercase tracking-wider font-semibold">Downloaded Videos</span>
              <button onclick="loadDownloads()" class="ui-text-dim hover:text-indigo-500 transition text-xs">
                <i class="fa-solid fa-rotate"></i>
              </button>
            </div>
            <div id="downloadsList" class="space-y-2.5 flex-1 overflow-auto custom-scrollbar max-h-[380px]">
              <!-- Dynamically populated -->
            </div>
          </div>
        </div>

      </div>
    </div>

    <!-- TAB 2: SESSIONS -->
    <div id="tab-sessions" class="tab-content hidden space-y-4">
      <div class="ui-panel rounded-2xl p-6 space-y-4">
        <div class="flex items-center justify-between border-b ui-border pb-4">
          <div>
            <h2 class="text-sm font-semibold tracking-tight">Connected Google Accounts</h2>
            <p class="text-xs ui-text-dim mt-0.5">The active account is used for video generation and API requests. Saved permanently in sessions.json.</p>
          </div>
          <button onclick="startInteractiveLogin()" class="bg-indigo-600 hover:bg-indigo-500 text-white font-medium text-xs px-3.5 py-2 rounded-xl transition shadow-sm flex items-center gap-2">
            <i class="fa-solid fa-plus text-[10px]"></i>
            <span>Add Account</span>
          </button>
        </div>

        <div id="sessionsGrid" class="grid grid-cols-1 md:grid-cols-2 lg:grid-cols-3 gap-4">
          <!-- Loaded dynamically -->
        </div>
      </div>
    </div>

    <!-- TAB 3: PLATFORM EXPLORER -->
    <div id="tab-learner" class="tab-content hidden space-y-4">
      <div class="ui-panel rounded-2xl p-6 space-y-4">
        <div>
          <h2 class="text-sm font-semibold tracking-tight">Autonomous Platform Explorer</h2>
          <p class="text-xs ui-text-dim mt-0.5">Discovers navigation, inputs, and APIs on any website and compiles a skill profile.</p>
        </div>

        <div class="flex gap-2">
          <input id="learnerUrl" type="url" value="https://flow.google.com/" placeholder="Enter URL..." class="flex-1 ui-input rounded-xl px-3.5 py-2.5 text-xs font-mono">
          <button id="learnerBtn" onclick="runLearner()" class="bg-indigo-600 hover:bg-indigo-500 text-white font-medium text-xs px-4 py-2.5 rounded-xl transition whitespace-nowrap">
            <span>Explore Platform</span>
          </button>
        </div>

        <div id="learnerStatusBox" class="ui-subpanel rounded-xl p-4 text-xs font-mono space-y-2">
          <div class="flex justify-between items-center">
            <span id="learnerPhase" class="font-semibold text-emerald-500">Ready</span>
            <span id="learnerPct" class="ui-text-dim">100%</span>
          </div>
          <div class="w-full bg-slate-800 rounded-full h-1.5 overflow-hidden">
            <div id="learnerBar" class="bg-indigo-500 h-1.5 transition-all duration-300" style="width: 100%"></div>
          </div>
          <p id="learnerText" class="ui-text-dim text-[11px]">Platform skill compiled and ready.</p>
        </div>
      </div>
    </div>

    <!-- TAB 4: 3-TIER RUNNER -->
    <div id="tab-playground" class="tab-content hidden space-y-4">
      <div class="ui-panel rounded-2xl p-6 space-y-4">
        <h2 class="text-sm font-semibold tracking-tight">3-Tier Hybrid Runner</h2>
        <div class="flex gap-2">
          <input id="runnerUrl" type="url" value="https://jsonplaceholder.typicode.com/todos/1" class="flex-1 ui-input rounded-xl px-3.5 py-2.5 text-xs font-mono">
          <select id="runnerTier" class="ui-input rounded-xl px-3 py-2 text-xs font-mono">
            <option value="1">Tier 1: Fast Path (&lt;200ms)</option>
            <option value="2">Tier 2: CDP Sniffer</option>
            <option value="3">Tier 3: DOM Fallback</option>
          </select>
          <button onclick="runRequest()" class="bg-indigo-600 hover:bg-indigo-500 text-white font-medium text-xs px-4 py-2.5 rounded-xl transition">Run</button>
        </div>
        <pre id="runnerOutput" class="p-3.5 rounded-xl ui-subpanel text-xs font-mono ui-text-muted max-h-72 overflow-auto custom-scrollbar"><code>Output will appear here.</code></pre>
      </div>
    </div>

  </main>

  <!-- Inline Rename Modal -->
  <div id="renameModal" class="hidden fixed inset-0 z-50 bg-black/60 backdrop-blur-sm flex items-center justify-center p-4">
    <div class="ui-panel rounded-2xl max-w-sm w-full p-5 space-y-3">
      <h3 class="text-xs font-semibold uppercase tracking-wider font-mono">Rename Video File</h3>
      <input id="newFilenameInput" type="text" class="w-full ui-input rounded-lg px-3 py-2 text-xs font-mono">
      <input id="oldFilepathInput" type="hidden">
      <div class="flex justify-end gap-2 pt-2">
        <button onclick="closeRenameModal()" class="text-xs ui-text-dim px-3 py-1.5 rounded-lg">Cancel</button>
        <button onclick="saveRename()" class="bg-indigo-600 text-white text-xs px-3.5 py-1.5 rounded-lg font-medium">Save</button>
      </div>
    </div>
  </div>

  <script>
    // Theme Management (Light / Dark)
    function initTheme() {
      const saved = localStorage.getItem('theme') || 'dark';
      if (saved === 'dark') {
        document.documentElement.classList.add('dark');
        document.getElementById('themeToggleBtn').innerHTML = '<i class="fa-solid fa-sun"></i>';
      } else {
        document.documentElement.classList.remove('dark');
        document.getElementById('themeToggleBtn').innerHTML = '<i class="fa-solid fa-moon"></i>';
      }
    }

    function toggleTheme() {
      const isDark = document.documentElement.classList.contains('dark');
      if (isDark) {
        document.documentElement.classList.remove('dark');
        localStorage.setItem('theme', 'light');
        document.getElementById('themeToggleBtn').innerHTML = '<i class="fa-solid fa-moon"></i>';
      } else {
        document.documentElement.classList.add('dark');
        localStorage.setItem('theme', 'dark');
        document.getElementById('themeToggleBtn').innerHTML = '<i class="fa-solid fa-sun"></i>';
      }
    }

    // Tabs
    function switchTab(tabId) {
      document.querySelectorAll('.tab-content').forEach(el => el.classList.add('hidden'));
      document.querySelectorAll('.tab-btn').forEach(btn => {
        btn.classList.remove('border-indigo-500', 'text-indigo-500');
        btn.classList.add('border-transparent', 'ui-text-dim');
      });

      const target = document.getElementById('tab-' + tabId);
      const btn = document.getElementById('tab-btn-' + tabId);
      if (target) target.classList.remove('hidden');
      if (btn) {
        btn.classList.remove('border-transparent', 'ui-text-dim');
        btn.classList.add('border-indigo-500', 'text-indigo-500');
      }

      if (tabId === 'sessions') loadSessions();
      if (tabId === 'flow') loadDownloads();
    }

    // Model & Durations
    function onModelChange() {
      const m = document.getElementById('modelSelect').value;
      const pills = document.getElementById('durationPills');
      if (m.includes('veo')) {
        pills.innerHTML = `
          <button type="button" onclick="setDuration('8')" class="dur-btn px-3 py-1.5 rounded-lg text-xs font-mono border border-indigo-500 bg-indigo-500/10 text-indigo-500 font-semibold">8s (Veo Max)</button>
          <button type="button" onclick="setDuration('30s_ad')" class="dur-btn px-3 py-1.5 rounded-lg text-xs font-mono border ui-subpanel ui-border text-slate-300">30s Ad (4-Scenes)</button>
        `;
        setDuration('8');
      } else {
        pills.innerHTML = `
          <button type="button" onclick="setDuration('4')" class="dur-btn px-3 py-1.5 rounded-lg text-xs font-mono border ui-subpanel ui-border text-slate-300">4s</button>
          <button type="button" onclick="setDuration('6')" class="dur-btn px-3 py-1.5 rounded-lg text-xs font-mono border ui-subpanel ui-border text-slate-300">6s</button>
          <button type="button" onclick="setDuration('8')" class="dur-btn px-3 py-1.5 rounded-lg text-xs font-mono border border-indigo-500 bg-indigo-500/10 text-indigo-500 font-semibold">8s</button>
          <button type="button" onclick="setDuration('10')" class="dur-btn px-3 py-1.5 rounded-lg text-xs font-mono border ui-subpanel ui-border text-slate-300">10s</button>
          <button type="button" onclick="setDuration('30s_ad')" class="dur-btn px-3 py-1.5 rounded-lg text-xs font-mono border ui-subpanel ui-border text-slate-300">30s Ad</button>
        `;
        setDuration('8');
      }
    }

    function setDuration(dur) {
      document.getElementById('selectedDuration').value = dur;
      document.querySelectorAll('.dur-btn').forEach(b => {
        b.className = 'dur-btn px-3 py-1.5 rounded-lg text-xs font-mono border ui-subpanel ui-border ui-text-muted';
      });
      event.target.className = 'dur-btn px-3 py-1.5 rounded-lg text-xs font-mono border border-indigo-500 bg-indigo-500/10 text-indigo-500 font-semibold';
    }

    function appendTag(t) {
      const area = document.getElementById('promptInput');
      area.value = area.value + ' ' + t;
      area.focus();
    }

    // Sessions Management
    async function loadSessions() {
      try {
        const res = await fetch('/api/sessions');
        const data = await res.json();
        const container = document.getElementById('sessionsGrid');
        container.innerHTML = '';

        const sessions = data.sessions || [];
        let activeName = 'None';

        sessions.forEach(s => {
          if (s.is_active) activeName = s.email || s.name;
          const hasCookies = (s.cookie_count || 0) > 0;

          const card = document.createElement('div');
          card.className = `p-4 rounded-xl border transition ${s.is_active ? 'border-indigo-500/60 bg-indigo-500/5' : 'ui-subpanel ui-border'}`;
          card.innerHTML = `
            <div class="flex items-start justify-between">
              <div>
                <p class="font-medium text-xs">${s.name}</p>
                <p class="text-[11px] font-mono ui-text-dim mt-0.5">${s.email || 'No email'}</p>
              </div>
              ${s.is_active ? '<span class="text-[9px] font-mono bg-emerald-500/20 text-emerald-500 border border-emerald-500/30 px-2 py-0.5 rounded uppercase font-semibold">ACTIVE</span>' : ''}
            </div>

            <div class="mt-3 flex items-center justify-between text-xs">
              <span class="text-[10px] font-mono ${hasCookies ? 'text-emerald-500' : 'text-amber-500'}">
                ${hasCookies ? `<i class="fa-solid fa-circle text-[6px] mr-1"></i>${s.cookie_count} cookies` : '<i class="fa-regular fa-circle text-[6px] mr-1"></i>No auth cookies'}
              </span>

              <div class="flex items-center gap-1.5">
                ${!hasCookies ? `<button onclick="startInteractiveLogin('${s.email}')" class="text-[10px] font-mono bg-amber-500/10 text-amber-500 border border-amber-500/30 px-2 py-1 rounded hover:bg-amber-500/20">Log In</button>` : ''}
                ${!s.is_active && hasCookies ? `<button onclick="selectSession('${s.id}')" class="text-[10px] font-mono bg-indigo-600/10 text-indigo-500 border border-indigo-500/30 px-2 py-1 rounded hover:bg-indigo-600/20">Set Active</button>` : ''}
                <button onclick="removeSession('${s.id}')" class="text-[10px] ui-text-dim hover:text-rose-500 p-1"><i class="fa-regular fa-trash-can"></i></button>
              </div>
            </div>
          `;
          container.appendChild(card);
        });

        document.getElementById('activeAccountName').innerText = activeName;
      } catch (e) {
        console.error(e);
      }
    }

    async function selectSession(id) {
      await fetch(`/api/sessions/${id}/select`, { method: 'POST' });
      loadSessions();
    }

    async function removeSession(id) {
      if (!confirm('Remove this session?')) return;
      await fetch(`/api/sessions/${id}`, { method: 'DELETE' });
      loadSessions();
    }

    async function startInteractiveLogin(presetEmail) {
      const email = prompt('Enter the Google account email to log into:', presetEmail || 'arq5158@gmail.com');
      if (!email) return;

      alert('Opening Chrome. Please log into ' + email + ' and open Google Flow. Your session will be saved permanently once authenticated.');

      try {
        const res = await fetch('/api/authenticate?target_url=' + encodeURIComponent('https://flow.google.com/') + '&expected_email=' + encodeURIComponent(email), { method: 'POST' });
        const data = await res.json();
        alert(data.message || 'Login completed!');
        loadSessions();
      } catch (e) {
        alert('Login error: ' + e);
      }
    }

    // Video Generation
    async function submitGeneration() {
      const prompt = document.getElementById('promptInput').value.trim();
      const model = document.getElementById('modelSelect').value;
      const duration = document.getElementById('selectedDuration').value;
      const quality = document.getElementById('qualitySelect').value;
      const startFrame = document.getElementById('startFrame').value.trim();
      const endFrame = document.getElementById('endFrame').value.trim();
      const slug = document.getElementById('slugInput').value.trim() || 'video';

      if (!prompt) return alert('Please enter a prompt');

      const btn = document.getElementById('genBtn');
      btn.disabled = true;
      btn.innerHTML = '<i class="fa-solid fa-spinner animate-spin"></i> Submitting...';

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
            slug
          })
        });
        const data = await res.json();
        alert(data.message || 'Generation submitted');
        loadDownloads();
      } catch (e) {
        alert('Error: ' + e);
      } finally {
        btn.disabled = false;
        btn.innerHTML = '<i class="fa-solid fa-play text-[10px]"></i> <span>Generate Video</span>';
      }
    }

    // Download Vault & Inline Rename
    async function loadDownloads() {
      try {
        const res = await fetch('/api/flow/downloads');
        const files = await res.json();
        const container = document.getElementById('downloadsList');
        container.innerHTML = '';

        if (!files || files.length === 0) {
          container.innerHTML = '<p class="text-xs ui-text-dim font-mono text-center py-8">No downloaded video files yet.</p>';
          return;
        }

        files.forEach(f => {
          const item = document.createElement('div');
          item.className = 'p-3 rounded-xl ui-subpanel border ui-border flex items-center justify-between';
          item.innerHTML = `
            <div class="truncate max-w-[220px]">
              <p class="text-xs font-mono font-medium truncate" title="${f.name}">${f.name}</p>
              <p class="text-[10px] font-mono ui-text-dim mt-0.5">${f.size_mb} MB &bull; ${f.modified}</p>
            </div>
            <div class="flex items-center gap-1.5">
              <button onclick="openRename('${f.path}', '${f.name}')" class="p-1.5 rounded ui-text-dim hover:text-indigo-500 transition" title="Rename"><i class="fa-solid fa-pen text-xs"></i></button>
              <a href="/downloads/${f.name}" target="_blank" class="p-1.5 rounded ui-text-dim hover:text-indigo-500 transition" title="Play"><i class="fa-solid fa-play text-xs"></i></a>
              <a href="/downloads/${f.name}" download class="p-1.5 rounded text-indigo-500 hover:text-indigo-400 transition" title="Download"><i class="fa-solid fa-download text-xs"></i></a>
            </div>
          `;
          container.appendChild(item);
        });
      } catch (e) {
        console.error(e);
      }
    }

    function openRename(path, name) {
      document.getElementById('oldFilepathInput').value = path;
      document.getElementById('newFilenameInput').value = name;
      document.getElementById('renameModal').classList.remove('hidden');
    }

    function closeRenameModal() {
      document.getElementById('renameModal').classList.add('hidden');
    }

    async function saveRename() {
      const path = document.getElementById('oldFilepathInput').value;
      const newName = document.getElementById('newFilenameInput').value.trim();
      if (!newName) return;
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
        alert(data.message || 'Error renaming');
      }
    }

    // Platform Explorer
    async function runLearner() {
      const url = document.getElementById('learnerUrl').value.trim();
      if (!url) return;
      const btn = document.getElementById('learnerBtn');
      btn.disabled = true;
      await fetch('/api/learn-platform', {
        method: 'POST',
        headers: { 'Content-Type': 'application/json' },
        body: JSON.stringify({ url })
      });
      pollLearner();
    }

    async function pollLearner() {
      const res = await fetch('/api/learn-platform/status');
      const s = await res.json();
      document.getElementById('learnerPhase').innerText = s.state;
      document.getElementById('learnerPct').innerText = (s.progress || 0) + '%';
      document.getElementById('learnerBar').style.width = (s.progress || 0) + '%';
      document.getElementById('learnerText').innerText = s.status_text || 'Exploring...';
      if (s.state !== 'READY' && s.state !== 'ERROR') {
        setTimeout(pollLearner, 1500);
      } else {
        document.getElementById('learnerBtn').disabled = false;
      }
    }

    // 3-Tier Runner
    async function runRequest() {
      const url = document.getElementById('runnerUrl').value;
      const tier = parseInt(document.getElementById('runnerTier').value);
      const res = await fetch('/api/request', {
        method: 'POST',
        headers: { 'Content-Type': 'application/json' },
        body: JSON.stringify({ url, method: 'GET', force_tier: tier })
      });
      const data = await res.json();
      document.getElementById('runnerOutput').querySelector('code').innerText = JSON.stringify(data, null, 2);
    }

    // Init
    initTheme();
    loadSessions();
    loadDownloads();
  </script>
</body>
</html>
"""

# =====================================================================
# REST API Endpoints
# =====================================================================

@web_app.get("/", response_class=HTMLResponse)
async def get_dashboard():
    return HTMLResponse(content=DASHBOARD_HTML)


@web_app.get("/api/flow/credits")
async def api_get_credits():
    return {
        "status": "success",
        "account": "arq5020@gmail.com",
        "plan": "Google AI Pro Tier",
        "daily_credits": 50,
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
    prompt = payload.get("prompt", "")
    model = payload.get("model", "omni_flash")
    duration = payload.get("duration", "8")
    quality = payload.get("download_quality", "1080p")
    start_frame = payload.get("starting_frame")
    end_frame = payload.get("ending_frame")
    slug = payload.get("slug", "video")

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
        "message": f"Generation queued for model '{model.upper()}' ({dur_num}s, quality={quality}). Check download vault shortly."
    }


@web_app.post("/api/flow/rename")
async def api_rename_video(payload: Dict[str, Any]):
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


@web_app.delete("/api/sessions/{session_id}")
async def api_delete_session(session_id: str):
    ok = session_manager.remove_session(session_id)
    return {"status": "success" if ok else "not_found"}


@web_app.post("/api/authenticate")
async def api_authenticate(target_url: str = "https://flow.google.com/", expected_email: Optional[str] = None):
    try:
        res = await run_interactive_login(target_url=target_url, expected_email=expected_email)
        return JSONResponse(content=res)
    except Exception as e:
        return JSONResponse(status_code=500, content={"status": "error", "message": str(e)})


@web_app.post("/api/learn-platform")
async def api_learn_platform(payload: Dict[str, Any], background_tasks: BackgroundTasks):
    url = payload.get("url", "https://flow.google.com/")
    background_tasks.add_task(platform_learner.learn_platform, url)
    return {"status": "started", "url": url}


@web_app.get("/api/learn-platform/status")
async def api_learn_platform_status():
    return platform_learner.get_status()


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
    print("Universal-Web-MCP Minimal Studio is running!")
    print(f"Dashboard: http://localhost:{port}")
    print("=======================================================")
    uvicorn.run("app:web_app", host="0.0.0.0", port=port, reload=False)
