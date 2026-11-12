#!/usr/bin/env python3
"""Generate real browser screenshots; never cache browser error pages as previews."""
import json
import os
import re
from pathlib import Path
from PIL import Image, ImageDraw, ImageFont, ImageStat
from playwright.sync_api import sync_playwright

root = Path(__file__).resolve().parents[1]
html = (root / "index.html").read_text(encoding="utf-8")
sites = json.loads(re.search(r"const sites=(\[.*?\]);let selected=", html, re.S).group(1))
folder = root / "screenshots"
folder.mkdir(exist_ok=True)
# Previously cached error/blank pages: always refresh these.
bad_names = {"水晶礦礦", "禾鈞國際人力開發", "COCOMEi", "芭達桑原住民主題餐廳"}
refresh_all = os.environ.get("REFRESH_ALL") == "1"
font_path = "/usr/share/fonts/truetype/dejavu/DejaVuSans.ttf"

def placeholder(dest, category, name):
    im = Image.new("RGB", (900, 540), "#e9f0fb")
    d = ImageDraw.Draw(im)
    d.rounded_rectangle((48, 48, 852, 492), radius=28, fill="#f8fbff", outline="#d8e4f5", width=3)
    big = ImageFont.truetype(font_path, 58)
    small = ImageFont.truetype(font_path, 25)
    d.text((450, 205), "WEBSITE PREVIEW", anchor="mm", font=big, fill="#45658d")
    d.text((450, 290), "Preview temporarily unavailable", anchor="mm", font=small, fill="#7890ae")
    im.save(dest, "PNG", optimize=True)

def looks_blank(path):
    im = Image.open(path).convert("RGB").resize((120, 75))
    stat = ImageStat.Stat(im)
    return max(stat.stddev) < 8

errors = ("this site can't be reached", "this page isn’t working", "this page isn't working",
          "err_tunnel_connection_failed", "err_name_not_resolved", "err_connection",
          "site can't be reached", "404 not found")
ok = 0
fallbacks = []
with sync_playwright() as p:
    browser = p.chromium.launch(headless=True, args=["--no-sandbox"])
    for i, (category, name, url) in enumerate(sites, 1):
        dest = folder / f"{i:03d}.png"
        if dest.exists() and dest.stat().st_size > 5000 and not refresh_all and name not in bad_names:
            ok += 1
            continue
        page = browser.new_page(viewport={"width": 1280, "height": 780}, device_scale_factor=1)
        try:
            response = page.goto(url, wait_until="domcontentloaded", timeout=22000)
            page.wait_for_timeout(2000)
            title = page.title().lower()
            body = page.locator("body").inner_text(timeout=5000)[:1200].lower()
            if (response and response.status >= 400) or any(e in title or e in body for e in errors):
                raise ValueError("Website returned an error page")
            page.screenshot(path=str(dest), type="png", animations="disabled", timeout=12000)
            if looks_blank(dest):
                raise ValueError("Blank screenshot")
            ok += 1
            print(f"[{i}/{len(sites)}] Captured: {name}", flush=True)
        except Exception as e:
            placeholder(dest, category, name)
            fallbacks.append(name)
            print(f"[{i}/{len(sites)}] Placeholder: {name}: {str(e)[:120]}", flush=True)
        finally:
            page.close()
    browser.close()
print(f"Valid or retained: {ok}; placeholders: {len(fallbacks)} ({', '.join(fallbacks)})")
