"""Ambil screenshot halaman tertentu pada viewport tertentu (untuk review visual).
Pemakaian: python tests/responsive_shots.py out_dir "WxH:/rute[:aksi]" ...
aksi opsional: click=<css>  (klik elemen sebelum screenshot)
"""
import asyncio
import os
import sys

from playwright.async_api import async_playwright

BASE = os.environ.get("BASE_URL", "").rstrip("/")
EMAIL = os.environ.get("AUDIT_EMAIL", "")
PASSWORD = os.environ.get("AUDIT_PASSWORD", "")


async def main():
    out = sys.argv[1]
    os.makedirs(out, exist_ok=True)
    async with async_playwright() as p:
        b = await p.chromium.launch(executable_path=os.environ.get("CHROME_PATH", "/usr/bin/google-chrome"), args=["--no-sandbox"])
        page = await (await b.new_context(viewport={"width": 1280, "height": 800})).new_page()
        await page.goto(BASE + "/login")
        await page.wait_for_timeout(1500)
        await page.fill("input[type=email]", EMAIL)
        await page.fill("input[type=password]", PASSWORD)
        await page.keyboard.press("Enter")
        await page.wait_for_timeout(3500)
        for i, spec in enumerate(sys.argv[2:]):
            parts = spec.split(":", 2)
            w, h = (int(x) for x in parts[0].split("x"))
            await page.set_viewport_size({"width": w, "height": h})
            await page.goto(BASE + parts[1], wait_until="domcontentloaded")
            await page.wait_for_timeout(2500)
            if len(parts) > 2 and parts[2].startswith("click="):
                try:
                    await page.click(parts[2][6:], timeout=5000)
                    await page.wait_for_timeout(900)
                except Exception as e:  # noqa: BLE001
                    print("click gagal", spec, repr(e)[:80])
            path = os.path.join(out, f"{i:02d}_{w}x{h}.jpg")
            await page.screenshot(path=path, type="jpeg", quality=45)
            print("saved", path, spec, flush=True)
        await b.close()

asyncio.run(main())
