"""Pemetaan isi halaman (judul + elemen ber-data-testid) untuk penyusunan Manual Book."""
import asyncio, json, os, sys
from playwright.async_api import async_playwright

BASE = os.environ.get("BASE", "http://localhost:3000")
EMAIL, PW = sys.argv[1], sys.argv[2]
PAGES = sys.argv[3].split(",")

JS = """() => {
  const vis = (e) => { const r = e.getBoundingClientRect(); return r.width > 0 && r.height > 0 && r.top < 900 && r.bottom > 0; };
  const heads = [...document.querySelectorAll('main h1, main h2, main h3, h1, h2')].filter(vis).map(e => e.innerText.trim().slice(0, 70));
  const tids = [...document.querySelectorAll('main [data-testid], [data-testid]')].filter(vis)
    .filter(e => !e.closest('aside nav') && !String(e.dataset.testid).startsWith('nav-'))
    .map(e => e.dataset.testid + '=' + (e.innerText || e.value || e.placeholder || e.getAttribute('aria-label') || '').replace(/\\s+/g,' ').trim().slice(0, 40));
  return { heads: [...new Set(heads)].slice(0, 12), tids: [...new Set(tids)].slice(0, 40) };
}"""


async def main():
    async with async_playwright() as p:
        b = await p.chromium.launch(executable_path="/usr/bin/chromium", args=["--no-sandbox"])
        ctx = await b.new_context(viewport={"width": 1440, "height": 900})
        pg = await ctx.new_page()
        await pg.goto(BASE + "/login")
        await pg.wait_for_timeout(1500)
        await pg.fill('[data-testid="login-email"]', EMAIL)
        await pg.fill('[data-testid="login-password"]', PW)
        await pg.keyboard.press("Enter")
        await pg.wait_for_timeout(3000)
        out = {}
        for url in PAGES:
            try:
                await pg.goto(BASE + url)
                await pg.wait_for_timeout(3500)
                out[url] = await pg.evaluate(JS)
            except Exception as e:
                out[url] = {"err": str(e)[:100]}
        for k, v in out.items():
            print("##", k, "|", " / ".join(v.get("heads", [])))
            print("   ", "; ".join(v.get("tids", [])))
        await b.close()

asyncio.run(main())
