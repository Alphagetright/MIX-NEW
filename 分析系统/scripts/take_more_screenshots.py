"""Take additional screenshots of the pipeline web app for the documentation."""
import os, json, time
from playwright.sync_api import sync_playwright

OUT = r"C:\Users\Administrator\Desktop\All Mix\_diagrams"
os.makedirs(OUT, exist_ok=True)
BASE = "http://127.0.0.1:5000"

with sync_playwright() as p:
    browser = p.chromium.launch(headless=True)
    context = browser.new_context(viewport={"width": 1280, "height": 800})
    page = context.new_page()

    # 1. Login page
    page.goto(f"{BASE}/login")
    page.wait_for_load_state("networkidle")
    page.screenshot(path=os.path.join(OUT, "ss_login.png"), full_page=True)
    print("1/13 ss_login.png")

    # 2. Register page
    page.goto(f"{BASE}/register")
    page.wait_for_load_state("networkidle")
    page.screenshot(path=os.path.join(OUT, "ss_register.png"), full_page=True)
    print("2/13 ss_register.png")

    # === Login (explicit) ===
    # First try registering; if exists, ignore error
    page.goto(f"{BASE}/register")
    page.wait_for_load_state("networkidle")
    page.fill("input[name=username]", "testscreenshot")
    page.fill("input[name=password]", "test123")
    page.fill("input[name=confirm]", "test123")
    page.click("button[type=submit]")
    page.wait_for_load_state("networkidle")

    # Always re-login explicitly to ensure fresh session
    page.goto(f"{BASE}/login")
    page.wait_for_load_state("networkidle")
    page.fill("input[name=username]", "testscreenshot")
    page.fill("input[name=password]", "test123")
    page.click("button[type=submit]")
    page.wait_for_load_state("networkidle")
    time.sleep(0.5)

    # Verify we are logged in
    assert "home" in page.url, f"Login failed! URL is {page.url}"
    print("  Login verified, on home page")

    # 3. Home page (logged in)
    page.screenshot(path=os.path.join(OUT, "ss_home.png"), full_page=True)
    print("3/13 ss_home.png")

    # === Create demo data before dashboard screenshot ===
    # Pipeline run
    response = page.evaluate("""async () => {
        const r = await fetch('/api/v1/pipeline/run', {
            method: 'POST',
            headers: {'Content-Type': 'application/json'},
            body: JSON.stringify({input: 'poem.txt', format: 'json'})
        });
        return await r.json();
    }""")
    print(f"  Pipeline run: {response}")

    # Second pipeline run for more data
    response = page.evaluate("""async () => {
        const r = await fetch('/api/v1/pipeline/run', {
            method: 'POST',
            headers: {'Content-Type': 'application/json'},
            body: JSON.stringify({input: 'poems.json', format: 'json'})
        });
        return await r.json();
    }""")
    print(f"  Pipeline run 2: {response}")

    # Submit annotation
    response = page.evaluate("""async () => {
        const r = await fetch('/api/v1/annotations/submit', {
            method: 'POST',
            headers: {'Content-Type': 'application/json'},
            credentials: 'same-origin',
            body: JSON.stringify({
                poem: '静夜思',
                author: '李白',
                verses: ['床前明月光', '疑是地上霜', '举头望明月', '低头思故乡']
            })
        });
        return await r.json();
    }""")
    print(f"  Annotation submit: {response}")

    # 4. Dashboard (now with data populated)
    page.goto(f"{BASE}/dashboard")
    page.wait_for_load_state("networkidle")
    page.screenshot(path=os.path.join(OUT, "ss_dashboard.png"), full_page=True)
    print("4/13 ss_dashboard.png")

    # 5. Annotation detail page
    page.goto(f"{BASE}/annotations")
    page.wait_for_load_state("networkidle")
    page.screenshot(path=os.path.join(OUT, "ss_annotations.png"), full_page=True)
    print("5/13 ss_annotations.png")

    # 6. Pipeline list API
    page.goto(f"{BASE}/api/v1/pipeline/list")
    page.wait_for_load_state("networkidle")
    page.screenshot(path=os.path.join(OUT, "ss_api_pipelines.png"), full_page=True)
    print("6/13 ss_api_pipelines.png")

    # 7. Pipeline stats API
    page.goto(f"{BASE}/api/v1/pipeline/stats")
    page.wait_for_load_state("networkidle")
    page.screenshot(path=os.path.join(OUT, "ss_api_pipeline_stats.png"), full_page=True)
    print("7/13 ss_api_pipeline_stats.png")

    # 8. Annotation list API
    page.goto(f"{BASE}/api/v1/annotations/list")
    page.wait_for_load_state("networkidle")
    page.screenshot(path=os.path.join(OUT, "ss_api_annotations.png"), full_page=True)
    print("8/13 ss_api_annotations.png")

    # 9. Annotation export API
    page.goto(f"{BASE}/api/v1/annotations/export/json")
    page.wait_for_load_state("networkidle")
    page.screenshot(path=os.path.join(OUT, "ss_api_annotations_export.png"), full_page=True)
    print("9/13 ss_api_annotations_export.png")

    # 12. System info API
    page.goto(f"{BASE}/api/v1/system/info")
    page.wait_for_load_state("networkidle")
    page.screenshot(path=os.path.join(OUT, "ss_api_info.png"), full_page=True)
    print("12/13 ss_api_info.png")

    # 13. Health check API
    page.goto(f"{BASE}/api/v1/system/health")
    page.wait_for_load_state("networkidle")
    page.screenshot(path=os.path.join(OUT, "ss_api_health.png"), full_page=True)
    print("13/13 ss_api_health.png")

    browser.close()
    print("\nAll screenshots taken successfully!")
