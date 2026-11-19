"""Modul pengelolaan data terintegrasi SIDATA (input manual / ubah / hapus).

Melengkapi `import_wizard.py` (impor Excel/CSV) dengan jalur INPUT MANUAL dan
pemeliharaan data:

* Master kode referensi DTSEN (arti kode diisi administrator, tidak ditebak sistem).
* Master wilayah berantai: provinsi -> kabupaten/kota -> kecamatan -> kelurahan.
* Metadata field per dataset (dipakai frontend untuk membangun form otomatis).
* CRUD DTSEN keluarga (`households`) dengan pemeriksaan duplikat + UPSERT aman.
* CRUD rekap disabilitas (`disability_region_stats`).
* CRUD matriks RAD disabilitas (`rad_items`).
* Titik koordinat kelurahan (`gis_locations`) — centroid resmi atau input manual.
* Audit log lengkap (data sebelum & sesudah) untuk setiap aksi tulis.
* Penyegaran agregat (village_stats / district_stats) secara inkremental agar
  dashboard, tabel, grafik, dan peta langsung mengikuti perubahan data.

Semua endpoint di-mount pada prefix /api oleh server.py.
"""
from __future__ import annotations

import csv
import io
import json
import math
import uuid
from datetime import datetime, timezone
from typing import Any, Dict, List, Optional

from fastapi import APIRouter, Depends, HTTPException, Query, Request
from fastapi.responses import StreamingResponse
from openpyxl import Workbook
from openpyxl.styles import Alignment, Font, PatternFill
from pydantic import BaseModel, Field

import etl_import as etl
import import_wizard as iw
import scoring
import sosial

now_iso = lambda: datetime.now(timezone.utc).isoformat()  # noqa: E731

# Peran yang boleh menulis data & yang boleh menghapus data
WRITE_ROLES = ("superadmin", "admin", "admin_bappeda", "verifikator", "admin_opd",
               "petugas", "operator", "operator_kecamatan", "operator_kelurahan")
DELETE_ROLES = ("superadmin", "admin", "admin_bappeda", "verifikator")
# Peran dengan batasan wilayah (hanya boleh menulis pada wilayahnya sendiri)
KECAMATAN_SCOPED = ("operator", "operator_kecamatan")
KELURAHAN_SCOPED = ("operator_kelurahan",)


def _clean(doc: Optional[Dict[str, Any]]) -> Dict[str, Any]:
    return {k: v for k, v in (doc or {}).items() if k != "_id"}


async def refresh_agregat_for(db, kode_kelurahan: str, kode_kecamatan: str = ""):
    """Hitung ulang village_stats kelurahan terkait + district_stats kecamatannya."""
    if not kode_kelurahan:
        return
    hs = await db.households.find({"kode_kelurahan": str(kode_kelurahan)}).to_list(100000)
    if not hs:
        await db.village_stats.delete_many({"kode_kelurahan": str(kode_kelurahan)})
    else:
        contoh = hs[0]
        kode_kec = str(contoh.get("kode_kecamatan") or kode_kecamatan or "")
        dis = await db.disability_region_stats.find(
            {"kelurahan_norm": iw.norm_name(contoh.get("kelurahan"))}).to_list(50)
        v: Dict[str, Any] = {
            "id": str(kode_kelurahan), "kode_kelurahan": str(kode_kelurahan),
            "kelurahan": contoh.get("kelurahan"), "kecamatan": contoh.get("kecamatan"),
            "kode_kecamatan": kode_kec,
            "total_households": 0, "total_individu": 0, "per_desil": {}, "per_risk": {},
            "pbi_nas": 0, "pbi_pemda": 0, "rumah_rentan": 0, "sanitasi_tidak_layak": 0,
            "air_rentan": 0, "hunian_rentan": 0, "listrik_rentan": 0,
            "perlu_validasi": 0, "updated_at": now_iso(),
        }
        sum_risk = 0.0
        for h in hs:
            v["total_households"] += 1
            v["total_individu"] += int(h.get("jumlah_anggota_keluarga") or 0)
            d = str(h.get("desil_nasional") or "-")
            v["per_desil"][d] = v["per_desil"].get(d, 0) + 1
            lvl = h.get("risk_level") or "rendah"
            v["per_risk"][lvl] = v["per_risk"].get(lvl, 0) + 1
            v["pbi_nas"] += 1 if int(h.get("pbi_nas") or 0) == 1 else 0
            v["pbi_pemda"] += 1 if int(h.get("pbi_pemda") or 0) == 1 else 0
            for key, flag in (("rumah_rentan", "rumah_rentan"),
                              ("sanitasi_tidak_layak", "sanitasi_rentan"),
                              ("air_rentan", "air_rentan"),
                              ("hunian_rentan", "hunian_rentan"),
                              ("listrik_rentan", "listrik_rentan")):
                v[key] += 1 if h.get(flag) else 0
            v["perlu_validasi"] += 1 if h.get("perlu_validasi") else 0
            sum_risk += float(h.get("risk_score") or 0)
        n = max(v["total_households"], 1)
        v["avg_risk"] = round(sum_risk / n, 2)
        v["desil_1_2"] = int(v["per_desil"].get("1", 0)) + int(v["per_desil"].get("2", 0))
        v["persen_desil_1_2"] = round(v["desil_1_2"] * 100.0 / n, 2)
        v["persen_rumah_rentan"] = round(v["rumah_rentan"] * 100.0 / n, 2)
        v["prioritas_tinggi"] = int(v["per_risk"].get("sangat_tinggi", 0)) + \
            int(v["per_risk"].get("tinggi", 0))
        v["disabilitas"] = sum(int(x.get("jumlah") or 0) for x in dis)
        v["skor_prioritas"] = round(min(100.0, (
            0.40 * v["avg_risk"] + 0.25 * v["persen_desil_1_2"]
            + 0.20 * v["persen_rumah_rentan"]
            + 0.15 * min(100.0, v["disabilitas"] / 5.0))), 2)
        geo = await db.geo_kelurahan.find_one(
            {"kelurahan_norm": iw.norm_name(v["kelurahan"])})
        v["punya_batas_wilayah"] = bool(geo)
        await db.village_stats.find_one_and_update(
            {"id": str(kode_kelurahan)}, {"$set": v}, upsert=True)
        kode_kecamatan = kode_kec or kode_kecamatan

    if not kode_kecamatan:
        return
    vs = await db.village_stats.find({"kode_kecamatan": str(kode_kecamatan)}).to_list(1000)
    if not vs:
        await db.district_stats.delete_many({"kode_kecamatan": str(kode_kecamatan)})
        return
    d: Dict[str, Any] = {
        "id": str(kode_kecamatan), "kode_kecamatan": str(kode_kecamatan),
        "kecamatan": vs[0].get("kecamatan"), "total_households": 0, "total_individu": 0,
        "per_desil": {}, "per_risk": {}, "pbi_nas": 0, "pbi_pemda": 0, "rumah_rentan": 0,
        "sanitasi_tidak_layak": 0, "air_rentan": 0, "hunian_rentan": 0, "disabilitas": 0,
        "jumlah_kelurahan": len(vs), "updated_at": now_iso(),
    }
    sum_risk = 0.0
    for v in vs:
        for key in ("total_households", "total_individu", "pbi_nas", "pbi_pemda",
                    "rumah_rentan", "sanitasi_tidak_layak", "air_rentan",
                    "hunian_rentan", "disabilitas"):
            d[key] += int(v.get(key) or 0)
        for dk, dv in (v.get("per_desil") or {}).items():
            d["per_desil"][dk] = d["per_desil"].get(dk, 0) + dv
        for rk, rv in (v.get("per_risk") or {}).items():
            d["per_risk"][rk] = d["per_risk"].get(rk, 0) + rv
        sum_risk += float(v.get("avg_risk") or 0) * int(v.get("total_households") or 0)
    n = max(d["total_households"], 1)
    d["avg_risk"] = round(sum_risk / n, 2)
    d["desil_1_2"] = int(d["per_desil"].get("1", 0)) + int(d["per_desil"].get("2", 0))
    d["persen_desil_1_2"] = round(d["desil_1_2"] * 100.0 / n, 2)
    d["persen_rumah_rentan"] = round(d["rumah_rentan"] * 100.0 / n, 2)
    await db.district_stats.find_one_and_update(
        {"id": str(kode_kecamatan)}, {"$set": d}, upsert=True)


class KodeIn(BaseModel):
    field: str
    kode: str
    label: str = ""
    keterangan: str = ""


class KodeUpdate(BaseModel):
    label: Optional[str] = None
    keterangan: Optional[str] = None


class RecordIn(BaseModel):
    """Satu baris data dengan nama kolom mengikuti template Excel."""
    data: Dict[str, Any] = Field(default_factory=dict)
    mode_duplikat: str = "tolak"  # tolak | skip | update | update_perubahan
    catatan: str = ""


class KoordinatIn(BaseModel):
    latitude: float = Field(..., ge=-90, le=90)
    longitude: float = Field(..., ge=-180, le=180)
    keterangan: str = ""


def build_router(db, current_user_dep, editor_dep, admin_dep) -> APIRouter:  # noqa: C901
    router = APIRouter(tags=["pengelolaan-data"])

    # ------------------------------------------------------------------ helper
    async def writer(request: Request) -> dict:
        user = await current_user_dep(request)
        if (user.get("role") or "") not in WRITE_ROLES:
            raise HTTPException(status_code=403,
                                detail="Peran Anda tidak berwenang menambah atau mengubah data")
        return user

    async def remover(request: Request) -> dict:
        user = await current_user_dep(request)
        if (user.get("role") or "") not in DELETE_ROLES:
            raise HTTPException(
                status_code=403,
                detail="Penghapusan data hanya dapat dilakukan Super Admin / Admin Bappeda")
        return user

    def cek_wilayah(user: dict, kecamatan: str, kelurahan: str = ""):
        """Operator kecamatan/kelurahan hanya boleh menyentuh wilayahnya."""
        role = user.get("role") or ""
        wil = iw.norm_name(user.get("wilayah"))
        if role in KECAMATAN_SCOPED and wil and iw.norm_name(kecamatan) != wil:
            raise HTTPException(
                status_code=403,
                detail=f"Anda hanya berwenang atas Kecamatan {user.get('wilayah')}")
        if role in KELURAHAN_SCOPED:
            if wil and iw.norm_name(kecamatan) != wil:
                raise HTTPException(
                    status_code=403,
                    detail=f"Anda hanya berwenang atas Kecamatan {user.get('wilayah')}")
            kel_user = iw.norm_name(user.get("kelurahan") or user.get("wilayah"))
            if kel_user and kel_user != iw.norm_name(kelurahan):
                raise HTTPException(
                    status_code=403,
                    detail=f"Anda hanya berwenang atas Kelurahan {user.get('kelurahan') or user.get('wilayah')}")

    async def audit(user: dict, action: str, entitas: str, ref: str,
                    sebelum: Any = None, sesudah: Any = None, modul: str = "",
                    catatan: str = ""):
        await db.audit_logs.insert_one({
            "id": str(uuid.uuid4()),
            "user": user.get("email") or "-",
            "user_nama": user.get("name") or "",
            "role": user.get("role") or "",
            "action": action,
            "modul": modul or entitas,
            "entitas": entitas,
            "ref": ref or "",
            "detail": catatan[:500],
            "data_sebelum": json.dumps(_clean(sebelum), default=str)[:4000] if sebelum else "",
            "data_sesudah": json.dumps(_clean(sesudah), default=str)[:4000] if sesudah else "",
            "created_at": now_iso(),
        })

    async def kel_index() -> Dict[str, Dict[str, Any]]:
        docs = await db.geo_kelurahan.find({}).to_list(500)
        return {d.get("kelurahan_norm"): d for d in docs}

    async def scoring_cfg() -> Dict[str, Any]:
        cfg = await db.scoring_config.find_one({"id": "default"})
        return _clean(cfg) or scoring.default_config()

    async def refresh_agregat(kode_kelurahan: str, kode_kecamatan: str = ""):
        await refresh_agregat_for(db, kode_kelurahan, kode_kecamatan)

    async def sinkron_kode_baru(doc: Dict[str, Any]):
        """Pastikan kode baru dari input manual ikut terdaftar pada master kode."""
        for f in etl.CODED_FIELDS:
            v = doc.get(f)
            kode = "(kosong)" if v is None or str(v).strip() == "" else str(v).strip()
            _id = f"{f}::{kode}"
            ada = await db.kode_referensi.find_one({"id": _id})
            if ada:
                await db.kode_referensi.update_one(
                    {"id": _id}, {"$inc": {"jumlah_data": 1}})
            else:
                await db.kode_referensi.insert_one({
                    "id": _id, "field": f, "field_label": etl.CODED_FIELDS[f],
                    "kode": kode, "label": "", "keterangan": "", "jumlah_data": 1,
                    "sumber": "input_manual", "updated_at": now_iso(), "updated_by": ""})

    # =================================================== 1. MASTER KODE REFERENSI
    @router.get("/master/kode")
    async def list_kode(field: Optional[str] = None, hanya_kosong: bool = False):
        q: Dict[str, Any] = {}
        if field:
            q["field"] = field
        docs = [_clean(d) for d in await db.kode_referensi.find(q).to_list(5000)]
        if hanya_kosong:
            docs = [d for d in docs if not d.get("label")]

        def _urut(d):
            k = str(d.get("kode") or "")
            return (d.get("field") or "", 0 if k.isdigit() else 1,
                    int(k) if k.isdigit() else 0, k)

        docs.sort(key=_urut)
        fields = [{"name": k, "label": v,
                   "jumlah_kode": len([d for d in docs if d.get("field") == k])}
                  for k, v in etl.CODED_FIELDS.items()]
        return {"total": len(docs), "items": docs, "fields": fields,
                "belum_didefinisikan": len([d for d in docs if not d.get("label")])}

    @router.get("/master/kode/map")
    async def map_kode():
        """Peta {field: {kode: label}} untuk pelabelan di dashboard & tabel."""
        docs = await db.kode_referensi.find({}).to_list(5000)
        out: Dict[str, Dict[str, str]] = {}
        for d in docs:
            if d.get("label"):
                out.setdefault(d.get("field"), {})[str(d.get("kode"))] = d.get("label")
        return {"labels": out, "fields": etl.CODED_FIELDS}

    @router.post("/master/kode")
    async def create_kode(payload: KodeIn, user: dict = Depends(admin_dep)):
        if payload.field not in etl.CODED_FIELDS:
            raise HTTPException(status_code=400, detail="Field kode tidak dikenal")
        _id = f"{payload.field}::{payload.kode}"
        if await db.kode_referensi.find_one({"id": _id}):
            raise HTTPException(status_code=409, detail="Kode tersebut sudah terdaftar")
        doc = {"id": _id, "field": payload.field,
               "field_label": etl.CODED_FIELDS[payload.field], "kode": payload.kode,
               "label": payload.label, "keterangan": payload.keterangan,
               "jumlah_data": 0, "sumber": "manual", "updated_at": now_iso(),
               "updated_by": user.get("email")}
        await db.kode_referensi.insert_one(doc)
        await audit(user, "kode_referensi_tambah", "kode_referensi", _id,
                    sesudah=doc, modul="master_kode")
        return _clean(doc)

    @router.put("/master/kode/{kode_id:path}")
    async def update_kode(kode_id: str, payload: KodeUpdate,
                          user: dict = Depends(admin_dep)):
        doc = await db.kode_referensi.find_one({"id": kode_id})
        if not doc:
            raise HTTPException(status_code=404, detail="Kode referensi tidak ditemukan")
        upd = {k: v for k, v in payload.model_dump().items() if v is not None}
        if not upd:
            raise HTTPException(status_code=400, detail="Tidak ada perubahan yang dikirim")
        upd["updated_at"] = now_iso()
        upd["updated_by"] = user.get("email")
        await db.kode_referensi.update_one({"id": kode_id}, {"$set": upd})
        fresh = await db.kode_referensi.find_one({"id": kode_id})
        await audit(user, "kode_referensi_ubah", "kode_referensi", kode_id,
                    sebelum=doc, sesudah=fresh, modul="master_kode")
        return _clean(fresh)

    @router.delete("/master/kode/{kode_id:path}")
    async def delete_kode(kode_id: str, user: dict = Depends(admin_dep)):
        doc = await db.kode_referensi.find_one({"id": kode_id})
        if not doc:
            raise HTTPException(status_code=404, detail="Kode referensi tidak ditemukan")
        if int(doc.get("jumlah_data") or 0) > 0:
            raise HTTPException(
                status_code=400,
                detail=f"Kode masih dipakai {doc.get('jumlah_data')} data — tidak dapat dihapus")
        await db.kode_referensi.delete_one({"id": kode_id})
        await audit(user, "kode_referensi_hapus", "kode_referensi", kode_id,
                    sebelum=doc, modul="master_kode")
        return {"status": "deleted", "id": kode_id}

    # =================================================== 2. MASTER WILAYAH BERANTAI
    @router.get("/master/wilayah/provinsi")
    async def wilayah_provinsi():
        docs = await db.provinces.find({}).to_list(100)
        return {"items": sorted([{"kode": d.get("kode"), "nama": d.get("nama")}
                                 for d in docs], key=lambda x: x["nama"] or "")}

    @router.get("/master/wilayah/kabupaten")
    async def wilayah_kabupaten(kode_provinsi: Optional[str] = None):
        q = {"kode_provinsi": kode_provinsi} if kode_provinsi else {}
        docs = await db.cities.find(q).to_list(200)
        return {"items": sorted([{"kode": d.get("kode"), "nama": d.get("nama"),
                                  "kode_provinsi": d.get("kode_provinsi")} for d in docs],
                                key=lambda x: x["nama"] or "")}

    @router.get("/master/wilayah/kecamatan")
    async def wilayah_kecamatan(kode_kabupaten_kota: Optional[str] = None):
        q = {"kode_kabupaten_kota": kode_kabupaten_kota} if kode_kabupaten_kota else {}
        docs = await db.districts.find(q).to_list(200)
        return {"items": sorted([{"kode": d.get("kode"), "nama": d.get("nama"),
                                  "kode_kabupaten_kota": d.get("kode_kabupaten_kota")}
                                 for d in docs], key=lambda x: x["nama"] or "")}

    @router.get("/master/wilayah/kelurahan")
    async def wilayah_kelurahan_master(kode_kecamatan: Optional[str] = None):
        q = {"kode_kecamatan": kode_kecamatan} if kode_kecamatan else {}
        docs = await db.villages.find(q).to_list(1000)
        return {"items": sorted([{"kode": d.get("kode"), "nama": d.get("nama"),
                                  "kecamatan": d.get("kecamatan"),
                                  "kode_kecamatan": d.get("kode_kecamatan")}
                                 for d in docs], key=lambda x: x["nama"] or "")}

    # =================================================== 3. METADATA FORM
    @router.get("/master/fields/{jenis}")
    async def field_metadata(jenis: str):
        if jenis not in iw.DATASETS:
            raise HTTPException(status_code=404, detail="Jenis dataset tidak dikenal")
        kode_docs = await db.kode_referensi.find({}).to_list(5000)
        opsi: Dict[str, List[Dict[str, Any]]] = {}
        for d in kode_docs:
            if str(d.get("kode")) == "(kosong)":
                continue
            opsi.setdefault(d.get("field"), []).append({
                "kode": d.get("kode"),
                "label": d.get("label") or f"Kode {d.get('kode')} (belum didefinisikan)",
                "jumlah_data": d.get("jumlah_data") or 0})
        for k in opsi:
            opsi[k].sort(key=lambda x: (int(x["kode"]) if str(x["kode"]).isdigit() else 999))
        sections: List[Dict[str, Any]] = []
        for f in iw.DATASETS[jenis]["fields"]:
            sec = next((s for s in sections if s["section"] == f["section"]), None)
            if sec is None:
                sec = {"section": f["section"], "fields": []}
                sections.append(sec)
            sec["fields"].append({**{k: v for k, v in f.items() if k != "synonyms"},
                                  "opsi": opsi.get(f["name"], [])})
        return {"jenis": jenis, "label": iw.DATASETS[jenis]["label"],
                "kunci_duplikat": iw.DATASETS[jenis]["kunci"], "sections": sections}

    # =================================================== 4. CRUD DTSEN KELUARGA
    async def _dtsen_doc(data: Dict[str, Any]):
        row = iw.normalize_row("dtsen", data)
        errors, warnings = iw.validate_row("dtsen", row, data, await kel_index())
        if errors:
            raise HTTPException(status_code=422, detail={
                "message": "Data tidak dapat disimpan karena masih ada kesalahan",
                "errors": errors, "warnings": warnings})
        doc = iw.to_document("dtsen", row, "", await scoring_cfg(),
                             {"file": "input-manual", "sheet": "manual"})
        return row, doc, warnings

    @router.post("/sosial/households")
    async def create_household(payload: RecordIn, user: dict = Depends(writer)):
        row, doc, warnings = await _dtsen_doc(payload.data)
        cek_wilayah(user, doc.get("kecamatan"), doc.get("kelurahan"))
        kunci = iw.DB_FILTER["dtsen"](row)
        lama = await db.households.find_one(kunci) if kunci.get("no_kk") else None
        if lama:
            mode = (payload.mode_duplikat or "tolak").lower()
            if mode == "tolak":
                raise HTTPException(status_code=409, detail={
                    "message": "Data sudah tersedia",
                    "kunci": f"{doc.get('no_kk_mask')} | {doc.get('kelurahan')}",
                    "id": lama.get("id"),
                    "pilihan": ["skip", "update", "update_perubahan"],
                })
            if mode == "skip":
                return {"status": "skipped", "id": lama.get("id"),
                        "message": "Data sudah ada, penyimpanan dilewati"}
            upd = dict(doc)
            if mode == "update_perubahan":
                upd = {k: v for k, v in doc.items()
                       if v not in (None, "", 0) and lama.get(k) != v}
            upd.update({"updated_at": now_iso(), "updated_by": user.get("email"),
                        "sumber_input": "manual"})
            upd.pop("id", None)
            await db.households.update_one({"id": lama.get("id")}, {"$set": upd})
            fresh = await db.households.find_one({"id": lama.get("id")})
            await refresh_agregat(fresh.get("kode_kelurahan"), fresh.get("kode_kecamatan"))
            await audit(user, "dtsen_upsert", "households", lama.get("id"),
                        sebelum=lama, sesudah=fresh, modul="dtsen",
                        catatan=f"mode={mode}. {payload.catatan}")
            return {"status": "updated", "id": lama.get("id"), "warnings": warnings,
                    "item": _clean(fresh)}

        doc.update({"id": str(uuid.uuid4()), "sumber_input": "manual",
                    "created_at": now_iso(), "created_by": user.get("email"),
                    "import_batch": "manual"})
        await db.households.insert_one(doc)
        if doc.get("kepala_keluarga"):
            await db.household_members.insert_one({
                "id": str(uuid.uuid4()), "household_id": doc["id"], "no_kk": doc["no_kk"],
                "nama": doc["kepala_keluarga"], "peran": "Kepala Keluarga",
                "kode_kelurahan": doc.get("kode_kelurahan"), "import_batch": "manual",
                "created_at": now_iso()})
        await sinkron_kode_baru(doc)
        await refresh_agregat(doc.get("kode_kelurahan"), doc.get("kode_kecamatan"))
        await audit(user, "dtsen_tambah", "households", doc["id"], sesudah=doc,
                    modul="dtsen", catatan=payload.catatan)
        return {"status": "created", "id": doc["id"], "warnings": warnings,
                "item": _clean(doc)}

    @router.put("/sosial/households/{household_id}")
    async def update_household(household_id: str, payload: RecordIn,
                               user: dict = Depends(writer)):
        lama = await db.households.find_one({"id": household_id})
        if not lama:
            raise HTTPException(status_code=404, detail="Rumah tangga tidak ditemukan")
        cek_wilayah(user, lama.get("kecamatan"), lama.get("kelurahan"))
        gabung = {**_household_to_row(lama), **{k: v for k, v in payload.data.items()
                                                if v is not None}}
        row, doc, warnings = await _dtsen_doc(gabung)
        cek_wilayah(user, doc.get("kecamatan"), doc.get("kelurahan"))
        kunci = iw.DB_FILTER["dtsen"](row)
        bentrok = await db.households.find_one({**kunci, "id": {"$ne": household_id}})
        if bentrok:
            raise HTTPException(status_code=409, detail={
                "message": "Nomor KK & kelurahan tersebut sudah dipakai data lain",
                "id": bentrok.get("id")})
        doc.update({"updated_at": now_iso(), "updated_by": user.get("email"),
                    "sumber_input": lama.get("sumber_input") or "impor"})
        doc.pop("id", None)
        doc["import_batch"] = lama.get("import_batch") or "manual"
        await db.households.update_one({"id": household_id}, {"$set": doc})
        fresh = await db.households.find_one({"id": household_id})
        if fresh.get("kepala_keluarga") != lama.get("kepala_keluarga"):
            await db.household_members.update_many(
                {"household_id": household_id},
                {"$set": {"nama": fresh.get("kepala_keluarga")}})
        await sinkron_kode_baru(fresh)
        await refresh_agregat(fresh.get("kode_kelurahan"), fresh.get("kode_kecamatan"))
        if lama.get("kode_kelurahan") != fresh.get("kode_kelurahan"):
            await refresh_agregat(lama.get("kode_kelurahan"), lama.get("kode_kecamatan"))
        await audit(user, "dtsen_ubah", "households", household_id, sebelum=lama,
                    sesudah=fresh, modul="dtsen", catatan=payload.catatan)
        return {"status": "updated", "id": household_id, "warnings": warnings,
                "item": _clean(fresh)}

    @router.delete("/sosial/households/{household_id}")
    async def delete_household(household_id: str, alasan: str = Query("", max_length=300),
                               user: dict = Depends(remover)):
        lama = await db.households.find_one({"id": household_id})
        if not lama:
            raise HTTPException(status_code=404, detail="Rumah tangga tidak ditemukan")
        await db.households.delete_one({"id": household_id})
        await db.household_members.delete_many({"household_id": household_id})
        await refresh_agregat(lama.get("kode_kelurahan"), lama.get("kode_kecamatan"))
        await audit(user, "dtsen_hapus", "households", household_id, sebelum=lama,
                    modul="dtsen", catatan=alasan)
        return {"status": "deleted", "id": household_id}

    def _household_to_row(doc: Dict[str, Any]) -> Dict[str, Any]:
        """Ubah dokumen DB kembali ke bentuk kolom Excel (untuk form ubah)."""
        row = {
            "nomor_kartu_keluarga": doc.get("no_kk"),
            "kode_provinsi": doc.get("kode_provinsi"),
            "provinsi": doc.get("provinsi"),
            "kode_kabupaten_kota": doc.get("kode_kabupaten_kota"),
            "kabupaten_kota": doc.get("kabupaten_kota"),
            "kode_kecamatan": doc.get("kode_kecamatan"),
            "kecamatan": doc.get("kecamatan"),
            "kode_kelurahan_desa": doc.get("kode_kelurahan"),
            "kelurahan_desa": doc.get("kelurahan"),
            "alamat": doc.get("alamat"),
            "jumlah_anggota_keluarga": doc.get("jumlah_anggota_keluarga"),
            "nama_anggota_keluarga": doc.get("kepala_keluarga"),
            "desil_nasional": doc.get("desil_nasional"),
            "pbi_nas": doc.get("pbi_nas"),
            "pbi_pemda": doc.get("pbi_pemda"),
        }
        for f in etl.HOUSING_FIELDS:
            row[f] = doc.get(f)
        return row

    @router.get("/sosial/households/{household_id}/form")
    async def household_form(household_id: str, user: dict = Depends(writer)):
        doc = await db.households.find_one({"id": household_id})
        if not doc:
            raise HTTPException(status_code=404, detail="Rumah tangga tidak ditemukan")
        return {"id": household_id, "data": _household_to_row(doc)}

    # =================================================== 5. CRUD DISABILITAS
    @router.get("/disabilitas/items")
    async def list_disabilitas(kecamatan: Optional[str] = None,
                               kelurahan: Optional[str] = None,
                               tahun: Optional[int] = None,
                               search: Optional[str] = None,
                               page: int = Query(1, ge=1),
                               size: int = Query(50, ge=1, le=500)):
        q: Dict[str, Any] = {}
        if kecamatan:
            q["kecamatan_norm"] = iw.norm_name(kecamatan)
        if kelurahan:
            q["kelurahan_norm"] = iw.norm_name(kelurahan)
        if tahun:
            q["tahun"] = str(tahun)
        docs = [_clean(d) for d in await db.disability_region_stats.find(q).to_list(5000)]
        if search:
            s = iw.norm_name(search)
            docs = [d for d in docs if s in iw.norm_name(d.get("kelurahan"))
                    or s in iw.norm_name(d.get("kecamatan"))]
        docs.sort(key=lambda d: (-int(d.get("jumlah") or 0), d.get("kelurahan") or ""))
        total = len(docs)
        mulai = (page - 1) * size
        return {"total": total, "page": page, "size": size,
                "pages": max(1, math.ceil(total / size)),
                "items": docs[mulai:mulai + size]}

    @router.post("/disabilitas/items")
    async def create_disabilitas(payload: RecordIn, user: dict = Depends(writer)):
        row = iw.normalize_row("disabilitas", payload.data)
        errors, warnings = iw.validate_row("disabilitas", row, payload.data, {})
        if errors:
            raise HTTPException(status_code=422, detail={
                "message": "Data disabilitas tidak valid", "errors": errors,
                "warnings": warnings})
        doc = iw.to_document("disabilitas", row, "manual", {}, {"file": "input-manual"})
        cek_wilayah(user, doc.get("kecamatan"), doc.get("kelurahan"))
        kunci = iw.DB_FILTER["disabilitas"](row)
        lama = await db.disability_region_stats.find_one({**kunci, "tahun": str(doc.get("tahun"))})
        if lama and (payload.mode_duplikat or "tolak") == "tolak":
            raise HTTPException(status_code=409, detail={
                "message": "Data disabilitas wilayah & tahun tersebut sudah ada",
                "id": lama.get("id"), "pilihan": ["skip", "update"]})
        if lama:
            if (payload.mode_duplikat or "") == "skip":
                return {"status": "skipped", "id": lama.get("id")}
            doc.update({"updated_at": now_iso(), "updated_by": user.get("email")})
            await db.disability_region_stats.update_one({"id": lama.get("id")}, {"$set": doc})
            fresh = await db.disability_region_stats.find_one({"id": lama.get("id")})
            await refresh_agregat(await _kode_kel_by_name(fresh.get("kelurahan")))
            await audit(user, "disabilitas_ubah", "disability_region_stats",
                        lama.get("id"), sebelum=lama, sesudah=fresh, modul="disabilitas")
            return {"status": "updated", "id": lama.get("id"), "item": _clean(fresh)}
        doc.update({"id": str(uuid.uuid4()), "sumber_input": "manual",
                    "created_by": user.get("email")})
        doc["tahun"] = str(doc.get("tahun"))
        await db.disability_region_stats.insert_one(doc)
        await refresh_agregat(await _kode_kel_by_name(doc.get("kelurahan")))
        await audit(user, "disabilitas_tambah", "disability_region_stats", doc["id"],
                    sesudah=doc, modul="disabilitas", catatan=payload.catatan)
        return {"status": "created", "id": doc["id"], "warnings": warnings,
                "item": _clean(doc)}

    async def _kode_kel_by_name(nama: Any) -> str:
        v = await db.village_stats.find_one({"kelurahan": etl.title_name(nama)})
        return str((v or {}).get("kode_kelurahan") or "")

    @router.put("/disabilitas/items/{item_id}")
    async def update_disabilitas(item_id: str, payload: RecordIn,
                                 user: dict = Depends(writer)):
        lama = await db.disability_region_stats.find_one({"id": item_id})
        if not lama:
            raise HTTPException(status_code=404, detail="Data disabilitas tidak ditemukan")
        cek_wilayah(user, lama.get("kecamatan"), lama.get("kelurahan"))
        gabung = {**_clean(lama), **{k: v for k, v in payload.data.items() if v is not None}}
        row = iw.normalize_row("disabilitas", gabung)
        errors, warnings = iw.validate_row("disabilitas", row, gabung, {})
        if errors:
            raise HTTPException(status_code=422, detail={
                "message": "Data disabilitas tidak valid", "errors": errors})
        doc = iw.to_document("disabilitas", row, lama.get("import_batch") or "manual", {},
                             {"file": lama.get("sumber") or "input-manual"})
        doc.update({"updated_at": now_iso(), "updated_by": user.get("email"),
                    "tahun": str(doc.get("tahun"))})
        await db.disability_region_stats.update_one({"id": item_id}, {"$set": doc})
        fresh = await db.disability_region_stats.find_one({"id": item_id})
        await refresh_agregat(await _kode_kel_by_name(fresh.get("kelurahan")))
        await audit(user, "disabilitas_ubah", "disability_region_stats", item_id,
                    sebelum=lama, sesudah=fresh, modul="disabilitas",
                    catatan=payload.catatan)
        return {"status": "updated", "id": item_id, "warnings": warnings,
                "item": _clean(fresh)}

    @router.delete("/disabilitas/items/{item_id}")
    async def delete_disabilitas(item_id: str, alasan: str = Query("", max_length=300),
                                 user: dict = Depends(remover)):
        lama = await db.disability_region_stats.find_one({"id": item_id})
        if not lama:
            raise HTTPException(status_code=404, detail="Data disabilitas tidak ditemukan")
        await db.disability_region_stats.delete_one({"id": item_id})
        await refresh_agregat(await _kode_kel_by_name(lama.get("kelurahan")))
        await audit(user, "disabilitas_hapus", "disability_region_stats", item_id,
                    sebelum=lama, modul="disabilitas", catatan=alasan)
        return {"status": "deleted", "id": item_id}

    # =================================================== 6. CRUD MATRIKS RAD
    @router.post("/rad/items")
    async def create_rad(payload: RecordIn, user: dict = Depends(writer)):
        row = iw.normalize_row("rad", payload.data)
        errors, warnings = iw.validate_row("rad", row, payload.data, {})
        if errors:
            raise HTTPException(status_code=422, detail={
                "message": "Data RAD tidak valid", "errors": errors})
        doc = iw.to_document("rad", row, "manual", {}, {"file": "input-manual"})
        kunci = iw.DB_FILTER["rad"](row)
        lama = await db.rad_items.find_one(kunci)
        if lama and (payload.mode_duplikat or "tolak") == "tolak":
            raise HTTPException(status_code=409, detail={
                "message": "Item RAD dengan program/kegiatan/sub kegiatan sama sudah ada",
                "id": lama.get("id"), "pilihan": ["skip", "update"]})
        if lama and (payload.mode_duplikat or "") == "skip":
            return {"status": "skipped", "id": lama.get("id")}
        if lama:
            doc.update({"updated_at": now_iso(), "updated_by": user.get("email")})
            await db.rad_items.update_one({"id": lama.get("id")}, {"$set": doc})
            fresh = await db.rad_items.find_one({"id": lama.get("id")})
            await audit(user, "rad_ubah", "rad_items", lama.get("id"), sebelum=lama,
                        sesudah=fresh, modul="rad")
            return {"status": "updated", "id": lama.get("id"), "item": _clean(fresh)}
        doc.update({"id": str(uuid.uuid4()), "sumber_input": "manual",
                    "created_by": user.get("email")})
        await db.rad_items.insert_one(doc)
        await audit(user, "rad_tambah", "rad_items", doc["id"], sesudah=doc, modul="rad",
                    catatan=payload.catatan)
        return {"status": "created", "id": doc["id"], "warnings": warnings,
                "item": _clean(doc)}

    @router.put("/rad/items/{item_id}")
    async def update_rad(item_id: str, payload: RecordIn, user: dict = Depends(writer)):
        lama = await db.rad_items.find_one({"id": item_id})
        if not lama:
            raise HTTPException(status_code=404, detail="Item RAD tidak ditemukan")
        gabung = {**_rad_to_row(lama), **{k: v for k, v in payload.data.items()
                                          if v is not None}}
        row = iw.normalize_row("rad", gabung)
        errors, _w = iw.validate_row("rad", row, gabung, {})
        if errors:
            raise HTTPException(status_code=422, detail={
                "message": "Data RAD tidak valid", "errors": errors})
        doc = iw.to_document("rad", row, lama.get("import_batch") or "manual", {},
                             {"file": "input-manual"})
        doc.update({"updated_at": now_iso(), "updated_by": user.get("email"),
                    "sasaran_strategis": lama.get("sasaran_strategis") or "",
                    "kebijakan": lama.get("kebijakan") or ""})
        await db.rad_items.update_one({"id": item_id}, {"$set": doc})
        fresh = await db.rad_items.find_one({"id": item_id})
        await audit(user, "rad_ubah", "rad_items", item_id, sebelum=lama, sesudah=fresh,
                    modul="rad", catatan=payload.catatan)
        return {"status": "updated", "id": item_id, "item": _clean(fresh)}

    def _rad_to_row(doc: Dict[str, Any]) -> Dict[str, Any]:
        targets = doc.get("targets") or {}
        anggaran = doc.get("anggaran") or {}
        row = {
            "strategi_implementasi": doc.get("strategi_implementasi"),
            "target_capaian": doc.get("target_capaian"),
            "program": doc.get("program"), "kegiatan": doc.get("kegiatan"),
            "sub_kegiatan": doc.get("sub_kegiatan"),
            "indikator_capaian": doc.get("indikator_capaian"),
            "output_kegiatan": doc.get("output_kegiatan"),
            "indikator_capaian_terkait_disabilitas": doc.get("indikator_disabilitas"),
            "hambatan_tantangan": doc.get("hambatan"),
            "satuan_target_kegiatan": doc.get("satuan"),
            "lokasi": doc.get("lokasi"),
            "spesifik_tidak_spesifik": doc.get("spesifik"),
            "perangkat_daerah_penanggung_jawab": doc.get("opd"),
            "keterangan": doc.get("keterangan"),
        }
        for t in (2023, 2024, 2025, 2026):
            row[f"target_{t}"] = doc.get(f"target_{t}") if doc.get(f"target_{t}") is not None \
                else targets.get(str(t))
            row[f"anggaran_{t}"] = doc.get(f"anggaran_{t}") \
                if doc.get(f"anggaran_{t}") is not None else anggaran.get(str(t))
        return row

    @router.get("/rad/items/{item_id}/form")
    async def rad_form(item_id: str, user: dict = Depends(writer)):
        doc = await db.rad_items.find_one({"id": item_id})
        if not doc:
            raise HTTPException(status_code=404, detail="Item RAD tidak ditemukan")
        return {"id": item_id, "data": _rad_to_row(doc)}

    @router.delete("/rad/items/{item_id}")
    async def delete_rad(item_id: str, alasan: str = Query("", max_length=300),
                         user: dict = Depends(remover)):
        lama = await db.rad_items.find_one({"id": item_id})
        if not lama:
            raise HTTPException(status_code=404, detail="Item RAD tidak ditemukan")
        await db.rad_items.delete_one({"id": item_id})
        await db.rad_monitoring.delete_many({"item_id": item_id})
        await audit(user, "rad_hapus", "rad_items", item_id, sebelum=lama, modul="rad",
                    catatan=alasan)
        return {"status": "deleted", "id": item_id}

    # =================================================== 7. TITIK KOORDINAT GIS
    @router.get("/gis/locations")
    async def list_locations(kode_kecamatan: Optional[str] = None):
        locs = await db.gis_locations.find({}).to_list(1000)
        vstats = await db.village_stats.find({}).to_list(1000)
        by_norm = {iw.norm_name(v.get("kelurahan")): v for v in vstats}
        items = []
        for loc in locs:
            v = by_norm.get(loc.get("kelurahan_norm")) or {}
            if kode_kecamatan and str(v.get("kode_kecamatan")) != str(kode_kecamatan):
                continue
            per_desil = v.get("per_desil") or {}
            dominan = max(per_desil.items(), key=lambda x: x[1])[0] if per_desil else "-"
            items.append({
                **_clean(loc),
                "total_households": v.get("total_households", 0),
                "total_individu": v.get("total_individu", 0),
                "desil_dominan": dominan,
                "pbi_nas": v.get("pbi_nas", 0), "pbi_pemda": v.get("pbi_pemda", 0),
                "rumah_rentan": v.get("rumah_rentan", 0),
                "disabilitas": v.get("disabilitas", 0),
                "skor_prioritas": v.get("skor_prioritas"),
                "kode_kecamatan": v.get("kode_kecamatan"),
            })
        items.sort(key=lambda x: (x.get("kecamatan") or "", x.get("kelurahan") or ""))
        sudah = {loc.get("kelurahan_norm") for loc in locs}
        tanpa_koordinat = [v.get("kelurahan") for v in vstats
                           if iw.norm_name(v.get("kelurahan")) not in sudah]
        return {"total": len(items), "items": items,
                "tanpa_koordinat": sorted(tanpa_koordinat),
                "catatan": "Koordinat berasal dari titik pusat batas wilayah resmi "
                           "(BIG 2021) atau input manual operator."}

    @router.put("/gis/locations/{kelurahan}")
    async def set_location(kelurahan: str, payload: KoordinatIn,
                           user: dict = Depends(writer)):
        norm = iw.norm_name(kelurahan)
        lama = await db.gis_locations.find_one({"kelurahan_norm": norm})
        v = await db.village_stats.find_one({"kelurahan": etl.title_name(kelurahan)})
        if not lama and not v:
            raise HTTPException(status_code=404,
                                detail="Kelurahan tidak ditemukan pada data wilayah")
        doc = {
            "kelurahan": (lama or {}).get("kelurahan") or (v or {}).get("kelurahan"),
            "kelurahan_norm": norm,
            "kecamatan": (lama or {}).get("kecamatan") or (v or {}).get("kecamatan"),
            "kode_kelurahan": (lama or {}).get("kode_kelurahan")
            or (v or {}).get("kode_kelurahan"),
            "latitude": round(payload.latitude, 6),
            "longitude": round(payload.longitude, 6),
            "keterangan": payload.keterangan or "Koordinat diinput manual operator",
            "sumber": "manual",
            "updated_at": now_iso(), "updated_by": user.get("email"),
        }
        cek_wilayah(user, doc.get("kecamatan"), doc.get("kelurahan"))
        if lama:
            await db.gis_locations.update_one({"id": lama.get("id")}, {"$set": doc})
            ref = lama.get("id")
        else:
            doc["id"] = str(uuid.uuid4())
            await db.gis_locations.insert_one(doc)
            ref = doc["id"]
        fresh = await db.gis_locations.find_one({"id": ref})
        await audit(user, "koordinat_simpan", "gis_locations", ref, sebelum=lama,
                    sesudah=fresh, modul="gis")
        return {"status": "saved", "item": _clean(fresh)}

    @router.delete("/gis/locations/{kelurahan}")
    async def reset_location(kelurahan: str, user: dict = Depends(writer)):
        """Kembalikan titik ke centroid batas wilayah resmi."""
        norm = iw.norm_name(kelurahan)
        lama = await db.gis_locations.find_one({"kelurahan_norm": norm})
        if not lama:
            raise HTTPException(status_code=404, detail="Titik koordinat tidak ditemukan")
        geo = await db.geo_kelurahan.find_one({"kelurahan_norm": norm})
        titik = etl.centroid_of((geo or {}).get("geometry")) if geo else None
        if not titik:
            await db.gis_locations.delete_one({"id": lama.get("id")})
            await audit(user, "koordinat_hapus", "gis_locations", lama.get("id"),
                        sebelum=lama, modul="gis")
            return {"status": "deleted", "message": "Titik dihapus (batas wilayah tidak tersedia)"}
        upd = {"latitude": titik[0], "longitude": titik[1],
               "sumber": "centroid_batas_wilayah_big",
               "keterangan": "Titik pusat polygon batas kelurahan resmi (BIG 2021)",
               "updated_at": now_iso(), "updated_by": user.get("email")}
        await db.gis_locations.update_one({"id": lama.get("id")}, {"$set": upd})
        fresh = await db.gis_locations.find_one({"id": lama.get("id")})
        await audit(user, "koordinat_reset", "gis_locations", lama.get("id"),
                    sebelum=lama, sesudah=fresh, modul="gis")
        return {"status": "reset", "item": _clean(fresh)}

    # =================================================== 8. PEMELIHARAAN AGREGAT
    @router.post("/sosial/refresh-agregat")
    async def refresh_semua(user: dict = Depends(admin_dep)):
        villages = await db.village_stats.find({}).to_list(1000)
        kode_kel = [str(v.get("kode_kelurahan")) for v in villages]
        hh_kode = {str(h.get("kode_kelurahan")) for h in
                   await db.households.find({}).to_list(200000)}
        for k in sorted(set(kode_kel) | hh_kode):
            if k:
                await refresh_agregat(k)
        await audit(user, "agregat_refresh", "village_stats", "-", modul="administrasi",
                    catatan=f"{len(set(kode_kel) | hh_kode)} kelurahan dihitung ulang")
        return {"status": "ok", "kelurahan_diproses": len(set(kode_kel) | hh_kode)}

    # =================================================== 9. EXPORT (mengikuti filter)
    def _xlsx(judul: str, info: List[str], kolom: List[str],
              baris: List[List[Any]]) -> bytes:
        wb = Workbook()
        ws = wb.active
        ws.title = "DATA"
        ws.append([judul])
        ws["A1"].font = Font(bold=True, size=13, color="0F172A")
        for teks in info:
            ws.append([teks])
        ws.append([])
        awal = ws.max_row + 1
        ws.append([str(k) for k in kolom])
        for c in range(1, len(kolom) + 1):
            sel = ws.cell(row=awal, column=c)
            sel.font = Font(bold=True, color="FFFFFF", size=10)
            sel.fill = PatternFill("solid", fgColor="0F172A")
            sel.alignment = Alignment(horizontal="center", vertical="center", wrap_text=True)
        for r in baris:
            ws.append(r)
        for i, k in enumerate(kolom, start=1):
            lebar = max(12, min(42, len(str(k)) + 4))
            ws.column_dimensions[ws.cell(row=awal, column=i).column_letter].width = lebar
        ws.freeze_panes = ws.cell(row=awal + 1, column=1)
        buf = io.BytesIO()
        wb.save(buf)
        return buf.getvalue()

    def _csv(kolom: List[str], baris: List[List[Any]]) -> bytes:
        buf = io.StringIO()
        w = csv.writer(buf, delimiter=";")
        w.writerow(kolom)
        for r in baris:
            w.writerow(["" if v is None else v for v in r])
        return buf.getvalue().encode("utf-8-sig")

    def _unduh(nama: str, fmt: str, judul: str, info: List[str],
               kolom: List[str], baris: List[List[Any]]) -> StreamingResponse:
        stamp = datetime.now(timezone.utc).strftime("%Y%m%d_%H%M")
        if fmt == "csv":
            isi = _csv(kolom, baris)
            media = "text/csv"
            berkas = f"{nama}_{stamp}.csv"
        else:
            isi = _xlsx(judul, info, kolom, baris)
            media = "application/vnd.openxmlformats-officedocument.spreadsheetml.sheet"
            berkas = f"{nama}_{stamp}.xlsx"
        return StreamingResponse(
            io.BytesIO(isi), media_type=media,
            headers={"Content-Disposition": f'attachment; filename="{berkas}"'})

    async def _label_map() -> Dict[str, Dict[str, str]]:
        out: Dict[str, Dict[str, str]] = {}
        for d in await db.kode_referensi.find({}).to_list(5000):
            if d.get("label"):
                out.setdefault(d.get("field"), {})[str(d.get("kode"))] = d.get("label")
        return out

    @router.get("/export/dtsen")
    async def export_dtsen(
        request: Request, format: str = Query("xlsx", pattern="^(xlsx|csv)$"),
        kode_kecamatan: Optional[str] = None, kode_kelurahan: Optional[str] = None,
        desil: Optional[int] = None, risk_level: Optional[str] = None,
        pbi_nas: Optional[int] = None, pbi_pemda: Optional[int] = None,
        status_kepemilikan_rumah: Optional[str] = None,
        search: Optional[str] = None, limit: int = Query(50000, ge=1, le=200000),
    ):
        user = await current_user_dep(request)
        penuh = (user.get("role") or "") in sosial.SENSITIVE_ROLES
        q: Dict[str, Any] = {}
        if kode_kelurahan:
            q["kode_kelurahan"] = str(kode_kelurahan)
        elif kode_kecamatan:
            q["kode_kecamatan"] = str(kode_kecamatan)
        if desil is not None:
            q["desil_nasional"] = int(desil)
        if risk_level:
            q["risk_level"] = risk_level
        if pbi_nas is not None:
            q["pbi_nas"] = int(pbi_nas)
        if pbi_pemda is not None:
            q["pbi_pemda"] = int(pbi_pemda)
        if status_kepemilikan_rumah:
            q["status_kepemilikan_rumah"] = str(status_kepemilikan_rumah)
        if search:
            s = str(search).strip()
            if s.isdigit():
                q["no_kk"] = {"$regex": s}
            else:
                q["kepala_keluarga"] = {"$regex": s.upper()}
        docs = [d for d in await db.households.find(q).to_list(limit)
                if sosial.household_allowed(user, d)]
        labels = await _label_map()
        kode_fields = list(etl.CODED_FIELDS.keys())
        kolom = ["No", "Nomor KK", "Kepala Keluarga", "Alamat", "Provinsi",
                 "Kabupaten/Kota", "Kecamatan", "Kelurahan", "Kode Kelurahan",
                 "Jumlah ART", "Luas Lantai", "Skor Kerentanan", "Tingkat Prioritas"]
        for f in kode_fields:
            kolom.append(etl.CODED_FIELDS[f])
            kolom.append(f"{etl.CODED_FIELDS[f]} (arti)")
        baris = []
        for i, d in enumerate(docs, start=1):
            m = sosial.mask_household(d, penuh)
            r = [i, m.get("no_kk"), m.get("kepala_keluarga"), m.get("alamat"),
                 d.get("provinsi"), d.get("kabupaten_kota"), d.get("kecamatan"),
                 d.get("kelurahan"), d.get("kode_kelurahan"),
                 d.get("jumlah_anggota_keluarga"), d.get("luas_lantai"),
                 d.get("risk_score"), scoring.LEVEL_LABELS.get(d.get("risk_level"), "-")]
            for f in kode_fields:
                v = d.get(f)
                r.append(v)
                r.append(labels.get(f, {}).get(str(v), ""))
            baris.append(r)
        info = [
            "SIDATA — Sistem Informasi Data Terpadu Bappeda Kota Makassar",
            f"Diunduh: {datetime.now(timezone.utc).strftime('%d-%m-%Y %H:%M')} UTC oleh {user.get('email')}",
            f"Filter aktif: {json.dumps({k: v for k, v in q.items()}, default=str)}",
            f"Jumlah baris: {len(baris)}"
            + ("" if penuh else " · data pribadi disamarkan sesuai peran pengguna"),
        ]
        await audit(user, "export_dtsen", "households", "-", modul="export",
                    catatan=f"{len(baris)} baris, format {format}")
        return _unduh("DTSEN_Keluarga", format, "DATA DTSEN KELUARGA", info, kolom, baris)

    @router.get("/export/disabilitas")
    async def export_disabilitas(request: Request,
                                 format: str = Query("xlsx", pattern="^(xlsx|csv)$"),
                                 kecamatan: Optional[str] = None,
                                 kelurahan: Optional[str] = None,
                                 tahun: Optional[int] = None):
        user = await current_user_dep(request)
        q: Dict[str, Any] = {}
        if kecamatan:
            q["kecamatan_norm"] = iw.norm_name(kecamatan)
        if kelurahan:
            q["kelurahan_norm"] = iw.norm_name(kelurahan)
        if tahun:
            q["tahun"] = str(tahun)
        docs = await db.disability_region_stats.find(q).to_list(5000)
        kolom = ["No", "Kecamatan", "Kelurahan", "Tahun", "Laki-laki", "Perempuan",
                 "Usia <18", "Usia 18-59", "Usia 60+", "Fisik", "Ganda", "Intelektual",
                 "Mental", "Sensorik Pendengaran", "Sensorik Penglihatan", "Total", "Sumber"]
        baris = [[i, d.get("kecamatan"), d.get("kelurahan"), d.get("tahun"),
                  d.get("laki_laki"), d.get("perempuan"), d.get("usia_dibawah_18"),
                  d.get("usia_18_59"), d.get("usia_60_keatas"), d.get("fisik"),
                  d.get("ganda"), d.get("intelektual"), d.get("mental"),
                  d.get("sensorik_pendengaran"), d.get("sensorik_penglihatan"),
                  d.get("jumlah") or d.get("total"), d.get("sumber")]
                 for i, d in enumerate(docs, start=1)]
        await audit(user, "export_disabilitas", "disability_region_stats", "-",
                    modul="export", catatan=f"{len(baris)} baris")
        return _unduh("Data_Disabilitas", format, "DATA PENYANDANG DISABILITAS",
                      [f"Jumlah baris: {len(baris)}"], kolom, baris)

    @router.get("/export/rad")
    async def export_rad(request: Request,
                         format: str = Query("xlsx", pattern="^(xlsx|csv)$"),
                         search: Optional[str] = None):
        user = await current_user_dep(request)
        docs = await db.rad_items.find({}).to_list(5000)
        if search:
            s = iw.norm_name(search)
            docs = [d for d in docs if s in iw.norm_name(
                f"{d.get('program')} {d.get('kegiatan')} {d.get('sub_kegiatan')} "
                f"{d.get('indikator_capaian')}")]
        tahun = [2023, 2024, 2025, 2026, 2027, 2028, 2029, 2030]
        kolom = ["No", "Strategi Implementasi", "Target Capaian", "Program", "Kegiatan",
                 "Sub Kegiatan", "Indikator Capaian", "Output Kegiatan",
                 "Indikator Terkait Disabilitas", "Hambatan/Tantangan", "Satuan"]
        kolom += [f"Target {t}" for t in tahun] + [f"Anggaran {t}" for t in tahun]
        kolom += ["Lokasi", "Spesifik/Tidak", "Perangkat Daerah", "Keterangan"]
        baris = []
        for i, d in enumerate(docs, start=1):
            t = d.get("targets") or {}
            a = d.get("anggaran") or {}
            r = [i, d.get("strategi_implementasi"), d.get("target_capaian"),
                 d.get("program"), d.get("kegiatan"), d.get("sub_kegiatan"),
                 d.get("indikator_capaian"), d.get("output_kegiatan"),
                 d.get("indikator_disabilitas"), d.get("hambatan"), d.get("satuan")]
            r += [d.get(f"target_{y}") if d.get(f"target_{y}") is not None else t.get(str(y))
                  for y in tahun]
            r += [d.get(f"anggaran_{y}") if d.get(f"anggaran_{y}") is not None else a.get(str(y))
                  for y in tahun]
            r += [d.get("lokasi"), d.get("spesifik"), d.get("opd"), d.get("keterangan")]
            baris.append(r)
        await audit(user, "export_rad", "rad_items", "-", modul="export",
                    catatan=f"{len(baris)} baris")
        return _unduh("Matriks_RAD_Disabilitas", format, "MATRIKS RAD PENYANDANG DISABILITAS",
                      [f"Jumlah baris: {len(baris)}"], kolom, baris)

    @router.get("/export/kelurahan")
    async def export_kelurahan(request: Request,
                               format: str = Query("xlsx", pattern="^(xlsx|csv)$"),
                               kode_kecamatan: Optional[str] = None):
        user = await current_user_dep(request)
        q = {"kode_kecamatan": str(kode_kecamatan)} if kode_kecamatan else {}
        docs = await db.village_stats.find(q).to_list(1000)
        docs.sort(key=lambda d: -float(d.get("skor_prioritas") or 0))
        kolom = ["No", "Kecamatan", "Kelurahan", "Kode Kelurahan", "Jumlah Keluarga",
                 "Jumlah Jiwa", "Desil 1-2", "% Desil 1-2", "PBI Nasional", "PBI Pemda",
                 "Rumah Rentan", "Sanitasi Tidak Layak", "Air Rentan", "Hunian Rentan",
                 "Listrik Rentan", "Disabilitas", "Skor Kerentanan Rata-rata",
                 "Skor Prioritas"]
        baris = [[i, d.get("kecamatan"), d.get("kelurahan"), d.get("kode_kelurahan"),
                  d.get("total_households"), d.get("total_individu"), d.get("desil_1_2"),
                  d.get("persen_desil_1_2"), d.get("pbi_nas"), d.get("pbi_pemda"),
                  d.get("rumah_rentan"), d.get("sanitasi_tidak_layak"), d.get("air_rentan"),
                  d.get("hunian_rentan"), d.get("listrik_rentan"), d.get("disabilitas"),
                  d.get("avg_risk"), d.get("skor_prioritas")]
                 for i, d in enumerate(docs, start=1)]
        await audit(user, "export_kelurahan", "village_stats", "-", modul="export",
                    catatan=f"{len(baris)} baris")
        return _unduh("Rekap_Kelurahan", format, "REKAP DATA SOSIAL PER KELURAHAN",
                      [f"Jumlah kelurahan: {len(baris)}"], kolom, baris)

    return router
