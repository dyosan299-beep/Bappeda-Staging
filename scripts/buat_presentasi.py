"""Generator presentasi PETA INKLUSI (.pptx, dapat diedit).

Pemakaian:
  python scripts/buat_presentasi.py
Membaca: docs/presentasi/summary.json (GET /api/public/summary) & docs/presentasi/shots/*.png
Menulis: docs/presentasi/Presentasi_Peta_Inklusi.pptx
"""
import json
from pathlib import Path

from PIL import Image
from pptx import Presentation
from pptx.chart.data import CategoryChartData
from pptx.dml.color import RGBColor
from pptx.enum.chart import XL_CHART_TYPE, XL_LEGEND_POSITION, XL_LABEL_POSITION
from pptx.enum.shapes import MSO_SHAPE
from pptx.enum.text import PP_ALIGN, MSO_ANCHOR
from pptx.util import Inches, Pt, Emu

ROOT = Path(__file__).resolve().parent.parent
DOC = ROOT / "docs" / "presentasi"
SHOTS = DOC / "shots"
LOGO = ROOT / "frontend" / "public" / "logo-peta-inklusi.png"
OUT = DOC / "Presentasi_Peta_Inklusi.pptx"
S = json.loads((DOC / "summary.json").read_text())

# ---------------------------------------------------------------- tokens (warna aplikasi)
NAVY = RGBColor(0x1E, 0x29, 0x3B)
NAVY2 = RGBColor(0x33, 0x3D, 0x55)
NAVY_BG = RGBColor(0x27, 0x2E, 0x41)  # = latar logo
TEAL = RGBColor(0x6F, 0xE3, 0xCF)
TEAL_D = RGBColor(0x11, 0x7A, 0x69)
DIS = RGBColor(0x0F, 0x7B, 0x6C)
STU = RGBColor(0xC0, 0x39, 0x5A)
ATS = RGBColor(0xB7, 0x79, 0x1F)
MIS = RGBColor(0x33, 0x41, 0x55)
BG = RGBColor(0xF8, 0xFA, 0xFC)
INK = RGBColor(0x0F, 0x17, 0x2A)
MUTED = RGBColor(0x64, 0x74, 0x8B)
LINE = RGBColor(0xE2, 0xE8, 0xF0)
WHITE = RGBColor(0xFF, 0xFF, 0xFF)
FONT = "Segoe UI"
FONT_H = "Segoe UI Semibold"

prs = Presentation()
prs.slide_width, prs.slide_height = Inches(13.333), Inches(7.5)
BLANK = prs.slide_layouts[6]
SW, SH = 13.333, 7.5
PAGE = {"n": 0}


def fmt(n):
    return f"{n:,.0f}".replace(",", ".")


def rect(slide, x, y, w, h, fill, line=None, shape=MSO_SHAPE.RECTANGLE, radius=None):
    s = slide.shapes.add_shape(shape, Inches(x), Inches(y), Inches(w), Inches(h))
    s.fill.solid()
    s.fill.fore_color.rgb = fill
    if line is None:
        s.line.fill.background()
    else:
        s.line.color.rgb = line
        s.line.width = Pt(1)
    s.shadow.inherit = False
    if radius is not None and shape == MSO_SHAPE.ROUNDED_RECTANGLE:
        s.adjustments[0] = radius
    return s


def text(slide, x, y, w, h, content, size=16, color=INK, bold=False, font=FONT, align=PP_ALIGN.LEFT,
         anchor=MSO_ANCHOR.TOP, spacing=1.1):
    tb = slide.shapes.add_textbox(Inches(x), Inches(y), Inches(w), Inches(h))
    tf = tb.text_frame
    tf.word_wrap = True
    tf.vertical_anchor = anchor
    tf.margin_left = tf.margin_right = Inches(0.02)
    tf.margin_top = tf.margin_bottom = Inches(0.02)
    lines = content if isinstance(content, list) else [content]
    for i, ln in enumerate(lines):
        p = tf.paragraphs[0] if i == 0 else tf.add_paragraph()
        p.alignment = align
        p.line_spacing = spacing
        r = p.add_run()
        r.text = ln
        r.font.size = Pt(size)
        r.font.color.rgb = color
        r.font.bold = bold
        r.font.name = font
    return tb


def bullets(slide, x, y, w, h, items, size=16, color=INK, dot=TEAL_D, gap=8):
    """items: list of str atau (judul, keterangan)."""
    tb = slide.shapes.add_textbox(Inches(x), Inches(y), Inches(w), Inches(h))
    tf = tb.text_frame
    tf.word_wrap = True
    for i, it in enumerate(items):
        p = tf.paragraphs[0] if i == 0 else tf.add_paragraph()
        p.space_after = Pt(gap)
        p.line_spacing = 1.1
        r0 = p.add_run()
        r0.text = "■  "
        r0.font.size = Pt(size - 6)
        r0.font.color.rgb = dot
        r0.font.name = FONT
        if isinstance(it, tuple):
            r1 = p.add_run()
            r1.text = it[0]
            r1.font.bold = True
            r1.font.size = Pt(size)
            r1.font.color.rgb = color
            r1.font.name = FONT_H
            r2 = p.add_run()
            r2.text = " — " + it[1]
            r2.font.size = Pt(size)
            r2.font.color.rgb = MUTED if color == INK else color
            r2.font.name = FONT
        else:
            r1 = p.add_run()
            r1.text = it
            r1.font.size = Pt(size)
            r1.font.color.rgb = color
            r1.font.name = FONT
    return tb


def image_fit(slide, path, x, y, w, h, border=True):
    path = Path(path)
    iw, ih = Image.open(path).size
    scale = min(w / iw, h / ih)
    dw, dh = iw * scale, ih * scale
    dx, dy = x + (w - dw) / 2, y + (h - dh) / 2
    if border:
        rect(slide, dx - 0.04, dy - 0.04, dw + 0.08, dh + 0.08, WHITE, line=LINE)
    return slide.shapes.add_picture(str(path), Inches(dx), Inches(dy), Inches(dw), Inches(dh))


def caption(slide, x, y, w, t):
    text(slide, x, y, w, 0.3, t, size=11, color=MUTED, align=PP_ALIGN.CENTER)


def notes(slide, t):
    slide.notes_slide.notes_text_frame.text = t


def base(kicker, title, dark=False):
    PAGE["n"] += 1
    s = prs.slides.add_slide(BLANK)
    rect(s, 0, 0, SW, SH, NAVY_BG if dark else BG)
    if not dark:
        rect(s, 0, 0, 0.18, SH, TEAL_D)
    tc = TEAL if dark else TEAL_D
    text(s, 0.7, 0.45, 11, 0.35, kicker.upper(), size=12, color=tc, bold=True, font=FONT_H)
    text(s, 0.7, 0.78, 11.9, 0.8, title, size=30, color=WHITE if dark else INK, font=FONT_H)
    # footer
    fc = RGBColor(0x94, 0xA3, 0xB8)
    text(s, 0.7, 7.02, 8, 0.3, "PETA INKLUSI Bappeda Kota Makassar", size=10, color=fc)
    text(s, SW - 1.4, 7.02, 0.8, 0.3, str(PAGE["n"]), size=10, color=fc, align=PP_ALIGN.RIGHT)
    return s


def stat_card(s, x, y, w, h, label, value, unit, accent, note=None, dark=False):
    rect(s, x, y, w, h, NAVY2 if dark else WHITE, line=None if dark else LINE)
    rect(s, x, y, w, 0.08, accent)
    text(s, x + 0.25, y + 0.25, w - 0.5, 0.3, label.upper(), size=11, color=accent if not dark else TEAL,
         bold=True, font=FONT_H)
    text(s, x + 0.25, y + 0.55, w - 0.5, 0.7, value, size=34, color=WHITE if dark else INK, font=FONT_H)
    text(s, x + 0.25, y + 1.3, w - 0.5, 0.3, unit, size=12, color=MUTED if not dark else LINE)
    if note:
        text(s, x + 0.25, y + 1.62, w - 0.5, h - 1.7, note, size=10, color=MUTED)


def style_chart(chart, legend=True, size=11):
    chart.font.size = Pt(size)
    chart.font.name = FONT
    chart.font.color.rgb = INK
    chart.has_title = False
    chart.has_legend = legend
    if legend:
        chart.legend.position = XL_LEGEND_POSITION.TOP
        chart.legend.include_in_layout = False
        chart.legend.font.size = Pt(size)


K = S["kategori"]
PK = S["per_kecamatan"]
TR = S["tren"]

# ================================================================ 1. COVER
PAGE["n"] += 1
s = prs.slides.add_slide(BLANK)
rect(s, 0, 0, SW, SH, NAVY_BG)
rect(s, 0, SH - 0.12, SW / 4, 0.12, DIS)
rect(s, SW / 4, SH - 0.12, SW / 4, 0.12, STU)
rect(s, SW / 2, SH - 0.12, SW / 4, 0.12, ATS)
rect(s, 3 * SW / 4, SH - 0.12, SW / 4, 0.12, TEAL)
image_fit(s, LOGO, 8.2, 1.3, 4.4, 3.8, border=False)
text(s, 0.8, 1.35, 7, 0.4, "PRESENTASI APLIKASI WEB", size=14, color=TEAL, bold=True, font=FONT_H)
text(s, 0.8, 1.8, 7.4, 1.0, "PETA INKLUSI", size=54, color=WHITE, font=FONT_H, spacing=1.0)
text(s, 0.8, 2.8, 7.4, 0.7, "Bappeda Kota Makassar", size=32, color=TEAL, font=FONT_H, spacing=1.0)
text(s, 0.8, 3.75, 7.0, 1.2, "Data sosial terintegrasi untuk program yang tepat sasaran — Disabilitas, "
     "Stunting, Anak Tidak Sekolah, dan Kemiskinan hingga tingkat kelurahan.", size=17,
     color=RGBColor(0xCB, 0xD5, 0xE1))
rect(s, 0.8, 5.3, 3.3, 0.5, TEAL, shape=MSO_SHAPE.ROUNDED_RECTANGLE, radius=0.5)
text(s, 0.8, 5.3, 3.3, 0.5, "Kota Makassar · 2026", size=14, color=NAVY, bold=True, font=FONT_H,
     align=PP_ALIGN.CENTER, anchor=MSO_ANCHOR.MIDDLE)
notes(s, "Pembukaan. Perkenalkan PETA INKLUSI sebagai platform data sosial terpadu Bappeda Kota Makassar. "
         "Sampaikan bahwa presentasi mencakup manfaat kebijakan (pimpinan), cara kerja (OPD & NGO), "
         "dan fondasi teknis (tim IT).")

# ================================================================ 2. AGENDA
s = base("Agenda", "Yang akan kita bahas")
agenda = [("01", "Latar belakang & solusi", "Mengapa PETA INKLUSI dibutuhkan"),
          ("02", "Potret data Kota Makassar", "4 data utama, sebaran, dan tren"),
          ("03", "Fitur untuk publik", "Dashboard informasi umum & peta interaktif"),
          ("04", "Kolaborasi OPD & NGO", "Hak akses, alur inquiry, cerita dampak"),
          ("05", "Alat kerja internal", "Dashboard, prioritas intervensi, laporan PDF, impor data"),
          ("06", "Teknologi & keamanan", "Arsitektur, privasi data, deployment"),
          ("07", "Manfaat & tindak lanjut", "Nilai bagi setiap pemangku kepentingan")]
for i, (no, t, d) in enumerate(agenda):
    col, row = i % 2, i // 2
    x, y = 0.7 + col * 6.1, 1.85 + row * 1.25
    rect(s, x, y, 5.8, 1.05, WHITE, line=LINE)
    text(s, x + 0.25, y + 0.18, 0.9, 0.7, no, size=28, color=TEAL_D, font=FONT_H)
    text(s, x + 1.2, y + 0.17, 4.4, 0.4, t, size=17, color=INK, font=FONT_H)
    text(s, x + 1.2, y + 0.56, 4.4, 0.4, d, size=12, color=MUTED)
notes(s, "Alur presentasi: dari masalah ke solusi, lalu data, fitur per pengguna, teknis, dan tindak lanjut.")

# ================================================================ 3. LATAR BELAKANG
s = base("Latar belakang", "Tantangan pengelolaan data sosial")
probs = [("Data tersebar", "Data disabilitas, stunting, anak tidak sekolah, dan kemiskinan berada di OPD & "
          "format berbeda (Excel, rekap manual, DTSEN).", STU),
         ("Sasaran kurang tepat", "Program intervensi sulit diarahkan ke kelurahan yang paling membutuhkan "
          "tanpa peta sebaran yang utuh.", ATS),
         ("Kolaborasi belum terpadu", "Usulan program NGO/mitra belum memiliki kanal resmi, jejak status, "
          "dan bukti dampak yang terdokumentasi.", MIS),
         ("Risiko privasi", "Data pribadi (NIK, alamat, kontak) rawan terpapar bila dibagikan tanpa "
          "pengendalian akses.", DIS)]
for i, (t, d, c) in enumerate(probs):
    x = 0.7 + i * 3.05
    rect(s, x, 1.9, 2.85, 3.6, WHITE, line=LINE)
    rect(s, x, 1.9, 2.85, 0.08, c)
    text(s, x + 0.25, 2.2, 2.4, 0.5, f"0{i + 1}", size=26, color=c, font=FONT_H)
    text(s, x + 0.25, 2.75, 2.4, 0.8, t, size=17, color=INK, font=FONT_H, spacing=1.0)
    text(s, x + 0.25, 3.6, 2.4, 1.8, d, size=13, color=MUTED)
rect(s, 0.7, 5.8, 11.95, 0.85, NAVY)
text(s, 1.0, 5.8, 11.4, 0.85, "Kebutuhan: satu sumber data sosial yang terpadu, aman, berbasis wilayah, dan "
     "mendorong kolaborasi program yang terukur.", size=16, color=WHITE, font=FONT_H, anchor=MSO_ANCHOR.MIDDLE)
notes(s, "Tekankan empat masalah utama. Untuk pimpinan: dampaknya pada ketepatan sasaran anggaran. "
         "Untuk tim IT: fragmentasi format data dan risiko kebocoran data pribadi.")

# ================================================================ 4. SOLUSI
s = base("Solusi", "PETA INKLUSI: satu platform, empat data utama")
image_fit(s, SHOTS / "landing.png", 6.35, 1.75, 6.3, 3.55)
caption(s, 6.35, 5.4, 6.3, "Beranda publik PETA INKLUSI")
bullets(s, 0.7, 1.85, 5.4, 4.8, [
    ("Terintegrasi", "Disabilitas, Stunting, ATS, dan Kemiskinan dalam satu dashboard."),
    ("Berbasis wilayah", f"{S['wilayah']['kecamatan']} kecamatan & {S['wilayah']['kelurahan']} kelurahan, "
     "peta interaktif hingga tingkat kelurahan."),
    ("Terbuka namun aman", "Publik melihat data agregat; data pribadi hanya untuk peran berwenang."),
    ("Kolaboratif", "NGO mengajukan program, Bappeda meninjau, dampak didokumentasikan."),
    ("Siap dipakai", "Web responsif dengan fitur aksesibilitas (ukuran teks, kontras, suara)."),
], size=15)
notes(s, "PETA INKLUSI menjawab keempat tantangan. Tunjukkan beranda: 4 kartu data utama dan galeri program.")

# ================================================================ 5. 4 DATA UTAMA
s = base("Potret data", "Empat data utama Kota Makassar")
cards = [("Disabilitas", fmt(K["disabilitas"]["total"]), K["disabilitas"]["satuan"], DIS, K["disabilitas"]["sumber"]),
         ("Stunting", fmt(K["stunting"]["total"]), K["stunting"]["satuan"], STU,
          f"{fmt(K['stunting'].get('terdata_by_name', 0))} balita terdata by-name"),
         ("Anak Tidak Sekolah", fmt(K["ats"]["total"]), K["ats"]["satuan"], ATS, K["ats"]["sumber"]),
         ("Kemiskinan", fmt(K["kemiskinan"]["total"]), K["kemiskinan"]["satuan"], MIS,
          f"{str(K['kemiskinan']['persen_kota']).replace('.', ',')}% penduduk miskin (2025)")]
for i, (l, v, u, c, n) in enumerate(cards):
    stat_card(s, 0.7 + i * 3.05, 1.8, 2.85, 2.35, l, v, u, c, note=n)
mini = [("Kecamatan", fmt(S["wilayah"]["kecamatan"])), ("Kelurahan", fmt(S["wilayah"]["kelurahan"])),
        ("Rumah tangga DTSEN", fmt(S["dtsen"]["rumah_tangga"])), ("Individu DTSEN", fmt(S["dtsen"]["individu"]))]
for i, (l, v) in enumerate(mini):
    x = 0.7 + i * 3.05
    rect(s, x, 4.4, 2.85, 1.25, NAVY)
    text(s, x + 0.25, 4.55, 2.4, 0.3, l.upper(), size=11, color=TEAL, bold=True, font=FONT_H)
    text(s, x + 0.25, 4.85, 2.4, 0.6, v, size=28, color=WHITE, font=FONT_H)
text(s, 0.7, 5.9, 11.9, 0.8, "Seluruh angka merupakan data agregat dari dashboard publik PETA INKLUSI "
     f"(diperbarui {S['diperbarui'][:10]}). Data pribadi tidak ditampilkan.", size=12, color=MUTED)
notes(s, "Angka diambil langsung dari API dashboard publik. Anak Tidak Sekolah adalah angka terbesar — "
         "potensi prioritas intervensi pendidikan. Kemiskinan 4,43% (2025) turun dari 4,97% (2024).")

# ================================================================ 6. SEBARAN PER KECAMATAN (chart)
s = base("Potret data", "Sebaran per kecamatan (4 kategori)")
cd = CategoryChartData()
cd.categories = [r["kecamatan"] for r in PK]
cd.add_series("Disabilitas", [r["disabilitas"] for r in PK])
cd.add_series("Stunting", [r["stunting"] for r in PK])
cd.add_series("Anak Tidak Sekolah", [r["ats"] for r in PK])
cd.add_series("Kemiskinan (KK)", [r["kemiskinan"] for r in PK])
gf = s.shapes.add_chart(XL_CHART_TYPE.COLUMN_CLUSTERED, Inches(0.7), Inches(1.7), Inches(8.6), Inches(5.1), cd)
ch = gf.chart
style_chart(ch, size=10)
for ser, c in zip(ch.series, [DIS, STU, ATS, MIS]):
    ser.format.fill.solid()
    ser.format.fill.fore_color.rgb = c
ch.plots[0].gap_width = 60
ch.value_axis.major_gridlines.format.line.color.rgb = LINE
ch.value_axis.format.line.fill.background()
ch.category_axis.tick_labels.font.size = Pt(9)
top = lambda key: sorted(PK, key=lambda r: r[key], reverse=True)[:3]
rect(s, 9.6, 1.7, 3.05, 5.1, WHITE, line=LINE)
text(s, 9.85, 1.85, 2.6, 0.35, "3 KECAMATAN TERTINGGI", size=11, color=TEAL_D, bold=True, font=FONT_H)
yy = 2.3
for label, key, c in [("Disabilitas", "disabilitas", DIS), ("Stunting", "stunting", STU),
                      ("Anak Tidak Sekolah", "ats", ATS), ("Kemiskinan", "kemiskinan", MIS)]:
    text(s, 9.85, yy, 2.6, 0.3, label, size=12, color=c, font=FONT_H)
    text(s, 9.85, yy + 0.3, 2.6, 0.8, [f"{r['kecamatan']} · {fmt(r[key])}" for r in top(key)], size=11,
         color=INK, spacing=1.0)
    yy += 1.12
notes(s, "Grafik dapat diedit (klik kanan > Edit Data). Tallo dan Tamalate konsisten tinggi di beberapa "
         "kategori — kandidat lokasi intervensi terpadu lintas OPD.")

# ================================================================ 7. TREN (charts)
s = base("Potret data", "Tren indikator utama")
cd = CategoryChartData()
cd.categories = [str(r["tahun"]) for r in TR["kemiskinan"]]
cd.add_series("Penduduk miskin (%)", [r["persen"] for r in TR["kemiskinan"]])
gf = s.shapes.add_chart(XL_CHART_TYPE.LINE_MARKERS, Inches(0.7), Inches(2.05), Inches(5.9), Inches(3.9), cd)
ch = gf.chart
style_chart(ch, legend=False)
ser = ch.series[0]
ser.format.line.color.rgb = MIS
ser.format.line.width = Pt(3)
ser.smooth = False
pl = ch.plots[0]
pl.has_data_labels = True
pl.data_labels.number_format = '0.00'
pl.data_labels.number_format_is_linked = False
pl.data_labels.position = XL_LABEL_POSITION.ABOVE
ch.value_axis.major_gridlines.format.line.color.rgb = LINE
text(s, 0.7, 1.7, 5.9, 0.35, "Persentase penduduk miskin Kota Makassar", size=14, color=INK, font=FONT_H)

cd = CategoryChartData()
cd.categories = [str(r["tahun"]) for r in TR["stunting"]]
cd.add_series("e-PPGBM (%)", [r["eppgbm_persen"] for r in TR["stunting"]])
cd.add_series("SSGI (%)", [r["ssgi_persen"] for r in TR["stunting"]])
gf = s.shapes.add_chart(XL_CHART_TYPE.LINE_MARKERS, Inches(6.9), Inches(2.05), Inches(5.75), Inches(3.9), cd)
ch = gf.chart
style_chart(ch)
for ser, c in zip(ch.series, [STU, ATS]):
    ser.format.line.color.rgb = c
    ser.format.line.width = Pt(3)
    ser.smooth = False
ch.plots[0].has_data_labels = True
ch.plots[0].data_labels.position = XL_LABEL_POSITION.ABOVE
ch.value_axis.major_gridlines.format.line.color.rgb = LINE
text(s, 6.9, 1.7, 5.75, 0.35, "Prevalensi stunting (e-PPGBM vs SSGI)", size=14, color=INK, font=FONT_H)
k0, k1 = TR["kemiskinan"][0], TR["kemiskinan"][-1]
st0, st1 = TR["stunting"][0], TR["stunting"][-1]
text(s, 0.7, 6.1, 11.9, 0.8, f"Kemiskinan turun dari {str(k0['persen']).replace('.', ',')}% ({k0['tahun']}) menjadi "
     f"{str(k1['persen']).replace('.', ',')}% ({k1['tahun']}). Stunting e-PPGBM turun dari "
     f"{str(st0['eppgbm_persen']).replace('.', ',')}% ({st0['tahun']}) menjadi "
     f"{str(st1['eppgbm_persen']).replace('.', ',')}% ({st1['tahun']}).", size=13, color=MUTED)
notes(s, "Tren positif pada dua indikator. Catat perbedaan metodologi e-PPGBM (penimbangan) dan SSGI (survei).")

# ================================================================ 8. RAGAM DISABILITAS (doughnut)
s = base("Potret data", "Ragam disabilitas")
rg = sorted(S["disabilitas_ragam"], key=lambda r: r["jumlah"], reverse=True)
cd = CategoryChartData()
cd.categories = [r["kategori"] for r in rg]
cd.add_series("Jumlah", [r["jumlah"] for r in rg])
gf = s.shapes.add_chart(XL_CHART_TYPE.DOUGHNUT, Inches(0.7), Inches(1.7), Inches(6.2), Inches(5.1), cd)
ch = gf.chart
style_chart(ch, legend=False)
palette = [DIS, STU, ATS, MIS, TEAL, RGBColor(0x94, 0xA3, 0xB8)]
for i, pt in enumerate(ch.plots[0].series[0].points):
    pt.format.fill.solid()
    pt.format.fill.fore_color.rgb = palette[i % len(palette)]
ch.plots[0].has_data_labels = True
ch.plots[0].data_labels.show_percentage = True
ch.plots[0].data_labels.show_value = False
ch.plots[0].data_labels.number_format = '0%'
ch.plots[0].data_labels.number_format_is_linked = False
ch.plots[0].data_labels.font.color.rgb = WHITE
ch.plots[0].data_labels.font.bold = True
tot = sum(r["jumlah"] for r in rg)
yy = 1.9
for i, r in enumerate(rg):
    rect(s, 7.3, yy + 0.08, 0.28, 0.28, palette[i % len(palette)])
    text(s, 7.75, yy, 3.9, 0.45, r["kategori"], size=14, color=INK)
    text(s, 11.4, yy, 1.25, 0.45, fmt(r["jumlah"]), size=14, color=INK, font=FONT_H, align=PP_ALIGN.RIGHT)
    yy += 0.62
rect(s, 7.3, yy + 0.1, 5.35, 0.02, LINE)
text(s, 7.75, yy + 0.25, 3.9, 0.45, "Total terdata per ragam", size=14, color=MUTED)
text(s, 11.4, yy + 0.25, 1.25, 0.45, fmt(tot), size=14, color=INK, font=FONT_H, align=PP_ALIGN.RIGHT)
notes(s, "Disabilitas fisik mendominasi. Data ragam mendukung perencanaan RAD Disabilitas dan layanan "
         "yang sesuai kebutuhan (mis. alat bantu dengar, pendampingan disabilitas buta).")

# ================================================================ 9. DASHBOARD PUBLIK
s = base("Fitur publik", "Dashboard Informasi Umum")
image_fit(s, SHOTS / "publik.png", 0.7, 1.7, 7.9, 4.45)
caption(s, 0.7, 6.25, 7.9, "Halaman /publik — dapat diakses tanpa login")
bullets(s, 8.95, 1.8, 3.8, 5, [
    ("Transparan", "angka agregat 4 kategori beserta sumbernya."),
    ("Statistik kecamatan", "grafik perbandingan 15 kecamatan."),
    ("Tren tahunan", "kemiskinan, stunting, ATS, disabilitas."),
    ("Galeri program", "program NGO yang telah selesai."),
    ("Aksesibel", "ukuran teks, kontras tinggi, kurangi animasi, pembaca suara."),
], size=14)
notes(s, "Untuk masyarakat & media. Tidak ada data pribadi, hanya agregat. Fitur aksesibilitas "
         "mendukung warga penyandang disabilitas.")

# ================================================================ 10. PETA
s = base("Fitur publik", "Peta Sosial & Peta Kemiskinan interaktif")
image_fit(s, SHOTS / "peta_sosial_publik.png", 0.7, 1.7, 5.85, 3.3)
caption(s, 0.7, 5.08, 5.85, "Peta Sosial — Disabilitas / Stunting / ATS")
image_fit(s, SHOTS / "peta_kemiskinan_publik.png", 6.8, 1.7, 5.85, 3.3)
caption(s, 6.8, 5.08, 5.85, "Peta Kemiskinan — KK miskin ekstrem")
bullets(s, 0.7, 5.5, 12, 1.4, [
    "Peta tematik (choropleth) + marker proporsional; drill-down dari kecamatan ke kelurahan.",
    "Pencarian wilayah, legenda gradasi, dan peringkat wilayah tertinggi untuk menentukan prioritas.",
], size=14, gap=4)
notes(s, "Peta berbasis Leaflet/OpenStreetMap. Klik kecamatan untuk melihat rincian kelurahan.")

# ================================================================ 11. RBAC
s = base("Kolaborasi", "Pengguna & hak akses (RBAC)")
rows = [("Peran", "Contoh pengguna", "Akses utama", "Data pribadi"),
        ("Publik", "Masyarakat, media", "Dashboard & peta agregat, galeri program", "Tidak"),
        ("NGO / Mitra", "Yayasan, CSR, komunitas", "Ajukan inquiry, pantau status, unggah cerita dampak", "Dimasking"),
        ("Operator / Petugas", "Operator kecamatan & OPD", "Input & kelola data wilayahnya, proses inquiry",
         "Dimasking"),
        ("Verifikator / Admin Bappeda", "Tim Bappeda", "Verifikasi data & inquiry, laporan, notifikasi",
         "Ya (berwenang)"),
        ("Super Admin", "Pengelola sistem", "Kelola pengguna, peran, audit log, impor data", "Ya")]
tbl = s.shapes.add_table(len(rows), 4, Inches(0.7), Inches(1.75), Inches(11.95), Inches(3.9)).table
widths = [2.6, 2.7, 4.8, 1.85]
for i, w in enumerate(widths):
    tbl.columns[i].width = Inches(w)
for r, row in enumerate(rows):
    for c, val in enumerate(row):
        cell = tbl.cell(r, c)
        cell.text = val
        cell.fill.solid()
        cell.fill.fore_color.rgb = NAVY if r == 0 else (WHITE if r % 2 else BG)
        p = cell.text_frame.paragraphs[0]
        p.runs[0].font.size = Pt(13)
        p.runs[0].font.name = FONT_H if (r == 0 or c == 0) else FONT
        p.runs[0].font.color.rgb = WHITE if r == 0 else INK
        cell.vertical_anchor = MSO_ANCHOR.MIDDLE
rect(s, 0.7, 5.9, 11.95, 0.8, NAVY)
text(s, 1.0, 5.9, 11.4, 0.8, "Masking otomatis: NIK, email, dan nomor telepon disamarkan sesuai peran. "
     "Setiap aksi penting tercatat di Audit Log.", size=15, color=WHITE, font=FONT_H, anchor=MSO_ANCHOR.MIDDLE)
notes(s, "Prinsip least privilege. Operator hanya melihat wilayahnya. Data asli hanya untuk peran "
         "berwenang (superadmin, verifikator, admin Bappeda).")

# ================================================================ 12. ALUR INQUIRY
s = base("Kolaborasi", "Alur NGO Inquiry: dari usulan hingga dampak")
steps = [("Daftar NGO", "Akun diaktifkan admin"), ("Ajukan", "SUBMITTED"), ("Ditinjau", "UNDER_REVIEW"),
         ("Verifikasi", "VERIFICATION"), ("Disetujui", "APPROVED"), ("Pelaksanaan", "PROGRAM_IMPLEMENTATION"),
         ("Monitoring", "MONITORING"), ("Selesai", "COMPLETED")]
n = len(steps)
w = 1.38
gap = (11.95 - n * w) / (n - 1)
for i, (t, d) in enumerate(steps):
    x = 0.7 + i * (w + gap)
    c = TEAL_D if i < n - 1 else DIS
    shp = rect(s, x, 2.0, w, 1.35, c if i in (0, n - 1) else WHITE, line=None if i in (0, n - 1) else TEAL_D,
               shape=MSO_SHAPE.ROUNDED_RECTANGLE, radius=0.12)
    tc = WHITE if i in (0, n - 1) else INK
    text(s, x + 0.05, 2.12, w - 0.1, 0.45, t, size=14, color=tc, font=FONT_H, align=PP_ALIGN.CENTER)
    text(s, x + 0.05, 2.6, w - 0.1, 0.65, d, size=9, color=tc if i in (0, n - 1) else MUTED,
         align=PP_ALIGN.CENTER)
    if i < n - 1:
        a = s.shapes.add_shape(MSO_SHAPE.RIGHT_ARROW, Inches(x + w + 0.02), Inches(2.55), Inches(gap - 0.04),
                               Inches(0.25))
        a.fill.solid()
        a.fill.fore_color.rgb = TEAL
        a.line.fill.background()
# cabang revisi/tolak
rect(s, 2.6, 3.75, 4.6, 0.75, RGBColor(0xFD, 0xF2, 0xF4), line=STU, shape=MSO_SHAPE.ROUNDED_RECTANGLE, radius=0.2)
text(s, 2.75, 3.75, 4.3, 0.75, "Perlu revisi (NEED_REVISION) → NGO memperbaiki → ditinjau ulang;  "
     "atau Ditolak (REJECTED) dengan catatan wajib", size=11, color=INK, anchor=MSO_ANCHOR.MIDDLE)
bullets(s, 0.7, 4.85, 12, 2, [
    ("Notifikasi email otomatis", "NGO menerima email setiap perubahan status (antrean SMTP)."),
    ("Jejak lengkap", "setiap transisi status tercatat beserta catatan petugas & waktu."),
    ("Bukti dampak", "setelah COMPLETED, NGO mengunggah foto & testimoni (Cerita Dampak)."),
], size=14, gap=5)
notes(s, "Transisi status dikunci oleh sistem: tidak bisa melompati tahapan. Revisi dan penolakan "
         "wajib disertai catatan agar NGO tahu apa yang perlu diperbaiki.")

# ================================================================ 13. LAYAR NGO
s = base("Kolaborasi", "Pengalaman pengguna NGO")
image_fit(s, SHOTS / "ngo_inquiry_baru.png", 0.7, 1.7, 5.85, 3.3)
caption(s, 0.7, 5.08, 5.85, "Formulir pengajuan program intervensi")
image_fit(s, SHOTS / "ngo_inquiry_detail.png", 6.8, 1.7, 5.85, 3.3)
caption(s, 6.8, 5.08, 5.85, "Detail inquiry, riwayat status & panel cerita dampak")
bullets(s, 0.7, 5.5, 12, 1.4, [
    "NGO memilih kategori & lokasi sasaran berdasarkan peta, melampirkan proposal (PDF/Office/gambar, maks. 10 MB).",
    "Akses peta sosial & statistik agregat untuk merancang program yang tepat sasaran.",
], size=14, gap=4)
notes(s, "Tunjukkan kemudahan: satu formulir, status transparan, dan catatan revisi yang jelas.")

# ================================================================ 14. CERITA DAMPAK
s = base("Kolaborasi", "Cerita Dampak & Galeri Program Selesai")
flow = [("Program selesai", "Status inquiry COMPLETED", TEAL_D), ("NGO unggah cerita", "Maks. 5 foto (8 MB/foto) + hingga 3 testimoni", DIS),
        ("Pembersihan otomatis", "EXIF/GPS dihapus, ukuran & tipe divalidasi", ATS), ("Moderasi Bappeda", "Setujui / sembunyikan publikasi", STU),
        ("Tampil di galeri publik", "Beranda & Dashboard Informasi Umum", MIS)]
for i, (t, d, c) in enumerate(flow):
    y = 1.8 + i * 1.0
    rect(s, 0.7, y, 6.2, 0.82, WHITE, line=LINE)
    rect(s, 0.7, y, 0.1, 0.82, c)
    rect(s, 1.0, y + 0.16, 0.5, 0.5, c, shape=MSO_SHAPE.OVAL)
    text(s, 1.0, y + 0.16, 0.5, 0.5, str(i + 1), size=15, color=WHITE, font=FONT_H, align=PP_ALIGN.CENTER, anchor=MSO_ANCHOR.MIDDLE)
    text(s, 1.7, y + 0.08, 5.1, 0.4, t, size=15, color=INK, font=FONT_H)
    text(s, 1.7, y + 0.44, 5.1, 0.35, d, size=11, color=MUTED)
bullets(s, 7.2, 1.8, 5.5, 5, [
    ("Foto & testimoni", "NGO mengunggah dokumentasi setelah program selesai."),
    ("Privasi foto", "metadata EXIF (lokasi GPS, perangkat) otomatis dihapus."),
    ("Moderasi", "Bappeda memutuskan cerita mana yang dipublikasikan."),
    ("Anonimisasi", "nama NGO disamarkan di galeri publik."),
    ("Akuntabilitas", "publik melihat hasil nyata program kolaborasi."),
], size=14)
notes(s, "Fitur ini membangun kepercayaan publik dan mendorong lebih banyak mitra berkolaborasi. "
         "Penghapusan EXIF mencegah kebocoran lokasi penerima manfaat.")

# ================================================================ 15. DASHBOARD INTERNAL
s = base("Alat kerja internal", "Dashboard pengambilan keputusan")
image_fit(s, SHOTS / "operator_dashboard.png", 0.7, 1.7, 3.85, 2.45)
caption(s, 0.7, 4.2, 3.85, "Dashboard real-time")
image_fit(s, SHOTS / "admin_disabilitas.png", 4.75, 1.7, 3.85, 2.45)
caption(s, 4.75, 4.2, 3.85, "Dashboard disabilitas")
image_fit(s, SHOTS / "admin_prioritas.png", 8.8, 1.7, 3.85, 2.45)
caption(s, 8.8, 4.2, 3.85, "Prioritas intervensi")
bullets(s, 0.7, 4.65, 12, 2.3, [
    ("Dashboard per peran", "admin, operator, dan NGO melihat ringkasan yang relevan."),
    ("Prioritas intervensi", "skoring wilayah untuk menentukan kelurahan yang paling membutuhkan."),
    ("Modul tematik", "Disabilitas (RAD), Stunting (matriks kegiatan & anggaran), ATS, Kemiskinan."),
    ("Manajemen program", "pemantauan program & anggaran lintas OPD."),
], size=14, gap=5)
notes(s, "Untuk pimpinan: dashboard real-time mendukung rapat koordinasi dan penetapan lokus prioritas.")

# ================================================================ 16. LAPORAN & IMPOR
s = base("Alat kerja internal", "Laporan PDF, impor data & notifikasi")
image_fit(s, SHOTS / "admin_laporan.png", 0.7, 1.7, 3.85, 2.45)
caption(s, 0.7, 4.2, 3.85, "Laporan wilayah (PDF)")
image_fit(s, SHOTS / "admin_ats.png", 4.75, 1.7, 3.85, 2.45)
caption(s, 4.75, 4.2, 3.85, "Impor data ATS per kelurahan")
image_fit(s, SHOTS / "admin_role.png", 8.8, 1.7, 3.85, 2.45)
caption(s, 8.8, 4.2, 3.85, "Role & permission")
bullets(s, 0.7, 4.65, 12, 2.3, [
    ("Laporan PDF per kelurahan", "ringkasan 4 kategori siap cetak untuk rapat & musrenbang."),
    ("Import Wizard", "unggah Excel/CSV dengan validasi, pratinjau, dan penyimpanan di database."),
    ("Notifikasi email", "antrean email SMTP dengan status terkirim/gagal dan kirim ulang."),
    ("Audit log", "rekam jejak siapa melakukan apa dan kapan."),
], size=14, gap=5)
notes(s, "Untuk OPD: pembaruan data cukup lewat Import Wizard tanpa bantuan developer.")

# ================================================================ 17. ARSITEKTUR
s = base("Teknologi", "Arsitektur sistem")
boxes = [(0.7, "Pengguna", ["Browser desktop & ponsel", "Publik · NGO · OPD · Admin"], NAVY2),
         (3.8, "Frontend", ["React + TypeScript", "Tailwind · Shadcn UI", "Leaflet / OSM · Recharts"], TEAL_D),
         (6.9, "Backend API", ["Python FastAPI", "JWT (cookie HttpOnly) · RBAC", "ReportLab PDF · Pillow"], DIS),
         (10.0, "Database", ["MariaDB 11", "Data sosial, pengguna,", "inquiry, cerita, file"], MIS)]
for x, t, lines, c in boxes:
    rect(s, x, 1.9, 2.65, 2.0, WHITE, line=LINE)
    rect(s, x, 1.9, 2.65, 0.55, c)
    text(s, x, 1.9, 2.65, 0.55, t, size=15, color=WHITE, font=FONT_H, align=PP_ALIGN.CENTER,
         anchor=MSO_ANCHOR.MIDDLE)
    text(s, x + 0.2, 2.6, 2.3, 1.6, lines, size=12, color=INK, align=PP_ALIGN.CENTER)
for x in (3.38, 6.48, 9.58):
    a = s.shapes.add_shape(MSO_SHAPE.LEFT_RIGHT_ARROW, Inches(x), Inches(2.75), Inches(0.38), Inches(0.3))
    a.fill.solid()
    a.fill.fore_color.rgb = TEAL
    a.line.fill.background()
ext = [("SMTP", "Notifikasi email NGO"), ("LLM (opsional)", "Analisa program & text-to-speech"),
       ("Coolify + Docker", "Deploy satu container, HTTPS"), ("GitHub", "Repositori & versi kode")]
for i, (t, d) in enumerate(ext):
    x = 0.7 + i * 3.1
    rect(s, x, 4.3, 2.95, 1.0, NAVY, shape=MSO_SHAPE.ROUNDED_RECTANGLE, radius=0.12)
    text(s, x + 0.2, 4.38, 2.6, 0.4, t, size=14, color=TEAL, font=FONT_H)
    text(s, x + 0.2, 4.76, 2.6, 0.5, d, size=11, color=WHITE)
text(s, 0.7, 5.6, 11.95, 0.9, "Satu image Docker menyajikan frontend (build statis) dan API /api pada domain "
     "yang sama. Konfigurasi sepenuhnya melalui environment variable — tanpa kredensial di dalam kode.",
     size=13, color=MUTED)
notes(s, "Untuk tim IT: stack open-source, mudah dipelihara. Deployment via Coolify di VPS sendiri "
         "(data tetap di server Pemkot).")

# ================================================================ 18. KEAMANAN
s = base("Keamanan", "Keamanan & perlindungan data pribadi", dark=True)
sec = [("Autentikasi", "JWT dalam cookie HttpOnly, password bcrypt, sesi kedaluwarsa otomatis."),
       ("Otorisasi RBAC", "Akses per peran & per wilayah; transisi status dikunci server."),
       ("Masking PII", "NIK, email, telepon disamarkan untuk peran tanpa kewenangan."),
       ("Publik = agregat", "Dashboard publik tidak pernah memuat data individu."),
       ("Privasi media", "EXIF/GPS foto dihapus; validasi tipe & ukuran berkas."),
       ("Anti-XSS & validasi", "Input dibersihkan dari tag HTML; validasi skema Pydantic."),
       ("Audit log", "Aksi penting tercatat: siapa, apa, kapan."),
       ("Manajemen rahasia", "Tanpa password/kunci di kode; semua via environment variable.")]
for i, (t, d) in enumerate(sec):
    col, row = i % 2, i // 2
    x, y = 0.7 + col * 6.1, 1.8 + row * 1.25
    rect(s, x, y, 5.85, 1.08, NAVY2)
    rect(s, x, y, 0.08, 1.08, TEAL)
    text(s, x + 0.3, y + 0.13, 5.4, 0.4, t, size=15, color=TEAL, font=FONT_H)
    text(s, x + 0.3, y + 0.5, 5.4, 0.55, d, size=12, color=RGBColor(0xE2, 0xE8, 0xF0))
notes(s, "Selaras dengan prinsip UU No. 27/2022 tentang Pelindungan Data Pribadi: minimisasi data, "
         "pembatasan akses, dan akuntabilitas. Audit keamanan pra-rilis telah dilakukan.")

# ================================================================ 19. MANFAAT
s = base("Manfaat", "Nilai bagi setiap pemangku kepentingan")
aud = [("Pimpinan Bappeda / Wali Kota", DIS, ["Keputusan berbasis data hingga kelurahan",
                                              "Lokus prioritas lintas 4 isu sosial",
                                              "Monitoring program & dampak terukur",
                                              "Transparansi kepada publik"]),
       ("OPD & Mitra NGO", ATS, ["Satu kanal resmi usulan program",
                                 "Status & catatan revisi yang jelas",
                                 "Data sasaran siap pakai (peta & PDF)",
                                 "Dampak program terdokumentasi"]),
       ("Tim Teknis / IT", MIS, ["Stack open-source (React, FastAPI, MariaDB)",
                                 "Deploy mandiri via Coolify/Docker",
                                 "Impor data tanpa coding",
                                 "Keamanan & audit bawaan"])]
for i, (t, c, items) in enumerate(aud):
    x = 0.7 + i * 4.05
    rect(s, x, 1.8, 3.85, 4.9, WHITE, line=LINE)
    rect(s, x, 1.8, 3.85, 0.9, c)
    text(s, x + 0.25, 1.8, 3.4, 0.9, t, size=16, color=WHITE, font=FONT_H, anchor=MSO_ANCHOR.MIDDLE)
    bullets(s, x + 0.25, 3.0, 3.4, 3.6, items, size=16, dot=c, gap=14)
notes(s, "Sesuaikan penekanan dengan audiens yang hadir.")

# ================================================================ 20. TINDAK LANJUT & PENUTUP
PAGE["n"] += 1
s = prs.slides.add_slide(BLANK)
rect(s, 0, 0, SW, SH, NAVY_BG)
text(s, 0.7, 0.45, 11, 0.35, "TINDAK LANJUT", size=12, color=TEAL, bold=True, font=FONT_H)
text(s, 0.7, 0.78, 7.5, 0.8, "Langkah berikutnya", size=30, color=WHITE, font=FONT_H)
nxt = [("1", "Go-live produksi", "Deploy versi terbaru ke trirara.my.id melalui Coolify & rotasi kredensial."),
       ("2", "Pemutakhiran data", "OPD memperbarui data berkala melalui Import Wizard (triwulanan)."),
       ("3", "Sosialisasi mitra", "Onboarding NGO/CSR untuk mengajukan program melalui NGO Inquiry."),
       ("4", "Integrasi lanjutan", "Integrasi DTSEN & data OPD lain; perluasan data by-name terverifikasi.")]
for i, (no, t, d) in enumerate(nxt):
    y = 1.85 + i * 1.18
    rect(s, 0.7, y, 0.8, 0.8, TEAL, shape=MSO_SHAPE.OVAL)
    text(s, 0.7, y, 0.8, 0.8, no, size=22, color=NAVY, font=FONT_H, align=PP_ALIGN.CENTER,
         anchor=MSO_ANCHOR.MIDDLE)
    text(s, 1.75, y - 0.02, 6.2, 0.4, t, size=17, color=WHITE, font=FONT_H)
    text(s, 1.75, y + 0.38, 6.2, 0.6, d, size=12, color=RGBColor(0xCB, 0xD5, 0xE1))
image_fit(s, LOGO, 8.6, 1.4, 3.9, 3.3, border=False)
text(s, 8.2, 4.95, 4.7, 0.7, "Terima kasih", size=34, color=WHITE, font=FONT_H, align=PP_ALIGN.CENTER)
text(s, 8.2, 5.65, 4.7, 0.8, ["Bappeda Kota Makassar", "trirara.my.id"], size=14, color=TEAL,
     align=PP_ALIGN.CENTER)
rect(s, 0, SH - 0.12, SW / 4, 0.12, DIS)
rect(s, SW / 4, SH - 0.12, SW / 4, 0.12, STU)
rect(s, SW / 2, SH - 0.12, SW / 4, 0.12, ATS)
rect(s, 3 * SW / 4, SH - 0.12, SW / 4, 0.12, TEAL)
notes(s, "Tutup dengan ajakan: dukungan pimpinan untuk go-live dan instruksi pemutakhiran data oleh OPD. "
         "Buka sesi tanya jawab.")

prs.save(OUT)
print("Tersimpan:", OUT, "slide:", len(prs.slides))
