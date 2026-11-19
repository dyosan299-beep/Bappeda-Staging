"""Pengujian modul GeoTag-Verval DTSEN (Operator RT/RW) dengan data UJI sintetis.

Jalankan:  cd /app && VERVAL_IZINKAN_DATA_UJI=true python -m pytest tests/test_verval_geotag.py -q
Membutuhkan backend berjalan (BASE_URL, default http://localhost:8001) & kredensial uji di env:
TEST_ADMIN_PASSWORD, TEST_PETUGAS_PASSWORD, TEST_OPERATOR_PASSWORD, TEST_VERIFIKATOR_PASSWORD.
Data UJI dibuat di awal dan DIHAPUS di akhir (hanya data bertanda UJI).
"""
import io
import os
import subprocess
import sys
import uuid

import pytest
import requests
from PIL import Image

BASE = os.environ.get("BASE_URL", "http://localhost:8001").rstrip("/") + "/api"
ROOT = os.path.dirname(os.path.dirname(os.path.abspath(__file__)))
UJI_PW = os.environ.get("VERVAL_UJI_PASSWORD")
if not UJI_PW:
    pytest.skip("VERVAL_UJI_PASSWORD belum di-set — lewati tes Verval GeoTag.", allow_module_level=True)
D = "@uji-verval.example.com"


def run_script(cmd):
    env = dict(os.environ, VERVAL_IZINKAN_DATA_UJI="true")
    out = subprocess.run([sys.executable, os.path.join(ROOT, "scripts", "verval_data_uji.py"), cmd],
                         capture_output=True, text=True, env=env, cwd=ROOT)
    assert out.returncode == 0, out.stderr
    return out.stdout


def login(email, pw):
    s = requests.Session()
    r = s.post(f"{BASE}/auth/login", json={"email": email, "password": pw})
    assert r.status_code == 200, (email, r.text)
    return s


def jpeg(color=(120, 80, 40)):
    b = io.BytesIO()
    Image.new("RGB", (64, 48), color).save(b, "JPEG")
    return b.getvalue()


@pytest.fixture(scope="module")
def ctx():
    run_script("hapus")
    run_script("seed")
    c = {
        "a": login("op.rtrw.a" + D, UJI_PW), "b": login("op.rtrw.b" + D, UJI_PW), "c": login("op.rtrw.c" + D, UJI_PW),
        "admin": login("admin@bappeda.makassarkota.go.id", os.environ["TEST_ADMIN_PASSWORD"]),
        "petugas": login("petugas.tallo@makassarkota.go.id", os.environ["TEST_PETUGAS_PASSWORD"]),
        "operator": login("operator.rappocini@makassarkota.go.id", os.environ["TEST_OPERATOR_PASSWORD"]),
        "verif": login("verifikator@bappeda.makassarkota.go.id", os.environ["TEST_VERIFIKATOR_PASSWORD"]),
        "anon": requests.Session(),
    }
    hh = c["admin"].get(f"{BASE}/sosial/households", params={"size": 200}).json()["items"]
    c["hh"] = {h["no_kk"]: h for h in hh if str(h.get("no_kk", "")).startswith("9999")}
    ops = c["admin"].get(f"{BASE}/verval/operator").json()["items"]
    c["uid"] = {o["email"].split("@")[0]: o["id"] for o in ops}
    yield c
    print(run_script("hapus"))


def refs(sess):
    r = sess.get(f"{BASE}/verval/sasaran", params={"size": 100})
    assert r.status_code == 200, r.text
    return {i["dtsen_ref"]: i for i in r.json()["items"]}


def ref_of(c, kk):
    return c["hh"][kk]["dtsen_ref"]


# ---------------------------------------------------------------- cakupan wilayah
def test_ref_stabil_dan_kk_tidak_bocor(ctx):
    assert len(ctx["hh"]) == 6
    for kk, h in ctx["hh"].items():
        assert h["dtsen_ref"].startswith("DR-") and kk not in h["dtsen_ref"]


def test_operator_hanya_sasaran_penugasan(ctx):
    a = refs(ctx["a"])
    assert set(a) == {ref_of(ctx, "9999000000000101"), ref_of(ctx, "9999000000000102")}
    assert all(i["no_kk_tersamar"] and "*" in i["no_kk"] for i in a.values())
    assert set(refs(ctx["b"])) == {ref_of(ctx, "9999000000000201")}
    assert refs(ctx["c"]) == {}


def test_manipulasi_id_lintas_wilayah_ditolak(ctx):
    other = ref_of(ctx, "9999000000000201")
    assert ctx["a"].get(f"{BASE}/verval/sasaran/{other}").status_code == 404
    r = ctx["a"].post(f"{BASE}/verval/records", json={"dtsen_ref": other, "client_uuid": uuid.uuid4().hex})
    assert r.status_code == 404
    assert ctx["a"].get(f"{BASE}/verval/sasaran/DR-{'0' * 40}").status_code == 404
    hid = ctx["hh"]["9999000000000201"]["id"]
    assert ctx["a"].get(f"{BASE}/sosial/households/{hid}").status_code == 404
    lst = ctx["a"].get(f"{BASE}/sosial/households", params={"size": 100}).json()
    assert lst["total"] == 2 and lst["masked"] is True


def test_operator_rtrw_tidak_bisa_akses_modul_lain(ctx):
    for path in ("/inquiries", "/admin/users", "/verval/penugasan"):
        assert ctx["a"].get(f"{BASE}{path}").status_code == 403, path


def test_peran_lain_tidak_bisa_geotag(ctx):
    ref = ref_of(ctx, "9999000000000101")
    for who in ("admin", "petugas", "operator", "verif"):
        s = ctx[who]
        assert s.get(f"{BASE}/verval/sasaran").status_code == 403, who
        r = s.post(f"{BASE}/verval/records", json={"dtsen_ref": ref, "client_uuid": uuid.uuid4().hex})
        assert r.status_code == 403, who
    assert ctx["anon"].post(f"{BASE}/verval/records", json={"dtsen_ref": ref, "client_uuid": "x" * 10}).status_code == 401


def test_households_dibatasi_wilayah_peran_existing(ctx):
    pet = ctx["petugas"].get(f"{BASE}/sosial/households", params={"size": 200}).json()["items"]
    assert pet and all(i["kecamatan"] == "Tallo" for i in pet)
    hid = ctx["hh"]["9999000000000301"]["id"]  # Rappocini
    assert ctx["petugas"].get(f"{BASE}/sosial/households/{hid}").status_code == 404
    op = ctx["operator"].get(f"{BASE}/sosial/households", params={"size": 200}).json()["items"]
    assert op and all(i["kecamatan"] == "Rappocini" for i in op)
    assert ctx["operator"].get(f"{BASE}/sosial/households/{hid}").status_code == 200
    assert ctx["anon"].get(f"{BASE}/sosial/households/{hid}").status_code == 401
    assert ctx["admin"].get(f"{BASE}/sosial/households/{hid}").json()["no_kk"] == "9999000000000301"


# ---------------------------------------------------------------- alur Verval
def test_alur_lengkap_verval(ctx):
    a, ref = ctx["a"], ref_of(ctx, "9999000000000101")
    cu = uuid.uuid4().hex
    r1 = a.post(f"{BASE}/verval/records", json={"dtsen_ref": ref, "client_uuid": cu}).json()
    r2 = a.post(f"{BASE}/verval/records", json={"dtsen_ref": ref, "client_uuid": cu}).json()
    r3 = a.post(f"{BASE}/verval/records", json={"dtsen_ref": ref, "client_uuid": uuid.uuid4().hex}).json()
    assert r1["id"] == r2["id"] == r3["id"] and r1["status"] == "draft"
    rid = r1["id"]
    ctx["rid"] = rid

    # kirim kosong ditolak
    k = a.post(f"{BASE}/verval/records/{rid}/kirim")
    assert k.status_code == 422 and len(k.json()["detail"]["masalah"]) >= 3

    # GPS: izin ditolak / akurasi rendah / memenuhi (<= 5 m)
    g = a.put(f"{BASE}/verval/records/{rid}", json={"gps": {"izin": "denied", "galat": "PERMISSION_DENIED"}}).json()
    assert g["gps"]["status_gps"] == "izin_ditolak"
    g = a.put(f"{BASE}/verval/records/{rid}", json={"gps": {"lat": -5.11, "lng": 119.43, "akurasi_m": 12, "izin": "granted"}}).json()
    assert g["gps"]["status_gps"] == "akurasi_rendah" and g["gps"]["terverifikasi"] is False

    # unggah foto SEBELUM form lengkap => DITOLAK (gating baru)
    sebelum = a.post(f"{BASE}/verval/records/{rid}/foto", files={"file": ("r.jpg", jpeg(), "image/jpeg")},
                     data={"client_foto_id": uuid.uuid4().hex, "jenis": "rumah_depan"})
    assert sebelum.status_code == 422
    assert "Form Verval" in sebelum.json()["detail"]["msg"]

    # isi Form Verval komprehensif: 11 variabel + kesimpulan
    ind = {k: {"kesesuaian": "sesuai", "kondisi_riil": "sesuai", "catatan": ""} for k in
           ("no_kk", "nama_krt", "jumlah_anggota", "pln", "kepemilikan_rumah")}
    ind["status_desil"] = {"kesesuaian": "tetap", "kondisi_riil": "tetap", "catatan": ""}
    ind["pbi_jkn"] = {"kesesuaian": "aktif", "kondisi_riil": "aktif", "catatan": ""}
    ind["fisik_rumah"] = {"kesesuaian": "rlh", "kondisi_riil": "layak", "catatan": ""}
    ind["air_minum"] = {"kesesuaian": "layak", "kondisi_riil": "layak", "catatan": ""}
    ind["sanitasi"] = {"kesesuaian": "odf", "kondisi_riil": "odf", "catatan": ""}
    ind["aset_pekerjaan"] = {"kesesuaian": "cukup", "kondisi_riil": "cukup", "catatan": ""}
    a.put(f"{BASE}/verval/records/{rid}", json={
        "indikator": ind,
        "kesimpulan": {"pilihan": "ditemukan_sesuai", "catatan": ""},
    })

    # dedup client_foto_id & tolak non-gambar
    bad = a.post(f"{BASE}/verval/records/{rid}/foto", files={"file": ("x.jpg", b"bukan gambar", "image/jpeg")},
                 data={"client_foto_id": uuid.uuid4().hex})
    assert bad.status_code == 400
    fid = uuid.uuid4().hex
    up = a.post(f"{BASE}/verval/records/{rid}/foto", files={"file": ("r.jpg", jpeg(), "image/jpeg")},
                data={"client_foto_id": fid, "jenis": "rumah_depan"}).json()
    assert up["duplikat"] is False and len(up["foto"]) == 1
    up2 = a.post(f"{BASE}/verval/records/{rid}/foto", files={"file": ("r.jpg", jpeg(), "image/jpeg")},
                 data={"client_foto_id": fid}).json()
    up3 = a.post(f"{BASE}/verval/records/{rid}/foto", files={"file": ("r.jpg", jpeg(), "image/jpeg")},
                 data={"client_foto_id": uuid.uuid4().hex}).json()
    assert up2["duplikat"] and up3["duplikat"] and len(up3["foto"]) == 1
    ctx["foto_id"] = up["foto"][0]["id"]

    # kirim: GPS masih rendah -> 422
    k = a.post(f"{BASE}/verval/records/{rid}/kirim")
    assert k.status_code == 422
    msg = " ".join(k.json()["detail"]["masalah"])
    assert "GPS" in msg

    # ubah salah satu variabel menjadi "beda" tanpa catatan -> harus 422
    ind2 = dict(ind)
    ind2["fisik_rumah"] = {"kesesuaian": "rtlh", "kondisi_riil": "tidak_layak", "catatan": ""}
    a.put(f"{BASE}/verval/records/{rid}", json={"indikator": ind2,
                                                  "gps": {"lat": -5.1105, "lng": 119.4301, "akurasi_m": 3.5, "izin": "granted"}})
    k = a.post(f"{BASE}/verval/records/{rid}/kirim")
    assert k.status_code == 422
    assert "catatan" in " ".join(k.json()["detail"]["masalah"]).lower()

    # beri catatan -> boleh kirim
    ind2["fisik_rumah"]["catatan"] = "Atap seng rapuh; dinding kayu lapuk; lantai tanah"
    a.put(f"{BASE}/verval/records/{rid}", json={"indikator": ind2})
    k = a.post(f"{BASE}/verval/records/{rid}/kirim")
    assert k.status_code == 200 and k.json()["status"] == "terkirim" and k.json()["tanda_terima"].startswith("VV-")
    k2 = a.post(f"{BASE}/verval/records/{rid}/kirim")
    assert k2.status_code == 200 and k2.json()["idempoten"] is True
    assert a.put(f"{BASE}/verval/records/{rid}", json={"catatan_umum": "x"}).status_code == 409


def test_akses_foto_terotorisasi(ctx):
    url = f"{BASE}/verval/foto/{ctx['foto_id']}"
    assert ctx["a"].get(url).status_code == 200
    assert ctx["a"].get(url).headers["content-type"] == "image/jpeg"
    assert ctx["verif"].get(url).status_code == 200
    for who in ("b", "admin", "petugas"):
        assert ctx[who].get(url).status_code == 404, who
    assert ctx["anon"].get(url).status_code == 401
    assert ctx["b"].get(f"{BASE}/verval/records/{ctx['rid']}").status_code == 404


def test_review_dan_data_sumber_tidak_berubah(ctx):
    rid, hid = ctx["rid"], ctx["hh"]["9999000000000101"]["id"]
    before = ctx["admin"].get(f"{BASE}/sosial/households/{hid}").json()
    assert ctx["admin"].post(f"{BASE}/verval/records/{rid}/review", json={"keputusan": "disetujui"}).status_code == 403
    assert ctx["a"].post(f"{BASE}/verval/records/{rid}/review", json={"keputusan": "disetujui"}).status_code == 403
    v = ctx["verif"]
    assert v.post(f"{BASE}/verval/records/{rid}/review", json={"keputusan": "perlu_perbaikan"}).status_code == 422
    r = v.post(f"{BASE}/verval/records/{rid}/review", json={"keputusan": "perlu_perbaikan", "catatan": "Foto samping rumah"})
    assert r.status_code == 200 and r.json()["status"] == "perlu_perbaikan"
    up = ctx["a"].post(f"{BASE}/verval/records/{rid}/foto", files={"file": ("s.jpg", jpeg((10, 200, 10)), "image/jpeg")},
                       data={"client_foto_id": uuid.uuid4().hex, "jenis": "rumah_samping"})
    assert up.status_code == 200
    assert ctx["a"].post(f"{BASE}/verval/records/{rid}/kirim").status_code == 200
    r = v.post(f"{BASE}/verval/records/{rid}/review", json={"keputusan": "disetujui", "catatan": "OK"})
    assert r.status_code == 200 and r.json()["status"] == "disetujui"
    aksi = [x["aksi"] for x in r.json()["riwayat"]]
    assert aksi == ["buat_draft", "kirim", "review", "kirim", "review"]
    after = ctx["admin"].get(f"{BASE}/sosial/households/{hid}").json()
    for f in ("jenis_atap_terluas", "alamat", "jumlah_anggota_keluarga", "risk_score"):
        assert before[f] == after[f]


def test_peta_satu_sumber_dan_hak_akses(ctx):
    pa = ctx["a"].get(f"{BASE}/verval/peta").json()
    pv = ctx["verif"].get(f"{BASE}/verval/peta").json()
    pp = ctx["admin"].get(f"{BASE}/verval/peta").json()
    assert pa["mode"] == pv["mode"] == "titik" and pp["mode"] == "agregat"
    assert ctx["rid"] in {t["id"] for t in pa["titik"]} and ctx["rid"] in {t["id"] for t in pv["titik"]}
    assert "lat" not in str(pp["kelurahan"]) and "kepala" not in str(pv["titik"])
    assert pp["integrasi_bangunan"]["tersedia"] is False
    assert ctx["anon"].get(f"{BASE}/verval/peta").status_code == 401
    assert ctx["b"].get(f"{BASE}/verval/peta").json()["titik"] == []


# ---------------------------------------------------------------- penugasan & sasaran KK
def test_sasaran_kk_dan_lintas_wilayah(ctx):
    adm, uid = ctx["admin"], ctx["uid"]["op.rtrw.a"]
    assert ctx["verif"].post(f"{BASE}/verval/sasaran-kk", json={"user_id": uid}).status_code == 403
    s1 = adm.post(f"{BASE}/verval/sasaran-kk", json={"user_id": uid, "household_id": ctx["hh"]["9999000000000104"]["id"]})
    assert s1.status_code == 200 and s1.json()["lintas_wilayah"] is False
    assert ref_of(ctx, "9999000000000104") in refs(ctx["a"])
    hid301 = ctx["hh"]["9999000000000301"]["id"]
    assert adm.post(f"{BASE}/verval/sasaran-kk", json={"user_id": uid, "household_id": hid301}).status_code == 422
    s2 = adm.post(f"{BASE}/verval/sasaran-kk", json={"user_id": uid, "household_id": hid301,
                                                      "dasar_penugasan": "SK Lurah No. UJI/01/2026"})
    assert s2.status_code == 200 and s2.json()["lintas_wilayah"] is True
    a = refs(ctx["a"])
    assert a[ref_of(ctx, "9999000000000301")]["dasar_akses"] == "lintas_wilayah"
    assert adm.post(f"{BASE}/verval/sasaran-kk/{s2.json()['id']}/cabut", json={"alasan": "selesai uji"}).status_code == 200
    assert ref_of(ctx, "9999000000000301") not in refs(ctx["a"])
    # operator bukan operator_rt_rw tidak bisa diberi penugasan
    bad = adm.post(f"{BASE}/verval/penugasan", json={"user_id": ctx["uid"]["op.rtrw.a"].replace("a", "b", 1),
                                                     "kode_kelurahan": "9900000001", "rw": "2"})
    assert bad.status_code == 400


def test_cabut_penugasan_menghentikan_akses(ctx):
    adm, uid = ctx["admin"], ctx["uid"]["op.rtrw.b"]
    ref = ref_of(ctx, "9999000000000201")
    rec = ctx["b"].post(f"{BASE}/verval/records", json={"dtsen_ref": ref, "client_uuid": uuid.uuid4().hex}).json()
    pen = [p for p in adm.get(f"{BASE}/verval/penugasan", params={"user_id": uid}).json()["penugasan"] if p["status"] == "aktif"]
    assert adm.post(f"{BASE}/verval/penugasan/{pen[0]['id']}/cabut", json={"alasan": "uji pencabutan"}).status_code == 200
    assert ctx["b"].put(f"{BASE}/verval/records/{rec['id']}", json={"catatan_umum": "x"}).status_code == 403
    assert refs(ctx["b"]) == {}


def test_etl_reset_relasi_tetap(ctx):
    old_hid = ctx["hh"]["9999000000000101"]["id"]
    run_script("simulasi-reset")
    d = ctx["a"].get(f"{BASE}/verval/records/{ctx['rid']}").json()
    assert d["sasaran"] is not None and d["household_id_terkini"] != old_hid
    assert d["household_id_saat_verval"] == old_hid
    assert ref_of(ctx, "9999000000000101") in refs(ctx["a"])


def test_audit_log_tercatat(ctx):
    r = ctx["admin"].get(f"{BASE}/inklusi/audit-logs", params={"aksi": "verval_kirim", "size": 50}).json()
    assert r["total"] >= 2
    r = ctx["admin"].get(f"{BASE}/inklusi/audit-logs", params={"aksi": "verval_akses_lintas_ditolak"}).json()
    assert r["total"] >= 1
    assert "9999000000000" not in str(r["items"])  # No. KK tidak masuk log
