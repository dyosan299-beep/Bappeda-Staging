"""PETA INKLUSI — Cerita Dampak Program.

NGO (pemilik inquiry) mengisi ringkasan hasil, realisasi penerima, testimoni, dan foto saat program
berstatus MONITORING/COMPLETED. Cerita tampil di galeri publik HANYA setelah disetujui admin.
Foto: dikompresi & metadata EXIF (termasuk lokasi GPS) dibuang, disimpan di MariaDB (bukan disk pod).
"""
from __future__ import annotations

import base64
import io
import re
import uuid
from datetime import datetime, timezone
from typing import Any, Dict, List, Optional

from fastapi import APIRouter, Depends, File, Form, HTTPException, Request, UploadFile
from fastapi.responses import Response
from pydantic import BaseModel, Field, field_validator

import notifier
from inklusi import SENSITIVE_ROLES, STAFF_ROLES, _clean, _strip_tags, audit, role_group

now_iso = lambda: datetime.now(timezone.utc).isoformat()  # noqa: E731
STATUS_BOLEH = ("MONITORING", "COMPLETED")
MAX_FOTO = 5
MAX_FOTO_BYTES = 8 * 1024 * 1024
STATUS_CERITA = {"menunggu_review": "Menunggu review", "dipublikasikan": "Dipublikasikan", "ditolak": "Perlu perbaikan"}


class Testimoni(BaseModel):
    kutipan: str = Field(..., min_length=10, max_length=600)
    sumber: str = Field(..., min_length=3, max_length=120)  # peran, bukan nama lengkap

    @field_validator("kutipan", "sumber")
    @classmethod
    def _xss(cls, v):
        return _strip_tags(v)


class CeritaInput(BaseModel):
    ringkasan_hasil: str = Field(..., min_length=30, max_length=3000)
    realisasi_penerima: int = Field(..., ge=0, le=10_000_000)
    testimoni: List[Testimoni] = Field(default_factory=list, max_length=3)
    persetujuan: bool

    @field_validator("ringkasan_hasil")
    @classmethod
    def _xss(cls, v):
        return _strip_tags(v)


class ReviewInput(BaseModel):
    keputusan: str  # publikasikan | tolak
    catatan: str = Field("", max_length=1000)

    @field_validator("catatan")
    @classmethod
    def _xss(cls, v):
        return _strip_tags(v)


def _process_image(data: bytes) -> bytes:
    """Validasi gambar, buang EXIF/GPS, perkecil ke maks 1600px, simpan JPEG q82."""
    from PIL import Image, ImageOps
    try:
        im = Image.open(io.BytesIO(data))
        im.verify()
        im = Image.open(io.BytesIO(data))
    except Exception:  # noqa: BLE001
        raise HTTPException(status_code=422, detail="Berkas bukan gambar yang valid")
    im = ImageOps.exif_transpose(im)  # hormati orientasi, lalu metadata dibuang saat simpan ulang
    if im.mode not in ("RGB", "L"):
        im = im.convert("RGB")
    im.thumbnail((1600, 1600))
    out = io.BytesIO()
    im.save(out, format="JPEG", quality=82, optimize=True)
    return out.getvalue()


def public_story(s: Optional[Dict[str, Any]]) -> Optional[Dict[str, Any]]:
    if not s or s.get("status") != "dipublikasikan":
        return None
    return {"ringkasan_hasil": s.get("ringkasan_hasil"), "realisasi_penerima": s.get("realisasi_penerima"),
            "testimoni": s.get("testimoni") or [],
            "foto": [{"id": f["id"], "keterangan": f.get("keterangan", ""), "url": f"/api/public/cerita-foto/{f['id']}"}
                     for f in s.get("foto") or []],
            "dipublikasikan_at": s.get("reviewed_at")}


def build_router(db, current_user_dep, writer_dep, admin_dep) -> APIRouter:
    router = APIRouter(tags=["inklusi-cerita"])

    async def get_inq(iid: str, user: dict) -> Dict[str, Any]:
        d = await db.ngo_inquiries.find_one({"id": iid})
        if not d or (user.get("role") == "ngo" and d.get("user_email") != user.get("email")):
            raise HTTPException(status_code=404, detail="Inquiry tidak ditemukan")
        if user.get("role") not in STAFF_ROLES + ("ngo",):
            raise HTTPException(status_code=403, detail="Tidak berwenang")
        return d

    def owner_only(d: Dict[str, Any], user: dict):
        if d.get("user_email") != user.get("email"):
            raise HTTPException(status_code=403, detail="Hanya NGO pengaju yang dapat mengisi cerita dampak")
        if d.get("status") not in STATUS_BOLEH:
            raise HTTPException(status_code=409, detail="Cerita dampak dapat diisi saat program berstatus Monitoring atau Selesai")

    def out(s: Optional[Dict[str, Any]], iid: str) -> Dict[str, Any]:
        if not s:
            return {"ada": False}
        s = _clean(s)
        for f in s.get("foto") or []:
            f["url"] = f"/api/inquiries/{iid}/cerita/foto/{f['id']}"
        s["ada"] = True
        s["status_label"] = STATUS_CERITA.get(s.get("status"), s.get("status"))
        return s

    @router.get("/inquiries/{iid}/cerita")
    async def get_cerita(iid: str, user: dict = Depends(current_user_dep)):
        await get_inq(iid, user)
        return out(await db.program_stories.find_one({"inquiry_id": iid}), iid)

    @router.put("/inquiries/{iid}/cerita")
    async def save_cerita(iid: str, inp: CeritaInput, request: Request, user: dict = Depends(current_user_dep)):
        d = await get_inq(iid, user)
        owner_only(d, user)
        if not inp.persetujuan:
            raise HTTPException(status_code=422, detail="Centang persetujuan publikasi terlebih dahulu")
        s = await db.program_stories.find_one({"inquiry_id": iid})
        data = {**inp.model_dump(), "status": "menunggu_review", "catatan_admin": "", "updated_at": now_iso()}
        if s:
            await db.program_stories.update_one({"inquiry_id": iid}, {"$set": data})
        else:
            await db.program_stories.insert_one({"id": str(uuid.uuid4()), "inquiry_id": iid, "nomor": d.get("nomor"),
                                                 "foto": [], "user_email": user.get("email"), "created_at": now_iso(), **data})
        await audit(db, user, "simpan_cerita_dampak", "program_stories", iid, {"nomor": d.get("nomor")}, request)
        return out(await db.program_stories.find_one({"inquiry_id": iid}), iid)

    @router.post("/inquiries/{iid}/cerita/foto")
    async def upload_foto(iid: str, request: Request, file: UploadFile = File(...), keterangan: str = Form(""),
                          user: dict = Depends(current_user_dep)):
        d = await get_inq(iid, user)
        owner_only(d, user)
        s = await db.program_stories.find_one({"inquiry_id": iid})
        if not s:
            raise HTTPException(status_code=409, detail="Simpan isi cerita terlebih dahulu sebelum mengunggah foto")
        if len(s.get("foto") or []) >= MAX_FOTO:
            raise HTTPException(status_code=422, detail=f"Maksimal {MAX_FOTO} foto")
        if not (file.filename or "").lower().endswith((".jpg", ".jpeg", ".png", ".webp")):
            raise HTTPException(status_code=422, detail="Format foto: JPG, PNG, atau WEBP")
        raw = await file.read(MAX_FOTO_BYTES + 1)
        if len(raw) > MAX_FOTO_BYTES:
            raise HTTPException(status_code=413, detail="Ukuran foto maksimal 8 MB")
        img = _process_image(raw)
        fid = str(uuid.uuid4())
        for seq, start in enumerate(range(0, len(img), 1024 * 1024)):
            await db.story_files.insert_one({"id": f"{fid}-{seq:03d}", "file_id": fid, "inquiry_id": iid, "seq": seq,
                                             "data": base64.b64encode(img[start:start + 1024 * 1024]).decode()})
        meta = {"id": fid, "keterangan": re.sub(r"<[^>]*>", "", keterangan or "")[:200].strip(), "ukuran": len(img),
                "waktu": now_iso()}
        await db.program_stories.update_one({"inquiry_id": iid}, {"$set": {
            "foto": (s.get("foto") or []) + [meta], "status": "menunggu_review", "updated_at": now_iso()}})
        await audit(db, user, "unggah_foto_cerita", "program_stories", iid, {"foto": fid}, request)
        return out(await db.program_stories.find_one({"inquiry_id": iid}), iid)

    @router.delete("/inquiries/{iid}/cerita/foto/{fid}")
    async def delete_foto(iid: str, fid: str, request: Request, user: dict = Depends(current_user_dep)):
        d = await get_inq(iid, user)
        if d.get("user_email") != user.get("email") and user.get("role") not in SENSITIVE_ROLES:
            raise HTTPException(status_code=403, detail="Tidak berwenang")
        s = await db.program_stories.find_one({"inquiry_id": iid})
        if not s or not any(f["id"] == fid for f in s.get("foto") or []):
            raise HTTPException(status_code=404, detail="Foto tidak ditemukan")
        await db.story_files.delete_many({"file_id": fid})
        await db.program_stories.update_one({"inquiry_id": iid}, {"$set": {
            "foto": [f for f in s["foto"] if f["id"] != fid], "updated_at": now_iso()}})
        await audit(db, user, "hapus_foto_cerita", "program_stories", iid, {"foto": fid}, request)
        return out(await db.program_stories.find_one({"inquiry_id": iid}), iid)

    async def _foto_bytes(fid: str) -> bytes:
        parts = await db.story_files.find({"file_id": fid}).sort("seq", 1).to_list(50)
        if not parts:
            raise HTTPException(status_code=404, detail="Foto tidak ditemukan")
        return b"".join(base64.b64decode(p["data"]) for p in parts)

    @router.get("/inquiries/{iid}/cerita/foto/{fid}")
    async def foto_private(iid: str, fid: str, user: dict = Depends(current_user_dep)):
        await get_inq(iid, user)
        s = await db.program_stories.find_one({"inquiry_id": iid})
        if not s or not any(f["id"] == fid for f in s.get("foto") or []):
            raise HTTPException(status_code=404, detail="Foto tidak ditemukan")
        return Response(await _foto_bytes(fid), media_type="image/jpeg", headers={"Cache-Control": "private, max-age=300"})

    @router.get("/public/cerita-foto/{fid}")
    async def foto_public(fid: str):
        part = await db.story_files.find_one({"file_id": fid})
        if not part:
            raise HTTPException(status_code=404, detail="Foto tidak ditemukan")
        s = await db.program_stories.find_one({"inquiry_id": part.get("inquiry_id")})
        inq = await db.ngo_inquiries.find_one({"id": part.get("inquiry_id")})
        if (not s or s.get("status") != "dipublikasikan" or not inq or inq.get("status") != "COMPLETED"
                or not any(f["id"] == fid for f in s.get("foto") or [])):
            raise HTTPException(status_code=404, detail="Foto tidak ditemukan")
        return Response(await _foto_bytes(fid), media_type="image/jpeg", headers={"Cache-Control": "public, max-age=3600"})

    @router.patch("/inquiries/{iid}/cerita/review")
    async def review(iid: str, inp: ReviewInput, request: Request, user: dict = Depends(current_user_dep)):
        if user.get("role") not in SENSITIVE_ROLES:
            raise HTTPException(status_code=403, detail="Review cerita dampak khusus Admin/Super Admin")
        d = await get_inq(iid, user)
        s = await db.program_stories.find_one({"inquiry_id": iid})
        if not s:
            raise HTTPException(status_code=404, detail="Cerita dampak belum diisi")
        if inp.keputusan not in ("publikasikan", "tolak"):
            raise HTTPException(status_code=422, detail="Keputusan harus publikasikan atau tolak")
        if inp.keputusan == "tolak" and len(inp.catatan.strip()) < 5:
            raise HTTPException(status_code=422, detail="Catatan wajib diisi saat meminta perbaikan")
        st = "dipublikasikan" if inp.keputusan == "publikasikan" else "ditolak"
        await db.program_stories.update_one({"inquiry_id": iid}, {"$set": {
            "status": st, "catatan_admin": inp.catatan, "reviewed_by": user.get("email"), "reviewed_at": now_iso()}})
        await audit(db, user, "review_cerita_dampak", "program_stories", iid, {"keputusan": st, "catatan": inp.catatan}, request)
        # notifikasi email ke NGO
        label = "dipublikasikan di galeri publik" if st == "dipublikasikan" else "perlu diperbaiki"
        teks = (f"Yth. {d.get('nama_pic') or 'Bapak/Ibu'} ({d.get('nama_ngo')}),\n\nCerita dampak program "
                f"\"{d.get('program_usulan')}\" ({d.get('nomor')}) {label}.\n\nCatatan admin:\n{inp.catatan or '-'}\n\n"
                "Salam,\nTim PETA INKLUSI — Bappeda Kota Makassar")
        html_ = "<div style='font-family:Arial,sans-serif'>" + "".join(
            f"<p>{notifier.html.escape(p)}</p>" for p in teks.split("\n\n")).replace("\n", "<br>") + "</div>"
        try:
            await notifier.queue_email(db, [d.get("email"), d.get("user_email")],
                                       f"[PETA INKLUSI] Cerita dampak {d.get('nomor')} {label}", teks, html_,
                                       jenis="cerita_dampak", ref=iid)
        except Exception:  # noqa: BLE001
            pass
        return out(await db.program_stories.find_one({"inquiry_id": iid}), iid)

    @router.get("/inklusi/cerita")
    async def list_cerita(status: Optional[str] = None, user: dict = Depends(current_user_dep)):
        if user.get("role") not in STAFF_ROLES:
            raise HTTPException(status_code=403, detail="Tidak berwenang")
        f: Dict[str, Any] = {"status": status} if status else {}
        rows = await db.program_stories.find(f).sort("updated_at", -1).limit(100).to_list(100)
        items = []
        for r in rows:
            inq = await db.ngo_inquiries.find_one({"id": r.get("inquiry_id")}) or {}
            items.append({"inquiry_id": r.get("inquiry_id"), "nomor": r.get("nomor"), "status": r.get("status"),
                          "status_label": STATUS_CERITA.get(r.get("status")), "program": inq.get("program_usulan"),
                          "nama_ngo": inq.get("nama_ngo"), "jumlah_foto": len(r.get("foto") or []),
                          "updated_at": r.get("updated_at")})
        return {"items": items, "menunggu": await db.program_stories.count_documents({"status": "menunggu_review"})}

    return router
