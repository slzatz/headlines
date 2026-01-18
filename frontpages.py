#!/home/slzatz/frontpages/.venv/bin/python

import json
from playwright.sync_api import sync_playwright
from newspaper_list import newspapers


def retrieve_images(url=None):
    """
    Scrape front page URLs from frontpages.com using Playwright.

    Visits each newspaper's individual page to capture the real image URLs
    (which include extra characters added by JavaScript).
    """
    results = {}

    with sync_playwright() as p:
        browser = p.chromium.launch(headless=True)

        for newspaper_name in newspapers:
            newspaper_url = f"https://www.frontpages.com/{newspaper_name}"
            print(f"Fetching: {newspaper_name}")

            # Create a fresh page for each newspaper to avoid navigation conflicts
            page = browser.new_page()

            try:
                page.goto(newspaper_url, timeout=45000, wait_until='domcontentloaded')
                # Wait a bit for JavaScript to execute
                page.wait_for_timeout(2000)

                # Look for images with the newspaper name in the URL
                all_imgs = page.query_selector_all('img')
                for img in all_imgs:
                    src = img.get_attribute('src') or ''
                    if newspaper_name in src and ('.webp' in src or '.jpg' in src):
                        img_url = src
                        # Ensure it's the full-size path
                        if '/t/' in img_url:
                            img_url = img_url.replace('/t/', '/g/')
                        # Store just the path portion
                        if img_url.startswith('https://www.frontpages.com'):
                            img_url = img_url.replace('https://www.frontpages.com', '')
                        results[newspaper_name] = img_url
                        print(f"  -> {img_url}")
                        break
                else:
                    print(f"  -> Not found")

            except Exception as e:
                print(f"  -> Error: {e}")
            finally:
                page.close()

        browser.close()

    # Write Python list format for backward compatibility
    select_images = list(results.values())
    with open('frontpageurls.py', 'w') as file:
        text = "urls = " + repr(select_images)
        file.write(text)

    # Write JSON format (primary format used by servers)
    with open('frontpageurls.json', 'w') as file:
        json.dump(results, file)

    print(f"\nUpdated {len(results)} newspaper URLs")
    return results


if __name__ == '__main__':
    retrieve_images()
