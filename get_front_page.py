#!/home/slzatz/frontpages/.venv/bin/python

import argparse
import requests
from pathlib import Path
import wand.image
from io import BytesIO
import random
import json
from frontpageurls import urls
#from newspaper_list import newspapers


user_agent = "Mozilla/5.0 (Wayland; Linux x86_64) AppleWebKit/537.36 (KHTML, like Gecko) Chrome/91.0.4472.124 Safari/537.36"
headers = {'User-Agent': user_agent}

def display_image(uri, w=None, h=None):
    #global can_transfer_with_files
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
        print(f"wand.image.Image(file=BytesIO(response.content))"\
              f"generated exception from {uri} {e}")
        return False

    #img.transform(resize='825x1600>')
    if w and h:
        img.transform(resize=f"{w}x{h}>")


    print("Hello")
    if img.format == 'JPEG':
        #tf = NamedTemporaryFile(suffix='.rgba', delete=False)
        #img.save(filename = tf.name)
        #return tf
        img.save(filename = "fp.jpg")
        img.close()
        return True
    else:
        print("format is not JPEG")
        return False

if __name__ == "__main__":

    NEWSPAPERS_JSON = Path(__file__).parent / "frontpageurls.json"
    parser = argparse.ArgumentParser(description="Fetch and display a newspaper front page image.")
    parser.add_argument("name", type=str, nargs="?", default=None,
                        help="Name of the newspaper to fetch (e.g., 'nytimes'). If not provided, a random newspaper will be selected.")
    args = parser.parse_args()
    name = args.name
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
        success = display_image(full_url, w=900, h=1050)

        if not success:
            raise RuntimeError(f"Failed to retrieve front page for '{name}'. The image may be temporarily unavailable.")

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

