"""Membangun Manual Book PETA INKLUSI dalam format DOCX dan PDF dari content.py."""
import os
from docx import Document
from docx.enum.section import WD_SECTION
from docx.enum.table import WD_TABLE_ALIGNMENT
from docx.enum.text import WD_ALIGN_PARAGRAPH, WD_BREAK
from docx.oxml import OxmlElement
from docx.oxml.ns import qn
from docx.shared import Cm, Pt, RGBColor
from reportlab.lib import colors
from reportlab.lib.enums import TA_CENTER
from reportlab.lib.pagesizes import A4
from reportlab.lib.styles import ParagraphStyle
from reportlab.lib.units import cm
from reportlab.pdfbase import pdfmetrics
from reportlab.pdfbase.ttfonts import TTFont
from reportlab.platypus import (Image as RLImage, KeepTogether, PageBreak, Paragraph, Spacer, Table, TableStyle)
from reportlab.platypus.doctemplate import BaseDocTemplate, Frame, PageTemplate
from reportlab.platypus.tableofcontents import TableOfContents

import content as C

SHOTS = "/app/docs/manual/shots"
OUT = "/app/docs/manual"
LOGO = "/app/frontend/public/logo-peta-inklusi.png"
TEAL, NAVY, AMBER, MINT = "117A69", "232F3E", "F4B63A", "6FE3CF"
NAMA = "Manual_Book_PETA_INKLUSI_v1.0"


def shot(sid):
    p = f"{SHOTS}/{sid}.jpg"
    return p if os.path.exists(p) else None


# ============================================================ DOCX
def _shade(cell, hexcolor):
    tcPr = cell._tc.get_or_add_tcPr()
    sh = OxmlElement("w:shd")
    sh.set(qn("w:val"), "clear"); sh.set(qn("w:color"), "auto"); sh.set(qn("w:fill"), hexcolor)
    tcPr.append(sh)


def _field(par, instr):
    r = par.add_run()
    for t, v in (("begin", None), ("instr", instr), ("separate", None), ("end", None)):
        if t == "instr":
            el = OxmlElement("w:instrText"); el.set(qn("xml:space"), "preserve"); el.text = v
        else:
            el = OxmlElement("w:fldChar"); el.set(qn("w:fldCharType"), t)
        r._r.append(el)
    return r


def _borders(table, color="D9E2E8"):
    tbl = table._tbl
    tblPr = tbl.tblPr
    b = OxmlElement("w:tblBorders")
    for e in ("top", "left", "bottom", "right", "insideH", "insideV"):
        el = OxmlElement(f"w:{e}"); el.set(qn("w:val"), "single"); el.set(qn("w:sz"), "4"); el.set(qn("w:color"), color)
        b.append(el)
    tblPr.append(b)


def build_docx():
    d = Document()
    st = d.styles["Normal"]
    st.font.name = "Calibri"; st.font.size = Pt(10.5)
    st.element.rPr.rFonts.set(qn("w:eastAsia"), "Calibri")
    for lvl, size, col in ((1, 18, NAVY), (2, 13, TEAL)):
        h = d.styles[f"Heading {lvl}"]
        h.font.name = "Calibri"; h.font.size = Pt(size); h.font.bold = True; h.font.color.rgb = RGBColor.from_string(col)
    sec = d.sections[0]
    sec.page_height, sec.page_width = Cm(29.7), Cm(21)
    sec.left_margin = sec.right_margin = Cm(2.2); sec.top_margin = Cm(2); sec.bottom_margin = Cm(2)
    sec.different_first_page_header_footer = True

    # ---- Sampul
    for _ in range(3):
        d.add_paragraph()
    if os.path.exists(LOGO):
        p = d.add_paragraph(); p.alignment = WD_ALIGN_PARAGRAPH.CENTER; p.add_run().add_picture(LOGO, width=Cm(6))
    for txt, size, col, bold in ((C.JUDUL, 34, NAVY, True), (C.SUBJUDUL, 15, TEAL, True), ("", 10, NAVY, False),
                                 (C.INSTANSI, 16, NAVY, True), (C.VERSI, 12, "475569", False)):
        p = d.add_paragraph(); p.alignment = WD_ALIGN_PARAGRAPH.CENTER
        r = p.add_run(txt); r.font.size = Pt(size); r.bold = bold; r.font.color.rgb = RGBColor.from_string(col)
    p = d.add_paragraph(); p.alignment = WD_ALIGN_PARAGRAPH.CENTER
    r = p.add_run("Panduan penggunaan untuk Publik, NGO, Petugas/Operator, Verifikator, Pimpinan, dan Admin"); r.italic = True; r.font.size = Pt(10)
    d.add_paragraph().add_run().add_break(WD_BREAK.PAGE)

    # ---- Header/footer
    hp = sec.header.paragraphs[0]; hp.alignment = WD_ALIGN_PARAGRAPH.RIGHT
    hr = hp.add_run(f"{C.INSTANSI} — PETA INKLUSI  |  Manual Book {C.VERSI}"); hr.font.size = Pt(8); hr.font.color.rgb = RGBColor.from_string("64748B")
    fp = sec.footer.paragraphs[0]; fp.alignment = WD_ALIGN_PARAGRAPH.CENTER
    fr = fp.add_run("Halaman "); fr.font.size = Pt(8)
    _field(fp, "PAGE").font.size = Pt(8)

    # ---- Daftar isi
    d.add_heading("Daftar Isi", 1)
    p = d.add_paragraph(); _field(p, 'TOC \\o "1-2" \\h \\z \\u')
    p.add_run("(Klik kanan → Update Field untuk memperbarui nomor halaman)").italic = True
    for i, bab in enumerate(C.BAB, 1):
        q = d.add_paragraph(); r = q.add_run(f"BAB {i}. {bab['bab']}"); r.bold = True; r.font.color.rgb = RGBColor.from_string(NAVY)
        for j, it in enumerate(bab["items"], 1):
            q = d.add_paragraph(f"    {i}.{j}  {it['h']}"); q.paragraph_format.space_after = Pt(0)
    d.add_paragraph().add_run().add_break(WD_BREAK.PAGE)

    for i, bab in enumerate(C.BAB, 1):
        d.add_heading(f"BAB {i}. {bab['bab']}", 1)
        for j, it in enumerate(bab["items"], 1):
            d.add_heading(f"{i}.{j}  {it['h']}", 2)
            for t in it.get("p", []):
                d.add_paragraph(t).paragraph_format.space_after = Pt(6)
            sp = shot(it["shot"]) if it.get("shot") else None
            if sp:
                p = d.add_paragraph(); p.alignment = WD_ALIGN_PARAGRAPH.CENTER; p.add_run().add_picture(sp, width=Cm(16.4))
                c = d.add_paragraph(); c.alignment = WD_ALIGN_PARAGRAPH.CENTER
                cr = c.add_run(f"Gambar {i}.{j} — {it['h']}"); cr.italic = True; cr.font.size = Pt(8.5); cr.font.color.rgb = RGBColor.from_string("64748B")
            if it.get("steps"):
                t = d.add_table(rows=0, cols=2); t.alignment = WD_TABLE_ALIGNMENT.CENTER; _borders(t)
                for n, s in enumerate(it["steps"], 1):
                    row = t.add_row().cells
                    row[0].width = Cm(1.1); row[1].width = Cm(15.3)
                    _shade(row[0], TEAL)
                    rp = row[0].paragraphs[0]; rp.alignment = WD_ALIGN_PARAGRAPH.CENTER
                    rr = rp.add_run(str(n)); rr.bold = True; rr.font.color.rgb = RGBColor(255, 255, 255)
                    row[1].paragraphs[0].add_run(s)
                d.add_paragraph()
            if it.get("table"):
                tb = it["table"]
                t = d.add_table(rows=1, cols=len(tb["head"])); _borders(t)
                for k, h in enumerate(tb["head"]):
                    _shade(t.rows[0].cells[k], NAVY)
                    r = t.rows[0].cells[k].paragraphs[0].add_run(h); r.bold = True; r.font.color.rgb = RGBColor(255, 255, 255)
                for rowv in tb["rows"]:
                    cells = t.add_row().cells
                    for k, v in enumerate(rowv):
                        r = cells[k].paragraphs[0].add_run(v)
                        if k == 0:
                            r.bold = True
                for row in t.rows:
                    row.cells[0].width = Cm(4.2); row.cells[-1].width = Cm(12.2)
                d.add_paragraph()
            for tip in it.get("tips", []):
                p = d.add_paragraph(); r = p.add_run("Catatan: "); r.bold = True; r.font.color.rgb = RGBColor.from_string("B7791F")
                p.add_run(tip)
    path = f"{OUT}/{NAMA}.docx"
    d.save(path)
    return path


# ============================================================ PDF
pdfmetrics.registerFont(TTFont("DV", "/usr/share/fonts/truetype/liberation/LiberationSans-Regular.ttf"))
pdfmetrics.registerFont(TTFont("DVB", "/usr/share/fonts/truetype/liberation/LiberationSans-Bold.ttf"))
pdfmetrics.registerFont(TTFont("DVI", "/usr/share/fonts/truetype/liberation/LiberationSans-Italic.ttf") if os.path.exists("/usr/share/fonts/truetype/liberation/LiberationSans-Italic.ttf") else TTFont("DVI", "/usr/share/fonts/truetype/liberation/LiberationSans-Regular.ttf"))
from reportlab.pdfbase.pdfmetrics import registerFontFamily  # noqa: E402
registerFontFamily("DV", normal="DV", bold="DVB", italic="DVI", boldItalic="DVB")
cT, cN, cA, cG = colors.HexColor("#" + TEAL), colors.HexColor("#" + NAVY), colors.HexColor("#B7791F"), colors.HexColor("#64748B")
S = {
    "body": ParagraphStyle("body", fontName="DV", fontSize=9.5, leading=14, spaceAfter=5),
    "h1": ParagraphStyle("h1", fontName="DVB", fontSize=17, leading=22, textColor=cN, spaceAfter=10, spaceBefore=4),
    "h2": ParagraphStyle("h2", fontName="DVB", fontSize=12, leading=16, textColor=cT, spaceAfter=6, spaceBefore=10),
    "cap": ParagraphStyle("cap", fontName="DVI", fontSize=7.5, textColor=cG, alignment=TA_CENTER, spaceAfter=6),
    "cell": ParagraphStyle("cell", fontName="DV", fontSize=8.8, leading=12),
    "cellw": ParagraphStyle("cellw", fontName="DVB", fontSize=8.8, leading=12, textColor=colors.white, alignment=TA_CENTER),
    "tip": ParagraphStyle("tip", fontName="DV", fontSize=8.8, leading=12.5, backColor=colors.HexColor("#FFF7E6"), borderPadding=5, spaceBefore=4, spaceAfter=8),
}


class Doc(BaseDocTemplate):
    def __init__(self, fn):
        super().__init__(fn, pagesize=A4, leftMargin=2 * cm, rightMargin=2 * cm, topMargin=2 * cm, bottomMargin=1.8 * cm,
                         title="Manual Book PETA INKLUSI v1.0", author=C.INSTANSI)
        fr = Frame(self.leftMargin, self.bottomMargin, self.width, self.height, id="f")
        self.addPageTemplates([PageTemplate("cover", [fr], onPage=lambda c, d: None), PageTemplate("isi", [fr], onPage=self._deco)])

    def _deco(self, c, d):
        w, h = A4
        c.setFillColor(cN); c.rect(0, h - 0.9 * cm, w, 0.9 * cm, fill=1, stroke=0)
        c.setFillColor(colors.white); c.setFont("DVB", 8); c.drawString(2 * cm, h - 0.58 * cm, "PETA INKLUSI")
        c.setFont("DV", 8); c.drawRightString(w - 2 * cm, h - 0.58 * cm, f"{C.INSTANSI}  |  Manual Book {C.VERSI}")
        c.setStrokeColor(cT); c.setLineWidth(1.2); c.line(2 * cm, 1.3 * cm, w - 2 * cm, 1.3 * cm)
        c.setFillColor(cG); c.setFont("DV", 8); c.drawCentredString(w / 2, 0.8 * cm, f"Halaman {d.page}")

    def afterFlowable(self, f):
        if isinstance(f, Paragraph) and f.style.name in ("h1", "h2"):
            lvl = 0 if f.style.name == "h1" else 1
            key = f"k{id(f)}"
            self.canv.bookmarkPage(key); self.canv.addOutlineEntry(f.getPlainText(), key, level=lvl)
            self.notify("TOCEntry", (lvl, f.getPlainText(), self.page, key))


def build_pdf():
    path = f"{OUT}/{NAMA}.pdf"
    doc = Doc(path)
    from reportlab.platypus import NextPageTemplate
    st = [Spacer(1, 2.5 * cm)]
    if os.path.exists(LOGO):
        st.append(RLImage(LOGO, width=6.5 * cm, height=6.5 * cm))
    st += [Spacer(1, 1 * cm),
           Paragraph(C.JUDUL, ParagraphStyle("t", fontName="DVB", fontSize=34, leading=40, textColor=cN, alignment=TA_CENTER)),
           Spacer(1, 0.4 * cm),
           Paragraph(C.SUBJUDUL, ParagraphStyle("s", fontName="DVB", fontSize=14, leading=19, textColor=cT, alignment=TA_CENTER)),
           Spacer(1, 2.2 * cm),
           Paragraph(C.INSTANSI, ParagraphStyle("i", fontName="DVB", fontSize=16, leading=20, textColor=cN, alignment=TA_CENTER)),
           Paragraph(C.VERSI, ParagraphStyle("v", fontName="DV", fontSize=11, leading=16, textColor=cG, alignment=TA_CENTER)),
           Spacer(1, 0.6 * cm),
           Paragraph("Panduan penggunaan untuk Publik, NGO, Petugas/Operator, Verifikator, Pimpinan, dan Admin",
                     ParagraphStyle("x", fontName="DVI", fontSize=9, textColor=cG, alignment=TA_CENTER)),
           NextPageTemplate("isi"), PageBreak()]
    toc = TableOfContents()
    toc.levelStyles = [ParagraphStyle("t1", fontName="DVB", fontSize=10, leading=15, textColor=cN, spaceBefore=4),
                       ParagraphStyle("t2", fontName="DV", fontSize=9, leading=13, leftIndent=14)]
    st += [Paragraph("Daftar Isi", ParagraphStyle("dh", parent=S["h1"])), toc, PageBreak()]
    for i, bab in enumerate(C.BAB, 1):
        st.append(Paragraph(f"BAB {i}. {bab['bab']}", S["h1"]))
        for j, it in enumerate(bab["items"], 1):
            blok = [Paragraph(f"{i}.{j}  {it['h']}", S["h2"])]
            blok += [Paragraph(t, S["body"]) for t in it.get("p", [])]
            sp = shot(it["shot"]) if it.get("shot") else None
            if sp:
                wimg = doc.width
                img = RLImage(sp, width=wimg, height=wimg * 900 / 1440)
                img.hAlign = "CENTER"
                blok += [img, Paragraph(f"Gambar {i}.{j} — {it['h']}", S["cap"])]
            st.append(KeepTogether(blok))
            if it.get("steps"):
                rows = [[Paragraph(str(n), S["cellw"]), Paragraph(s, S["cell"])] for n, s in enumerate(it["steps"], 1)]
                t = Table(rows, colWidths=[1.0 * cm, doc.width - 1.0 * cm])
                t.setStyle(TableStyle([("BACKGROUND", (0, 0), (0, -1), cT), ("VALIGN", (0, 0), (-1, -1), "MIDDLE"),
                                       ("GRID", (0, 0), (-1, -1), 0.4, colors.HexColor("#D9E2E8")),
                                       ("ROWBACKGROUNDS", (1, 0), (1, -1), [colors.white, colors.HexColor("#F6F9FA")]),
                                       ("TOPPADDING", (0, 0), (-1, -1), 4), ("BOTTOMPADDING", (0, 0), (-1, -1), 4)]))
                st += [t, Spacer(1, 6)]
            if it.get("table"):
                tb = it["table"]
                rows = [[Paragraph(h, S["cellw"]) for h in tb["head"]]] + [[Paragraph(f"<b>{r[0]}</b>", S["cell"])] + [Paragraph(v, S["cell"]) for v in r[1:]] for r in tb["rows"]]
                t = Table(rows, colWidths=[4.3 * cm, doc.width - 4.3 * cm], repeatRows=1)
                t.setStyle(TableStyle([("BACKGROUND", (0, 0), (-1, 0), cN), ("VALIGN", (0, 0), (-1, -1), "TOP"),
                                       ("GRID", (0, 0), (-1, -1), 0.4, colors.HexColor("#D9E2E8")),
                                       ("ROWBACKGROUNDS", (0, 1), (-1, -1), [colors.white, colors.HexColor("#F6F9FA")])]))
                st += [t, Spacer(1, 6)]
            for tip in it.get("tips", []):
                st.append(Paragraph(f"<font color='#B7791F'><b>Catatan:</b></font> {tip}", S["tip"]))
        st.append(PageBreak())
    doc.multiBuild(st)
    return path


if __name__ == "__main__":
    print(build_docx())
    print(build_pdf())
