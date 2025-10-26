# CLAUDE.md

This file provides guidance to Claude Code (claude.ai/code) when working with code in this repository.

## Project Overview

This project scrapes newspaper front pages from frontpages.com and serves them via a Flask API. It targets a curated list of major international newspapers and provides endpoints to retrieve specific front pages or random selections.

## Architecture

The codebase consists of three main components:

1. **Scraper** (`frontpages.py`): Fetches front page image URLs from frontpages.com, filters them against the curated newspaper list, and writes results to:
   - `frontpageurls.py`: Python list of URLs (for backward compatibility)
   - `frontpageurls.json`: JSON dictionary mapping newspaper names to URLs

2. **Flask Server** (`image_server.py`): REST API that:
   - Downloads front page images from frontpages.com on-demand
   - Uses ImageMagick (via Wand) to process/resize images to JPEG format
   - Caches the last processed image as `fp.jpg`
   - Provides multiple endpoints for different access patterns

3. **Scheduler** (`schedule_frontpages.py`): Runs the scraper daily at 10:00 AM to update front page URLs

4. **Configuration** (`newspaper_list.py`): Curated list of ~45 newspapers from US, UK, France, Germany, Spain, Israel, Netherlands, Japan, China, Australia, Italy, Switzerland, Canada, and Austria. Tabloids are commented out.

## Key Data Flow

1. Scraper retrieves HTML from frontpages.com
2. BeautifulSoup extracts all `<img>` tags with `data-src` attributes (WebP front pages)
3. Image paths are filtered against the curated newspaper list
4. URLs are transformed from thumbnail (`/t`) to full-size (`/g`) paths
5. Results stored in `frontpageurls.json` and `frontpageurls.py`
6. Flask server reads from these files and fetches images on-demand

## Development Commands

### Setup
```bash
# Install dependencies (uses uv package manager)
uv sync
```

### Run the Flask server
```bash
python image_server.py
# Server runs on http://0.0.0.0:5000
```

### Run the MCP server
```bash
python front_page_mcp.py
# Runs MCP server for Claude integration
```

### Run the scraper manually
```bash
python frontpages.py
```

### Run the scheduler
```bash
python schedule_frontpages.py
# Runs scraper daily at 10:00 AM
```

## API Endpoints (Flask Server)

- `GET /imagejpg` - Returns a random newspaper front page
- `GET /newspaper/<name>` - Returns specific newspaper by slug (e.g., "the-new-york-times")
- `GET /newspapers` - Returns list of available newspaper names

## MCP Server Tools

The `front_page_mcp.py` server provides three tools for Claude and other AI assistants:

### `list_newspapers()`
Returns a sorted list of all available newspaper identifiers (e.g., "the-new-york-times", "the-guardian", "le-monde"). Use this to discover what newspapers are available and get the exact format needed for retrieval.

### `get_newspaper(name: str)`
Retrieves a specific newspaper's front page as a base64-encoded JPEG image. Claude can directly analyze the image to identify headlines, stories, layout, and other visual elements.

**Usage Pattern**: When asked about a newspaper (e.g., "What are the major stories in the NY Times?"), Claude should:
1. Call `list_newspapers()` to find the exact identifier (e.g., "the-new-york-times")
2. Call `get_newspaper("the-new-york-times")` to retrieve and analyze the front page image

### `update_front_pages()`
Updates the local database (`frontpageurls.json`) with today's front page URLs by scraping frontpages.com. The MCP server automatically checks if the database is stale when calling `get_newspaper()`, but this tool allows manual updates when needed.

**Complementary Use**: After Claude analyzes a front page via MCP, humans can view the same image by accessing `http://localhost:5000/newspaper/the-new-york-times` in a browser (Flask server must be running).

## MCP Server Implementation Details

### Image Format Requirements

**CRITICAL**: The MCP server MUST use FastMCP's `Image` class to return images. Returning raw base64 strings or data URIs in a dictionary will cause Claude Desktop to hallucinate from training data instead of analyzing the actual image.

**Correct approach**:
```python
from fastmcp.utilities.types import Image

@mcp.tool()
def get_newspaper(name: str) -> Image:
    # ... fetch and process image ...
    with open("fp.jpg", "rb") as f:
        image_bytes = f.read()
    return Image(data=image_bytes, format="jpeg")
```

**Incorrect approach** (will cause hallucination):
```python
# DON'T DO THIS - Claude won't properly analyze the image
return {"image": base64_data, "format": "jpeg"}
```

### Image Size and Quality Settings

The MCP server resizes images to balance readability with Claude Desktop's limitations:

- **Resolution**: 1000x1500 pixels (maintains aspect ratio with `>` flag)
- **JPEG Quality**: 95 (high quality for text readability)
- **Resulting size**: ~650KB raw, ~870KB base64-encoded
- **Claude Desktop limit**: 1MB for tool responses

These settings were chosen after testing to ensure:
1. Text is clearly readable by Claude's vision model
2. File size stays under Claude Desktop's 1MB limit
3. Headlines and article text are sharp enough for accurate analysis

**Why these specific values**:
- Lower resolutions (800x1200) resulted in Claude being unable to read headlines
- Lower JPEG quality created compression artifacts that confused the vision model
- Higher resolutions exceed the 1MB limit

### Configuration in Claude Desktop

Add to `~/.config/Claude/claude_desktop_config.json`:
```json
{
  "mcpServers": {
    "front_page_mcp": {
      "command": "/home/slzatz/headlines/.venv/bin/python3",
      "args": ["/home/slzatz/headlines/front_page_mcp.py"]
    }
  }
}
```

Restart Claude Desktop after configuration changes.

## Important Implementation Details

- Image processing uses Wand (ImageMagick binding) to handle various image formats and convert to JPEG
- The `display_image()` function in image_server.py:75 handles all image fetching, error handling, and format conversion
- Images are resized using ImageMagick's transform() with optional width/height parameters
- Custom User-Agent header is required for fetching from frontpages.com
- Error handling covers connection timeouts, encoding issues, and malformed image files
- All scripts have shebangs pointing to the virtual environment Python

### MCP Tool Implementation Pattern

**CRITICAL**: When implementing MCP tools that need to call other tool functions internally, you CANNOT directly call `@mcp.tool()` decorated functions because the decorator wraps them into `FunctionTool` objects that are not callable from Python code.

**Correct approach**: Extract shared logic into helper functions prefixed with `_`:
```python
def _get_newspaper_list() -> list[str]:
    """Internal helper to get newspaper list."""
    try:
        with open(NEWSPAPERS_JSON, 'r') as f:
            newspapers = json.load(f)
        return sorted(newspapers.keys())
    except FileNotFoundError:
        return []

@mcp.tool()
def list_newspapers() -> list[str]:
    """MCP tool that returns newspaper list."""
    return _get_newspaper_list()

@mcp.tool()
def update_front_pages() -> str:
    """MCP tool that can use the helper."""
    retrieve_images('https://www.frontpages.com/newspaper-list')
    newspapers = _get_newspaper_list()  # Use helper, not list_newspapers()
    return f"Successfully updated {len(newspapers)} newspapers"
```

**Incorrect approach** (will raise "'FunctionTool' object is not callable"):
```python
@mcp.tool()
def update_front_pages() -> str:
    retrieve_images('https://www.frontpages.com/newspaper-list')
    newspapers = list_newspapers()  # ERROR: Can't call decorated function
    return f"Successfully updated {len(newspapers)} newspapers"
```

## Python Version

Requires Python 3.13 or higher (specified in pyproject.toml)
