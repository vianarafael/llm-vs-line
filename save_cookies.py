
from playwright.sync_api import sync_playwright
import json

COOKIES_PATH = "cookies.json"
BASE_URL = "https://lymcampus.jp/line-green-badge/courses/line-official-account-advanced/"

with sync_playwright() as p:
    browser = p.chromium.launch(headless=False)
    context = browser.new_context()
    page = context.new_page()
    
    print("🔑 Please log in manually...")
    page.goto(BASE_URL)
    
    input("✅ Press Enter after you're fully logged in and see the lessons...")

    cookies = context.cookies()
    with open(COOKIES_PATH, "w", encoding="utf-8") as f:
        json.dump(cookies, f)

    print("✅ Cookies saved to cookies.json")
    browser.close()
