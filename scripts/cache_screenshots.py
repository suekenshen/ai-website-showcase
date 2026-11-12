#!/usr/bin/env python3
"""Cache website screenshots in the repository for fast GitHub Pages loading."""
import json
import re
import time
import urllib.request
import urllib.error
from pathlib import Path

root = Path(__file__).resolve().parents[1]
html = (root / "index.html").read_text(encoding="utf-8")
match = re.search(r"const sites=(\[.*?\]);let selected=", html, re.S)
if not match:
    raise SystemExit("Could not find site list")
sites = json.loads(match.group(1))
folder = root / "screenshots"
folder.mkdir(exist_ok=True)
success = 0
failed = []
for i, (_, name, url) in enumerate(sites, 1):
    dest = folder / f"{i:03d}.png"
    if dest.exists() and dest.stat().st_size > 5000:
        success += 1
        continue
    screenshot = "https://image.thum.io/get/width/700/crop/500/noanimate/" + url
    for attempt in range(3):
        try:
            req = urllib.request.Request(screenshot, headers={"User-Agent": "Mozilla/5.0 (compatible; WebsiteShowcase/1.0)"})
            with urllib.request.urlopen(req, timeout=55) as response:
                data = response.read(4_000_000)
                kind = response.headers.get("Content-Type", "")
            is_image = data.startswith(b"\x89PNG\r\n\x1a\n") or data.startswith(b"\xff\xd8\xff") or data.startswith(b"RIFF") and data[8:12] == b"WEBP"
            if not is_image or len(data) < 5000:
                raise ValueError(f"Not a valid screenshot: {kind}, {len(data)} bytes")
            dest.write_bytes(data)
            success += 1
            print(f"[{i}/{len(sites)}] OK {name} ({len(data)} bytes)", flush=True)
            break
        except Exception as e:
            print(f"[{i}/{len(sites)}] Attempt {attempt+1} failed: {name}: {e}", flush=True)
            if attempt == 2:
                failed.append((i, name))
            else:
                time.sleep(8)
    time.sleep(1.5)
print(f"Saved {success}/{len(sites)} screenshots; failed: {failed}")
