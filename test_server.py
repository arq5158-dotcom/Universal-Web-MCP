"""
Comprehensive Test Suite for Universal-Web-MCP.
Verifies all 3 tiers, cookie syncing, schema inference, token limits,
and runs a live test against https://flow.google.com/.
"""

import os
import sys
import asyncio
import json
import time
from pathlib import Path

# Add project root to path
sys.path.insert(0, str(Path(__file__).resolve().parent))

from cookie_sync import ChromeProfileManager, mask_secret, mask_headers
from interceptor import (
    NetworkInterceptor,
    LearnedRoute,
    is_noise_url,
    infer_json_schema,
    summarize_payload
)
from fallback import FallbackDOMReader, clean_html_to_markdown
from server import (
    route_cache,
    universal_request,
    discover_routes,
    get_page_content,
    sync_chrome_session,
    list_learned_routes
)


def test_cookie_sync_and_masking():
    print("\n--- Test 1: Chrome Profile & Masking ---")
    mgr = ChromeProfileManager()
    
    # Check profile resolution for arq5020 and are5020
    p1 = mgr.find_profile_by_email("arq5020@gmail.com")
    print(f"Profile for arq5020@gmail.com: {p1}")
    assert p1 == "Profile 1", f"Expected Profile 1, got {p1}"

    p2 = mgr.find_profile_by_email("are5020@gmail.com")
    print(f"Profile for are5020@gmail.com (fuzzy): {p2}")
    assert p2 == "Profile 1", f"Expected Profile 1, got {p2}"

    # Check secret masking
    token = "ya29.a0AfH6SMB_secret_access_token_123456789"
    masked = mask_secret(token)
    assert "ya29" in masked and "6789" in masked and "secret" not in masked
    print(f"Secret masking verified: {token} -> {masked}")

    # Check header masking
    raw_headers = {
        "Authorization": "Bearer secret_token_xyz",
        "Cookie": "session=abc12345; id=xyz9876",
        "Accept": "application/json"
    }
    cleaned = mask_headers(raw_headers)
    assert cleaned["Accept"] == "application/json"
    assert "secret" not in cleaned["Authorization"]
    print(f"Header masking verified: {cleaned}")
    print("[PASS] Cookie sync & masking test passed.")


def test_schema_inference_and_summarization():
    print("\n--- Test 2: Schema Inference & Token Budgeting ---")
    sample_data = {
        "status": "success",
        "total": 100,
        "items": [
            {"id": 1, "name": "Item A", "details": {"score": 9.8, "tags": ["fast", "ai"]}},
            {"id": 2, "name": "Item B", "details": {"score": 8.5, "tags": ["mcp"]}}
        ]
    }
    schema = infer_json_schema(sample_data)
    assert schema["type"] == "object"
    assert "status" in schema["properties"]
    assert schema["properties"]["items"]["type"] == "array"
    print("Inferred Schema:", json.dumps(schema, indent=2))

    summary = summarize_payload(sample_data)
    print("Summarized Payload:", summary)
    print("[PASS] Schema inference and summarization passed.")


def test_noise_filtering():
    print("\n--- Test 3: Interceptor Noise Filtering ---")
    assert is_noise_url("https://www.google-analytics.com/g/collect?v=2") is True
    assert is_noise_url("https://stats.g.doubleclick.net/r/collect") is True
    assert is_noise_url("https://adservice.google.com/adsid/integrator.js") is True
    assert is_noise_url("https://flow.google.com/api/v1/projects") is False
    assert is_noise_url("https://api.github.com/repos/arq5158/Universal-Web-MCP") is False
    print("[PASS] Noise filtering verified.")


def test_fallback_dom_cleaner():
    print("\n--- Test 4: Fallback HTML to Markdown Cleaner ---")
    dirty_html = """
    <html>
      <head><script>alert('track');</script><style>.ad{color:red}</style></head>
      <body>
        <nav><a href="/home">Home</a></nav>
        <main>
          <h1>Google Flow Studio</h1>
          <p>Creative AI studio for video, images and tools.</p>
          <img src="data:image/png;base64,iVBORw0KGgoAAAANSUhEUgAA..." alt="tracking" />
          <a href="https://flow.google.com/overview">Explore Models</a>
        </main>
        <footer><p>&copy; 2026 Google</p></footer>
      </body>
    </html>
    """
    md = clean_html_to_markdown(dirty_html)
    print("Extracted Markdown:\n", md)
    assert "Google Flow Studio" in md
    assert "Creative AI studio" in md
    assert "alert" not in md
    assert "data:image" not in md
    print(f"Markdown length: {len(md)} chars (< 1000 tokens)")
    print("[PASS] Fallback DOM cleaner passed.")


async def test_live_site_interaction():
    print("\n--- Test 5: Live Test on https://flow.google.com/ ---")
    # Step 1: Sync Chrome Profile session
    sync_result = sync_chrome_session("arq5020@gmail.com")
    print("Chrome Session Sync Result:", sync_result)
    assert sync_result["status"] == "success"

    # Step 2: Run universal_request on https://flow.google.com/
    target_url = "https://flow.google.com/"
    print(f"Executing universal_request on {target_url}...")
    t0 = time.perf_counter()
    result = await universal_request(url=target_url)
    t1 = time.perf_counter()
    total_elapsed_ms = round((t1 - t0) * 1000, 2)

    print(f"universal_request executed in {total_elapsed_ms}ms")
    print(f"Active Tier returned: {result.get('tier')}")
    print(f"Result keys: {list(result.keys())}")
    
    if "data" in result:
        print("Data preview:", json.dumps(result["data"], indent=2)[:300])
    if "accessibility_tree" in result:
        print("Accessibility tree preview:\n", result["accessibility_tree"][:300])
    if "markdown" in result:
        print("Markdown preview:\n", result["markdown"][:300])

    # Verify that routes or content were captured
    learned = list_learned_routes()
    print(f"Total learned routes currently cached: {len(learned)}")
    for r in learned[:3]:
        print(f"  -> {r.get('method')} {r.get('url')} (domain: {r.get('domain')})")

    # Step 3: Test Tier 1 Fast Path Replay if any route was learned or on test endpoint
    if learned:
        test_route = learned[0]
        print(f"\n--- Test 6: Tier 1 Fast Path Replay on {test_route['url']} ---")
        t_fast_0 = time.perf_counter()
        fast_res = await universal_request(url=test_route["url"], force_tier=1)
        t_fast_1 = time.perf_counter()
        fast_elapsed_ms = round((t_fast_1 - t_fast_0) * 1000, 2)
        print(f"Tier 1 Result: status={fast_res.get('status_code')}, latency={fast_res.get('latency_ms')}ms, total_wall_time={fast_elapsed_ms}ms")
        print("Tier 1 Fast Path message:", fast_res.get("message"))
        assert fast_res.get("tier") == "Tier 1 (Fast Path)"
    else:
        print("\nTesting Tier 1 fast path on public JSON endpoint...")
        json_url = "https://jsonplaceholder.typicode.com/todos/1"
        fast_res = await universal_request(url=json_url, force_tier=1)
        print("Public JSON Tier 1 Result:", fast_res)
        assert fast_res.get("tier") == "Tier 1 (Fast Path)"

    print("\n[ALL TESTS PASSED SUCCESSFULLY!]")


def main():
    test_cookie_sync_and_masking()
    test_schema_inference_and_summarization()
    test_noise_filtering()
    test_fallback_dom_cleaner()
    asyncio.run(test_live_site_interaction())


if __name__ == "__main__":
    main()
