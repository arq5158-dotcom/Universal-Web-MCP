"""
Universal-Web-MCP Web Dashboard & SSE Server.
Combines:
1. Official Model Context Protocol (MCP) Server-Sent Events (SSE) server for remote AI clients.
2. An interactive, real-time Web Dashboard for testing 3-Tier Hybrid Routing,
   browsing learned API schemas, and managing Chrome profile cookies.
"""

import os
import sys
import json
import time
import asyncio
from typing import Optional, Dict, Any
from pathlib import Path

from fastapi import FastAPI, Request
from fastapi.responses import HTMLResponse, JSONResponse
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

# Initialize FastAPI app
web_app = FastAPI(
    title="Universal-Web-MCP Dashboard",
    description="3-Tier Hybrid Routing Web Bridge & Live Testing Dashboard",
    version="1.0.0"
)

web_app.add_middleware(
    CORSMiddleware,
    allow_origins=["*"],
    allow_credentials=True,
    allow_methods=["*"],
    allow_headers=["*"],
)

# Mount the MCP SSE application at /mcp
try:
    mcp_sse_app = mcp.sse_app()
    web_app.mount("/mcp", mcp_sse_app)
except Exception as e:
    print(f"Notice: MCP SSE mount: {e}")


DASHBOARD_HTML = """<!DOCTYPE html>
<html lang="en" class="dark">
<head>
  <meta charset="UTF-8">
  <meta name="viewport" content="width=device-width, initial-scale=1.0">
  <title>Universal-Web-MCP | 3-Tier Routing Dashboard</title>
  <script src="https://cdn.tailwindcss.com"></script>
  <script>
    tailwind.config = {
      darkMode: 'class',
      theme: {
        extend: {
          colors: {
            brand: { 500: '#3b82f6', 600: '#2563eb', 700: '#1d4ed8' },
            fast: { 500: '#10b981', 600: '#059669' },
            sniff: { 500: '#8b5cf6', 600: '#7c3aed' },
            fall: { 500: '#f59e0b', 600: '#d97706' }
          }
        }
      }
    }
  </script>
  <link rel="stylesheet" href="https://cdnjs.cloudflare.com/ajax/libs/font-awesome/6.4.0/css/all.min.css">
  <style>
    pre code { font-family: ui-monospace, SFMono-Regular, Menlo, Monaco, Consolas, monospace; font-size: 0.85rem; }
  </style>
</head>
<body class="bg-slate-950 text-slate-100 min-h-screen flex flex-col font-sans">

  <!-- Header -->
  <header class="border-b border-slate-800 bg-slate-900/80 backdrop-blur sticky top-0 z-50">
    <div class="max-w-7xl mx-auto px-4 py-3 flex items-center justify-between">
      <div class="flex items-center space-x-3">
        <div class="w-10 h-10 rounded-xl bg-gradient-to-tr from-blue-600 via-indigo-600 to-purple-600 flex items-center justify-center shadow-lg shadow-blue-500/20">
          <i class="fa-solid fa-bolt text-white text-lg"></i>
        </div>
        <div>
          <h1 class="text-lg font-bold tracking-tight flex items-center gap-2">
            Universal-Web-MCP
            <span class="text-xs bg-blue-500/20 text-blue-400 border border-blue-500/30 px-2 py-0.5 rounded-full font-mono">v1.0 Production</span>
          </h1>
          <p class="text-xs text-slate-400">3-Tier Hybrid Routing Web Bridge (<200ms Fast Path &bull; CDP Sniffer &bull; DOM Fallback)</p>
        </div>
      </div>
      <div class="flex items-center space-x-3">
        <button onclick="startInteractiveAuth()" class="text-xs bg-blue-600 hover:bg-blue-500 text-white font-medium px-3 py-1.5 rounded-lg flex items-center gap-2 transition shadow">
          <i class="fa-solid fa-key"></i>
          <span>1-Click Google Login</span>
        </button>
        <button onclick="syncCookies()" class="text-xs bg-slate-800 hover:bg-slate-700 text-slate-200 border border-slate-700 px-3 py-1.5 rounded-lg flex items-center gap-2 transition">
          <i class="fa-brands fa-chrome text-amber-400"></i>
          <span>Sync Chrome (arq5020)</span>
        </button>
        <span class="w-2.5 h-2.5 rounded-full bg-emerald-500 animate-pulse" title="Server Live"></span>
        <span class="text-xs font-mono text-emerald-400">ONLINE</span>
      </div>
    </div>
  </header>

  <!-- Main Container -->
  <main class="max-w-7xl mx-auto px-4 py-6 flex-1 w-full grid grid-cols-1 lg:grid-cols-12 gap-6">

    <!-- Left Column: URL Tester & Tiers (7 cols) -->
    <div class="lg:col-span-7 space-y-6">
      
      <!-- Input Panel -->
      <div class="bg-slate-900 border border-slate-800 rounded-2xl p-5 shadow-xl">
        <h2 class="text-sm font-semibold text-slate-200 mb-3 flex items-center gap-2">
          <i class="fa-solid fa-globe text-blue-400"></i> Execute Universal Request
        </h2>
        
        <div class="flex flex-col sm:flex-row gap-2">
          <div class="relative flex-1">
            <input 
              type="url" 
              id="targetUrl" 
              value="https://flow.google.com/" 
              placeholder="https://example.com" 
              class="w-full bg-slate-950 border border-slate-700 rounded-xl px-4 py-2.5 text-sm focus:outline-none focus:border-blue-500 text-slate-100 placeholder-slate-500 font-mono"
            />
          </div>
          <select id="forceTier" class="bg-slate-950 border border-slate-700 text-sm rounded-xl px-3 py-2 text-slate-300 focus:outline-none focus:border-blue-500">
            <option value="auto">Auto 3-Tier</option>
            <option value="1">Tier 1: Fast Path (<200ms)</option>
            <option value="2">Tier 2: CDP Sniffer</option>
            <option value="3">Tier 3: DOM Fallback</option>
          </select>
          <button 
            id="runBtn" 
            onclick="executeRequest()" 
            class="bg-blue-600 hover:bg-blue-500 text-white font-medium px-5 py-2.5 rounded-xl text-sm flex items-center justify-center gap-2 transition shadow-lg shadow-blue-600/30 disabled:opacity-50"
          >
            <i class="fa-solid fa-play text-xs"></i> Run Request
          </button>
        </div>

        <!-- Tier Explanation Bar -->
        <div class="grid grid-cols-3 gap-3 mt-4 text-xs font-mono">
          <div class="bg-slate-950/60 border border-slate-800/80 rounded-xl p-2.5 flex items-center gap-2">
            <span class="w-2 h-2 rounded-full bg-emerald-400"></span>
            <div>
              <div class="font-semibold text-emerald-400">Tier 1: Fast Path</div>
              <div class="text-[10px] text-slate-400">Replay API &lt;200ms</div>
            </div>
          </div>
          <div class="bg-slate-950/60 border border-slate-800/80 rounded-xl p-2.5 flex items-center gap-2">
            <span class="w-2 h-2 rounded-full bg-purple-400"></span>
            <div>
              <div class="font-semibold text-purple-400">Tier 2: Auto-Discover</div>
              <div class="text-[10px] text-slate-400">CDP JSON Sniffer</div>
            </div>
          </div>
          <div class="bg-slate-950/60 border border-slate-800/80 rounded-xl p-2.5 flex items-center gap-2">
            <span class="w-2 h-2 rounded-full bg-amber-400"></span>
            <div>
              <div class="font-semibold text-amber-400">Tier 3: DOM Fallback</div>
              <div class="text-[10px] text-slate-400">&lt;1000 tokens Markdown</div>
            </div>
          </div>
        </div>
      </div>

      <!-- Execution Results -->
      <div class="bg-slate-900 border border-slate-800 rounded-2xl p-5 shadow-xl min-h-[400px] flex flex-col">
        <div class="flex items-center justify-between pb-3 border-b border-slate-800">
          <div class="flex items-center gap-3">
            <span id="tierBadge" class="hidden text-xs font-semibold px-2.5 py-1 rounded-full uppercase tracking-wider font-mono"></span>
            <span id="latencyBadge" class="hidden text-xs text-slate-400 font-mono flex items-center gap-1">
              <i class="fa-regular fa-clock"></i> <span id="latencyVal">0</span>ms
            </span>
          </div>
          <div id="loader" class="hidden flex items-center gap-2 text-xs text-blue-400 font-mono">
            <i class="fa-solid fa-circle-notch fa-spin"></i> Sniffing &amp; Routing...
          </div>
        </div>

        <div id="resultContent" class="flex-1 mt-4">
          <div id="placeholder" class="h-64 flex flex-col items-center justify-center text-slate-500 text-sm">
            <i class="fa-solid fa-network-wired text-4xl mb-3 text-slate-700"></i>
            <p>Enter any URL above to test 3-Tier Hybrid Routing</p>
            <p class="text-xs text-slate-600 mt-1">Try https://flow.google.com/ to inspect live AI models and APIs</p>
          </div>
          <pre id="codeView" class="hidden bg-slate-950 p-4 rounded-xl border border-slate-800/80 overflow-x-auto max-h-[500px] text-slate-200"><code></code></pre>
        </div>
      </div>

    </div>

    <!-- Right Column: Cached Routes & Chrome Profile (5 cols) -->
    <div class="lg:col-span-5 space-y-6">

      <!-- Chrome Profile Status -->
      <div class="bg-slate-900 border border-slate-800 rounded-2xl p-5 shadow-xl">
        <h2 class="text-sm font-semibold text-slate-200 mb-2 flex items-center justify-between">
          <span class="flex items-center gap-2">
            <i class="fa-brands fa-google text-amber-400"></i> Local Chrome Session
          </span>
          <span class="text-[11px] text-slate-400 font-mono" id="profileTag">Profile 1</span>
        </h2>
        <div class="bg-slate-950 border border-slate-800 rounded-xl p-3 text-xs space-y-1.5 font-mono">
          <div class="flex justify-between text-slate-400">
            <span>Target Account:</span>
            <span class="text-slate-200 font-semibold">arq5020@gmail.com</span>
          </div>
          <div class="flex justify-between text-slate-400">
            <span>Cookies Synced:</span>
            <span class="text-emerald-400 font-semibold" id="cookieCount">3 active</span>
          </div>
          <div class="flex justify-between text-slate-400">
            <span>Bot Bypass:</span>
            <span class="text-blue-400">Pre-authenticated</span>
          </div>
        </div>
      </div>

      <!-- Learned Routes List -->
      <div class="bg-slate-900 border border-slate-800 rounded-2xl p-5 shadow-xl flex flex-col max-h-[560px]">
        <div class="flex items-center justify-between mb-3">
          <h2 class="text-sm font-semibold text-slate-200 flex items-center gap-2">
            <i class="fa-solid fa-database text-purple-400"></i> Learned Routes Cache
          </h2>
          <button onclick="loadRoutes()" class="text-xs text-slate-400 hover:text-slate-200">
            <i class="fa-solid fa-arrows-rotate"></i>
          </button>
        </div>
        <div id="routesList" class="overflow-y-auto space-y-2 pr-1 flex-1 text-xs">
          <!-- Routes injected dynamically -->
        </div>
      </div>

    </div>

  </main>

  <!-- Footer -->
  <footer class="border-t border-slate-800 bg-slate-900/50 py-3 text-center text-xs text-slate-500 font-mono">
    Universal-Web-MCP &bull; Model Context Protocol &bull; FastMCP Bridge
  </footer>

  <script>
    async function loadRoutes() {
      try {
        const res = await fetch('/api/routes');
        const routes = await res.json();
        const list = document.getElementById('routesList');
        list.innerHTML = '';
        if (routes.length === 0) {
          list.innerHTML = '<div class="text-slate-500 py-4 text-center">No cached routes yet. Run a request to discover APIs.</div>';
          return;
        }
        routes.forEach(r => {
          const card = document.createElement('div');
          card.className = 'bg-slate-950 border border-slate-800 rounded-xl p-3 hover:border-slate-700 transition cursor-pointer';
          card.onclick = () => {
            document.getElementById('targetUrl').value = r.url;
            document.getElementById('forceTier').value = '1';
            executeRequest();
          };
          const methodClass = r.method === 'GET' ? 'text-emerald-400 bg-emerald-500/10' : 'text-blue-400 bg-blue-500/10';
          card.innerHTML = `
            <div class="flex items-center justify-between mb-1">
              <span class="px-1.5 py-0.5 rounded text-[10px] font-mono font-bold ${methodClass}">${r.method}</span>
              <span class="text-[10px] text-slate-500 truncate max-w-[180px]">${r.domain}</span>
            </div>
            <div class="text-slate-300 font-mono truncate text-[11px]">${r.url}</div>
          `;
          list.appendChild(card);
        });
      } catch (err) {
        console.error(err);
      }
    }

    async function startInteractiveAuth() {
      alert("Launching interactive Google Login window. Please sign in with arq5020@gmail.com in the Chrome window that opens. The MCP will automatically capture your session!");
      try {
        const res = await fetch('/api/authenticate', { method: 'POST' });
        const data = await res.json();
        alert(data.message || "Authentication complete!");
        loadRoutes();
      } catch (err) {
        alert("Authentication error: " + err);
      }
    }

    async function syncCookies() {
      try {
        const res = await fetch('/api/sync-cookies');
        const data = await res.json();
        document.getElementById('cookieCount').innerText = `${data.total_cookies_cached} active`;
        document.getElementById('profileTag').innerText = data.resolved_profile;
        alert(`Synced ${data.total_cookies_cached} session cookies from ${data.resolved_profile} (${data.target})`);
      } catch (err) {
        alert('Failed to sync cookies: ' + err);
      }
    }

    async function executeRequest() {
      const url = document.getElementById('targetUrl').value;
      const tierSelect = document.getElementById('forceTier').value;
      const btn = document.getElementById('runBtn');
      const loader = document.getElementById('loader');
      const placeholder = document.getElementById('placeholder');
      const codeView = document.getElementById('codeView');
      const tierBadge = document.getElementById('tierBadge');
      const latencyBadge = document.getElementById('latencyBadge');
      const latencyVal = document.getElementById('latencyVal');

      if (!url) return;

      btn.disabled = true;
      loader.classList.remove('hidden');
      tierBadge.classList.add('hidden');
      latencyBadge.classList.add('hidden');

      try {
        const forceTier = tierSelect === 'auto' ? null : parseInt(tierSelect);
        const res = await fetch('/api/request', {
          method: 'POST',
          headers: { 'Content-Type': 'application/json' },
          body: JSON.stringify({ url: url, force_tier: forceTier })
        });
        const data = await res.json();

        placeholder.classList.add('hidden');
        codeView.classList.remove('hidden');
        codeView.querySelector('code').textContent = JSON.stringify(data, null, 2);

        // Tier styling
        tierBadge.classList.remove('hidden');
        tierBadge.innerText = data.tier || 'Universal Request';
        if ((data.tier || '').includes('Tier 1')) {
          tierBadge.className = 'text-xs font-semibold px-2.5 py-1 rounded-full uppercase tracking-wider font-mono bg-emerald-500/20 text-emerald-400 border border-emerald-500/30';
        } else if ((data.tier || '').includes('Tier 2')) {
          tierBadge.className = 'text-xs font-semibold px-2.5 py-1 rounded-full uppercase tracking-wider font-mono bg-purple-500/20 text-purple-400 border border-purple-500/30';
        } else {
          tierBadge.className = 'text-xs font-semibold px-2.5 py-1 rounded-full uppercase tracking-wider font-mono bg-amber-500/20 text-amber-400 border border-amber-500/30';
        }

        latencyBadge.classList.remove('hidden');
        latencyVal.innerText = data.latency_ms || 0;

        // Refresh routes
        loadRoutes();

      } catch (err) {
        alert('Request failed: ' + err);
      } finally {
        btn.disabled = false;
        loader.classList.add('hidden');
      }
    }

    // Initial load
    loadRoutes();
  </script>
</body>
</html>
"""

@web_app.post("/api/authenticate")
async def api_authenticate(target_url: str = "https://flow.google.com/"):
    """Launches visible Chrome window for one-time Google Login and session capture."""
    from auth_flow import run_interactive_login
    return await run_interactive_login(target_url=target_url)


# Web UI Routes
@web_app.get("/", response_class=HTMLResponse)
async def get_dashboard():
    """Serves the interactive 3-Tier Web Dashboard."""
    return HTMLResponse(content=DASHBOARD_HTML)


# REST API Endpoints for Dashboard & Remote Clients
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


@web_app.get("/api/sync-cookies")
async def api_sync_cookies(profile: str = "arq5020@gmail.com"):
    """Syncs session cookies from local Chrome profile."""
    return sync_chrome_session(profile_name_or_email=profile)


@web_app.post("/api/clear-cache")
async def api_clear_cache(domain: Optional[str] = None):
    """Purges cached routes."""
    return clear_cache(domain=domain)


if __name__ == "__main__":
    port = int(os.environ.get("PORT", 8000))
    print("=======================================================")
    print("Universal-Web-MCP Dashboard & Server is running!")
    print(f"Web UI Dashboard: http://localhost:{port}")
    print(f"MCP SSE Endpoint: http://localhost:{port}/mcp/sse")
    print("=======================================================")
    uvicorn.run("app:web_app", host="0.0.0.0", port=port, reload=False)
