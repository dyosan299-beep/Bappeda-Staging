"""Ambil screenshot aplikasi PETA INKLUSI untuk bahan presentasi.

Pemakaian:
  BASE_URL=https://... ADMIN_EMAIL=.. ADMIN_PASS=.. OP_EMAIL=.. OP_PASS=.. NGO_EMAIL=.. NGO_PASS=.. \
  python scripts/presentasi_screenshots.py
"""
import asyncio
import os
from pathlib import Path

from playwright.async_api import async_playwright

BASE = os.environ["BASE_URL"].rstrip("/")
OUT = Path(os.environ.get("OUT_DIR", "/app/docs/presentasi/shots"))
OUT.mkdir(parents=True, exist_ok=True)

PUBLIC = [("landing", "/"), ("publik", "/publik"), ("peta_sosial_publik", "/publik/peta-sosial"),
          ("peta_kemiskinan_publik", "/publik/peta-kemiskinan"), ("flow_sistem", "/flow-sistem"), ("login", "/login")]
ADMIN = [("admin_dashboard", "/dashboard"), ("admin_inquiry", "/ngo/inquiry"), ("admin_laporan", "/laporan-wilayah"),
         ("admin_email", "/notifikasi-email"), ("admin_ats", "/data-ats"), ("admin_role", "/role-permission"),
         ("admin_audit", "/audit-log"), ("admin_stunting", "/stunting"), ("admin_disabilitas", "/disabilitas"),
         ("admin_prioritas", "/prioritas"), ("admin_peta_sosial", "/peta-sosial")]
OPERATOR = [("operator_dashboard", "/dashboard")]
NGO = [("ngo_inquiry", "/ngo/inquiry"), ("ngo_inquiry_baru", "/ngo/inquiry/baru"), ("ngo_peta_sosial", "/ngo/peta-sosial")]


async def shoot(page, name, path, wait=3500):
    try:
        await page.goto(BASE + path, wait_until="networkidle", timeout=60000)
    except Exception:
        pass
    await page.wait_for_timeout(wait)
    await page.screenshot(path=str(OUT / f"{name}.png"))
    print("OK", name)


async def login(browser, email, pw):
    ctx = await browser.new_context(viewport={"width": 1600, "height": 900}, device_scale_factor=1)
    page = await ctx.new_page()
    await page.goto(BASE + "/login", wait_until="networkidle")
    await page.fill("#email", email)
    await page.fill("#password", pw)
    await page.click("[data-testid=login-submit]")
    await page.wait_for_timeout(4000)
    return ctx, page


async def main():
    async with async_playwright() as p:
        browser = await p.chromium.launch()
        ctx = await browser.new_context(viewport={"width": 1600, "height": 900})
        page = await ctx.new_page()
        for n, u in PUBLIC:
            await shoot(page, n, u)
        await ctx.close()

        for (email_env, pass_env, pages) in [("ADMIN_EMAIL", "ADMIN_PASS", ADMIN), ("OP_EMAIL", "OP_PASS", OPERATOR),
                                             ("NGO_EMAIL", "NGO_PASS", NGO)]:
            ctx, page = await login(browser, os.environ[email_env], os.environ[pass_env])
            for n, u in pages:
                await shoot(page, n, u)
            if email_env == "NGO_EMAIL":
                # detail inquiry pertama (berisi panel Cerita Dampak bila selesai)
                r = await page.request.get(BASE + "/api/inquiries")
                try:
                    data = await r.json()
                    items = data if isinstance(data, list) else data.get("items", [])
                    done = [i for i in items if i.get("status") in ("selesai", "completed")] or items
                    if done:
                        await shoot(page, "ngo_inquiry_detail", f"/ngo/inquiry/{done[0]['id']}")
                except Exception as e:
                    print("detail gagal", e)
            await ctx.close()
        await browser.close()


asyncio.run(main())
