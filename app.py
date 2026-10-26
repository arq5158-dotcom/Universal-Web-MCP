"""
Universal-Web-MCP Web Dashboard & SSE Server.
Combines:
1. Official Model Context Protocol (MCP) Server-Sent Events (SSE) server for remote AI clients.
2. Awwwards-Inspired Luxury Web Dashboard for:
   - 3-Tier Hybrid Routing (<200ms Fast Path, CDP Sniffer, DOM Fallback)
   - Persistent Multi-Session Profile Manager (Add, Remove, Retain across restarts)
   - Autonomous Platform Skill Learner with live progress ('getting ready on dashboard...')
   - Google Flow Creative Studio & Batch Video Automation (Veo 8s vs Omni Flash 10s, Agent mode, @ tags, local MP4 downloads)
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

# Import core MCP components
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
from flow_video_automator import FlowVideoAutomator, build_30s_storyboard

BASE_DIR = Path(__file__).resolve().parent
DOWNLOADS_DIR = BASE_DIR / "downloads"
DOWNLOADS_DIR.mkdir(parents=True, exist_ok=True)

# Initialize FastAPI app
web_app = FastAPI(
    title="Universal-Web-MCP Luxury Studio",
    description="3-Tier Hybrid Routing & Autonomous Web Bridge",
    version="2.0.0"
)

web_app.add_middleware(
    CORSMiddleware,
    allow_origins=["*"],
    allow_credentials=True,
    allow_methods=["*"],
    allow_headers=["*"],
)

# Mount downloads directory for direct video playback/downloading
web_app.mount("/downloads", StaticFiles(directory=str(DOWNLOADS_DIR)), name="downloads")

# Mount MCP SSE application at /mcp
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
  <title>Universal-Web-MCP | Luxury Autonomous Studio</title>
  <script src="https://cdn.tailwindcss.com"></script>
  <link rel="preconnect" href="https://fonts.googleapis.com">
  <link rel="preconnect" href="https://fonts.gstatic.com" crossorigin>
  <link href="https://fonts.googleapis.com/css2?family=Plus+Jakarta+Sans:wght@300;400;500;600;700;800&family=JetBrains+Mono:wght@400;500;600&display=swap" rel="stylesheet">
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
            obsidian: '#07080d',
            surface: {
              DEFAULT: '#0f111a',
              card: '#131622',
              border: '#1f2438',
              hover: '#292f49'
            },
            accent: {
              violet: '#8b5cf6',
              cyan: '#06b6d4',
              emerald: '#10b981',
              amber: '#f59e0b',
              rose: '#f43f5e'
            }
          }
        }
      }
    }
  </script>
  <style>
    body {
      background-color: #07080d;
      background-image: 
        radial-gradient(circle at 15% 15%, rgba(99, 102, 241, 0.08) 0%, transparent 45%),
        radial-gradient(circle at 85% 80%, rgba(16, 185, 129, 0.06) 0%, transparent 45%),
        radial-gradient(circle at 50% 50%, rgba(6, 182, 212, 0.04) 0%, transparent 60%);
      background-attachment: fixed;
    }
    .glass-panel {
      background: rgba(19, 22, 34, 0.7);
      backdrop-filter: blur(24px);
      -webkit-backdrop-filter: blur(24px);
      border: 1px solid rgba(255, 255, 255, 0.07);
      box-shadow: 0 20px 45px -15px rgba(0, 0, 0, 0.6);
    }
    .glass-input {
      background: rgba(15, 17, 26, 0.85);
      border: 1px solid rgba(255, 255, 255, 0.08);
      transition: all 0.2s ease;
    }
    .glass-input:focus {
      border-color: #8b5cf6;
      box-shadow: 0 0 15px -3px rgba(139, 92, 246, 0.3);
      outline: none;
    }
    .glow-violet {
      box-shadow: 0 0 25px -5px rgba(139, 92, 246, 0.4);
    }
    .glow-emerald {
      box-shadow: 0 0 25px -5px rgba(16, 185, 129, 0.4);
    }
    .custom-scrollbar::-webkit-scrollbar {
      width: 6px;
      height: 6px;
    }
    .custom-scrollbar::-webkit-scrollbar-track {
      background: rgba(0, 0, 0, 0.2);
    }
    .custom-scrollbar::-webkit-scrollbar-thumb {
      background: rgba(255, 255, 255, 0.15);
      border-radius: 3px;
    }
    .custom-scrollbar::-webkit-scrollbar-thumb:hover {
      background: rgba(255, 255, 255, 0.25);
    }
    @keyframes pulse-slow {
      0%, 100% { opacity: 1; transform: scale(1); }
      50% { opacity: 0.5; transform: scale(0.98); }
    }
    .animate-pulse-slow {
      animation: pulse-slow 3s infinite ease-in-out;
    }
  </style>
</head>
<body class="text-slate-100 min-h-screen flex flex-col font-sans selection:bg-purple-600/40">

  <!-- Top Luxury Glass Navbar -->
  <header class="border-b border-surface-border bg-obsidian/80 backdrop-blur-xl sticky top-0 z-50">
    <div class="max-w-7xl mx-auto px-6 py-3.5 flex items-center justify-between">
      <div class="flex items-center space-x-4">
        <div class="w-11 h-11 rounded-2xl bg-gradient-to-tr from-indigo-600 via-purple-600 to-cyan-500 flex items-center justify-center glow-violet shadow-lg">
          <i class="fa-solid fa-cube text-white text-lg"></i>
        </div>
        <div>
          <div class="flex items-center gap-2.5">
            <h1 class="text-lg font-bold tracking-tight text-white flex items-center gap-2">
              Universal-Web-MCP
              <span class="text-[10px] uppercase font-mono px-2 py-0.5 rounded-full bg-purple-500/10 text-purple-400 border border-purple-500/20 font-semibold tracking-wider">Awwwards Luxury Studio</span>
            </h1>
          </div>
          <p class="text-xs text-slate-400 font-mono flex items-center gap-2">
            <span>3-Tier Hybrid Routing</span>
            <span class="text-slate-600">&bull;</span>
            <span class="text-emerald-400">&lt;200ms Fast Path</span>
            <span class="text-slate-600">&bull;</span>
            <span>CDP Sniffer</span>
            <span class="text-slate-600">&bull;</span>
            <span>DOM Fallback</span>
          </p>
        </div>
      </div>

      <!-- Quick Session Badge & Actions -->
      <div class="flex items-center space-x-3">
        <div id="activeSessionBadge" class="hidden sm:flex items-center gap-2 px-3 py-1.5 rounded-xl bg-surface-card border border-surface-border text-xs">
          <span class="w-2 h-2 rounded-full bg-emerald-400 animate-ping"></span>
          <span class="text-slate-400">Active Profile:</span>
          <span id="activeSessionName" class="font-semibold text-slate-200 font-mono">None</span>
        </div>
        <button onclick="switchTab('sessions')" class="text-xs bg-surface-card hover:bg-surface-hover border border-surface-border text-slate-200 px-3 py-2 rounded-xl transition flex items-center gap-2">
          <i class="fa-solid fa-users text-purple-400"></i>
          <span>Sessions</span>
        </button>
        <button onclick="startInteractiveAuth()" class="text-xs bg-gradient-to-r from-purple-600 to-indigo-600 hover:from-purple-500 hover:to-indigo-500 text-white font-medium px-4 py-2 rounded-xl transition shadow-lg shadow-purple-600/20 flex items-center gap-2">
          <i class="fa-solid fa-key"></i>
          <span>1-Click Google Login</span>
        </button>
      </div>
    </div>
  </header>

  <!-- Main Content Container -->
  <main class="flex-1 max-w-7xl w-full mx-auto px-6 py-6 space-y-6">

    <!-- KPI / Status Cards -->
    <div class="grid grid-cols-2 md:grid-cols-4 gap-4">
      <div class="glass-panel rounded-2xl p-4 flex items-center justify-between">
        <div>
          <p class="text-[11px] font-mono uppercase tracking-wider text-slate-400">Tier 1 Fast Path</p>
          <h3 class="text-2xl font-bold text-emerald-400 font-mono mt-1">&lt; 200 ms</h3>
          <p class="text-[11px] text-slate-500 mt-0.5">Direct Replay with Cookies</p>
        </div>
        <div class="w-10 h-10 rounded-xl bg-emerald-500/10 border border-emerald-500/20 flex items-center justify-center text-emerald-400">
          <i class="fa-solid fa-bolt-lightning text-lg"></i>
        </div>
      </div>

      <div class="glass-panel rounded-2xl p-4 flex items-center justify-between">
        <div>
          <p class="text-[11px] font-mono uppercase tracking-wider text-slate-400">Learned Routes</p>
          <h3 id="statLearnedRoutes" class="text-2xl font-bold text-cyan-400 font-mono mt-1">0</h3>
          <p class="text-[11px] text-slate-500 mt-0.5">Cached in learned_routes.json</p>
        </div>
        <div class="w-10 h-10 rounded-xl bg-cyan-500/10 border border-cyan-500/20 flex items-center justify-center text-cyan-400">
          <i class="fa-solid fa-network-wired text-lg"></i>
        </div>
      </div>

      <div class="glass-panel rounded-2xl p-4 flex items-center justify-between">
        <div>
          <p class="text-[11px] font-mono uppercase tracking-wider text-slate-400">Saved Sessions</p>
          <h3 id="statSavedSessions" class="text-2xl font-bold text-purple-400 font-mono mt-1">1</h3>
          <p class="text-[11px] text-slate-500 mt-0.5">Retained permanently on disk</p>
        </div>
        <div class="w-10 h-10 rounded-xl bg-purple-500/10 border border-purple-500/20 flex items-center justify-center text-purple-400">
          <i class="fa-solid fa-address-card text-lg"></i>
        </div>
      </div>

      <div class="glass-panel rounded-2xl p-4 flex items-center justify-between">
        <div>
          <p class="text-[11px] font-mono uppercase tracking-wider text-slate-400">Media Downloads</p>
          <h3 id="statDownloadsCount" class="text-2xl font-bold text-amber-400 font-mono mt-1">1</h3>
          <p class="text-[11px] text-slate-500 mt-0.5">MP4 files stored in downloads/</p>
        </div>
        <div class="w-10 h-10 rounded-xl bg-amber-500/10 border border-amber-500/20 flex items-center justify-center text-amber-400">
          <i class="fa-solid fa-video text-lg"></i>
        </div>
      </div>
    </div>

    <!-- Navigation Tabs -->
    <div class="flex items-center space-x-2 border-b border-surface-border pb-2 overflow-x-auto custom-scrollbar">
      <button onclick="switchTab('playground')" id="tab-btn-playground" class="tab-btn px-4 py-2 rounded-xl text-xs font-semibold transition flex items-center gap-2 bg-purple-600/20 text-purple-400 border border-purple-500/30">
        <i class="fa-solid fa-play"></i>
        <span>3-Tier Playground</span>
      </button>
      <button onclick="switchTab('sessions')" id="tab-btn-sessions" class="tab-btn px-4 py-2 rounded-xl text-xs font-semibold transition flex items-center gap-2 text-slate-400 hover:text-white hover:bg-surface-card">
        <i class="fa-solid fa-users"></i>
        <span>Session Manager</span>
      </button>
      <button onclick="switchTab('learner')" id="tab-btn-learner" class="tab-btn px-4 py-2 rounded-xl text-xs font-semibold transition flex items-center gap-2 text-slate-400 hover:text-white hover:bg-surface-card">
        <i class="fa-solid fa-brain"></i>
        <span>Autonomous Platform Explorer</span>
      </button>
      <button onclick="switchTab('flow')" id="tab-btn-flow" class="tab-btn px-4 py-2 rounded-xl text-xs font-semibold transition flex items-center gap-2 text-slate-400 hover:text-white hover:bg-surface-card">
        <i class="fa-solid fa-wand-magic-sparkles"></i>
        <span>Google Flow Creative Studio</span>
      </button>
      <button onclick="switchTab('routes')" id="tab-btn-routes" class="tab-btn px-4 py-2 rounded-xl text-xs font-semibold transition flex items-center gap-2 text-slate-400 hover:text-white hover:bg-surface-card">
        <i class="fa-solid fa-code"></i>
        <span>Learned Routes &amp; Schemas</span>
      </button>
    </div>

    <!-- TAB 1: 3-TIER PLAYGROUND -->
    <div id="tab-playground" class="tab-content space-y-6">
      <div class="grid grid-cols-1 lg:grid-cols-12 gap-6">
        
        <!-- Request Controls -->
        <div class="lg:col-span-5 space-y-4">
          <div class="glass-panel rounded-2xl p-5 space-y-4">
            <h2 class="text-sm font-bold tracking-tight text-slate-200 flex items-center gap-2">
              <i class="fa-solid fa-terminal text-purple-400"></i>
              <span>Universal Request Runner</span>
            </h2>

            <div class="space-y-3">
              <div>
                <label class="text-[11px] font-mono uppercase text-slate-400 tracking-wider">Target Endpoint URL</label>
                <input id="targetUrl" type="url" value="https://flow.google.com/project/5730a6a6-a00a-4a95-8f22-20942efd1413" class="mt-1 w-full glass-input rounded-xl px-3.5 py-2.5 text-xs text-slate-100 font-mono placeholder-slate-600">
              </div>

              <div class="grid grid-cols-2 gap-3">
                <div>
                  <label class="text-[11px] font-mono uppercase text-slate-400 tracking-wider">HTTP Method</label>
                  <select id="reqMethod" class="mt-1 w-full glass-input rounded-xl px-3 py-2 text-xs text-slate-100 font-mono">
                    <option value="GET">GET</option>
                    <option value="POST">POST</option>
                  </select>
                </div>
                <div>
                  <label class="text-[11px] font-mono uppercase text-slate-400 tracking-wider">Force Tier</label>
                  <select id="reqTier" class="mt-1 w-full glass-input rounded-xl px-3 py-2 text-xs text-slate-100 font-mono">
                    <option value="">Auto (Tier 1 &rarr; 2 &rarr; 3)</option>
                    <option value="1">Tier 1: Fast Path (&lt;200ms)</option>
                    <option value="2">Tier 2: CDP Sniffer</option>
                    <option value="3">Tier 3: DOM Fallback</option>
                  </select>
                </div>
              </div>

              <div class="pt-2">
                <button id="sendBtn" onclick="executeUniversalRequest()" class="w-full bg-gradient-to-r from-purple-600 via-indigo-600 to-cyan-500 hover:from-purple-500 hover:to-cyan-400 text-white font-semibold py-2.5 px-4 rounded-xl text-xs transition duration-200 flex items-center justify-center gap-2 shadow-lg shadow-purple-600/20">
                  <i class="fa-solid fa-paper-plane"></i>
                  <span>Execute 3-Tier Request</span>
                </button>
              </div>
            </div>
          </div>

          <!-- Quick Actions Panel -->
          <div class="glass-panel rounded-2xl p-5 space-y-3">
            <h3 class="text-xs font-bold tracking-tight text-slate-300 uppercase font-mono">Quick Preset Tests</h3>
            <div class="flex flex-col gap-2">
              <button onclick="setTestPreset('flow')" class="text-left p-2.5 rounded-xl bg-surface-card hover:bg-surface-hover border border-surface-border text-xs transition flex items-center justify-between">
                <div>
                  <span class="font-semibold text-purple-400">Google Flow Workspace</span>
                  <p class="text-[10px] text-slate-400 font-mono">flow.google.com/project/5730a6a6...</p>
                </div>
                <span class="text-[10px] bg-purple-500/10 text-purple-400 border border-purple-500/20 px-2 py-0.5 rounded font-mono">Auth Auto</span>
              </button>
              <button onclick="setTestPreset('json')" class="text-left p-2.5 rounded-xl bg-surface-card hover:bg-surface-hover border border-surface-border text-xs transition flex items-center justify-between">
                <div>
                  <span class="font-semibold text-emerald-400">Public JSON Fast Path</span>
                  <p class="text-[10px] text-slate-400 font-mono">jsonplaceholder.typicode.com/todos/1</p>
                </div>
                <span class="text-[10px] bg-emerald-500/10 text-emerald-400 border border-emerald-500/20 px-2 py-0.5 rounded font-mono">&lt; 100ms</span>
              </button>
            </div>
          </div>
        </div>

        <!-- Response Viewer -->
        <div class="lg:col-span-7">
          <div class="glass-panel rounded-2xl p-5 flex flex-col h-full min-h-[460px]">
            <div class="flex items-center justify-between border-b border-surface-border pb-3 mb-3">
              <div class="flex items-center space-x-2">
                <span class="text-xs font-bold text-slate-200 font-mono">Response Payload</span>
                <span id="resTierBadge" class="hidden text-[10px] font-mono uppercase px-2 py-0.5 rounded-full"></span>
                <span id="resLatencyBadge" class="hidden text-[10px] font-mono px-2 py-0.5 rounded-full bg-slate-800 text-slate-300 border border-slate-700">
                  <span id="resLatencyVal">0</span> ms
                </span>
                <span id="resTokensBadge" class="hidden text-[10px] font-mono px-2 py-0.5 rounded-full bg-cyan-500/10 text-cyan-400 border border-cyan-500/20">
                  <span id="resTokensVal">0</span> tokens
                </span>
              </div>
              <button onclick="copyResponsePayload()" class="text-xs text-slate-400 hover:text-white transition">
                <i class="fa-regular fa-copy"></i>
              </button>
            </div>

            <div id="resLoading" class="hidden flex-1 flex flex-col items-center justify-center py-12 text-center space-y-3">
              <div class="w-10 h-10 border-2 border-purple-500/30 border-t-purple-500 rounded-full animate-spin"></div>
              <p class="text-xs font-mono text-purple-400 animate-pulse">Routing through 3-tier hybrid pipeline...</p>
            </div>

            <div id="resEmpty" class="flex-1 flex flex-col items-center justify-center py-12 text-center text-slate-600 space-y-2">
              <i class="fa-solid fa-code text-3xl opacity-30"></i>
              <p class="text-xs font-mono">No request executed yet. Click 'Execute 3-Tier Request'.</p>
            </div>

            <pre id="resCodeBlock" class="hidden flex-1 overflow-auto custom-scrollbar p-3 rounded-xl bg-obsidian/90 border border-surface-border text-xs font-mono text-slate-300 whitespace-pre-wrap max-h-[480px]"><code></code></pre>
          </div>
        </div>

      </div>
    </div>

    <!-- TAB 2: SESSION MANAGER (Add, Remove, Retain Across Machine Restarts) -->
    <div id="tab-sessions" class="tab-content hidden space-y-6">
      <div class="glass-panel rounded-2xl p-6 space-y-6">
        
        <div class="flex flex-col md:flex-row md:items-center justify-between gap-4 border-b border-surface-border pb-4">
          <div>
            <h2 class="text-base font-bold text-white flex items-center gap-2">
              <i class="fa-solid fa-address-card text-purple-400"></i>
              <span>Persistent Multi-Session Profile Manager</span>
            </h2>
            <p class="text-xs text-slate-400 mt-1">
              All browser authentication sessions are permanently stored in <code class="text-purple-300 font-mono">sessions.json</code>. Login credentials and storage states survive server restarts and machine reboots.
            </p>
          </div>
          <div class="flex items-center gap-2">
            <button onclick="openAddSessionModal()" class="text-xs bg-purple-600 hover:bg-purple-500 text-white font-medium px-3.5 py-2 rounded-xl transition flex items-center gap-2 shadow-lg shadow-purple-600/20">
              <i class="fa-solid fa-plus"></i>
              <span>Add Session</span>
            </button>
            <button onclick="loadSessions()" class="text-xs bg-surface-card hover:bg-surface-hover border border-surface-border text-slate-300 px-3 py-2 rounded-xl transition">
              <i class="fa-solid fa-rotate"></i>
            </button>
          </div>
        </div>

        <!-- Saved Sessions Table / Cards -->
        <div id="sessionsListContainer" class="grid grid-cols-1 md:grid-cols-2 lg:grid-cols-3 gap-4">
          <!-- Loaded dynamically -->
        </div>

      </div>
    </div>

    <!-- TAB 3: AUTONOMOUS PLATFORM EXPLORER (Learn Any Website with Live Progress) -->
    <div id="tab-learner" class="tab-content hidden space-y-6">
      <div class="glass-panel rounded-2xl p-6 space-y-6">
        
        <div class="border-b border-surface-border pb-4">
          <h2 class="text-base font-bold text-white flex items-center gap-2">
            <i class="fa-solid fa-brain text-cyan-400"></i>
            <span>Universal Autonomous Platform Skill Engine</span>
          </h2>
          <p class="text-xs text-slate-400 mt-1">
            Give the AI any website URL. It explores navigation, discovers buttons and prompt boxes, sniffs background APIs, and compiles a comprehensive operational Skill profile so any model knows exactly how to automate it.
          </p>
        </div>

        <!-- Input & Trigger -->
        <div class="grid grid-cols-1 md:grid-cols-12 gap-3">
          <div class="md:col-span-9">
            <input id="learnerTargetUrl" type="url" value="https://flow.google.com/" placeholder="Enter any platform URL (e.g. https://flow.google.com/)" class="w-full glass-input rounded-xl px-4 py-3 text-xs text-slate-100 font-mono placeholder-slate-600">
          </div>
          <div class="md:col-span-3">
            <button id="startLearnBtn" onclick="startPlatformLearning()" class="w-full bg-gradient-to-r from-cyan-600 to-purple-600 hover:from-cyan-500 hover:to-purple-500 text-white font-semibold py-3 px-4 rounded-xl text-xs transition duration-200 flex items-center justify-center gap-2 shadow-lg shadow-cyan-600/20">
              <i class="fa-solid fa-magnifying-glass-chart"></i>
              <span>Explore &amp; Train Agent</span>
            </button>
          </div>
        </div>

        <!-- Real-Time Learning Monitor (Phase Progress + 'Getting Ready on Dashboard...') -->
        <div id="learnerProgressBox" class="p-5 rounded-2xl bg-surface-card border border-surface-border space-y-4">
          <div class="flex items-center justify-between">
            <div class="flex items-center space-x-3">
              <div id="learnerStatusDot" class="w-3 h-3 rounded-full bg-emerald-400"></div>
              <span id="learnerStatusLabel" class="text-xs font-mono font-semibold uppercase tracking-wider text-slate-200">Engine Ready</span>
            </div>
            <span id="learnerPercent" class="text-xs font-mono font-bold text-cyan-400">100%</span>
          </div>

          <!-- Progress Bar -->
          <div class="w-full bg-obsidian rounded-full h-2.5 overflow-hidden border border-surface-border">
            <div id="learnerProgressBar" class="bg-gradient-to-r from-purple-500 via-indigo-500 to-cyan-400 h-2.5 rounded-full transition-all duration-500" style="width: 100%"></div>
          </div>

          <!-- Live Dynamic Message -->
          <div id="learnerMessageBox" class="p-4 rounded-xl bg-obsidian/70 border border-surface-border flex items-start gap-3">
            <i id="learnerMessageIcon" class="fa-solid fa-circle-check text-emerald-400 mt-0.5"></i>
            <div>
              <p id="learnerMessageText" class="text-xs text-slate-200 font-mono leading-relaxed">
                Platform Skill for Google Flow is compiled and ready to automate.
              </p>
              <p id="learnerSubText" class="text-[11px] text-slate-500 mt-1">
                20 sub-routes, 30 controls, and first-party batch execute APIs mapped.
              </p>
            </div>
          </div>

          <!-- Skill Output Preview Button -->
          <div id="learnerOutputActions" class="flex items-center gap-3 pt-2">
            <button onclick="viewPlatformSkill()" class="text-xs bg-surface-hover hover:bg-surface-border text-slate-200 font-medium px-4 py-2 rounded-xl transition flex items-center gap-2">
              <i class="fa-regular fa-file-lines text-cyan-400"></i>
              <span>View Compiled Skill Guide (GOOGLE_FLOW_SKILL.md)</span>
            </button>
          </div>
        </div>

      </div>
    </div>

    <!-- TAB 4: GOOGLE FLOW CREATIVE STUDIO & BATCH AUTOMATION -->
    <div id="tab-flow" class="tab-content hidden space-y-6">
      <div class="grid grid-cols-1 lg:grid-cols-12 gap-6">

        <!-- Controls Column -->
        <div class="lg:col-span-6 space-y-5">
          <div class="glass-panel rounded-2xl p-6 space-y-5">
            <div class="flex items-center justify-between border-b border-surface-border pb-3">
              <div>
                <h2 class="text-sm font-bold text-white flex items-center gap-2">
                  <i class="fa-solid fa-wand-magic-sparkles text-amber-400"></i>
                  <span>Google Flow Creative Studio</span>
                </h2>
                <p class="text-xs text-slate-400 mt-0.5">Veo (8s) &bull; Omni Flash (10s) &bull; Agent Mode &bull; @ References</p>
              </div>
              <span class="text-[10px] font-mono px-2 py-0.5 rounded-full bg-amber-500/10 text-amber-400 border border-amber-500/20 font-semibold">Pre-Auth Connected</span>
            </div>

            <!-- Model & Duration Selectors -->
            <div class="grid grid-cols-2 gap-3">
              <div>
                <label class="text-[11px] font-mono uppercase text-slate-400 tracking-wider">AI Video Model</label>
                <select id="flowModelSelect" class="mt-1 w-full glass-input rounded-xl px-3 py-2 text-xs text-slate-100 font-mono">
                  <option value="veo">Google Veo (8s max, 4K Photorealism)</option>
                  <option value="omni_flash">Omni 1.1 Flash (10s max, Rapid Dynamic)</option>
                  <option value="imagen_3">Imagen 3 (Visual Asset Reference)</option>
                </select>
              </div>
              <div>
                <label class="text-[11px] font-mono uppercase text-slate-400 tracking-wider">Creation Mode</label>
                <select id="flowModeSelect" class="mt-1 w-full glass-input rounded-xl px-3 py-2 text-xs text-slate-100 font-mono">
                  <option value="agent">Agent Mode (Autonomous Director)</option>
                  <option value="direct">Direct Mode (Strict Execution)</option>
                </select>
              </div>
            </div>

            <!-- Video Duration Option -->
            <div>
              <label class="text-[11px] font-mono uppercase text-slate-400 tracking-wider">Video Format &amp; Duration</label>
              <select id="flowDurationSelect" class="mt-1 w-full glass-input rounded-xl px-3 py-2 text-xs text-slate-100 font-mono">
                <option value="30s_ad">30-Second Commercial Ad (Auto 4-Scene Breakdown &amp; Assembly)</option>
                <option value="single">Single Scene Shot (8s / 10s based on model)</option>
              </select>
            </div>

            <!-- Reference & Tag Helper Chips -->
            <div>
              <label class="text-[11px] font-mono uppercase text-slate-400 tracking-wider">Quick Tag &amp; Ingredient Injectors (Click to add)</label>
              <div class="flex flex-wrap gap-1.5 mt-1.5">
                <button type="button" onclick="injectTag('@Character:LeadDeveloper ')" class="text-[10px] font-mono px-2.5 py-1 rounded-lg bg-surface-card hover:bg-surface-hover border border-surface-border text-purple-300 transition">@Character</button>
                <button type="button" onclick="injectTag('@Ingredient:CyberpunkNeon ')" class="text-[10px] font-mono px-2.5 py-1 rounded-lg bg-surface-card hover:bg-surface-hover border border-surface-border text-cyan-300 transition">@Ingredient</button>
                <button type="button" onclick="injectTag('Cinematic 35mm lens, moody lighting, shallow depth of field, 4K ')" class="text-[10px] font-mono px-2.5 py-1 rounded-lg bg-surface-card hover:bg-surface-hover border border-surface-border text-emerald-300 transition">35mm Lens</button>
                <button type="button" onclick="injectTag('Dynamic FPV drone push-in, volumetric light rays ')" class="text-[10px] font-mono px-2.5 py-1 rounded-lg bg-surface-card hover:bg-surface-hover border border-surface-border text-amber-300 transition">FPV Push</button>
                <button type="button" onclick="injectTag('Dramatic slow-motion 60fps particle acceleration ')" class="text-[10px] font-mono px-2.5 py-1 rounded-lg bg-surface-card hover:bg-surface-hover border border-surface-border text-rose-300 transition">Slow Motion</button>
              </div>
            </div>

            <!-- Prompt Box -->
            <div>
              <label class="text-[11px] font-mono uppercase text-slate-400 tracking-wider">Video Concept / Prompt</label>
              <textarea id="flowPromptInput" rows="3" class="mt-1 w-full glass-input rounded-xl p-3 text-xs text-slate-100 font-mono placeholder-slate-600" placeholder="Describe the ad or video concept... e.g. A hyper-fast AI terminal solving impossible engineering problems in milliseconds with glowing cyan data streams.">A futuristic high-tech developer workstation running Universal-Web-MCP at light speed. Glowing cyan data streams, sleek holographic UI, cinematic lighting, 4K resolution.</textarea>
            </div>

            <!-- Action Button -->
            <button id="flowGenBtn" onclick="startFlowGeneration()" class="w-full bg-gradient-to-r from-amber-600 via-orange-600 to-rose-600 hover:from-amber-500 hover:to-rose-500 text-white font-semibold py-3 px-4 rounded-xl text-xs transition duration-200 flex items-center justify-center gap-2 shadow-lg shadow-amber-600/20">
              <i class="fa-solid fa-clapperboard"></i>
              <span>Generate Video &amp; Auto-Download to Local Disk</span>
            </button>
          </div>
        </div>

        <!-- Downloaded Media Vault -->
        <div class="lg:col-span-6 space-y-4">
          <div class="glass-panel rounded-2xl p-6 flex flex-col h-full min-h-[460px]">
            <div class="flex items-center justify-between border-b border-surface-border pb-3 mb-4">
              <div class="flex items-center space-x-2">
                <i class="fa-solid fa-folder-closed text-amber-400"></i>
                <h3 class="text-sm font-bold text-white">Local Download Vault</h3>
              </div>
              <button onclick="loadDownloads()" class="text-xs text-slate-400 hover:text-white transition">
                <i class="fa-solid fa-rotate"></i>
              </button>
            </div>

            <div id="downloadsListContainer" class="space-y-3 flex-1 overflow-auto custom-scrollbar max-h-[420px]">
              <!-- Loaded dynamically -->
            </div>
          </div>
        </div>

      </div>
    </div>

    <!-- TAB 5: LEARNED ROUTES & SCHEMAS -->
    <div id="tab-routes" class="tab-content hidden space-y-6">
      <div class="glass-panel rounded-2xl p-6 space-y-4">
        <div class="flex items-center justify-between border-b border-surface-border pb-4">
          <div>
            <h2 class="text-sm font-bold text-white flex items-center gap-2">
              <i class="fa-solid fa-code text-cyan-400"></i>
              <span>Discovered Routes &amp; Reverse-Engineered Schemas</span>
            </h2>
            <p class="text-xs text-slate-400 mt-0.5">Persisted to learned_routes.json for instant sub-200ms Fast Path replay.</p>
          </div>
          <div class="flex items-center gap-2">
            <button onclick="clearLearnedRoutes()" class="text-xs bg-rose-500/10 hover:bg-rose-500/20 border border-rose-500/30 text-rose-400 px-3 py-1.5 rounded-xl transition">
              <i class="fa-regular fa-trash-can mr-1"></i> Clear Cache
            </button>
            <button onclick="loadRoutes()" class="text-xs bg-surface-card hover:bg-surface-hover border border-surface-border text-slate-300 px-3 py-1.5 rounded-xl transition">
              <i class="fa-solid fa-rotate"></i>
            </button>
          </div>
        </div>

        <div class="overflow-x-auto custom-scrollbar">
          <table class="w-full text-left text-xs font-mono">
            <thead>
              <tr class="border-b border-surface-border text-slate-400">
                <th class="py-2.5 px-3">Method</th>
                <th class="py-2.5 px-3">Endpoint URL</th>
                <th class="py-2.5 px-3">Domain</th>
                <th class="py-2.5 px-3">Schema Key</th>
                <th class="py-2.5 px-3 text-right">Action</th>
              </tr>
            </thead>
            <tbody id="routesTableBody" class="divide-y divide-surface-border text-slate-300">
              <!-- Dynamically populated -->
            </tbody>
          </table>
        </div>
      </div>
    </div>

  </main>

  <!-- Add Session Modal -->
  <div id="addSessionModal" class="hidden fixed inset-0 z-50 bg-black/80 backdrop-blur-sm flex items-center justify-center p-4">
    <div class="glass-panel rounded-2xl max-w-lg w-full p-6 space-y-4 border border-surface-border">
      <div class="flex items-center justify-between border-b border-surface-border pb-3">
        <h3 class="text-sm font-bold text-white flex items-center gap-2">
          <i class="fa-solid fa-user-plus text-purple-400"></i>
          <span>Add New Session Profile</span>
        </h3>
        <button onclick="closeAddSessionModal()" class="text-slate-400 hover:text-white transition">
          <i class="fa-solid fa-xmark"></i>
        </button>
      </div>

      <div class="space-y-3">
        <div>
          <label class="text-[11px] font-mono uppercase text-slate-400">Session Name</label>
          <input id="modalSessName" type="text" placeholder="e.g. Work Google Account" class="mt-1 w-full glass-input rounded-xl px-3 py-2 text-xs text-slate-100 font-mono">
        </div>
        <div>
          <label class="text-[11px] font-mono uppercase text-slate-400">Account Email</label>
          <input id="modalSessEmail" type="email" placeholder="e.g. arq5020@gmail.com" class="mt-1 w-full glass-input rounded-xl px-3 py-2 text-xs text-slate-100 font-mono">
        </div>
        <div>
          <label class="text-[11px] font-mono uppercase text-slate-400">Target Domain</label>
          <input id="modalSessDomain" type="text" value="flow.google.com" class="mt-1 w-full glass-input rounded-xl px-3 py-2 text-xs text-slate-100 font-mono">
        </div>
        <div>
          <label class="text-[11px] font-mono uppercase text-slate-400">Raw Cookies or JSON (Optional)</label>
          <textarea id="modalSessCookies" rows="3" placeholder='Paste cookie string (SID=...; SSID=...) or JSON dict' class="mt-1 w-full glass-input rounded-xl p-3 text-xs text-slate-100 font-mono placeholder-slate-600"></textarea>
        </div>
      </div>

      <div class="flex items-center justify-end gap-2 pt-2 border-t border-surface-border">
        <button onclick="closeAddSessionModal()" class="text-xs bg-surface-card hover:bg-surface-hover text-slate-300 px-4 py-2 rounded-xl transition">Cancel</button>
        <button onclick="submitAddSession()" class="text-xs bg-purple-600 hover:bg-purple-500 text-white font-medium px-4 py-2 rounded-xl transition shadow-lg shadow-purple-600/20">Save Profile</button>
      </div>
    </div>
  </div>

  <!-- View Skill Modal -->
  <div id="skillModal" class="hidden fixed inset-0 z-50 bg-black/80 backdrop-blur-sm flex items-center justify-center p-4">
    <div class="glass-panel rounded-2xl max-w-3xl w-full p-6 space-y-4 border border-surface-border max-h-[85vh] flex flex-col">
      <div class="flex items-center justify-between border-b border-surface-border pb-3">
        <h3 class="text-sm font-bold text-white flex items-center gap-2">
          <i class="fa-solid fa-file-lines text-cyan-400"></i>
          <span id="skillModalTitle">Platform Skill Profile</span>
        </h3>
        <button onclick="closeSkillModal()" class="text-slate-400 hover:text-white transition">
          <i class="fa-solid fa-xmark"></i>
        </button>
      </div>
      <div class="flex-1 overflow-auto custom-scrollbar p-3 rounded-xl bg-obsidian border border-surface-border">
        <pre id="skillModalContent" class="text-xs font-mono text-slate-300 whitespace-pre-wrap"></pre>
      </div>
    </div>
  </div>

  <!-- Scripts -->
  <script>
    let activeTab = 'playground';

    function switchTab(tabId) {
      activeTab = tabId;
      document.querySelectorAll('.tab-content').forEach(el => el.classList.add('hidden'));
      document.querySelectorAll('.tab-btn').forEach(btn => {
        btn.classList.remove('bg-purple-600/20', 'text-purple-400', 'border-purple-500/30');
        btn.classList.add('text-slate-400');
      });

      const target = document.getElementById('tab-' + tabId);
      const btn = document.getElementById('tab-btn-' + tabId);
      if (target) target.classList.remove('hidden');
      if (btn) {
        btn.classList.remove('text-slate-400');
        btn.classList.add('bg-purple-600/20', 'text-purple-400', 'border', 'border-purple-500/30');
      }

      if (tabId === 'sessions') loadSessions();
      if (tabId === 'routes') loadRoutes();
      if (tabId === 'flow') loadDownloads();
      if (tabId === 'learner') pollLearnerStatus();
    }

    function setTestPreset(type) {
      if (type === 'flow') {
        document.getElementById('targetUrl').value = 'https://flow.google.com/project/5730a6a6-a00a-4a95-8f22-20942efd1413';
        document.getElementById('reqMethod').value = 'GET';
        document.getElementById('reqTier').value = '';
      } else if (type === 'json') {
        document.getElementById('targetUrl').value = 'https://jsonplaceholder.typicode.com/todos/1';
        document.getElementById('reqMethod').value = 'GET';
        document.getElementById('reqTier').value = '1';
      }
    }

    function injectTag(tag) {
      const textarea = document.getElementById('flowPromptInput');
      textarea.value = textarea.value + ' ' + tag;
      textarea.focus();
    }

    // --- Universal Request Runner ---
    async function executeUniversalRequest() {
      const url = document.getElementById('targetUrl').value.trim();
      const method = document.getElementById('reqMethod').value;
      const tierVal = document.getElementById('reqTier').value;
      const force_tier = tierVal ? parseInt(tierVal) : null;

      if (!url) return alert('Please enter a target URL');

      const btn = document.getElementById('sendBtn');
      const loading = document.getElementById('resLoading');
      const empty = document.getElementById('resEmpty');
      const codeBlock = document.getElementById('resCodeBlock');
      const tierBadge = document.getElementById('resTierBadge');
      const latencyBadge = document.getElementById('resLatencyBadge');
      const latencyVal = document.getElementById('resLatencyVal');
      const tokensBadge = document.getElementById('resTokensBadge');
      const tokensVal = document.getElementById('resTokensVal');

      btn.disabled = true;
      empty.classList.add('hidden');
      codeBlock.classList.add('hidden');
      loading.classList.remove('hidden');

      try {
        const res = await fetch('/api/request', {
          method: 'POST',
          headers: { 'Content-Type': 'application/json' },
          body: JSON.stringify({ url, method, force_tier })
        });
        const data = await res.json();

        codeBlock.querySelector('code').innerText = JSON.stringify(data, null, 2);
        codeBlock.classList.remove('hidden');

        // Update badges
        tierBadge.classList.remove('hidden');
        tierBadge.innerText = data.tier || 'Unknown Tier';
        if ((data.tier || '').includes('Tier 1')) {
          tierBadge.className = 'text-[10px] font-mono uppercase px-2 py-0.5 rounded-full bg-emerald-500/10 text-emerald-400 border border-emerald-500/20';
        } else if ((data.tier || '').includes('Tier 2')) {
          tierBadge.className = 'text-[10px] font-mono uppercase px-2 py-0.5 rounded-full bg-purple-500/10 text-purple-400 border border-purple-500/20';
        } else {
          tierBadge.className = 'text-[10px] font-mono uppercase px-2 py-0.5 rounded-full bg-amber-500/10 text-amber-400 border border-amber-500/20';
        }

        latencyBadge.classList.remove('hidden');
        latencyVal.innerText = data.latency_ms || 0;

        if (data.token_count) {
          tokensBadge.classList.remove('hidden');
          tokensVal.innerText = data.token_count;
        } else {
          tokensBadge.classList.add('hidden');
        }

        loadRoutes();
      } catch (err) {
        alert('Execution failed: ' + err);
      } finally {
        btn.disabled = false;
        loading.classList.add('hidden');
      }
    }

    function copyResponsePayload() {
      const code = document.getElementById('resCodeBlock').querySelector('code').innerText;
      if (!code) return;
      navigator.clipboard.writeText(code);
      alert('Copied response payload to clipboard!');
    }

    // --- Session Manager ---
    async function loadSessions() {
      try {
        const res = await fetch('/api/sessions');
        const data = await res.json();
        const container = document.getElementById('sessionsListContainer');
        container.innerHTML = '';

        const sessions = data.sessions || [];
        document.getElementById('statSavedSessions').innerText = sessions.length;

        let activeFound = false;

        sessions.forEach(s => {
          if (s.is_active) {
            activeFound = true;
            document.getElementById('activeSessionName').innerText = s.email || s.name;
          }

          const card = document.createElement('div');
          card.className = `p-5 rounded-2xl border transition ${s.is_active ? 'bg-purple-950/20 border-purple-500/40 glow-violet' : 'bg-surface-card border-surface-border'}`;
          card.innerHTML = `
            <div class="flex items-start justify-between">
              <div>
                <div class="flex items-center gap-2">
                  <h4 class="text-sm font-bold text-white">${s.name || 'Unnamed Session'}</h4>
                  ${s.is_active ? '<span class="text-[9px] font-mono bg-emerald-500/20 text-emerald-400 border border-emerald-500/30 px-2 py-0.5 rounded-full uppercase">ACTIVE</span>' : ''}
                </div>
                <p class="text-xs text-slate-400 font-mono mt-0.5">${s.email || 'No email'}</p>
                <p class="text-[10px] text-slate-500 font-mono mt-1">Domain: ${s.domain || 'All'}</p>
              </div>
              <div class="text-right">
                <span class="text-xs font-mono font-bold text-cyan-400">${s.cookie_count || 0}</span>
                <p class="text-[9px] uppercase tracking-wider text-slate-500 font-mono">Cookies</p>
              </div>
            </div>

            <div class="mt-4 pt-3 border-t border-surface-border flex items-center justify-between text-xs">
              <span class="text-[10px] text-slate-500 font-mono">Retained on disk</span>
              <div class="flex items-center gap-2">
                ${!s.is_active ? `<button onclick="selectSession('${s.id}')" class="text-[11px] bg-purple-600/20 hover:bg-purple-600/40 text-purple-300 border border-purple-500/30 px-2.5 py-1 rounded-lg transition font-mono">Set Active</button>` : ''}
                <button onclick="removeSession('${s.id}')" class="text-[11px] text-rose-400 hover:text-rose-300 px-2 py-1 transition font-mono"><i class="fa-regular fa-trash-can"></i></button>
              </div>
            </div>
          `;
          container.appendChild(card);
        });

        if (!activeFound) {
          document.getElementById('activeSessionName').innerText = 'None';
        }
      } catch (e) {
        console.error('Failed to load sessions:', e);
      }
    }

    async function selectSession(sessionId) {
      try {
        await fetch(`/api/sessions/${sessionId}/select`, { method: 'POST' });
        loadSessions();
      } catch (e) {
        alert('Failed to switch session: ' + e);
      }
    }

    async function removeSession(sessionId) {
      if (!confirm('Are you sure you want to remove this saved session profile?')) return;
      try {
        await fetch(`/api/sessions/${sessionId}`, { method: 'DELETE' });
        loadSessions();
      } catch (e) {
        alert('Failed to remove session: ' + e);
      }
    }

    function openAddSessionModal() {
      document.getElementById('addSessionModal').classList.remove('hidden');
    }

    function closeAddSessionModal() {
      document.getElementById('addSessionModal').classList.add('hidden');
    }

    async function submitAddSession() {
      const name = document.getElementById('modalSessName').value.trim();
      const email = document.getElementById('modalSessEmail').value.trim();
      const domain = document.getElementById('modalSessDomain').value.trim();
      const rawCookies = document.getElementById('modalSessCookies').value.trim();

      if (!name) return alert('Please enter a session name');

      try {
        const res = await fetch('/api/sessions/add', {
          method: 'POST',
          headers: { 'Content-Type': 'application/json' },
          body: JSON.stringify({ name, email, domain, raw_cookies: rawCookies })
        });
        const data = await res.json();
        if (data.status === 'success') {
          closeAddSessionModal();
          loadSessions();
        } else {
          alert('Error adding session: ' + (data.message || 'Unknown error'));
        }
      } catch (e) {
        alert('Error: ' + e);
      }
    }

    // --- 1-Click Interactive Google Login ---
    async function startInteractiveAuth() {
      const targetUrl = prompt('Enter the login URL to open in Chrome:', 'https://flow.google.com/');
      if (!targetUrl) return;

      alert('Opening Chrome window on your screen. Please complete your Google log in inside the browser window. The session will be saved automatically once you reach the project dashboard.');

      try {
        const res = await fetch('/api/authenticate?target_url=' + encodeURIComponent(targetUrl), { method: 'POST' });
        const data = await res.json();
        if (data.status === 'success') {
          alert('Authentication Successful! ' + data.message);
          loadSessions();
        } else {
          alert('Notice: ' + (data.message || JSON.stringify(data)));
        }
      } catch (e) {
        alert('Authentication error: ' + e);
      }
    }

    // --- Autonomous Platform Explorer ---
    let learnerPollInterval = null;

    async function startPlatformLearning() {
      const url = document.getElementById('learnerTargetUrl').value.trim();
      if (!url) return alert('Please enter a valid website URL to explore.');

      const btn = document.getElementById('startLearnBtn');
      btn.disabled = true;

      try {
        const res = await fetch('/api/learn-platform', {
          method: 'POST',
          headers: { 'Content-Type': 'application/json' },
          body: JSON.stringify({ url })
        });
        const data = await res.json();
        
        // Start polling status
        pollLearnerStatus();
        if (learnerPollInterval) clearInterval(learnerPollInterval);
        learnerPollInterval = setInterval(pollLearnerStatus, 1500);

      } catch (e) {
        alert('Failed to start exploration: ' + e);
        btn.disabled = false;
      }
    }

    async function pollLearnerStatus() {
      try {
        const res = await fetch('/api/learn-platform/status');
        const status = await res.json();

        const dot = document.getElementById('learnerStatusDot');
        const label = document.getElementById('learnerStatusLabel');
        const percent = document.getElementById('learnerPercent');
        const bar = document.getElementById('learnerProgressBar');
        const msgText = document.getElementById('learnerMessageText');
        const subText = document.getElementById('learnerSubText');
        const icon = document.getElementById('learnerMessageIcon');
        const btn = document.getElementById('startLearnBtn');

        percent.innerText = (status.progress || 0) + '%';
        bar.style.width = (status.progress || 0) + '%';

        if (status.state === 'READY') {
          dot.className = 'w-3 h-3 rounded-full bg-emerald-400';
          label.innerText = 'Platform Ready';
          msgText.innerText = status.status_text || 'BOOM! Platform Skill is fully compiled and ready to automate!';
          icon.className = 'fa-solid fa-circle-check text-emerald-400 mt-0.5';
          if (btn) btn.disabled = false;
          if (learnerPollInterval) {
            clearInterval(learnerPollInterval);
            learnerPollInterval = null;
          }
        } else if (status.state === 'ERROR') {
          dot.className = 'w-3 h-3 rounded-full bg-rose-400';
          label.innerText = 'Exploration Error';
          msgText.innerText = status.status_text || 'An error occurred during platform exploration.';
          icon.className = 'fa-solid fa-triangle-exclamation text-rose-400 mt-0.5';
          if (btn) btn.disabled = false;
          if (learnerPollInterval) clearInterval(learnerPollInterval);
        } else {
          dot.className = 'w-3 h-3 rounded-full bg-amber-400 animate-ping';
          label.innerText = 'Learning Platform...';
          msgText.innerText = 'getting ready on dashboard until the ai agent is fully done with learning: ' + (status.status_text || '');
          subText.innerText = `Phase: ${status.state} (${status.progress}%)`;
          icon.className = 'fa-solid fa-spinner text-amber-400 animate-spin mt-0.5';
        }
      } catch (e) {
        console.error('Error polling learner status:', e);
      }
    }

    async function viewPlatformSkill() {
      try {
        const res = await fetch('/api/learn-platform/skill');
        const data = await res.json();
        document.getElementById('skillModalTitle').innerText = data.filename || 'Platform Skill Guide';
        document.getElementById('skillModalContent').innerText = data.content || 'No skill content generated yet.';
        document.getElementById('skillModal').classList.remove('hidden');
      } catch (e) {
        alert('Failed to load skill guide: ' + e);
      }
    }

    function closeSkillModal() {
      document.getElementById('skillModal').classList.add('hidden');
    }

    // --- Google Flow Studio ---
    async function startFlowGeneration() {
      const prompt = document.getElementById('flowPromptInput').value.trim();
      const model = document.getElementById('flowModelSelect').value;
      const mode = document.getElementById('flowModeSelect').value;
      const duration = document.getElementById('flowDurationSelect').value;

      if (!prompt) return alert('Please enter a prompt concept.');

      const btn = document.getElementById('flowGenBtn');
      btn.disabled = true;
      btn.innerHTML = '<i class="fa-solid fa-spinner animate-spin"></i> Submitting to Google Flow & Polling Render...';

      try {
        const res = await fetch('/api/flow/generate', {
          method: 'POST',
          headers: { 'Content-Type': 'application/json' },
          body: JSON.stringify({ prompt, model, mode, duration })
        });
        const data = await res.json();
        alert(data.message || 'Generation initiated!');
        loadDownloads();
      } catch (e) {
        alert('Flow generation error: ' + e);
      } finally {
        btn.disabled = false;
        btn.innerHTML = '<i class="fa-solid fa-clapperboard"></i> <span>Generate Video & Auto-Download to Local Disk</span>';
      }
    }

    async function loadDownloads() {
      try {
        const res = await fetch('/api/flow/downloads');
        const files = await res.json();
        const container = document.getElementById('downloadsListContainer');
        container.innerHTML = '';

        document.getElementById('statDownloadsCount').innerText = files.length;

        if (files.length === 0) {
          container.innerHTML = '<p class="text-xs text-slate-500 font-mono text-center py-8">No downloaded videos yet. Run a generation to download MP4 files.</p>';
          return;
        }

        files.forEach(f => {
          const item = document.createElement('div');
          item.className = 'p-3.5 rounded-xl bg-surface-card border border-surface-border flex items-center justify-between';
          item.innerHTML = `
            <div class="flex items-center space-x-3">
              <div class="w-9 h-9 rounded-lg bg-amber-500/10 border border-amber-500/20 flex items-center justify-center text-amber-400">
                <i class="fa-solid fa-file-video"></i>
              </div>
              <div>
                <p class="text-xs font-semibold text-slate-200 font-mono truncate max-w-[240px]">${f.name}</p>
                <p class="text-[10px] text-slate-500 font-mono">${f.size_mb} MB &bull; ${f.modified}</p>
              </div>
            </div>
            <div class="flex items-center gap-2">
              <a href="/downloads/${f.name}" target="_blank" class="text-xs bg-surface-hover hover:bg-surface-border text-slate-300 px-2.5 py-1.5 rounded-lg font-mono transition">
                <i class="fa-solid fa-play"></i>
              </a>
              <a href="/downloads/${f.name}" download class="text-xs bg-amber-600/20 hover:bg-amber-600/40 text-amber-300 border border-amber-500/30 px-2.5 py-1.5 rounded-lg font-mono transition">
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

    // --- Learned Routes ---
    async function loadRoutes() {
      try {
        const res = await fetch('/api/routes');
        const routes = await res.json();
        const tbody = document.getElementById('routesTableBody');
        tbody.innerHTML = '';

        document.getElementById('statLearnedRoutes').innerText = routes.length;

        if (routes.length === 0) {
          tbody.innerHTML = '<tr><td colspan="5" class="py-6 text-center text-slate-500">No routes learned yet. Execute requests to populate cache.</td></tr>';
          return;
        }

        routes.forEach(r => {
          const tr = document.createElement('tr');
          tr.className = 'hover:bg-surface-card/40 transition';
          tr.innerHTML = `
            <td class="py-2.5 px-3 font-bold ${r.method === 'GET' ? 'text-emerald-400' : 'text-purple-400'}">${r.method}</td>
            <td class="py-2.5 px-3 text-slate-300 truncate max-w-[280px]" title="${r.url}">${r.url}</td>
            <td class="py-2.5 px-3 text-slate-400">${r.domain || '-'}</td>
            <td class="py-2.5 px-3 text-cyan-400">${r.schema_key || 'generic'}</td>
            <td class="py-2.5 px-3 text-right">
              <button onclick="testRouteFast('${r.url}')" class="text-[10px] bg-emerald-500/10 hover:bg-emerald-500/20 text-emerald-400 border border-emerald-500/20 px-2 py-1 rounded transition">Replay Fast</button>
            </td>
          `;
          tbody.appendChild(tr);
        });
      } catch (e) {
        console.error('Failed to load routes:', e);
      }
    }

    function testRouteFast(url) {
      document.getElementById('targetUrl').value = url;
      document.getElementById('reqTier').value = '1';
      switchTab('playground');
      executeUniversalRequest();
    }

    async function clearLearnedRoutes() {
      if (!confirm('Clear all cached routes from learned_routes.json?')) return;
      try {
        await fetch('/api/clear-cache', { method: 'POST' });
        loadRoutes();
      } catch (e) {
        alert('Failed to clear routes: ' + e);
      }
    }

    // Initial boot load
    loadSessions();
    loadRoutes();
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
    """Serves the interactive 3-Tier Luxury Dashboard."""
    return HTMLResponse(content=DASHBOARD_HTML)


# --- Session Management Endpoints ---

@web_app.get("/api/sessions")
async def api_list_sessions():
    """Returns all saved session profiles and the active profile."""
    return {
        "status": "success",
        "active_session": session_manager.get_active_session(),
        "sessions": session_manager.list_sessions()
    }


@web_app.post("/api/sessions/add")
async def api_add_session(payload: Dict[str, Any]):
    """Adds a new session profile and retains it permanently."""
    name = payload.get("name", "New Session")
    email = payload.get("email", "")
    domain = payload.get("domain", "flow.google.com")
    raw_cookies = payload.get("raw_cookies", "")

    cookies_dict = {}
    if raw_cookies:
        raw_cookies = raw_cookies.strip()
        if raw_cookies.startswith("{") and raw_cookies.endswith("}"):
            try:
                cookies_dict = json.loads(raw_cookies)
            except Exception:
                pass
        if not cookies_dict:
            for item in raw_cookies.split(";"):
                if "=" in item:
                    k, v = item.strip().split("=", 1)
                    cookies_dict[k] = v

    record = session_manager.add_session(
        name=name,
        email=email,
        domain=domain,
        cookies_dict=cookies_dict,
        set_active=True
    )
    return {"status": "success", "session": record}


@web_app.delete("/api/sessions/{session_id}")
async def api_remove_session(session_id: str):
    """Deletes a session profile permanently."""
    ok = session_manager.remove_session(session_id)
    return {"status": "success" if ok else "not_found", "session_id": session_id}


@web_app.post("/api/sessions/{session_id}/select")
async def api_select_session(session_id: str):
    """Switches the active session profile."""
    rec = session_manager.select_session(session_id)
    if not rec:
        raise HTTPException(status_code=404, detail="Session not found")
    return {"status": "success", "active_session": rec}


@web_app.post("/api/authenticate")
async def api_authenticate(target_url: str = "https://flow.google.com/"):
    """Launches visible Chrome window for one-time Google Login and session capture."""
    try:
        res = await run_interactive_login(target_url=target_url)
        return JSONResponse(content=res)
    except Exception as e:
        return JSONResponse(
            status_code=500,
            content={"status": "error", "message": f"Interactive authentication error: {str(e)}"}
        )


# --- Autonomous Platform Skill Learner Endpoints ---

@web_app.post("/api/learn-platform")
async def api_learn_platform(payload: Dict[str, Any], background_tasks: BackgroundTasks):
    """Starts autonomous deep exploration of any platform in the background."""
    url = payload.get("url", "https://flow.google.com/")
    
    # Launch in background so user gets instant response
    background_tasks.add_task(platform_learner.learn_platform, url)
    return {
        "status": "started",
        "url": url,
        "message": "Platform exploration initiated in background. Poll /api/learn-platform/status for progress."
    }


@web_app.get("/api/learn-platform/status")
async def api_learn_platform_status():
    """Returns the live learning state and progress percentage for the dashboard."""
    return platform_learner.get_status()


@web_app.get("/api/learn-platform/skill")
async def api_get_platform_skill():
    """Returns the content of the generated Platform Skill guide markdown."""
    status = platform_learner.get_status()
    skill_file = status.get("skill_file")
    
    # Fallback to root GOOGLE_FLOW_SKILL.md if none generated yet
    target_path = Path(skill_file) if skill_file and os.path.exists(skill_file) else (BASE_DIR / "GOOGLE_FLOW_SKILL.md")
    
    if target_path.exists():
        with open(target_path, "r", encoding="utf-8") as f:
            content = f.read()
        return {"filename": target_path.name, "content": content}
    return {"filename": "No skill compiled", "content": "No platform skill file found yet."}


# --- Google Flow Video Generation & Media Downloads ---

@web_app.post("/api/flow/generate")
async def api_flow_generate(payload: Dict[str, Any], background_tasks: BackgroundTasks):
    """Triggers video generation on Google Flow using active session."""
    prompt = payload.get("prompt", "High tech developer workstation")
    model = payload.get("model", "veo")
    duration = payload.get("duration", "30s_ad")
    project_url = "https://flow.google.com/project/5730a6a6-a00a-4a95-8f22-20942efd1413"

    automator = FlowVideoAutomator(project_url=project_url, output_dir=DOWNLOADS_DIR)

    if duration == "30s_ad":
        concepts = [{"title": "Universal_Web_MCP_Ad", "concept": prompt}]
    else:
        concepts = [{"title": "Single_Scene_Shot", "concept": prompt}]

    # Run production pipeline in background
    background_tasks.add_task(automator.execute_batch_production, concepts, model)

    return {
        "status": "initiated",
        "model": model,
        "duration": duration,
        "message": f"Generation task queued with model '{model.upper()}'. Check Local Download Vault when complete."
    }


@web_app.get("/api/flow/downloads")
async def api_list_downloads():
    """Lists downloaded MP4 files in the downloads directory."""
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


# --- 3-Tier Hybrid Request Runner & Cache ---

@web_app.post("/api/request")
async def api_universal_request(payload: Dict[str, Any]):
    """Executes a 3-tier hybrid request on any target URL."""
    url = payload.get("url")
    method = payload.get("method", "GET")
    force_tier = payload.get("force_tier")
    return await universal_request(url=url, method=method, force_tier=force_tier)


@web_app.get("/api/routes")
async def api_get_routes(domain: Optional[str] = None):
    """Returns the list of learned API routes and schemas."""
    return list_learned_routes(domain=domain)


@web_app.post("/api/clear-cache")
async def api_clear_cache(domain: Optional[str] = None):
    """Purges cached routes."""
    return clear_cache(domain=domain)


if __name__ == "__main__":
    port = int(os.environ.get("PORT", 8000))
    print("=======================================================")
    print("Universal-Web-MCP Luxury Studio & Server is starting")
    print(f"Web Dashboard: http://localhost:{port}")
    print(f"MCP SSE Endpoint: http://localhost:{port}/mcp/sse")
    print("=======================================================")
    uvicorn.run("app:web_app", host="0.0.0.0", port=port, reload=False)
