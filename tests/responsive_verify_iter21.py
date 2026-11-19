"""Verifikasi interaksi responsif yang dilaporkan testing agent (iteration_21)."""
import asyncio
import os

from playwright.async_api import async_playwright

BASE = os.environ["BASE_URL"].rstrip("/")


async def main():
    async with async_playwright() as p:
        b = await p.chromium.launch(executable_path="/usr/bin/google-chrome", args=["--no-sandbox"])
        page = await (await b.new_context(viewport={"width": 390, "height": 844})).new_page()
        await page.goto(BASE + "/login")
        await page.wait_for_timeout(1500)
        await page.fill("input[type=email]", os.environ["AUDIT_EMAIL"])
        await page.fill("input[type=password]", os.environ["AUDIT_PASSWORD"])
        await page.keyboard.press("Enter")
        await page.wait_for_timeout(3500)

        # 1) backdrop: klik di area backdrop yang TIDAK tertutup drawer (sisi kanan)
        await page.goto(BASE + "/dashboard"); await page.wait_for_timeout(2000)
        await page.click("[data-testid=sidebar-open]"); await page.wait_for_timeout(400)
        dw = await page.evaluate("document.querySelector('[data-testid=sidebar]').getBoundingClientRect().right")
        await page.mouse.click(375, 400); await page.wait_for_timeout(500)
        vis = await page.evaluate("getComputedStyle(document.querySelector('[data-testid=sidebar]')).visibility")
        print(f"1) drawer right edge={dw:.0f}px; klik backdrop x=375 -> sidebar visibility={vis}")

        # 2) flow-sistem 320x568: tombol di dalam batas horizontal viewport
        await page.set_viewport_size({"width": 320, "height": 568})
        await page.goto(BASE + "/flow-sistem"); await page.wait_for_timeout(2000)
        for t in ["flow-prev", "flow-next"]:
            r = await page.evaluate(f"(()=>{{const r=document.querySelector('[data-testid={t}]').getBoundingClientRect();return [r.left,r.right,r.top,r.bottom]}})()")
            print(f"2) {t} left={r[0]:.0f} right={r[1]:.0f} top={r[2]:.0f} bottom={r[3]:.0f} (vw=320, butuh scroll vertikal={r[3] > 568})")
        await page.click("[data-testid=flow-next]"); await page.wait_for_timeout(400)
        print("   slide indicator:", await page.evaluate("document.querySelector('[aria-current=step]')?.getAttribute('aria-label')"))

        # 3) ringkasan-mingguan tabs 360
        await page.set_viewport_size({"width": 360, "height": 780})
        await page.goto(BASE + "/ringkasan-mingguan"); await page.wait_for_timeout(5000)
        tabs = await page.query_selector("[data-testid=ringkasan-tabs]")
        print("3) ringkasan-tabs ada:", bool(tabs))
        if tabs:
            m = await page.evaluate("(()=>{const e=document.querySelector('[data-testid=ringkasan-tabs]');return [e.scrollWidth,e.clientWidth]})()")
            print("   tabs scrollWidth/clientWidth:", m)
            await page.click("[data-testid=ringkasan-tab-riwayat]"); await page.wait_for_timeout(500)
            st = await page.get_attribute("[data-testid=ringkasan-tab-riwayat]", "data-state")
            print("   tab riwayat state:", st)
        else:
            print("   body:", (await page.inner_text("main"))[:300])

        # 4) kelola-petugas add-user-btn
        await page.goto(BASE + "/kelola-petugas"); await page.wait_for_timeout(2500)
        await page.click("[data-testid=add-user-btn]"); await page.wait_for_timeout(500)
        print("4) add-user-form tampil:", await page.is_visible("[data-testid=add-user-form]"))

        # 5) peta bangunan 360
        await page.goto(BASE + "/peta-kemiskinan"); await page.wait_for_timeout(2000)
        await page.click("[data-testid=kemiskinan-tab-bangunan]"); await page.wait_for_timeout(3500)
        inhdr = await page.evaluate("!!document.querySelector('#layout-header-slot [data-testid=peta-filter-bar]')")
        print("5) filter di header (harus False di 360):", inhdr, "| legend hidden:", not await page.is_visible("#gis-legend"))
        await page.click("[data-testid=btn-legend-open]"); await page.wait_for_timeout(300)
        print("   legend terbuka:", await page.is_visible("#gis-legend"))
        await page.click("[data-testid=btn-legend-close]"); await page.wait_for_timeout(300)
        print("   legend tertutup lagi:", not await page.is_visible("#gis-legend"))
        await page.click("[data-testid=btn-tools-toggle]"); await page.wait_for_timeout(300)
        print("   basemap-select tampil:", await page.is_visible("[data-testid=basemap-select]"))
        await page.click("[data-testid=btn-zoom-in]"); await page.wait_for_timeout(600)
        await page.select_option("[data-testid=filter-kelurahan]", index=1)
        await page.click("[data-testid=btn-terapkan]"); await page.wait_for_timeout(1500)
        print("   zoom-in & terapkan filter OK; total rumah:", await page.inner_text("[data-testid=total-rumah]"))
        await page.set_viewport_size({"width": 1440, "height": 900}); await page.wait_for_timeout(1200)
        inhdr = await page.evaluate("!!document.querySelector('#layout-header-slot [data-testid=peta-filter-bar]')")
        print("   1440: filter di header:", inhdr, "| legend tampil:", await page.is_visible("#gis-legend"))
        await b.close()

asyncio.run(main())
