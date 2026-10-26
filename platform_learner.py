"""
Universal Autonomous Platform Explorer & Skill Compiler for Universal-Web-MCP.
Thoroughly explores ANY website, maps out navigation, UI inputs, tools, modes,
and background APIs, and compiles a comprehensive 'Platform Skill' profile.
Emits live progress to the dashboard: 'getting ready on dashboard until the ai agent is fully done with learning'.
"""

import os
import sys
import json
import time
import asyncio
import logging
from pathlib import Path
from urllib.parse import urlparse
from typing import Dict, List, Any, Optional
from playwright.async_api import async_playwright
from interceptor import is_noise_url, infer_json_schema, summarize_payload

logger = logging.getLogger("UniversalWebMCP.PlatformLearner")

BASE_DIR = Path(__file__).resolve().parent
SKILLS_DIR = BASE_DIR / "platform_skills"
SKILLS_DIR.mkdir(parents=True, exist_ok=True)
AUTH_STATE_FILE = BASE_DIR / "flow_auth_state.json"


class PlatformLearner:
    """Explores any website and compiles a complete operational Skill profile."""

    def __init__(self):
        self.current_job: Dict[str, Any] = {
            "state": "IDLE",
            "progress": 0,
            "status_text": "Ready",
            "url": None,
            "domain": None,
            "skill_file": None,
            "started_at": None,
            "completed_at": None
        }

    def get_status(self) -> Dict[str, Any]:
        """Returns the live learning state for the dashboard."""
        return dict(self.current_job)

    async def learn_platform(self, target_url: str, session_auth_file: Optional[Path] = None) -> Dict[str, Any]:
        """
        Executes a 5-phase deep exploration of the platform:
        1. Initialize & attach network listener
        2. Crawl navigation & routes
        3. Inspect UI elements, modes & tools
        4. Sniff background API schemas
        5. Compile permanent Platform Skill profile
        """
        parsed = urlparse(target_url)
        domain = parsed.netloc or "unknown_domain"
        auth_file = session_auth_file or (AUTH_STATE_FILE if AUTH_STATE_FILE.exists() else None)

        self.current_job = {
            "state": "INITIALIZING",
            "progress": 10,
            "status_text": f"Connecting to {domain} and loading authenticated session...",
            "url": target_url,
            "domain": domain,
            "skill_file": None,
            "started_at": time.time(),
            "completed_at": None
        }

        captured_routes = []
        captured_nav = []
        captured_inputs = []
        captured_buttons = []
        page_title = ""

        try:
            async with async_playwright() as p:
                browser = await p.chromium.launch(
                    headless=True,
                    args=["--disable-blink-features=AutomationControlled", "--no-sandbox"]
                )
                context_args = {
                    "user_agent": "Mozilla/5.0 (Windows NT 10.0; Win64; x64) AppleWebKit/537.36 (KHTML, like Gecko) Chrome/126.0.0.0 Safari/537.36",
                    "viewport": {"width": 1440, "height": 900}
                }
                if auth_file and os.path.exists(auth_file):
                    context_args["storage_state"] = str(auth_file)

                context = await browser.new_context(**context_args)
                page = await context.new_page()

                # Attach network sniffer
                async def handle_resp(resp):
                    if not is_noise_url(resp.url):
                        ct = resp.headers.get("content-type", "").lower()
                        if "json" in ct:
                            try:
                                body = await resp.json()
                                captured_routes.append({
                                    "url": resp.url.split("?")[0],
                                    "method": resp.request.method,
                                    "status": resp.status,
                                    "schema": infer_json_schema(body),
                                    "sample": summarize_payload(body, 300)
                                })
                            except Exception:
                                pass

                page.on("response", handle_resp)

                # Phase 2: Crawl Navigation (25%)
                self.current_job["state"] = "CRAWLING_NAVIGATION"
                self.current_job["progress"] = 25
                self.current_job["status_text"] = "Mapping platform navigation, sub-routes, and views..."
                await page.goto(target_url, wait_until="domcontentloaded", timeout=25000)
                await page.wait_for_timeout(4000)
                page_title = await page.title()

                links = await page.eval_on_selector_all("a[href]", "els => els.map(e => ({ text: e.innerText.trim(), href: e.href }))")
                seen_links = set()
                for link in links:
                    if link["text"] and link["href"] not in seen_links and domain in link["href"]:
                        seen_links.add(link["href"])
                        captured_nav.append(link)

                # Phase 3: Inspect Interactive Elements & Modes (50%)
                self.current_job["state"] = "INSPECTING_UI"
                self.current_job["progress"] = 50
                self.current_job["status_text"] = "Analyzing interactive inputs, modes, tools, and prompt controls..."

                # Find buttons
                raw_buttons = await page.eval_on_selector_all("button", "els => els.map(e => e.innerText.trim()).filter(Boolean)")
                seen_btn = set()
                for b in raw_buttons:
                    clean_b = b.replace("\n", " ").strip()
                    if clean_b and clean_b not in seen_btn:
                        seen_btn.add(clean_b)
                        captured_buttons.append(clean_b)

                # Find inputs & textareas
                raw_inputs = await page.eval_on_selector_all(
                    "input, textarea, [contenteditable='true']",
                    """els => els.map(e => ({
                        tag: e.tagName,
                        placeholder: e.placeholder || '',
                        aria: e.getAttribute('aria-label') || '',
                        className: e.className || ''
                    }))"""
                )
                for inp in raw_inputs:
                    if inp["aria"] or inp["placeholder"] or "ProseMirror" in inp["className"]:
                        captured_inputs.append(inp)

                # Phase 4: Sniff APIs & Trigger Lazy Endpoints (75%)
                self.current_job["state"] = "SNIFFING_APIS"
                self.current_job["progress"] = 75
                self.current_job["status_text"] = "Sniffing first-party APIs and reverse-engineering schemas..."
                await page.evaluate("window.scrollTo(0, 1000)")
                await page.wait_for_timeout(3000)

                await browser.close()

            # Phase 5: Compile Platform Skill (90%)
            self.current_job["state"] = "COMPILING_SKILL"
            self.current_job["progress"] = 90
            self.current_job["status_text"] = f"Compiling permanent Platform Skill profile for {domain}..."

            clean_domain = domain.replace(":", "_").replace(".", "_")
            skill_json_path = SKILLS_DIR / f"{clean_domain}_skill.json"
            skill_md_path = SKILLS_DIR / f"{clean_domain}_SKILL.md"

            skill_data = {
                "domain": domain,
                "url": target_url,
                "title": page_title,
                "learned_at": time.strftime("%Y-%m-%d %H:%M:%S"),
                "navigation_routes": captured_nav[:20],
                "interactive_inputs": captured_inputs[:10],
                "controls_and_buttons": captured_buttons[:30],
                "intercepted_apis": captured_routes[:15]
            }

            with open(skill_json_path, "w", encoding="utf-8") as f:
                json.dump(skill_data, f, indent=2)

            # Generate beautiful Markdown Skill Guide
            md_content = f"""# Platform Skill: {domain} 🌐

Compiled automatically by **Universal-Web-MCP Autonomous Explorer**.
This document serves as the operational handbook for any AI model or user automating **{domain}**.

---

## 📌 Executive Overview
- **Domain:** `{domain}`
- **Page Title:** {page_title}
- **Entrypoint URL:** {target_url}
- **Compiled At:** {skill_data['learned_at']}

---

## 🧭 Navigation & Core Sub-Routes
| Route / Section | Target URL |
| :--- | :--- |
"""
            for nav in captured_nav[:12]:
                md_content += f"| {nav['text'][:30]} | `{nav['href']}` |\n"

            md_content += """
---

## 🎛️ Primary Controls & Action Buttons
"""
            for btn in captured_buttons[:20]:
                md_content += f"- `{btn}`\n"

            md_content += """
---

## 📝 Input Fields & Prompt Interfaces
"""
            for inp in captured_inputs[:8]:
                desc = inp['aria'] or inp['placeholder'] or inp['className']
                md_content += f"- `<{inp['tag']}>` — Description / Aria: **{desc}**\n"

            md_content += f"""
---

## ⚡ Intercepted First-Party APIs ({len(captured_routes)} Discovered)
"""
            for api in captured_routes[:8]:
                md_content += f"- **{api['method']}** `{api['url']}` (Status {api['status']})\n"

            md_content += """
---

## 🚀 Autonomous Execution Instructions
1. Use `universal_request(url)` for sub-200ms Fast Path API calls.
2. If UI action is required, target the inputs and controls documented above.
"""

            with open(skill_md_path, "w", encoding="utf-8") as f:
                f.write(md_content)

            # Complete!
            self.current_job = {
                "state": "READY",
                "progress": 100,
                "status_text": f"BOOM! Platform Skill for {domain} is fully compiled and ready to automate!",
                "url": target_url,
                "domain": domain,
                "skill_file": str(skill_md_path),
                "started_at": self.current_job["started_at"],
                "completed_at": time.time(),
                "summary": {
                    "routes_count": len(captured_nav),
                    "buttons_count": len(captured_buttons),
                    "inputs_count": len(captured_inputs),
                    "apis_count": len(captured_routes)
                }
            }
            logger.info(f"Platform Skill compiled for {domain} -> {skill_md_path}")
            return self.current_job

        except Exception as e:
            logger.error(f"Error exploring platform {target_url}: {e}")
            self.current_job = {
                "state": "ERROR",
                "progress": 0,
                "status_text": f"Platform exploration error: {str(e)}",
                "url": target_url,
                "domain": domain,
                "skill_file": None,
                "started_at": self.current_job["started_at"],
                "completed_at": time.time()
            }
            return self.current_job


platform_learner = PlatformLearner()
