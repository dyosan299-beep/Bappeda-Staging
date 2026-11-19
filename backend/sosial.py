"""API modul data sosial (DTSEN), analisis kerentanan, disabilitas, stunting,
RAD disabilitas, GIS choropleth, serta audit impor & kualitas data.

Semua endpoint di-mount pada prefix /api oleh server.py.
"""
from __future__ import annotations

import json
import math
import re
import unicodedata
import uuid
from datetime import datetime, timezone
from pathlib import Path
from typing import Any, Dict, List, Optional

from fastapi import APIRouter, Depends, HTTPException, Query, Request
from pydantic import BaseModel, Field

import scoring

ROOT = Path(__file__).parent
GEOJSON_PATH = ROOT / "assets" / "geo" / "kelurahan_makassar.geojson"

# Peran yang boleh melihat data pribadi lengkap (kota vs ter-scope wilayah)
CITY_SENSITIVE_ROLES = ("superadmin", "admin", "admin_bappeda")
SENSITIVE_ROLES = (
    "superadmin", "admin", "admin_bappeda", "verifikator",
    "operator", "operator_kecamatan", "operator_kelurahan",
    "petugas", "operator_rt_rw",
)
now_iso = lambda: datetime.now(timezone.utc).isoformat()  # noqa: E731

RISK_ORDER = ["sangat_tinggi", "tinggi", "sedang", "rendah"]


def norm_name(value: Any) -> str:
    s = str(value or "").strip().upper()
    s = unicodedata.normalize("NFKD", s).encode("ascii", "ignore").decode()
    s = re.sub(r"[^A-Z0-9' -]", " ", s)
    return re.sub(r"\s+", " ", s).strip()


def _clean(doc: Dict[str, Any]) -> Dict[str, Any]:
    return {k: v for k, v in (doc or {}).items() if k != "_id"}


def mask_household(doc: Dict[str, Any], allow: bool) -> Dict[str, Any]:
    d = _clean(doc)
    if allow:
        return d
    d["no_kk"] = d.get("no_kk_mask") or scoring.mask_kk(d.get("no_kk"))
    nama = str(d.get("kepala_keluarga") or "")
    parts = nama.split()
    d["kepala_keluarga"] = (parts[0] + " " + " ".join(p[0] + "***" for p in parts[1:])) if parts else "-"
    alamat = str(d.get("alamat") or "")
    d["alamat"] = (alamat[:12] + "…") if len(alamat) > 12 else alamat
    d["data_masked"] = True
    return d


class ScoringConfigUpdate(BaseModel):
    weights: Optional[Dict[str, float]] = None
    thresholds: Optional[Dict[str, float]] = None
    code_maps: Optional[Dict[str, Dict[str, List[int]]]] = None
    luas_per_kapita_min: Optional[float] = Field(None, gt=0)


class MonitoringUpdate(BaseModel):
    status: Optional[str] = None
    progress: Optional[int] = Field(None, ge=0, le=100)
    catatan: Optional[str] = None
    dokumen: Optional[str] = None
    penanggung_jawab: Optional[str] = None


# Pembatasan wilayah akses data rumah tangga per peran (ditegakkan di backend)
KECAMATAN_SCOPED = ("operator", "operator_kecamatan")
KELURAHAN_SCOPED = ("operator_kelurahan",)
CITY_READ_ROLES = ("pimpinan", "admin_opd", "viewer")  # baca seluruh kota, data tersamar
OPERATOR_RTRW = "operator_rt_rw"
OPERATOR_RTRW_ROLES = ("operator_rt_rw", "petugas")


def household_allowed(user: dict, doc: Dict[str, Any]) -> bool:
    """Cakupan wilayah untuk peran non-Operator RT/RW."""
    import scope as scope_mod
    role = (user or {}).get("role")
    if role == "verifikator":
        # verifikator kecamatan hanya kecamatannya; wilayah "Kota Makassar" = seluruh kota
        return scope_mod.same_kecamatan(scope_mod.kecamatan_scope(user), doc.get("kecamatan"))
    if role in CITY_SENSITIVE_ROLES or role in CITY_READ_ROLES:
        return True
    wil = norm_name((user or {}).get("wilayah"))
    if role in KECAMATAN_SCOPED:
        if not wil:
            return False
        return scope_mod.same_kecamatan(user.get("wilayah"), doc.get("kecamatan"))
    if role in KELURAHAN_SCOPED:
        kel_user = str((user or {}).get("kelurahan") or (user or {}).get("wilayah") or "").strip()
        if not kel_user:
            return False
        if wil and not scope_mod.same_kecamatan(user.get("wilayah"), doc.get("kecamatan")):
            return False
        kode_u = str((user or {}).get("kode_kelurahan") or "").strip()
        kode_d = str(doc.get("kode_kelurahan") or "").strip()
        if kode_u and kode_d:
            return kode_u == kode_d
        return scope_mod.same_kelurahan(kel_user, doc.get("kelurahan"))
    return False


def build_router(db, current_user_dep, editor_dep, admin_dep) -> APIRouter:
    router = APIRouter(tags=["sosial"])

    async def optional_user(request: Request) -> Optional[dict]:
        try:
            return await current_user_dep(request)
        except Exception:
            return None

    def sensitive_allowed(user: Optional[dict]) -> bool:
        return bool(user and user.get("role") in SENSITIVE_ROLES)

    # ---------------------------------------------------------- master wilayah
    @router.get("/wilayah/summary")
    async def wilayah_summary():
        districts = await db.district_stats.find({}).to_list(100)
        villages = await db.village_stats.find({}).to_list(1000)
        total_hh = sum(int(d.get("total_households") or 0) for d in districts)
        total_ind = sum(int(d.get("total_individu") or 0) for d in districts)
        return {
            "kota": "Kota Makassar",
            "jumlah_kecamatan": len(districts),
            "jumlah_kelurahan": len(villages),
            "total_households": total_hh,
            "total_individu": total_ind,
            "kecamatan": sorted(
                [{"kode": d.get("kode_kecamatan"), "nama": d.get("kecamatan"),
                  "jumlah_kelurahan": d.get("jumlah_kelurahan", 0),
                  "total_households": d.get("total_households", 0)} for d in districts],
                key=lambda x: x["nama"] or ""),
        }

    @router.get("/wilayah/kelurahan")
    async def wilayah_kelurahan(kode_kecamatan: Optional[str] = None):
        q = {"kode_kecamatan": kode_kecamatan} if kode_kecamatan else {}
        docs = await db.village_stats.find(q).to_list(1000)
        return {"items": sorted(
            [{"kode": d.get("kode_kelurahan"), "nama": d.get("kelurahan"),
              "kecamatan": d.get("kecamatan"), "kode_kecamatan": d.get("kode_kecamatan"),
              "total_households": d.get("total_households", 0)} for d in docs],
            key=lambda x: x["nama"] or "")}

    # ---------------------------------------------------------- helper agregasi
    def _hh_filter(kode_kecamatan, kode_kelurahan, desil, pbi_nas, pbi_pemda,
                   risk_level) -> Dict[str, Any]:
        q: Dict[str, Any] = {}
        if kode_kelurahan:
            q["kode_kelurahan"] = str(kode_kelurahan)
        elif kode_kecamatan:
            q["kode_kecamatan"] = str(kode_kecamatan)
        if desil:
            q["desil_nasional"] = int(desil)
        if pbi_nas is not None:
            q["pbi_nas"] = int(pbi_nas)
        if pbi_pemda is not None:
            q["pbi_pemda"] = int(pbi_pemda)
        if risk_level:
            q["risk_level"] = risk_level
        return q

    def _empty_kpi() -> Dict[str, Any]:
        return {
            "total_households": 0, "total_individu": 0, "pbi_nas": 0, "pbi_pemda": 0,
            "rumah_rentan": 0, "sanitasi_tidak_layak": 0, "air_rentan": 0,
            "hunian_rentan": 0, "listrik_rentan": 0, "perlu_validasi": 0,
            "per_desil": {}, "per_risk": {}, "avg_risk": 0.0,
        }

    def _accumulate(kpi: Dict[str, Any], doc: Dict[str, Any], from_stats: bool):
        if from_stats:
            for k in ("total_households", "total_individu", "pbi_nas", "pbi_pemda",
                      "rumah_rentan", "sanitasi_tidak_layak", "air_rentan",
                      "hunian_rentan", "listrik_rentan", "perlu_validasi"):
                kpi[k] += int(doc.get(k) or 0)
            for dk, dv in (doc.get("per_desil") or {}).items():
                kpi["per_desil"][str(dk)] = kpi["per_desil"].get(str(dk), 0) + int(dv)
            for rk, rv in (doc.get("per_risk") or {}).items():
                kpi["per_risk"][rk] = kpi["per_risk"].get(rk, 0) + int(rv)
            kpi["_risk_sum"] = kpi.get("_risk_sum", 0.0) + \
                float(doc.get("avg_risk") or 0) * int(doc.get("total_households") or 0)
        else:
            kpi["total_households"] += 1
            kpi["total_individu"] += int(doc.get("jumlah_anggota_keluarga") or 0)
            kpi["pbi_nas"] += 1 if int(doc.get("pbi_nas") or 0) == 1 else 0
            kpi["pbi_pemda"] += 1 if int(doc.get("pbi_pemda") or 0) == 1 else 0
            for k in ("rumah_rentan", "sanitasi_rentan", "air_rentan", "hunian_rentan",
                      "listrik_rentan", "perlu_validasi"):
                target = "sanitasi_tidak_layak" if k == "sanitasi_rentan" else k
                if doc.get(k):
                    kpi[target] += 1
            d = str(doc.get("desil_nasional") or "-")
            kpi["per_desil"][d] = kpi["per_desil"].get(d, 0) + 1
            lvl = doc.get("risk_level") or "rendah"
            kpi["per_risk"][lvl] = kpi["per_risk"].get(lvl, 0) + 1
            kpi["_risk_sum"] = kpi.get("_risk_sum", 0.0) + float(doc.get("risk_score") or 0)

    @router.get("/sosial/overview")
    async def sosial_overview(
        kode_kecamatan: Optional[str] = None, kode_kelurahan: Optional[str] = None,
        desil: Optional[int] = None, pbi_nas: Optional[int] = None,
        pbi_pemda: Optional[int] = None, risk_level: Optional[str] = None,
    ):
        pakai_agregat = desil is None and pbi_nas is None and pbi_pemda is None and not risk_level
        kpi = _empty_kpi()
        if pakai_agregat:
            q: Dict[str, Any] = {}
            if kode_kelurahan:
                q["id"] = str(kode_kelurahan)
            elif kode_kecamatan:
                q["kode_kecamatan"] = str(kode_kecamatan)
            docs = await db.village_stats.find(q).to_list(1000)
            for d in docs:
                _accumulate(kpi, d, True)
            kpi["jumlah_kelurahan"] = len(docs)
            kpi["jumlah_kecamatan"] = len({d.get("kode_kecamatan") for d in docs})
            kpi["sumber"] = "agregat"
        else:
            q = _hh_filter(kode_kecamatan, kode_kelurahan, desil, pbi_nas, pbi_pemda, risk_level)
            docs = await db.households.find(q).to_list(60000)
            kels = set()
            kecs = set()
            for d in docs:
                _accumulate(kpi, d, False)
                kels.add(d.get("kode_kelurahan"))
                kecs.add(d.get("kode_kecamatan"))
            kpi["jumlah_kelurahan"] = len(kels)
            kpi["jumlah_kecamatan"] = len(kecs)
            kpi["sumber"] = "detail"
        n = max(kpi["total_households"], 1)
        kpi["avg_risk"] = round(kpi.pop("_risk_sum", 0.0) / n, 2)
        kpi["desil_1_2"] = int(kpi["per_desil"].get("1", 0)) + int(kpi["per_desil"].get("2", 0))
        kpi["persen_desil_1_2"] = round(kpi["desil_1_2"] * 100.0 / n, 2)
        kpi["persen_rumah_rentan"] = round(kpi["rumah_rentan"] * 100.0 / n, 2)
        kpi["per_risk_urut"] = [{"level": lv, "label": scoring.LEVEL_LABELS[lv],
                                 "jumlah": kpi["per_risk"].get(lv, 0)} for lv in RISK_ORDER]
        return kpi

    @router.get("/sosial/ranking")
    async def sosial_ranking(level: str = "kelurahan", metric: str = "skor_prioritas",
                             kode_kecamatan: Optional[str] = None,
                             limit: int = Query(15, ge=1, le=200)):
        coll = db.village_stats if level == "kelurahan" else db.district_stats
        q = {"kode_kecamatan": str(kode_kecamatan)} if (level == "kelurahan" and kode_kecamatan) else {}
        docs = await coll.find(q).to_list(1000)
        key = metric if metric in (docs[0] if docs else {}) else "total_households"
        docs.sort(key=lambda d: float(d.get(key) or 0), reverse=True)
        items = []
        for d in docs[:limit]:
            items.append({
                "kode": d.get("kode_kelurahan") or d.get("kode_kecamatan"),
                "nama": d.get("kelurahan") or d.get("kecamatan"),
                "kecamatan": d.get("kecamatan"),
                "nilai": d.get(key),
                "total_households": d.get("total_households", 0),
                "total_individu": d.get("total_individu", 0),
                "avg_risk": d.get("avg_risk", 0),
                "desil_1_2": d.get("desil_1_2", 0),
                "rumah_rentan": d.get("rumah_rentan", 0),
                "disabilitas": d.get("disabilitas", 0),
                "skor_prioritas": d.get("skor_prioritas"),
            })
        return {"level": level, "metric": key, "items": items}

    @router.get("/sosial/households")
    async def list_households(
        request: Request,
        kode_kecamatan: Optional[str] = None, kode_kelurahan: Optional[str] = None,
        desil: Optional[int] = None, risk_level: Optional[str] = None,
        pbi_nas: Optional[int] = None, pbi_pemda: Optional[int] = None,
        search: Optional[str] = None, page: int = Query(1, ge=1),
        size: int = Query(25, ge=1, le=200),
        sort_by: str = "risk_score", sort_dir: int = -1,
    ):
        user = await optional_user(request)
        if not user:  # data per rumah tangga: wajib login staf (publik hanya agregat)
            raise HTTPException(status_code=401, detail="Data rumah tangga hanya untuk pengguna berwenang")
        allow = sensitive_allowed(user)
        base_q = _hh_filter(kode_kecamatan, kode_kelurahan, desil, pbi_nas, pbi_pemda, risk_level)
        role = user.get("role")
        if role in OPERATOR_RTRW_ROLES:
            # hanya sasaran yang ditugaskan (penugasan RT/RW / kelurahan / KK sasaran sah)
            import verval as verval_mod
            pairs = await verval_mod.operator_households(db, user)
            docs_all = [h for h, _ in pairs if all(
                (str(h.get(k)) == str(v)) if not isinstance(v, dict) else True for k, v in base_q.items())]
            if search:
                s = str(search).strip().upper()
                docs_all = [h for h in docs_all if (
                    s in str(h.get("no_kk") or "")
                    or s in str(h.get("nik") or "")
                    or s in str(h.get("kepala_keluarga") or "").upper()
                    or s in str(h.get("alamat") or "").upper()
                )]
            docs_all.sort(key=lambda d: d.get(sort_by) or 0, reverse=sort_dir < 0)
            total = len(docs_all)
            docs = docs_all[(page - 1) * size:(page - 1) * size + size]
            return {"total": total, "page": page, "size": size, "pages": max(1, math.ceil(total / size)),
                    "masked": False, "cakupan": "sasaran_operator_rt_rw",
                    "items": [mask_household(d, True) for d in docs]}

        q = dict(base_q)
        digit_search = bool(search and str(search).strip().isdigit())
        if search and not digit_search:
            q["kepala_keluarga"] = {"$regex": re.escape(str(search).strip().upper())}
        if role in KECAMATAN_SCOPED:
            wil = str(user.get("wilayah") or "").strip()
            if not wil:
                return {"total": 0, "page": page, "size": size, "pages": 1, "masked": True,
                        "cakupan": "tanpa_wilayah", "items": []}
            q["kecamatan"] = {"$regex": "^" + re.escape(wil) + "$", "$options": "i"}
        elif role in KELURAHAN_SCOPED:
            kel_user = str(user.get("kelurahan") or user.get("wilayah") or "").strip()
            if not kel_user:
                return {"total": 0, "page": page, "size": size, "pages": 1, "masked": True,
                        "cakupan": "tanpa_wilayah", "items": []}
            docs_all = [d for d in await db.households.find(q).to_list(60000) if household_allowed(user, d)]
            if digit_search:
                s = str(search).strip()
                docs_all = [d for d in docs_all if s in str(d.get("no_kk") or "") or s in str(d.get("nik") or "")]
            docs_all.sort(key=lambda d: d.get(sort_by) or 0, reverse=sort_dir < 0)
            total = len(docs_all)
            docs = docs_all[(page - 1) * size:(page - 1) * size + size]
            return {"total": total, "page": page, "size": size, "pages": max(1, math.ceil(total / size)),
                    "masked": not allow, "cakupan": "wilayah_kelurahan",
                    "items": [mask_household(d, allow) for d in docs]}
        elif role == "verifikator":
            import scope as scope_mod
            sc = scope_mod.kecamatan_scope(user)
            if sc:
                q["kecamatan"] = {"$regex": "^" + re.escape(sc) + "$", "$options": "i"}
        elif not (role in CITY_SENSITIVE_ROLES or role in CITY_READ_ROLES):
            raise HTTPException(status_code=403, detail="Peran Anda tidak berwenang melihat data rumah tangga")

        if digit_search:
            s_esc = re.escape(str(search).strip())
            by_kk = await db.households.find({**q, "no_kk": {"$regex": s_esc}}).to_list(5000)
            by_nik = await db.households.find({**q, "nik": {"$regex": s_esc}}).to_list(5000)
            merged: Dict[str, dict] = {}
            for d in by_kk + by_nik:
                key = str(d.get("id") or d.get("_id") or d.get("no_kk"))
                merged[key] = d
            docs_all = sorted(merged.values(), key=lambda d: d.get(sort_by) or 0, reverse=sort_dir < 0)
            total = len(docs_all)
            docs = docs_all[(page - 1) * size:(page - 1) * size + size]
        else:
            total = await db.households.count_documents(q)
            cursor = db.households.find(q).sort(sort_by, -1 if sort_dir < 0 else 1)
            docs = await cursor.skip((page - 1) * size).limit(size).to_list(size)
        return {
            "total": total, "page": page, "size": size,
            "pages": max(1, math.ceil(total / size)),
            "masked": not allow,
            "items": [mask_household(d, allow) for d in docs],
        }

    @router.get("/sosial/households/{household_id}")
    async def get_household(household_id: str, request: Request):
        user = await optional_user(request)
        if not user:  # data per rumah tangga: wajib login staf (publik hanya agregat)
            raise HTTPException(status_code=401, detail="Data rumah tangga hanya untuk pengguna berwenang")
        doc = await db.households.find_one({"id": household_id})
        role = user.get("role")
        if doc and role in OPERATOR_RTRW_ROLES:
            import verval as verval_mod
            pens, sas = await verval_mod.operator_scope(db, user)
            ok = bool(verval_mod.dasar_akses(doc, pens, sas))
        else:
            ok = bool(doc) and household_allowed(user, doc)
        if not ok:
            # 404 seragam: tidak membocorkan keberadaan data di luar wilayah (anti manipulasi ID)
            if doc:
                await db.audit_logs.insert_one({
                    "id": str(uuid.uuid4()), "user": user.get("email"), "role": role,
                    "aksi": "akses_rumah_tangga_ditolak", "entitas": "households", "ref": household_id,
                    "detail": "di luar wilayah kewenangan", "status": "ditolak", "created_at": now_iso()})
            raise HTTPException(status_code=404, detail="Rumah tangga tidak ditemukan atau di luar wilayah kewenangan")
        allow_detail = role in OPERATOR_RTRW_ROLES or sensitive_allowed(user)
        out = mask_household(doc, allow_detail)
        if sensitive_allowed(user):
            await db.audit_logs.insert_one({
                "id": str(uuid.uuid4()), "user": user.get("email"), "role": role,
                "aksi": "lihat_identitas_rumah_tangga", "entitas": "households", "ref": household_id,
                "detail": "", "status": "sukses", "created_at": now_iso()})
        out["penjelasan_level"] = scoring.LEVEL_LABELS.get(doc.get("risk_level"), "-")
        return out

    # ---------------------------------------------------------- scoring config
    @router.get("/sosial/scoring-config")
    async def get_scoring_config():
        cfg = await db.scoring_config.find_one({"id": "default"})
        return _clean(cfg or scoring.default_config())

    @router.put("/sosial/scoring-config")
    async def put_scoring_config(payload: ScoringConfigUpdate, admin: dict = Depends(admin_dep)):
        cfg = await db.scoring_config.find_one({"id": "default"}) or scoring.default_config()
        upd = {k: v for k, v in payload.model_dump().items() if v is not None}
        if upd:
            upd["updated_at"] = now_iso()
            upd["updated_by"] = admin.get("email")
            await db.scoring_config.find_one_and_update(
                {"id": "default"}, {"$set": upd}, upsert=True)
        fresh = await db.scoring_config.find_one({"id": "default"})
        return _clean(fresh or cfg)

    # ---------------------------------------------------------- disabilitas
    @router.get("/disabilitas/overview")
    async def disabilitas_overview(kecamatan: Optional[str] = None):
        region = await db.disability_region_stats.find({}).to_list(1000)
        opd = await db.disability_opd_stats.find({}).to_list(200)
        if kecamatan:
            region = [r for r in region if norm_name(r.get("kecamatan")) == norm_name(kecamatan)]
        total_region = sum(int(r.get("jumlah") or 0) for r in region)
        per_kec: Dict[str, int] = {}
        for r in region:
            k = r.get("kecamatan") or "-"
            per_kec[k] = per_kec.get(k, 0) + int(r.get("jumlah") or 0)
        ragam: Dict[str, int] = {}
        gender = {"laki_laki": 0, "perempuan": 0, "tidak_menjawab": 0}
        usia = {"dibawah_18": 0, "usia_18_59": 0, "usia_60_keatas": 0}
        for o in opd:
            for k, v in (o.get("ragam") or {}).items():
                ragam[k] = ragam.get(k, 0) + int(v or 0)
            gender["laki_laki"] += int(o.get("laki_laki") or 0)
            gender["perempuan"] += int(o.get("perempuan") or 0)
            gender["tidak_menjawab"] += int(o.get("memilih_untuk_tidak_menjawab") or 0)
            usia["dibawah_18"] += int(o.get("usia_dibawah_18") or 0)
            usia["usia_18_59"] += int(o.get("usia_18_59") or 0)
            usia["usia_60_keatas"] += int(o.get("usia_60_keatas") or 0)
        # rekap tambahan yang berasal dari data wilayah/kelurahan (impor & input manual)
        wilayah_agregat = {k: 0 for k in (
            "laki_laki", "perempuan", "usia_dibawah_18", "usia_18_59", "usia_60_keatas",
            "fisik", "ganda", "intelektual", "mental", "sensorik_pendengaran",
            "sensorik_penglihatan")}
        for r in region:
            for k in wilayah_agregat:
                wilayah_agregat[k] += int(r.get(k) or 0)
        usia["usia_60_keatas"] += wilayah_agregat["usia_60_keatas"]
        return {
            "total_wilayah": total_region,
            "total_laporan_opd": sum(int(o.get("total") or 0) for o in opd),
            "per_kecamatan": [{"kecamatan": k, "jumlah": v} for k, v in
                              sorted(per_kec.items(), key=lambda x: -x[1])],
            "per_kelurahan": sorted(
                [{"kecamatan": r.get("kecamatan"), "kelurahan": r.get("kelurahan"),
                  "jumlah": int(r.get("jumlah") or 0)} for r in region],
                key=lambda x: -x["jumlah"]),
            "ragam": [{"nama": k, "jumlah": v} for k, v in
                      sorted(ragam.items(), key=lambda x: -x[1])],
            "gender": gender, "usia": usia, "wilayah_agregat": wilayah_agregat,
            "sumber_opd": [{"skpd": o.get("skpd"), "total": o.get("total"),
                            "ragam": o.get("ragam"), "laki_laki": o.get("laki_laki"),
                            "perempuan": o.get("perempuan"),
                            "usia_dibawah_18": o.get("usia_dibawah_18"),
                            "usia_18_59": o.get("usia_18_59")} for o in opd],
            "catatan": ("Data individu penyandang disabilitas belum tersedia pada berkas "
                        "sumber; angka berikut adalah rekap agregat per wilayah & SKPD."),
        }

    # ---------------------------------------------------------- stunting
    @router.get("/stunting/overview")
    async def stunting_overview():
        subs = await db.stunting_subactivities.find({}).to_list(5000)
        per_opd: Dict[str, Dict[str, float]] = {}
        per_program: Dict[str, Dict[str, float]] = {}
        t25 = t26 = 0.0
        for s in subs:
            a25 = float(s.get("anggaran_2025") or 0)
            a26 = float(s.get("anggaran_2026") or 0)
            t25 += a25
            t26 += a26
            o = per_opd.setdefault(s.get("opd") or "-",
                                   {"anggaran_2025": 0.0, "anggaran_2026": 0.0,
                                    "sub_kegiatan": 0, "program": set()})
            o["anggaran_2025"] += a25
            o["anggaran_2026"] += a26
            o["sub_kegiatan"] += 1
            o["program"].add(s.get("program") or "-")
            p = per_program.setdefault(s.get("program") or "-",
                                       {"anggaran_2025": 0.0, "anggaran_2026": 0.0,
                                        "sub_kegiatan": 0, "opd": s.get("opd")})
            p["anggaran_2025"] += a25
            p["anggaran_2026"] += a26
            p["sub_kegiatan"] += 1
        opd_items = [{"opd": k, "anggaran_2025": v["anggaran_2025"],
                      "anggaran_2026": v["anggaran_2026"],
                      "sub_kegiatan": v["sub_kegiatan"], "program": len(v["program"])}
                     for k, v in per_opd.items()]
        opd_items.sort(key=lambda x: -x["anggaran_2025"])
        prog_items = [{"program": k, **{kk: vv for kk, vv in v.items()}} for k, v in per_program.items()]
        prog_items.sort(key=lambda x: -float(x["anggaran_2025"]))
        targets = [s for s in subs if s.get("target_2027") not in (None, "", "nan")]
        return {
            "jumlah_opd": len(per_opd),
            "jumlah_program": await db.stunting_programs.count_documents({}),
            "jumlah_kegiatan": await db.stunting_activities.count_documents({}),
            "jumlah_sub_kegiatan": len(subs),
            "anggaran_2025": t25, "anggaran_2026": t26,
            "selisih_anggaran": t26 - t25,
            "jumlah_target_2027": len(targets),
            "per_opd": opd_items, "per_program": prog_items[:20],
        }

    @router.get("/stunting/items")
    async def stunting_items(opd: Optional[str] = None, program: Optional[str] = None,
                             search: Optional[str] = None, page: int = Query(1, ge=1),
                             size: int = Query(25, ge=1, le=500)):
        docs = await db.stunting_subactivities.find({}).to_list(5000)
        if opd:
            docs = [d for d in docs if norm_name(d.get("opd")) == norm_name(opd)]
        if program:
            docs = [d for d in docs if norm_name(program) in norm_name(d.get("program"))]
        if search:
            s = norm_name(search)
            docs = [d for d in docs if s in norm_name(d.get("nama")) or
                    s in norm_name(d.get("kegiatan")) or s in norm_name(d.get("indikator")) or
                    s in norm_name(d.get("program")) or s in norm_name(d.get("opd"))]
        total = len(docs)
        docs.sort(key=lambda d: -float(d.get("anggaran_2025") or 0))
        start = (page - 1) * size
        return {"total": total, "page": page, "size": size,
                "pages": max(1, math.ceil(total / size)),
                "opd_list": sorted({d.get("opd") for d in docs if d.get("opd")}),
                "items": [_clean(d) for d in docs[start:start + size]]}

    # ---------------------------------------------------------- RAD disabilitas
    @router.get("/rad/overview")
    async def rad_overview():
        items = await db.rad_items.find({}).to_list(2000)
        monitor = {m.get("item_id"): m for m in await db.rad_monitoring.find({}).to_list(2000)}
        tahun_total: Dict[str, float] = {}
        for it in items:
            for tahun, val in (it.get("targets") or {}).items():
                if val is not None:
                    tahun_total[tahun] = tahun_total.get(tahun, 0.0) + float(val)
        status_count: Dict[str, int] = {}
        progress_sum = 0.0
        for it in items:
            m = monitor.get(it.get("id")) or {}
            st = m.get("status") or "Belum Dimulai"
            status_count[st] = status_count.get(st, 0) + 1
            progress_sum += float(m.get("progress") or 0)
        hambatan = [it.get("hambatan") for it in items if it.get("hambatan")]
        return {
            "jumlah_strategi": await db.rad_strategies.count_documents({"jenis": "sasaran_strategis"}),
            "jumlah_kebijakan": await db.rad_strategies.count_documents({"jenis": "kebijakan"}),
            "jumlah_program": len({norm_name(i.get("program")) for i in items if i.get("program")}),
            "jumlah_kegiatan": len({norm_name(i.get("kegiatan")) for i in items if i.get("kegiatan")}),
            "jumlah_item": len(items),
            "target_per_tahun": [{"tahun": t, "target": v} for t, v in sorted(tahun_total.items())],
            "status": [{"status": k, "jumlah": v} for k, v in sorted(status_count.items(), key=lambda x: -x[1])],
            "rata_progress": round(progress_sum / max(len(items), 1), 2),
            "hambatan_utama": hambatan[:10],
        }

    @router.get("/rad/items")
    async def rad_items(search: Optional[str] = None, status: Optional[str] = None,
                        page: int = Query(1, ge=1), size: int = Query(25, ge=1, le=500)):
        items = await db.rad_items.find({}).to_list(2000)
        monitor = {m.get("item_id"): m for m in await db.rad_monitoring.find({}).to_list(2000)}
        out = []
        for it in items:
            m = monitor.get(it.get("id")) or {}
            row = _clean(it)
            row["monitoring"] = {
                "status": m.get("status") or "Belum Dimulai",
                "progress": m.get("progress") or 0,
                "catatan": m.get("catatan") or "",
                "dokumen": m.get("dokumen") or "",
                "penanggung_jawab": m.get("penanggung_jawab") or "",
                "updated_at": m.get("updated_at") or "",
            }
            out.append(row)
        if status:
            out = [r for r in out if r["monitoring"]["status"] == status]
        if search:
            s = norm_name(search)
            out = [r for r in out if s in norm_name(r.get("program")) or
                   s in norm_name(r.get("kegiatan")) or s in norm_name(r.get("sub_kegiatan")) or
                   s in norm_name(r.get("indikator_capaian")) or
                   s in norm_name(r.get("strategi_implementasi"))]
        total = len(out)
        start = (page - 1) * size
        return {"total": total, "page": page, "size": size,
                "pages": max(1, math.ceil(total / size)), "items": out[start:start + size]}

    @router.put("/rad/monitoring/{item_id}")
    async def update_monitoring(item_id: str, payload: MonitoringUpdate,
                                user: dict = Depends(editor_dep)):
        item = await db.rad_items.find_one({"id": item_id})
        if not item:
            raise HTTPException(status_code=404, detail="Item RAD tidak ditemukan")
        upd = {k: v for k, v in payload.model_dump().items() if v is not None}
        upd["updated_at"] = now_iso()
        upd["updated_by"] = user.get("email")
        existing = await db.rad_monitoring.find_one({"item_id": item_id})
        if existing:
            await db.rad_monitoring.update_one({"item_id": item_id}, {"$set": upd})
        else:
            await db.rad_monitoring.insert_one({"id": str(uuid.uuid4()), "item_id": item_id,
                                                "status": "Belum Dimulai", "progress": 0, **upd})
        await db.audit_logs.insert_one({
            "id": str(uuid.uuid4()), "user": user.get("email"), "action": "rad_monitoring_update",
            "entitas": "rad_items", "ref": item_id, "detail": json.dumps(upd)[:800],
            "created_at": now_iso()})
        fresh = await db.rad_monitoring.find_one({"item_id": item_id})
        return _clean(fresh or {})

    # ---------------------------------------------------------- GIS choropleth
    @router.get("/geo/kelurahan")
    async def geo_kelurahan(metric: str = "skor_prioritas",
                            kode_kecamatan: Optional[str] = None):
        feats = await db.geo_kelurahan.find({}).to_list(500)
        stats = await db.village_stats.find({}).to_list(1000)
        by_norm = {norm_name(s.get("kelurahan")): s for s in stats}
        dis = await db.disability_region_stats.find({}).to_list(1000)
        dis_by_norm: Dict[str, int] = {}
        for d in dis:
            k = norm_name(d.get("kelurahan"))
            dis_by_norm[k] = dis_by_norm.get(k, 0) + int(d.get("jumlah") or 0)
        features = []
        values: List[float] = []
        for f in feats:
            kel_norm = f.get("kelurahan_norm")
            s = by_norm.get(kel_norm) or {}
            if kode_kecamatan and s.get("kode_kecamatan") != str(kode_kecamatan):
                if norm_name(f.get("kecamatan")) != norm_name(kode_kecamatan):
                    pass
            value = s.get(metric)
            if metric == "disabilitas":
                value = dis_by_norm.get(kel_norm, 0)
            if value is None:
                value = 0
            values.append(float(value))
            features.append({
                "type": "Feature",
                "id": f.get("id"),
                "geometry": f.get("geometry"),
                "properties": {
                    "kelurahan": f.get("kelurahan"), "kecamatan": f.get("kecamatan"),
                    "kode_kelurahan": s.get("kode_kelurahan"),
                    "kode_kecamatan": s.get("kode_kecamatan"),
                    "value": value, "metric": metric,
                    "punya_data": bool(s),
                    "total_households": s.get("total_households", 0),
                    "total_individu": s.get("total_individu", 0),
                    "desil_1_2": s.get("desil_1_2", 0),
                    "persen_desil_1_2": s.get("persen_desil_1_2", 0),
                    "rumah_rentan": s.get("rumah_rentan", 0),
                    "sanitasi_tidak_layak": s.get("sanitasi_tidak_layak", 0),
                    "air_rentan": s.get("air_rentan", 0),
                    "avg_risk": s.get("avg_risk", 0),
                    "skor_prioritas": s.get("skor_prioritas", 0),
                    "disabilitas": dis_by_norm.get(kel_norm, 0),
                    "prioritas_tinggi": s.get("prioritas_tinggi", 0),
                },
            })
        nonzero = [v for v in values if v > 0]
        return {"type": "FeatureCollection", "features": features, "metric": metric,
                "min": min(nonzero) if nonzero else 0,
                "max": max(values) if values else 0,
                "count": len(features),
                "count_dengan_data": len(nonzero)}

    # ---------------------------------------------------------- prioritas & rekomendasi
    def _rekomendasi(v: Dict[str, Any]) -> List[str]:
        out = []
        if (v.get("persen_desil_1_2") or 0) >= 25:
            out.append("Perluasan perlindungan sosial & verifikasi DTKS pada desil 1-2")
        if (v.get("sanitasi_tidak_layak") or 0) > 0:
            out.append("Intervensi sanitasi (jamban sehat, tangki septik, sanitasi komunal)")
        if (v.get("air_rentan") or 0) > 0:
            out.append("Perluasan akses air minum layak (SPAM/PDAM)")
        if (v.get("hunian_rentan") or 0) > 0:
            out.append("Program bedah rumah / peningkatan kualitas rumah tidak layak huni")
        if (v.get("disabilitas") or 0) >= 20:
            out.append("Layanan & aksesibilitas penyandang disabilitas (alat bantu, RAD PD)")
        if (v.get("prioritas_tinggi") or 0) > 0:
            out.append("Pendampingan keluarga prioritas & konvergensi program stunting")
        return out or ["Pemantauan berkala; tidak ada indikator kritis terdeteksi"]

    def _masalah(v: Dict[str, Any]) -> List[str]:
        out = []
        if (v.get("persen_desil_1_2") or 0) >= 20:
            out.append(f"{v.get('desil_1_2')} KK berada pada desil 1-2 "
                       f"({v.get('persen_desil_1_2')}% dari total KK)")
        if (v.get("sanitasi_tidak_layak") or 0) > 0:
            out.append(f"{v.get('sanitasi_tidak_layak')} KK dengan sanitasi rentan")
        if (v.get("air_rentan") or 0) > 0:
            out.append(f"{v.get('air_rentan')} KK dengan sumber air minum rentan")
        if (v.get("hunian_rentan") or 0) > 0:
            out.append(f"{v.get('hunian_rentan')} KK dengan kondisi hunian rentan")
        if (v.get("disabilitas") or 0) > 0:
            out.append(f"{v.get('disabilitas')} penyandang disabilitas terdata")
        return out

    @router.get("/analisis/prioritas")
    async def analisis_prioritas(limit: int = Query(10, ge=1, le=200),
                                 kode_kecamatan: Optional[str] = None):
        q = {"kode_kecamatan": str(kode_kecamatan)} if kode_kecamatan else {}
        stats = await db.village_stats.find(q).to_list(1000)
        stats.sort(key=lambda d: float(d.get("skor_prioritas") or 0), reverse=True)
        subs = await db.stunting_subactivities.find({}).to_list(5000)
        rad = await db.rad_items.find({}).to_list(2000)

        def program_relevan(v: Dict[str, Any]) -> Dict[str, List[Dict[str, Any]]]:
            keys = []
            if (v.get("sanitasi_tidak_layak") or 0) > 0:
                keys += ["sanitasi", "air", "jamban", "lingkungan"]
            if (v.get("hunian_rentan") or 0) > 0:
                keys += ["rumah", "perumahan", "hunian"]
            if (v.get("persen_desil_1_2") or 0) >= 20:
                keys += ["sosial", "kemiskinan", "pangan", "gizi", "stunting"]
            if (v.get("disabilitas") or 0) > 0:
                keys += ["disabilitas", "rehabilitasi", "aksesibilitas"]
            keys = keys or ["stunting"]
            st = []
            for s in subs:
                blob = norm_name(f"{s.get('program')} {s.get('kegiatan')} {s.get('nama')} {s.get('indikator')}")
                if any(norm_name(k) in blob for k in keys):
                    st.append({"opd": s.get("opd"), "program": s.get("program"),
                               "sub_kegiatan": s.get("nama"),
                               "anggaran_2025": s.get("anggaran_2025"),
                               "anggaran_2026": s.get("anggaran_2026")})
                if len(st) >= 5:
                    break
            rd = []
            for r in rad:
                blob = norm_name(f"{r.get('program')} {r.get('kegiatan')} {r.get('sub_kegiatan')} {r.get('indikator_disabilitas')}")
                if any(norm_name(k) in blob for k in keys):
                    rd.append({"program": r.get("program"), "kegiatan": r.get("kegiatan"),
                               "indikator": r.get("indikator_capaian"),
                               "targets": r.get("targets")})
                if len(rd) >= 5:
                    break
            return {"stunting": st, "rad_disabilitas": rd}

        items = []
        for v in stats[:limit]:
            items.append({
                "kode_kelurahan": v.get("kode_kelurahan"), "kelurahan": v.get("kelurahan"),
                "kecamatan": v.get("kecamatan"),
                "skor_prioritas": v.get("skor_prioritas"),
                "avg_risk": v.get("avg_risk"),
                "total_households": v.get("total_households"),
                "total_individu": v.get("total_individu"),
                "populasi_terdampak": v.get("prioritas_tinggi"),
                "desil_1_2": v.get("desil_1_2"),
                "persen_desil_1_2": v.get("persen_desil_1_2"),
                "disabilitas": v.get("disabilitas"),
                "masalah_utama": _masalah(v),
                "rekomendasi": _rekomendasi(v),
                "program_relevan": program_relevan(v),
                "indikator": {
                    "sanitasi_tidak_layak": v.get("sanitasi_tidak_layak"),
                    "air_rentan": v.get("air_rentan"),
                    "hunian_rentan": v.get("hunian_rentan"),
                    "rumah_rentan": v.get("rumah_rentan"),
                    "per_risk": v.get("per_risk"),
                },
            })
        return {"total": len(stats), "items": items}

    # ---------------------------------------------------------- audit impor & kualitas data
    @router.get("/admin/import-batches")
    async def import_batches(admin: dict = Depends(admin_dep), jenis: Optional[str] = None):
        q = {"jenis": jenis} if jenis else {}
        docs = await db.import_batches.find(q).sort("uploaded_at", -1).to_list(500)
        return {"total": len(docs), "items": [_clean(d) for d in docs]}

    @router.get("/admin/data-quality")
    async def data_quality(admin: dict = Depends(admin_dep),
                           jenis: Optional[str] = None, entitas: Optional[str] = None,
                           page: int = Query(1, ge=1), size: int = Query(50, ge=1, le=500)):
        q: Dict[str, Any] = {}
        if jenis:
            q["jenis"] = jenis
        if entitas:
            q["entitas"] = entitas
        total = await db.data_quality_issues.count_documents(q)
        docs = await db.data_quality_issues.find(q).skip((page - 1) * size).limit(size).to_list(size)
        return {"total": total, "page": page, "size": size,
                "pages": max(1, math.ceil(total / size)),
                "items": [_clean(d) for d in docs]}

    @router.get("/admin/data-quality/summary")
    async def data_quality_summary(admin: dict = Depends(admin_dep)):
        docs = await db.data_quality_issues.find({}).to_list(100000)
        per_jenis: Dict[str, int] = {}
        per_entitas: Dict[str, int] = {}
        for d in docs:
            per_jenis[d.get("jenis") or "-"] = per_jenis.get(d.get("jenis") or "-", 0) + 1
            per_entitas[d.get("entitas") or "-"] = per_entitas.get(d.get("entitas") or "-", 0) + 1
        return {"total": len(docs),
                "per_jenis": [{"jenis": k, "jumlah": v} for k, v in
                              sorted(per_jenis.items(), key=lambda x: -x[1])],
                "per_entitas": [{"entitas": k, "jumlah": v} for k, v in
                                sorted(per_entitas.items(), key=lambda x: -x[1])]}

    @router.get("/admin/import-summary")
    async def import_summary(admin: dict = Depends(admin_dep)):
        counts = {}
        for coll in ["households", "household_members", "villages", "districts",
                     "geo_kelurahan", "disability_region_stats", "disability_opd_stats",
                     "stunting_subactivities", "stunting_programs", "stunting_activities",
                     "rad_items", "rad_strategies", "raw_imports", "import_batches",
                     "data_quality_issues", "village_stats", "district_stats", "opd"]:
            counts[coll] = await getattr(db, coll).count_documents({})
        batches = await db.import_batches.find({}).to_list(500)
        per_jenis: Dict[str, Dict[str, int]] = {}
        for b in batches:
            j = per_jenis.setdefault(b.get("jenis") or "-", {
                "file": 0, "total_rows": 0, "inserted": 0, "duplicate": 0, "failed": 0})
            j["file"] += 1
            for k in ("total_rows", "inserted", "duplicate", "failed"):
                j[k] += int(b.get(k) or 0)
        return {"counts": counts,
                "per_jenis": [{"jenis": k, **v} for k, v in per_jenis.items()],
                "total_file": len(batches)}

    @router.get("/admin/audit-logs")
    async def audit_logs(admin: dict = Depends(admin_dep), size: int = Query(100, ge=1, le=500)):
        docs = await db.audit_logs.find({}).sort("created_at", -1).to_list(size)
        return {"total": len(docs), "items": [_clean(d) for d in docs]}

    return router
