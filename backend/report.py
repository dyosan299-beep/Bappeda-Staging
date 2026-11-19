"""Pembuatan laporan PDF resmi Bappeda Kota Makassar."""
import io
import os
import re
from datetime import datetime
from reportlab.lib.pagesizes import A4
from reportlab.lib.units import mm
from reportlab.lib import colors
from reportlab.lib.styles import getSampleStyleSheet, ParagraphStyle
from reportlab.lib.enums import TA_CENTER, TA_JUSTIFY
from reportlab.platypus import (
    SimpleDocTemplate, Paragraph, Spacer, Table, TableStyle, HRFlowable, Image,
)

LOGO_MAKASSAR = os.path.join(os.path.dirname(__file__), "assets", "logo_makassar.png")
LOGO_BAPPEDA = os.path.join(os.path.dirname(__file__), "assets", "logo_bappeda.jpg")
LOGO_PATH = os.path.join(os.path.dirname(__file__), "assets", "emblem.jpeg")  # fallback lama

PRIMARY = colors.HexColor("#DC2626")
ACCENT = colors.HexColor("#0F172A")
MUTED = colors.HexColor("#475569")

MONTHS_ID = ["", "Januari", "Februari", "Maret", "April", "Mei", "Juni", "Juli",
             "Agustus", "September", "Oktober", "November", "Desember"]


def _tanggal_id():
    n = datetime.now()
    return f"{n.day} {MONTHS_ID[n.month]} {n.year}"


def _styles():
    ss = getSampleStyleSheet()
    styles = {
        "kop1": ParagraphStyle("kop1", parent=ss["Normal"], fontName="Helvetica-Bold",
                               fontSize=13, alignment=TA_CENTER, textColor=ACCENT, leading=16),
        "kop2": ParagraphStyle("kop2", parent=ss["Normal"], fontName="Helvetica-Bold",
                               fontSize=15, alignment=TA_CENTER, textColor=PRIMARY, leading=18),
        "kop3": ParagraphStyle("kop3", parent=ss["Normal"], fontName="Helvetica",
                               fontSize=8.5, alignment=TA_CENTER, textColor=MUTED, leading=11),
        "title": ParagraphStyle("title", parent=ss["Normal"], fontName="Helvetica-Bold",
                                 fontSize=13, alignment=TA_CENTER, textColor=ACCENT, leading=17,
                                 spaceBefore=6, spaceAfter=2),
        "subtitle": ParagraphStyle("subtitle", parent=ss["Normal"], fontName="Helvetica",
                                    fontSize=10, alignment=TA_CENTER, textColor=MUTED),
        "meta": ParagraphStyle("meta", parent=ss["Normal"], fontName="Helvetica",
                               fontSize=9, textColor=MUTED),
        "h2": ParagraphStyle("h2", parent=ss["Normal"], fontName="Helvetica-Bold",
                             fontSize=12, textColor=PRIMARY, spaceBefore=12, spaceAfter=4, leading=15),
        "h3": ParagraphStyle("h3", parent=ss["Normal"], fontName="Helvetica-Bold",
                             fontSize=10.5, textColor=ACCENT, spaceBefore=8, spaceAfter=3, leading=13),
        "body": ParagraphStyle("body", parent=ss["Normal"], fontName="Helvetica",
                               fontSize=10, alignment=TA_JUSTIFY, leading=15, spaceAfter=4),
        "bullet": ParagraphStyle("bullet", parent=ss["Normal"], fontName="Helvetica",
                                 fontSize=10, leading=15, leftIndent=14, bulletIndent=4, spaceAfter=2),
        "small": ParagraphStyle("small", parent=ss["Normal"], fontName="Helvetica",
                                fontSize=8, textColor=MUTED, alignment=TA_CENTER),
        "cell": ParagraphStyle("cell", parent=ss["Normal"], fontName="Helvetica", fontSize=9, leading=12),
        "cellb": ParagraphStyle("cellb", parent=ss["Normal"], fontName="Helvetica-Bold", fontSize=9, leading=12),
    }
    return styles


def _inline(text):
    text = text.replace("&", "&amp;").replace("<", "&lt;").replace(">", "&gt;")
    text = re.sub(r"\*\*(.+?)\*\*", r"<b>\1</b>", text)
    text = re.sub(r"__(.+?)__", r"<b>\1</b>", text)
    text = re.sub(r"`(.+?)`", r"\1", text)
    return text


def _kop(styles):
    heading = [
        Paragraph("PEMERINTAH KOTA MAKASSAR", styles["kop1"]),
        Paragraph("BADAN PERENCANAAN PEMBANGUNAN DAERAH", styles["kop2"]),
        Paragraph("Jl. A. P. Pettarani No.62, Kota Makassar, Sulawesi Selatan · sidata.bappeda.makassarkota.go.id",
                  styles["kop3"]),
    ]
    # Logo Kota Makassar (kiri) + Logo Bappeda (kanan) di atas kop
    left = ""
    right = ""
    if os.path.exists(LOGO_MAKASSAR):
        # rasio asli 1080x1354 (potret)
        left = Image(LOGO_MAKASSAR, width=19 * mm, height=24 * mm)
    elif os.path.exists(LOGO_PATH):
        left = Image(LOGO_PATH, width=22 * mm, height=22 * mm)
    if os.path.exists(LOGO_BAPPEDA):
        # rasio asli 399x501
        right = Image(LOGO_BAPPEDA, width=17 * mm, height=21 * mm)

    if left or right:
        header_tbl = Table([[left, heading, right]], colWidths=[24 * mm, 128 * mm, 18 * mm])
        header_tbl.setStyle(TableStyle([
            ("VALIGN", (0, 0), (-1, -1), "MIDDLE"),
            ("ALIGN", (0, 0), (0, 0), "LEFT"),
            ("ALIGN", (2, 0), (2, 0), "RIGHT"),
            ("LEFTPADDING", (0, 0), (-1, -1), 0),
            ("RIGHTPADDING", (0, 0), (-1, -1), 0),
            ("TOPPADDING", (0, 0), (-1, -1), 0),
            ("BOTTOMPADDING", (0, 0), (-1, -1), 0),
        ]))
        story = [header_tbl]
    else:
        story = list(heading)
    story += [
        Spacer(1, 4),
        HRFlowable(width="100%", thickness=2, color=ACCENT),
        HRFlowable(width="100%", thickness=0.8, color=PRIMARY, spaceBefore=1.5),
        Spacer(1, 10),
    ]
    return story


def _markdown_to_flowables(md, styles):
    flow = []
    for raw in md.split("\n"):
        line = raw.rstrip()
        if not line.strip():
            flow.append(Spacer(1, 3))
            continue
        if line.startswith("### "):
            flow.append(Paragraph(_inline(line[4:]), styles["h3"]))
        elif line.startswith("## "):
            flow.append(Paragraph(_inline(line[3:]), styles["h2"]))
        elif line.startswith("# "):
            flow.append(Paragraph(_inline(line[2:]), styles["h2"]))
        elif re.match(r"^\s*[-*]\s+", line):
            item = re.sub(r"^\s*[-*]\s+", "", line)
            flow.append(Paragraph(_inline(item), styles["bullet"], bulletText="•"))
        elif re.match(r"^\s*\d+\.\s+", line):
            item = re.sub(r"^\s*\d+\.\s+", "", line)
            flow.append(Paragraph(_inline(item), styles["bullet"], bulletText="•"))
        else:
            flow.append(Paragraph(_inline(line), styles["body"]))
    return flow


def _footer(canvas, doc):
    canvas.saveState()
    canvas.setFont("Helvetica", 7.5)
    canvas.setFillColor(MUTED)
    canvas.drawString(20 * mm, 12 * mm,
                      "Dokumen dihasilkan oleh SIDATA Bappeda Kota Makassar")
    canvas.drawRightString(A4[0] - 20 * mm, 12 * mm, f"Halaman {doc.page}")
    canvas.setStrokeColor(colors.HexColor("#E2E8F0"))
    canvas.line(20 * mm, 15 * mm, A4[0] - 20 * mm, 15 * mm)
    canvas.restoreState()


def _build(story):
    buf = io.BytesIO()
    doc = SimpleDocTemplate(buf, pagesize=A4, topMargin=18 * mm, bottomMargin=20 * mm,
                            leftMargin=20 * mm, rightMargin=20 * mm,
                            title="Laporan Bappeda Kota Makassar")
    doc.build(story, onFirstPage=_footer, onLaterPages=_footer)
    buf.seek(0)
    return buf.read()


def build_ai_report(kategori_label, wilayah, markdown_text):
    styles = _styles()
    story = _kop(styles)
    story.append(Paragraph("LAPORAN ANALISA & REKOMENDASI PROGRAM", styles["title"]))
    story.append(Paragraph(f"Kategori: {kategori_label} · Wilayah: {wilayah}", styles["subtitle"]))
    story.append(Spacer(1, 8))
    story.append(Paragraph(
        f"Analisa dihasilkan oleh sistem kecerdasan buatan (Claude Sonnet 4.6) berdasarkan data "
        f"matriks {kategori_label.lower()}. Dicetak pada {_tanggal_id()}.", styles["meta"]))
    story.append(Spacer(1, 6))
    story.append(HRFlowable(width="100%", thickness=0.6, color=colors.HexColor("#CBD5E1")))
    story.append(Spacer(1, 6))
    story.extend(_markdown_to_flowables(markdown_text, styles))
    story.append(Spacer(1, 18))
    story.append(Paragraph(
        "Catatan: Rekomendasi program di atas bersifat indikatif dan perlu ditelaah lebih lanjut "
        "melalui mekanisme perencanaan resmi (RKPD/APBD) Kota Makassar.", styles["meta"]))
    return _build(story)


def _table(data, styles, col_widths=None):
    t = Table(data, colWidths=col_widths, hAlign="LEFT")
    t.setStyle(TableStyle([
        ("BACKGROUND", (0, 0), (-1, 0), ACCENT),
        ("TEXTCOLOR", (0, 0), (-1, 0), colors.white),
        ("FONTNAME", (0, 0), (-1, 0), "Helvetica-Bold"),
        ("FONTSIZE", (0, 0), (-1, -1), 9),
        ("GRID", (0, 0), (-1, -1), 0.4, colors.HexColor("#CBD5E1")),
        ("ROWBACKGROUNDS", (0, 1), (-1, -1), [colors.white, colors.HexColor("#F1F5F9")]),
        ("VALIGN", (0, 0), (-1, -1), "MIDDLE"),
        ("TOPPADDING", (0, 0), (-1, -1), 4),
        ("BOTTOMPADDING", (0, 0), (-1, -1), 4),
        ("LEFTPADDING", (0, 0), (-1, -1), 6),
    ]))
    return t


def _fmt(n):
    try:
        return f"{int(n):,}".replace(",", ".")
    except Exception:
        return str(n)


def build_dashboard_report(overview, regions, poverty, stunting, pmks, disability):
    styles = _styles()
    story = _kop(styles)
    story.append(Paragraph("RINGKASAN DATA SOSIAL KOTA MAKASSAR", styles["title"]))
    story.append(Paragraph("Dashboard Sistem Intelijen Data (SIDATA)", styles["subtitle"]))
    story.append(Spacer(1, 6))
    story.append(Paragraph(f"Dicetak pada {_tanggal_id()}.", styles["meta"]))
    story.append(Spacer(1, 8))

    # KPI ringkas
    story.append(Paragraph("Indikator Utama", styles["h2"]))
    kpi = [
        ["Indikator", "Nilai", "Satuan"],
        ["Jumlah Kecamatan", _fmt(overview["jumlah_kecamatan"]), "kecamatan"],
        ["Jumlah Kelurahan", _fmt(overview["jumlah_kelurahan"]), "kelurahan"],
        ["Kemiskinan Ekstrim", _fmt(overview["kemiskinan_ekstrim_kk"]), "KK"],
        ["Tingkat Kemiskinan Kota (2025)", f'{overview["kemiskinan_persen_terkini"]}', "%"],
        ["Stunting", _fmt(overview["stunting_anak"]), "anak"],
        ["Anak Tidak Sekolah", _fmt(overview["ats"]), "anak"],
        ["Anak Jalanan", _fmt(overview["anak_jalanan"]), "jiwa"],
        ["Penyandang Disabilitas", _fmt(overview["disabilitas"]), "orang"],
    ]
    story.append(_table(kpi, styles, [90 * mm, 45 * mm, 35 * mm]))
    story.append(Spacer(1, 10))

    # Sebaran per kecamatan
    story.append(Paragraph("Sebaran Data per Kecamatan", styles["h2"]))
    header = ["Kecamatan", "Kemiskinan (KK)", "Stunting", "ATS", "Anak Jln", "Disabilitas"]
    rows = [header]
    for r in sorted(regions, key=lambda x: x.get("kemiskinan_ekstrim_kk", 0), reverse=True):
        rows.append([
            r["nama"], _fmt(r.get("kemiskinan_ekstrim_kk", 0)), _fmt(r.get("stunting_anak", 0)),
            _fmt(r.get("ats", 0)), _fmt(r.get("anak_jalanan", 0)), _fmt(r.get("disabilitas", 0)),
        ])
    story.append(_table(rows, styles, [40 * mm, 30 * mm, 22 * mm, 22 * mm, 22 * mm, 26 * mm]))
    story.append(Spacer(1, 10))

    # Tren kemiskinan
    story.append(Paragraph("Tren Kemiskinan Kota (2021–2025)", styles["h2"]))
    tren = [["Tahun", "Persentase (%)", "Penduduk Miskin (ribu jiwa)"]]
    for t in poverty["tren"]:
        tren.append([str(t["tahun"]), str(t["persen"]), str(t["penduduk_miskin_ribu"])])
    story.append(_table(tren, styles, [40 * mm, 50 * mm, 60 * mm]))
    story.append(Spacer(1, 10))

    # PMKS
    story.append(Paragraph("Data PMKS (2022–2025)", styles["h2"]))
    pm = [["Indikator", "2022", "2023", "2024", "2025"]]
    for p in pmks:
        pm.append([p["indikator"], _pmk(p.get("y2022")), _pmk(p.get("y2023")),
                   _pmk(p.get("y2024")), _pmk(p.get("y2025"))])
    story.append(_table(pm, styles, [70 * mm, 22 * mm, 22 * mm, 22 * mm, 22 * mm]))
    story.append(Spacer(1, 14))
    story.append(Paragraph("Sumber data: Kelurahan & Kecamatan se-Kota Makassar.", styles["meta"]))
    return _build(story)


def _pmk(v):
    return "–" if v is None else _fmt(v)
