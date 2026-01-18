#!/home/slzatz/frontpages/.venv/bin/python

from flask import Flask, send_file
from playwright.sync_api import sync_playwright
import wand.image
import random
import json
from frontpageurls import urls

app = Flask(__name__)


def fetch_image_with_playwright(uri: str, timeout: int = 30000) -> bytes | None:
    """
    Fetch an image using Playwright to bypass anti-scraping measures.

    Args:
        uri: Full URL to the image
        timeout: Request timeout in milliseconds

    Returns:
        Image bytes if successful, None otherwise
    """
    try:
        with sync_playwright() as p:
            browser = p.chromium.launch(headless=True)
            page = browser.new_page()

            # Navigate directly to the image URL
            response = page.goto(uri, timeout=timeout)

            if response is None or response.status != 200:
                print(f"Failed to fetch image: status={response.status if response else 'no response'}")
                browser.close()
                return None

            # Get image bytes from response
            image_bytes = response.body()
            browser.close()
            return image_bytes

    except Exception as e:
        print(f"Playwright error fetching {uri}: {e}")
        return None


def display_image(uri: str, w: int | None = None, h: int | None = None) -> bool:
    """
    Fetch and process a newspaper front page image using Playwright.

    Args:
        uri: Full URL to the image
        w: Optional width for resizing
        h: Optional height for resizing

    Returns:
        True if successful, False otherwise
    """
    print(f"Fetching: {uri}")

    # Use Playwright to fetch the image
    image_bytes = fetch_image_with_playwright(uri)

    if image_bytes is None:
        return False

    # Check if we got actual image data (not an error page)
    if len(image_bytes) < 1000:
        content_preview = image_bytes[:200].decode('utf-8', errors='replace')
        if '<html' in content_preview.lower() or '<!doctype' in content_preview.lower():
            print(f"Received HTML instead of image")
            return False

    # Process with Wand
    try:
        img = wand.image.Image(blob=image_bytes)
    except Exception as e:
        print(f"wand.image.Image error: {e}")
        return False

    if w and h:
        img.transform(resize=f"{w}x{h}>")

    # Convert to JPEG and save
    img.format = 'jpeg'
    img.compression_quality = 95
    img.save(filename="fp.jpg")
    img.close()
    return True


@app.route("/image")
def image():
    return send_file("image.jpg", mimetype="image/jpg")


@app.route("/imagejpg")
def imagejpg():
    partial_url = random.choice(urls)
    f = display_image("https://www.frontpages.com" + partial_url)
    return send_file("fp.jpg", mimetype="image/jpg")


@app.route("/newspaper/<name>")
def newspaper(name):
    with open('frontpageurls.json', 'r') as f:
        newspapers = json.load(f)
    selection = newspapers.get(name, None)
    if selection:
        f = display_image("https://www.frontpages.com" + selection)
        return send_file("fp.jpg", mimetype="image/jpg")
    else:
        return f"No newspaper with name {name} found", 404


@app.route("/newspapers")
def newspapers():
    with open('frontpageurls.json', 'r') as f:
        newspapers = json.load(f)
    return list(newspapers.keys())


if __name__ == "__main__":
    app.run(debug=True,
            host='0.0.0.0',
            port=5000)
