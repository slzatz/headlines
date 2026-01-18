#!/home/slzatz/frontpages/.venv/bin/python

"""
MCP Server for Newspaper Front Pages

Provides tools to list available newspapers and retrieve front page images
for analysis by Claude and other AI assistants.
"""

import json
from pathlib import Path
from playwright.sync_api import sync_playwright
from fastmcp import FastMCP
from fastmcp.utilities.types import Image
import wand.image
from frontpages import retrieve_images

# Initialize FastMCP server
mcp = FastMCP("front_page_mcp")

# Path to the JSON file containing newspaper URLs
NEWSPAPERS_JSON = Path(__file__).parent / "frontpageurls.json"


def _fetch_image_with_playwright(uri: str, timeout: int = 30000) -> bytes | None:
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


def _fetch_and_save_image(uri: str, w: int | None = None, h: int | None = None) -> bool:
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
    image_bytes = _fetch_image_with_playwright(uri)

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

    # Convert to JPEG and save with high quality for text readability
    img.format = 'jpeg'
    img.compression_quality = 95
    img.save(filename="fp.jpg")
    img.close()
    return True


def _is_database_stale() -> bool:
    """Check if the cached front pages are from today."""
    from datetime import date
    try:
        with open(NEWSPAPERS_JSON, 'r') as f:
            newspapers = json.load(f)
        if not newspapers:
            return True

        # Get first newspaper URL and extract date
        # URL format: /g/2025/10/14/newspaper-name...
        first_url = next(iter(newspapers.values()))
        parts = first_url.split('/')
        db_date = f"{parts[2]}-{parts[3]}-{parts[4]}"
        today = date.today().isoformat()
        return db_date != today
    except:
        return True  # If we can't tell, assume stale


def _get_newspaper_list() -> list[str]:
    """Internal helper to get newspaper list."""
    try:
        with open(NEWSPAPERS_JSON, 'r') as f:
            newspapers = json.load(f)
        return sorted(newspapers.keys())
    except FileNotFoundError:
        return []
    except json.JSONDecodeError:
        return []


@mcp.tool()
def list_newspapers() -> list[str]:
    """
    List all available newspapers that can be retrieved.

    Returns a list of newspaper identifier strings (e.g., "the-new-york-times",
    "the-guardian", "le-monde"). These identifiers should be used when calling
    get_newspaper to retrieve a specific front page.

    Returns:
        List of newspaper identifier strings
    """
    return _get_newspaper_list()


@mcp.tool()
def get_newspaper(name: str) -> Image:
    """
    Retrieve a specific newspaper's front page image.

    Fetches the latest front page for the specified newspaper and returns it
    as an image that can be viewed and analyzed directly.

    Args:
        name: The newspaper identifier (e.g., "the-new-york-times").
              Use list_newspapers() to see all available options.

    Returns:
        Image object containing the newspaper front page as a JPEG.
        Raises an error if the newspaper is not found or cannot be retrieved.
    """
    # Auto-update if database is stale
    if _is_database_stale():
        retrieve_images('https://www.frontpages.com/newspaper-list')

    try:
        # Load available newspapers
        with open(NEWSPAPERS_JSON, 'r') as f:
            newspapers = json.load(f)

        # Check if newspaper exists
        if name not in newspapers:
            available = ", ".join(sorted(newspapers.keys())[:10])
            raise ValueError(f"Newspaper '{name}' not found. Available newspapers include: {available}... (use list_newspapers for full list)")

        # Get the partial URL for this newspaper
        partial_url = newspapers[name]
        full_url = "https://www.frontpages.com" + partial_url

        # Fetch and save the image (resized for MCP compatibility)
        success = _fetch_and_save_image(full_url, w=1000, h=1500)

        if not success:
            raise RuntimeError(f"Failed to retrieve front page for '{name}'. The image may be temporarily unavailable.")

        # Read the saved image and return as Image object
        try:
            with open("fp.jpg", "rb") as f:
                image_bytes = f.read()

            return Image(data=image_bytes, format="jpeg")

        except FileNotFoundError:
            raise FileNotFoundError("Image file not found after download")

    except FileNotFoundError as e:
        if "frontpageurls.json" in str(e):
            raise FileNotFoundError("Newspapers database not found. Run frontpages.py to update the newspaper list.")
        raise
    except json.JSONDecodeError:
        raise ValueError("Newspapers database is corrupted. Run frontpages.py to regenerate it.")
    except (ValueError, RuntimeError):
        # Re-raise our own exceptions
        raise
    except Exception as e:
        raise RuntimeError(f"Unexpected error: {str(e)}")


@mcp.tool()
def update_front_pages() -> str:
    """
    Update the list of available front pages to today's date.

    Scrapes frontpages.com to get the latest front page URLs and updates
    the local database (frontpageurls.json). Call this when you need access
    to today's front pages rather than cached ones from a previous date.

    Returns:
        Success message with count of newspapers updated
    """
    try:
        retrieve_images('https://www.frontpages.com/newspaper-list')
        newspapers = _get_newspaper_list()
        return f"Successfully updated {len(newspapers)} newspaper front pages to today's date"
    except Exception as e:
        raise RuntimeError(f"Failed to update front pages: {str(e)}")


if __name__ == "__main__":
    # Run the MCP server
    mcp.run()
