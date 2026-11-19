"""Ekspor data mentah kecamatan & kelurahan ke Excel (.xlsx)."""
import io
from datetime import datetime
from openpyxl import Workbook
from openpyxl.styles import Font, PatternFill, Alignment, Border, Side

HEADER_FILL = PatternFill("solid", fgColor="0F172A")
HEADER_FONT = Font(bold=True, color="FFFFFF", size=10)
TITLE_FONT = Font(bold=True, size=13, color="DC2626")
SUB_FONT = Font(italic=True, size=9, color="475569")
THIN = Side(style="thin", color="CBD5E1")
BORDER = Border(left=THIN, right=THIN, top=THIN, bottom=THIN)

KEC_COLS = [
    ("nama", "Kecamatan"),
    ("kelurahan", "Jumlah Kelurahan"),
    ("kemiskinan_ekstrim_kk", "Kemiskinan Ekstrim (KK)"),
    ("kemiskinan_persen", "Kemiskinan (%)"),
    ("stunting_anak", "Stunting (anak)"),
    ("ats", "Anak Tidak Sekolah"),
    ("anak_jalanan", "Anak Jalanan (jiwa)"),
    ("disabilitas", "Disabilitas (orang)"),
    ("updated_by", "Diperbarui oleh"),
    ("updated_at", "Waktu Pembaruan"),
]

KEL_COLS = [
    ("kecamatan", "Kecamatan"),
    ("nama", "Kelurahan"),
    ("kemiskinan_ekstrim_kk", "Kemiskinan Ekstrim (KK)"),
    ("kemiskinan_persen", "Kemiskinan (%)"),
    ("stunting_anak", "Stunting (anak)"),
    ("ats", "Anak Tidak Sekolah"),
    ("anak_jalanan", "Anak Jalanan (jiwa)"),
    ("disabilitas", "Disabilitas (orang)"),
    ("updated_by", "Diperbarui oleh"),
    ("updated_at", "Waktu Pembaruan"),
]


def _style_sheet(ws, title, subtitle, cols, rows):
    ncol = len(cols)
    last_col = chr(ord("A") + ncol - 1)
    # Judul
    ws.merge_cells(f"A1:{last_col}1")
    ws["A1"] = title
    ws["A1"].font = TITLE_FONT
    ws["A1"].alignment = Alignment(horizontal="left")
    ws.merge_cells(f"A2:{last_col}2")
    ws["A2"] = subtitle
    ws["A2"].font = SUB_FONT
    # Header baris 4
    header_row = 4
    for j, (_, label) in enumerate(cols):
        c = ws.cell(row=header_row, column=j + 1, value=label)
        c.fill = HEADER_FILL
        c.font = HEADER_FONT
        c.alignment = Alignment(horizontal="center", vertical="center", wrap_text=True)
        c.border = BORDER
    # Data
    for i, row in enumerate(rows):
        for j, (key, _) in enumerate(cols):
            val = row.get(key, "")
            if val is None:
                val = ""
            c = ws.cell(row=header_row + 1 + i, column=j + 1, value=val)
            c.border = BORDER
            c.alignment = Alignment(horizontal="left" if j <= 1 or key in ("updated_by", "updated_at") else "right")
    # Lebar kolom
    for j, (key, label) in enumerate(cols):
        width = max(len(label) + 2, 14)
        if key in ("nama", "kecamatan", "updated_by", "updated_at"):
            width = max(width, 20)
        ws.column_dimensions[chr(ord("A") + j)].width = width
    ws.freeze_panes = f"A{header_row + 1}"


def build_data_excel(regions, kelurahan):
    wb = Workbook()
    tanggal = datetime.now().strftime("%d/%m/%Y %H:%M")
    sub = f"Diekspor {tanggal} · Bappeda Kota Makassar"

    ws1 = wb.active
    ws1.title = "Data Kecamatan"
    _style_sheet(ws1, "DATA SOSIAL PER KECAMATAN — KOTA MAKASSAR", sub, KEC_COLS,
                 sorted(regions, key=lambda r: r.get("nama", "")))

    ws2 = wb.create_sheet("Data Kelurahan")
    _style_sheet(ws2, "DATA SOSIAL PER KELURAHAN — KOTA MAKASSAR", sub, KEL_COLS,
                 sorted(kelurahan, key=lambda r: (r.get("kecamatan", ""), r.get("nama", ""))))

    buf = io.BytesIO()
    wb.save(buf)
    return buf.getvalue()
