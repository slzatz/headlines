#!/home/slzatz/frontpages/.venv/bin/python

import argparse
import json
from pathlib import Path
from io import BytesIO
from playwright.sync_api import sync_playwright
import wand.image

# Path to the JSON file containing newspaper URLs
NEWSPAPERS_JSON = Path(__file__).parent / "frontpageurls.json"


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

    print("Image saved to fp.jpg")
    return True


if __name__ == "__main__":
    parser = argparse.ArgumentParser(description="Fetch and display a newspaper front page image.")
    parser.add_argument("name", type=str, nargs="?", default=None,
                        help="Name of the newspaper to fetch (e.g., 'the-new-york-times'). If not provided, lists available newspapers.")
    args = parser.parse_args()
    name = args.name

    try:
        # Load available newspapers
        with open(NEWSPAPERS_JSON, 'r') as f:
            newspapers = json.load(f)

        if name is None:
            print("Available newspapers:")
            for n in sorted(newspapers.keys()):
                print(f"  {n}")
            exit(0)

        # Check if newspaper exists
        if name not in newspapers:
            available = ", ".join(sorted(newspapers.keys())[:10])
            raise ValueError(f"Newspaper '{name}' not found. Available newspapers include: {available}...")

        # Get the partial URL for this newspaper
        partial_url = newspapers[name]
        full_url = "https://www.frontpages.com" + partial_url

        # Fetch and save the image (resized for MCP compatibility)
        success = display_image(full_url, w=1000, h=1500)

        if not success:
            raise RuntimeError(f"Failed to retrieve front page for '{name}'. The image may be temporarily unavailable.")

    except FileNotFoundError as e:
        if "frontpageurls.json" in str(e):
            raise FileNotFoundError("Newspapers database not found. Run frontpages.py to update the newspaper list.")
        raise
    except json.JSONDecodeError:
        raise ValueError("Newspapers database is corrupted. Run frontpages.py to regenerate it.")
    except (ValueError, RuntimeError):
        raise
    except Exception as e:
        raise RuntimeError(f"Unexpected error: {str(e)}")
