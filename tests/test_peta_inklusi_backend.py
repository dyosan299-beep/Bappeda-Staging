"""PETA INKLUSI Backend API Tests - comprehensive testing of public APIs, NGO flows, RBAC, masking."""
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

# Test credentials from /app/memory/test_credentials.md
SUPERADMIN = {"email": "admin@bappeda.makassarkota.go.id", "password": os.environ.get("TEST_ADMIN_PASSWORD", "")}
OPERATOR = {"email": "petugas.tallo@makassarkota.go.id", "password": os.environ.get("TEST_PETUGAS_PASSWORD", "")}
NGO_ACTIVE = {"email": "ngo.uji@petainklusi.org", "password": os.environ.get("TEST_NGO_PASSWORD", "")}


@pytest.fixture(scope="session")
def api_client():
    """Unauthenticated session."""
    s = requests.Session()
    s.headers.update({"Content-Type": "application/json"})
    return s


@pytest.fixture(scope="session")
def superadmin_client():
    """Superadmin authenticated session."""
    s = requests.Session()
    r = s.post(f"{API}/auth/login", json=SUPERADMIN, timeout=30)
    if r.status_code != 200:
        pytest.fail(f"Superadmin login failed {r.status_code}: {r.text[:300]}")
    return s


@pytest.fixture(scope="session")
def operator_client():
    """Operator authenticated session."""
    s = requests.Session()
    r = s.post(f"{API}/auth/login", json=OPERATOR, timeout=30)
    if r.status_code != 200:
        pytest.fail(f"Operator login failed {r.status_code}: {r.text[:300]}")
    return s


@pytest.fixture(scope="session")
def ngo_client():
    """NGO authenticated session."""
    s = requests.Session()
    r = s.post(f"{API}/auth/login", json=NGO_ACTIVE, timeout=30)
    if r.status_code != 200:
        pytest.fail(f"NGO login failed {r.status_code}: {r.text[:300]}")
    return s


# ============================================================
# PUBLIC APIs (no auth, no personal data)
# ============================================================
class TestPublicAPIs:
    """Public endpoints must return 200 without auth and contain NO personal fields."""

    def test_public_summary(self, api_client):
        """GET /api/public/summary returns aggregated stats without personal data."""
        r = api_client.get(f"{API}/public/summary", timeout=30)
        assert r.status_code == 200, f"Expected 200, got {r.status_code}: {r.text[:300]}"
        d = r.json()
        # Check structure
        assert "kategori" in d
        assert "wilayah" in d
        assert "per_kecamatan" in d
        # Check no personal fields
        text = str(d).lower()
        for field in ["nik", "nama", "alamat", "email", "telepon", "password"]:
            assert field not in text, f"Personal field '{field}' found in public/summary"
        print(f"✓ /public/summary: {d['wilayah']['kecamatan']} kecamatan, {d['wilayah']['kelurahan']} kelurahan")

    @pytest.mark.parametrize("kategori", ["disabilitas", "stunting", "ats", "kemiskinan"])
    def test_public_map_kecamatan(self, api_client, kategori):
        """GET /api/public/map/{kategori}?level=kecamatan returns aggregated data."""
        r = api_client.get(f"{API}/public/map/{kategori}?level=kecamatan", timeout=30)
        assert r.status_code == 200, f"{kategori}: {r.status_code} {r.text[:300]}"
        d = r.json()
        assert d["kategori"] == kategori
        assert d["level"] == "kecamatan"
        assert "items" in d
        assert len(d["items"]) > 0
        # No personal data
        text = str(d).lower()
        for field in ["nik", "email", "telepon", "password"]:
            assert field not in text, f"Personal field '{field}' in public/map/{kategori}"
        print(f"✓ /public/map/{kategori} (kecamatan): {len(d['items'])} items, total={d.get('total', 0)}")

    @pytest.mark.parametrize("kategori", ["disabilitas", "stunting", "kemiskinan"])
    def test_public_map_kelurahan(self, api_client, kategori):
        """GET /api/public/map/{kategori}?level=kelurahan returns kelurahan-level data."""
        r = api_client.get(f"{API}/public/map/{kategori}?level=kelurahan", timeout=30)
        assert r.status_code == 200, f"{kategori}: {r.status_code} {r.text[:300]}"
        d = r.json()
        assert d["level"] == "kelurahan"
        assert "items" in d
        # No personal data
        text = str(d).lower()
        for field in ["nik", "nama", "alamat", "email", "telepon"]:
            assert field not in text, f"Personal field '{field}' in public/map/{kategori} kelurahan"
        print(f"✓ /public/map/{kategori} (kelurahan): {len(d['items'])} items")

    def test_public_stunting_breakdown(self, api_client):
        """GET /api/public/stunting/breakdown returns aggregated breakdown."""
        r = api_client.get(f"{API}/public/stunting/breakdown", timeout=30)
        assert r.status_code == 200, r.text[:300]
        d = r.json()
        assert "total" in d
        assert "per_kecamatan" in d
        assert "kelompok_umur" in d
        # No personal data
        text = str(d).lower()
        for field in ["nik", "nama", "alamat", "email", "telepon"]:
            assert field not in text, f"Personal field '{field}' in public/stunting/breakdown"
        print(f"✓ /public/stunting/breakdown: total={d['total']}")

    def test_public_ats(self, api_client):
        """GET /api/public/ats returns ATS data."""
        r = api_client.get(f"{API}/public/ats", timeout=30)
        assert r.status_code == 200, r.text[:300]
        d = r.json()
        assert "per_kecamatan" in d
        assert "ringkasan" in d
        print(f"✓ /public/ats: {len(d['per_kecamatan'])} kecamatan")

    def test_public_wilayah(self, api_client):
        """GET /api/public/wilayah returns kecamatan/kelurahan list."""
        r = api_client.get(f"{API}/public/wilayah", timeout=30)
        assert r.status_code == 200, r.text[:300]
        d = r.json()
        assert d["kota"] == "Kota Makassar"
        assert "kecamatan" in d
        assert len(d["kecamatan"]) > 0
        print(f"✓ /public/wilayah: {len(d['kecamatan'])} kecamatan")


# ============================================================
# AUTH & NGO REGISTRATION
# ============================================================
class TestAuthAndNGORegistration:
    """Test login, NGO registration, and admin approval flow."""

    def test_login_superadmin(self, api_client):
        """Superadmin can login."""
        r = api_client.post(f"{API}/auth/login", json=SUPERADMIN, timeout=30)
        assert r.status_code == 200, r.text[:300]
        d = r.json()
        assert d["email"] == SUPERADMIN["email"]
        assert d["role"] in ("superadmin", "admin")
        print(f"✓ Superadmin login: {d['email']} ({d['role']})")

    def test_login_operator(self, api_client):
        """Operator can login."""
        r = api_client.post(f"{API}/auth/login", json=OPERATOR, timeout=30)
        assert r.status_code == 200, r.text[:300]
        d = r.json()
        assert d["email"] == OPERATOR["email"]
        assert d["role"] == "petugas"
        assert d["wilayah"] == "Tallo"
        print(f"✓ Operator login: {d['email']} ({d['role']}, {d['wilayah']})")

    def test_login_ngo_active(self, api_client):
        """Active NGO can login."""
        r = api_client.post(f"{API}/auth/login", json=NGO_ACTIVE, timeout=30)
        assert r.status_code == 200, r.text[:300]
        d = r.json()
        assert d["email"] == NGO_ACTIVE["email"]
        assert d["role"] == "ngo"
        print(f"✓ NGO login: {d['email']} ({d['role']})")

    def test_ngo_registration_creates_pending(self, api_client, superadmin_client):
        """NGO self-registration creates pending account."""
        test_email = f"test_ngo_{uuid.uuid4().hex[:8]}@test.org"
        payload = {
            "name": "TEST NGO PIC",
            "email": test_email,
            "password": "TestNgo2025!",
            "organisasi": "TEST Yayasan Inklusi",
            "telepon": "081234567890",
            "alamat_organisasi": "Jl. Test No. 123",
        }
        r = api_client.post(f"{API}/auth/register-ngo", json=payload, timeout=30)
        assert r.status_code == 200, r.text[:300]
        d = r.json()
        assert d["status"] == "pending"
        assert "verifikasi admin" in d["message"].lower()
        print(f"✓ NGO registration: {test_email} (pending)")

        # Verify cannot login before approval
        r2 = api_client.post(f"{API}/auth/login", json={"email": test_email, "password": "TestNgo2025!"}, timeout=30)
        assert r2.status_code == 403, f"Expected 403 for pending NGO, got {r2.status_code}"
        assert "menunggu persetujuan" in r2.json()["detail"].lower()
        print(f"✓ Pending NGO cannot login: {r2.json()['detail']}")

        # Admin approves
        users = superadmin_client.get(f"{API}/admin/users", timeout=30).json()
        uid = next((u["id"] for u in users if u["email"] == test_email), None)
        assert uid, f"NGO user {test_email} not found in admin/users"
        r3 = superadmin_client.patch(f"{API}/admin/users/{uid}/status", json={"status": "active"}, timeout=30)
        assert r3.status_code == 200, r3.text[:300]
        print(f"✓ Admin approved NGO: {test_email}")

        # Now NGO can login
        r4 = api_client.post(f"{API}/auth/login", json={"email": test_email, "password": "TestNgo2025!"}, timeout=30)
        assert r4.status_code == 200, f"Expected 200 after approval, got {r4.status_code}: {r4.text[:300]}"
        print(f"✓ Approved NGO can login: {test_email}")

        # Cleanup
        superadmin_client.delete(f"{API}/admin/users/{uid}", timeout=30)


# ============================================================
# NGO RBAC (restricted access)
# ============================================================
class TestNGORBAC:
    """NGO role must be blocked from internal data endpoints."""

    def test_ngo_blocked_from_households(self, ngo_client):
        """NGO cannot access /api/sosial/households."""
        r = ngo_client.get(f"{API}/sosial/households", timeout=30)
        assert r.status_code in (401, 403), f"Expected 401/403, got {r.status_code}"
        print(f"✓ NGO blocked from /sosial/households: {r.status_code}")

    def test_ngo_blocked_from_stunting_children(self, ngo_client):
        """NGO cannot access /api/inklusi/stunting/children."""
        r = ngo_client.get(f"{API}/inklusi/stunting/children", timeout=30)
        assert r.status_code in (401, 403), f"Expected 401/403, got {r.status_code}"
        print(f"✓ NGO blocked from /inklusi/stunting/children: {r.status_code}")

    def test_ngo_can_access_public_apis(self, ngo_client):
        """NGO can access public APIs."""
        r = ngo_client.get(f"{API}/public/summary", timeout=30)
        assert r.status_code == 200, r.text[:300]
        print(f"✓ NGO can access /public/summary")

    def test_ngo_can_access_inquiry_apis(self, ngo_client):
        """NGO can access inquiry APIs."""
        r = ngo_client.get(f"{API}/inquiries", timeout=30)
        assert r.status_code == 200, r.text[:300]
        print(f"✓ NGO can access /inquiries")


# ============================================================
# NGO INQUIRY E2E FLOW
# ============================================================
class TestNGOInquiryFlow:
    """Test NGO inquiry creation, admin review, status updates."""

    def test_inquiry_meta(self, ngo_client):
        """GET /api/inquiries/meta returns kategori and status flow."""
        r = ngo_client.get(f"{API}/inquiries/meta", timeout=30)
        assert r.status_code == 200, r.text[:300]
        d = r.json()
        assert "kategori" in d
        assert "status_flow" in d
        assert "transisi" in d
        print(f"✓ /inquiries/meta: {len(d['kategori'])} kategori, {len(d['status_flow'])} status")

    def test_create_inquiry(self, ngo_client):
        """NGO creates inquiry."""
        payload = {
            "nama_ngo": "TEST Yayasan Uji Inklusi",
            "nama_pic": "TEST PIC",
            "email": "test@test.org",
            "telepon": "081234567890",
            "organisasi": "TEST Yayasan",
            "alamat_organisasi": "Jl. Test",
            "kategori": "Stunting",
            "kecamatan": "Tallo",
            "kelurahan": "Tallo",
            "statistik_wilayah": {},
            "permasalahan": "TEST permasalahan stunting di wilayah Tallo",
            "deskripsi_kebutuhan": "TEST kebutuhan intervensi gizi",
            "program_usulan": "TEST program pemberian makanan tambahan",
            "target_penerima": "Balita stunting",
            "jumlah_penerima": 50,
            "durasi_bulan": 12,
            "estimasi_anggaran": 50000000,
            "catatan": "TEST catatan tambahan",
        }
        r = ngo_client.post(f"{API}/inquiries", json=payload, timeout=30)
        assert r.status_code == 200, r.text[:300]
        d = r.json()
        assert d["status"] == "SUBMITTED"
        assert "id" in d
        assert "nomor" in d
        print(f"✓ NGO created inquiry: {d['nomor']} (status={d['status']})")
        return d["id"]

    def test_list_inquiries_ngo(self, ngo_client):
        """NGO lists their own inquiries."""
        r = ngo_client.get(f"{API}/inquiries", timeout=30)
        assert r.status_code == 200, r.text[:300]
        d = r.json()
        assert "items" in d
        assert "total" in d
        print(f"✓ NGO lists inquiries: {d['total']} total")

    def test_admin_change_inquiry_status(self, superadmin_client, ngo_client):
        """Admin changes inquiry status through workflow."""
        # Get existing inquiry or create one
        r = superadmin_client.get(f"{API}/inquiries?status=SUBMITTED", timeout=30)
        if r.status_code == 200 and r.json()["total"] > 0:
            iid = r.json()["items"][0]["id"]
        else:
            # Create test inquiry as NGO
            payload = {
                "nama_ngo": "TEST Admin Flow",
                "nama_pic": "TEST PIC",
                "email": "test@test.org",
                "telepon": "081234567890",
                "organisasi": "TEST",
                "alamat_organisasi": "TEST",
                "kategori": "Disabilitas",
                "kecamatan": "Makassar",
                "kelurahan": "Baru",
                "statistik_wilayah": {},
                "permasalahan": "TEST permasalahan disabilitas",
                "deskripsi_kebutuhan": "TEST kebutuhan aksesibilitas",
                "program_usulan": "TEST program ramah disabilitas",
                "target_penerima": "Penyandang disabilitas",
                "jumlah_penerima": 30,
                "durasi_bulan": 6,
                "estimasi_anggaran": 30000000,
                "catatan": "",
            }
            r2 = ngo_client.post(f"{API}/inquiries", json=payload, timeout=30)
            assert r2.status_code == 200, r2.text[:300]
            iid = r2.json()["id"]

        # Admin changes status: SUBMITTED -> UNDER_REVIEW
        r3 = superadmin_client.patch(f"{API}/inquiries/{iid}/status", json={
            "status": "UNDER_REVIEW",
            "catatan": "Sedang ditinjau oleh tim Bappeda"
        }, timeout=30)
        assert r3.status_code == 200, r3.text[:300]
        d = r3.json()
        assert d["status"] == "UNDER_REVIEW"
        print(f"✓ Admin changed inquiry status: SUBMITTED -> UNDER_REVIEW")

        # Admin changes: UNDER_REVIEW -> VERIFICATION
        r4 = superadmin_client.patch(f"{API}/inquiries/{iid}/status", json={
            "status": "VERIFICATION",
            "catatan": "Verifikasi data lapangan"
        }, timeout=30)
        assert r4.status_code == 200, r4.text[:300]
        assert r4.json()["status"] == "VERIFICATION"
        print(f"✓ Admin changed inquiry status: UNDER_REVIEW -> VERIFICATION")

        # Admin approves: VERIFICATION -> APPROVED
        r5 = superadmin_client.patch(f"{API}/inquiries/{iid}/status", json={
            "status": "APPROVED",
            "catatan": "Inquiry disetujui untuk dilanjutkan ke program"
        }, timeout=30)
        assert r5.status_code == 200, r5.text[:300]
        assert r5.json()["status"] == "APPROVED"
        print(f"✓ Admin approved inquiry: VERIFICATION -> APPROVED")

        # Verify riwayat
        r6 = superadmin_client.get(f"{API}/inquiries/{iid}", timeout=30)
        assert r6.status_code == 200, r6.text[:300]
        d6 = r6.json()
        assert "riwayat" in d6
        assert len(d6["riwayat"]) >= 4  # SUBMITTED, UNDER_REVIEW, VERIFICATION, APPROVED
        print(f"✓ Inquiry riwayat: {len(d6['riwayat'])} entries")


# ============================================================
# DATA MASKING
# ============================================================
class TestDataMasking:
    """Test data masking for operator vs superadmin."""

    def test_operator_sees_masked_stunting_data(self, operator_client):
        """Operator sees masked names in stunting children data."""
        r = operator_client.get(f"{API}/inklusi/stunting/children?size=5", timeout=30)
        assert r.status_code == 200, r.text[:300]
        d = r.json()
        assert d["masked"] is True, "Expected masked=True for operator"
        if d["total"] > 0:
            item = d["items"][0]
            # Check if nama is masked (contains *)
            if "nama" in item and item["nama"]:
                assert "*" in item["nama"], f"Expected masked nama, got: {item['nama']}"
                print(f"✓ Operator sees masked nama: {item['nama']}")
        print(f"✓ Operator data masking: masked={d['masked']}")

    def test_superadmin_sees_unmasked_stunting_data(self, superadmin_client):
        """Superadmin sees unmasked names in stunting children data."""
        r = superadmin_client.get(f"{API}/inklusi/stunting/children?size=5", timeout=30)
        assert r.status_code == 200, r.text[:300]
        d = r.json()
        assert d["masked"] is False, "Expected masked=False for superadmin"
        print(f"✓ Superadmin data masking: masked={d['masked']}")


# ============================================================
# ADMIN DASHBOARD
# ============================================================
class TestAdminDashboard:
    """Test admin overview and audit log."""

    def test_admin_overview(self, superadmin_client):
        """GET /api/inklusi/admin/overview returns admin dashboard data."""
        r = superadmin_client.get(f"{API}/inklusi/admin/overview", timeout=30)
        assert r.status_code == 200, r.text[:300]
        d = r.json()
        assert "totals" in d
        assert "ngo" in d
        assert "inquiry" in d
        assert "per_kecamatan" in d
        assert "audit_terbaru" in d
        print(f"✓ Admin overview: {d['totals']['disabilitas']} disabilitas, {d['ngo']['total']} NGO, {d['inquiry']['total']} inquiry")

    def test_audit_logs_admin_only(self, superadmin_client, operator_client):
        """Audit logs accessible only to admin."""
        r = superadmin_client.get(f"{API}/inklusi/audit-logs?size=10", timeout=30)
        assert r.status_code == 200, r.text[:300]
        d = r.json()
        assert "items" in d
        assert "total" in d
        print(f"✓ Admin can access audit logs: {d['total']} total")

        # Operator should be blocked
        r2 = operator_client.get(f"{API}/inklusi/audit-logs", timeout=30)
        assert r2.status_code == 403, f"Expected 403 for operator, got {r2.status_code}"
        print(f"✓ Operator blocked from audit logs: {r2.status_code}")


# ============================================================
# REGRESSION TESTS
# ============================================================
class TestRegression:
    """Ensure existing pages still work for admin."""

    @pytest.mark.parametrize("endpoint", [
        "/regions",
        "/kelurahan",
        "/stats/overview",
        "/trends/poverty",
        "/trends/stunting",
        "/categories",
    ])
    def test_existing_endpoints_work(self, superadmin_client, endpoint):
        """Existing endpoints still return 200."""
        r = superadmin_client.get(f"{API}{endpoint}", timeout=30)
        assert r.status_code == 200, f"{endpoint}: {r.status_code} {r.text[:300]}"
        print(f"✓ {endpoint}: 200 OK")


if __name__ == "__main__":
    pytest.main([__file__, "-v", "--tb=short"])
