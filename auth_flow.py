"""
Interactive Authentication Helper for Universal-Web-MCP.
Opens a visible Google Chrome window on the user's screen, allows the user
to log into any Google account (e.g. arq5020@gmail.com, arq5158@gmail.com),
extracts the actual logged-in email and 20+ session cookies, and saves
the complete storage state permanently in SessionManager and sessions.json.
"""

import os
import sys
import json
import asyncio
import logging
from pathlib import Path
from typing import Optional, Dict, Any
from playwright.async_api import async_playwright
from session_manager import session_manager

logger = logging.getLogger("UniversalWebMCP.AuthFlow")

BASE_DIR = Path(__file__).resolve().parent
AUTH_STATE_FILE = BASE_DIR / "flow_auth_state.json"
SESSION_COOKIES_FILE = BASE_DIR / "session_cookies.json"


async def run_interactive_login(
    target_url: str = "https://flow.google.com/",
    timeout_seconds: int = 180,
    session_name: Optional[str] = None,
    expected_email: Optional[str] = None
) -> Dict[str, Any]:
    """
    Launches a visible Google Chrome window on the user's screen.
    Waits for the user to complete Google Sign-in and reach the authenticated Flow workspace.
    Properly detects true auth cookies (SID, __Secure-1PSID) and extracts the real email.
    """
    print("\n=======================================================")
    print("[AUTH] Universal-Web-MCP Interactive Chrome Login")
    print(f"Opening window for: {target_url}")
    print("Please log into your Google Account in the browser window.")
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
                current_url = page.url
                cookies = await context.cookies()

                # Check for REAL Google auth cookies (SID, __Secure-1PSID, HSID, SSID)
                # NOT visitor cookies like NID!
                auth_cookies = [
                    c for c in cookies
                    if c["name"] in ["SID", "__Secure-1PSID", "__Secure-3PSID", "HSID", "SSID"] and len(c.get("value", "")) > 15
                ]

                # Ensure user is past login redirect and NOT on unauthenticated landing page
                is_on_landing = "flow.google.com/about" in current_url
                is_on_accounts = "accounts.google.com" in current_url

                if len(auth_cookies) >= 2 and not is_on_accounts and not is_on_landing:
                    print(f"[AUTH] Detected active authentication cookies on: {current_url}")
                    await page.wait_for_timeout(3000)

                    # Extract the real logged-in email from the page DOM
                    try:
                        detected_email = await page.evaluate('''() => {
                            // 1. Check aria-labels for email addresses
                            for (const el of document.querySelectorAll('[aria-label]')) {
                                const aria = el.getAttribute('aria-label') || '';
                                const m = aria.match(/([a-zA-Z0-9._%+-]+@[a-zA-Z0-9.-]+\\.[a-zA-Z]{2,})/);
                                if (m) return m[1];
                            }
                            // 2. Check profile avatar or account menu buttons
                            const accEl = document.querySelector('a[href*="SignOutOptions"], [aria-label*="Google Account"]');
                            if (accEl) {
                                const m = (accEl.getAttribute('aria-label') || '').match(/([a-zA-Z0-9._%+-]+@[a-zA-Z0-9.-]+\\.[a-zA-Z]{2,})/);
                                if (m) return m[1];
                            }
                            // 3. Search document body text
                            const m = document.body.innerText.match(/([a-zA-Z0-9._%+-]+@[a-zA-Z0-9.-]+\\.[a-zA-Z]{2,})/);
                            if (m) return m[1];
                            return null;
                        }''')
                        if detected_email:
                            extracted_email = detected_email
                            print(f"[AUTH] Extracted account email from page: {extracted_email}")
                    except Exception as e:
                        print(f"[AUTH] Email extraction notice: {e}")

                    logged_in = True
                    break

                await asyncio.sleep(2)

            if not logged_in:
                await browser.close()
                return {
                    "status": "timeout",
                    "message": f"Login timed out after {timeout_seconds}s. Please complete Google sign-in in the Chrome window."
                }

            # Save full storage state
            await context.storage_state(path=str(AUTH_STATE_FILE))
            print(f"[AUTH] Saved complete storage state to: {AUTH_STATE_FILE}")

            # Extract cookies dict
            all_cookies = await context.cookies()
            cookies_dict = {c["name"]: c["value"] for c in all_cookies}
            with open(SESSION_COOKIES_FILE, "w", encoding="utf-8") as f:
                json.dump(cookies_dict, f, indent=2)

            # Finalize email & session name
            final_email = extracted_email or expected_email or "google_user@gmail.com"
            final_name = session_name or f"Google Flow ({final_email})"

            storage_state_data = None
            try:
                with open(AUTH_STATE_FILE, "r", encoding="utf-8") as f:
                    storage_state_data = json.load(f)
            except Exception:
                pass

            sess_record = session_manager.add_session(
                name=final_name,
                email=final_email,
                domain="flow.google.com",
                cookies_dict=cookies_dict,
                storage_state_data=storage_state_data,
                set_active=True
            )

            title = await page.title()
            final_url = page.url
            await browser.close()

            return {
                "status": "success",
                "session_id": sess_record["id"],
                "session_name": sess_record["name"],
                "email": final_email,
                "url": final_url,
                "title": title,
                "cookies_captured": len(cookies_dict),
                "message": f"Login successful for {final_email}! Captured {len(cookies_dict)} session cookies. Permanently saved to Session Manager."
            }

    except Exception as e:
        logger.error(f"Authentication flow error: {e}")
        return {
            "status": "error",
            "message": f"Interactive authentication error: {str(e)}"
        }


def main():
    target = sys.argv[1] if len(sys.argv) > 1 else "https://flow.google.com/"
    email = sys.argv[2] if len(sys.argv) > 2 else None
    res = asyncio.run(run_interactive_login(target_url=target, expected_email=email))
    print("\nResult:", json.dumps(res, indent=2))


if __name__ == "__main__":
    main()
