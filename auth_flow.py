"""
Universal Interactive Authentication Helper for Ashzo MCP.
Opens a visible Google Chrome window on the user's screen for ANY website
(Google, GitHub, Stripe, Twitter, Notion, Flow, or custom platforms).
Detects authentication, captures storage state, tokens, and cookies,
and saves the profile permanently in SessionManager and sessions.json.
"""

import os
import sys
import json
import asyncio
import logging
from urllib.parse import urlparse
from pathlib import Path
from typing import Optional, Dict, Any
from playwright.async_api import async_playwright
from session_manager import session_manager

logger = logging.getLogger("AshzoMCP.AuthFlow")

BASE_DIR = Path(__file__).resolve().parent
AUTH_STATE_FILE = BASE_DIR / "flow_auth_state.json"
SESSION_COOKIES_FILE = BASE_DIR / "session_cookies.json"


async def run_interactive_login(
    target_url: str = "https://accounts.google.com/",
    timeout_seconds: int = 180,
    session_name: Optional[str] = None,
    expected_email: Optional[str] = None
) -> Dict[str, Any]:
    """
    Launches a visible Chrome window for ANY target platform.
    Waits for the user to log in, captures the complete session storage state,
    and registers it permanently into the SessionManager.
    """
    parsed = urlparse(target_url)
    domain = parsed.netloc or "web"

    print("\n=======================================================")
    print("[AUTH] Ashzo MCP Universal Platform Login")
    print(f"Target URL: {target_url} (Domain: {domain})")
    print(f"Account: {expected_email or 'Custom'}")
    print(f"Please log into your account in the browser window.")
    print(f"Waiting up to {timeout_seconds}s for login completion...")
    print("=======================================================\n")

    try:
        async with async_playwright() as p:
            browser = await p.chromium.launch(
                channel="chrome",
                headless=False,
                args=["--no-first-run", "--no-default-browser-check"]
            )
            context = await browser.new_context(
                viewport={"width": 1440, "height": 900}
            )
            page = await context.new_page()

            await page.goto(target_url)

            logged_in = False
            start_time = asyncio.get_event_loop().time()
            extracted_email = expected_email

            while (asyncio.get_event_loop().time() - start_time) < timeout_seconds:
                # If user closed the page manually after logging in
                if page.is_closed():
                    print("[AUTH] Browser page was closed by user. Capturing current state...")
                    logged_in = True
                    break

                current_url = page.url
                cookies = await context.cookies()

                # 1. Google Authentication Detection
                if "google" in domain.lower() or "google" in current_url:
                    auth_cookies = [
                        c for c in cookies
                        if c["name"] in ["SID", "__Secure-1PSID", "__Secure-3PSID", "HSID", "SSID"] and len(c.get("value", "")) > 15
                    ]
                    is_on_landing = "flow.google.com/about" in current_url
                    is_on_signin = "accounts.google.com/v3/signin" in current_url or "accounts.google.com/signin" in current_url

                    if len(auth_cookies) >= 2 and not is_on_signin and not is_on_landing:
                        print(f"[AUTH] Google authentication detected on: {current_url}")
                        await page.wait_for_timeout(3000)
                        logged_in = True
                        break

                # 2. GitHub Authentication Detection
                elif "github.com" in domain.lower():
                    has_session = any(c["name"] == "user_session" for c in cookies)
                    if has_session and "/login" not in current_url:
                        print(f"[AUTH] GitHub authentication detected on: {current_url}")
                        logged_in = True
                        break

                # 3. Generic Universal Platform Detection
                else:
                    # Look for session/auth token cookies and navigation past /login /signin
                    generic_auth = [
                        c for c in cookies
                        if any(token in c["name"].lower() for token in ["session", "auth", "token", "jwt", "sid"])
                    ]
                    is_login_page = any(kw in current_url.lower() for kw in ["/login", "/signin", "/auth/login"])
                    if len(generic_auth) >= 1 and not is_login_page and len(cookies) >= 3:
                        print(f"[AUTH] Session cookies captured on: {current_url}")
                        await page.wait_for_timeout(2000)
                        logged_in = True
                        break

                await asyncio.sleep(2)

            if not logged_in and not page.is_closed():
                await browser.close()
                return {
                    "status": "timeout",
                    "message": f"Login timed out after {timeout_seconds}s for {domain}. Please try again."
                }

            # Attempt to extract email if page is still open
            if not page.is_closed():
                try:
                    detected_email = await page.evaluate('''() => {
                        for (const el of document.querySelectorAll('[aria-label]')) {
                            const aria = el.getAttribute('aria-label') || '';
                            const m = aria.match(/([a-zA-Z0-9._%+-]+@[a-zA-Z0-9.-]+\\.[a-zA-Z]{2,})/);
                            if (m) return m[1];
                        }
                        const accEl = document.querySelector('a[href*="SignOutOptions"], [aria-label*="Google Account"], [aria-label*="profile" i]');
                        if (accEl) {
                            const m = (accEl.getAttribute('aria-label') || '').match(/([a-zA-Z0-9._%+-]+@[a-zA-Z0-9.-]+\\.[a-zA-Z]{2,})/);
                            if (m) return m[1];
                        }
                        return null;
                    }''')
                    if detected_email:
                        extracted_email = detected_email
                        print(f"[AUTH] Extracted account identity: {extracted_email}")
                except Exception:
                    pass

            # Save complete storage state
            await context.storage_state(path=str(AUTH_STATE_FILE))
            all_cookies = await context.cookies()
            cookies_dict = {c["name"]: c["value"] for c in all_cookies}
            with open(SESSION_COOKIES_FILE, "w", encoding="utf-8") as f:
                json.dump(cookies_dict, f, indent=2)

            final_email = extracted_email or expected_email or f"user@{domain}"
            final_name = session_name or f"{domain.capitalize()} ({final_email})"

            storage_state_data = None
            try:
                with open(AUTH_STATE_FILE, "r", encoding="utf-8") as f:
                    storage_state_data = json.load(f)
            except Exception:
                pass

            sess_record = session_manager.add_session(
                name=final_name,
                email=final_email,
                domain=domain,
                cookies_dict=cookies_dict,
                storage_state_data=storage_state_data,
                set_active=True
            )

            if not page.is_closed():
                await browser.close()

            print(f"[AUTH] Saved session profile: {sess_record['id']} ({len(cookies_dict)} cookies)")

            return {
                "status": "success",
                "session_id": sess_record["id"],
                "session_name": sess_record["name"],
                "email": final_email,
                "domain": domain,
                "cookies_captured": len(cookies_dict),
                "message": f"Successfully connected {final_email} on {domain}! Captured {len(cookies_dict)} session cookies."
            }

    except Exception as e:
        logger.error(f"Authentication error: {e}")
        return {
            "status": "error",
            "message": f"Authentication error: {str(e)}"
        }


def main():
    target = sys.argv[1] if len(sys.argv) > 1 else "https://accounts.google.com/"
    email = sys.argv[2] if len(sys.argv) > 2 else None
    res = asyncio.run(run_interactive_login(target_url=target, expected_email=email))
    print("\nResult:", json.dumps(res, indent=2))


if __name__ == "__main__":
    main()
