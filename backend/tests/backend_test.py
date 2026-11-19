"""Backend API tests - Sistem Intelijen Data Bappeda Kota Makassar."""
import os
import re
from pathlib import Path

import pytest
import requests
from dotenv import dotenv_values

frontend_env = dotenv_values("/app/frontend/.env")
base_url = os.environ.get("REACT_APP_BACKEND_URL") or frontend_env.get("REACT_APP_BACKEND_URL")
if not base_url:
    raise RuntimeError("REACT_APP_BACKEND_URL missing")
BASE_URL = base_url.rstrip("/")
API = f"{BASE_URL}/api"


@pytest.fixture(scope="session")
def test_credentials():
    p = Path("/app/memory/test_credentials.md")
    if not p.exists():
        pytest.skip("missing test_credentials.md")
    c = p.read_text(encoding="utf-8")
    em = re.search(r'(?im)^\s*(?:[-*]\s*)?(?:\*\*)?email(?:\*\*)?\s*:\s*`?([^`\s]+)', c)
    pw = re.search(r'(?im)^\s*(?:[-*]\s*)?(?:\*\*)?password(?:\*\*)?\s*:\s*`?([^`\s]+)', c)
    if not em or not pw:
        pytest.skip("no creds found")
    return {"email": em.group(1), "password": pw.group(1)}


@pytest.fixture(scope="session")
def api_client():
    s = requests.Session()
    s.headers.update({"Content-Type": "application/json"})
    return s


@pytest.fixture(scope="session")
def auth_client(test_credentials):
    s = requests.Session()
    r = s.post(f"{API}/auth/login", json=test_credentials, timeout=30)
    if r.status_code != 200:
        pytest.fail(f"Login failed {r.status_code}: {r.text[:300]}")
    return s


@pytest.fixture(scope="session")
def petugas_client():
    s = requests.Session()
    r = s.post(f"{API}/auth/login", json={
        "email": "petugas.tallo@makassarkota.go.id", "password": os.environ.get("TEST_PETUGAS_PASSWORD", "")}, timeout=30)
    if r.status_code != 200:
        pytest.fail(f"Petugas login failed {r.status_code}: {r.text[:300]}")
    return s


# ---------------- Health / root ----------------
class TestHealth:
    def test_root(self, api_client):
        r = api_client.get(f"{API}/", timeout=30)
        assert r.status_code == 200
        assert "message" in r.json()


# ---------------- Stats overview ----------------
class TestStats:
    def test_overview(self, api_client):
        r = api_client.get(f"{API}/stats/overview", timeout=30)
        assert r.status_code == 200
        d = r.json()
        assert d["jumlah_kecamatan"] == 15
        assert d["jumlah_kelurahan"] == 153, f"kelurahan={d['jumlah_kelurahan']}"
        for k in ["kemiskinan_ekstrim_kk", "stunting_anak", "anak_jalanan", "ats", "disabilitas"]:
            assert isinstance(d[k], int) and d[k] > 0, f"{k}={d.get(k)}"
        assert isinstance(d["kemiskinan_persen_terkini"], (int, float))


# ---------------- Regions ----------------
class TestRegions:
    def test_list_regions(self, api_client):
        r = api_client.get(f"{API}/regions", timeout=30)
        assert r.status_code == 200
        data = r.json()
        assert len(data) == 15
        for reg in data:
            assert "_id" not in reg
            assert isinstance(reg["id"], str)
            for f in ["nama", "lat", "lng", "kelurahan", "kemiskinan_ekstrim_kk",
                      "stunting_anak", "anak_jalanan", "ats", "disabilitas"]:
                assert f in reg, f"missing {f} in {reg.get('nama')}"
            assert -6 < reg["lat"] < -4
            assert 119 < reg["lng"] < 120

    def test_get_region_by_id(self, api_client):
        rid = api_client.get(f"{API}/regions", timeout=30).json()[0]["id"]
        r = api_client.get(f"{API}/regions/{rid}", timeout=30)
        assert r.status_code == 200
        assert r.json()["id"] == rid

    def test_get_region_not_found(self, api_client):
        r = api_client.get(f"{API}/regions/507f1f77bcf86cd799439011", timeout=30)
        assert r.status_code == 404, r.text[:200]

    def test_get_region_invalid_id(self, api_client):
        r = api_client.get(f"{API}/regions/not-an-objectid", timeout=30)
        assert r.status_code in (400, 404, 422), f"got {r.status_code}: {r.text[:200]}"


# ---------------- Trends & category data ----------------
class TestDataEndpoints:
    def test_poverty_trend(self, api_client):
        r = api_client.get(f"{API}/trends/poverty", timeout=30)
        assert r.status_code == 200
        d = r.json()
        assert len(d["tren"]) > 0
        assert "persen" in d["tren"][0]
        assert d["target"]

    def test_stunting_trend(self, api_client):
        r = api_client.get(f"{API}/trends/stunting", timeout=30)
        assert r.status_code == 200
        assert len(r.json()["tren"]) > 0

    def test_pmks(self, api_client):
        r = api_client.get(f"{API}/pmks", timeout=30)
        assert r.status_code == 200
        assert isinstance(r.json()["data"], list) and len(r.json()["data"]) > 0

    def test_disability(self, api_client):
        r = api_client.get(f"{API}/disability", timeout=30)
        assert r.status_code == 200
        d = r.json()
        assert "ragam" in d and len(d["ragam"]) > 0

    def test_ats(self, api_client):
        r = api_client.get(f"{API}/ats", timeout=30)
        assert r.status_code == 200
        assert isinstance(r.json(), (dict, list))

    def test_categories(self, api_client):
        r = api_client.get(f"{API}/categories", timeout=30)
        assert r.status_code == 200
        d = r.json()
        for k in ["kemiskinan", "stunting", "anak_jalanan", "ats", "disabilitas"]:
            assert k in d
            assert "field" in d[k]


# ---------------- Auth ----------------
class TestAuth:
    def test_login_success(self, api_client, test_credentials):
        r = api_client.post(f"{API}/auth/login", json=test_credentials, timeout=30)
        assert r.status_code == 200
        d = r.json()
        assert d["email"] == test_credentials["email"].lower()
        assert d["role"] == "admin"
        assert "access_token" in r.cookies or "access_token" in str(r.headers.get("set-cookie", ""))

    def test_login_wrong_password(self, api_client, test_credentials):
        r = api_client.post(f"{API}/auth/login", json={
            "email": test_credentials["email"], "password": "SalahBanget123"}, timeout=30)
        assert r.status_code == 401

    def test_login_petugas(self):
        s = requests.Session()
        r = s.post(f"{API}/auth/login", json={
            "email": "petugas.tallo@makassarkota.go.id", "password": os.environ.get("TEST_PETUGAS_PASSWORD", "")}, timeout=30)
        assert r.status_code == 200, r.text[:200]
        assert r.json()["role"] == "petugas"
        assert r.json()["wilayah"] == "Tallo"

    def test_me_unauthenticated(self, api_client):
        s = requests.Session()
        r = s.get(f"{API}/auth/me", timeout=30)
        assert r.status_code == 401

    def test_me_authenticated(self, auth_client, test_credentials):
        r = auth_client.get(f"{API}/auth/me", timeout=30)
        assert r.status_code == 200
        d = r.json()
        assert d["email"] == test_credentials["email"].lower()
        assert "password_hash" not in d
        assert "_id" not in d

    def test_logout(self, test_credentials):
        s = requests.Session()
        s.post(f"{API}/auth/login", json=test_credentials, timeout=30)
        r = s.post(f"{API}/auth/logout", timeout=30)
        assert r.status_code == 200
        r2 = s.get(f"{API}/auth/me", timeout=30)
        assert r2.status_code == 401, "session still valid after logout"


# ---------------- Region update (protected) ----------------
class TestRegionUpdate:
    def test_update_requires_auth(self, api_client):
        rid = api_client.get(f"{API}/regions", timeout=30).json()[0]["id"]
        s = requests.Session()
        r = s.put(f"{API}/regions/{rid}", json={"stunting_anak": 1}, timeout=30)
        assert r.status_code == 401

    def test_update_and_persist(self, auth_client):
        regions = auth_client.get(f"{API}/regions", timeout=30).json()
        reg = regions[0]
        rid = reg["id"]
        original = reg["stunting_anak"]
        new_val = original + 7
        r = auth_client.put(f"{API}/regions/{rid}", json={"stunting_anak": new_val}, timeout=30)
        assert r.status_code == 200, r.text[:300]
        d = r.json()
        assert d["stunting_anak"] == new_val
        assert "_id" not in d
        assert d.get("updated_by")
        # verify persistence
        g = auth_client.get(f"{API}/regions/{rid}", timeout=30).json()
        assert g["stunting_anak"] == new_val
        # restore
        auth_client.put(f"{API}/regions/{rid}", json={"stunting_anak": original}, timeout=30)

    def test_update_empty_payload(self, auth_client):
        rid = auth_client.get(f"{API}/regions", timeout=30).json()[0]["id"]
        r = auth_client.put(f"{API}/regions/{rid}", json={}, timeout=30)
        assert r.status_code == 400

    def test_update_not_found(self, auth_client):
        r = auth_client.put(f"{API}/regions/507f1f77bcf86cd799439011",
                            json={"stunting_anak": 5}, timeout=30)
        assert r.status_code == 404

    def test_update_invalid_objectid(self, auth_client):
        r = auth_client.put(f"{API}/regions/not-an-objectid",
                            json={"stunting_anak": 5}, timeout=30)
        assert r.status_code in (400, 404, 422), f"got {r.status_code}: {r.text[:200]}"

    def test_petugas_can_update_own_wilayah(self, petugas_client):
        regions = petugas_client.get(f"{API}/regions", timeout=30).json()
        tallo = next(x for x in regions if x["nama"].lower() == "tallo")
        orig = tallo["anak_jalanan"]
        r = petugas_client.put(f"{API}/regions/{tallo['id']}",
                               json={"anak_jalanan": orig + 1}, timeout=30)
        assert r.status_code == 200, r.text[:300]
        assert r.json()["anak_jalanan"] == orig + 1
        petugas_client.put(f"{API}/regions/{tallo['id']}", json={"anak_jalanan": orig}, timeout=30)
        back = petugas_client.get(f"{API}/regions/{tallo['id']}", timeout=30).json()
        assert back["anak_jalanan"] == orig

    def test_petugas_cannot_update_other_wilayah(self, petugas_client):
        regions = petugas_client.get(f"{API}/regions", timeout=30).json()
        mariso = next(x for x in regions if x["nama"].lower() == "mariso")
        orig = mariso["anak_jalanan"]
        r = petugas_client.put(f"{API}/regions/{mariso['id']}",
                               json={"anak_jalanan": orig + 5}, timeout=30)
        assert r.status_code == 403, f"expected 403, got {r.status_code}: {r.text[:300]}"
        check = petugas_client.get(f"{API}/regions/{mariso['id']}", timeout=30).json()
        assert check["anak_jalanan"] == orig, "data changed despite 403"

    def test_admin_can_update_any_wilayah(self, auth_client):
        regions = auth_client.get(f"{API}/regions", timeout=30).json()
        mariso = next(x for x in regions if x["nama"].lower() == "mariso")
        orig = mariso["stunting_anak"]
        r = auth_client.put(f"{API}/regions/{mariso['id']}",
                            json={"stunting_anak": orig + 3}, timeout=30)
        assert r.status_code == 200, r.text[:300]
        auth_client.put(f"{API}/regions/{mariso['id']}", json={"stunting_anak": orig}, timeout=30)


# ---------------- Register now creates pending account, no auto-login ----------------
class TestRegister:
    def test_register_creates_pending_and_no_session(self, auth_client):
        import uuid
        s = requests.Session()
        email = f"test_qa_{uuid.uuid4().hex[:8]}@example.com"
        r = s.post(f"{API}/auth/register", json={
            "email": email, "password": "TestPass2026", "name": "TEST QA",
            "role": "admin", "wilayah": "Tallo"}, timeout=30)
        assert r.status_code in (200, 201), r.text[:300]
        d = r.json()
        assert d.get("status") == "pending", d
        assert "menunggu persetujuan" in d.get("message", "").lower()
        # no session cookie issued
        assert "access_token" not in s.cookies.get_dict()
        assert s.get(f"{API}/auth/me", timeout=30).status_code == 401
        # cleanup
        users = auth_client.get(f"{API}/admin/users", timeout=30).json()
        uid = next((u["id"] for u in users if u["email"] == email), None)
        if uid:
            auth_client.delete(f"{API}/admin/users/{uid}", timeout=30)


# ---------------- AI analysis (Claude, SSE streaming) ----------------
import json
import time


def consume_sse(payload, timeout=180):
    """POST /api/ai/analyze and aggregate SSE deltas. Returns (status, text, done, err, ttfb)."""
    t0 = time.time()
    with requests.post(f"{API}/ai/analyze", json=payload, stream=True, timeout=timeout) as r:
        if r.status_code != 200:
            return r.status_code, r.text[:400], False, None, None
        ctype = r.headers.get("content-type", "")
        assert "text/event-stream" in ctype, f"content-type={ctype}"
        chunks, done, err, ttfb = [], False, None, None
        for line in r.iter_lines(decode_unicode=True):
            if not line:
                continue
            if ttfb is None:
                ttfb = round(time.time() - t0, 2)
            if line.startswith("data: "):
                obj = json.loads(line[6:])
                if "delta" in obj:
                    chunks.append(obj["delta"])
                elif obj.get("done"):
                    done = True
                elif "error" in obj:
                    err = obj["error"]
        return r.status_code, "".join(chunks), done, err, ttfb


class TestAI:
    @pytest.mark.parametrize("kategori", ["kemiskinan", "stunting", "anak_jalanan", "ats", "disabilitas"])
    def test_analyze_citywide_streams(self, kategori):
        status, text, done, err, ttfb = consume_sse({"kategori": kategori})
        assert status == 200, f"{kategori}: {status} {text}"
        assert err is None, f"{kategori} stream error: {err}"
        assert done, f"{kategori}: no done event. len={len(text)}"
        assert len(text) > 200, f"{kategori}: short output {len(text)}"
        assert "##" in text
        print(f"{kategori}: ttfb={ttfb}s chars={len(text)}")

    def test_analyze_kemiskinan_wilayah(self):
        status, text, done, err, ttfb = consume_sse({"kategori": "kemiskinan", "wilayah": "Tallo"})
        assert status == 200, text
        assert err is None, err
        assert done and len(text) > 200
        print(f"Tallo: ttfb={ttfb}s chars={len(text)}")

    def test_analyze_invalid_kategori(self, api_client):
        r = api_client.post(f"{API}/ai/analyze", json={"kategori": "xyz"}, timeout=60)
        assert r.status_code == 400


# ---------------- TTS (OpenAI) ----------------
class TestTTS:
    def test_tts_returns_audio(self, api_client):
        r = api_client.post(f"{API}/tts", json={"text": "Selamat datang", "voice": "alloy"}, timeout=120)
        assert r.status_code == 200, r.text[:400]
        assert r.headers.get("content-type", "").startswith("audio/mpeg")
        assert len(r.content) > 1000

    def test_tts_empty_text(self, api_client):
        r = api_client.post(f"{API}/tts", json={"text": "   ", "voice": "alloy"}, timeout=60)
        assert r.status_code == 400
