"""Take screenshots of the poem analysis system"""
import os, time
from playwright.sync_api import sync_playwright

BASE = "http://127.0.0.1:5000"
OUT = r"C:\Users\Administrator\Desktop\All Mix\screenshots"
os.makedirs(OUT, exist_ok=True)

with sync_playwright() as p:
    browser = p.chromium.launch(headless=True)
    page = browser.new_page()

    # Login
    page.goto(f"{BASE}/login")
    page.wait_for_load_state("networkidle")
    page.fill('input[name="username"]', 'admin')
    page.fill('input[name="password"]', 'admin123')
    page.click('button[type="submit"]')
    page.wait_for_load_state("networkidle")
    time.sleep(1)
    print(f"URL: {page.url}")

    # Dashboard
    page.goto(f"{BASE}/dashboard")
    page.wait_for_load_state("networkidle")
    time.sleep(2)
    page.screenshot(path=os.path.join(OUT, "dashboard.png"), full_page=True)
    print("[OK] dashboard")

    # Graph table (意象溯源数据表)
    page.goto(f"{BASE}/graph/table")
    page.wait_for_load_state("networkidle")
    time.sleep(2)
    page.screenshot(path=os.path.join(OUT, "graph_table.png"), full_page=True)
    print("[OK] graph_table")

    for route in ["/graph", "/recycle"]:
        page.goto(f"{BASE}{route}")
        page.wait_for_load_state("networkidle")
        time.sleep(1)
        name = route.strip("/")
        page.screenshot(path=os.path.join(OUT, f"{name}.png"), full_page=True)
        print(f"[OK] {name}")

    browser.close()
    print("Done")
