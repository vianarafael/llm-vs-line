import os
import re
import json
import time
from pathlib import Path
from playwright.sync_api import sync_playwright
from google.cloud import vision
import io
from dotenv import load_dotenv

COURSE_MAP = {
    "basic": "https://lymcampus.jp/line-green-badge/courses/line-official-account-basic/",
    "advanced": "https://lymcampus.jp/line-green-badge/courses/line-official-account-advanced/"
}

COOKIES_PATH = "cookies.json"

def sanitize_filename(name):
    return re.sub(r'[\\/*?:"<>|]', "_", name)

def setup_google_cloud():
    os.environ["GOOGLE_APPLICATION_CREDENTIALS"] = str(Path("vision-api.json").resolve())
    return vision.ImageAnnotatorClient()

def extract_text_from_image(vision_client, image_path):
    with open(image_path, 'rb') as f:
        content = f.read()
    image = vision.Image(content=content)
    response = vision_client.text_detection(image=image)
    texts = response.text_annotations
    return texts[0].description.strip() if texts else ""

def scrape_and_save_markdown(course_key):
    BASE_URL = COURSE_MAP[course_key]
    OUTPUT_DIR = Path(course_key)
    IMG_DIR = OUTPUT_DIR / "images"
    IMG_DIR.mkdir(parents=True, exist_ok=True)

    vision_client = setup_google_cloud()

    with sync_playwright() as p:
        browser = p.chromium.launch(headless=False)
        context = browser.new_context()

        if not os.path.exists(COOKIES_PATH):
            print("❌ cookies.json not found.")
            return
        with open(COOKIES_PATH, "r", encoding="utf-8") as f:
            context.add_cookies(json.load(f))

        page = context.new_page()
        page.goto(BASE_URL)
        page.wait_for_selector("ol.mdMN11Li li a")

        # First collect all lesson information
        lessons_info = page.evaluate('''
            () => {
                const lessons = document.querySelectorAll("ol.mdMN11Li li a");
                return Array.from(lessons).map(lesson => ({
                    href: lesson.getAttribute("href"),
                    title: lesson.innerText.trim()
                }));
            }
        ''')

        # Then process each lesson
        for idx, lesson in enumerate(lessons_info):
            href = lesson["href"]
            title = lesson["title"]
            full_url = f"https://lymcampus.jp{href}"
            filename = sanitize_filename(f"{idx:02d}_{title}")
            md_path = OUTPUT_DIR / f"{filename}.md"

            print(f"\n📘 {title}")
            page.goto(full_url)
            time.sleep(3)

            # Extract main text content
            lesson_text = page.evaluate('''
                () => {
                    const nodes = document.querySelectorAll(".mdMN31Content p, .mdMN31Content li, .mdMN31Content h2, .mdMN31Content h3");
                    return Array.from(nodes).map(n => n.innerText.trim()).join("\\n");
                }
            ''')

            # Hide header and help popup
            page.evaluate("""
            const header = document.querySelector("header");
            if (header) header.style.display = "none";

            const help = document.querySelector(".help-popup");
            if (help) help.style.display = "none";
            """)

            # Extract text from canvas slides
            canvas = page.query_selector("canvas")
            slide_texts = []
            if canvas:
                count = 0
                while True:
                    # Wait for the next button to be present and stable
                    try:
                        next_button = page.wait_for_selector(".mdMN36Next", timeout=5000)
                        if not next_button:
                            break
                            
                        # Get button state
                        is_disabled = next_button.get_attribute("class") or ""
                        if "is-disabled" in is_disabled or "disabled" in is_disabled:
                            break

                        # Take screenshot before clicking
                        img_path = IMG_DIR / f"{filename}_slide_{count}.png"
                        canvas.screenshot(path=str(img_path))
                        extracted = extract_text_from_image(vision_client, img_path)
                        if extracted:
                            slide_texts.append(f"### Slide {count}\n\n{extracted}")
                        print(f"🖼️ Captured slide {count}")
                        
                        # Click and wait for animation
                        next_button.click()
                        page.wait_for_timeout(1000)  # Wait for animation
                        count += 1
                        
                    except Exception as e:
                        print(f"⚠️ Error on slide {count}: {str(e)}")
                        break

            # Save as markdown
            with open(md_path, "w", encoding="utf-8") as f:
                f.write(f"# {title}\n\n")
                f.write(f"URL: {full_url}\n\n")
                f.write("## Main Content\n\n")
                f.write(lesson_text + "\n\n")
                if slide_texts:
                    f.write("## Slide OCR Text\n\n")
                    f.write("\n\n".join(slide_texts))

            print(f"✅ Saved: {md_path}")

if __name__ == "__main__":
    import argparse
    parser = argparse.ArgumentParser()
    parser.add_argument("--course", choices=["basic", "advanced"], default="advanced")
    args = parser.parse_args()

    scrape_and_save_markdown(args.course)
