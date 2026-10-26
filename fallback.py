"""
Universal Fallback Reader for Universal-Web-MCP (Tier 3).
Extracts clean Accessibility Tree snapshots or cleans raw DOM/HTML into
token-efficient Markdown using BeautifulSoup and html2text.
Enforces strict token limits (< 1,000 tokens) to prevent LLM context bloat.
"""

import re
import logging
from typing import Dict, Any, Optional
from bs4 import BeautifulSoup
import html2text
from playwright.async_api import Page, async_playwright

logger = logging.getLogger("UniversalWebMCP.Fallback")

# Target token budget: ~1000 tokens =~ 3500-4000 characters
MAX_OUTPUT_CHARS = 3800


def clean_html_to_markdown(html_content: str, max_chars: int = MAX_OUTPUT_CHARS) -> str:
    """
    Cleans raw HTML by stripping scripts, styles, inline SVGs, tracker tags,
    and converts the core readable content to structured Markdown.
    """
    if not html_content:
        return "*Empty HTML body*"

    try:
        soup = BeautifulSoup(html_content, "html.parser")

        # Strip noisy, non-content elements
        for element in soup(["script", "style", "svg", "noscript", "iframe", "canvas"]):
            element.decompose()

        # Remove elements with inline base64 images or tracking pixels
        for img in soup.find_all("img"):
            src = img.get("src", "")
            if src.startswith("data:image") or "pixel" in src.lower() or "1x1" in src:
                img.decompose()
            elif len(src) > 150:
                img["src"] = src[:150] + "..."

        # Prioritize main content if landmark exists
        main_tag = soup.find("main") or soup.find("article") or soup.find(id=re.compile(r"content|main", re.I))
        content_soup = main_tag if main_tag else soup.body or soup

        # Configure html2text
        h2t = html2text.HTML2Text()
        h2t.ignore_links = False
        h2t.ignore_images = False
        h2t.ignore_emphasis = False
        h2t.body_width = 0  # No hard wrapping
        h2t.skip_internal_links = True

        raw_md = h2t.handle(str(content_soup))

        # Collapse excessive newlines and whitespace
        cleaned_md = re.sub(r"\n{3,}", "\n\n", raw_md).strip()

        # Enforce token budget (< 1000 tokens)
        if len(cleaned_md) > max_chars:
            head = cleaned_md[:max_chars - 200]
            truncated = (
                f"{head}\n\n"
                f"... [Content truncated to preserve token efficiency. "
                f"Total length: {len(cleaned_md)} chars. Use specific sub-path or targeted query for more details.]"
            )
            return truncated

        return cleaned_md if cleaned_md else "*No readable content extracted*"

    except Exception as e:
        logger.error(f"HTML to Markdown conversion failed: {e}")
        return f"*Error parsing DOM content: {e}*"


async def extract_accessibility_tree(page: Page, max_chars: int = MAX_OUTPUT_CHARS) -> str:
    """
    Extracts an accessibility tree snapshot from the live browser page.
    Supports modern Playwright aria_snapshot, legacy accessibility.snapshot,
    or CDP full accessibility tree.
    """
    # Strategy 1: Modern Playwright aria_snapshot() (Playwright 1.48+)
    try:
        body_locator = page.locator("body")
        if hasattr(body_locator, "aria_snapshot"):
            aria_text = await body_locator.aria_snapshot()
            if aria_text and len(aria_text.strip()) > 0:
                if len(aria_text) > max_chars:
                    return aria_text[:max_chars - 150] + "\n\n... [Aria tree truncated to <1000 tokens]"
                return aria_text
    except Exception as e:
        logger.debug(f"aria_snapshot attempt failed: {e}")

    # Strategy 2: Legacy page.accessibility.snapshot()
    try:
        if hasattr(page, "accessibility") and hasattr(page.accessibility, "snapshot"):
            ax_dict = await page.accessibility.snapshot()
            if ax_dict:
                import json
                raw_json = json.dumps(ax_dict, indent=2)
                if len(raw_json) > max_chars:
                    return raw_json[:max_chars - 150] + "\n... [Snapshot truncated]"
                return raw_json
    except Exception as e:
        logger.debug(f"page.accessibility.snapshot attempt failed: {e}")

    # Strategy 3: CDP Accessibility
    try:
        cdp = await page.context.new_cdp_session(page)
        tree = await cdp.send("Accessibility.getFullAXTree")
        nodes = tree.get("nodes", [])
        lines = []
        for node in nodes[:60]:
            role = node.get("role", {}).get("value", "")
            name = node.get("name", {}).get("value", "")
            val = node.get("value", {}).get("value", "")
            if name or val:
                line = f"- {role}: {name} {val}".strip()
                lines.append(line)
        output = "\n".join(lines)
        if len(output) > max_chars:
            return output[:max_chars - 150] + "\n... [CDP AX Tree truncated]"
        return output
    except Exception as e:
        logger.debug(f"CDP Accessibility attempt failed: {e}")

    return "*Accessibility tree unavailable*"


class FallbackDOMReader:
    """
    Tier 3 Fallback runner that navigates to a URL and extracts clean Markdown
    or Accessibility Tree snapshots.
    """

    def __init__(self, headless: bool = True):
        self.headless = headless

    async def extract_content(
        self,
        url: str,
        mode: str = "both",  # "markdown", "accessibility", or "both"
        timeout_ms: int = 15000
    ) -> Dict[str, Any]:
        """Loads the page in headless browser and extracts clean fallback content."""
        async with async_playwright() as p:
            browser = await p.chromium.launch(
                headless=self.headless,
                args=["--disable-blink-features=AutomationControlled", "--no-sandbox"]
            )
            context = await browser.new_context(
                viewport={"width": 1280, "height": 800},
                user_agent="Mozilla/5.0 (Windows NT 10.0; Win64; x64) AppleWebKit/537.36 (KHTML, like Gecko) Chrome/126.0.0.0 Safari/537.36"
            )
            page = await context.new_page()

            try:
                await page.goto(url, wait_until="domcontentloaded", timeout=timeout_ms)
            except Exception as e:
                logger.warning(f"Fallback page navigation warning: {e}")

            title = await page.title()
            final_url = page.url

            result: Dict[str, Any] = {
                "title": title,
                "url": final_url,
                "tier": "Tier 3 (Universal Fallback)"
            }

            if mode in ("accessibility", "both"):
                ax_tree = await extract_accessibility_tree(page)
                result["accessibility_tree"] = ax_tree

            if mode in ("markdown", "both"):
                html_body = await page.content()
                markdown = clean_html_to_markdown(html_body)
                result["markdown"] = markdown

            await browser.close()
            return result
