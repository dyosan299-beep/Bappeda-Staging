"""Membangun 2 file PowerPoint: Presentasi PETA INKLUSI & SOP Penginputan Data."""
import os
from pptx import Presentation
from pptx.dml.color import RGBColor
from pptx.enum.shapes import MSO_CONNECTOR, MSO_SHAPE
from pptx.enum.text import MSO_ANCHOR, PP_ALIGN
from pptx.util import Emu, Inches, Pt

SHOTS = "/app/docs/manual/shots"
OUT = "/app/docs/manual"
LOGO = "/app/frontend/public/logo-peta-inklusi.png"
NAVY, TEAL, DTEAL, MINT, AMBER = RGBColor(0x23, 0x2F, 0x3E), RGBColor(0x11, 0x7A, 0x69), RGBColor(0x0B, 0x4F, 0x45), RGBColor(0x6F, 0xE3, 0xCF), RGBColor(0xF4, 0xB6, 0x3A)
WHITE, INK, MUTED, BG, LINE = RGBColor(255, 255, 255), RGBColor(0x0F, 0x17, 0x2A), RGBColor(0x64, 0x74, 0x8B), RGBColor(0xF4, 0xF7, 0xF8), RGBColor(0xD9, 0xE2, 0xE8)
ROSE, GOLD, SLATE = RGBColor(0xC8, 0x37, 0x5B), RGBColor(0xB7, 0x79, 0x1F), RGBColor(0x3B, 0x4F, 0x6B)
FONT = "Calibri"
W, H = Inches(13.333), Inches(7.5)


class Deck:
    def __init__(self, footer):
        self.p = Presentation(); self.p.slide_width, self.p.slide_height = W, H
        self.footer = footer; self.n = 0

    # ------------------------------------------------ primitives
    def box(self, s, x, y, w, h, fill=None, line=None, shape=MSO_SHAPE.RECTANGLE, radius=None):
        sh = s.shapes.add_shape(shape, x, y, w, h)
        if fill is None:
            sh.fill.background()
        else:
            sh.fill.solid(); sh.fill.fore_color.rgb = fill
        if line is None:
            sh.line.fill.background()
        else:
            sh.line.color.rgb = line; sh.line.width = Pt(1)
        if radius is not None and shape == MSO_SHAPE.ROUNDED_RECTANGLE:
            sh.adjustments[0] = radius
        sh.shadow.inherit = False
        return sh

    def text(self, s, x, y, w, h, txt, size=16, color=INK, bold=False, align=PP_ALIGN.LEFT, anchor=MSO_ANCHOR.TOP, shape=None):
        tb = shape if shape is not None else s.shapes.add_textbox(x, y, w, h)
        tf = tb.text_frame; tf.word_wrap = True; tf.vertical_anchor = anchor
        tf.margin_left = tf.margin_right = Inches(0.08); tf.margin_top = tf.margin_bottom = Inches(0.04)
        lines = txt if isinstance(txt, list) else [txt]
        for i, ln in enumerate(lines):
            par = tf.paragraphs[0] if i == 0 else tf.add_paragraph()
            par.alignment = align
            r = par.add_run(); r.text = ln
            r.font.size = Pt(size); r.font.bold = bold; r.font.color.rgb = color; r.font.name = FONT
        return tb

    def bullets(self, s, x, y, w, h, items, size=15, color=INK, gap=6, dot=TEAL):
        tb = s.shapes.add_textbox(x, y, w, h); tf = tb.text_frame; tf.word_wrap = True
        for i, it in enumerate(items):
            par = tf.paragraphs[0] if i == 0 else tf.add_paragraph()
            par.space_after = Pt(gap)
            r0 = par.add_run(); r0.text = "■  "; r0.font.size = Pt(size - 5); r0.font.color.rgb = dot; r0.font.name = FONT
            if isinstance(it, tuple):
                r1 = par.add_run(); r1.text = it[0] + " "; r1.font.bold = True; r1.font.size = Pt(size); r1.font.color.rgb = color; r1.font.name = FONT
                r2 = par.add_run(); r2.text = it[1]; r2.font.size = Pt(size); r2.font.color.rgb = color; r2.font.name = FONT
            else:
                r = par.add_run(); r.text = it; r.font.size = Pt(size); r.font.color.rgb = color; r.font.name = FONT
        return tb

    def circle_num(self, s, x, y, n, d=Inches(0.5), fill=TEAL, size=16):
        c = self.box(s, x, y, d, d, fill=fill, shape=MSO_SHAPE.OVAL)
        self.text(s, 0, 0, 0, 0, str(n), size=size, color=WHITE, bold=True, align=PP_ALIGN.CENTER, anchor=MSO_ANCHOR.MIDDLE, shape=c)
        return c

    def card(self, s, x, y, w, h, title, body, accent=TEAL, title_size=15, body_size=12):
        self.box(s, x, y, w, h, fill=WHITE, line=LINE, shape=MSO_SHAPE.ROUNDED_RECTANGLE, radius=0.06)
        self.box(s, x, y + Inches(0.18), Inches(0.08), h - Inches(0.36), fill=accent)
        self.text(s, x + Inches(0.22), y + Inches(0.12), w - Inches(0.35), Inches(0.5), title, size=title_size, bold=True, color=NAVY)
        if body:
            if isinstance(body, list):
                self.bullets(s, x + Inches(0.22), y + Inches(0.6), w - Inches(0.35), h - Inches(0.7), body, size=body_size, gap=3, dot=accent)
            else:
                self.text(s, x + Inches(0.22), y + Inches(0.58), w - Inches(0.35), h - Inches(0.65), body, size=body_size, color=MUTED)

    def img(self, s, sid, x, y, w):
        p = f"{SHOTS}/{sid}.jpg"
        if not os.path.exists(p):
            return
        h = int(w * 900 / 1440)
        self.box(s, x - Inches(0.06), y - Inches(0.06), w + Inches(0.12), h + Inches(0.12), fill=WHITE, line=LINE, shape=MSO_SHAPE.ROUNDED_RECTANGLE, radius=0.03)
        s.shapes.add_picture(p, x, y, w, h)

    def arrow(self, s, x1, y1, x2, y2, color=MUTED):
        c = s.shapes.add_connector(MSO_CONNECTOR.STRAIGHT, x1, y1, x2, y2)
        c.line.color.rgb = color; c.line.width = Pt(2)
        ln = c.line._get_or_add_ln()
        from pptx.oxml.ns import qn
        from lxml import etree
        tail = etree.SubElement(ln, qn("a:tailEnd")); tail.set("type", "triangle"); tail.set("w", "med"); tail.set("len", "med")

    def table(self, s, x, y, w, rows, colw, head_fill=NAVY, size=12, rowh=Inches(0.42)):
        t = s.shapes.add_table(len(rows), len(rows[0]), x, y, w, rowh * len(rows)).table
        for j, cw in enumerate(colw):
            t.columns[j].width = cw
        for i, r in enumerate(rows):
            for j, v in enumerate(r):
                c = t.cell(i, j); c.text = ""
                c.fill.solid(); c.fill.fore_color.rgb = head_fill if i == 0 else (WHITE if i % 2 else BG)
                par = c.text_frame.paragraphs[0]; run = par.add_run(); run.text = str(v)
                run.font.size = Pt(size); run.font.name = FONT
                run.font.bold = i == 0 or j == 0; run.font.color.rgb = WHITE if i == 0 else (NAVY if j == 0 else INK)
                c.margin_left = c.margin_right = Inches(0.08); c.vertical_anchor = MSO_ANCHOR.MIDDLE
        return t

    # ------------------------------------------------ slide templates
    def new(self, title, kicker=""):
        s = self.p.slides.add_slide(self.p.slide_layouts[6]); self.n += 1
        self.box(s, 0, 0, W, H, fill=BG)
        self.box(s, 0, 0, W, Inches(1.05), fill=NAVY)
        self.box(s, 0, Inches(1.05), W, Inches(0.05), fill=TEAL)
        if kicker:
            self.text(s, Inches(0.55), Inches(0.12), Inches(9), Inches(0.35), kicker.upper(), size=11, color=MINT, bold=True)
        self.text(s, Inches(0.55), Inches(0.36) if kicker else Inches(0.25), Inches(11), Inches(0.6), title, size=26, color=WHITE, bold=True)
        if os.path.exists(LOGO):
            s.shapes.add_picture(LOGO, W - Inches(1.2), Inches(0.13), Inches(0.8), Inches(0.8))
        self.text(s, Inches(0.55), H - Inches(0.42), Inches(10), Inches(0.3), self.footer, size=9, color=MUTED)
        self.text(s, W - Inches(1.3), H - Inches(0.42), Inches(0.8), Inches(0.3), str(self.n), size=9, color=MUTED, align=PP_ALIGN.RIGHT)
        return s

    def cover(self, title, sub, meta):
        s = self.p.slides.add_slide(self.p.slide_layouts[6]); self.n += 1
        self.box(s, 0, 0, W, H, fill=NAVY)
        self.box(s, 0, H - Inches(0.35), W, Inches(0.35), fill=TEAL)
        if os.path.exists(LOGO):
            s.shapes.add_picture(LOGO, Inches(9.55), Inches(1.15), Inches(3.4), Inches(3.4))
        self.text(s, Inches(0.8), Inches(1.0), Inches(7.6), Inches(0.4), "BAPPEDA KOTA MAKASSAR", size=14, color=MINT, bold=True)
        self.text(s, Inches(0.8), Inches(1.6), Inches(7.8), Inches(2.2), title, size=40, color=WHITE, bold=True)
        self.box(s, Inches(0.8), Inches(3.95), Inches(1.2), Inches(0.08), fill=AMBER)
        self.text(s, Inches(0.8), Inches(4.2), Inches(7.6), Inches(1.4), sub, size=18, color=RGBColor(0xCB, 0xD5, 0xE1))
        self.text(s, Inches(0.8), Inches(6.1), Inches(8), Inches(0.5), meta, size=13, color=WHITE, bold=True)
        return s

    def closing(self, title, sub):
        s = self.p.slides.add_slide(self.p.slide_layouts[6]); self.n += 1
        self.box(s, 0, 0, W, H, fill=NAVY)
        self.box(s, 0, H - Inches(0.35), W, Inches(0.35), fill=TEAL)
        if os.path.exists(LOGO):
            s.shapes.add_picture(LOGO, Inches(5.67), Inches(0.9), Inches(2), Inches(2))
        self.text(s, Inches(1), Inches(3.3), W - Inches(2), Inches(1), title, size=40, color=WHITE, bold=True, align=PP_ALIGN.CENTER)
        self.text(s, Inches(1), Inches(4.4), W - Inches(2), Inches(1.4), sub.split("\n"), size=16, color=MINT, align=PP_ALIGN.CENTER)

    def save(self, name):
        path = f"{OUT}/{name}.pptx"; self.p.save(path); return path


# =================================================================== PRESENTASI
def presentasi():
    d = Deck("PETA INKLUSI — Bappeda Kota Makassar · Presentasi Sistem v1.0 · 2026")
    d.cover("PETA INKLUSI", "Penguatan Perencanaan Pembangunan Inklusi melalui Pemetaan Data Tematik dan Evaluasi Program pada Kelompok Rentan", "Presentasi Sistem · Versi 1.0 · 2026")

    s = d.new("Latar Belakang & Tujuan", "Mengapa PETA INKLUSI")
    d.card(s, Inches(0.55), Inches(1.45), Inches(6), Inches(5.3), "Tantangan", [
        "Data sosial tersebar di banyak OPD dan format (Excel, PDF, GDB)",
        "Risiko data ganda & penerima program yang tumpang tindih",
        "Sulit melihat wilayah prioritas hingga tingkat kelurahan",
        "Usulan program NGO belum terhubung dengan data wilayah",
        "Informasi publik belum ramah penyandang disabilitas"], accent=ROSE, body_size=18)
    d.card(s, Inches(6.8), Inches(1.45), Inches(6), Inches(5.3), "Tujuan", [
        "Satu platform data Disabilitas, Stunting, ATS & Kemiskinan",
        "Master wilayah tunggal: Kota → Kecamatan → Kelurahan",
        "Validasi & verifikasi berlapis agar data tidak ganda",
        "Penetapan sasaran program berbasis peta & skor prioritas",
        "Layanan publik inklusif: suara, subtitle, Bahasa Mudah, BISINDO"], accent=TEAL, body_size=18)

    s = d.new("Empat Data Utama", "Cakupan data")
    data = [("Disabilitas", "4.670", "orang", TEAL), ("Stunting", "3.138", "anak", ROSE), ("Anak Tidak Sekolah", "15.276", "anak", GOLD), ("Kemiskinan", "13.334", "KK miskin ekstrem", SLATE)]
    for i, (l, v, u, c) in enumerate(data):
        x = Inches(0.55 + i * 3.1)
        d.box(s, x, Inches(1.5), Inches(2.9), Inches(2.4), fill=WHITE, line=LINE, shape=MSO_SHAPE.ROUNDED_RECTANGLE, radius=0.06)
        d.box(s, x, Inches(1.5), Inches(2.9), Inches(0.12), fill=c)
        d.text(s, x + Inches(0.2), Inches(1.75), Inches(2.6), Inches(0.4), l.upper(), size=13, color=c, bold=True)
        d.text(s, x + Inches(0.2), Inches(2.25), Inches(2.6), Inches(0.9), v, size=40, color=INK, bold=True)
        d.text(s, x + Inches(0.2), Inches(3.2), Inches(2.6), Inches(0.4), u, size=13, color=MUTED)
    d.bullets(s, Inches(0.6), Inches(4.3), Inches(12), Inches(2.5), [
        ("Wilayah:", "15 kecamatan, 153 kelurahan Kota Makassar."),
        ("Sumber:", "Matriks Bappeda, DTSEN, data balita stunting by-name 2026 (Kec. Makassar & Tallo), Matriks ATS, BPS, dan PETA_DASAR."),
        ("Publik:", "hanya angka agregat — NIK, nama, alamat, email, dan telepon tidak pernah ditampilkan.")], size=15)

    s = d.new("Alur Kerja Sistem", "Dari data menjadi program")
    steps = [("Pengumpulan", "Input & impor data\n(Excel/CSV/PDF)"), ("Validasi", "Cek format &\nduplikat otomatis"), ("Verifikasi", "Verifikator\nsetujui/tolak"),
             ("Analisis", "Peta, prioritas,\nAI Analytics"), ("Program", "Inquiry NGO &\nprogram OPD"), ("Monitoring", "Cerita dampak\n& laporan")]
    for i, (t, b) in enumerate(steps):
        x = Inches(0.5 + i * 2.13)
        d.box(s, x, Inches(2.0), Inches(1.85), Inches(2.6), fill=WHITE, line=LINE, shape=MSO_SHAPE.ROUNDED_RECTANGLE, radius=0.08)
        d.circle_num(s, x + Inches(0.67), Inches(2.2), i + 1, d=Inches(0.55), fill=TEAL if i % 2 == 0 else NAVY)
        d.text(s, x, Inches(2.9), Inches(1.85), Inches(0.4), t, size=15, bold=True, color=NAVY, align=PP_ALIGN.CENTER)
        d.text(s, x, Inches(3.35), Inches(1.85), Inches(1.1), b.split("\n"), size=11.5, color=MUTED, align=PP_ALIGN.CENTER)
        if i < 5:
            d.arrow(s, x + Inches(1.87), Inches(3.3), x + Inches(2.11), Inches(3.3))
    d.box(s, Inches(0.5), Inches(5.1), Inches(12.3), Inches(1.4), fill=RGBColor(0xE6, 0xFA, 0xF6), shape=MSO_SHAPE.ROUNDED_RECTANGLE, radius=0.1)
    d.text(s, Inches(0.8), Inches(5.25), Inches(11.8), Inches(1.1), ["Setiap langkah tercatat di Audit Log dan setiap perubahan status inquiry otomatis dikirim lewat email ke NGO.",
                                                                       "Hak akses ditegakkan di server sesuai peran (RBAC)."], size=14, color=DTEAL)

    s = d.new("Pengguna & Peran", "Siapa melakukan apa")
    rows = [["Peran", "Tugas utama"], ["Publik", "Melihat dashboard, peta, dan flow sistem (agregat, tanpa login)"],
            ["NGO / Mitra", "Mengajukan & memantau inquiry program intervensi; peta & statistik agregat"],
            ["Petugas / Operator", "Input & impor data wilayah kewenangannya; data pribadi tampil tersamar"],
            ["Verifikator", "Memeriksa, menyetujui/menolak usulan perubahan data & meninjau inquiry"],
            ["Pimpinan", "Dashboard, rekap & laporan untuk pengambilan keputusan"],
            ["Admin / Super Admin", "Kelola pengguna, peran, master kode, kualitas data, email, BISINDO, audit"]]
    d.table(s, Inches(0.55), Inches(1.5), Inches(12.2), rows, [Inches(3.2), Inches(9.0)], size=14, rowh=Inches(0.62))

    for sid, title, kick, pts in [
        ("p02_publik", "Dashboard Informasi Umum", "Halaman publik", ["Kartu 4 kategori + sumber data", "Grafik per kecamatan & tren", "Ringkasan teks + tabel data tiap grafik", "Tombol dengarkan di setiap kartu"]),
        ("p05_peta_detail", "Peta Sosial & Drill-down", "Pemetaan tematik", ["Choropleth kecamatan → kelurahan", "Filter, pencarian & peringkat wilayah", "Panel detail wilayah", "Langsung Ajukan Program Intervensi dari peta"]),
        ("d26_impor", "Impor Data Terkendali", "Pengelolaan data", ["Template resmi per jenis data", "Upload → Mapping → Validasi → Preview → Impor", "Kunci anti-duplikat per jenis data", "Riwayat impor & audit"]),
        ("d13_inquiry_admin", "NGO Inquiry → Program", "Kolaborasi program", ["NGO mengajukan dari wilayah bermasalah", "9 status: Diajukan s.d. Selesai", "Catatan, lampiran & riwayat email", "Masuk Manajemen Program & Cerita Dampak"]),
        ("d20_ai_assistant", "Analisis AI & Laporan", "Pendukung keputusan", ["AI Assistant: tanya data bahasa sehari-hari", "AI Analytics: rekomendasi program per wilayah", "Laporan Wilayah PDF per kelurahan", "Rekap lengkap PDF + Excel"]),
        ("a04_tunarungu", "Aksesibilitas Inklusif", "Untuk semua warga", ["Bacakan halaman (suara AI jelas, tempo normal)", "Subtitle, transkrip & Bahasa Mudah", "Video juru bahasa isyarat BISINDO", "Pintasan keyboard & perintah suara"]),
    ]:
        s = d.new(title, kick)
        d.img(s, sid, Inches(0.6), Inches(1.55), Inches(8.2))
        d.bullets(s, Inches(9.15), Inches(1.7), Inches(3.8), Inches(5), pts, size=16, gap=14)

    s = d.new("Perlindungan Data Pribadi & Keamanan", "Kepercayaan publik")
    items = [("Masking data", "NIK 7371********1234, email gu****@gmail.com, telepon 0812******89 — disamarkan di server.", TEAL),
             ("API publik agregat", "Halaman publik hanya menerima angka per wilayah, bukan data individu.", NAVY),
             ("RBAC", "Akses menu & data dibatasi sesuai peran dan wilayah tugas.", GOLD),
             ("Audit Log", "Login, impor, perubahan data, dan status inquiry tercatat lengkap.", ROSE)]
    for i, (t, b, c) in enumerate(items):
        d.card(s, Inches(0.55 + (i % 2) * 6.2), Inches(1.5 + (i // 2) * 2.65), Inches(6), Inches(2.4), t, b, accent=c, title_size=20, body_size=17)

    s = d.new("Manfaat bagi Pemerintah Kota", "Dampak")
    d.bullets(s, Inches(0.7), Inches(1.6), Inches(12), Inches(5), [
        ("Tepat sasaran:", "lokasi & penerima ditentukan dari data terverifikasi dan skor prioritas."),
        ("Efisien:", "mencegah duplikasi data dan tumpang tindih bantuan antar OPD/NGO."),
        ("Kolaboratif:", "NGO, OPD, dan Bappeda bekerja di atas satu data yang sama."),
        ("Transparan:", "publik dapat melihat kondisi wilayah secara agregat."),
        ("Inklusif:", "informasi dapat diakses penyandang disabilitas buta & tuli."),
        ("Terukur:", "monitoring program & cerita dampak terdokumentasi.")], size=19, gap=14)

    s = d.new("Rencana Pengembangan", "Tahap berikutnya")
    for i, (t, b) in enumerate([("Ringkasan Mingguan Pimpinan", "Email otomatis per kecamatan & perkembangan inquiry NGO."),
                                 ("Ekspor Mengikuti Filter", "Excel, PDF, CSV di setiap dashboard."),
                                 ("Data Quality Center", "Pusat temuan data ganda, kosong, dan janggal sebelum disimpan."),
                                 ("Integrasi Data DTSEN", "Sinkronisasi data rumah tangga seluruh kecamatan.")]):
        d.circle_num(s, Inches(0.7), Inches(1.6 + i * 1.3), i + 1, d=Inches(0.7), fill=TEAL if i % 2 == 0 else AMBER, size=20)
        d.text(s, Inches(1.65), Inches(1.6 + i * 1.3), Inches(10.5), Inches(0.45), t, size=20, bold=True, color=NAVY)
        d.text(s, Inches(1.65), Inches(2.05 + i * 1.3), Inches(10.5), Inches(0.4), b, size=14, color=MUTED)

    d.closing("Terima Kasih", "PETA INKLUSI — Bappeda Kota Makassar\nSatu data sosial untuk program yang tepat sasaran")
    return d.save("Presentasi_PETA_INKLUSI_v1.0")


# =================================================================== SOP
def sop():
    d = Deck("SOP Penginputan Data PETA INKLUSI · Bappeda Kota Makassar · v1.0 · 2026")
    d.cover("SOP Penginputan Data", "Standar Operasional Prosedur agar data tidak ganda (double) dan seluruh program intervensi tepat sasaran", "No. SOP: SOP/PI-BAPPEDA/01/2026 · Versi 1.0 · 2026")

    s = d.new("Tujuan & Ruang Lingkup", "Bagian 1")
    d.card(s, Inches(0.55), Inches(1.45), Inches(6), Inches(5.3), "Tujuan", [
        "Menjamin satu orang / satu keluarga hanya tercatat satu kali",
        "Menjamin data akurat, mutakhir, dan terverifikasi sebelum dipakai",
        "Menjamin penetapan sasaran program berbasis data & prioritas wilayah",
        "Mencegah tumpang tindih bantuan antar OPD dan NGO",
        "Melindungi data pribadi warga"], body_size=18)
    d.card(s, Inches(6.8), Inches(1.45), Inches(6), Inches(5.3), "Ruang Lingkup", [
        "Data DTSEN Keluarga / Rumah Tangga",
        "Data Penyandang Disabilitas",
        "Data Balita Stunting (by-name)",
        "Data Anak Tidak Sekolah (ATS)",
        "Matriks RAD Disabilitas & Koordinat GIS",
        "Penetapan sasaran program & NGO Inquiry"], accent=NAVY, body_size=18)

    s = d.new("Definisi", "Bagian 2")
    rows = [["Istilah", "Pengertian"],
            ["Data ganda (double)", "Dua atau lebih baris yang merujuk ke orang/keluarga/wilayah yang sama"],
            ["Kunci unik", "Kombinasi kolom penanda satu data (mis. Nomor KK 16 digit + kelurahan)"],
            ["Validasi", "Pemeriksaan otomatis sistem: kolom wajib, format, kode, dan duplikat"],
            ["Verifikasi", "Pemeriksaan oleh Verifikator sebelum data dipakai untuk analisis/program"],
            ["Tepat sasaran", "Program diberikan kepada penerima & lokasi yang memenuhi kriteria prioritas"],
            ["Desil", "Peringkat kesejahteraan DTSEN; desil 1–2 = kelompok termiskin"]]
    d.table(s, Inches(0.55), Inches(1.5), Inches(12.2), rows, [Inches(3.3), Inches(8.9)], size=14, rowh=Inches(0.66))

    s = d.new("Pelaksana & Tanggung Jawab", "Bagian 3")
    rows = [["Pelaksana", "Tanggung jawab dalam SOP"],
            ["Petugas / Operator", "Menyiapkan berkas, cek data existing, input/impor, memperbaiki temuan kualitas data"],
            ["Verifikator", "Memeriksa & menyetujui/menolak usulan data; memastikan bukti & kewajaran"],
            ["Admin / Super Admin", "Mengelola akun & master kode, memantau Data Quality, impor data sensitif (stunting PDF)"],
            ["Pimpinan / Kepala Bidang", "Menetapkan sasaran program dari data terverifikasi & laporan prioritas"],
            ["NGO / OPD Pelaksana", "Mengajukan program sesuai wilayah prioritas & melaporkan penerima manfaat"]]
    d.table(s, Inches(0.55), Inches(1.5), Inches(12.2), rows, [Inches(3.3), Inches(8.9)], size=14, rowh=Inches(0.72))

    s = d.new("Prinsip: Satu Warga, Satu Data", "Bagian 4 · Kunci anti-duplikat")
    rows = [["Jenis data", "Kunci unik yang dipakai sistem", "Aturan tambahan"],
            ["DTSEN Keluarga", "Nomor KK (16 digit) + kelurahan", "NIK 16 digit; satu NIK hanya di satu KK aktif"],
            ["Balita Stunting", "Nama anak + nama orang tua (kemiripan ≥ 85%)", "Cek tanggal lahir & puskesmas; kembar tetap 2 data"],
            ["Disabilitas (rekap)", "Kecamatan + kelurahan + tahun", "Satu baris per kelurahan per tahun"],
            ["Matriks RAD", "OPD + program + kegiatan + sub kegiatan", "Perubahan target = perbarui, bukan tambah"],
            ["Koordinat GIS", "Kelurahan", "Satu titik per kelurahan"],
            ["ATS (per kelurahan)", "Kelurahan + tahun + jenjang + kelompok usia", "Impor ulang tahun sama → mode Ganti data tahun, bukan Tambah"]]
    d.table(s, Inches(0.55), Inches(1.5), Inches(12.2), rows, [Inches(2.6), Inches(4.9), Inches(4.7)], size=13, rowh=Inches(0.66))

    s = d.new("Alur SOP Penginputan Data", "Bagian 5 · Diagram alur")
    fl = [("Siapkan berkas", "Template resmi"), ("Cek data ada?", "Cari Nama/No. KK"), ("Input / Impor", "Formulir / Wizard"),
          ("Validasi sistem", "Format & duplikat"), ("Tangani duplikat", "Lewati / Perbarui"), ("Verifikasi", "Setujui / Tolak"),
          ("Kualitas data", "Tindak lanjut temuan"), ("Tetapkan sasaran", "Prioritas & desil"), ("Monitoring", "Laporan & dampak")]
    for i, (t, b) in enumerate(fl):
        row, col = divmod(i, 5)
        x = Inches(0.55 + col * 2.5) if row == 0 else Inches(1.8 + col * 2.5)
        y = Inches(1.65 + row * 2.6)
        d.box(s, x, y, Inches(2.1), Inches(1.55), fill=WHITE, line=TEAL if i not in (1, 4) else AMBER, shape=MSO_SHAPE.ROUNDED_RECTANGLE, radius=0.1)
        d.circle_num(s, x + Inches(0.08), y + Inches(0.1), i + 1, d=Inches(0.42), fill=NAVY, size=13)
        d.text(s, x + Inches(0.05), y + Inches(0.55), Inches(2.0), Inches(0.45), t, size=14, bold=True, color=NAVY, align=PP_ALIGN.CENTER)
        d.text(s, x + Inches(0.05), y + Inches(0.98), Inches(2.0), Inches(0.4), b, size=11, color=MUTED, align=PP_ALIGN.CENTER)
        if i in (0, 1, 2, 3, 5, 6, 7):
            d.arrow(s, x + Inches(2.12), y + Inches(0.78), x + Inches(2.48), y + Inches(0.78))
    d.arrow(s, Inches(10.55 + 1.05), Inches(3.22), Inches(1.8 + 1.05), Inches(4.25))
    d.text(s, Inches(0.55), Inches(6.45), Inches(12), Inches(0.4), "Kotak kuning = titik keputusan. Jika data sudah ada → perbarui data lama, JANGAN membuat data baru.", size=12, color=GOLD, bold=True)

    s = d.new("Langkah 1–2: Persiapan & Cek Data Existing", "Bagian 6")
    d.card(s, Inches(0.55), Inches(1.45), Inches(6), Inches(5.3), "1. Persiapan berkas", [
        "Unduh Template Excel resmi dari menu Impor Data",
        "Jangan ubah baris judul kolom; hapus baris contoh",
        "NIK & No. KK 16 digit, ditulis sebagai teks (tanpa spasi/titik)",
        "Nama wilayah sesuai master (cek ejaan kecamatan/kelurahan)",
        "Tanggal format DD/MM/YYYY; nama tanpa gelar & huruf besar konsisten",
        "Kolom berkode diisi sesuai Master Kode Referensi"], body_size=17)
    d.card(s, Inches(6.8), Inches(1.45), Inches(6), Inches(5.3), "2. Cek sebelum input", [
        "Cari Nama / No. KK pada menu data terkait (Data Rumah Tangga, Data Stunting, dll.)",
        "Data DITEMUKAN → gunakan Perbarui / ajukan perubahan",
        "Data TIDAK ditemukan → lanjut input baru",
        "Nama mirip (ejaan berbeda) → cocokkan tanggal lahir, nama orang tua, alamat",
        "Ragu → konsultasikan ke Verifikator, jangan input ganda"], accent=AMBER, body_size=17)

    s = d.new("Langkah 3: Input / Impor Data", "Bagian 7")
    d.img(s, "d26_impor", Inches(0.6), Inches(1.55), Inches(7.6))
    d.bullets(s, Inches(8.55), Inches(1.6), Inches(4.4), Inches(5.2), [
        ("Input manual:", "Input Data → pilih kecamatan & kelurahan → isi formulir → Simpan."),
        ("Impor Excel/CSV:", "Upload → Mapping Kolom → Validasi → Preview → Impor."),
        ("Stunting (PDF):", "khusus Admin; data baru menggantikan data lama, baris ganda dibuang otomatis."),
        ("Wajib:", "periksa Preview sebelum klik Impor/Simpan.")], size=14, gap=10)

    s = d.new("Langkah 4: Menangani Duplikat saat Validasi", "Bagian 8")
    rows = [["Pilihan sistem", "Kapan digunakan", "Hasil"],
            ["Tolak (bawaan)", "Belum yakin / data perlu dicek", "Impor berhenti, tidak ada data berubah"],
            ["Lewati", "Data lama sudah benar", "Baris kembar diabaikan, data baru lainnya masuk"],
            ["Perbarui", "Berkas baru lebih mutakhir & sudah dicek", "Data lama ditimpa seluruhnya"],
            ["Perbarui yang berubah", "Hanya sebagian kolom berubah", "Hanya kolom yang berbeda diperbarui"]]
    d.table(s, Inches(0.55), Inches(1.5), Inches(12.2), rows, [Inches(3.1), Inches(4.8), Inches(4.3)], size=14, rowh=Inches(0.7))
    d.box(s, Inches(0.55), Inches(5.3), Inches(12.2), Inches(1.3), fill=RGBColor(0xFF, 0xF7, 0xE6), shape=MSO_SHAPE.ROUNDED_RECTANGLE, radius=0.1)
    d.text(s, Inches(0.8), Inches(5.42), Inches(11.8), Inches(1.1), ["Larangan: mengubah satu digit NIK/No. KK atau menambah spasi pada nama agar lolos validasi duplikat.",
                                                                      "Pelanggaran tercatat di Audit Log."], size=14, color=GOLD, bold=True)

    s = d.new("Langkah 5: Verifikasi Data", "Bagian 9")
    d.img(s, "d25_verifikasi", Inches(0.6), Inches(1.55), Inches(7.6))
    d.text(s, Inches(8.55), Inches(1.55), Inches(4.4), Inches(0.4), "Checklist Verifikator", size=17, bold=True, color=NAVY)
    d.bullets(s, Inches(8.55), Inches(2.05), Inches(4.4), Inches(4.8), [
        "Identitas lengkap & format benar", "Tidak ada data kembar di wilayah lain", "Wilayah sesuai domisili",
        "Nilai wajar (umur, jumlah jiwa, TB/U)", "Ada dasar/bukti perubahan", "Tolak dengan catatan yang jelas",
        "Tuntas maks. 3 hari kerja"], size=14, gap=7)

    s = d.new("Langkah 6: Pengendalian Kualitas Data", "Bagian 10")
    d.img(s, "d27_kualitas", Inches(0.6), Inches(1.55), Inches(7.6))
    d.bullets(s, Inches(8.55), Inches(1.6), Inches(4.4), Inches(5.2), [
        ("Setiap minggu:", "Admin memeriksa menu Impor & Kualitas Data."),
        ("Temuan:", "baris duplikat, kolom wajib kosong, kode tidak valid, berkas/sheet duplikat."),
        ("Tindak lanjut:", "Petugas wilayah memperbaiki ≤ 3 hari kerja."),
        ("Bulanan:", "rekap temuan dilaporkan ke Kepala Bidang.")], size=14, gap=10)

    s = d.new("Program Tepat Sasaran: Kriteria Penetapan", "Bagian 11")
    crit = [("Lokasi prioritas", "Gunakan menu Prioritas Intervensi & peringkat peta (skor kerentanan tertinggi).", TEAL),
            ("Penerima by-name", "Penerima diambil dari data terverifikasi (desil 1–2 DTSEN, balita stunting, penyandang disabilitas).", NAVY),
            ("Cek tumpang tindih", "Cek menu Bantuan Sosial: satu KK tidak menerima program sejenis ganda pada periode yang sama.", ROSE),
            ("Sesuai kebutuhan", "Jenis intervensi sesuai ragam masalah (mis. TB/U Sangat Pendek, ragam disabilitas, jenjang ATS).", GOLD)]
    for i, (t, b, c) in enumerate(crit):
        d.card(s, Inches(0.55 + (i % 2) * 6.2), Inches(1.5 + (i // 2) * 2.65), Inches(6), Inches(2.4), t, b, accent=c, title_size=20, body_size=17)

    s = d.new("Alur Program NGO yang Tepat Sasaran", "Bagian 12")
    fl = [("Pilih wilayah", "dari peta / prioritas"), ("Ajukan inquiry", "data wilayah terisi"), ("Tinjau & verifikasi", "cek lokasi & penerima"),
          ("Koordinasi OPD", "hindari tumpang tindih"), ("Disetujui", "masuk Manajemen Program"), ("Monitoring", "laporan & cerita dampak")]
    for i, (t, b) in enumerate(fl):
        x = Inches(0.5 + i * 2.13)
        d.box(s, x, Inches(1.9), Inches(1.85), Inches(2.2), fill=WHITE, line=LINE, shape=MSO_SHAPE.ROUNDED_RECTANGLE, radius=0.08)
        d.circle_num(s, x + Inches(0.67), Inches(2.05), i + 1, d=Inches(0.52), fill=TEAL)
        d.text(s, x, Inches(2.7), Inches(1.85), Inches(0.45), t, size=14, bold=True, color=NAVY, align=PP_ALIGN.CENTER)
        d.text(s, x, Inches(3.2), Inches(1.85), Inches(0.8), b, size=11.5, color=MUTED, align=PP_ALIGN.CENTER)
        if i < 5:
            d.arrow(s, x + Inches(1.87), Inches(3.0), x + Inches(2.11), Inches(3.0))
    d.bullets(s, Inches(0.6), Inches(4.5), Inches(12), Inches(2.2), [
        ("Perlu Revisi:", "bila lokasi/penerima tidak sesuai prioritas — NGO memperbaiki melalui tombol Revisi."),
        ("Ditolak:", "bila wilayah sudah tertangani program sejenis atau data tidak dapat diverifikasi."),
        ("Selesai:", "NGO wajib melaporkan penerima manfaat & cerita dampak.")], size=14, gap=8)

    s = d.new("Checklist Harian Petugas", "Bagian 13")
    d.card(s, Inches(0.55), Inches(1.45), Inches(6), Inches(5.3), "LAKUKAN", [
        "Login dengan akun sendiri; Logout setelah selesai", "Gunakan template & master kode resmi", "Cari dulu sebelum menambah data",
        "Periksa Preview sebelum Impor", "Perbaiki temuan kualitas data", "Simpan bukti/dokumen sumber"], accent=TEAL, body_size=18)
    d.card(s, Inches(6.8), Inches(1.45), Inches(6), Inches(5.3), "JANGAN", [
        "Meminjamkan akun / kata sandi", "Mengakali validasi duplikat", "Input data di luar wilayah tugas",
        "Mengunduh & membagikan data pribadi", "Memakai data belum terverifikasi untuk program", "Menghapus data tanpa persetujuan Admin"], accent=ROSE, body_size=18)

    s = d.new("Indikator Keberhasilan SOP", "Bagian 14")
    kpi = [("< 1%", "Tingkat data ganda per jenis data"), ("100%", "Data terverifikasi sebelum dipakai program"), ("≤ 3 hari", "Penyelesaian temuan kualitas data"),
           ("0", "Penerima bantuan sejenis ganda per periode"), ("100%", "Program NGO berlokasi di wilayah prioritas")]
    for i, (v, l) in enumerate(kpi):
        x = Inches(0.55 + i * 2.48)
        d.box(s, x, Inches(1.8), Inches(2.3), Inches(2.6), fill=WHITE, line=LINE, shape=MSO_SHAPE.ROUNDED_RECTANGLE, radius=0.08)
        d.text(s, x, Inches(2.1), Inches(2.3), Inches(0.9), v, size=34, bold=True, color=TEAL if i % 2 == 0 else NAVY, align=PP_ALIGN.CENTER)
        d.text(s, x + Inches(0.1), Inches(3.1), Inches(2.1), Inches(1.1), l, size=13, color=MUTED, align=PP_ALIGN.CENTER)
    d.text(s, Inches(0.6), Inches(4.9), Inches(12), Inches(1.5), ["Evaluasi dilakukan setiap bulan oleh Admin Bappeda berdasarkan menu Impor & Kualitas Data, Audit Log, dan Manajemen Program.",
                                                                   "SOP ditinjau ulang minimal satu kali per tahun."], size=15, color=INK)

    s = d.new("Pengesahan", "Bagian 15")
    d.table(s, Inches(0.55), Inches(1.6), Inches(12.2), [["Keterangan", "Isi"], ["Nomor SOP", "SOP/PI-BAPPEDA/01/2026"], ["Tanggal berlaku", "…………………… 2026"],
                                                          ["Revisi", "00"], ["Disusun oleh", "Tim PETA INKLUSI Bappeda Kota Makassar"]], [Inches(3.3), Inches(8.9)], size=15, rowh=Inches(0.6))
    d.text(s, Inches(8.0), Inches(4.85), Inches(4.8), Inches(1.9), ["Makassar, ……………… 2026", "Kepala Bappeda Kota Makassar", "", "", "(…………………………………)"], size=14, color=INK, align=PP_ALIGN.CENTER)

    d.closing("Satu Warga, Satu Data", "Data yang bersih adalah dasar program yang tepat sasaran.\nBappeda Kota Makassar — PETA INKLUSI")
    return d.save("SOP_Penginputan_Data_PETA_INKLUSI_v1.0")


if __name__ == "__main__":
    print(presentasi())
    print(sop())
