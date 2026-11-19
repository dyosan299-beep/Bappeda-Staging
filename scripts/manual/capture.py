"""Ambil screenshot setiap halaman PETA INKLUSI + beri penanda langkah bernomor (untuk Manual Book).

Keluaran: /app/docs/manual/shots/<id>.jpg dan /app/docs/manual/shots/marks.json
Pemakaian: python3 capture.py <superadmin_email> <superadmin_pw> <ngo_email> <ngo_pw> <petugas_email> <petugas_pw> [id1,id2,...]
"""
import asyncio, json, os, sys
from PIL import Image, ImageDraw, ImageFont
from playwright.async_api import async_playwright

BASE = os.environ.get("BASE", "https://commit-checker-live-13.preview.emergentagent.com")
OUT = "/app/docs/manual/shots"
os.makedirs(OUT, exist_ok=True)
ACC = {"admin": (sys.argv[1], sys.argv[2]), "ngo": (sys.argv[3], sys.argv[4]), "petugas": (sys.argv[5], sys.argv[6])}
ONLY = set(sys.argv[7].split(",")) if len(sys.argv) > 7 and sys.argv[7] else None
T = lambda t: f'[data-testid="{t}"]'  # noqa: E731

# (id, peran, url, aksi_sebelum, penanda[selector])  aksi: ("click", sel) | ("scroll", sel) | ("wait", ms) | ("key", k) | ("js", code)
SHOTS = [
    # ---------------- Publik
    ("p01_beranda", "public", "/", [], [T("pubnav--publik"), T("pubnav--publik-peta-sosial"), T("public-login-btn"), T("hero-dashboard-btn"), T("hero-peta-btn"), T("speak-landing-pengantar"), T("a11y-assistant-btn")]),
    ("p02_publik", "public", "/publik", [], [T("speak-publik-pembuka"), T("public-privacy-badge"), T("public-card-disabilitas"), T("speak-card-disabilitas"), T("public-card-kemiskinan")]),
    ("p03_publik_grafik", "public", "/publik", [("scroll", T("chart-kemiskinan-a11y-block")), ("click", T("chart-kemiskinan-toggle")), ("wait", 600), ("js", "window.scrollBy(0,-260)")], [T("chart-kemiskinan-ringkasan"), T("chart-kemiskinan-toggle"), T("chart-kemiskinan-speak"), T("chart-kemiskinan-table")]),
    ("p04_peta_sosial", "public", "/publik/peta-sosial", [("wait", 2500)], [T("map-tab-disabilitas"), T("map-level-kecamatan"), T("map-filter-kecamatan"), T("map-search-input"), T("map-reset-btn"), T("map-marker-toggle"), T("map-ranking"), T("inklusi-map-canvas")]),
    ("p05_peta_detail", "public", "/publik/peta-sosial", [("wait", 3500), ("js", "(()=>{const p=[...document.querySelectorAll('path.leaflet-interactive')];const r=p[Math.floor(p.length/2)];r&&r.dispatchEvent(new MouseEvent('click',{bubbles:true}));})()"), ("wait", 1800)], [T("map-detail"), T("map-ajukan-btn"), T("map-detail-close")]),
    ("p06_peta_kemiskinan", "public", "/publik/peta-kemiskinan", [("wait", 2500)], [T("map-level-kelurahan"), T("map-filter-kecamatan"), T("map-source"), T("map-ranking")]),
    ("p07_peta_tabel", "public", "/publik/peta-kemiskinan", [("wait", 1500), ("scroll", T("a11y-map-table")), ("js", "window.scrollBy(0,-80)")], [T("a11y-map-table")]),
    ("p08_flow", "public", "/flow-sistem", [], [T("flow-slide"), T("flow-prev"), T("flow-next")]),
    ("p09_tentang", "public", "/tentang", [], [T("tentang-daftar-ngo")]),
    # ---------------- Aksesibilitas
    ("a01_tampilan", "public", "/publik", [("click", T("a11y-assistant-btn")), ("click", T("a11y-tab-tampilan")), ("wait", 500)], [T("a11y-assistant-btn"), T("a11y-tab-tampilan"), T("a11y-text-large"), T("a11y-contrast"), T("a11y-motion"), T("a11y-rate-normal"), T("a11y-try-voice")]),
    ("a02_tunanetra", "public", "/publik", [("click", T("a11y-assistant-btn")), ("click", T("a11y-tab-netra")), ("wait", 500)], [T("a11y-tab-netra"), T("a11y-read-page"), T("a11y-stop"), T("a11y-jump-1"), T("a11y-read-1"), T("a11y-status")]),
    ("a03_tunanetra2", "public", "/publik", [("click", T("a11y-assistant-btn")), ("click", T("a11y-tab-netra")), ("wait", 400), ("scroll", T("a11y-open-help"))], [T("a11y-toggle-focusread"), T("a11y-toggle-voice"), T("a11y-open-help")]),
    ("a04_tunarungu", "public", "/publik", [("click", T("a11y-assistant-btn")), ("click", T("a11y-tab-rungu")), ("wait", 500)], [T("a11y-tab-rungu"), T("a11y-toggle-captions"), T("a11y-toggle-easy"), T("a11y-toggle-bisindo"), T("a11y-open-transcript"), T("a11y-try-caption")]),
    ("a05_bantuan", "public", "/publik", [("key", "?"), ("wait", 600)], [T("a11y-help-dialog"), T("a11y-help-speak"), T("a11y-help-close")]),
    ("a06_bahasa_mudah", "public", "/publik", [("js", "localStorage.setItem('a11y_easy','true')"), ("reload", ""), ("wait", 2500)], [T("a11y-easy-read"), T("a11y-easy-speak-0")]),
    ("a07_subtitle", "public", "/publik", [("click", T("speak-publik-pembuka")), ("wait", 4500)], [T("speak-publik-pembuka"), T("a11y-caption-bar")]),
    # ---------------- Login
    ("l01_login", "public", "/login", [], [T("auth-tab-login"), T("login-email"), T("login-password"), T("login-submit"), T("auth-tab-ngo"), T("auth-tab-register")]),
    ("l02_daftar_ngo", "public", "/login", [("click", T("auth-tab-ngo")), ("wait", 600)], [T("auth-tab-ngo"), "form", "form button[type=submit]"]),
    # ---------------- Admin / Super Admin
    ("d01_dashboard", "admin", "/dashboard", [("wait", 1500)], [T("sidebar"), T("sidebar-user"), T("notif-bell"), T("logout-btn"), T("admin-overview")]),
    ("d02_peta_kemiskinan", "admin", "/peta-kemiskinan", [("wait", 2500)], [T("kemiskinan-tab-wilayah"), T("kemiskinan-tab-bangunan"), T("map-level-kelurahan"), T("map-ranking")]),
    ("d03_peta_dasar", "admin", "/peta-dasar", [("wait", 1500)], [T("kpi-luas-kota"), T("kpi-jalan"), T("panel-jalan"), T("panel-layers")]),
    ("d04_gis_koordinat", "admin", "/gis-koordinat", [("wait", 1500)], [T("kg-kecamatan"), T("kg-peta"), T("kg-tabel")]),
    ("d05_disabilitas", "admin", "/disabilitas", [("wait", 2000)], [T("btn-input-disabilitas"), T("dis-export"), T("kpi-dis-total"), T("chart-ragam"), T("chart-dis-kelurahan")]),
    ("d06_input_menu", "admin", "/disabilitas", [("wait", 1500), ("click", T("btn-input-disabilitas")), ("wait", 600)], [T("btn-input-disabilitas"), "[role=menu]"]),
    ("d07_data_stunting", "admin", "/data-stunting", [("wait", 2000), ("js", "document.querySelectorAll('[data-testid=stunting-row] td:nth-child(1),[data-testid=stunting-row] td:nth-child(3),[data-testid=stunting-row] td:nth-child(5),[data-testid=stunting-row] td:nth-child(9)').forEach(e=>e.style.filter='blur(5px)')")], [T("btn-input-stunting"), T("stunting-search"), T("stunting-filter-status"), T("stunting-row")]),
    ("d08_import_stunting", "admin", "/data-stunting", [("wait", 1500), ("js", "document.querySelectorAll('[data-testid=stunting-row] td:nth-child(1),[data-testid=stunting-row] td:nth-child(3),[data-testid=stunting-row] td:nth-child(5),[data-testid=stunting-row] td:nth-child(9)').forEach(e=>e.style.filter='blur(5px)')"), ("click", T("btn-input-stunting")), ("wait", 500), ("click", "[role=menuitem] >> nth=0"), ("wait", 1000)], ["[role=dialog]", "[role=dialog] input[type=file]", "[role=dialog] button >> nth=-1"]),
    ("d09_data_ats", "admin", "/data-ats", [("wait", 2000)], [T("btn-input-ats"), T("data-ats")]),
    ("d10_kemiskinan", "admin", "/sosial", [("wait", 2000)], [T("filter-kecamatan"), T("filter-kelurahan"), T("filter-desil"), T("filter-pbi"), T("sosial-export"), T("kpi-households"), T("chart-desil")]),
    ("d11_rumah_tangga", "admin", "/rumah-tangga", [("wait", 2000)], [T("btn-input-data"), T("rt-export"), T("rt-kecamatan"), T("rt-risk"), T("rt-search"), T("tabel-rt")]),
    ("d12_rumah_bangunan", "admin", "/peta-rumah", [("wait", 2000), ("js", "document.querySelectorAll('[data-testid=tabel-rumah] tbody td:nth-child(2)').forEach(e=>e.style.filter='blur(5px)')")], [T("btn-import-geojson"), T("btn-tambah-rumah"), T("dr-filter-kelurahan"), T("dr-filter-status"), T("dr-search"), T("tabel-rumah")]),
    ("d13_inquiry_admin", "admin", "/ngo/inquiry", [("wait", 2000)], [T("inquiry-filter-status"), T("inquiry-filter-kategori"), T("inquiry-search"), T("inquiry-new-btn"), "[data-testid^=inquiry-row-]"]),
    ("d14_inquiry_detail", "admin", "/ngo/inquiry", [("wait", 2000), ("click", "[data-testid^=inquiry-row-] a, [data-testid^=inquiry-row-]"), ("wait", 2000)], [T("inquiry-detail"), T("inquiry-actions"), T("inquiry-note"), T("inquiry-history")]),
    ("d15_program", "admin", "/program", [("wait", 2000)], [T("program-manajemen"), T("cerita-list"), T("musrenbang-filter")]),
    ("d16_prioritas", "admin", "/prioritas", [("wait", 2000)], [T("prioritas-kecamatan"), T("page-prioritas")]),
    ("d17_stunting_program", "admin", "/stunting", [("wait", 2000)], [T("kpi-opd"), T("kpi-anggaran-2025"), T("chart-stunting-opd"), T("stunting-opd"), T("stunting-search")]),
    ("d18_rad", "admin", "/rad", [("wait", 2000)], [T("btn-input-rad"), T("rad-export"), T("chart-rad-target"), T("rad-status"), T("rad-filter-status"), T("rad-search")]),
    ("d19_bantuan", "admin", "/bantuan", [("wait", 2000), ("js", "document.querySelectorAll('[data-testid=tabel-bantuan] tbody td:nth-child(2)').forEach(e=>e.style.filter='blur(5px)')")], [T("bantuan-filter-kelurahan"), T("bantuan-filter-jenis"), T("tabel-bantuan")]),
    ("d20_ai_assistant", "admin", "/ai-assistant", [("wait", 2000)], [T("ai-model-select"), T("ai-wilayah-select"), T("ai-suggestion-0"), T("ai-question-input"), T("ai-send-btn"), T("ai-new-chat"), T("ai-session-list")]),
    ("d21_analisa_ai", "admin", "/analisa-ai", [("wait", 2000)], [T("ai-kategori"), T("ai-wilayah"), T("ai-analyze-btn"), T("ai-history"), T("ai-compare-btn")]),
    ("d22_laporan_wilayah", "admin", "/laporan-wilayah", [("wait", 1500)], [T("laporan-kecamatan"), T("laporan-kelurahan"), T("laporan-unduh-btn")]),
    ("d23_rekap", "admin", "/rekap", [("wait", 2000)], [T("rekap-kpi"), T("rekap-download-all"), T("rekap-pdf-btn"), T("rekap-excel-btn")]),
    ("d24_input_data", "admin", "/input-data", [("wait", 2000), ("click", T("region-select-Tallo")), ("wait", 800)], [T("region-list"), T("kelurahan-list")]),
    ("d25_verifikasi", "admin", "/verifikasi", [("wait", 1500)], [T("verif-tab-pending"), T("verif-tab-approved"), T("verif-tab-rejected")]),
    ("d26_impor", "admin", "/impor", [("wait", 2000)], [T("btn-template"), T("wizard-stepper"), T("panel-upload"), T("panel-riwayat")]),
    ("d27_kualitas", "admin", "/administrasi", [("wait", 2000)], [T("kpi-households"), T("kpi-issues"), T("tabel-import-jenis"), T("quality-summary")]),
    ("d28_master_kode", "admin", "/master-kode", [("wait", 1500)], [T("mk-tambah"), T("mk-muat-ulang"), T("mk-field"), T("mk-cari")]),
    ("d29_kelola_user", "admin", "/kelola-petugas", [("wait", 1500)], [T("add-user-btn"), "[data-testid^=edit-] >> nth=0", "[data-testid^=reset-] >> nth=0", "[data-testid^=deactivate-] >> nth=0", "[data-testid^=delete-] >> nth=0", T("users-table")]),
    ("d30_role", "admin", "/role-permission", [("wait", 1500)], [T("role-permission")]),
    ("d31_audit", "admin", "/audit-log", [("wait", 1500)], [T("audit-filter-aksi"), "[data-testid=audit-row] >> nth=0"]),
    ("d32_email", "admin", "/notifikasi-email", [("wait", 1500)], [T("smtp-status"), T("email-count-terkirim"), T("email-retry-btn"), T("email-test-input"), T("email-test-btn")]),
    ("d33_bisindo", "admin", "/aksesibilitas-bisindo", [("wait", 1500)], [T("bisindo-url-beranda"), T("bisindo-judul-beranda"), T("bisindo-save-beranda"), T("bisindo-status-beranda")]),
    ("d34_mode_aksesibilitas", "admin", "/aksesibilitas", [("wait", 1500)], [T("mode-tunanetra"), T("tunanetra-speak"), T("tunanetra-bigtext"), T("tunanetra-contrast"), T("mode-tunarungu")]),
    # ---------------- NGO
    ("n01_ngo_beranda", "ngo", "/ngo/inquiry", [("wait", 2000)], [T("nav-ngo-inquiry"), T("nav-ngo-inquiry-baru"), T("nav-ngo-peta-sosial"), T("nav-ngo-peta-kemiskinan"), T("nav-ngo-statistik"), T("nav-ngo-laporan"), T("inquiry-new-btn")]),
    ("n02_ngo_form1", "ngo", "/ngo/inquiry/baru", [("wait", 2000)], [T("inq-nama-ngo"), T("inq-nama-pic"), T("inq-email"), T("inq-telepon"), T("inq-kategori"), T("inq-kecamatan"), T("inq-kelurahan")]),
    ("n03_ngo_form2", "ngo", "/ngo/inquiry/baru", [("wait", 2000), ("scroll", T("inq-submit"))], [T("inq-permasalahan"), T("inq-kebutuhan"), T("inq-program"), T("inq-target"), T("inq-jumlah"), T("inq-durasi"), T("inq-anggaran"), T("inq-lampiran"), T("inq-submit")]),
    ("n04_ngo_peta", "ngo", "/ngo/peta-sosial", [("wait", 2500)], [T("map-tab-stunting"), T("map-ranking")]),
    ("n05_ngo_statistik", "ngo", "/ngo/statistik", [("wait", 2500)], [T("public-card-disabilitas")]),
    # ---------------- Petugas / Operator
    ("t01_petugas_dashboard", "petugas", "/dashboard", [("wait", 2000)], [T("sidebar"), T("sidebar-user")]),
]

TEAL, AMBER = (17, 122, 105), (244, 182, 58)
try:
    FONT = ImageFont.truetype("/usr/share/fonts/truetype/liberation/LiberationSans-Bold.ttf", 19)
except Exception:
    FONT = ImageFont.load_default()


def annotate(path, boxes, vw, vh):
    im = Image.open(path).convert("RGB")
    d = ImageDraw.Draw(im)
    for n, b in boxes:
        x, y, w, h = b
        x1, y1 = max(2, x - 4), max(2, y - 4)
        x2, y2 = min(vw - 3, x + w + 4), min(vh - 3, y + h + 4)
        d.rounded_rectangle([x1, y1, x2, y2], radius=8, outline=AMBER, width=3)
        r = 15
        cx, cy = max(r + 2, min(x1, vw - r - 2)), max(r + 2, y1)
        d.ellipse([cx - r - 2, cy - r - 2, cx + r + 2, cy + r + 2], fill=(255, 255, 255))
        d.ellipse([cx - r, cy - r, cx + r, cy + r], fill=TEAL)
        t = str(n)
        tw = d.textlength(t, font=FONT)
        d.text((cx - tw / 2, cy - 11), t, font=FONT, fill=(255, 255, 255))
    im.save(path.replace(".png", ".jpg"), "JPEG", quality=84, optimize=True)
    os.remove(path)


async def login(ctx, role):
    pg = await ctx.new_page()
    await pg.goto(BASE + "/login")
    await pg.wait_for_selector(T("login-email"))
    await pg.fill(T("login-email"), ACC[role][0])
    await pg.fill(T("login-password"), ACC[role][1])
    await pg.click(T("login-submit"))
    await pg.wait_for_timeout(3500)
    return pg


async def main():
    marks_path = f"{OUT}/marks.json"
    allmarks = json.load(open(marks_path)) if os.path.exists(marks_path) else {}
    vw, vh = 1440, 900
    async with async_playwright() as p:
        b = await p.chromium.launch(executable_path="/usr/bin/chromium", args=["--no-sandbox"])
        pages = {}
        for sid, role, url, acts, marks in SHOTS:
            if ONLY and sid not in ONLY:
                continue
            if role not in pages:
                ctx = await b.new_context(viewport={"width": vw, "height": vh}, locale="id-ID")
                pages[role] = await login(ctx, role) if role != "public" else await ctx.new_page()
            pg = pages[role]
            try:
                await pg.evaluate("localStorage.removeItem('a11y_easy')") if pg.url.startswith("http") else None
                await pg.goto(BASE + url, wait_until="domcontentloaded")
                await pg.wait_for_timeout(2500)
                for a, v in acts:
                    try:
                        if a == "click":
                            await pg.locator(v).first.click(timeout=6000)
                        elif a == "scroll":
                            await pg.locator(v).first.scroll_into_view_if_needed(timeout=6000)
                        elif a == "wait":
                            await pg.wait_for_timeout(int(v))
                        elif a == "key":
                            await pg.keyboard.press(v)
                        elif a == "js":
                            await pg.evaluate(v)
                        elif a == "reload":
                            await pg.reload(wait_until="domcontentloaded")
                    except Exception as e:
                        print(f"  [{sid}] aksi {a} {v} gagal: {str(e)[:80]}")
                await pg.wait_for_timeout(700)
                boxes, missing = [], []
                for i, sel in enumerate(marks, 1):
                    try:
                        loc = pg.locator(sel).first
                        bb = await loc.bounding_box(timeout=2500)
                        if bb and bb["width"] > 0 and bb["y"] < vh and bb["y"] + bb["height"] > 0:
                            x, y = bb["x"], max(0, bb["y"])
                            h = min(bb["height"], vh - y)
                            boxes.append((i, (x, y, min(bb["width"], vw - x), h)))
                        else:
                            missing.append(i)
                    except Exception:
                        missing.append(i)
                png = f"{OUT}/{sid}.png"
                await pg.screenshot(path=png)
                annotate(png, boxes, vw, vh)
                allmarks[sid] = {"url": url, "role": role, "marks": len(marks), "missing": missing}
                print(f"OK {sid} marks={len(marks)} missing={missing}", flush=True)
            except Exception as e:
                print(f"ERR {sid}: {str(e)[:150]}", flush=True)
            if sid == "a06_bahasa_mudah":
                await pg.evaluate("localStorage.setItem('a11y_easy','false')")
        await b.close()
    json.dump(allmarks, open(marks_path, "w"), indent=1)

asyncio.run(main())
