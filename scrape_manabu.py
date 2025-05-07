import os
import re
import json
import time
from pathlib import Path
from playwright.sync_api import sync_playwright
from google.cloud import vision
import io
import requests

BASE_URL = "https://lymcampus.jp/line-official-account"
COOKIES_PATH = "cookies.json"
OUTPUT_DIR = Path("manabu")
IMG_DIR = OUTPUT_DIR / "images"

os.environ["GOOGLE_APPLICATION_CREDENTIALS"] = str(Path("vision-api.json").resolve())

def sanitize_filename(name):
    return re.sub(r'[\\/*?:"<>|]', "_", name)

def extract_text_from_image(vision_client, image_path):
    with open(image_path, "rb") as f:
        content = f.read()
    image = vision.Image(content=content)
    response = vision_client.text_detection(image=image)
    texts = response.text_annotations
    return texts[0].description.strip() if texts else ""

def scrape_courses():
    vision_client = vision.ImageAnnotatorClient()

    OUTPUT_DIR.mkdir(parents=True, exist_ok=True)
    IMG_DIR.mkdir(parents=True, exist_ok=True)

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
        page.wait_for_selector("div.mdMN08Content")
        time.sleep(2)

        # Find all course anchors in the intended container
        course_anchors = page.query_selector_all("div.MdMN09Li.mdMN09Course a")
        courses = []
        for anchor in course_anchors:
            text = anchor.inner_text().strip().replace("\n", " ")
            href = anchor.get_attribute("href")
            # Remove 'LINE公式アカウント' and extra spaces for course name
            course_name = text.replace('LINE公式アカウント', '').strip().split('  ')[0]
            courses.append({"name": course_name, "href": href})
        print(f"Found {len(courses)} courses")

        for course_idx, course in enumerate(courses):
            course_name = sanitize_filename(course["name"])
            href = course["href"]
            full_url = f"https://lymcampus.jp{href}"
            print(f"🟩 {course_name} — {full_url}")

            course_dir = OUTPUT_DIR / course_name
            course_dir.mkdir(parents=True, exist_ok=True)
            page.goto(full_url)
            page.wait_for_selector("ol.mdMN11Li")
            time.sleep(2)

            # Collect all lesson anchors in the course
            lesson_anchors = page.query_selector_all("ol.mdMN11Li li > a")
            lessons = []
            for anchor in lesson_anchors:
                lesson_title = anchor.inner_text().strip().splitlines()[0]
                lesson_href = anchor.get_attribute("href")
                lessons.append({"title": lesson_title, "href": lesson_href})

            print(f"  Found {len(lessons)} lessons")

            for lesson_idx, lesson in enumerate(lessons):
                lesson_title = lesson["title"]
                lesson_url = f"https://lymcampus.jp{lesson['href']}"
                print(f"    ▶️ {lesson_title} — {lesson_url}")
                page.goto(lesson_url)
                page.wait_for_selector("body")
                time.sleep(2)

                # Extract all visible text from the main content area
                lesson_text = page.evaluate("""
                    () => {
                        // Try to find the largest content block
                        let main = document.querySelector('.mdMN12Content, .mdMN13Content, .mdMN31Content, main, article, section');
                        if (!main) main = document.body;
                        return Array.from(main.querySelectorAll('p, li, h2, h3')).map(n => n.innerText.trim()).filter(Boolean).join('\\n\\n');
                    }
                """)

                # Extract all images from the page
                image_elements = page.query_selector_all("img")
                image_md = []
                ocr_md = []
                for img_idx, img_elem in enumerate(image_elements):
                    try:
                        box = img_elem.bounding_box()
                        if not box or box['width'] == 0 or box['height'] == 0:
                            print(f"Skipping invisible image {img_idx}")
                            continue
                        img_filename = f"{course_name}_lesson_{lesson_idx:02d}_img_{img_idx}.png"
                        img_path = IMG_DIR / img_filename
                        img_elem.screenshot(path=str(img_path))
                        image_md.append(f"![img](../images/{img_filename})")
                        # OCR
                        extracted = extract_text_from_image(vision_client, img_path)
                        if extracted:
                            ocr_md.append(f"### Image {img_idx}\n\n{extracted}")
                    except Exception as e:
                        print(f"❌ Failed to screenshot or OCR image: {img_filename} — {e}")

                filename = f"{sanitize_filename(lesson_title)}.md"
                md_path = course_dir / filename

                with open(md_path, "w", encoding="utf-8") as f:
                    f.write(f"# {lesson_title}\n\n")
                    f.write(f"URL: {lesson_url}\n\n")
                    f.write("## Main Content\n\n")
                    f.write(lesson_text + "\n\n")
                    if image_md:
                        f.write("## Images\n\n")
                        f.write("\n\n".join(image_md) + "\n\n")
                    if ocr_md:
                        f.write("## Image OCR Text\n\n")
                        f.write("\n\n".join(ocr_md))

                print(f"      ✅ Saved: {md_path}")

if __name__ == "__main__":
    scrape_courses()
