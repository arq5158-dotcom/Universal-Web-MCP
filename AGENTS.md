# Ashzo MCP: rules for AI agents

Read this before changing or running anything in this repo (Cursor, Antigravity, Claude Code, Codex and others).

## 1. First run on a computer: create the app icon (must do)

1. Set up and create the icon:
   - **Windows:** run `CREATE_DESKTOP_ICON.bat` (creates `.venv`, installs requirements and Playwright Chromium, then the icon).
   - **macOS / Linux:**
     ```bash
     python3 -m venv .venv && .venv/bin/pip install -r requirements.txt
     .venv/bin/python -m playwright install chromium
     .venv/bin/python create_desktop_shortcut.py
     ```
   - If the environment already exists, `python create_desktop_shortcut.py` is enough.
2. **Tell the user**, with the path the script printed:
   > I added an **Ashzo MCP** icon to your desktop (`<path>`). Double-click it any time: it starts Ashzo MCP on this computer and opens the dashboard in your browser at http://localhost:8000.
3. If creating the icon fails, say why. `START_ASHZO.bat` (Windows) or `python launch_ashzo.py` does the same thing.

The icon runs `launch_ashzo.py`: it starts `app.py` in the background if it isn't running, waits until it answers, then opens the default browser (Chrome, Edge, Firefox, ...). Server output goes to `logs/ashzo_server.log`.

## 2. Doing work for the user

- **Use the MCP tools, not screenshots or web control.** One `flow_generate_video` call plus a few `flow_job_status(wait_seconds=45)` calls costs about 2k tokens per video. Driving a browser by screenshots costs 50-100x more.
- **Google Flow:** follow [GOOGLE_FLOW_SKILL.md](GOOGLE_FLOW_SKILL.md). Sections 0 and 0.5 are mandatory: generate visibly through the Ashzo Browser, report real credits only, never bypass reCAPTCHA or anti-bot checks.
- **Recreating any video:** follow [VIDEO_RECREATION_SKILL.md](VIDEO_RECREATION_SKILL.md) every time. Start with the `study_video` tool and look at every image it produces before writing prompts.
- **Other websites:** use `universal_request`. It tries the Fast Path first, then learns the site's API, then reads the page as text.
- **Never fake anything:** credits, emails, plans, "success". If you couldn't read or do something, say so.

## 3. How the app works (keep it this way)

- **Everything is live.** Any state the user should see is pushed through `live_events.live_broadcaster` (`broadcast` / `emit`) and shows up on `/api/live/stream` without a page refresh. The MCP stdio process forwards its events to the dashboard (`/api/live/ingest`). Never build a feature that needs F5.
- **Long work returns at once and reports progress as live events.** See `auth_flow.start_login` and `FlowJobRunner`. Never block an HTTP request until a person finishes something.
- **Signed-in browsing goes through `browser_hub.hub`**, the "Ashzo Browser": a real Chrome window the user can watch, mirrored into Live View. Don't launch a separate hidden Playwright Chromium for Google sign-in; Google refuses those.
- **Errors reach the user.** Every failure ends in an `error` / `cancelled` / `timeout` event with a plain-language message. Spinners must always stop.

## 4. Changing the dashboard (`web/`)

- Plain HTML/JS, no framework. CSS is compiled Tailwind in `web/vendor/tailwind.css`, plus `web/styles.css`. After adding or changing Tailwind classes, run `npm install && npm run build:css`. The app uses no CDNs, so it also works offline.
- **Dropdowns, menus and popovers are overlays.** Use `position: absolute` inside a `position: relative` wrapper, with a z-index; never put them in the page flow. Opening one must not move anything else. Reuse `.custom-dropdown` and `.popover-anchor`.
- **Spinners:** `<span class="spin-ring"></span>` (a square box rotating around its centre). Never use `fa-spinner` with `animate-spin`: it wobbles.
- **Theme:** light / dark / system through `setTheme()` in `app.js` (a circular reveal from the button, same as the Ashzo site). Colours come from CSS variables in `styles.css`. Check both themes.
- **Inline `onclick` names** must not match DOM methods (`togglePopover`, `remove`, `click`, `focus`, ...): the element's own method runs instead.
- After a visible change:
  - run `python scripts/verify_dashboard.py` (no layout shift, spinner geometry, live updates, no console errors);
  - refresh the README pictures with `python scripts/capture_screenshots.py`.

## 5. Security

- The server listens on `127.0.0.1` only and refuses cross-site requests. Keep `local_only_guard` in `app.py`.
- Cookies are sent only to their own site: `cookie_manager.get_cookie_header(host)`.
- Never print, log or commit cookies, tokens or sessions. They're listed in `.gitignore`.
- In MCP stdio mode nothing may be printed to stdout (it breaks the protocol). Log to stderr with `logging`.
