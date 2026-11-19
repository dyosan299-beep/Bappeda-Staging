"""Pengujian terisolasi modul Verval + GeoTag v2 (alur 2 tahap, watermark, warga baru, sync sistem, & scoping role).

Seluruh operasi database memakai FakeDB in-memory + tmp_path agar 100% terisolasi dari MariaDB produksi.
"""
from __future__ import annotations

import copy
import io
import os
import re
import sys
import uuid
from pathlib import Path
from typing import Any, Dict, List, Optional

import pytest
from bsonlite import ObjectId
from fastapi import FastAPI, HTTPException, Request
from fastapi.testclient import TestClient
from PIL import Image

BACKEND_DIR = Path(__file__).resolve().parents[1]
if str(BACKEND_DIR) not in sys.path:
    sys.path.insert(0, str(BACKEND_DIR))

import data_manage as data_manage_mod
import dtsen_ref as dref
import scope as scope_mod
import server as server_mod
import sosial as sosial_mod
import verval as verval_mod
import verval_config as cfg


# ===================================================================== FakeDB in-memory
def _get_nested(doc: dict, field: str) -> Any:
    if "." not in field:
        return doc.get(field)
    cur: Any = doc
    for part in field.split("."):
        if not isinstance(cur, dict):
            return None
        cur = cur.get(part)
    return cur


def _match_doc(doc: dict, filt: Optional[Dict[str, Any]]) -> bool:
    if not filt:
        return True
    for k, cond in filt.items():
        val = _get_nested(doc, k)
        if k == "_id" and isinstance(cond, ObjectId):
            if str(val) != str(cond):
                return False
            continue
        if isinstance(cond, dict):
            for op, target in cond.items():
                if op == "$ne":
                    if val == target:
                        return False
                elif op == "$exists":
                    exists = k in doc and doc[k] is not None
                    if bool(target) != exists:
                        return False
                elif op == "$in":
                    if val not in target:
                        return False
                elif op == "$nin":
                    if val in target:
                        return False
                elif op == "$regex":
                    flags = re.IGNORECASE if "i" in str(cond.get("$options") or "") else 0
                    if not re.search(str(target), str(val or ""), flags):
                        return False
                elif op == "$options":
                    continue
                elif op == "$gt":
                    if val is None or val <= target:
                        return False
                elif op == "$gte":
                    if val is None or val < target:
                        return False
                elif op == "$lt":
                    if val is None or val >= target:
                        return False
                elif op == "$lte":
                    if val is None or val > target:
                        return False
        else:
            if isinstance(val, ObjectId):
                val = str(val)
            if isinstance(cond, ObjectId):
                cond = str(cond)
            if val != cond:
                return False
    return True


class _FakeResult:
    def __init__(self, inserted_id=None, modified_count=0, deleted_count=0):
        self.inserted_id = inserted_id
        self.modified_count = modified_count
        self.deleted_count = deleted_count


class FakeCursor:
    def __init__(self, docs: List[dict]):
        self._docs = docs

    def sort(self, field, direction: int = 1):
        reverse = direction < 0
        self._docs.sort(key=lambda d: str(_get_nested(d, field) or ""), reverse=reverse)
        return self

    def skip(self, n: int):
        self._docs = self._docs[n:]
        return self

    def limit(self, n: int):
        self._docs = self._docs[:n]
        return self

    async def to_list(self, n: Optional[int] = None) -> List[dict]:
        return [copy.deepcopy(d) for d in (self._docs[:n] if n is not None else self._docs)]


class FakeCollection:
    def __init__(self):
        self.docs: List[dict] = []

    def find(self, filt: Optional[Dict[str, Any]] = None) -> FakeCursor:
        matched = [copy.deepcopy(d) for d in self.docs if _match_doc(d, filt)]
        return FakeCursor(matched)

    async def find_one(self, filt: Optional[Dict[str, Any]] = None) -> Optional[dict]:
        for d in self.docs:
            if _match_doc(d, filt):
                return copy.deepcopy(d)
        return None

    async def count_documents(self, filt: Optional[Dict[str, Any]] = None) -> int:
        return sum(1 for d in self.docs if _match_doc(d, filt))

    async def insert_one(self, doc: dict) -> _FakeResult:
        rec = copy.deepcopy(doc)
        if "_id" not in rec:
            rec["_id"] = str(ObjectId())
        self.docs.append(rec)
        return _FakeResult(inserted_id=rec["_id"])

    async def update_one(self, filt: Dict[str, Any], update: Dict[str, Any], upsert: bool = False) -> _FakeResult:
        for d in self.docs:
            if _match_doc(d, filt):
                for k, v in (update.get("$set") or {}).items():
                    d[k] = copy.deepcopy(v)
                for k in (update.get("$unset") or {}).keys():
                    d.pop(k, None)
                for k, inc in (update.get("$inc") or {}).items():
                    d[k] = (d.get(k) or 0) + inc
                return _FakeResult(modified_count=1)
        if upsert:
            new_doc = {k: copy.deepcopy(v) for k, v in filt.items() if not isinstance(v, dict)}
            new_doc.update(copy.deepcopy(update.get("$set") or {}))
            if "_id" not in new_doc:
                new_doc["_id"] = str(ObjectId())
            self.docs.append(new_doc)
            return _FakeResult(inserted_id=new_doc["_id"], modified_count=1)
        return _FakeResult(modified_count=0)

    async def find_one_and_update(
        self, filt: Dict[str, Any], update: Dict[str, Any], return_document=None, upsert: bool = False
    ) -> Optional[dict]:
        for d in self.docs:
            if _match_doc(d, filt):
                for k, v in (update.get("$set") or {}).items():
                    d[k] = copy.deepcopy(v)
                return copy.deepcopy(d)
        if upsert:
            new_doc = {k: copy.deepcopy(v) for k, v in filt.items() if not isinstance(v, dict)}
            new_doc.update(copy.deepcopy(update.get("$set") or {}))
            if "_id" not in new_doc:
                new_doc["_id"] = str(ObjectId())
            self.docs.append(new_doc)
            return copy.deepcopy(new_doc)
        return None

    async def delete_many(self, filt: Dict[str, Any]) -> _FakeResult:
        before = len(self.docs)
        self.docs = [d for d in self.docs if not _match_doc(d, filt)]
        return _FakeResult(deleted_count=before - len(self.docs))

    async def delete_one(self, filt: Dict[str, Any]) -> _FakeResult:
        for idx, d in enumerate(self.docs):
            if _match_doc(d, filt):
                self.docs.pop(idx)
                return _FakeResult(deleted_count=1)
        return _FakeResult(deleted_count=0)


class FakeDB:
    def __init__(self):
        self._cols: Dict[str, FakeCollection] = {}

    def __getattr__(self, name: str) -> FakeCollection:
        if name.startswith("_"):
            raise AttributeError(name)
        return self._cols.setdefault(name, FakeCollection())


# ===================================================================== Fixtures
def _make_jpeg(color=(200, 220, 240), size=(640, 480), with_exif_gps: bool = False) -> bytes:
    buf = io.BytesIO()
    im = Image.new("RGB", size, color)
    if with_exif_gps:
        exif = im.getexif()
        exif[0x8825] = {
            1: "S",
            2: (5.0, 8.0, 50.0),
            3: "E",
            4: (119.0, 25.0, 50.0),
            29: "2026:11:19",
            7: (7.0, 15.0, 0.0),
        }
        im.save(buf, format="JPEG", exif=exif.tobytes())
    else:
        im.save(buf, format="JPEG")
    return buf.getvalue()


def _valid_indikator() -> dict:
    ind = {
        k: {"kesesuaian": "sesuai", "kondisi_riil": "sesuai", "catatan": ""}
        for k in ("no_kk", "nama_krt", "jumlah_anggota", "pln", "kepemilikan_rumah")
    }
    ind["status_desil"] = {"kesesuaian": "tetap", "kondisi_riil": "graduasi", "catatan": "Ekonomi membaik"}
    ind["pbi_jkn"] = {"kesesuaian": "aktif", "kondisi_riil": "aktif", "catatan": ""}
    ind["fisik_rumah"] = {"kesesuaian": "rtlh", "kondisi_riil": "tidak_layak", "catatan": "Atap bocor parah"}
    ind["air_minum"] = {"kesesuaian": "layak", "kondisi_riil": "layak", "catatan": ""}
    ind["sanitasi"] = {"kesesuaian": "odf", "kondisi_riil": "odf", "catatan": ""}
    ind["aset_pekerjaan"] = {"kesesuaian": "cukup", "kondisi_riil": "cukup", "catatan": ""}
    return ind


@pytest.fixture()
def env(tmp_path, monkeypatch):
    monkeypatch.setenv("VERVAL_STORAGE_DIR", str(tmp_path / "verval_photos"))
    monkeypatch.setenv("VERVAL_REF_SECRET", "uji-rahasia-verval-2026-tidak-untuk-produksi")
    monkeypatch.setenv("VERVAL_GPS_MAX_AKURASI_M", "30")
    monkeypatch.delenv("VERVAL_IZINKAN_KIRIM_TANPA_GPS", raising=False)
    scope_mod.invalidate()

    db = FakeDB()
    users = {
        "rt1": {
            "_id": ObjectId(), "id": None, "email": "rt1@bonto.local", "name": "Ketua RT 01",
            "role": "petugas", "wilayah": "Mamajang", "kelurahan": "Bonto Lebang",
            "kode_kelurahan": "7371010001", "rw": "1", "rt": ["1"], "status": "active",
        },
        "rt2": {
            "_id": ObjectId(), "id": None, "email": "rt2@bonto.local", "name": "Ketua RT 02",
            "role": "petugas", "wilayah": "Mamajang", "kelurahan": "Bonto Lebang",
            "kode_kelurahan": "7371010001", "rw": "1", "rt": ["2"], "status": "active",
        },
        "rw1": {
            "_id": ObjectId(), "id": None, "email": "rw1@bonto.local", "name": "Ketua RW 01",
            "role": "petugas", "wilayah": "Mamajang", "kelurahan": "Bonto Lebang",
            "kode_kelurahan": "7371010001", "rw": "1", "rt": [], "status": "active",
        },
        "kel_bonto": {
            "_id": ObjectId(), "id": None, "email": "kel.bonto@makassar.local", "name": "Lurah Bonto Lebang",
            "role": "operator_kelurahan", "wilayah": "Mamajang", "kelurahan": "Bonto Lebang",
            "kode_kelurahan": "7371010001", "rw": "", "rt": [], "status": "active",
        },
        "kel_karang": {
            "_id": ObjectId(), "id": None, "email": "kel.karang@makassar.local", "name": "Lurah Karang Anyar",
            "role": "operator_kelurahan", "wilayah": "Mamajang", "kelurahan": "Karang Anyar",
            "kode_kelurahan": "7371010002", "rw": "", "rt": [], "status": "active",
        },
        "kec_mamajang": {
            "_id": ObjectId(), "id": None, "email": "kec.mamajang@makassar.local", "name": "Camat Mamajang",
            "role": "operator", "wilayah": "Mamajang", "kelurahan": "", "kode_kelurahan": "",
            "rw": "", "rt": [], "status": "active",
        },
        "kec_tallo": {
            "_id": ObjectId(), "id": None, "email": "kec.tallo@makassar.local", "name": "Camat Tallo",
            "role": "operator_kecamatan", "wilayah": "Tallo", "kelurahan": "", "kode_kelurahan": "",
            "rw": "", "rt": [], "status": "active",
        },
        "bappeda": {
            "_id": ObjectId(), "id": None, "email": "bappeda@makassar.local", "name": "Admin Bappeda",
            "role": "admin_bappeda", "wilayah": "Kota Makassar", "kelurahan": "", "kode_kelurahan": "",
            "rw": "", "rt": [], "status": "active",
        },
        "super": {
            "_id": ObjectId(), "id": None, "email": "super@makassar.local", "name": "Superadmin",
            "role": "superadmin", "wilayah": "Kota Makassar", "kelurahan": "", "kode_kelurahan": "",
            "rw": "", "rt": [], "status": "active",
        },
    }
    for key, u in users.items():
        u["id"] = str(u["_id"])
        db.users.docs.append(copy.deepcopy(u))

    # Kelurahan master untuk server user validation
    for kec, kel in [("Mamajang", "Bonto Lebang"), ("Mamajang", "Karang Anyar"), ("Tallo", "Pannampu")]:
        db.kelurahan.docs.append({"kecamatan": kec, "nama": kel})

    # Seed households: 2 di Bonto Lebang (rw/rt kosong!), 1 di Karang Anyar, 1 di Tallo
    ref_b1 = dref.make_ref("7371010101010001", "7371010001", "Bonto Lebang")
    ref_b2 = dref.make_ref("7371010101010002", "7371010001", "Bonto Lebang")
    ref_ka = dref.make_ref("7371020202020001", "7371010002", "Karang Anyar")
    ref_tl = dref.make_ref("7371030303030001", "7371050001", "Pannampu")

    households = [
        {
            "id": "hh-b1", "dtsen_ref": ref_b1, "no_kk": "7371010101010001", "no_kk_mask": "7371********0001",
            "nik": "", "kepala_keluarga": "BUDI SANTOSO", "alamat": "JL VETERAN LR 1",
            "kecamatan": "Mamajang", "kode_kecamatan": "737101",
            "kelurahan": "Bonto Lebang", "kode_kelurahan": "7371010001",
            "rw": "", "rt": "", "jumlah_anggota_keluarga": 4, "desil_nasional": 1,
            "pbi_nas": 1, "pbi_pemda": 0, "risk_score": 55.0, "risk_level": "tinggi",
            "rumah_rentan": False, "hunian_rentan": False, "air_rentan": False, "sanitasi_rentan": False,
        },
        {
            "id": "hh-b2", "dtsen_ref": ref_b2, "no_kk": "7371010101010002", "no_kk_mask": "7371********0002",
            "nik": "", "kepala_keluarga": "SITI AMINAH", "alamat": "JL VETERAN LR 2",
            "kecamatan": "Mamajang", "kode_kecamatan": "737101",
            "kelurahan": "Bonto Lebang", "kode_kelurahan": "7371010001",
            "rw": "", "rt": "", "jumlah_anggota_keluarga": 3, "desil_nasional": 2,
            "pbi_nas": 0, "pbi_pemda": 0, "risk_score": 30.0, "risk_level": "rendah",
            "rumah_rentan": False, "hunian_rentan": False, "air_rentan": False, "sanitasi_rentan": False,
        },
        {
            "id": "hh-ka", "dtsen_ref": ref_ka, "no_kk": "7371020202020001", "no_kk_mask": "7371********0001",
            "nik": "", "kepala_keluarga": "RAHMAT HIDAYAT", "alamat": "JL KARANG ANYAR 5",
            "kecamatan": "Mamajang", "kode_kecamatan": "737101",
            "kelurahan": "Karang Anyar", "kode_kelurahan": "7371010002",
            "rw": "", "rt": "", "jumlah_anggota_keluarga": 2, "desil_nasional": 2,
            "pbi_nas": 0, "pbi_pemda": 0, "risk_score": 25.0, "risk_level": "rendah",
            "rumah_rentan": False, "hunian_rentan": False, "air_rentan": False, "sanitasi_rentan": False,
        },
        {
            "id": "hh-tl", "dtsen_ref": ref_tl, "no_kk": "7371030303030001", "no_kk_mask": "7371********0001",
            "nik": "", "kepala_keluarga": "HASANUDDIN", "alamat": "JL TALLO RAYA 9",
            "kecamatan": "Tallo", "kode_kecamatan": "737105",
            "kelurahan": "Pannampu", "kode_kelurahan": "7371050001",
            "rw": "1", "rt": "1", "jumlah_anggota_keluarga": 5, "desil_nasional": 1,
            "pbi_nas": 1, "pbi_pemda": 0, "risk_score": 60.0, "risk_level": "tinggi",
            "rumah_rentan": False, "hunian_rentan": False, "air_rentan": False, "sanitasi_rentan": False,
        },
    ]
    for h in households:
        db.households.docs.append(copy.deepcopy(h))
        db.household_members.docs.append({
            "id": f"m-{h['id']}", "household_id": h["id"], "no_kk": h["no_kk"],
            "nik": "", "nama": h["kepala_keluarga"], "peran": "Kepala Keluarga",
            "kode_kelurahan": h["kode_kelurahan"],
        })

    app = FastAPI()

    async def current_user_dep(request: Request) -> dict:
        key = request.headers.get("X-Test-User") or ""
        if key not in users:
            raise HTTPException(status_code=401, detail="Unauthorized test user")
        return copy.deepcopy(users[key])

    async def editor_dep(request: Request) -> dict:
        return await current_user_dep(request)

    async def admin_dep(request: Request) -> dict:
        u = await current_user_dep(request)
        if u.get("role") not in ("superadmin", "admin"):
            raise HTTPException(status_code=403, detail="Superadmin only")
        return u

    app.include_router(verval_mod.build_router(db, current_user_dep), prefix="/api")
    app.include_router(sosial_mod.build_router(db, current_user_dep, editor_dep, admin_dep), prefix="/api")

    monkeypatch.setattr(server_mod, "db", db)
    client = TestClient(app)

    return {
        "app": app, "client": client, "db": db, "users": users,
        "refs": {"b1": ref_b1, "b2": ref_b2, "ka": ref_ka, "tl": ref_tl},
    }


def _hdr(who: str) -> dict:
    return {"X-Test-User": who}


# ===================================================================== Tests
def test_1_kelurahan_fallback_ketika_rtrw_kosong_dan_blokir_lintas_kelurahan(env):
    c, refs = env["client"], env["refs"]
    r = c.get("/api/verval/sasaran", headers=_hdr("rt1"))
    assert r.status_code == 200
    items = {i["dtsen_ref"]: i for i in r.json()["items"]}
    # RT 1 di Bonto Lebang dapat melihat warga Bonto Lebang walau rw="" di DTSEN
    assert refs["b1"] in items and refs["b2"] in items
    assert items[refs["b1"]]["dasar_akses"] == "kelurahan_tanpa_rtrw"
    # Detail lengkap (No. KK tidak tersamar) terlihat di wilayahnya
    assert items[refs["b1"]]["no_kk"] == "7371010101010001"
    assert items[refs["b1"]]["no_kk_tersamar"] is False
    # Lintas kelurahan & kecamatan tetap diblokir 404
    assert refs["ka"] not in items and refs["tl"] not in items
    assert c.get(f"/api/verval/sasaran/{refs['ka']}", headers=_hdr("rt1")).status_code == 404
    assert c.post("/api/verval/records", headers=_hdr("rt1"),
                  json={"dtsen_ref": refs["ka"], "client_uuid": uuid.uuid4().hex}).status_code == 404


def test_2_watermark_jpg_strip_exif_dan_tanpa_nik_atau_nama_warga(env):
    c, refs, users = env["client"], env["refs"], env["users"]
    rec = c.post("/api/verval/records", headers=_hdr("rt1"),
                 json={"dtsen_ref": refs["b1"], "client_uuid": uuid.uuid4().hex}).json()
    rid = rec["id"]

    # Simpan identitas lapangan dengan NIK & nama warga, lalu lengkapi formulir
    upd = c.put(f"/api/verval/records/{rid}", headers=_hdr("rt1"), json={
        "identitas_lapangan": {"nik": "7371001122334455", "rw": "1", "rt": "1"},
        "indikator": _valid_indikator(),
        "kesimpulan": {"pilihan": "ditemukan_sesuai", "catatan": ""},
    })
    assert upd.status_code == 200

    wm = verval_mod.build_watermark_lines(
        upd.json(), users["rt1"], {"lat": -5.145, "lng": 119.431, "akurasi_m": 18.0}, "2026-11-19T07:00:00Z"
    )
    joined = "\n".join(wm)
    assert "7371001122334455" not in joined and "BUDI SANTOSO" not in joined
    assert "-5.145000, 119.431000" in joined and "WITA" in joined and "Bonto Lebang" in joined and "Ketua RT 01" in joined

    raw_img = _make_jpeg(color=(210, 230, 245), size=(640, 480), with_exif_gps=True)
    up = c.post(
        f"/api/verval/records/{rid}/foto",
        headers=_hdr("rt1"),
        files={"file": ("cam.jpg", raw_img, "image/jpeg")},
        data={"client_foto_id": uuid.uuid4().hex, "jenis": "rumah_depan",
              "lat": "-5.145", "lng": "119.431", "akurasi_m": "18", "sumber_kamera": "kamera_web_langsung"},
    )
    assert up.status_code == 200
    fid = up.json()["foto"][0]["id"]
    assert up.json()["foto"][0]["watermark"] is True

    foto_resp = c.get(f"/api/verval/foto/{fid}", headers=_hdr("rt1"))
    assert foto_resp.status_code == 200 and foto_resp.headers["content-type"] == "image/jpeg"
    saved = Image.open(io.BytesIO(foto_resp.content))
    # EXIF GPS terbuang saat re-encode JPEG
    assert not (saved.getexif().get_ifd(0x8825) if saved.getexif() else {})
    # Banner gelap watermark di bagian bawah gambar lebih gelap daripada bagian atas yang cerah
    top_luma = sum(saved.getpixel((320, 10))) / 3.0
    bot_luma = sum(saved.getpixel((320, 470))) / 3.0
    assert bot_luma < top_luma - 50


def test_3_batas_gps_30m_dan_pin_manual_beralasan(env):
    c, refs = env["client"], env["refs"]
    # Konfigurasi default sekarang 30 m
    cfg_resp = c.get("/api/verval/konfigurasi", headers=_hdr("rt1"))
    assert cfg_resp.status_code == 200 and cfg_resp.json()["gps_max_akurasi_m"] == 30.0

    rec = c.post("/api/verval/records", headers=_hdr("rt1"),
                 json={"dtsen_ref": refs["b1"], "client_uuid": uuid.uuid4().hex}).json()
    rid = rec["id"]
    c.put(f"/api/verval/records/{rid}", headers=_hdr("rt1"), json={
        "indikator": _valid_indikator(), "kesimpulan": {"pilihan": "ditemukan_sesuai"},
    })
    c.post(f"/api/verval/records/{rid}/foto", headers=_hdr("rt1"),
           files={"file": ("cam.jpg", _make_jpeg(), "image/jpeg")},
           data={"client_foto_id": uuid.uuid4().hex})

    # Akurasi 35 m > 30 m -> ditolak saat kirim
    g35 = c.put(f"/api/verval/records/{rid}", headers=_hdr("rt1"), json={
        "gps": {"lat": -5.145, "lng": 119.431, "akurasi_m": 35.0, "izin": "granted"},
    })
    assert g35.status_code == 200 and g35.json()["gps"]["status_gps"] == "akurasi_rendah"
    assert c.post(f"/api/verval/records/{rid}/kirim", headers=_hdr("rt1")).status_code == 422

    # Akurasi 28 m <= 30 m -> memenuhi!
    g28 = c.put(f"/api/verval/records/{rid}", headers=_hdr("rt1"), json={
        "gps": {"lat": -5.145, "lng": 119.431, "akurasi_m": 28.0, "izin": "granted"},
    })
    assert g28.status_code == 200 and g28.json()["gps"]["status_gps"] == "memenuhi"

    # Pin manual tanpa alasan / di luar Makassar -> 422
    assert c.put(f"/api/verval/records/{rid}", headers=_hdr("rt1"), json={
        "gps": {"lat": -5.145, "lng": 119.431, "sumber": "pin_manual", "alasan_manual": "ok"},
    }).status_code == 422
    assert c.put(f"/api/verval/records/{rid}", headers=_hdr("rt1"), json={
        "gps": {"lat": -6.2, "lng": 106.8, "sumber": "pin_manual", "alasan_manual": "Sinyal lorong lemah"},
    }).status_code == 422

    # Pin manual valid -> memenuhi kirim!
    gm = c.put(f"/api/verval/records/{rid}", headers=_hdr("rt1"), json={
        "gps": {"lat": -5.146, "lng": 119.432, "akurasi_m": 42.0, "sumber": "pin_manual",
                "alasan_manual": "Sinyal GPS di lorong sempit di atas 30 meter"},
    })
    assert gm.status_code == 200 and gm.json()["gps"]["status_gps"] == "pin_manual"
    k = c.post(f"/api/verval/records/{rid}/kirim", headers=_hdr("rt1"))
    assert k.status_code == 200 and k.json()["status"] == "menunggu_kelurahan"


def test_4_alur_2_tahap_visibilitas_role_dan_sinkron_sistem(env):
    c, db, refs = env["client"], env["db"], env["refs"]
    rec = c.post("/api/verval/records", headers=_hdr("rt1"),
                 json={"dtsen_ref": refs["b1"], "client_uuid": uuid.uuid4().hex}).json()
    rid = rec["id"]

    c.put(f"/api/verval/records/{rid}", headers=_hdr("rt1"), json={
        "identitas_lapangan": {"nik": "7371001122334455", "rw": "1", "rt": "1", "desil_usulan": 6},
        "indikator": _valid_indikator(),
        "anggota_rentan": [{"id": "a1", "nik": "7371001122339999", "nama": "ANI", "status_hubungan": "istri",
                            "kondisi_rentan": ["pelaku_usaha_mikro"], "rekomendasi_opd": "Diskop UKM"}],
        "kesimpulan": {"pilihan": "graduasi_mandiri", "catatan": "Ekonomi warga sudah membaik"},
        "gps": {"lat": -5.141, "lng": 119.421, "akurasi_m": 15.0, "izin": "granted"},
    })
    c.post(f"/api/verval/records/{rid}/foto", headers=_hdr("rt1"),
           files={"file": ("cam.jpg", _make_jpeg(), "image/jpeg")},
           data={"client_foto_id": uuid.uuid4().hex})
    sub = c.post(f"/api/verval/records/{rid}/kirim", headers=_hdr("rt1"))
    assert sub.status_code == 200 and sub.json()["status"] == "menunggu_kelurahan"

    # Visibilitas antar role pada record terkirim:
    assert c.get(f"/api/verval/records/{rid}", headers=_hdr("rw1")).status_code == 200  # Ketua RW pantau RT 1
    assert c.get(f"/api/verval/records/{rid}", headers=_hdr("rt2")).status_code == 404  # RT 2 terblokir
    assert c.get(f"/api/verval/records/{rid}", headers=_hdr("kel_karang")).status_code == 404  # Kelurahan lain terblokir
    assert c.get(f"/api/verval/records/{rid}", headers=_hdr("kec_tallo")).status_code == 404  # Kecamatan lain terblokir
    kel_detail = c.get(f"/api/verval/records/{rid}", headers=_hdr("kel_bonto"))
    assert kel_detail.status_code == 200 and kel_detail.json()["sasaran"]["no_kk"] == "7371010101010001"
    assert c.get(f"/api/verval/records/{rid}", headers=_hdr("bappeda")).status_code == 200

    # Kecamatan TIDAK boleh melangkahi Kelurahan sebelum tahap 1 selesai
    assert c.post(f"/api/verval/records/{rid}/review", headers=_hdr("kec_mamajang"),
                  json={"keputusan": "disetujui", "catatan": "skip"}).status_code == 409
    # Kelurahan TIDAK boleh memutus akhir 'disetujui'
    assert c.post(f"/api/verval/records/{rid}/review", headers=_hdr("kel_bonto"),
                  json={"keputusan": "disetujui", "catatan": "ok"}).status_code == 403

    # Kelurahan kembalikan -> RT/RW perbaiki & kirim ulang -> Kelurahan teruskan ke Kecamatan
    r_back = c.post(f"/api/verval/records/{rid}/review", headers=_hdr("kel_bonto"),
                    json={"keputusan": "perlu_perbaikan", "catatan": "Lengkapi jumlah anggota"})
    assert r_back.status_code == 200 and r_back.json()["status"] == "perlu_perbaikan"
    c.put(f"/api/verval/records/{rid}", headers=_hdr("rt1"), json={
        "identitas_lapangan": {"jumlah_anggota_keluarga": 5},
    })
    assert c.post(f"/api/verval/records/{rid}/kirim", headers=_hdr("rt1")).json()["status"] == "menunggu_kelurahan"

    r_fwd = c.post(f"/api/verval/records/{rid}/review", headers=_hdr("kel_bonto"),
                   json={"keputusan": "teruskan_kecamatan", "catatan": "Sudah sesuai"})
    assert r_fwd.status_code == 200 and r_fwd.json()["status"] == "menunggu_kecamatan"

    # Data utama belum berubah sebelum persetujuan akhir Kecamatan
    hh_before = db.households.find_one({"id": "hh-b1"})
    assert asyncio_run(hh_before)["nik"] == ""

    # Persetujuan akhir Kecamatan -> sinkron ke sistem + menjaga dtsen_awal!
    r_fin = c.post(f"/api/verval/records/{rid}/review", headers=_hdr("kec_mamajang"),
                   json={"keputusan": "disetujui", "catatan": "Disahkan Camat"})
    assert r_fin.status_code == 200
    body_fin = r_fin.json()
    assert body_fin["status"] == "disetujui" and body_fin["sinkron_sistem"]["disinkronkan"] is True

    hh_after = asyncio_run(db.households.find_one({"id": "hh-b1"}))
    assert hh_after["nik"] == "7371001122334455"
    assert hh_after["rw"] == "1" and hh_after["rt"] == "1"
    assert hh_after["desil_nasional"] == 6
    assert hh_after["hunian_rentan"] is True and hh_after["rumah_rentan"] is True
    assert hh_after["lat"] == -5.141 and hh_after["verval_status"] == "disetujui"
    # Nilai awal DTSEN tetap utuh di dtsen_awal!
    assert hh_after["dtsen_awal"]["nik"] == ""
    assert hh_after["dtsen_awal"]["rw"] == ""
    assert hh_after["dtsen_awal"]["desil_nasional"] == 1
    assert hh_after["dtsen_awal"]["hunian_rentan"] is False

    # household_members & village_stats + district_stats ikut diperbarui
    members = asyncio_run(db.household_members.find({"household_id": "hh-b1"}).to_list(20))
    assert any(m.get("nik") == "7371001122334455" for m in members)
    assert any(m.get("nik") == "7371001122339999" and m.get("nama") == "ANI" for m in members)
    vs = asyncio_run(db.village_stats.find_one({"id": "7371010001"}))
    ds = asyncio_run(db.district_stats.find_one({"id": "737101"}))
    assert vs["total_households"] == 2 and ds["total_households"] == 2


def test_5_daftar_warga_baru_2_tahap_dan_masuk_households_setelah_acc(env):
    c, db, _ = env["client"], env["db"], env["users"]

    # Duplikat No. KK di kelurahan yang sama -> 409
    assert c.post("/api/verval/warga-baru", headers=_hdr("rt1"), json={
        "client_uuid": uuid.uuid4().hex, "no_kk": "7371010101010001", "nik": "7371019999990001",
        "kepala_keluarga": "BUDI SANTOSO", "alamat": "JL VETERAN", "rw": "1", "rt": "1",
    }).status_code == 409

    # RT 1 mencoba daftar untuk RT 2 -> 403
    assert c.post("/api/verval/warga-baru", headers=_hdr("rt1"), json={
        "client_uuid": uuid.uuid4().hex, "no_kk": "7371010101990001", "nik": "7371019999990001",
        "kepala_keluarga": "WARGA RT 2", "alamat": "JL BARU 2", "rw": "1", "rt": "2",
    }).status_code == 403

    # Pendaftaran valid oleh RT 1
    wb = c.post("/api/verval/warga-baru", headers=_hdr("rt1"), json={
        "client_uuid": uuid.uuid4().hex, "no_kk": "7371010101990001", "nik": "7371019999990001",
        "kepala_keluarga": "ANDI WARGA BARU", "alamat": "JL LORONG BARU 88",
        "rw": "1", "rt": "1", "jumlah_anggota_keluarga": 3, "desil_usulan": 2,
    })
    assert wb.status_code == 200
    rec = wb.json()
    rid, ref_baru = rec["id"], rec["dtsen_ref"]
    assert rec["jenis_verval"] == "warga_baru"
    # Belum masuk households sebelum Kecamatan approve
    assert asyncio_run(db.households.find_one({"dtsen_ref": ref_baru})) is None

    # Dapat dibuka via /sasaran/{ref} dan /records/{rid}, lalu diisi & kirim
    assert c.get(f"/api/verval/sasaran/{ref_baru}", headers=_hdr("rt1")).status_code == 200
    ind_baru = {k: {"kondisi_riil": v["kondisi_riil"], "catatan": v["catatan"]} for k, v in _valid_indikator().items()}
    c.put(f"/api/verval/records/{rid}", headers=_hdr("rt1"), json={
        "indikator": ind_baru,
        "kesimpulan": {"pilihan": "ditemukan_sesuai"},
        "gps": {"lat": -5.142, "lng": 119.422, "akurasi_m": 20.0, "izin": "granted"},
    })
    c.post(f"/api/verval/records/{rid}/foto", headers=_hdr("rt1"),
           files={"file": ("cam.jpg", _make_jpeg(), "image/jpeg")},
           data={"client_foto_id": uuid.uuid4().hex})
    assert c.post(f"/api/verval/records/{rid}/kirim", headers=_hdr("rt1")).json()["status"] == "menunggu_kelurahan"
    assert c.post(f"/api/verval/records/{rid}/review", headers=_hdr("kel_bonto"),
                  json={"keputusan": "teruskan_kecamatan"}).json()["status"] == "menunggu_kecamatan"

    fin = c.post(f"/api/verval/records/{rid}/review", headers=_hdr("kec_mamajang"),
                 json={"keputusan": "disetujui"})
    assert fin.status_code == 200 and fin.json()["sinkron_sistem"]["jenis"] == "warga_baru_didaftarkan"

    baru_hh = asyncio_run(db.households.find_one({"dtsen_ref": ref_baru}))
    assert baru_hh is not None and baru_hh["nik"] == "7371019999990001" and baru_hh["warga_baru_verval"] is True
    assert baru_hh["dtsen_awal"] is None
    vs = asyncio_run(db.village_stats.find_one({"id": "7371010001"}))
    assert vs["total_households"] == 3


def test_6_kecamatan_kelola_user_dan_penugasan_terscope(env):
    c, users = env["client"], env["users"]
    # Kecamatan (operator Mamajang) dapat mengelola /verval/penugasan Mamajang saja
    ops = c.get("/api/verval/operator", headers=_hdr("kec_mamajang")).json()["items"]
    assert all(o["wilayah"] == "Mamajang" for o in ops) and len(ops) == 3

    # Tidak boleh menetapkan penugasan di Kecamatan Tallo
    assert c.post("/api/verval/penugasan", headers=_hdr("kec_mamajang"), json={
        "user_id": users["rt1"]["id"], "kode_kelurahan": "7371050001", "rw": "1",
    }).status_code == 403
    assert c.post("/api/verval/sasaran-kk", headers=_hdr("kec_mamajang"), json={
        "user_id": users["rt1"]["id"], "household_id": "hh-tl", "dasar_penugasan": "SK Test",
    }).status_code == 403

    # Test manajemen user Kecamatan via server endpoints directly on FakeDB
    req_kec = server_mod.AdminCreateUser(
        email="baru.kel@example.com", password="PasswordAman123",
        name="Lurah Baru", role="operator_kelurahan", wilayah="Tallo", kelurahan="Bonto Lebang",
    )
    res_kel = asyncio_run(server_mod.admin_create_user(req_kec, admin=users["kec_mamajang"]))
    assert res_kel["role"] == "operator_kelurahan" and res_kel["wilayah"] == "Mamajang" and res_kel["kelurahan"] == "Bonto Lebang"

    # Kecamatan dilarang membuat akun superadmin
    with pytest.raises(HTTPException) as exc:
        asyncio_run(server_mod.admin_create_user(
            server_mod.AdminCreateUser(
                email="hacker@example.com", password="PasswordAman123",
                name="Bad", role="superadmin", wilayah="Mamajang",
            ),
            admin=users["kec_mamajang"],
        ))
    assert exc.value.status_code == 403


def asyncio_run(coro):
    import asyncio
    return asyncio.run(coro)
