"""Take screenshots - save to non-space path"""
import os, time
OUT = r"C:\Users\Administrator\screenshots"
os.makedirs(OUT, exist_ok=True)
from playwright.sync_api import sync_playwright

BASE = "http://127.0.0.1:5000"

with sync_playwright() as p:
    browser = p.chromium.launch(headless=True)
    page = browser.new_page()

    page.goto(f"{BASE}/login")
    page.wait_for_load_state("networkidle")
    page.fill('input[name="username"]', 'admin')
    page.fill('input[name="password"]', 'admin123')
    page.click('button[type="submit"]')
    page.wait_for_load_state("networkidle")

    page.goto(f"{BASE}/graph/table")
    page.wait_for_load_state("networkidle")
    time.sleep(3)
    png = os.path.join(OUT, "graph_table.png")
    page.screenshot(path=png, full_page=True)
    print(f"Saved: {png} size={os.path.getsize(png)}")

    browser.close()
