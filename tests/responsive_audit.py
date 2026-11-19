"""Audit responsif otomatis PETA INKLUSI.

Membuka setiap rute pada daftar viewport, lalu memeriksa:
  * horizontal overflow dokumen (scrollWidth > clientWidth)
  * elemen yang keluar dari batas kanan viewport / area konten utama
  * error JavaScript (pageerror) per rute

Pemakaian (butuh paket `playwright` di venv terpisah):
  BASE_URL=https://<preview> AUDIT_EMAIL=... AUDIT_PASSWORD=... \
  python tests/responsive_audit.py [WxH WxH ...]
"""
import asyncio
import os
import sys
import time

from playwright.async_api import async_playwright

sys.path.insert(0, os.path.dirname(__file__))
from responsive_audit_snippet import AUDIT_JS, ROUTES  # noqa: E402

BASE = os.environ.get("BASE_URL", "").rstrip("/")
EMAIL = os.environ.get("AUDIT_EMAIL", "")
PASSWORD = os.environ.get("AUDIT_PASSWORD", "")
CHROME = os.environ.get("CHROME_PATH", "/usr/bin/google-chrome")
# Kelas aksesibilitas opsional pada <html>, mis. "a11y-xlarge" (teks 150%)
HTML_CLASS = os.environ.get("HTML_CLASS", "").strip()

DEFAULT_VIEWPORTS = [
    (320, 568), (360, 800), (375, 812), (390, 844), (430, 932),
    (844, 390), (768, 1024), (820, 1180), (1180, 820), (1024, 768),
    (1280, 800), (1366, 768), (1440, 900), (1920, 1080), (2560, 1440),
]


async def main():
    vps = DEFAULT_VIEWPORTS
    if len(sys.argv) > 1:
        vps = [tuple(int(x) for x in a.split("x")) for a in sys.argv[1:]]
    async with async_playwright() as p:
        browser = await p.chromium.launch(executable_path=CHROME, args=["--no-sandbox"])
        ctx = await browser.new_context(viewport={"width": 1280, "height": 800})
        page = await ctx.new_page()
        errors = []
        page.on("pageerror", lambda e: errors.append(str(e)[:160]))
        await page.goto(BASE + "/login", wait_until="domcontentloaded")
        await page.wait_for_timeout(1500)
        await page.fill("input[type=email]", EMAIL)
        await page.fill("input[type=password]", PASSWORD)
        await page.keyboard.press("Enter")
        await page.wait_for_timeout(4000)
        print("login ->", page.url, flush=True)
        total_bad = 0
        for (w, h) in vps:
            await page.set_viewport_size({"width": w, "height": h})
            bad = 0
            t0 = time.time()
            for rt in ROUTES:
                errors.clear()
                try:
                    await page.goto(BASE + rt, wait_until="domcontentloaded", timeout=25000)
                    await page.wait_for_timeout(1500)
                    if HTML_CLASS:
                        await page.evaluate("(c) => document.documentElement.classList.add(...c.split(' '))", HTML_CLASS)
                        await page.wait_for_timeout(400)
                    res = await page.evaluate(AUDIT_JS)
                    if res["off"] or res["sw"] > res["vw"] + 1:
                        bad += 1
                        print(f"  BAD {w}x{h} {rt} sw={res['sw']} m={res.get('m', '-')} {res['off']}", flush=True)
                    if res["path"] != rt:
                        print(f"  REDIRECT {w}x{h} {rt} -> {res['path']}", flush=True)
                    if errors:
                        print(f"  JSERR {w}x{h} {rt}: {errors[:2]}", flush=True)
                except Exception as e:  # noqa: BLE001
                    bad += 1
                    print(f"  ERR {w}x{h} {rt} {repr(e)[:100]}", flush=True)
            total_bad += bad
            print(f"VIEWPORT {w}x{h}: {len(ROUTES)} rute, {bad} bermasalah ({time.time() - t0:.0f}s)", flush=True)
        print(f"SELESAI: total bermasalah = {total_bad}", flush=True)
        await browser.close()


if __name__ == "__main__":
    asyncio.run(main())
