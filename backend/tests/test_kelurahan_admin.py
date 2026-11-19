"""Tests for new features: Kelurahan data, Kelola Petugas (admin users), PDF with logo."""
import os
import re
import uuid
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

CATEGORY_FIELDS = ["kemiskinan_ekstrim_kk", "stunting_anak", "anak_jalanan", "ats", "disabilitas"]


@pytest.fixture(scope="session")
def admin_creds():
    p = Path("/app/memory/test_credentials.md")
    if not p.exists():
        pytest.skip("missing test_credentials.md")
    c = p.read_text(encoding="utf-8")
    em = re.search(r'(?im)^\s*[-*]\s*Email\s*:\s*`?([^`\s]+)', c)
    pw = re.search(r'(?im)^\s*[-*]\s*Password\s*:\s*`?([^`\s]+)', c)
    if not em or not pw:
        pytest.skip("no creds in test_credentials.md")
    return {"email": em.group(1), "password": pw.group(1)}


@pytest.fixture(scope="session")
def anon():
    s = requests.Session()
    s.headers.update({"Content-Type": "application/json"})
    return s


@pytest.fixture(scope="session")
def admin(admin_creds):
    s = requests.Session()
    r = s.post(f"{API}/auth/login", json=admin_creds, timeout=30)
    if r.status_code != 200:
        pytest.fail(f"admin login failed {r.status_code}: {r.text[:300]}")
    assert r.json()["role"] == "admin"
    return s


@pytest.fixture(scope="session")
def petugas():
    s = requests.Session()
    r = s.post(f"{API}/auth/login", json={
        "email": "petugas.tallo@makassarkota.go.id", "password": os.environ.get("TEST_PETUGAS_PASSWORD", "")}, timeout=30)
    if r.status_code != 200:
        pytest.fail(f"petugas login failed {r.status_code}: {r.text[:300]}")
    return s


@pytest.fixture(scope="session")
def created_user_ids():
    return []


@pytest.fixture(scope="session", autouse=True)
def cleanup(admin, created_user_ids):
    yield
    for uid in created_user_ids:
        admin.delete(f"{API}/admin/users/{uid}", timeout=30)


# ---------------- Kelurahan read endpoints ----------------
class TestKelurahanRead:
    def test_all_kelurahan(self, anon):
        r = anon.get(f"{API}/kelurahan", timeout=30)
        assert r.status_code == 200
        data = r.json()
        assert len(data) == 153, f"expected 153 kelurahan, got {len(data)}"
        k = data[0]
        assert "_id" not in k
        assert isinstance(k["id"], str)
        for f in CATEGORY_FIELDS:
            assert f in k, f"missing field {f}"
        assert "kecamatan" in k and "nama" in k

    def test_filter_by_kecamatan(self, anon):
        r = anon.get(f"{API}/kelurahan", params={"kecamatan": "Tallo"}, timeout=30)
        assert r.status_code == 200
        data = r.json()
        assert len(data) == 15, f"Tallo should have 15 kelurahan, got {len(data)}"
        assert all(k["kecamatan"] == "Tallo" for k in data)
        names = [k["nama"] for k in data]
        assert names == sorted(names), "not sorted by nama"

    def test_filter_unknown_kecamatan(self, anon):
        r = anon.get(f"{API}/kelurahan", params={"kecamatan": "TidakAda"}, timeout=30)
        assert r.status_code == 200
        assert r.json() == []

    def test_region_kelurahan_and_sum_matches_aggregate(self, anon):
        regions = anon.get(f"{API}/regions", timeout=30).json()
        assert len(regions) == 15
        mismatches = []
        for reg in regions:
            kr = anon.get(f"{API}/regions/{reg['id']}/kelurahan", timeout=30)
            assert kr.status_code == 200
            kels = kr.json()
            assert len(kels) == reg["kelurahan"], (
                f"{reg['nama']}: kelurahan count {len(kels)} != region.kelurahan {reg['kelurahan']}")
            for f in CATEGORY_FIELDS:
                s = sum(int(k.get(f, 0)) for k in kels)
                if s != int(reg.get(f, 0)):
                    mismatches.append(f"{reg['nama']}.{f}: sum={s} region={reg.get(f)}")
        assert not mismatches, mismatches

    def test_region_kelurahan_invalid_id(self, anon):
        assert anon.get(f"{API}/regions/nonexistent/kelurahan", timeout=30).status_code == 404
        assert anon.get(f"{API}/regions/507f1f77bcf86cd799439011/kelurahan", timeout=30).status_code == 404


# ---------------- Kelurahan update + recompute ----------------
class TestKelurahanUpdate:
    def test_requires_auth(self, anon):
        kels = anon.get(f"{API}/kelurahan", params={"kecamatan": "Tallo"}, timeout=30).json()
        r = anon.put(f"{API}/kelurahan/{kels[0]['id']}", json={"stunting_anak": 5}, timeout=30)
        assert r.status_code == 401, r.status_code

    def test_invalid_id_404(self, admin):
        assert admin.put(f"{API}/kelurahan/bogus", json={"stunting_anak": 1}, timeout=30).status_code == 404
        assert admin.put(f"{API}/kelurahan/507f1f77bcf86cd799439011",
                         json={"stunting_anak": 1}, timeout=30).status_code == 404

    def test_empty_payload_400(self, admin):
        kels = admin.get(f"{API}/kelurahan", params={"kecamatan": "Tallo"}, timeout=30).json()
        assert admin.put(f"{API}/kelurahan/{kels[0]['id']}", json={}, timeout=30).status_code == 400

    def test_admin_update_recomputes_parent(self, admin):
        regions = admin.get(f"{API}/regions", timeout=30).json()
        reg = next(x for x in regions if x["nama"] == "Mariso")
        kels = admin.get(f"{API}/regions/{reg['id']}/kelurahan", timeout=30).json()
        target = kels[0]
        original = int(target["stunting_anak"])
        new_val = original + 37
        r = admin.put(f"{API}/kelurahan/{target['id']}", json={"stunting_anak": new_val}, timeout=30)
        assert r.status_code == 200, r.text[:300]
        body = r.json()
        assert body["stunting_anak"] == new_val
        assert "_id" not in body
        assert body.get("updated_by")

        # persisted
        kels2 = admin.get(f"{API}/regions/{reg['id']}/kelurahan", timeout=30).json()
        got = next(k for k in kels2 if k["id"] == target["id"])
        assert got["stunting_anak"] == new_val
        expected_sum = sum(int(k["stunting_anak"]) for k in kels2)

        reg2 = admin.get(f"{API}/regions/{reg['id']}", timeout=30).json()
        assert reg2["stunting_anak"] == expected_sum, (
            f"region aggregate {reg2['stunting_anak']} != sum {expected_sum}")

        # restore
        rr = admin.put(f"{API}/kelurahan/{target['id']}", json={"stunting_anak": original}, timeout=30)
        assert rr.status_code == 200
        reg3 = admin.get(f"{API}/regions/{reg['id']}", timeout=30).json()
        assert reg3["stunting_anak"] == expected_sum - 37

    def test_petugas_can_update_own_kecamatan(self, petugas, admin):
        kels = admin.get(f"{API}/kelurahan", params={"kecamatan": "Tallo"}, timeout=30).json()
        t = kels[0]
        orig = int(t["ats"])
        r = petugas.put(f"{API}/kelurahan/{t['id']}", json={"ats": orig + 3}, timeout=30)
        assert r.status_code == 200, r.text[:300]
        assert r.json()["ats"] == orig + 3
        petugas.put(f"{API}/kelurahan/{t['id']}", json={"ats": orig}, timeout=30)

    def test_petugas_cannot_update_other_kecamatan(self, petugas, admin):
        kels = admin.get(f"{API}/kelurahan", params={"kecamatan": "Mariso"}, timeout=30).json()
        r = petugas.put(f"{API}/kelurahan/{kels[0]['id']}", json={"ats": 1}, timeout=30)
        assert r.status_code == 403, f"expected 403, got {r.status_code}"


# ---------------- Admin users (Kelola Petugas) ----------------
class TestAdminUsers:
    def test_list_requires_admin(self, anon, petugas):
        assert anon.get(f"{API}/admin/users", timeout=30).status_code == 401
        assert petugas.get(f"{API}/admin/users", timeout=30).status_code == 403

    def test_list_users(self, admin):
        r = admin.get(f"{API}/admin/users", timeout=30)
        assert r.status_code == 200
        users = r.json()
        assert len(users) >= 2
        u = users[0]
        for f in ("id", "email", "name", "role", "wilayah", "status"):
            assert f in u
        assert "password_hash" not in u and "_id" not in u
        emails = [x["email"] for x in users]
        assert "admin@bappeda.makassarkota.go.id" in emails

    def test_create_active_petugas_and_login(self, admin, created_user_ids):
        email = f"test_petugas_{uuid.uuid4().hex[:6]}@example.com"
        r = admin.post(f"{API}/admin/users", json={
            "email": email, "password": "QaPass2026", "name": "TEST Petugas Baru",
            "wilayah": "Mariso"}, timeout=30)
        assert r.status_code in (200, 201), r.text[:300]
        d = r.json()
        created_user_ids.append(d["id"])
        assert d["status"] == "active"
        assert d["role"] == "petugas"
        assert d["wilayah"] == "Mariso"
        # verify in list
        users = admin.get(f"{API}/admin/users", timeout=30).json()
        assert any(x["email"] == email and x["status"] == "active" for x in users)
        # can log in immediately
        s = requests.Session()
        lr = s.post(f"{API}/auth/login", json={"email": email, "password": "QaPass2026"}, timeout=30)
        assert lr.status_code == 200, lr.text[:300]

    def test_create_duplicate_email_400(self, admin, admin_creds):
        r = admin.post(f"{API}/admin/users", json={
            "email": admin_creds["email"], "password": "x12345", "name": "dup"}, timeout=30)
        assert r.status_code == 400

    def test_create_requires_admin(self, petugas):
        r = petugas.post(f"{API}/admin/users", json={
            "email": "test_x@example.com", "password": "x12345", "name": "x"}, timeout=30)
        assert r.status_code == 403

    def test_role_escalation_via_admin_create(self, admin, created_user_ids):
        """Admin may intentionally create another admin - documents behaviour."""
        email = f"test_adm_{uuid.uuid4().hex[:6]}@example.com"
        r = admin.post(f"{API}/admin/users", json={
            "email": email, "password": "QaPass2026", "name": "TEST Admin2", "role": "admin"}, timeout=30)
        assert r.status_code in (200, 201)
        created_user_ids.append(r.json()["id"])
        assert r.json()["role"] == "admin"

    def test_status_invalid_value(self, admin, created_user_ids):
        email = f"test_st_{uuid.uuid4().hex[:6]}@example.com"
        u = admin.post(f"{API}/admin/users", json={
            "email": email, "password": "QaPass2026", "name": "TEST Status"}, timeout=30).json()
        created_user_ids.append(u["id"])
        r = admin.patch(f"{API}/admin/users/{u['id']}/status", json={"status": "bogus"}, timeout=30)
        assert r.status_code == 400

    def test_deactivate_blocks_login(self, admin, created_user_ids):
        email = f"test_deact_{uuid.uuid4().hex[:6]}@example.com"
        u = admin.post(f"{API}/admin/users", json={
            "email": email, "password": "QaPass2026", "name": "TEST Deact"}, timeout=30).json()
        created_user_ids.append(u["id"])
        r = admin.patch(f"{API}/admin/users/{u['id']}/status", json={"status": "inactive"}, timeout=30)
        assert r.status_code == 200
        assert r.json()["status"] == "inactive"
        lr = requests.post(f"{API}/auth/login", json={"email": email, "password": "QaPass2026"}, timeout=30)
        assert lr.status_code == 403, lr.status_code
        # reactivate -> login works
        admin.patch(f"{API}/admin/users/{u['id']}/status", json={"status": "active"}, timeout=30)
        lr2 = requests.post(f"{API}/auth/login", json={"email": email, "password": "QaPass2026"}, timeout=30)
        assert lr2.status_code == 200

    def test_cannot_modify_own_account(self, admin, admin_creds):
        users = admin.get(f"{API}/admin/users", timeout=30).json()
        me = next(u for u in users if u["email"] == admin_creds["email"])
        assert admin.patch(f"{API}/admin/users/{me['id']}/status",
                           json={"status": "inactive"}, timeout=30).status_code == 400
        assert admin.delete(f"{API}/admin/users/{me['id']}", timeout=30).status_code == 400
        # still able to authenticate
        assert admin.get(f"{API}/auth/me", timeout=30).status_code == 200

    def test_status_and_delete_unknown_user(self, admin):
        assert admin.patch(f"{API}/admin/users/507f1f77bcf86cd799439011/status",
                           json={"status": "active"}, timeout=30).status_code == 404
        assert admin.delete(f"{API}/admin/users/507f1f77bcf86cd799439011", timeout=30).status_code == 404

    def test_delete_user(self, admin):
        email = f"test_del_{uuid.uuid4().hex[:6]}@example.com"
        u = admin.post(f"{API}/admin/users", json={
            "email": email, "password": "QaPass2026", "name": "TEST Del"}, timeout=30).json()
        r = admin.delete(f"{API}/admin/users/{u['id']}", timeout=30)
        assert r.status_code == 200
        users = admin.get(f"{API}/admin/users", timeout=30).json()
        assert not any(x["email"] == email for x in users)


# ---------------- End-to-end approval flow ----------------
class TestApprovalFlow:
    def test_register_pending_then_approve_then_login(self, admin):
        email = f"test_flow_{uuid.uuid4().hex[:6]}@example.com"
        pwd = "QaPass2026"
        r = requests.post(f"{API}/auth/register", json={
            "email": email, "password": pwd, "name": "TEST Flow", "wilayah": "Tallo"}, timeout=30)
        assert r.status_code in (200, 201), r.text[:300]
        assert r.json().get("status") == "pending"

        # login blocked
        lr = requests.post(f"{API}/auth/login", json={"email": email, "password": pwd}, timeout=30)
        assert lr.status_code == 403, lr.status_code
        assert "menunggu" in lr.json().get("detail", "").lower()

        # duplicate register
        dr = requests.post(f"{API}/auth/register", json={
            "email": email, "password": pwd, "name": "dup"}, timeout=30)
        assert dr.status_code == 400

        users = admin.get(f"{API}/admin/users", timeout=30).json()
        u = next(x for x in users if x["email"] == email)
        assert u["status"] == "pending"
        assert u["role"] == "petugas"

        pr = admin.patch(f"{API}/admin/users/{u['id']}/status", json={"status": "active"}, timeout=30)
        assert pr.status_code == 200
        assert pr.json()["status"] == "active"

        s = requests.Session()
        lr2 = s.post(f"{API}/auth/login", json={"email": email, "password": pwd}, timeout=30)
        assert lr2.status_code == 200, lr2.text[:300]
        assert lr2.json()["wilayah"] == "Tallo"
        me = s.get(f"{API}/auth/me", timeout=30)
        assert me.status_code == 200
        assert me.json().get("status") == "active"

        admin.delete(f"{API}/admin/users/{u['id']}", timeout=30)
        users2 = admin.get(f"{API}/admin/users", timeout=30).json()
        assert not any(x["email"] == email for x in users2)


# ---------------- PDF reports with emblem ----------------
class TestReports:
    def test_dashboard_pdf(self, anon):
        r = anon.get(f"{API}/report/dashboard", timeout=120)
        assert r.status_code == 200
        assert r.headers.get("content-type", "").startswith("application/pdf")
        assert r.content[:4] == b"%PDF"
        assert len(r.content) > 50_000, f"pdf too small ({len(r.content)}) - logo may be missing"

    def test_ai_pdf(self, anon):
        r = anon.post(f"{API}/report/ai", json={
            "kategori": "stunting", "wilayah": "Tallo",
            "hasil": "## Ringkasan Situasi\nUji laporan otomatis QA."}, timeout=120)
        assert r.status_code == 200
        assert r.headers.get("content-type", "").startswith("application/pdf")
        assert r.content[:4] == b"%PDF"
        assert len(r.content) > 20_000, f"pdf too small ({len(r.content)})"

    def test_ai_pdf_empty_body(self, anon):
        r = anon.post(f"{API}/report/ai", json={"kategori": "stunting", "hasil": "   "}, timeout=60)
        assert r.status_code == 400


# ---------------- Security / playbook checks ----------------
class TestSecurityPlaybook:
    def test_bcrypt_hash_format(self):
        import subprocess
        out = subprocess.run(
            ["mongosh", "--quiet", "--eval",
             'db.users.findOne({role:"admin"}).password_hash'],
            capture_output=True, text=True, timeout=60,
            env={**os.environ}, cwd="/app")
        combined = (out.stdout or "") + (out.stderr or "")
        if "$2" not in combined:
            pytest.skip(f"mongosh unavailable: {combined[:200]}")
        assert "$2b$" in combined, f"hash not bcrypt $2b$: {combined[:120]}"

    def test_brute_force_lockout(self):
        """Playbook expects lockout after 5 failed attempts."""
        email = "admin@bappeda.makassarkota.go.id"
        codes = []
        for _ in range(6):
            r = requests.post(f"{API}/auth/login",
                              json={"email": email, "password": "WrongPass!123"}, timeout=30)
            codes.append(r.status_code)
        assert 429 in codes or 423 in codes, f"no lockout after 6 failed logins: {codes}"
