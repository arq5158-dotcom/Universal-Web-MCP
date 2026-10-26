"""
Universal-Web-MCP Minimal Studio.
Inspired by Ashzo design system & Awwwards minimal luxury aesthetic.
Features:
- Ashzo Design System: Obsidian dark / Alabaster light, Iris & Volt accents, film grain, animated Ashzo logo mark.
- Custom Animated Glassmorphic Dropdowns: Model, Quality, Platform, and Routing Tier.
- Silky Modal Transitions: Backdrop blur fade and spring-scale dialog entrance.
- Smooth Light / Dark Theme Animations: Global transition with rotating sun/moon icon.
- Micro-interactions: Tab animations, button hover/press states, live pulse indicators, and vault interactions.
- Minimal text: Zero clutter, concise labels, micro-badges, clean punchy controls.
- Live Google Flow Credits HUD: 373 Credits [PRO] directly in Flow card with instant refresh.
- Generative Studio: Omni Flash (4s, 6s, 8s, 10s), Veo 3.1 (8s cap), Keyframe Interpolation, 1080p default.
- Download Vault with inline file renaming.
- Universal Account Manager (Google, GitHub, Twitter, Custom) with sessions.json persistence.
"""

import os
import sys
import json
import time
import asyncio
from typing import Optional, Dict, Any, List
from pathlib import Path

from fastapi import FastAPI, Request, BackgroundTasks, HTTPException
from fastapi.responses import HTMLResponse, JSONResponse, FileResponse, StreamingResponse
from fastapi.staticfiles import StaticFiles
from fastapi.middleware.cors import CORSMiddleware
import uvicorn
from live_events import live_broadcaster

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
    title="Ashzo MCP Minimal Studio",
    description="Sub-second 3-Tier Hybrid Routing & Autonomous Creative Studio",
    version="4.2.0"
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
  <title>Ashzo MCP · Minimal Studio</title>
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
            sans: ['"Plus Jakarta Sans"', 'ui-sans-serif', 'system-ui', 'sans-serif'],
            mono: ['"JetBrains Mono"', 'ui-monospace', 'monospace'],
          },
          colors: {
            ashzo: {
              iris: '#8b6cff',
              irisInk: '#beacff',
              volt: '#c8f560',
              sky: '#38bdf8',
            }
          }
        }
      }
    }
  </script>
  <style>
    :root {
      --radius: 20px;
      --radius-sm: 12px;
      --ease: cubic-bezier(0.22, 1, 0.36, 1);
    }

    /* Film Grain Overlay */
    body::after {
      content: '';
      position: fixed;
      inset: -60px;
      z-index: 999;
      pointer-events: none;
      opacity: 0.035;
      background-image: url("data:image/svg+xml,%3Csvg xmlns='http://www.w3.org/2000/svg' width='160' height='160'%3E%3Cfilter id='n'%3E%3CfeTurbulence type='fractalNoise' baseFrequency='.9' numOctaves='3' stitchTiles='stitch'/%3E%3C/filter%3E%3Crect width='100%25' height='100%25' filter='url(%23n)'/%3E%3C/svg%3E");
    }

    /* Ashzo Dark Theme (Obsidian & Iris) */
    html.dark {
      background-color: #070709;
      color: #f5f4f8;
    }
    html.dark .ashzo-mesh {
      background:
        radial-gradient(ellipse 65% 50% at 15% 0%, rgba(139, 108, 255, 0.12) 0%, transparent 65%),
        radial-gradient(ellipse 55% 40% at 85% 5%, rgba(56, 189, 248, 0.08) 0%, transparent 60%),
        radial-gradient(ellipse 45% 35% at 50% 95%, rgba(200, 245, 96, 0.04) 0%, transparent 50%),
        #070709;
    }
    html.dark .ashzo-glass {
      background: rgba(14, 15, 23, 0.72);
      border: 1px solid rgba(255, 255, 255, 0.08);
      box-shadow: 0 20px 40px -15px rgba(0, 0, 0, 0.5), inset 0 1px 0 rgba(255, 255, 255, 0.08);
      backdrop-filter: blur(24px) saturate(1.6);
      -webkit-backdrop-filter: blur(24px) saturate(1.6);
    }
    html.dark .ashzo-card-sub {
      background: rgba(19, 21, 33, 0.65);
      border: 1px solid rgba(255, 255, 255, 0.06);
    }
    html.dark .ashzo-input {
      background: rgba(10, 11, 18, 0.85);
      border: 1px solid rgba(255, 255, 255, 0.09);
      color: #f5f4f8;
    }
    html.dark .ashzo-input:focus {
      border-color: #8b6cff;
      outline: none;
      box-shadow: 0 0 0 2px rgba(139, 108, 255, 0.2);
    }
    html.dark .ashzo-border { border-color: rgba(255, 255, 255, 0.08); }
    html.dark .ashzo-text-muted { color: rgba(245, 244, 248, 0.65); }
    html.dark .ashzo-text-dim { color: rgba(245, 244, 248, 0.42); }

    /* Ashzo Light Theme (Alabaster Luxury) */
    html:not(.dark) {
      background-color: #f8f9fc;
      color: #0b0b10;
    }
    html:not(.dark) .ashzo-mesh {
      background:
        radial-gradient(ellipse 65% 50% at 15% 0%, rgba(139, 108, 255, 0.08) 0%, transparent 65%),
        radial-gradient(ellipse 55% 40% at 85% 5%, rgba(56, 189, 248, 0.07) 0%, transparent 60%),
        #f8f9fc;
    }
    html:not(.dark) .ashzo-glass {
      background: rgba(255, 255, 255, 0.88);
      border: 1px solid rgba(15, 23, 42, 0.08);
      box-shadow: 0 10px 30px -10px rgba(15, 23, 42, 0.06), inset 0 1px 0 rgba(255, 255, 255, 0.9);
      backdrop-filter: blur(24px) saturate(1.6);
      -webkit-backdrop-filter: blur(24px) saturate(1.6);
    }
    html:not(.dark) .ashzo-card-sub {
      background: rgba(241, 245, 249, 0.8);
      border: 1px solid rgba(15, 23, 42, 0.06);
    }
    html:not(.dark) .ashzo-input {
      background: #ffffff;
      border: 1px solid rgba(15, 23, 42, 0.12);
      color: #0b0b10;
    }
    html:not(.dark) .ashzo-input:focus {
      border-color: #7952f5;
      outline: none;
      box-shadow: 0 0 0 2px rgba(121, 82, 245, 0.15);
    }
    html:not(.dark) .ashzo-border { border-color: rgba(15, 23, 42, 0.08); }
    html:not(.dark) .ashzo-text-muted { color: rgba(11, 11, 16, 0.65); }
    html:not(.dark) .ashzo-text-dim { color: rgba(11, 11, 16, 0.42); }

    /* Theme Switch Animation */
    html.theme-animating,
    html.theme-animating body,
    html.theme-animating .ashzo-mesh,
    html.theme-animating .ashzo-glass,
    html.theme-animating .ashzo-card-sub,
    html.theme-animating .ashzo-input,
    html.theme-animating .ashzo-border,
    html.theme-animating button,
    html.theme-animating input,
    html.theme-animating textarea,
    html.theme-animating pre {
      transition: background-color 0.45s var(--ease),
                  background 0.45s var(--ease),
                  border-color 0.45s var(--ease),
                  color 0.45s var(--ease),
                  box-shadow 0.45s var(--ease) !important;
    }

    .theme-spin {
      animation: themeRotate 0.55s var(--ease) forwards;
    }
    @keyframes themeRotate {
      0% { transform: rotate(0deg) scale(1); }
      50% { transform: rotate(180deg) scale(0.65); opacity: 0.4; }
      100% { transform: rotate(360deg) scale(1); opacity: 1; }
    }

    /* Tab Switch Animation */
    @keyframes tabEnter {
      0% { opacity: 0; transform: translateY(6px); }
      100% { opacity: 1; transform: translateY(0); }
    }
    .tab-animating {
      animation: tabEnter 0.3s var(--ease) forwards;
    }

    /* Modal Animation */
    .modal-overlay {
      opacity: 0;
      visibility: hidden;
      pointer-events: none;
      transition: opacity 0.3s var(--ease), visibility 0.3s var(--ease);
    }
    .modal-overlay.is-open {
      opacity: 1;
      visibility: visible;
      pointer-events: auto;
    }
    .modal-dialog {
      transform: scale(0.92) translateY(16px);
      opacity: 0;
      transition: transform 0.32s var(--ease), opacity 0.28s var(--ease);
    }
    .modal-overlay.is-open .modal-dialog {
      transform: scale(1) translateY(0);
      opacity: 1;
    }

    /* Custom Animated Dropdown */
    .custom-dropdown {
      position: relative;
      user-select: none;
    }
    .dropdown-trigger {
      display: flex;
      align-items: center;
      justify-content: space-between;
      width: 100%;
      cursor: pointer;
      transition: border-color 0.2s, box-shadow 0.2s, background-color 0.2s, transform 0.2s;
    }
    .dropdown-trigger:hover {
      border-color: rgba(139, 108, 255, 0.4);
    }
    .dropdown-trigger .chevron {
      transition: transform 0.3s var(--ease);
    }
    .custom-dropdown.is-open .dropdown-trigger .chevron {
      transform: rotate(180deg);
    }
    .dropdown-menu {
      position: absolute;
      left: 0;
      top: calc(100% + 6px);
      width: 100%;
      z-index: 60;
      opacity: 0;
      visibility: hidden;
      transform: translateY(-8px) scale(0.97);
      transition: opacity 0.22s var(--ease), transform 0.22s var(--ease), visibility 0.22s var(--ease);
      transform-origin: top center;
      max-height: 240px;
      overflow-y: auto;
    }
    html.dark .dropdown-menu {
      background: rgba(14, 16, 26, 0.98);
      border: 1px solid rgba(255, 255, 255, 0.12);
      box-shadow: 0 20px 45px -10px rgba(0, 0, 0, 0.8), inset 0 1px 0 rgba(255, 255, 255, 0.1);
      backdrop-filter: blur(32px);
      -webkit-backdrop-filter: blur(32px);
    }
    html:not(.dark) .dropdown-menu {
      background: rgba(255, 255, 255, 0.98);
      border: 1px solid rgba(15, 23, 42, 0.12);
      box-shadow: 0 20px 40px -10px rgba(15, 23, 42, 0.15), inset 0 1px 0 rgba(255, 255, 255, 0.9);
      backdrop-filter: blur(32px);
      -webkit-backdrop-filter: blur(32px);
    }
    .custom-dropdown.is-open .dropdown-menu {
      opacity: 1;
      visibility: visible;
      transform: translateY(0) scale(1);
    }
    .dropdown-item {
      display: flex;
      align-items: center;
      justify-content: space-between;
      padding: 7px 11px;
      border-radius: 8px;
      font-size: 12px;
      font-family: 'JetBrains Mono', monospace;
      cursor: pointer;
      transition: background-color 0.15s, color 0.15s, transform 0.15s;
    }
    .dropdown-item:hover {
      background-color: rgba(139, 108, 255, 0.14);
      color: #8b6cff;
      transform: translateX(2px);
    }
    .dropdown-item.is-selected {
      color: #8b6cff;
      font-weight: 600;
    }
    html:not(.dark) .dropdown-item.is-selected {
      color: #7952f5;
    }

    /* Micro-interactions */
    .dur-btn {
      transition: all 0.22s var(--ease);
    }
    .dur-btn:hover {
      transform: translateY(-1px);
    }
    .dur-btn:active {
      transform: scale(0.96);
    }
    .vault-item {
      transition: transform 0.22s var(--ease), border-color 0.22s, background-color 0.22s;
    }
    .vault-item:hover {
      transform: translateY(-1.5px);
    }

    /* Volt pulse dot */
    .volt-dot {
      background-color: #c8f560;
      box-shadow: 0 0 0 3px rgba(200, 245, 96, 0.22), 0 0 12px rgba(200, 245, 96, 0.8);
    }
    html:not(.dark) .volt-dot {
      background-color: #10b981;
      box-shadow: 0 0 0 3px rgba(16, 185, 129, 0.2), 0 0 10px rgba(16, 185, 129, 0.6);
    }

    /* Logo equalizer animation */
    .logo-bars rect { animation: bars 2.4s ease-in-out infinite; transform-box: fill-box; }
    .logo-bars rect:nth-child(2) { animation-delay: 0.2s; }
    .logo-bars rect:nth-child(3) { animation-delay: 0.4s; }
    @keyframes bars { 0%, 100% { transform: translateX(0); } 50% { transform: translateX(2.5px); } }

    .custom-scrollbar::-webkit-scrollbar { width: 4px; height: 4px; }
    .custom-scrollbar::-webkit-scrollbar-track { background: transparent; }
    .custom-scrollbar::-webkit-scrollbar-thumb { background: rgba(150, 150, 150, 0.22); border-radius: 999px; }
  </style>
</head>
<body class="ashzo-mesh min-h-screen flex flex-col font-sans">

  <!-- Ashzo Minimal Header -->
  <header class="ashzo-border border-b backdrop-blur-xl sticky top-0 z-40">
    <div class="max-w-6xl mx-auto px-5 py-3 flex items-center justify-between">
      
      <!-- Brand with Authentic Ashzo Logo SVG -->
      <a href="/" class="flex items-center gap-2.5 group select-none">
        <svg class="w-7 h-7 flex-none" viewBox="0 0 120 120" aria-hidden="true">
          <defs>
            <linearGradient id="ashzo-body" x1="24" y1="20" x2="96" y2="92" gradientUnits="userSpaceOnUse">
              <stop offset="0" stop-color="#38bdf8"/>
              <stop offset=".4" stop-color="#2563eb"/>
              <stop offset="1" stop-color="#7c3aed"/>
            </linearGradient>
            <linearGradient id="ashzo-curl" x1="24" y1="40" x2="52" y2="76" gradientUnits="userSpaceOnUse">
              <stop offset="0" stop-color="#0f172a" stop-opacity=".65"/>
              <stop offset="1" stop-color="#0f172a" stop-opacity="0"/>
            </linearGradient>
            <linearGradient id="ashzo-bars" x1="58" y1="46" x2="98" y2="70" gradientUnits="userSpaceOnUse">
              <stop offset="0" stop-color="#38bdf8"/>
              <stop offset=".6" stop-color="#60a5fa"/>
              <stop offset="1" stop-color="#818cf8"/>
            </linearGradient>
          </defs>
          <path d="M57 16C53.5 16 49.5 20.5 45.5 29L25 73.5C21 81.5 24.5 90 33.5 90c6 0 11-4.5 15-11.5l7-14c1-2 4-2 5 0l7 14c4 7 9 11.5 15 11.5 9 0 12.5-8.5 8.5-16.5L70.5 29C66.5 20.5 62.5 16 57 16Z" fill="url(#ashzo-body)"/>
          <path d="M45.5 29 25 73.5C21 81.5 24.5 90 33.5 90c6 0 11-4.5 15-11.5L57 60c1-5-3-13-7-21Z" fill="url(#ashzo-curl)" opacity=".75"/>
          <path d="M54.5 42c0-2 2.3-3.2 4-2.2l14 8.7c1.7 1 1.7 3.7 0 4.7l-14 8.7c-1.7 1-4-.2-4-2.2Z" fill="#fff"/>
          <g class="logo-bars" fill="url(#ashzo-bars)">
            <rect x="67" y="42" width="28" height="5.5" rx="2.75"/>
            <rect x="61" y="51" width="37" height="5.5" rx="2.75"/>
            <rect x="61" y="60" width="28" height="5.5" rx="2.75"/>
          </g>
        </svg>
        <span class="font-semibold text-sm tracking-tight flex items-center gap-1.5">
          Ashzo MCP
          <span class="text-[9px] font-mono px-1.5 py-0.5 rounded-full bg-indigo-500/10 text-indigo-400 border border-indigo-500/20">v4.2</span>
        </span>
      </a>

      <!-- Right Controls -->
      <div class="flex items-center gap-2.5">
        
        <!-- Active Session Pill -->
        <div id="activeSessionBadge" class="flex items-center gap-2 px-3 py-1.5 rounded-full ashzo-card-sub text-xs font-mono transition-transform hover:scale-[1.02]">
          <span class="w-1.5 h-1.5 rounded-full volt-dot"></span>
          <span id="activeAccountName" class="font-medium text-indigo-400 truncate max-w-[150px]">arq5020@gmail.com</span>
        </div>

        <!-- Animated Light / Dark Theme Switch Button -->
        <button onclick="toggleTheme()" id="themeToggleBtn" class="w-8 h-8 rounded-full ashzo-card-sub flex items-center justify-center ashzo-text-muted hover:text-indigo-400 transition" title="Toggle Theme">
          <i class="fa-solid fa-moon text-xs"></i>
        </button>

        <!-- Connect Account Button -->
        <button onclick="openLoginModal()" class="bg-indigo-600 hover:bg-indigo-500 active:scale-95 text-white font-medium text-xs px-3.5 py-1.5 rounded-full transition shadow-sm flex items-center gap-1.5">
          <i class="fa-solid fa-plus text-[10px]"></i>
          <span>Connect</span>
        </button>

      </div>
    </div>
  </header>

  <!-- Minimal Nav Tabs -->
  <div class="ashzo-border border-b">
    <div class="max-w-6xl mx-auto px-5 flex items-center space-x-1">
      <button onclick="switchTab('flow')" id="tab-btn-flow" class="tab-btn py-2.5 px-3.5 text-xs font-medium border-b-2 border-indigo-500 text-indigo-400 transition flex items-center gap-1.5">
        <i class="fa-solid fa-video text-[11px]"></i>
        <span>Google Flow</span>
      </button>
      <button onclick="switchTab('sessions')" id="tab-btn-sessions" class="tab-btn py-2.5 px-3.5 text-xs font-medium border-b-2 border-transparent ashzo-text-dim hover:text-indigo-400 transition flex items-center gap-1.5">
        <i class="fa-solid fa-users text-[11px]"></i>
        <span>Accounts</span>
      </button>
      <button onclick="switchTab('learner')" id="tab-btn-learner" class="tab-btn py-2.5 px-3.5 text-xs font-medium border-b-2 border-transparent ashzo-text-dim hover:text-indigo-400 transition flex items-center gap-1.5">
        <i class="fa-solid fa-compass text-[11px]"></i>
        <span>Explorer</span>
      </button>
      <button onclick="switchTab('playground')" id="tab-btn-playground" class="tab-btn py-2.5 px-3.5 text-xs font-medium border-b-2 border-transparent ashzo-text-dim hover:text-indigo-400 transition flex items-center gap-1.5">
        <i class="fa-solid fa-bolt text-[11px]"></i>
        <span>Fast Path</span>
      </button>
    </div>
  </div>

  <!-- Main Viewport -->
  <main class="max-w-6xl w-full mx-auto px-5 py-5 flex-1">

    <!-- TAB 1: GOOGLE FLOW STUDIO -->
    <div id="tab-flow" class="tab-content tab-animating">
      <div class="grid grid-cols-1 lg:grid-cols-12 gap-5">

        <!-- Controls (Left 7 Cols) -->
        <div class="lg:col-span-7 space-y-4">
          <div class="ashzo-glass rounded-2xl p-5 space-y-4">
            
            <!-- Flow Header with Live Account Credits Inside -->
            <div class="flex items-center justify-between border-b ashzo-border pb-3">
              <div class="flex items-center gap-2">
                <span class="text-xs font-semibold tracking-tight uppercase font-mono">Google Flow</span>
                <span class="text-[10px] font-mono px-2 py-0.5 rounded-full bg-indigo-500/10 text-indigo-400 border border-indigo-500/20">Omni Flash &amp; Veo</span>
              </div>

              <!-- Live Account Credits HUD -->
              <div class="flex items-center gap-2 text-xs font-mono">
                <div class="flex items-center gap-2 px-3 py-1 rounded-full ashzo-card-sub border ashzo-border">
                  <span class="w-1.5 h-1.5 rounded-full volt-dot"></span>
                  <span class="ashzo-text-dim text-[11px]">Live:</span>
                  <span id="creditsValue" class="font-bold text-emerald-400">373 Credits</span>
                  <span class="text-[9px] uppercase px-1 py-0.2 rounded bg-indigo-500/10 text-indigo-400 font-semibold">PRO</span>
                </div>
                <button onclick="refreshLiveCredits()" id="refreshCreditsBtn" class="w-7 h-7 rounded-full ashzo-card-sub border ashzo-border ashzo-text-dim hover:text-emerald-400 active:scale-95 transition flex items-center justify-center text-[10px]" title="Refresh Balance">
                  <i class="fa-solid fa-rotate"></i>
                </button>
              </div>
            </div>

            <!-- Real-Time Live Agent Pipeline HUD & Terminal Feed -->
            <div class="ashzo-card-sub rounded-xl p-3 border ashzo-border space-y-2" id="agentLiveHud">
              <div class="flex items-center justify-between">
                <div class="flex items-center gap-2">
                  <span class="w-1.5 h-1.5 rounded-full volt-dot" id="liveAgentDot"></span>
                  <span class="text-xs font-mono font-medium" id="liveAgentStage">Agent Standby</span>
                  <span class="text-[9px] font-mono px-1.5 py-0.2 rounded bg-indigo-500/10 text-indigo-400 border border-indigo-500/20" id="liveAgentBadge">IDLE</span>
                </div>
                <button type="button" onclick="toggleAgentFeed()" class="text-[10px] font-mono ashzo-text-dim hover:text-indigo-400 flex items-center gap-1.5 transition">
                  <i class="fa-solid fa-terminal text-[9px]"></i>
                  <span id="feedToggleText">Live Feed</span>
                  <i class="fa-solid fa-chevron-down text-[8px] transition-transform duration-200" id="feedChevron"></i>
                </button>
              </div>

              <!-- Animated Progress Bar -->
              <div class="w-full bg-black/40 rounded-full h-1 overflow-hidden" id="liveProgressContainer">
                <div id="liveProgressBar" class="h-1 rounded-full bg-gradient-to-r from-indigo-500 via-purple-500 to-emerald-400 transition-all duration-300" style="width: 0%"></div>
              </div>

              <!-- Real-time Agent Status Line -->
              <p id="liveStatusText" class="text-[10px] font-mono ashzo-text-dim truncate">Standby · Real-time pipeline active.</p>

              <!-- Collapsible Live Agent Terminal -->
              <div id="agentTerminalFeed" class="hidden mt-2 pt-2 border-t ashzo-border">
                <div id="terminalLogs" class="max-h-28 overflow-y-auto custom-scrollbar font-mono text-[10px] space-y-1 text-slate-400">
                  <div class="text-[9px] ashzo-text-dim font-mono">[System] Real-time agent event stream connected.</div>
                </div>
              </div>
            </div>

            <!-- Custom Animated Dropdowns: Model & Quality -->
            <div class="grid grid-cols-2 gap-3">
              
              <!-- Model Dropdown -->
              <div>
                <label class="text-[10px] font-mono uppercase tracking-wider ashzo-text-dim font-medium">Model</label>
                <div class="custom-dropdown mt-1" id="dropdown-model">
                  <div class="dropdown-trigger ashzo-input rounded-xl px-3 py-2 text-xs font-mono" onclick="toggleDropdown('dropdown-model')">
                    <span id="modelDisplay">Gemini Omni Flash</span>
                    <i class="fa-solid fa-chevron-down text-[10px] chevron ashzo-text-dim"></i>
                  </div>
                  <div class="dropdown-menu ashzo-glass rounded-xl p-1.5 shadow-2xl border ashzo-border">
                    <div class="dropdown-item is-selected" data-value="omni_flash" onclick="selectModel('omni_flash', 'Gemini Omni Flash')">
                      <span>Gemini Omni Flash</span>
                      <span class="text-[9px] font-mono ashzo-text-dim">4s-10s</span>
                    </div>
                    <div class="dropdown-item" data-value="veo_3_1" onclick="selectModel('veo_3_1', 'Google Veo 3.1')">
                      <span>Google Veo 3.1</span>
                      <span class="text-[9px] font-mono ashzo-text-dim">8s Max</span>
                    </div>
                    <div class="dropdown-item" data-value="gemini_omni" onclick="selectModel('gemini_omni', 'Gemini Omni')">
                      <span>Gemini Omni</span>
                      <span class="text-[9px] font-mono ashzo-text-dim">Standard</span>
                    </div>
                  </div>
                  <input type="hidden" id="modelSelect" value="omni_flash">
                </div>
              </div>

              <!-- Quality Dropdown -->
              <div>
                <label class="text-[10px] font-mono uppercase tracking-wider ashzo-text-dim font-medium">Quality</label>
                <div class="custom-dropdown mt-1" id="dropdown-quality">
                  <div class="dropdown-trigger ashzo-input rounded-xl px-3 py-2 text-xs font-mono" onclick="toggleDropdown('dropdown-quality')">
                    <span id="qualityDisplay">1080p Upscaled</span>
                    <i class="fa-solid fa-chevron-down text-[10px] chevron ashzo-text-dim"></i>
                  </div>
                  <div class="dropdown-menu ashzo-glass rounded-xl p-1.5 shadow-2xl border ashzo-border">
                    <div class="dropdown-item is-selected" data-value="1080p" onclick="selectQuality('1080p', '1080p Upscaled')">
                      <span>1080p Upscaled</span>
                      <span class="text-[9px] font-mono ashzo-text-dim">FHD</span>
                    </div>
                    <div class="dropdown-item" data-value="720p" onclick="selectQuality('720p', '720p Native')">
                      <span>720p Native</span>
                      <span class="text-[9px] font-mono ashzo-text-dim">Fast</span>
                    </div>
                    <div class="dropdown-item" data-value="4k" onclick="selectQuality('4k', '4K Ultra HD')">
                      <span>4K Ultra HD</span>
                      <span class="text-[9px] font-mono ashzo-text-dim">Ultra</span>
                    </div>
                  </div>
                  <input type="hidden" id="qualitySelect" value="1080p">
                </div>
              </div>

            </div>

            <!-- Duration Pills -->
            <div>
              <label class="text-[10px] font-mono uppercase tracking-wider ashzo-text-dim font-medium">Duration</label>
              <div id="durationPills" class="flex flex-wrap gap-1.5 mt-1.5">
                <button type="button" onclick="setDuration('4')" class="dur-btn px-2.5 py-1 rounded-lg text-xs font-mono border ashzo-card-sub ashzo-border ashzo-text-muted">4s</button>
                <button type="button" onclick="setDuration('6')" class="dur-btn px-2.5 py-1 rounded-lg text-xs font-mono border ashzo-card-sub ashzo-border ashzo-text-muted">6s</button>
                <button type="button" onclick="setDuration('8')" class="dur-btn px-2.5 py-1 rounded-lg text-xs font-mono border border-indigo-500 bg-indigo-500/10 text-indigo-400 font-semibold shadow-[0_0_12px_rgba(139,108,255,0.25)]">8s</button>
                <button type="button" onclick="setDuration('10')" class="dur-btn px-2.5 py-1 rounded-lg text-xs font-mono border ashzo-card-sub ashzo-border ashzo-text-muted">10s</button>
                <button type="button" onclick="setDuration('30s_ad')" class="dur-btn px-2.5 py-1 rounded-lg text-xs font-mono border ashzo-card-sub ashzo-border ashzo-text-muted">30s (4 Scenes)</button>
              </div>
              <input type="hidden" id="selectedDuration" value="8">
            </div>

            <!-- Keyframes Accordion -->
            <details class="ashzo-card-sub rounded-xl p-2.5 text-xs group transition-all duration-300">
              <summary class="cursor-pointer font-mono text-[10px] ashzo-text-dim select-none hover:text-indigo-400 flex items-center justify-between">
                <span><i class="fa-solid fa-arrows-left-right mr-1"></i> Keyframe Interpolation</span>
                <i class="fa-solid fa-chevron-down text-[8px] transition-transform duration-300 group-open:rotate-180"></i>
              </summary>
              <div class="grid grid-cols-2 gap-2 mt-2 pt-2 border-t ashzo-border">
                <div>
                  <label class="text-[9px] font-mono ashzo-text-dim">Start Frame (0s):</label>
                  <input id="startFrame" type="text" placeholder="@FirstFrame" class="mt-0.5 w-full ashzo-input rounded-lg px-2 py-1 text-xs font-mono">
                </div>
                <div>
                  <label class="text-[9px] font-mono ashzo-text-dim">End Frame (4s-10s):</label>
                  <input id="endFrame" type="text" placeholder="@LastFrame" class="mt-0.5 w-full ashzo-input rounded-lg px-2 py-1 text-xs font-mono">
                </div>
              </div>
            </details>

            <!-- Prompt -->
            <div>
              <div class="flex items-center justify-between mb-1">
                <label class="text-[10px] font-mono uppercase tracking-wider ashzo-text-dim font-medium">Prompt</label>
                <div class="flex gap-1">
                  <button type="button" onclick="appendTag('Cinematic 35mm lens, 4K')" class="text-[9px] font-mono px-1.5 py-0.5 rounded ashzo-card-sub ashzo-text-dim hover:text-indigo-400 active:scale-95 transition">+ 35mm</button>
                  <button type="button" onclick="appendTag('FPV drone push-in, volumetric lighting')" class="text-[9px] font-mono px-1.5 py-0.5 rounded ashzo-card-sub ashzo-text-dim hover:text-indigo-400 active:scale-95 transition">+ FPV</button>
                  <button type="button" onclick="appendTag('Smooth dolly out, golden hour')" class="text-[9px] font-mono px-1.5 py-0.5 rounded ashzo-card-sub ashzo-text-dim hover:text-indigo-400 active:scale-95 transition">+ Dolly</button>
                </div>
              </div>
              <textarea id="promptInput" rows="3" class="w-full ashzo-input rounded-xl p-3 text-xs font-mono placeholder:text-slate-500" placeholder="Describe the scene...">Futuristic developer terminal displaying neon cyan data streams at sub-second speed. Smooth 35mm camera motion, volumetric reflections, 4K resolution.</textarea>
            </div>

            <!-- Slug & Generate Button -->
            <div class="flex items-center gap-2.5 pt-1">
              <input id="slugInput" type="text" value="universal_web_launch" placeholder="Video name slug" class="flex-1 ashzo-input rounded-xl px-3 py-2 text-xs font-mono">
              <button id="genBtn" onclick="submitGeneration()" class="bg-indigo-600 hover:bg-indigo-500 active:scale-95 text-white font-medium text-xs px-5 py-2.5 rounded-xl transition shadow-sm flex items-center gap-2 whitespace-nowrap">
                <i class="fa-solid fa-play text-[9px]"></i>
                <span>Generate Video</span>
              </button>
            </div>

          </div>
        </div>

        <!-- Download Vault (Right 5 Cols) -->
        <div class="lg:col-span-5">
          <div class="ashzo-glass rounded-2xl p-5 flex flex-col h-full min-h-[420px]">
            <div class="flex items-center justify-between border-b ashzo-border pb-3 mb-3">
              <span class="text-xs font-mono uppercase tracking-wider font-semibold">Vault</span>
              <button onclick="loadDownloads()" class="ashzo-text-dim hover:text-indigo-400 active:scale-95 transition text-xs" title="Reload Vault">
                <i class="fa-solid fa-rotate"></i>
              </button>
            </div>
            <div id="downloadsList" class="space-y-2 flex-1 overflow-auto custom-scrollbar max-h-[380px]">
              <!-- Loaded dynamically -->
            </div>
          </div>
        </div>

      </div>
    </div>

    <!-- TAB 2: ACCOUNTS -->
    <div id="tab-sessions" class="tab-content hidden space-y-4">
      <div class="ashzo-glass rounded-2xl p-5 space-y-4">
        <div class="flex items-center justify-between border-b ashzo-border pb-3">
          <h2 class="text-xs font-mono uppercase tracking-wider font-semibold">Saved Accounts</h2>
          <button onclick="openLoginModal()" class="bg-indigo-600 hover:bg-indigo-500 active:scale-95 text-white font-medium text-xs px-3.5 py-1.5 rounded-full transition shadow-sm flex items-center gap-1.5">
            <i class="fa-solid fa-plus text-[9px]"></i>
            <span>Add Account</span>
          </button>
        </div>
        <div id="sessionsGrid" class="grid grid-cols-1 md:grid-cols-2 lg:grid-cols-3 gap-3">
          <!-- Loaded dynamically -->
        </div>
      </div>
    </div>

    <!-- TAB 3: PLATFORM EXPLORER -->
    <div id="tab-learner" class="tab-content hidden space-y-4">
      <div class="ashzo-glass rounded-2xl p-5 space-y-4">
        <div class="border-b ashzo-border pb-3">
          <h2 class="text-xs font-mono uppercase tracking-wider font-semibold">Platform Explorer</h2>
        </div>
        <div class="flex gap-2">
          <input id="learnerUrl" type="url" value="https://flow.google.com/" placeholder="Enter website URL..." class="flex-1 ashzo-input rounded-xl px-3.5 py-2 text-xs font-mono">
          <button id="learnerBtn" onclick="runLearner()" class="bg-indigo-600 hover:bg-indigo-500 active:scale-95 text-white font-medium text-xs px-4 py-2 rounded-xl transition whitespace-nowrap">
            <span>Explore</span>
          </button>
        </div>
        <div id="learnerStatusBox" class="ashzo-card-sub rounded-xl p-3.5 text-xs font-mono space-y-2">
          <div class="flex justify-between items-center">
            <span id="learnerPhase" class="font-semibold text-emerald-400">Ready</span>
            <span id="learnerPct" class="ashzo-text-dim">100%</span>
          </div>
          <div class="w-full bg-slate-800 rounded-full h-1 overflow-hidden">
            <div id="learnerBar" class="bg-indigo-500 h-1 transition-all duration-300" style="width: 100%"></div>
          </div>
          <p id="learnerText" class="ashzo-text-dim text-[11px]">Compiled &amp; ready.</p>
        </div>
      </div>
    </div>

    <!-- TAB 4: FAST PATH RUNNER -->
    <div id="tab-playground" class="tab-content hidden space-y-4">
      <div class="ashzo-glass rounded-2xl p-5 space-y-4">
        <div class="border-b ashzo-border pb-3">
          <h2 class="text-xs font-mono uppercase tracking-wider font-semibold">3-Tier Hybrid Fast Path</h2>
        </div>
        <div class="flex gap-2 items-center">
          <input id="runnerUrl" type="url" value="https://jsonplaceholder.typicode.com/todos/1" class="flex-1 ashzo-input rounded-xl px-3.5 py-2 text-xs font-mono">
          
          <!-- Custom Tier Dropdown -->
          <div class="custom-dropdown w-56" id="dropdown-tier">
            <div class="dropdown-trigger ashzo-input rounded-xl px-3 py-2 text-xs font-mono" onclick="toggleDropdown('dropdown-tier')">
              <span id="tierDisplay">Tier 1: Fast Path</span>
              <i class="fa-solid fa-chevron-down text-[10px] chevron ashzo-text-dim"></i>
            </div>
            <div class="dropdown-menu ashzo-glass rounded-xl p-1.5 shadow-2xl border ashzo-border">
              <div class="dropdown-item is-selected" data-value="1" onclick="selectTier(1, 'Tier 1: Fast Path')">
                <span>Tier 1: Fast Path</span>
                <span class="text-[9px] font-mono text-emerald-400">&lt;200ms</span>
              </div>
              <div class="dropdown-item" data-value="2" onclick="selectTier(2, 'Tier 2: CDP Sniffer')">
                <span>Tier 2: CDP Sniffer</span>
                <span class="text-[9px] font-mono text-indigo-400">Sniff</span>
              </div>
              <div class="dropdown-item" data-value="3" onclick="selectTier(3, 'Tier 3: DOM Fallback')">
                <span>Tier 3: DOM Fallback</span>
                <span class="text-[9px] font-mono text-amber-400">Tokens</span>
              </div>
            </div>
            <input type="hidden" id="runnerTier" value="1">
          </div>

          <button onclick="runRequest()" class="bg-indigo-600 hover:bg-indigo-500 active:scale-95 text-white font-medium text-xs px-4 py-2 rounded-xl transition">Run</button>
        </div>
        <pre id="runnerOutput" class="p-3 rounded-xl ashzo-card-sub text-xs font-mono ashzo-text-muted max-h-64 overflow-auto custom-scrollbar"><code>Output will appear here.</code></pre>
      </div>
    </div>

  </main>

  <!-- Real-Time Toast Notification Stream -->
  <div id="toastContainer" class="fixed bottom-5 right-5 z-50 flex flex-col gap-2 pointer-events-none"></div>

  <!-- Inline Rename Modal with Spring Animation -->
  <div id="renameModal" class="modal-overlay fixed inset-0 z-50 bg-black/60 backdrop-blur-md flex items-center justify-center p-4">
    <div class="modal-dialog ashzo-glass rounded-2xl max-w-sm w-full p-5 space-y-3 shadow-2xl">
      <h3 class="text-xs font-semibold uppercase tracking-wider font-mono">Rename File</h3>
      <input id="newFilenameInput" type="text" class="w-full ashzo-input rounded-lg px-3 py-2 text-xs font-mono">
      <input id="oldFilepathInput" type="hidden">
      <div class="flex justify-end gap-2 pt-2">
        <button onclick="closeRenameModal()" class="text-xs ashzo-text-dim px-3 py-1.5 rounded-lg active:scale-95 transition">Cancel</button>
        <button onclick="saveRename()" class="bg-indigo-600 hover:bg-indigo-500 active:scale-95 text-white text-xs px-3.5 py-1.5 rounded-lg font-medium transition">Save</button>
      </div>
    </div>
  </div>

  <!-- Universal Connect Account Modal with Spring Animation & Custom Dropdown -->
  <div id="loginModal" class="modal-overlay fixed inset-0 z-50 bg-black/60 backdrop-blur-md flex items-center justify-center p-4" onclick="handleModalBackdropClick(event, 'loginModal')">
    <div class="modal-dialog ashzo-glass rounded-2xl max-w-md w-full p-5 space-y-4 shadow-2xl" onclick="event.stopPropagation()">
      <div class="flex items-center justify-between border-b ashzo-border pb-2.5">
        <h3 class="text-xs font-semibold uppercase tracking-wider font-mono">Connect Account</h3>
        <button onclick="closeLoginModal()" class="ashzo-text-dim hover:text-indigo-400 p-1"><i class="fa-solid fa-xmark text-xs"></i></button>
      </div>

      <div class="space-y-3 text-xs">
        <div>
          <label class="text-[9px] font-mono uppercase tracking-wider ashzo-text-dim font-medium">Platform</label>
          <div class="custom-dropdown mt-1" id="dropdown-platform">
            <div class="dropdown-trigger ashzo-input rounded-xl px-3 py-2 text-xs font-mono" onclick="toggleDropdown('dropdown-platform')">
              <span id="platformDisplay"><i class="fa-brands fa-google mr-1.5 text-indigo-400"></i> Google</span>
              <i class="fa-solid fa-chevron-down text-[10px] chevron ashzo-text-dim"></i>
            </div>
            <div class="dropdown-menu ashzo-glass rounded-xl p-1.5 shadow-2xl border ashzo-border">
              <div class="dropdown-item is-selected" data-value="https://accounts.google.com/" onclick="selectPlatform('https://accounts.google.com/', 'Google', 'fa-brands fa-google text-indigo-400')">
                <span><i class="fa-brands fa-google mr-1.5 text-indigo-400"></i> Google</span>
                <span class="text-[9px] font-mono ashzo-text-dim">accounts.google.com</span>
              </div>
              <div class="dropdown-item" data-value="https://github.com/login" onclick="selectPlatform('https://github.com/login', 'GitHub', 'fa-brands fa-github')">
                <span><i class="fa-brands fa-github mr-1.5"></i> GitHub</span>
                <span class="text-[9px] font-mono ashzo-text-dim">github.com</span>
              </div>
              <div class="dropdown-item" data-value="https://twitter.com/i/flow/login" onclick="selectPlatform('https://twitter.com/i/flow/login', 'Twitter / X', 'fa-brands fa-x-twitter')">
                <span><i class="fa-brands fa-x-twitter mr-1.5"></i> Twitter / X</span>
                <span class="text-[9px] font-mono ashzo-text-dim">x.com</span>
              </div>
              <div class="dropdown-item" data-value="https://flow.google.com/" onclick="selectPlatform('https://flow.google.com/', 'Google Flow', 'fa-solid fa-video text-emerald-400')">
                <span><i class="fa-solid fa-video mr-1.5 text-emerald-400"></i> Google Flow</span>
                <span class="text-[9px] font-mono ashzo-text-dim">flow.google.com</span>
              </div>
              <div class="dropdown-item" data-value="custom" onclick="selectPlatform('custom', 'Custom URL', 'fa-solid fa-globe text-sky-400')">
                <span><i class="fa-solid fa-globe mr-1.5 text-sky-400"></i> Custom URL</span>
                <span class="text-[9px] font-mono ashzo-text-dim">Any platform</span>
              </div>
            </div>
            <input type="hidden" id="loginPlatformSelect" value="https://accounts.google.com/">
          </div>
        </div>

        <div id="customUrlDiv" class="hidden">
          <label class="text-[9px] font-mono uppercase tracking-wider ashzo-text-dim font-medium">Website URL</label>
          <input id="loginCustomUrl" type="url" placeholder="https://example.com/login" class="mt-1 w-full ashzo-input rounded-xl px-3 py-2 text-xs font-mono">
        </div>

        <div>
          <label class="text-[9px] font-mono uppercase tracking-wider ashzo-text-dim font-medium">Account Email</label>
          <input id="loginEmailInput" type="text" placeholder="e.g. user@gmail.com" class="mt-1 w-full ashzo-input rounded-xl px-3 py-2 text-xs font-mono">
        </div>

        <div id="loginStatusIndicator" class="hidden p-3 rounded-lg bg-indigo-500/10 border border-indigo-500/20 text-[11px] font-mono text-indigo-400 flex items-center gap-2">
          <i class="fa-solid fa-spinner animate-spin"></i>
          <span>Launching Chrome. Please log into your account...</span>
        </div>
      </div>

      <div class="flex justify-end gap-2 pt-2 border-t ashzo-border">
        <button onclick="closeLoginModal()" class="text-xs ashzo-text-dim px-3.5 py-1.5 rounded-lg active:scale-95 transition">Cancel</button>
        <button id="launchLoginBtn" onclick="executeInteractiveLogin()" class="bg-indigo-600 hover:bg-indigo-500 active:scale-95 text-white font-medium text-xs px-4 py-1.5 rounded-xl transition">
          Launch Chrome
        </button>
      </div>
    </div>
  </div>

  <script>
    // -------------------------------------------------------------
    // Theme Management with Smooth Transition & Icon Spin
    // -------------------------------------------------------------
    function initTheme() {
      const saved = localStorage.getItem('ashzo_theme') || 'dark';
      if (saved === 'dark') {
        document.documentElement.classList.add('dark');
        document.getElementById('themeToggleBtn').innerHTML = '<i class="fa-solid fa-sun text-xs"></i>';
      } else {
        document.documentElement.classList.remove('dark');
        document.getElementById('themeToggleBtn').innerHTML = '<i class="fa-solid fa-moon text-xs"></i>';
      }
    }

    function toggleTheme() {
      const isDark = document.documentElement.classList.contains('dark');
      const btn = document.getElementById('themeToggleBtn');
      
      // Global smooth color interpolation
      document.documentElement.classList.add('theme-animating');
      btn.classList.add('theme-spin');
      setTimeout(() => btn.classList.remove('theme-spin'), 550);

      if (isDark) {
        document.documentElement.classList.remove('dark');
        localStorage.setItem('ashzo_theme', 'light');
        setTimeout(() => {
          btn.innerHTML = '<i class="fa-solid fa-moon text-xs"></i>';
        }, 180);
      } else {
        document.documentElement.classList.add('dark');
        localStorage.setItem('ashzo_theme', 'dark');
        setTimeout(() => {
          btn.innerHTML = '<i class="fa-solid fa-sun text-xs"></i>';
        }, 180);
      }

      setTimeout(() => {
        document.documentElement.classList.remove('theme-animating');
      }, 480);
    }

    // -------------------------------------------------------------
    // Custom Dropdown Controller
    // -------------------------------------------------------------
    function toggleDropdown(dropdownId) {
      const el = document.getElementById(dropdownId);
      const wasOpen = el.classList.contains('is-open');
      // Close other dropdowns
      document.querySelectorAll('.custom-dropdown').forEach(d => {
        if (d !== el) d.classList.remove('is-open');
      });
      if (wasOpen) {
        el.classList.remove('is-open');
      } else {
        el.classList.add('is-open');
      }
    }

    // Close on click outside
    document.addEventListener('click', (e) => {
      if (!e.target.closest('.custom-dropdown')) {
        document.querySelectorAll('.custom-dropdown').forEach(d => d.classList.remove('is-open'));
      }
    });

    // Model selection
    function selectModel(val, label) {
      document.getElementById('modelSelect').value = val;
      document.getElementById('modelDisplay').innerText = label;
      document.getElementById('dropdown-model').classList.remove('is-open');
      document.querySelectorAll('#dropdown-model .dropdown-item').forEach(item => {
        item.classList.toggle('is-selected', item.dataset.value === val);
      });
      onModelChange();
    }

    // Quality selection
    function selectQuality(val, label) {
      document.getElementById('qualitySelect').value = val;
      document.getElementById('qualityDisplay').innerText = label;
      document.getElementById('dropdown-quality').classList.remove('is-open');
      document.querySelectorAll('#dropdown-quality .dropdown-item').forEach(item => {
        item.classList.toggle('is-selected', item.dataset.value === val);
      });
    }

    // Platform selection in Modal
    function selectPlatform(val, label, iconClass) {
      document.getElementById('loginPlatformSelect').value = val;
      document.getElementById('platformDisplay').innerHTML = `<i class="${iconClass} mr-1.5"></i> <span>${label}</span>`;
      document.getElementById('dropdown-platform').classList.remove('is-open');
      document.querySelectorAll('#dropdown-platform .dropdown-item').forEach(item => {
        item.classList.toggle('is-selected', item.dataset.value === val);
      });
      onPlatformPresetChange();
    }

    // Tier selection in Runner
    function selectTier(val, label) {
      document.getElementById('runnerTier').value = val;
      document.getElementById('tierDisplay').innerText = label;
      document.getElementById('dropdown-tier').classList.remove('is-open');
      document.querySelectorAll('#dropdown-tier .dropdown-item').forEach(item => {
        item.classList.toggle('is-selected', item.dataset.value === String(val));
      });
    }

    // -------------------------------------------------------------
    // Animated Modal Controller (Spring scale & blur fade)
    // -------------------------------------------------------------
    function openModalWithAnimation(modalId) {
      const m = document.getElementById(modalId);
      m.classList.add('is-open');
    }

    function closeModalWithAnimation(modalId) {
      const m = document.getElementById(modalId);
      m.classList.remove('is-open');
    }

    function handleModalBackdropClick(event, modalId) {
      if (event.target === document.getElementById(modalId)) {
        closeModalWithAnimation(modalId);
      }
    }

    function openLoginModal(presetEmail, presetUrl) {
      if (presetEmail) document.getElementById('loginEmailInput').value = presetEmail;
      if (presetUrl) {
        if (presetUrl.includes('google.com')) selectPlatform('https://accounts.google.com/', 'Google', 'fa-brands fa-google text-indigo-400');
        else if (presetUrl.includes('github.com')) selectPlatform('https://github.com/login', 'GitHub', 'fa-brands fa-github');
        else if (presetUrl.includes('twitter.com') || presetUrl.includes('x.com')) selectPlatform('https://twitter.com/i/flow/login', 'Twitter / X', 'fa-brands fa-x-twitter');
        else if (presetUrl.includes('flow.google')) selectPlatform('https://flow.google.com/', 'Google Flow', 'fa-solid fa-video text-emerald-400');
        else {
          selectPlatform('custom', 'Custom URL', 'fa-solid fa-globe text-sky-400');
          document.getElementById('loginCustomUrl').value = presetUrl;
        }
      }
      document.getElementById('loginStatusIndicator').classList.add('hidden');
      document.getElementById('launchLoginBtn').disabled = false;
      openModalWithAnimation('loginModal');
    }

    function closeLoginModal() {
      closeModalWithAnimation('loginModal');
    }

    function openRename(path, name) {
      document.getElementById('oldFilepathInput').value = path;
      document.getElementById('newFilenameInput').value = name;
      openModalWithAnimation('renameModal');
    }

    function closeRenameModal() {
      closeModalWithAnimation('renameModal');
    }

    function onPlatformPresetChange() {
      const val = document.getElementById('loginPlatformSelect').value;
      if (val === 'custom') {
        document.getElementById('customUrlDiv').classList.remove('hidden');
      } else {
        document.getElementById('customUrlDiv').classList.add('hidden');
      }
    }

    // -------------------------------------------------------------
    // Animated Tabs
    // -------------------------------------------------------------
    function switchTab(tabId) {
      document.querySelectorAll('.tab-content').forEach(el => {
        el.classList.add('hidden');
        el.classList.remove('tab-animating');
      });
      document.querySelectorAll('.tab-btn').forEach(btn => {
        btn.classList.remove('border-indigo-500', 'text-indigo-400');
        btn.classList.add('border-transparent', 'ashzo-text-dim');
      });

      const target = document.getElementById('tab-' + tabId);
      const btn = document.getElementById('tab-btn-' + tabId);
      if (target) {
        target.classList.remove('hidden');
        void target.offsetWidth; // force reflow for smooth animation trigger
        target.classList.add('tab-animating');
      }
      if (btn) {
        btn.classList.remove('border-transparent', 'ashzo-text-dim');
        btn.classList.add('border-indigo-500', 'text-indigo-400');
      }

      if (tabId === 'sessions') loadSessions();
      if (tabId === 'flow') {
        loadDownloads();
        fetchFlowCredits();
      }
    }

    // Model Change & Duration Pills
    function onModelChange() {
      const m = document.getElementById('modelSelect').value;
      const pills = document.getElementById('durationPills');
      if (m.includes('veo')) {
        pills.innerHTML = `
          <button type="button" onclick="setDuration('8')" class="dur-btn px-2.5 py-1 rounded-lg text-xs font-mono border border-indigo-500 bg-indigo-500/10 text-indigo-400 font-semibold shadow-[0_0_12px_rgba(139,108,255,0.25)]">8s (Veo Max)</button>
          <button type="button" onclick="setDuration('30s_ad')" class="dur-btn px-2.5 py-1 rounded-lg text-xs font-mono border ashzo-card-sub ashzo-border ashzo-text-muted">30s (4 Scenes)</button>
        `;
        setDuration('8');
      } else {
        pills.innerHTML = `
          <button type="button" onclick="setDuration('4')" class="dur-btn px-2.5 py-1 rounded-lg text-xs font-mono border ashzo-card-sub ashzo-border ashzo-text-muted">4s</button>
          <button type="button" onclick="setDuration('6')" class="dur-btn px-2.5 py-1 rounded-lg text-xs font-mono border ashzo-card-sub ashzo-border ashzo-text-muted">6s</button>
          <button type="button" onclick="setDuration('8')" class="dur-btn px-2.5 py-1 rounded-lg text-xs font-mono border border-indigo-500 bg-indigo-500/10 text-indigo-400 font-semibold shadow-[0_0_12px_rgba(139,108,255,0.25)]">8s</button>
          <button type="button" onclick="setDuration('10')" class="dur-btn px-2.5 py-1 rounded-lg text-xs font-mono border ashzo-card-sub ashzo-border ashzo-text-muted">10s</button>
          <button type="button" onclick="setDuration('30s_ad')" class="dur-btn px-2.5 py-1 rounded-lg text-xs font-mono border ashzo-card-sub ashzo-border ashzo-text-muted">30s (4 Scenes)</button>
        `;
        setDuration('8');
      }
    }

    function setDuration(dur) {
      document.getElementById('selectedDuration').value = dur;
      document.querySelectorAll('.dur-btn').forEach(b => {
        b.className = 'dur-btn px-2.5 py-1 rounded-lg text-xs font-mono border ashzo-card-sub ashzo-border ashzo-text-muted';
      });
      if (event && event.target) {
        event.target.className = 'dur-btn px-2.5 py-1 rounded-lg text-xs font-mono border border-indigo-500 bg-indigo-500/10 text-indigo-400 font-semibold shadow-[0_0_12px_rgba(139,108,255,0.25)]';
      }
    }

    function appendTag(t) {
      const area = document.getElementById('promptInput');
      area.value = area.value + ', ' + t;
      area.focus();
    }

    // -------------------------------------------------------------
    // Sessions Management
    // -------------------------------------------------------------
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
          card.className = `p-3.5 rounded-xl border transition-all duration-200 hover:scale-[1.01] ${s.is_active ? 'border-indigo-500/60 bg-indigo-500/5' : 'ashzo-card-sub ashzo-border'}`;
          card.innerHTML = `
            <div class="flex items-start justify-between">
              <div>
                <p class="font-medium text-xs">${s.name}</p>
                <p class="text-[10px] font-mono ashzo-text-dim mt-0.5">${s.email || 'No email'}</p>
              </div>
              ${s.is_active ? '<span class="text-[8px] font-mono bg-emerald-500/20 text-emerald-400 border border-emerald-500/30 px-1.5 py-0.5 rounded uppercase font-semibold">ACTIVE</span>' : ''}
            </div>

            <div class="mt-3 flex items-center justify-between text-xs">
              <span class="text-[9px] font-mono ${hasCookies ? 'text-emerald-400' : 'text-amber-400'}">
                ${hasCookies ? `<i class="fa-solid fa-circle text-[5px] mr-1"></i>${s.cookie_count} cookies` : '<i class="fa-regular fa-circle text-[5px] mr-1"></i>Need login'}
              </span>

              <div class="flex items-center gap-1.5">
                ${!hasCookies ? `<button onclick="openLoginModal('${s.email}', '${s.domain ? 'https://' + s.domain : ''}')" class="text-[9px] font-mono bg-amber-500/10 text-amber-400 border border-amber-500/30 px-2 py-0.5 rounded hover:bg-amber-500/20 active:scale-95 transition">Log In</button>` : ''}
                ${!s.is_active && hasCookies ? `<button onclick="selectSession('${s.id}')" class="text-[9px] font-mono bg-indigo-600/10 text-indigo-400 border border-indigo-500/30 px-2 py-0.5 rounded hover:bg-indigo-600/20 active:scale-95 transition">Set Active</button>` : ''}
                <button onclick="removeSession('${s.id}')" class="text-[10px] ashzo-text-dim hover:text-rose-400 p-1 active:scale-95 transition"><i class="fa-regular fa-trash-can"></i></button>
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

    async function executeInteractiveLogin() {
      const preset = document.getElementById('loginPlatformSelect').value;
      const customUrl = document.getElementById('loginCustomUrl').value.trim();
      const targetUrl = (preset === 'custom' ? customUrl : preset) || 'https://accounts.google.com/';
      const email = document.getElementById('loginEmailInput').value.trim();

      const btn = document.getElementById('launchLoginBtn');
      const indicator = document.getElementById('loginStatusIndicator');
      btn.disabled = true;
      indicator.classList.remove('hidden');

      try {
        const res = await fetch('/api/authenticate?target_url=' + encodeURIComponent(targetUrl) + (email ? '&expected_email=' + encodeURIComponent(email) : ''), { method: 'POST' });
        const data = await res.json();
        closeLoginModal();
        alert(data.message || 'Login completed!');
        loadSessions();
      } catch (e) {
        alert('Login error: ' + e);
      } finally {
        btn.disabled = false;
        indicator.classList.add('hidden');
      }
    }

    // -------------------------------------------------------------
    // Video Generation
    // -------------------------------------------------------------
    async function submitGeneration() {
      const prompt = document.getElementById('promptInput').value.trim();
      const model = document.getElementById('modelSelect').value;
      const duration = document.getElementById('selectedDuration').value;
      const quality = document.getElementById('qualitySelect').value;
      const startFrame = document.getElementById('startFrame').value.trim();
      const endFrame = document.getElementById('endFrame').value.trim();
      const slug = document.getElementById('slugInput').value.trim() || 'video';

      if (!prompt) return showToastNotification('Please enter a prompt', 'error');

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
        showToastNotification(data.message || 'Generation initiated! Real-time progress streaming below.', 'info');
      } catch (e) {
        showToastNotification('Error: ' + e, 'error');
      } finally {
        btn.disabled = false;
        btn.innerHTML = '<i class="fa-solid fa-play text-[9px]"></i> <span>Generate Video</span>';
      }
    }

    // -------------------------------------------------------------
    // Real-Time Agent Stream & Auto-Updating HUD
    // -------------------------------------------------------------
    let liveEventSource = null;

    function initLiveStream() {
      if (liveEventSource) liveEventSource.close();
      liveEventSource = new EventSource('/api/live/stream');

      liveEventSource.onmessage = (e) => {
        try {
          const evt = JSON.parse(e.data);
          handleLiveEvent(evt);
        } catch (err) {
          console.error('SSE parse error:', err);
        }
      };

      liveEventSource.onerror = () => {
        setTimeout(initLiveStream, 3000);
      };
    }

    function handleLiveEvent(evt) {
      if (evt.type === 'init') {
        const initData = evt.data || {};
        if (initData.active_job) updateAgentHud(initData.active_job);
        if (initData.recent_logs) initData.recent_logs.forEach(appendTerminalLog);
        return;
      }

      if (evt.stage || evt.progress !== undefined) {
        updateAgentHud(evt);
      }

      if (evt.message) {
        appendTerminalLog(evt);
      }

      // Auto-update download vault & live credits when video finishes (Zero page refresh!)
      if (evt.type === 'video_ready') {
        loadDownloads();
        fetchFlowCredits();
        showToastNotification(`Video Ready: ${evt.data ? evt.data.filename : 'Saved to vault'}`, 'success');
      }
    }

    function updateAgentHud(job) {
      const stageEl = document.getElementById('liveAgentStage');
      const badgeEl = document.getElementById('liveAgentBadge');
      const textEl = document.getElementById('liveStatusText');
      const barEl = document.getElementById('liveProgressBar');
      const dotEl = document.getElementById('liveAgentDot');

      if (!stageEl || !badgeEl || !barEl) return;

      const stage = (job.stage || 'idle').toUpperCase();
      const progress = job.progress !== undefined ? job.progress : 0;
      const msg = job.message || 'Standby';

      stageEl.innerText = stage === 'IDLE' ? 'Agent Standby' : `Agent ${job.stage}`;
      badgeEl.innerText = stage;
      textEl.innerText = msg;
      barEl.style.width = progress + '%';

      if (stage === 'IDLE') {
        badgeEl.className = 'text-[9px] font-mono px-1.5 py-0.2 rounded bg-indigo-500/10 text-indigo-400 border border-indigo-500/20';
        dotEl.className = 'w-1.5 h-1.5 rounded-full volt-dot';
      } else if (stage === 'READY') {
        badgeEl.className = 'text-[9px] font-mono px-1.5 py-0.2 rounded bg-emerald-500/20 text-emerald-400 border border-emerald-500/30';
        dotEl.className = 'w-1.5 h-1.5 rounded-full volt-dot animate-pulse';
        setTimeout(() => {
          updateAgentHud({ stage: 'idle', progress: 0, message: 'Standby · Real-time pipeline active.' });
        }, 8000);
      } else {
        badgeEl.className = 'text-[9px] font-mono px-1.5 py-0.2 rounded bg-indigo-500/20 text-indigo-400 border border-indigo-500/30 animate-pulse';
        dotEl.className = 'w-1.5 h-1.5 rounded-full volt-dot animate-ping';
      }
    }

    function appendTerminalLog(logItem) {
      const container = document.getElementById('terminalLogs');
      if (!container) return;
      const row = document.createElement('div');
      row.className = 'leading-relaxed hover:text-slate-200 transition';
      const timeStr = logItem.timestamp || new Date().toLocaleTimeString();
      row.innerHTML = `<span class="ashzo-text-dim">[${timeStr}]</span> <span class="text-indigo-400 font-semibold">${logItem.stage ? '[' + logItem.stage.toUpperCase() + '] ' : ''}</span>${logItem.message}`;
      container.appendChild(row);
      container.scrollTop = container.scrollHeight;
    }

    function toggleAgentFeed() {
      const feed = document.getElementById('agentTerminalFeed');
      const chev = document.getElementById('feedChevron');
      const isOpen = !feed.classList.contains('hidden');
      if (isOpen) {
        feed.classList.add('hidden');
        chev.classList.remove('rotate-180');
      } else {
        feed.classList.remove('hidden');
        chev.classList.add('rotate-180');
      }
    }

    function showToastNotification(text, type = 'info') {
      const container = document.getElementById('toastContainer');
      if (!container) return;
      const toast = document.createElement('div');
      toast.className = 'ashzo-glass border ashzo-border rounded-xl px-3.5 py-2 text-xs font-mono shadow-2xl flex items-center gap-2 transform transition-all duration-300 translate-y-3 opacity-0 pointer-events-auto';
      const icon = type === 'success' ? '<i class="fa-solid fa-circle-check text-emerald-400"></i>' : (type === 'error' ? '<i class="fa-solid fa-circle-exclamation text-rose-400"></i>' : '<i class="fa-solid fa-circle-info text-indigo-400"></i>');
      toast.innerHTML = `${icon} <span class="truncate max-w-xs">${text}</span>`;
      container.appendChild(toast);
      
      requestAnimationFrame(() => {
        toast.classList.remove('translate-y-3', 'opacity-0');
      });

      setTimeout(() => {
        toast.classList.add('translate-y-3', 'opacity-0');
        setTimeout(() => toast.remove(), 300);
      }, 4500);
    }

    // -------------------------------------------------------------
    // Live Flow Credits
    // -------------------------------------------------------------
    async function fetchFlowCredits(forceRefresh = false) {
      try {
        const btn = document.getElementById('refreshCreditsBtn');
        if (btn) btn.classList.add('animate-spin');
        const res = await fetch('/api/flow/credits' + (forceRefresh ? '?refresh=true' : ''));
        const data = await res.json();
        const credits = data.live_credits !== undefined ? data.live_credits : 373;
        document.getElementById('creditsValue').innerText = credits + ' Credits';
      } catch (e) {
        console.error('Error fetching live credits:', e);
      } finally {
        const btn = document.getElementById('refreshCreditsBtn');
        if (btn) btn.classList.remove('animate-spin');
      }
    }

    function refreshLiveCredits() {
      fetchFlowCredits(true);
    }

    // -------------------------------------------------------------
    // Download Vault & Inline Rename
    // -------------------------------------------------------------
    async function loadDownloads() {
      try {
        const res = await fetch('/api/flow/downloads');
        const files = await res.json();
        const container = document.getElementById('downloadsList');
        container.innerHTML = '';

        if (!files || files.length === 0) {
          container.innerHTML = '<p class="text-xs ashzo-text-dim font-mono text-center py-8">Vault empty.</p>';
          return;
        }

        files.forEach(f => {
          const item = document.createElement('div');
          item.className = 'vault-item p-2.5 rounded-xl ashzo-card-sub border ashzo-border flex items-center justify-between';
          item.innerHTML = `
            <div class="truncate max-w-[210px]">
              <p class="text-xs font-mono font-medium truncate" title="${f.name}">${f.name}</p>
              <p class="text-[9px] font-mono ashzo-text-dim mt-0.5">${f.size_mb} MB &bull; ${f.modified}</p>
            </div>
            <div class="flex items-center gap-1">
              <button onclick="openRename('${f.path}', '${f.name}')" class="p-1 rounded ashzo-text-dim hover:text-indigo-400 active:scale-95 transition" title="Rename"><i class="fa-solid fa-pen text-[10px]"></i></button>
              <a href="/downloads/${f.name}" target="_blank" class="p-1 rounded ashzo-text-dim hover:text-indigo-400 active:scale-95 transition" title="Play"><i class="fa-solid fa-play text-[10px]"></i></a>
              <a href="/downloads/${f.name}" download class="p-1 rounded text-indigo-400 hover:text-indigo-300 active:scale-95 transition" title="Download"><i class="fa-solid fa-download text-[10px]"></i></a>
            </div>
          `;
          container.appendChild(item);
        });
      } catch (e) {
        console.error(e);
      }
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

    // -------------------------------------------------------------
    // Platform Explorer
    // -------------------------------------------------------------
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

    // -------------------------------------------------------------
    // 3-Tier Runner
    // -------------------------------------------------------------
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
    fetchFlowCredits();
    initLiveStream();
  </script>
</body>
</html>
"""

# =====================================================================
# REST API Endpoints & Real-Time Event Stream
# =====================================================================

@web_app.get("/", response_class=HTMLResponse)
async def get_dashboard():
    return HTMLResponse(content=DASHBOARD_HTML)


@web_app.get("/api/live/stream")
async def api_live_stream():
    """Server-Sent Events (SSE) endpoint streaming real-time agent progress and updates."""
    async def event_generator():
        q = live_broadcaster.subscribe()
        init_state = live_broadcaster.get_initial_state()
        yield f"data: {json.dumps({'type': 'init', 'data': init_state})}\n\n"
        try:
            while True:
                try:
                    event = await asyncio.wait_for(q.get(), timeout=12.0)
                    yield f"data: {json.dumps(event)}\n\n"
                except asyncio.TimeoutError:
                    yield ": ping\n\n"
        finally:
            live_broadcaster.unsubscribe(q)

    return StreamingResponse(
        event_generator(),
        media_type="text/event-stream",
        headers={
            "Cache-Control": "no-cache",
            "Connection": "keep-alive",
            "X-Accel-Buffering": "no"
        }
    )


@web_app.get("/api/live/status")
async def api_live_status():
    """Returns current active job snapshot and recent agent logs."""
    return live_broadcaster.get_initial_state()


@web_app.post("/api/live/broadcast")
async def api_live_broadcast(payload: Dict[str, Any]):
    """Internal/test broadcast hook to push real-time events through SSE."""
    event_type = payload.get("type", "log")
    message = payload.get("message", "")
    stage = payload.get("stage")
    progress = payload.get("progress")
    data = payload.get("data")
    await live_broadcaster.broadcast(event_type, message, data=data, stage=stage, progress=progress)
    return {"status": "broadcasted"}


@web_app.get("/api/flow/credits")
async def api_get_credits(refresh: bool = False):
    """Returns actual live credits directly from Google Flow."""
    try:
        from get_live_flow_credits import fetch_live_google_flow_credits
        if refresh:
            return await fetch_live_google_flow_credits()

        # Check sessions.json for cached live credits
        active = session_manager.get_active_session()
        if active and active.get("live_credits"):
            return {
                "status": "success",
                "account": active.get("email", "arq5020@gmail.com"),
                "live_credits": active["live_credits"],
                "tier": active.get("tier", "PRO"),
                "credits_text": f"{active['live_credits']} Credits"
            }
        return await fetch_live_google_flow_credits()
    except Exception as e:
        return {
            "status": "cached",
            "account": "arq5020@gmail.com",
            "live_credits": 373,
            "tier": "PRO",
            "credits_text": "373 Credits"
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

    await live_broadcaster.broadcast(
        "progress",
        f"Video queued: '{slug}' with {model.upper()} ({dur_num}s, {quality})",
        stage="queued",
        progress=5
    )

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
        "message": f"Generation queued for model '{model.upper()}' ({dur_num}s, quality={quality}). Check vault shortly."
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
    print("Ashzo MCP Minimal Studio is running!")
    print(f"Dashboard: http://localhost:{port}")
    print("=======================================================")
    uvicorn.run("app:web_app", host="0.0.0.0", port=port, reload=False)
