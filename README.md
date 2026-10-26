# Ashzo MCP 🌐⚡

[![Model Context Protocol](https://img.shields.io/badge/MCP-2.0-blue.svg)](https://modelcontextprotocol.io/)
[![Playwright](https://img.shields.io/badge/Playwright-Chromium-green.svg)](https://playwright.dev/)
[![Python](https://img.shields.io/badge/Python-3.10%2B-blue.svg)](https://python.org/)
[![License: MIT](https://img.shields.io/badge/License-MIT-yellow.svg)](LICENSE)

A production-ready Python Model Context Protocol (MCP) server named **Ashzo MCP** (FastMCP Bridge: `Universal-Web-Bridge`) that empowers AI agents (like **Claude Desktop**, **Cursor**, **Windsurf**, or **OpenAI Agent SDK**) to interact with **ANY** website at sub-second speeds.

Instead of slow, fragile visual browser automation (like clicking coordinates or parsing massive DOM trees), Universal-Web-MCP utilizes an intelligent **3-Tier Hybrid Routing Architecture**.

---

## 🏛️ 3-Tier Hybrid Routing Architecture

```
                    ┌───────────────────────────────┐
                    │  AI Agent (Claude / Cursor)   │
                    └──────────────┬────────────────┘
                                   │ universal_request(url)
                                   ▼
        ┌───────────────────────────────────────────────────────┐
        │        Tier 1: Fast Path (< 200ms)                    │
        │  Replays cached first-party JSON/GraphQL API requests │
        │  using stored session cookies & keep-alive HTTP.      │
        └──────────────┬────────────────────────▲───────────────┘
                       │ Cache Miss             │ Compiles &
                       │ or 401/403             │ Caches Routes
                       ▼                        │
        ┌───────────────────────────────────────┴───────────────┐
        │        Tier 2: Auto-Discovery Path (CDP)             │
        │  Spins up Playwright CDP network sniffer. Filters ads │
        │  and analytics, captures clean JSON endpoints,        │
        │  and infers schema automatically.                     │
        └──────────────┬────────────────────────────────────────┘
                       │ No JSON API on page
                       ▼
        ┌───────────────────────────────────────────────────────┐
        │        Tier 3: Universal Fallback                     │
        │  Extracts clean Markdown / Accessibility Tree from    │
        │  the DOM, strictly bounded under 1,000 tokens.        │
        └───────────────────────────────────────────────────────┘
```

1. **Tier 1 (Fast Path):** Replays learned first-party JSON/GraphQL API requests directly using stored session cookies (`httpx` keep-alive client, latency **< 200ms**).
2. **Tier 2 (Auto-Discovery Path):** If an API route is unknown, spins up Playwright via Chrome DevTools Protocol (CDP), listens to background network XHR/Fetch traffic, filters out ads/analytics, extracts clean JSON schemas, and compiles them into permanent MCP tools on the fly.
3. **Tier 3 (Universal Fallback):** If no JSON API exists, falls back to extracting clean Markdown or Accessibility Tree snapshots from the live browser DOM.

---

## 🚀 Key Features

- ⚡ **Sub-Second Speed:** Learned endpoints bypass browser rendering entirely, achieving 100-200ms response times.
- 🍪 **Persistent Multi-Session Profile Manager:** Stores login profiles permanently in `sessions.json`. Sessions survive server restarts and machine reboots with complete Add, Remove, and Active Profile switching.
- 🧠 **Autonomous Platform Skill Engine:** Explores ANY website, discovers navigation routes, interactive inputs, and first-party APIs, and generates operational `<domain>_SKILL.md` profiles with live dashboard progress.
- 🎨 **Google Flow AI Creative Studio:** Deeply researched knowledge base ([GOOGLE_FLOW_SKILL.md](GOOGLE_FLOW_SKILL.md)) for Google Veo (8s max, 4K photorealism) vs Omni 1.1 Flash (10s max), Agent Mode vs Direct Mode, `@` references, and automated 30s ad storyboards.
- 🛡️ **Noise & Ad Filtering:** Intelligently filters out tracking beacons, analytics (`google-analytics`, `doubleclick`, `datadog`, `sentry`, etc.), and static assets.
- 🪙 **Strict Token Efficiency (< 1,000 tokens):** Summarizes massive payloads and strips DOM bloat (`<script>`, `<style>`, `<svg>`, tracking pixels) to keep LLM context clean and affordable.
- 🔒 **Security First:** Automatically masks sensitive authorization tokens and cookies in logs and state files.
- 💎 **Awwwards-Inspired Luxury Dashboard:** Real-time dark obsidian UI (`http://localhost:8000`) with live 3-tier testing playground, session switcher, autonomous platform explorer, and media download vault.

---

## 📦 Installation & Setup

### 1. Clone the Repository
```bash
git clone https://github.com/arq5158-dotcom/Universal-Web-MCP.git
cd Universal-Web-MCP
```

### 2. Create Virtual Environment & Install Dependencies
Using `uv` (recommended) or standard `venv`:
```bash
# Using uv:
uv venv .venv
uv pip install -p .venv/Scripts/python.exe -r requirements.txt

# Or standard python:
python -m venv .venv
source .venv/bin/activate  # On Windows: .venv\Scripts\activate
pip install -r requirements.txt
```

### 3. Install Playwright Chromium
```bash
playwright install chromium
```

---

## ⚙️ Claude Desktop Configuration

Add `Universal-Web-MCP` to your `claude_desktop_config.json`:

- **Windows:** `%APPDATA%\Claude\claude_desktop_config.json`
- **macOS:** `~/Library/Application Support/Claude/claude_desktop_config.json`

```json
{
  "mcpServers": {
    "universal-web": {
      "command": "C:\\Users\\creat\\Documents\\antigravity\\quirky-pasteur\\Universal-Web-MCP\\.venv\\Scripts\\python.exe",
      "args": [
        "C:\\Users\\creat\\Documents\\antigravity\\quirky-pasteur\\Universal-Web-MCP\\server.py"
      ],
      "env": {
        "PYTHONUNBUFFERED": "1"
      }
    }
  }
}
```

---

## 🛠️ Available MCP Tools

| Tool | Parameters | Description |
| :--- | :--- | :--- |
| `universal_request` | `url`, `method`, `params`, `body`, `force_tier` | Master tool with 3-Tier hybrid routing. Auto-escalates from Tier 1 -> Tier 2 -> Tier 3. |
| `discover_routes` | `url`, `interactive_action` | Explicitly triggers Tier 2 CDP sniffer on target page to map out background APIs. |
| `get_page_content` | `url`, `mode` (`markdown`/`accessibility`/`both`) | Explicitly extracts token-efficient DOM / Accessibility Tree snapshot (<1000 tokens). |
| `sync_chrome_session` | `profile_name_or_email` | Syncs session cookies from local Chrome profile (e.g., `arq5020@gmail.com`). |
| `list_learned_routes` | `domain` | Lists all cached routes, methods, and JSON schemas in `learned_routes.json`. |
| `clear_cache` | `domain` | Purges cached routes or session state. |

---

## 🎬 Google Flow AI Video Automation Pipeline

Universal-Web-MCP includes an automated batch video production engine for **Google Flow** (supporting **Google Veo** and **Omni 1.1 Flash** models).

- 📦 **Batch Generation (10–20 Videos):** Pass a list of concepts, and the engine breaks each 30s video into 4 scenes, submits prompts, and polls rendering.
- 🎯 **Strict Model Enforcement:** Adheres strictly to the requested model:
  - `model="veo"`: 8-second cinematic photorealism with 35mm lens camera instructions.
  - `model="omni_flash"`: 10-second rapid high-throughput generation.
- 💾 **Automatic Local Downloading:** Intercepts download streams and saves `.mp4` files directly to `downloads/flow_production/<video_title>/`.
- 📖 **Full Guide & Documentation:** See [GOOGLE_FLOW_AUTOMATION_GUIDE.md](GOOGLE_FLOW_AUTOMATION_GUIDE.md) for full prompting formulas and batch scripts.

---

## 🧪 Testing

Run the comprehensive automated test suite (includes a live test on `https://flow.google.com/`):

```bash
python test_server.py
```

### Test Output Highlights:
```text
[PASS] Cookie sync & masking test passed.
[PASS] Schema inference and summarization passed.
[PASS] Noise filtering verified.
[PASS] Fallback DOM cleaner passed.
--- Test 5: Live Test on https://flow.google.com/ ---
Captured clean API route: GET https://www.gstatic.com/glue/cookienotificationbar/config/2a.json
Captured clean API route: POST https://ogads-pa.clients6.google.com/$rpc/google.internal...
--- Test 6: Tier 1 Fast Path Replay ---
Tier 1 Result: status=200, latency=140ms
[ALL TESTS PASSED SUCCESSFULLY!]
```

---

## 🔒 Security & Privacy

- **Header Masking:** All headers containing `Authorization`, `Cookie`, `x-api-key`, etc., are automatically masked before logging (`ya29...7890`).
- **Local Cache:** Session state and learned routes are stored strictly locally in `session_cookies.json` and `learned_routes.json` and are ignored in version control (`.gitignore`).

---

## 📄 License

MIT License. See [LICENSE](LICENSE) for details.
