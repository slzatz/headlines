#!/home/slzatz/frontpages/.venv/bin/python

"""
MCP Server for Newspaper Front Pages

Provides tools to list available newspapers and retrieve front page images
for analysis by Claude and other AI assistants.
"""

import json
import requests
from io import BytesIO
from pathlib import Path
from fastmcp import FastMCP
from fastmcp.utilities.types import Image
import wand.image
from frontpages import retrieve_images

# Initialize FastMCP server
mcp = FastMCP("front_page_mcp")

# Configuration from image_server.py
user_agent = "Mozilla/5.0 (Wayland; Linux x86_64) AppleWebKit/537.36 (KHTML, like Gecko) Chrome/91.0.4472.124 Safari/537.36"
headers = {'User-Agent': user_agent}

# Path to the JSON file containing newspaper URLs
NEWSPAPERS_JSON = Path(__file__).parent / "frontpageurls.json"


def display_image(uri: str, w: int | None = None, h: int | None = None) -> bool:
    """
    Fetch and process a newspaper front page image.

    Args:
        uri: Full URL to the image
        w: Optional width for resizing
        h: Optional height for resizing

    Returns:
        True if successful, False otherwise
    """
    print(uri)
    try:
        response = requests.get(uri, timeout=5.0, headers=headers)
    except (requests.exceptions.ConnectionError,
            requests.exceptions.TooManyRedirects,
            requests.exceptions.ChunkedEncodingError,
            requests.exceptions.ReadTimeout) as e:
        print(f"requests.get({uri}) generated exception:\n{e}")
        return False

    if response.status_code != 200:
        print(f"status code = {response.status_code}")
        return False

    # it is possible to have encoding == None and ascii == True
    if response.encoding or response.content.isascii():
        print(f"{uri} returned ascii text and not an image")
        return False

    # this try/except is needed for occasional bad/unknown file format
    try:
        img = wand.image.Image(file=BytesIO(response.content))
    except Exception as e:
        print(f"wand.image.Image(file=BytesIO(response.content))"
              f"generated exception from {uri} {e}")
        return False

    if w and h:
        img.transform(resize=f"{w}x{h}>")

    if img.format == 'JPEG':
        # Set high quality for better text readability
        img.compression_quality = 95
        img.save(filename="fp.jpg")
        img.close()
        return True
    else:
        print("format is not JPEG")
        return False


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
    try:
        with open(NEWSPAPERS_JSON, 'r') as f:
            newspapers = json.load(f)
        return sorted(newspapers.keys())
    except FileNotFoundError:
        return []
    except json.JSONDecodeError:
        return []


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
        success = display_image(full_url, w=1000, h=1500)

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
        newspapers = list_newspapers()
        return f"Successfully updated {len(newspapers)} newspaper front pages to today's date"
    except Exception as e:
        raise RuntimeError(f"Failed to update front pages: {str(e)}")


if __name__ == "__main__":
    # Run the MCP server
    mcp.run()
