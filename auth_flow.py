"""
Interactive Authentication Helper for Universal-Web-MCP.
Opens a visible browser window, allows the user to log into Google / Flow once,
and saves the full persistent session (cookies, tokens, and storage state) to flow_auth_state.json
and the permanent SessionManager.
"""

import os
import sys
import json
import asyncio
import logging
from pathlib import Path
from playwright.async_api import async_playwright
from session_manager import session_manager

logger = logging.getLogger("UniversalWebMCP.AuthFlow")

BASE_DIR = Path(__file__).resolve().parent
AUTH_STATE_FILE = BASE_DIR / "flow_auth_state.json"
SESSION_COOKIES_FILE = BASE_DIR / "session_cookies.json"


async def run_interactive_login(
    target_url: str = "https://flow.google.com/",
    timeout_seconds: int = 120,
    session_name: str = "Google Flow Session"
) -> dict:
    """
    Launches a visible Google Chrome window on the user's screen.
    Waits for the user to log in and reach the target site.
    Once authenticated, extracts and saves the full session state permanently.
    """
    print("\n=======================================================")
    print(f"[AUTH] Universal-Web-MCP Interactive Login")
    print(f"Opening Google Chrome window for: {target_url}")
    print(f"Please log in with your Google Account in the window.")
    print(f"Waiting up to {timeout_seconds} seconds for login completion...")
    print("=======================================================\n")

    try:
        async with async_playwright() as p:
            browser = await p.chromium.launch(
                channel="chrome",
                headless=False,
                args=["--no-first-run", "--no-default-browser-check"]
            )
            context = await browser.new_context()
            page = await context.new_page()

            await page.goto(target_url)

            logged_in = False
            start_time = asyncio.get_event_loop().time()

            while (asyncio.get_event_loop().time() - start_time) < timeout_seconds:
                current_url = page.url
                # Check if user has navigated past login into flow project or dashboard
                if ("flow.google.com" in current_url or target_url in current_url) and "accounts.google.com" not in current_url:
                    cookies = await context.cookies()
                    google_auth_cookies = [
                        c for c in cookies
                        if any(token in c["name"] for token in ["SID", "NID", "flow", "session"])
                    ]
                    if len(google_auth_cookies) >= 1:
                        print(f"[AUTH] Detected active session on: {current_url}")
                        await page.wait_for_timeout(3000)
                        logged_in = True
                        break
                await asyncio.sleep(2)

            if not logged_in:
                await browser.close()
                return {
                    "status": "timeout",
                    "message": f"Login timed out after {timeout_seconds}s. Please click '1-Click Google Login' again to retry."
                }

            # Save complete storage state (cookies + local storage + tokens)
            await context.storage_state(path=str(AUTH_STATE_FILE))
            print(f"[AUTH] Saved complete storage state to: {AUTH_STATE_FILE}")

            # Extract cookies dict
            all_cookies = await context.cookies()
            cookies_dict = {c["name"]: c["value"] for c in all_cookies}
            with open(SESSION_COOKIES_FILE, "w", encoding="utf-8") as f:
                json.dump(cookies_dict, f, indent=2)

            # Register in SessionManager for permanent multi-session retention
            account_email = "authenticated_user"
            for c in all_cookies:
                if c.get("name") == "ACCOUNT_CHOOSER":
                    account_email = c.get("value", "")[:25]

            storage_state_data = None
            try:
                with open(AUTH_STATE_FILE, "r", encoding="utf-8") as f:
                    storage_state_data = json.load(f)
            except Exception:
                pass

            sess_record = session_manager.add_session(
                name=session_name,
                email=account_email,
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
                "url": final_url,
                "title": title,
                "cookies_captured": len(cookies_dict),
                "auth_file": str(AUTH_STATE_FILE),
                "message": f"Login successful! Captured {len(cookies_dict)} session cookies. Permanently saved to Session Manager."
            }

    except Exception as e:
        logger.error(f"Authentication flow error: {e}")
        return {
            "status": "error",
            "message": f"Interactive authentication error: {str(e)}"
        }


def main():
    target = sys.argv[1] if len(sys.argv) > 1 else "https://flow.google.com/"
    res = asyncio.run(run_interactive_login(target_url=target))
    print("\nResult:", json.dumps(res, indent=2))


if __name__ == "__main__":
    main()
