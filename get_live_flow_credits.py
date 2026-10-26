"""
Reads the real Google Flow credit balance of the signed-in account.

It opens Flow in a hidden browser that carries the same sign-in as the Ashzo
Browser (so your visible window is never disturbed), opens the account menu and
reads "N Google Flow credits". When the balance can't be read, it says so; it
never invents a number.
"""

from __future__ import annotations

import json
import logging
import re
import time
from pathlib import Path
from typing import Any, Dict, Optional

from ashzo_settings import load_settings

logger = logging.getLogger("AshzoMCP.Credits")

BASE_DIR = Path(__file__).resolve().parent
AUTH_STATE_FILE = BASE_DIR / "flow_auth_state.json"


async def _storage_state() -> Optional[Dict[str, Any]]:
    try:
        from browser_hub import hub
        if hub.is_connected() or await hub._port_alive():
            return await hub.storage_state()
    except Exception as e:
        logger.debug("hub storage state unavailable: %s", e)
    if AUTH_STATE_FILE.exists():
        try:
            return json.loads(AUTH_STATE_FILE.read_text(encoding="utf-8"))
        except Exception:
            return None
    return None


async def fetch_live_google_flow_credits(project_url: Optional[str] = None) -> Dict[str, Any]:
    state = await _storage_state()
    if not state or not state.get("cookies"):
        return {"status": "signed_out", "message": "Connect your Google account to read Flow credits."}
    url = project_url or load_settings().get("flow_project_url") or "https://flow.google.com/"
    try:
        from playwright.async_api import async_playwright
        async with async_playwright() as p:
            browser = await p.chromium.launch(headless=True)
            context = await browser.new_context(storage_state=state, viewport={"width": 1440, "height": 900})
            page = await context.new_page()
            await page.goto(url, wait_until="domcontentloaded", timeout=30000)
            await page.wait_for_timeout(3500)
            if "accounts.google.com" in page.url:
                await browser.close()
                return {"status": "signed_out", "message": "Your Google sign-in expired. Connect again."}

            user_btn = page.locator("div.header-user-button, [aria-label='Account details'], [aria-label*='Google Account']").first
            text = ""
            if await user_btn.count() > 0:
                await user_btn.click()
                await page.wait_for_timeout(1500)
                texts = await page.eval_on_selector_all(
                    ".cdk-overlay-pane, [role='dialog'], [role='menu']", "els => els.map(e => e.innerText)")
                text = "\n".join(texts)
            if not text:
                text = await page.evaluate("() => document.body.innerText")
            await browser.close()

        email_m = re.search(r"([a-zA-Z0-9._%+-]+@[a-zA-Z0-9.-]+\.[a-zA-Z]{2,})", text)
        credits_m = re.search(r"([\d,]+)\s+(?:Google\s+)?Flow credits", text, re.IGNORECASE) or \
            re.search(r"([\d,]+)\s+credits", text, re.IGNORECASE)
        tier_m = re.search(r"\b(Ultra|Pro|Plus|Free)\b", text)
        if not credits_m:
            return {"status": "unknown", "message": "Flow opened, but the credit balance wasn't shown.",
                    "account": email_m.group(1) if email_m else None}
        credits = int(credits_m.group(1).replace(",", ""))
        result = {
            "status": "success",
            "account": email_m.group(1) if email_m else None,
            "live_credits": credits,
            "tier": tier_m.group(1).upper() if tier_m else None,
            "credits_text": f"{credits} credits",
            "checked_at": int(time.time() * 1000),
        }
        try:
            from session_manager import session_manager
            active = session_manager.get_active_session()
            if active:
                active["live_credits"] = credits
                active["tier"] = result["tier"]
                active["credits_checked_at"] = result["checked_at"]
                if result["account"] and not active.get("email"):
                    active["email"] = result["account"]
                session_manager.save()
        except Exception:
            pass
        return result
    except Exception as e:
        logger.warning("Credit check failed: %s", e)
        return {"status": "error", "message": f"Couldn't read credits: {e}"}


if __name__ == "__main__":
    import asyncio
    import sys
    sys.stderr.write(json.dumps(asyncio.run(fetch_live_google_flow_credits()), indent=2) + "\n")
