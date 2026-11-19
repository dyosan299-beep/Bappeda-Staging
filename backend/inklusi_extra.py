"""PETA INKLUSI — fitur lanjutan:
1. Impor data ATS per kelurahan (template Excel, preview/validasi, commit, rollback)
2. Outbox notifikasi email (SMTP) untuk admin
3. Laporan PDF satu halaman per kelurahan (khusus pengguna login)
4. Galeri program NGO yang selesai (publik; nama NGO disamarkan)
"""
from __future__ import annotations

import io
import os
import re
import uuid
from datetime import datetime, timezone
from typing import Any, Dict, List, Optional

from fastapi import APIRouter, Depends, File, HTTPException, Query, Request, UploadFile
from fastapi.responses import StreamingResponse
from pydantic import BaseModel, EmailStr

import notifier
from inklusi_cerita import public_story
from inklusi import (SENSITIVE_ROLES, STAFF_ROLES, _clean, audit, mask_name, norm_wil, role_group)

now_iso = lambda: datetime.now(timezone.utc).isoformat()  # noqa: E731
ASSETS = os.path.join(os.path.dirname(__file__), "assets")

ATS_COLUMNS = ["kecamatan", "kelurahan", "tahun", "jenjang", "kelompok_usia", "status_pendidikan",
               "laki_laki", "perempuan"]
JENJANG = ["SD", "SMP", "SMA", "SMK", "PAUD", "LAINNYA"]
STATUS_PENDIDIKAN = ["Putus Sekolah", "Belum Pernah Sekolah", "Lulus Tidak Melanjutkan"]
USIA = ["5-6", "7-12", "13-15", "16-18", "Lainnya"]
MAX_UPLOAD = 10 * 1024 * 1024


def _int(v: Any) -> Optional[int]:
    if v is None or (isinstance(v, str) and not v.strip()):
        return None
    try:
        f = float(str(v).replace(",", ".").strip())
    except ValueError:
        raise ValueError(f"'{v}' bukan angka")
    if f < 0 or f != int(f):
        raise ValueError(f"'{v}' harus bilangan bulat >= 0")
    return int(f)


def _match_opt(v: Any, options: List[str]) -> Optional[str]:
    s = str(v or "").strip()
    if not s:
        return None
    for o in options:
        if norm_wil(o) == norm_wil(s):
            return o
    return "__INVALID__"


def _read_table(content: bytes, filename: str) -> List[Dict[str, Any]]:
    import pandas as pd
    name = (filename or "").lower()
    if name.endswith(".csv"):
        df = pd.read_csv(io.BytesIO(content), dtype=str, keep_default_na=False)
    elif name.endswith((".xlsx", ".xls")):
        xl = pd.ExcelFile(io.BytesIO(content))
        sheet = "DATA_ATS" if "DATA_ATS" in xl.sheet_names else xl.sheet_names[0]
        df = xl.parse(sheet, dtype=str, keep_default_na=False)
    else:
        raise HTTPException(status_code=422, detail="Format berkas harus .xlsx atau .csv")
    df.columns = [re.sub(r"[^a-z0-9]+", "_", str(c).strip().lower()).strip("_") for c in df.columns]
    alias = {"l": "laki_laki", "laki": "laki_laki", "lakilaki": "laki_laki", "p": "perempuan",
             "usia": "kelompok_usia", "umur": "kelompok_usia", "status": "status_pendidikan", "kec": "kecamatan",
             "kel": "kelurahan", "desa_kelurahan": "kelurahan"}
    df = df.rename(columns={c: alias.get(c, c) for c in df.columns})
    missing = [c for c in ("kecamatan", "kelurahan", "tahun", "laki_laki", "perempuan") if c not in df.columns]
    if missing:
        raise HTTPException(status_code=422, detail=f"Kolom wajib tidak ditemukan: {', '.join(missing)}. "
                                                    f"Gunakan template resmi.")
    return df.to_dict("records")


class CommitInput(BaseModel):
    preview_id: str
    mode: str = "ganti_tahun"  # ganti_tahun | tambah


class StuntingCommitInput(BaseModel):
    preview_id: str


MAX_PDF_UPLOAD = 25 * 1024 * 1024


class BisindoInput(BaseModel):
    halaman: str
    url: str = ""
    judul: str = ""


BISINDO_HALAMAN = {"beranda": "Beranda", "publik": "Dashboard Informasi Umum",
                   "peta_sosial": "Peta Sosial", "peta_kemiskinan": "Peta Kemiskinan"}
_YT = re.compile(r"(?:youtube\.com/(?:watch\?(?:.*&)?v=|embed/|shorts/|live/)|youtu\.be/)([A-Za-z0-9_-]{11})")
_VIMEO = re.compile(r"vimeo\.com/(?:video/)?(\d+)")


def bisindo_embed(url: str) -> Dict[str, str]:
    """Validasi tautan video BISINDO -> {jenis, embed}. Hanya https YouTube / Vimeo / berkas .mp4/.webm."""
    u = (url or "").strip()
    if not u.lower().startswith("https://"):
        raise HTTPException(status_code=422, detail="Tautan video harus diawali https://")
    m = _YT.search(u)
    if m:
        return {"jenis": "youtube", "embed": f"https://www.youtube-nocookie.com/embed/{m.group(1)}?cc_load_policy=1&rel=0&hl=id"}
    m = _VIMEO.search(u)
    if m:
        return {"jenis": "vimeo", "embed": f"https://player.vimeo.com/video/{m.group(1)}?texttrack=id"}
    if re.search(r"\.(mp4|webm)(\?.*)?$", u, re.I):
        return {"jenis": "video", "embed": u}
    raise HTTPException(status_code=422, detail="Gunakan tautan YouTube, Vimeo, atau berkas video .mp4/.webm")


class TestEmail(BaseModel):
    to: EmailStr


def build_router(db, current_user_dep, writer_dep, admin_dep) -> APIRouter:
    router = APIRouter(tags=["inklusi-extra"])

    async def staff_dep(user: dict = Depends(current_user_dep)):
        if user.get("role") not in STAFF_ROLES:
            raise HTTPException(status_code=403, detail="Akses khusus Operator/Admin")
        return user

    async def sensitive_dep(user: dict = Depends(current_user_dep)):
        if user.get("role") not in SENSITIVE_ROLES:
            raise HTTPException(status_code=403, detail="Akses khusus Admin/Super Admin")
        return user

    async def geo_index() -> Dict[str, Dict[str, Any]]:
        return {norm_wil(g.get("kelurahan")): _clean(g) for g in await db.geo_kelurahan.find({}).to_list(500)}

    # ================================================================ 1. ATS KELURAHAN
    @router.get("/inklusi/ats/template")
    async def ats_template(user: dict = Depends(staff_dep)):
        from openpyxl import Workbook
        from openpyxl.styles import Alignment, Font, PatternFill
        from openpyxl.worksheet.datavalidation import DataValidation
        geo = sorted((await geo_index()).values(), key=lambda g: (g.get("kecamatan") or "", g.get("kelurahan") or ""))
        wb = Workbook()
        ws = wb.active
        ws.title = "DATA_ATS"
        head_fill = PatternFill("solid", fgColor="232F3E")
        ws.append(ATS_COLUMNS)
        for c in ws[1]:
            c.font = Font(bold=True, color="6FE3CF")
            c.fill = head_fill
            c.alignment = Alignment(horizontal="center")
        tahun = datetime.now().year
        for g in geo:
            ws.append([g.get("kecamatan"), g.get("kelurahan"), tahun, "SD", "7-12", "Putus Sekolah", None, None])
        widths = [18, 26, 8, 10, 14, 26, 11, 11]
        for i, w in enumerate(widths):
            ws.column_dimensions[chr(65 + i)].width = w
        ws.freeze_panes = "A2"
        n = max(2, len(geo) + 1) + 500
        for col, opts in (("D", JENJANG), ("E", USIA), ("F", STATUS_PENDIDIKAN)):
            dv = DataValidation(type="list", formula1='"' + ",".join(opts) + '"', allow_blank=True)
            dv.add(f"{col}2:{col}{n}")
            ws.add_data_validation(dv)
        dvn = DataValidation(type="whole", operator="greaterThanOrEqual", formula1="0", allow_blank=True)
        dvn.add(f"G2:H{n}")
        ws.add_data_validation(dvn)

        ref = wb.create_sheet("REFERENSI")
        ref.append(["kecamatan", "kelurahan", "", "jenjang", "kelompok_usia", "status_pendidikan"])
        for c in ref[1]:
            c.font = Font(bold=True)
        rows = max(len(geo), len(JENJANG), len(USIA), len(STATUS_PENDIDIKAN))
        for i in range(rows):
            g = geo[i] if i < len(geo) else {}
            ref.append([g.get("kecamatan", ""), g.get("kelurahan", ""), "",
                        JENJANG[i] if i < len(JENJANG) else "", USIA[i] if i < len(USIA) else "",
                        STATUS_PENDIDIKAN[i] if i < len(STATUS_PENDIDIKAN) else ""])
        ref.column_dimensions["A"].width = 18
        ref.column_dimensions["B"].width = 26
        ref.column_dimensions["F"].width = 26

        pt = wb.create_sheet("PETUNJUK")
        for line in [
            "PETUNJUK PENGISIAN TEMPLATE DATA ANAK TIDAK SEKOLAH (ATS) PER KELURAHAN — PETA INKLUSI",
            "",
            "1. Isi lembar DATA_ATS. Satu baris = satu kombinasi kelurahan + tahun + jenjang + kelompok usia + status pendidikan.",
            "2. Kolom wajib: kecamatan, kelurahan, tahun, laki_laki, perempuan. Nama wilayah harus sesuai lembar REFERENSI.",
            "3. Baris dengan laki_laki DAN perempuan kosong akan dilewati (tidak diimpor).",
            "4. Tambahkan baris baru bila satu kelurahan memiliki lebih dari satu jenjang/status.",
            "5. jenjang: " + ", ".join(JENJANG) + " | kelompok_usia: " + ", ".join(USIA),
            "6. status_pendidikan: " + ", ".join(STATUS_PENDIDIKAN),
            "7. Unggah melalui menu Data ATS > Impor Data ATS Kelurahan. Sistem menampilkan pratinjau & validasi sebelum disimpan.",
            "8. Mode 'Ganti data tahun yang sama' menghapus data ATS kelurahan untuk tahun di berkas lalu menggantinya.",
            "9. Data yang diimpor bersifat agregat (jumlah anak) — JANGAN mencantumkan nama/NIK anak.",
        ]:
            pt.append([line])
        pt.column_dimensions["A"].width = 130
        pt["A1"].font = Font(bold=True, size=12)
        buf = io.BytesIO()
        wb.save(buf)
        buf.seek(0)
        return StreamingResponse(buf, media_type="application/vnd.openxmlformats-officedocument.spreadsheetml.sheet",
                                 headers={"Content-Disposition": 'attachment; filename="template_ats_kelurahan.xlsx"'})

    @router.post("/inklusi/ats/preview")
    async def ats_preview(request: Request, file: UploadFile = File(...), user: dict = Depends(writer_dep)):
        content = await file.read(MAX_UPLOAD + 1)
        if len(content) > MAX_UPLOAD:
            raise HTTPException(status_code=413, detail="Ukuran berkas maksimal 10 MB")
        if not content:
            raise HTTPException(status_code=422, detail="Berkas kosong")
        try:
            raw = _read_table(content, file.filename or "")
        except HTTPException:
            raise
        except Exception as e:  # noqa: BLE001
            raise HTTPException(status_code=422, detail=f"Berkas tidak dapat dibaca: {e}")
        geo = await geo_index()
        valid: List[Dict[str, Any]] = []
        errors: List[Dict[str, Any]] = []
        skipped = 0
        seen = set()
        for idx, r in enumerate(raw, start=2):
            try:
                lk = _int(r.get("laki_laki"))
                pr = _int(r.get("perempuan"))
            except ValueError as e:
                errors.append({"baris": idx, "pesan": f"Jumlah: {e}"})
                continue
            if lk is None and pr is None:
                skipped += 1
                continue
            msgs = []
            kel_n = norm_wil(r.get("kelurahan"))
            g = geo.get(kel_n)
            if not kel_n:
                msgs.append("kelurahan kosong")
            elif not g:
                msgs.append(f"kelurahan '{r.get('kelurahan')}' tidak dikenal")
            elif r.get("kecamatan") and norm_wil(r.get("kecamatan")) != norm_wil(g.get("kecamatan")):
                msgs.append(f"kelurahan '{g.get('kelurahan')}' berada di Kec. {g.get('kecamatan')}, bukan '{r.get('kecamatan')}'")
            try:
                tahun = _int(r.get("tahun"))
                if tahun is None or not 2000 <= tahun <= 2100:
                    msgs.append("tahun harus 2000-2100")
            except ValueError:
                tahun = None
                msgs.append("tahun tidak valid")
            jen = _match_opt(r.get("jenjang"), JENJANG)
            usia = _match_opt(r.get("kelompok_usia"), USIA)
            stp = _match_opt(r.get("status_pendidikan"), STATUS_PENDIDIKAN)
            if jen == "__INVALID__":
                msgs.append(f"jenjang '{r.get('jenjang')}' tidak valid")
            if usia == "__INVALID__":
                msgs.append(f"kelompok_usia '{r.get('kelompok_usia')}' tidak valid")
            if stp == "__INVALID__":
                msgs.append(f"status_pendidikan '{r.get('status_pendidikan')}' tidak valid")
            key = (kel_n, tahun, jen, usia, stp)
            if not msgs and key in seen:
                msgs.append("duplikat kombinasi kelurahan/tahun/jenjang/usia/status dalam berkas")
            if msgs:
                errors.append({"baris": idx, "pesan": "; ".join(msgs)})
                continue
            seen.add(key)
            valid.append({"kecamatan": g.get("kecamatan"), "kecamatan_norm": norm_wil(g.get("kecamatan")),
                          "kelurahan": g.get("kelurahan"), "kelurahan_norm": kel_n, "tahun": tahun,
                          "jenjang": jen or "LAINNYA", "kelompok_usia": usia or "Lainnya",
                          "status_pendidikan": stp or "Putus Sekolah", "laki_laki": lk or 0,
                          "perempuan": pr or 0, "jumlah": (lk or 0) + (pr or 0)})
        bid = str(uuid.uuid4())
        tahun_set = sorted({v["tahun"] for v in valid})
        summary = {"baris_dibaca": len(raw), "valid": len(valid), "error": len(errors), "dilewati_kosong": skipped,
                   "total_anak": sum(v["jumlah"] for v in valid),
                   "kelurahan": len({v["kelurahan_norm"] for v in valid}), "tahun": tahun_set}
        # satu pratinjau aktif per pengguna — pratinjau lama dibuang agar tidak menumpuk di DB
        await db.ats_import_batches.delete_many({"status": "preview", "oleh": user.get("email")})
        await db.ats_import_batches.insert_one({
            "id": bid, "status": "preview", "nama_berkas": (file.filename or "")[:160], "rows": valid,
            "errors": errors[:500], "ringkasan": summary, "oleh": user.get("email"), "created_at": now_iso()})
        per_kel: Dict[str, int] = {}
        for v in valid:
            per_kel[f"{v['kelurahan']} (Kec. {v['kecamatan']})"] = per_kel.get(f"{v['kelurahan']} (Kec. {v['kecamatan']})", 0) + v["jumlah"]
        existing = await db.ats_kelurahan.count_documents({"tahun": {"$in": tahun_set}}) if tahun_set else 0
        return {"preview_id": bid, "ringkasan": summary, "errors": errors[:200], "contoh": valid[:15],
                "per_kelurahan": sorted([{"wilayah": k, "jumlah": v} for k, v in per_kel.items()], key=lambda x: -x["jumlah"])[:20],
                "data_tahun_sama_saat_ini": existing}

    @router.post("/inklusi/ats/commit")
    async def ats_commit(inp: CommitInput, request: Request, user: dict = Depends(writer_dep)):
        b = await db.ats_import_batches.find_one({"id": inp.preview_id})
        if not b or b.get("status") != "preview":
            raise HTTPException(status_code=404, detail="Pratinjau tidak ditemukan atau sudah diproses")
        if b.get("oleh") != user.get("email") and user.get("role") not in SENSITIVE_ROLES:
            raise HTTPException(status_code=403, detail="Pratinjau milik pengguna lain")
        rows = b.get("rows") or []
        if not rows:
            raise HTTPException(status_code=422, detail="Tidak ada baris valid untuk diimpor")
        if inp.mode not in ("ganti_tahun", "tambah"):
            raise HTTPException(status_code=422, detail="Mode harus ganti_tahun atau tambah")
        dihapus = 0
        tahun_set = sorted({r["tahun"] for r in rows})
        if inp.mode == "ganti_tahun":
            res = await db.ats_kelurahan.delete_many({"tahun": {"$in": tahun_set}})
            dihapus = getattr(res, "deleted_count", 0)
        docs = [{**r, "id": str(uuid.uuid4()), "import_batch": b["id"], "sumber": b.get("nama_berkas"),
                 "created_at": now_iso()} for r in rows]
        await db.ats_kelurahan.insert_many(docs)
        await db.ats_import_batches.update_one({"id": b["id"]}, {"$set": {
            "status": "diimpor", "mode": inp.mode, "dihapus_sebelumnya": dihapus, "rows": [],
            "jumlah_baris": len(docs), "diimpor_at": now_iso()}})
        await audit(db, user, "import_excel", "ats_kelurahan", b["id"],
                    {"berkas": b.get("nama_berkas"), "baris": len(docs), "mode": inp.mode, "tahun": tahun_set}, request)
        return {"ok": True, "batch_id": b["id"], "diimpor": len(docs), "dihapus_sebelumnya": dihapus, "tahun": tahun_set}

    @router.get("/inklusi/ats/batches")
    async def ats_batches(user: dict = Depends(staff_dep)):
        rows = await db.ats_import_batches.find({"status": {"$in": ["diimpor", "dibatalkan"]}}).sort(
            "created_at", -1).limit(50).to_list(50)
        return {"items": [{k: v for k, v in _clean(r).items() if k not in ("rows", "errors")} for r in rows]}

    @router.delete("/inklusi/ats/batches/{bid}")
    async def ats_rollback(bid: str, request: Request, user: dict = Depends(sensitive_dep)):
        b = await db.ats_import_batches.find_one({"id": bid})
        if not b or b.get("status") != "diimpor":
            raise HTTPException(status_code=404, detail="Batch tidak ditemukan atau sudah dibatalkan")
        res = await db.ats_kelurahan.delete_many({"import_batch": bid})
        await db.ats_import_batches.update_one({"id": bid}, {"$set": {"status": "dibatalkan", "dibatalkan_at": now_iso(),
                                                                       "dibatalkan_oleh": user.get("email")}})
        await audit(db, user, "rollback_import", "ats_kelurahan", bid, {"dihapus": getattr(res, "deleted_count", 0)}, request)
        return {"ok": True, "dihapus": getattr(res, "deleted_count", 0)}

    async def ats_kelurahan_agg(tahun: Optional[int] = None) -> Dict[str, Any]:
        rows = await db.ats_kelurahan.find({}).to_list(50000)
        tahun_list = sorted({int(r.get("tahun") or 0) for r in rows}, reverse=True)
        if not rows:
            return {"tersedia": False, "tahun": None, "tahun_list": [], "items": [], "total": 0}
        t = tahun or tahun_list[0]
        agg: Dict[str, Dict[str, Any]] = {}
        jen: Dict[str, int] = {}
        stp: Dict[str, int] = {}
        for r in rows:
            if int(r.get("tahun") or 0) != t:
                continue
            a = agg.setdefault(r["kelurahan_norm"], {"kecamatan": r["kecamatan"], "kelurahan": r["kelurahan"],
                                                     "laki_laki": 0, "perempuan": 0, "jumlah": 0})
            a["laki_laki"] += int(r.get("laki_laki") or 0)
            a["perempuan"] += int(r.get("perempuan") or 0)
            a["jumlah"] += int(r.get("jumlah") or 0)
            jen[r.get("jenjang") or "-"] = jen.get(r.get("jenjang") or "-", 0) + int(r.get("jumlah") or 0)
            stp[r.get("status_pendidikan") or "-"] = stp.get(r.get("status_pendidikan") or "-", 0) + int(r.get("jumlah") or 0)
        items = sorted(agg.values(), key=lambda x: -x["jumlah"])
        return {"tersedia": True, "tahun": t, "tahun_list": tahun_list, "items": items,
                "total": sum(i["jumlah"] for i in items),
                "laki_laki": sum(i["laki_laki"] for i in items), "perempuan": sum(i["perempuan"] for i in items),
                "per_jenjang": [{"kategori": k, "jumlah": v} for k, v in sorted(jen.items(), key=lambda x: -x[1])],
                "per_status": [{"kategori": k, "jumlah": v} for k, v in sorted(stp.items(), key=lambda x: -x[1])]}

    @router.get("/inklusi/ats/kelurahan")
    async def ats_kelurahan(tahun: Optional[int] = None, user: dict = Depends(current_user_dep)):
        return await ats_kelurahan_agg(tahun)

    @router.get("/public/ats/kelurahan")
    async def public_ats_kelurahan(tahun: Optional[int] = None):
        return await ats_kelurahan_agg(tahun)

    # ================================================================ 2. EMAIL OUTBOX
    # ================================================================ 1b. IMPOR PDF BALITA STUNTING
    @router.post("/inklusi/stunting/import/preview")
    async def stunting_import_preview(request: Request, file: UploadFile = File(...),
                                      user: dict = Depends(sensitive_dep)):
        from starlette.concurrency import run_in_threadpool
        import inklusi_import

        name = (file.filename or "").strip()
        if not name.lower().endswith(".pdf"):
            raise HTTPException(status_code=422, detail="Format berkas harus .pdf")
        content = await file.read(MAX_PDF_UPLOAD + 1)
        if len(content) > MAX_PDF_UPLOAD:
            raise HTTPException(status_code=413, detail="Ukuran berkas maksimal 25 MB")
        if not content.startswith(b"%PDF"):
            raise HTTPException(status_code=422, detail="Berkas bukan PDF yang valid")
        try:
            rows = await run_in_threadpool(inklusi_import.extract_stunting_rows, content)
        except Exception as e:  # noqa: BLE001
            raise HTTPException(status_code=422, detail=f"PDF tidak dapat dibaca: {e}")
        bid = str(uuid.uuid4())
        res = await inklusi_import.build_stunting_docs(db, rows, name[:160], bid)
        docs = res["docs"]
        if not docs:
            raise HTTPException(status_code=422, detail=(
                "Tidak ada baris data balita yang terbaca. Pastikan PDF berbasis teks (bukan hasil scan) "
                "dengan kolom: No, Nama, JK, Tgl Lahir, Nama Orang Tua, Puskesmas, Kelurahan, Alamat, TB/U."))

        def count(key):
            c: Dict[str, int] = {}
            for d in docs:
                c[str(d.get(key) or "-")] = c.get(str(d.get(key) or "-"), 0) + 1
            return [{"kategori": k, "jumlah": v} for k, v in sorted(c.items(), key=lambda x: -x[1])]
        ringkasan = {"baris_dibaca": res["baris"], "valid": len(docs), "dilewati": res["dilewati"],
                     "duplikat": len(res["duplikat"]),
                     "kelurahan_tidak_cocok": res["kelurahan_tidak_cocok"],
                     "kelurahan": len({d["kelurahan_norm"] for d in docs if d.get("kelurahan_norm")})}
        await db.stunting_import_batches.delete_many({"status": "preview", "oleh": user.get("email")})
        await db.stunting_import_batches.insert_one({
            "id": bid, "status": "preview", "nama_berkas": name[:160], "docs": docs, "ringkasan": ringkasan,
            "daftar_tidak_cocok": res["daftar_tidak_cocok"][:100], "duplikat": res["duplikat"][:500],
            "oleh": user.get("email"), "created_at": now_iso()})
        contoh = [{"nama": mask_name(d["nama"]), "jk": d["jk"], "kelurahan": d["kelurahan"],
                   "kecamatan": d["kecamatan"], "puskesmas": d["puskesmas"], "status_tbu": d["status_tbu"],
                   "kelompok_umur": d["kelompok_umur"]} for d in docs[:10]]
        return {"preview_id": bid, "ringkasan": ringkasan, "per_kecamatan": count("kecamatan"),
                "status_tbu": count("status_tbu"), "jenis_kelamin": count("jk"),
                "daftar_tidak_cocok": res["daftar_tidak_cocok"][:30], "duplikat": res["duplikat"][:100], "contoh": contoh,
                "data_saat_ini": await db.stunting_children.count_documents({})}

    @router.post("/inklusi/stunting/import/commit")
    async def stunting_import_commit(inp: StuntingCommitInput, request: Request, user: dict = Depends(sensitive_dep)):
        import inklusi_import

        b = await db.stunting_import_batches.find_one({"id": inp.preview_id})
        if not b or b.get("status") != "preview":
            raise HTTPException(status_code=404, detail="Pratinjau tidak ditemukan atau sudah diproses")
        docs = b.get("docs") or []
        if not docs:
            raise HTTPException(status_code=422, detail="Tidak ada baris valid untuk diimpor")
        # klaim atomik via primary key -> permintaan ganda (klik dua kali / beberapa worker) ditolak
        try:
            await db.stunting_import_claims.insert_one({"_id": b["id"], "oleh": user.get("email"), "at": now_iso()})
        except Exception:  # noqa: BLE001  (duplicate key)
            raise HTTPException(status_code=409, detail="Pratinjau ini sedang/sudah diproses")
        await db.stunting_import_batches.update_one({"id": b["id"]}, {"$set": {"status": "memproses"}})
        sebelumnya = await db.stunting_children.count_documents({})
        try:
            n = await inklusi_import.save_stunting_docs(
                db, docs, b.get("nama_berkas") or "", b["id"], (b.get("ringkasan") or {}).get("baris_dibaca", len(docs)),
                (b.get("ringkasan") or {}).get("kelurahan_tidak_cocok", 0), user.get("email") or "")
        except Exception as e:  # noqa: BLE001
            await db.stunting_import_batches.update_one({"id": b["id"]}, {"$set": {"status": "preview"}})
            await db.stunting_import_claims.delete_one({"_id": b["id"]})
            raise HTTPException(status_code=500, detail=f"Gagal menyimpan data stunting: {e}")
        await db.stunting_import_batches.update_many({"status": "diimpor"}, {"$set": {"status": "diganti"}})
        await db.stunting_import_batches.update_one({"id": b["id"]}, {"$set": {
            "status": "diimpor", "docs": [], "jumlah_baris": n, "dihapus_sebelumnya": sebelumnya,
            "diimpor_at": now_iso()}})
        await audit(db, user, "import_pdf", "stunting_children", b["id"],
                    {"berkas": b.get("nama_berkas"), "baris": n, "dihapus_sebelumnya": sebelumnya}, request)
        return {"ok": True, "batch_id": b["id"], "diimpor": n, "dihapus_sebelumnya": sebelumnya}

    @router.get("/inklusi/stunting/import/batches")
    async def stunting_import_batches(user: dict = Depends(sensitive_dep)):
        rows = await db.stunting_import_batches.find({"status": {"$in": ["diimpor", "diganti"]}}).sort(
            "created_at", -1).limit(30).to_list(30)
        return {"items": [{k: v for k, v in _clean(r).items() if k != "docs"} for r in rows]}

    # ================================================================ AKSESIBILITAS: VIDEO BISINDO
    async def _bisindo_cfg() -> Dict[str, Any]:
        d = await db.a11y_settings.find_one({"_id": "bisindo"}) or {}
        return d.get("videos") or {}

    @router.get("/public/a11y/bisindo")
    async def public_bisindo():
        v = await _bisindo_cfg()
        return {"videos": {k: {"judul": x.get("judul") or "", "jenis": x["jenis"], "embed": x["embed"]}
                           for k, x in v.items() if k in BISINDO_HALAMAN and x.get("embed")}}

    @router.get("/inklusi/a11y/bisindo")
    async def admin_bisindo(user: dict = Depends(sensitive_dep)):
        v = await _bisindo_cfg()
        return {"halaman": [{"id": k, "label": lbl, **(v.get(k) or {})} for k, lbl in BISINDO_HALAMAN.items()]}

    @router.put("/inklusi/a11y/bisindo")
    async def set_bisindo(inp: BisindoInput, request: Request, user: dict = Depends(sensitive_dep)):
        if inp.halaman not in BISINDO_HALAMAN:
            raise HTTPException(status_code=422, detail="Halaman tidak dikenal")
        v = await _bisindo_cfg()
        if inp.url.strip():
            v[inp.halaman] = {"url": inp.url.strip()[:500], "judul": inp.judul.strip()[:160], **bisindo_embed(inp.url),
                              "oleh": user.get("email"), "diubah_at": now_iso()}
        else:
            v.pop(inp.halaman, None)
        await db.a11y_settings.update_one({"_id": "bisindo"}, {"$set": {"videos": v}}, upsert=True)
        await audit(db, user, "update" if inp.url.strip() else "delete", "a11y_bisindo", inp.halaman,
                    {"url": inp.url.strip()[:200]}, request)
        return {"ok": True, "halaman": inp.halaman, "video": v.get(inp.halaman)}

    @router.get("/inklusi/email-outbox")
    async def email_outbox(status: Optional[str] = None, page: int = Query(1, ge=1),
                           size: int = Query(25, ge=1, le=100), user: dict = Depends(sensitive_dep)):
        f: Dict[str, Any] = {}
        if status:
            f["status"] = status
        total = await db.email_outbox.count_documents(f)
        rows = await db.email_outbox.find(f).sort("created_at", -1).skip((page - 1) * size).limit(size).to_list(size)
        counts = {s: await db.email_outbox.count_documents({"status": s})
                  for s in ("terkirim", "belum_terkirim", "gagal", "antri")}
        return {"smtp": notifier.public_status(), "total": total, "page": page, "pages": max(1, -(-total // size)),
                "ringkasan": counts,
                "items": [{k: v for k, v in _clean(r).items() if k != "body_html"} for r in rows]}

    @router.post("/inklusi/email-outbox/kirim-ulang")
    async def email_retry(request: Request, user: dict = Depends(sensitive_dep)):
        if not notifier.smtp_ready():
            raise HTTPException(status_code=409, detail="SMTP belum dikonfigurasi. Isi SMTP_HOST, SMTP_PORT, SMTP_USER, "
                                                        "SMTP_PASSWORD, SMTP_FROM di .env backend lalu restart.")
        res = await notifier.flush_pending(db, include_failed=True)
        await audit(db, user, "kirim_ulang_email", "email_outbox", "", res, request)
        return res

    @router.post("/inklusi/email-outbox/tes")
    async def email_test(inp: TestEmail, request: Request, user: dict = Depends(sensitive_dep)):
        res = await notifier.queue_email(
            db, [inp.to], "[PETA INKLUSI] Tes konfigurasi email",
            "Email tes dari PETA INKLUSI. Jika Anda menerima email ini, konfigurasi SMTP sudah benar.",
            "<p>Email tes dari <b>PETA INKLUSI</b>. Jika Anda menerima email ini, konfigurasi SMTP sudah benar.</p>",
            jenis="tes", ref=user.get("email", ""))
        return {"status": res.get("status"), "error": res.get("error", "")}

    # ================================================================ 3. LAPORAN PDF KELURAHAN
    async def laporan_data(kecamatan: str, kelurahan: str) -> Dict[str, Any]:
        geo = await geo_index()
        g = geo.get(norm_wil(kelurahan))
        if not g or (kecamatan and norm_wil(g.get("kecamatan")) != norm_wil(kecamatan)):
            raise HTTPException(status_code=404, detail="Kelurahan tidak ditemukan")
        kel_n, kec_n = norm_wil(g["kelurahan"]), norm_wil(g["kecamatan"])
        reg = next((_clean(r) for r in await db.regions.find({}).to_list(100) if norm_wil(r.get("nama")) == kec_n), {})
        n_kel_kec = sum(1 for x in geo.values() if norm_wil(x.get("kecamatan")) == kec_n) or 1
        # disabilitas
        dis = [r for r in await db.disability_region_stats.find({"kelurahan_norm": kel_n}).to_list(100)]
        dis_val = sum(int(r.get("jumlah") or 0) for r in dis) if dis else None
        # stunting
        st = await db.stunting_children.find({"kelurahan_norm": kel_n}).to_list(5000)
        st_kec_by_name = await db.stunting_children.count_documents({"kecamatan_norm": kec_n})
        # ats
        ats_rows = await db.ats_kelurahan.find({"kelurahan_norm": kel_n}).to_list(2000)
        ats_t = max((int(r.get("tahun") or 0) for r in ats_rows), default=None)
        ats_rows = [r for r in ats_rows if int(r.get("tahun") or 0) == ats_t] if ats_t else []
        # kemiskinan
        vs = next((_clean(v) for v in await db.village_stats.find({}).to_list(2000)
                   if norm_wil(v.get("kelurahan")) == kel_n), None)
        # program NGO
        inq = [i for i in await db.ngo_inquiries.find({"kecamatan": g["kecamatan"]}).to_list(1000)
               if not i.get("kelurahan") or norm_wil(i.get("kelurahan")) == kel_n]
        inq = [i for i in inq if i.get("status") not in ("REJECTED",)]
        # musrenbang
        mus = []
        for m in await db.musrenbang_usulan.find({}).to_list(1000):
            lok = norm_wil(m.get("lokasi"))
            if kel_n in lok or kec_n in lok:
                mus.append(_clean(m))
        return {"geo": g, "region": reg, "n_kel_kec": n_kel_kec, "dis": dis_val,
                "dis_tahun": dis[0].get("tahun") if dis else None, "stunting": st, "st_kec_by_name": st_kec_by_name,
                "ats": ats_rows, "ats_tahun": ats_t, "vs": vs, "inquiries": inq, "musrenbang": mus[:4]}

    def render_pdf(d: Dict[str, Any], user: Dict[str, Any]) -> bytes:
        from reportlab.lib.colors import HexColor, white
        from reportlab.lib.pagesizes import A4
        from reportlab.lib.utils import ImageReader, simpleSplit
        from reportlab.pdfgen import canvas

        W, H = A4
        M = 36
        buf = io.BytesIO()
        c = canvas.Canvas(buf, pagesize=A4)
        g, reg = d["geo"], d["region"]
        c.setTitle(f"Laporan Wilayah Kel. {g['kelurahan']} - PETA INKLUSI")
        c.setAuthor("PETA INKLUSI - Bappeda Kota Makassar")
        NAVY, MINT, TEAL = HexColor("#232F3E"), HexColor("#6FE3CF"), HexColor("#117A69")
        SL5, SL7, SL9 = HexColor("#64748B"), HexColor("#334155"), HexColor("#0F172A")
        fmt = lambda n: "-" if n is None else f"{int(n):,}".replace(",", ".")  # noqa: E731

        def text(x, y, s, size=9, font="Helvetica", color=SL9):
            c.setFont(font, size)
            c.setFillColor(color)
            c.drawString(x, y, str(s))

        def para(x, y, s, width, size=8.5, lead=11, font="Helvetica", color=SL7, max_lines=4):
            lines = simpleSplit(str(s), font, size, width)
            if len(lines) > max_lines:
                lines = lines[:max_lines]
                lines[-1] = lines[-1][: max(0, len(lines[-1]) - 3)] + "..."
            c.setFont(font, size)
            c.setFillColor(color)
            for ln in lines:
                c.drawString(x, y, ln)
                y -= lead
            return y

        # ---- header
        c.setFillColor(NAVY)
        c.rect(0, H - 92, W, 92, stroke=0, fill=1)
        try:
            c.drawImage(ImageReader(os.path.join(ASSETS, "logo-icon-small.png")), M, H - 80, 64, 64, mask="auto")
        except Exception:  # noqa: BLE001
            pass
        text(M + 76, H - 36, "PETA INKLUSI", 18, "Helvetica-Bold", MINT)
        text(M + 76, H - 52, "LAPORAN RINGKAS WILAYAH  |  BAHAN MUSRENBANG", 8.5, "Helvetica-Bold", white)
        text(M + 76, H - 66, "Bappeda Kota Makassar", 8, "Helvetica", HexColor("#CBD5E1"))
        c.setFont("Helvetica-Bold", 15)
        c.setFillColor(white)
        c.drawRightString(W - M, H - 40, f"Kel. {g['kelurahan']}")
        c.setFont("Helvetica", 9)
        c.setFillColor(HexColor("#CBD5E1"))
        c.drawRightString(W - M, H - 55, f"Kec. {g['kecamatan']}  |  Kota Makassar")
        luas = g.get("luas_ha")
        c.drawRightString(W - M, H - 68, f"Luas wilayah: {str(luas).replace('.', ',')} ha" if luas else "")

        # ---- 4 kartu
        y0 = H - 110
        cw, ch = (W - 2 * M - 12) / 2, 172
        st = d["stunting"]
        sp = sum(1 for s in st if s.get("status_tbu") == "Sangat Pendek")
        pdk = sum(1 for s in st if s.get("status_tbu") == "Pendek")
        stL = sum(1 for s in st if s.get("jk") == "L")
        ats = d["ats"]
        ats_tot = sum(int(r.get("jumlah") or 0) for r in ats) if ats else None
        vs = d["vs"] or {}
        n = d["n_kel_kec"]
        cards = [
            ("DISABILITAS", "#117A69", d["dis"], "orang",
             [f"Data tahun {d['dis_tahun']}" if d["dis_tahun"] else "Belum ada data tingkat kelurahan",
              f"Kecamatan {g['kecamatan']}: {fmt(reg.get('disabilitas'))} orang",
              f"Rata-rata per kelurahan di kecamatan: {fmt((reg.get('disabilitas') or 0) / n)}"],
             "Rekap disabilitas per kelurahan / Matriks Bappeda"),
            ("STUNTING", "#C8375B", len(st) if st else None, "balita (by-name 2026)",
             [f"Sangat pendek: {fmt(sp)}   |   Pendek: {fmt(pdk)}" if st else "Belum ada data by-name kelurahan ini",
              f"Laki-laki: {fmt(stL)}   |   Perempuan: {fmt(len(st) - stL)}" if st else "",
              f"Kecamatan: {fmt(reg.get('stunting_anak'))} anak (rekap)  |  by-name: {fmt(d['st_kec_by_name'])}"],
             "Data balita stunting 2026 (Kec. Makassar & Tallo)"),
            ("ANAK TIDAK SEKOLAH", "#B7791F", ats_tot, f"anak (tahun {d['ats_tahun']})" if ats else "anak",
             ([f"Laki-laki: {fmt(sum(int(r.get('laki_laki') or 0) for r in ats))}   |   Perempuan: "
               f"{fmt(sum(int(r.get('perempuan') or 0) for r in ats))}",
               "Jenjang: " + ", ".join(f"{j} {fmt(sum(int(r.get('jumlah') or 0) for r in ats if r.get('jenjang') == j))}"
                                     for j in sorted({r.get('jenjang') for r in ats}))]
              if ats else ["Belum ada data ATS tingkat kelurahan (impor via menu Data ATS)"])
             + [f"Kecamatan {g['kecamatan']}: {fmt(reg.get('ats'))} anak (Matriks ATS)"],
             "Impor data ATS kelurahan / Matriks ATS"),
            ("KEMISKINAN", "#3B4F6B", vs.get("desil_1_2") if vs else None, "KK desil 1-2 (DTSEN)",
             ([f"Rumah tangga terdata: {fmt(vs.get('total_households'))}  |  {str(vs.get('persen_desil_1_2') or 0).replace('.', ',')}% desil 1-2",
               f"PBI Nasional: {fmt(vs.get('pbi_nas'))}  |  PBI Pemda: {fmt(vs.get('pbi_pemda'))}",
               f"Rumah rentan: {fmt(vs.get('rumah_rentan'))}  |  Sanitasi tdk layak: {fmt(vs.get('sanitasi_tidak_layak'))}"]
              if vs else ["Belum ada data DTSEN kelurahan ini"])
             + [f"Kecamatan: {fmt(reg.get('kemiskinan_ekstrim_kk'))} KK miskin ekstrem"],
             "DTSEN / Matriks Kemiskinan"),
        ]
        for i, (title, col, val, unit, lines, src) in enumerate(cards):
            x = M + (i % 2) * (cw + 12)
            y = y0 - (i // 2) * (ch + 12)
            c.setFillColor(HexColor("#F8FAFC"))
            c.setStrokeColor(HexColor("#E2E8F0"))
            c.roundRect(x, y - ch, cw, ch, 8, stroke=1, fill=1)
            c.setFillColor(HexColor(col))
            c.rect(x, y - 5, cw, 5, stroke=0, fill=1)
            text(x + 14, y - 24, title, 9.5, "Helvetica-Bold", HexColor(col))
            text(x + 14, y - 58, fmt(val) if val is not None else "Belum ada data",
                 28 if val is not None else 16, "Helvetica-Bold", SL9)
            text(x + 14, y - 74, unit if val is not None else "", 8.5, "Helvetica", SL5)
            yy = y - 96
            for ln in [ln for ln in lines if ln]:
                yy = para(x + 14, yy, ln, cw - 28, 8.3, 11, max_lines=2)
            text(x + 14, y - ch + 12, f"Sumber: {src}", 6.8, "Helvetica-Oblique", SL5)

        # ---- program NGO & musrenbang
        y = y0 - 2 * (ch + 12) - 8
        colw = (W - 2 * M - 12) / 2
        c.setFillColor(NAVY)
        text(M, y, "PROGRAM NGO DI WILAYAH INI", 9.5, "Helvetica-Bold", NAVY)
        text(M + colw + 12, y, "USULAN MUSRENBANG TEMATIK TERKAIT", 9.5, "Helvetica-Bold", NAVY)
        c.setStrokeColor(MINT)
        c.setLineWidth(1.5)
        c.line(M, y - 4, M + colw, y - 4)
        c.line(M + colw + 12, y - 4, W - M, y - 4)
        yl = y - 18
        see_ngo = user.get("role") in STAFF_ROLES
        if d["inquiries"]:
            for i in d["inquiries"][:5]:
                nm = i.get("nama_ngo") if see_ngo else mask_name(i.get("nama_ngo"))
                yl = para(M, yl, f"- {i.get('program_usulan')} ({i.get('kategori')}) - {nm}; "
                                 f"{fmt(i.get('jumlah_penerima'))} penerima; status: {notifier.STATUS_LABEL.get(i.get('status'), i.get('status'))}",
                          colw, 8.2, 10.5, max_lines=2) - 3
        else:
            yl = para(M, yl, "Belum ada inquiry/program NGO untuk wilayah ini.", colw, 8.2, 10.5, color=SL5)
        yr = y - 18
        if d["musrenbang"]:
            for m in d["musrenbang"]:
                yr = para(M + colw + 12, yr, f"- [{m.get('kelompok')}] {m.get('usulan_kegiatan')} - {m.get('permasalahan')}",
                          colw, 8.2, 10.5, max_lines=2) - 3
        else:
            yr = para(M + colw + 12, yr, "Tidak ada usulan Musrenbang Tematik yang menyebut kelurahan/kecamatan ini "
                                         "secara spesifik. Usulan lintas kota tersedia di menu Manajemen Program.",
                      colw, 8.2, 10.5, color=SL5)

        # ---- catatan analisis otomatis
        y = min(yl, yr) - 12
        text(M, y, "CATATAN UNTUK PEMBAHASAN MUSRENBANG", 9.5, "Helvetica-Bold", NAVY)
        c.line(M, y - 4, W - M, y - 4)
        notes = []
        if d["dis"] is not None and reg.get("disabilitas"):
            share = d["dis"] / max(1, reg["disabilitas"]) * 100
            notes.append(f"Disabilitas: {fmt(d['dis'])} orang, setara {share:.0f}% dari total kecamatan "
                         f"({'di atas' if d['dis'] > reg['disabilitas'] / n else 'di bawah'} rata-rata kelurahan).")
        if st:
            notes.append(f"Stunting: {fmt(len(st))} balita terdata by-name, {fmt(sp)} di antaranya sangat pendek - "
                         f"prioritaskan intervensi gizi spesifik & pendampingan keluarga.")
        if vs and vs.get("persen_desil_1_2") is not None:
            notes.append(f"Kemiskinan: {str(vs.get('persen_desil_1_2')).replace('.', ',')}% rumah tangga berada di desil 1-2; "
                         f"{fmt(vs.get('rumah_rentan'))} rumah kondisi rentan dan {fmt(vs.get('sanitasi_tidak_layak'))} sanitasi tidak layak.")
        if ats:
            notes.append(f"ATS: {fmt(ats_tot)} anak tidak sekolah (tahun {d['ats_tahun']}) - dorong program kembali ke sekolah.")
        if not notes:
            notes.append("Data tingkat kelurahan masih terbatas; gunakan angka kecamatan sebagai acuan awal dan lengkapi data melalui impor.")
        yy = y - 18
        for ntext in notes[:4]:
            yy = para(M, yy, f"- {ntext}", W - 2 * M, 8.4, 11, max_lines=2) - 2

        # ---- footer
        c.setFillColor(HexColor("#F1F5F9"))
        c.rect(0, 0, W, 34, stroke=0, fill=1)
        waktu = datetime.now(timezone.utc).astimezone().strftime("%d-%m-%Y %H:%M")
        text(M, 20, "Dokumen ini hanya memuat data agregat - tanpa NIK, nama, alamat, email, atau telepon perorangan.",
             7, "Helvetica", SL5)
        text(M, 10, f"Dicetak oleh {user.get('email')} ({role_group(user.get('role'))}) pada {waktu}  |  PETA INKLUSI",
             7, "Helvetica", SL5)
        c.setFont("Helvetica-Bold", 7)
        c.setFillColor(TEAL)
        c.drawRightString(W - M, 10, "Halaman 1/1")
        c.showPage()
        c.save()
        return buf.getvalue()

    @router.get("/inklusi/laporan/kelurahan")
    async def laporan_kelurahan(request: Request, kelurahan: str = Query(..., min_length=2),
                                kecamatan: str = Query(""), user: dict = Depends(current_user_dep)):
        d = await laporan_data(kecamatan, kelurahan)
        pdf = render_pdf(d, user)
        await audit(db, user, "unduh_laporan_pdf", "laporan_kelurahan", d["geo"]["kelurahan"],
                    {"kecamatan": d["geo"]["kecamatan"]}, request)
        safe = re.sub(r"[^A-Za-z0-9]+", "_", d["geo"]["kelurahan"]).strip("_")
        return StreamingResponse(io.BytesIO(pdf), media_type="application/pdf",
                                 headers={"Content-Disposition": f'attachment; filename="Laporan_Kel_{safe}_PETA_INKLUSI.pdf"'})

    # ================================================================ 4. GALERI PROGRAM SELESAI (publik)
    @router.get("/public/program-selesai")
    async def program_selesai(kategori: Optional[str] = None):
        f: Dict[str, Any] = {"status": "COMPLETED"}
        if kategori:
            f["kategori"] = kategori
        rows = await db.ngo_inquiries.find(f).sort("updated_at", -1).limit(60).to_list(60)
        items = []
        for r in rows:
            selesai = next((h.get("waktu") for h in reversed(r.get("riwayat") or []) if h.get("status") == "COMPLETED"),
                           r.get("updated_at"))
            mulai = next((h.get("waktu") for h in (r.get("riwayat") or []) if h.get("status") == "PROGRAM_IMPLEMENTATION"), None)
            cerita = public_story(await db.program_stories.find_one({"inquiry_id": r.get("id")}))
            items.append({"id": r.get("id"), "program": r.get("program_usulan"), "kategori": r.get("kategori"),
                          "cerita": cerita,
                          "kecamatan": r.get("kecamatan"), "kelurahan": r.get("kelurahan") or "",
                          "jumlah_penerima": r.get("jumlah_penerima"), "target_penerima": r.get("target_penerima"),
                          "durasi_bulan": r.get("durasi_bulan"), "ngo": mask_name(r.get("nama_ngo")),
                          "mulai": mulai, "selesai": selesai})
        penerima = lambda i: int((i["cerita"] or {}).get("realisasi_penerima") or i["jumlah_penerima"] or 0)  # noqa: E731
        return {"total": len(items), "total_penerima": sum(penerima(i) for i in items),
                "dengan_cerita": sum(1 for i in items if i["cerita"]),
                "kecamatan_terjangkau": len({i["kecamatan"] for i in items}), "items": items}

    return router
