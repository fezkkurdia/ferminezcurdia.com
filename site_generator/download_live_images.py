"""
Helper script to download all original photos and home slides from the live site ferminezcurdia.com
using the already extracted metadata.
"""

import os
import json
import urllib.request
import time

METADATA_FILE = os.path.join(os.path.dirname(__file__), "..", "existing_site_metadata.json")
CONTENT_DIR = os.path.join(os.path.dirname(__file__), "..", "content")

headers = {
    'User-Agent': 'Mozilla/5.0 (Windows NT 10.0; Win64; x64) AppleWebKit/537.36 (KHTML, like Gecko) Chrome/120.0.0.0 Safari/537.36',
    'Referer': 'https://ferminezcurdia.com/'
}

def download_file(url, target_path):
    if os.path.exists(target_path) and os.path.getsize(target_path) > 0:
        return True, "already exists"
    
    os.makedirs(os.path.dirname(target_path), exist_ok=True)
    req = urllib.request.Request(url, headers=headers)
    try:
        with urllib.request.urlopen(req, timeout=30) as resp:
            data = resp.read()
            with open(target_path, "wb") as f:
                f.write(data)
        return True, f"downloaded ({len(data)} bytes)"
    except Exception as e:
        return False, str(e)

def main():
    if not os.path.exists(METADATA_FILE):
        print(f"Error: {METADATA_FILE} not found.")
        return

    with open(METADATA_FILE, "r", encoding="utf-8") as f:
        data = json.load(f)

    # 1. Download gallery photos
    for gallery_name, photos in data.items():
        if gallery_name == "home_slides":
            continue
        gallery_dir = os.path.join(CONTENT_DIR, "galleries", gallery_name)
        print(f"\nProcessing {gallery_name} ({len(photos)} photos)...")
        for idx, p in enumerate(photos, start=1):
            url = p.get("full_url")
            filename = p.get("filename")
            if not url or not filename:
                continue
            target = os.path.join(gallery_dir, filename)
            ok, msg = download_file(url, target)
            print(f"  [{idx}/{len(photos)}] {filename}: {msg}")
            if "downloaded" in msg:
                time.sleep(0.1)

    # 2. Download home slides
    home_dir = os.path.join(CONTENT_DIR, "home_slides")
    slides = data.get("home_slides", [])
    print(f"\nProcessing home_slides ({len(slides)} slides)...")
    for idx, s in enumerate(slides, start=1):
        url = s.get("image_url")
        filename = s.get("filename")
        if not url or not filename:
            continue
        target = os.path.join(home_dir, filename)
        ok, msg = download_file(url, target)
        print(f"  [{idx}/{len(slides)}] {filename}: {msg}")
        if "downloaded" in msg:
            time.sleep(0.1)

    print("\nAll downloads completed!")

if __name__ == "__main__":
    main()
