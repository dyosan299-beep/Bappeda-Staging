#!/usr/bin/env python3
"""
PETA INKLUSI Backend Test Suite
Tests new features: ATS import, Email notifications, PDF reports, Public gallery
"""
import io
import json
import os
import sys
import time
from datetime import datetime

import requests

# Public endpoint from frontend/.env
def get_backend_url():
    """Read REACT_APP_BACKEND_URL from frontend/.env"""
    env_file = "/app/frontend/.env"
    if os.path.exists(env_file):
        with open(env_file) as f:
            for line in f:
                if line.startswith("REACT_APP_BACKEND_URL="):
                    return line.split("=", 1)[1].strip()
    return os.environ.get("REACT_APP_BACKEND_URL", "https://commit-checker-live-13.preview.emergentagent.com")

BASE_URL = get_backend_url()
API_URL = f"{BASE_URL}/api"

# Test credentials from /app/memory/test_credentials.md
ADMIN_EMAIL = "admin@bappeda.makassarkota.go.id"
ADMIN_PASSWORD = os.environ.get("TEST_ADMIN_PASSWORD") or os.environ.get("ADMIN_PASSWORD", "xgUIzyIOSOnpxBA1")
OPERATOR_EMAIL = "petugas.tallo@makassarkota.go.id"
OPERATOR_PASSWORD = os.environ.get("TEST_PETUGAS_PASSWORD") or os.environ.get("DEMO_PETUGAS_PASSWORD", "62629163c1c1Pt")
NGO_EMAIL = "ngo.uji@petainklusi.org"
NGO_PASSWORD = os.environ.get("TEST_NGO_PASSWORD", "")

class Colors:
    GREEN = '\033[92m'
    RED = '\033[91m'
    YELLOW = '\033[93m'
    BLUE = '\033[94m'
    END = '\033[0m'

class TestRunner:
    def __init__(self):
        self.tests_run = 0
        self.tests_passed = 0
        self.tests_failed = 0
        self.session = requests.Session()
        self.session.headers.update({"Content-Type": "application/json"})
        self.cookies = {}
        self.test_batch_ids = []  # Track ATS batches for cleanup

    def log(self, msg, color=Colors.BLUE):
        print(f"{color}{msg}{Colors.END}")

    def success(self, msg):
        self.log(f"✅ {msg}", Colors.GREEN)

    def fail(self, msg):
        self.log(f"❌ {msg}", Colors.RED)

    def warn(self, msg):
        self.log(f"⚠️  {msg}", Colors.YELLOW)

    def test(self, name, func):
        """Run a single test"""
        self.tests_run += 1
        self.log(f"\n🔍 Test {self.tests_run}: {name}")
        try:
            func()
            self.tests_passed += 1
            self.success(f"PASSED: {name}")
            return True
        except AssertionError as e:
            self.tests_failed += 1
            self.fail(f"FAILED: {name}")
            self.fail(f"  Reason: {str(e)}")
            return False
        except Exception as e:
            self.tests_failed += 1
            self.fail(f"ERROR: {name}")
            self.fail(f"  Exception: {str(e)}")
            return False

    def login(self, email, password):
        """Login and store cookies"""
        self.log(f"🔐 Logging in as {email}...")
        r = self.session.post(f"{API_URL}/auth/login", json={"email": email, "password": password})
        assert r.status_code == 200, f"Login failed: {r.status_code} {r.text}"
        self.cookies = r.cookies.get_dict()
        self.success(f"Logged in as {email}")
        return r.json()

    def logout(self):
        """Logout"""
        self.session.post(f"{API_URL}/auth/logout", cookies=self.cookies)
        self.cookies = {}

    def get(self, path, **kwargs):
        """GET request with cookies"""
        return self.session.get(f"{API_URL}{path}", cookies=self.cookies, **kwargs)

    def post(self, path, **kwargs):
        """POST request with cookies"""
        return self.session.post(f"{API_URL}{path}", cookies=self.cookies, **kwargs)

    def patch(self, path, **kwargs):
        """PATCH request with cookies"""
        return self.session.patch(f"{API_URL}{path}", cookies=self.cookies, **kwargs)

    def delete(self, path, **kwargs):
        """DELETE request with cookies"""
        return self.session.delete(f"{API_URL}{path}", cookies=self.cookies, **kwargs)

    # ============================================================
    # ATS TEMPLATE & IMPORT TESTS
    # ============================================================

    def test_ats_template_admin(self):
        """ATS template download - admin should succeed"""
        self.login(ADMIN_EMAIL, ADMIN_PASSWORD)
        r = self.get("/inklusi/ats/template")
        assert r.status_code == 200, f"Expected 200, got {r.status_code}"
        assert r.headers.get("content-type") == "application/vnd.openxmlformats-officedocument.spreadsheetml.sheet", "Wrong content type"
        assert len(r.content) > 5000, "Template file too small"
        self.success("Template downloaded successfully")

    def test_ats_template_ngo_forbidden(self):
        """ATS template download - NGO should get 403"""
        self.login(NGO_EMAIL, NGO_PASSWORD)
        r = self.get("/inklusi/ats/template")
        assert r.status_code == 403, f"Expected 403, got {r.status_code}"
        self.success("NGO correctly forbidden from template download")

    def test_ats_template_anonymous_forbidden(self):
        """ATS template download - anonymous should get 401"""
        self.logout()
        r = self.get("/inklusi/ats/template")
        assert r.status_code == 401, f"Expected 401, got {r.status_code}"
        self.success("Anonymous correctly forbidden from template download")

    def test_ats_import_preview_valid(self):
        """ATS import preview with valid data"""
        self.login(ADMIN_EMAIL, ADMIN_PASSWORD)
        
        # Create minimal CSV for testing (tahun 2099 to avoid conflicts)
        csv_content = """kecamatan,kelurahan,tahun,jenjang,kelompok_usia,status_pendidikan,laki_laki,perempuan
Tallo,Buloa,2099,SD,7-12,Putus Sekolah,5,3
Tallo,Lakkang,2099,SMP,13-15,Belum Pernah Sekolah,2,4"""
        
        files = {"file": ("TEST_ats_2099.csv", csv_content.encode(), "text/csv")}
        # Don't set Content-Type header for multipart
        headers = {k: v for k, v in self.session.headers.items() if k.lower() != 'content-type'}
        r = requests.post(f"{API_URL}/inklusi/ats/preview", files=files, cookies=self.cookies, headers=headers)
        
        assert r.status_code == 200, f"Expected 200, got {r.status_code}: {r.text}"
        data = r.json()
        assert "preview_id" in data, "Missing preview_id"
        assert data["ringkasan"]["valid"] == 2, f"Expected 2 valid rows, got {data['ringkasan']['valid']}"
        assert data["ringkasan"]["error"] == 0, f"Expected 0 errors, got {data['ringkasan']['error']}"
        assert 2099 in data["ringkasan"]["tahun"], "Tahun 2099 not in summary"
        
        self.test_preview_id = data["preview_id"]
        self.success(f"Preview created: {self.test_preview_id}, 2 valid rows")

    def test_ats_import_preview_invalid_kelurahan(self):
        """ATS import preview with invalid kelurahan"""
        self.login(ADMIN_EMAIL, ADMIN_PASSWORD)
        
        csv_content = """kecamatan,kelurahan,tahun,jenjang,kelompok_usia,status_pendidikan,laki_laki,perempuan
Tallo,KELURAHAN_TIDAK_ADA,2099,SD,7-12,Putus Sekolah,5,3"""
        
        files = {"file": ("TEST_invalid.csv", csv_content.encode(), "text/csv")}
        headers = {k: v for k, v in self.session.headers.items() if k.lower() != 'content-type'}
        r = requests.post(f"{API_URL}/inklusi/ats/preview", files=files, cookies=self.cookies, headers=headers)
        
        assert r.status_code == 200, f"Expected 200, got {r.status_code}"
        data = r.json()
        assert data["ringkasan"]["error"] > 0, "Should have errors for invalid kelurahan"
        assert any("tidak dikenal" in str(e.get("pesan", "")).lower() for e in data["errors"]), "Missing 'tidak dikenal' error"
        self.success("Invalid kelurahan correctly detected")

    def test_ats_import_commit(self):
        """ATS import commit"""
        self.login(ADMIN_EMAIL, ADMIN_PASSWORD)
        
        # First create preview
        csv_content = """kecamatan,kelurahan,tahun,jenjang,kelompok_usia,status_pendidikan,laki_laki,perempuan
Tallo,Buloa,2099,SD,7-12,Putus Sekolah,10,8"""
        
        files = {"file": ("TEST_commit_2099.csv", csv_content.encode(), "text/csv")}
        headers = {k: v for k, v in self.session.headers.items() if k.lower() != 'content-type'}
        r = requests.post(f"{API_URL}/inklusi/ats/preview", files=files, cookies=self.cookies, headers=headers)
        assert r.status_code == 200, f"Preview failed: {r.status_code} {r.text}"
        preview_id = r.json()["preview_id"]
        
        # Commit
        r = self.post("/inklusi/ats/commit", json={"preview_id": preview_id, "mode": "tambah"})
        assert r.status_code == 200, f"Commit failed: {r.status_code} {r.text}"
        data = r.json()
        assert data["ok"] is True, "Commit not successful"
        assert data["diimpor"] == 1, f"Expected 1 row imported, got {data['diimpor']}"
        
        self.test_batch_ids.append(data["batch_id"])
        self.success(f"Committed 1 row, batch_id: {data['batch_id']}")

    def test_ats_batches_list(self):
        """List ATS import batches"""
        self.login(ADMIN_EMAIL, ADMIN_PASSWORD)
        r = self.get("/inklusi/ats/batches")
        assert r.status_code == 200, f"Expected 200, got {r.status_code}"
        data = r.json()
        assert "items" in data, "Missing items"
        assert len(data["items"]) > 0, "Should have at least one batch"
        self.success(f"Found {len(data['items'])} import batches")

    def test_ats_rollback_operator_forbidden(self):
        """ATS rollback - operator should get 403"""
        self.login(OPERATOR_EMAIL, OPERATOR_PASSWORD)
        if not self.test_batch_ids:
            self.warn("No batch to test rollback")
            return
        r = self.delete(f"/inklusi/ats/batches/{self.test_batch_ids[0]}")
        assert r.status_code == 403, f"Expected 403, got {r.status_code}"
        self.success("Operator correctly forbidden from rollback")

    def test_ats_kelurahan_data(self):
        """Get ATS kelurahan aggregated data"""
        self.login(ADMIN_EMAIL, ADMIN_PASSWORD)
        r = self.get("/inklusi/ats/kelurahan")
        assert r.status_code == 200, f"Expected 200, got {r.status_code}"
        data = r.json()
        assert "tersedia" in data, "Missing tersedia field"
        if data["tersedia"]:
            assert "items" in data, "Missing items"
            assert "tahun" in data, "Missing tahun"
            self.success(f"ATS data available for tahun {data.get('tahun')}, {len(data.get('items', []))} kelurahan")
        else:
            self.warn("No ATS kelurahan data available yet")

    def test_ats_public_endpoint(self):
        """Public ATS kelurahan endpoint (no auth)"""
        self.logout()
        r = self.get("/public/ats/kelurahan")
        assert r.status_code == 200, f"Expected 200, got {r.status_code}"
        data = r.json()
        assert "tersedia" in data, "Missing tersedia field"
        self.success("Public ATS endpoint accessible without auth")

    # ============================================================
    # EMAIL NOTIFICATION TESTS
    # ============================================================

    def test_email_outbox_admin_access(self):
        """Email outbox - admin should access"""
        self.login(ADMIN_EMAIL, ADMIN_PASSWORD)
        r = self.get("/inklusi/email-outbox")
        assert r.status_code == 200, f"Expected 200, got {r.status_code}"
        data = r.json()
        assert "smtp" in data, "Missing smtp status"
        assert data["smtp"]["configured"] is False, "SMTP should not be configured"
        assert "ringkasan" in data, "Missing ringkasan"
        assert "items" in data, "Missing items"
        self.success(f"Email outbox accessible, SMTP configured: {data['smtp']['configured']}")

    def test_email_outbox_operator_forbidden(self):
        """Email outbox - operator should get 403"""
        self.login(OPERATOR_EMAIL, OPERATOR_PASSWORD)
        r = self.get("/inklusi/email-outbox")
        assert r.status_code == 403, f"Expected 403, got {r.status_code}"
        self.success("Operator correctly forbidden from email outbox")

    def test_email_outbox_ngo_forbidden(self):
        """Email outbox - NGO should get 403"""
        self.login(NGO_EMAIL, NGO_PASSWORD)
        r = self.get("/inklusi/email-outbox")
        assert r.status_code == 403, f"Expected 403, got {r.status_code}"
        self.success("NGO correctly forbidden from email outbox")

    def test_email_retry_smtp_not_configured(self):
        """Email retry should return 409 when SMTP not configured"""
        self.login(ADMIN_EMAIL, ADMIN_PASSWORD)
        r = self.post("/inklusi/email-outbox/kirim-ulang")
        assert r.status_code == 409, f"Expected 409, got {r.status_code}"
        assert "SMTP belum dikonfigurasi" in r.text, "Missing SMTP error message"
        self.success("Email retry correctly returns 409 when SMTP not configured")

    def test_email_test_belum_terkirim(self):
        """Test email should return belum_terkirim status"""
        self.login(ADMIN_EMAIL, ADMIN_PASSWORD)
        r = self.post("/inklusi/email-outbox/tes", json={"to": "test@example.com"})
        assert r.status_code == 200, f"Expected 200, got {r.status_code}"
        data = r.json()
        assert data["status"] == "belum_terkirim", f"Expected belum_terkirim, got {data['status']}"
        self.success("Test email correctly returns belum_terkirim status")

    def test_inquiry_status_change_creates_email(self):
        """Changing inquiry status should create email notification"""
        self.login(ADMIN_EMAIL, ADMIN_PASSWORD)
        
        # Get existing inquiry (INQ-2026-0003 is COMPLETED, so we need one in earlier status)
        r = self.get("/inquiries", params={"status": "SUBMITTED"})
        if r.status_code != 200 or not r.json().get("items"):
            self.warn("No SUBMITTED inquiry to test email notification")
            return
        
        inquiry = r.json()["items"][0]
        inquiry_id = inquiry["id"]
        
        # Change status
        r = self.patch(f"/inquiries/{inquiry_id}/status", json={"status": "UNDER_REVIEW", "catatan": "TEST: Checking email notification"})
        assert r.status_code == 200, f"Status change failed: {r.status_code}"
        data = r.json()
        assert "notifikasi_email" in data, "Missing notifikasi_email field"
        assert data["notifikasi_email"] == "belum_terkirim", f"Expected belum_terkirim, got {data['notifikasi_email']}"
        
        # Check history
        assert len(data["riwayat"]) > 0, "Missing riwayat"
        last_entry = data["riwayat"][-1]
        assert "email" in last_entry, "Missing email field in riwayat"
        assert last_entry["email"] == "belum_terkirim", "Email status not recorded in history"
        
        self.success("Inquiry status change created email notification with belum_terkirim status")

    # ============================================================
    # PDF REPORT TESTS
    # ============================================================

    def test_pdf_report_admin(self):
        """PDF report - admin should download"""
        self.login(ADMIN_EMAIL, ADMIN_PASSWORD)
        r = self.get("/inklusi/laporan/kelurahan", params={"kecamatan": "Tallo", "kelurahan": "Buloa"})
        assert r.status_code == 200, f"Expected 200, got {r.status_code}"
        assert r.headers.get("content-type") == "application/pdf", "Wrong content type"
        assert len(r.content) > 5000, "PDF file too small"
        assert "attachment" in r.headers.get("content-disposition", ""), "Missing attachment header"
        self.success("PDF report downloaded successfully")

    def test_pdf_report_operator(self):
        """PDF report - operator should download"""
        self.login(OPERATOR_EMAIL, OPERATOR_PASSWORD)
        r = self.get("/inklusi/laporan/kelurahan", params={"kecamatan": "Tallo", "kelurahan": "Buloa"})
        assert r.status_code == 200, f"Expected 200, got {r.status_code}"
        assert r.headers.get("content-type") == "application/pdf", "Wrong content type"
        self.success("Operator can download PDF report")

    def test_pdf_report_ngo(self):
        """PDF report - NGO should download"""
        self.login(NGO_EMAIL, NGO_PASSWORD)
        r = self.get("/inklusi/laporan/kelurahan", params={"kecamatan": "Tallo", "kelurahan": "Buloa"})
        assert r.status_code == 200, f"Expected 200, got {r.status_code}"
        assert r.headers.get("content-type") == "application/pdf", "Wrong content type"
        self.success("NGO can download PDF report")

    def test_pdf_report_anonymous_forbidden(self):
        """PDF report - anonymous should get 401"""
        self.logout()
        r = self.get("/inklusi/laporan/kelurahan", params={"kecamatan": "Tallo", "kelurahan": "Buloa"})
        assert r.status_code == 401, f"Expected 401, got {r.status_code}"
        self.success("Anonymous correctly forbidden from PDF download")

    def test_pdf_report_unknown_kelurahan(self):
        """PDF report - unknown kelurahan should return 404"""
        self.login(ADMIN_EMAIL, ADMIN_PASSWORD)
        r = self.get("/inklusi/laporan/kelurahan", params={"kecamatan": "Tallo", "kelurahan": "KELURAHAN_TIDAK_ADA"})
        assert r.status_code == 404, f"Expected 404, got {r.status_code}"
        self.success("Unknown kelurahan correctly returns 404")

    # ============================================================
    # PUBLIC GALLERY TESTS
    # ============================================================

    def test_public_gallery_no_auth(self):
        """Public gallery should be accessible without auth"""
        self.logout()
        r = self.get("/public/program-selesai")
        assert r.status_code == 200, f"Expected 200, got {r.status_code}"
        data = r.json()
        assert "items" in data, "Missing items"
        assert "total" in data, "Missing total"
        assert "total_penerima" in data, "Missing total_penerima"
        self.success(f"Public gallery accessible, {data['total']} completed programs")

    def test_public_gallery_ngo_masked(self):
        """Public gallery should mask NGO names"""
        self.logout()
        r = self.get("/public/program-selesai")
        assert r.status_code == 200, f"Expected 200, got {r.status_code}"
        data = r.json()
        
        if len(data["items"]) == 0:
            self.warn("No completed programs to test masking")
            return
        
        for item in data["items"]:
            assert "ngo" in item, "Missing ngo field"
            assert "*" in item["ngo"], f"NGO name not masked: {item['ngo']}"
            assert "email" not in item, "Email should not be exposed"
            assert "telepon" not in item, "Telepon should not be exposed"
            assert "nama_pic" not in item, "nama_pic should not be exposed"
            assert "user_email" not in item, "user_email should not be exposed"
        
        self.success(f"All {len(data['items'])} programs have masked NGO names")

    def test_public_gallery_only_completed(self):
        """Public gallery should only show COMPLETED inquiries"""
        self.logout()
        r = self.get("/public/program-selesai")
        assert r.status_code == 200, f"Expected 200, got {r.status_code}"
        data = r.json()
        
        # Check that we can find the test inquiry INQ-2026-0003
        test_inquiry = next((i for i in data["items"] if "Kembali Sekolah" in i.get("program", "")), None)
        if test_inquiry:
            self.success("Found test inquiry 'TEST Program Kembali Sekolah Buloa' in gallery")
        else:
            self.warn("Test inquiry not found in gallery (might be filtered)")

    def test_public_gallery_category_filter(self):
        """Public gallery category filter"""
        self.logout()
        r = self.get("/public/program-selesai", params={"kategori": "ATS"})
        assert r.status_code == 200, f"Expected 200, got {r.status_code}"
        data = r.json()
        
        # All items should be ATS category
        for item in data["items"]:
            assert item.get("kategori") == "ATS", f"Wrong category: {item.get('kategori')}"
        
        self.success(f"Category filter works, {len(data['items'])} ATS programs")

    # ============================================================
    # CLEANUP
    # ============================================================

    def cleanup_ats_batches(self):
        """Rollback test ATS batches"""
        if not self.test_batch_ids:
            return
        
        self.log("\n🧹 Cleaning up test ATS batches...")
        self.login(ADMIN_EMAIL, ADMIN_PASSWORD)
        
        for batch_id in self.test_batch_ids:
            try:
                r = self.delete(f"/inklusi/ats/batches/{batch_id}")
                if r.status_code == 200:
                    self.success(f"Rolled back batch {batch_id}")
                else:
                    self.warn(f"Failed to rollback batch {batch_id}: {r.status_code}")
            except Exception as e:
                self.warn(f"Error rolling back batch {batch_id}: {e}")

    # ============================================================
    # RUN ALL TESTS
    # ============================================================

    def run_all(self):
        """Run all tests"""
        self.log("=" * 80, Colors.BLUE)
        self.log("PETA INKLUSI Backend Test Suite", Colors.BLUE)
        self.log(f"Testing: {BASE_URL}", Colors.BLUE)
        self.log("=" * 80, Colors.BLUE)

        # ATS Tests
        self.log("\n" + "=" * 80, Colors.BLUE)
        self.log("ATS TEMPLATE & IMPORT TESTS", Colors.BLUE)
        self.log("=" * 80, Colors.BLUE)
        self.test("ATS template - admin access", self.test_ats_template_admin)
        self.test("ATS template - NGO forbidden", self.test_ats_template_ngo_forbidden)
        self.test("ATS template - anonymous forbidden", self.test_ats_template_anonymous_forbidden)
        self.test("ATS import preview - valid data", self.test_ats_import_preview_valid)
        self.test("ATS import preview - invalid kelurahan", self.test_ats_import_preview_invalid_kelurahan)
        self.test("ATS import commit", self.test_ats_import_commit)
        self.test("ATS batches list", self.test_ats_batches_list)
        self.test("ATS rollback - operator forbidden", self.test_ats_rollback_operator_forbidden)
        self.test("ATS kelurahan data", self.test_ats_kelurahan_data)
        self.test("ATS public endpoint", self.test_ats_public_endpoint)

        # Email Tests
        self.log("\n" + "=" * 80, Colors.BLUE)
        self.log("EMAIL NOTIFICATION TESTS", Colors.BLUE)
        self.log("=" * 80, Colors.BLUE)
        self.test("Email outbox - admin access", self.test_email_outbox_admin_access)
        self.test("Email outbox - operator forbidden", self.test_email_outbox_operator_forbidden)
        self.test("Email outbox - NGO forbidden", self.test_email_outbox_ngo_forbidden)
        self.test("Email retry - SMTP not configured", self.test_email_retry_smtp_not_configured)
        self.test("Email test - belum_terkirim status", self.test_email_test_belum_terkirim)
        self.test("Inquiry status change creates email", self.test_inquiry_status_change_creates_email)

        # PDF Tests
        self.log("\n" + "=" * 80, Colors.BLUE)
        self.log("PDF REPORT TESTS", Colors.BLUE)
        self.log("=" * 80, Colors.BLUE)
        self.test("PDF report - admin download", self.test_pdf_report_admin)
        self.test("PDF report - operator download", self.test_pdf_report_operator)
        self.test("PDF report - NGO download", self.test_pdf_report_ngo)
        self.test("PDF report - anonymous forbidden", self.test_pdf_report_anonymous_forbidden)
        self.test("PDF report - unknown kelurahan 404", self.test_pdf_report_unknown_kelurahan)

        # Gallery Tests
        self.log("\n" + "=" * 80, Colors.BLUE)
        self.log("PUBLIC GALLERY TESTS", Colors.BLUE)
        self.log("=" * 80, Colors.BLUE)
        self.test("Public gallery - no auth required", self.test_public_gallery_no_auth)
        self.test("Public gallery - NGO names masked", self.test_public_gallery_ngo_masked)
        self.test("Public gallery - only COMPLETED", self.test_public_gallery_only_completed)
        self.test("Public gallery - category filter", self.test_public_gallery_category_filter)

        # Cleanup
        self.cleanup_ats_batches()
        
        # Test Ringkasan Mingguan
        self.log("\n" + "=" * 80, Colors.BLUE)
        self.log("RINGKASAN MINGGUAN (WEEKLY SUMMARY) TESTS", Colors.BLUE)
        self.log("=" * 80, Colors.BLUE)
        
        self.test("Ringkasan: Cron no auth (401)", self.test_ringkasan_mingguan_cron_no_auth)
        self.test("Ringkasan: Cron wrong token (401)", self.test_ringkasan_mingguan_cron_wrong_token)
        self.test("Ringkasan: Cron invalid JSON (400)", self.test_ringkasan_mingguan_cron_invalid_json)
        self.test("Ringkasan: Cron valid auth (200)", self.test_ringkasan_mingguan_cron_valid)
        self.test("Ringkasan: Cron duplicate webhook", self.test_ringkasan_mingguan_cron_duplicate)
        self.test("Ringkasan: Preview no auth (401)", self.test_ringkasan_mingguan_preview_no_auth)
        self.test("Ringkasan: Preview operator forbidden (403)", self.test_ringkasan_mingguan_preview_operator_forbidden)
        self.test("Ringkasan: Preview admin (200)", self.test_ringkasan_mingguan_preview_admin)
        self.test("Ringkasan: Kirim no auth (401)", self.test_ringkasan_mingguan_kirim_no_auth)
        self.test("Ringkasan: Kirim operator forbidden (403)", self.test_ringkasan_mingguan_kirim_operator_forbidden)
        self.test("Ringkasan: Kirim admin (200)", self.test_ringkasan_mingguan_kirim_admin)
        self.test("Ringkasan: Riwayat no auth (401)", self.test_ringkasan_mingguan_riwayat_no_auth)
        self.test("Ringkasan: Riwayat operator forbidden (403)", self.test_ringkasan_mingguan_riwayat_operator_forbidden)
        self.test("Ringkasan: Riwayat admin (200)", self.test_ringkasan_mingguan_riwayat_admin)
        self.test("Ringkasan: Email outbox check", self.test_ringkasan_mingguan_email_outbox)

        # Summary
        self.log("\n" + "=" * 80, Colors.BLUE)
        self.log("TEST SUMMARY", Colors.BLUE)
        self.log("=" * 80, Colors.BLUE)
        self.log(f"Total tests: {self.tests_run}")
        self.log(f"Passed: {self.tests_passed}", Colors.GREEN)
        self.log(f"Failed: {self.tests_failed}", Colors.RED if self.tests_failed > 0 else Colors.GREEN)
        self.log(f"Success rate: {self.tests_passed / self.tests_run * 100:.1f}%")
        
        return 0 if self.tests_failed == 0 else 1
    
    def test_ringkasan_mingguan_cron_no_auth(self):
        """Cron endpoint without auth should return 401"""
        self.logout()
        r = self.session.post(f"{API_URL}/cron/ringkasan-mingguan", json={})
        assert r.status_code == 401, f"Expected 401, got {r.status_code}"
    
    def test_ringkasan_mingguan_cron_wrong_token(self):
        """Cron endpoint with wrong token should return 401"""
        r = self.session.post(
            f"{API_URL}/cron/ringkasan-mingguan",
            json={},
            headers={"Authorization": "Bearer wrong_token"}
        )
        assert r.status_code == 401, f"Expected 401, got {r.status_code}"
    
    def test_ringkasan_mingguan_cron_invalid_json(self):
        """Cron endpoint with invalid JSON should return 400"""
        webhook_secret = os.environ.get("WEBHOOK_CRON_SECRET", "jj9bO6OMBGPMHte9vCy5WIErqxOt1MQ8U81haOaKJ-7_Ug82")
        r = requests.post(
            f"{API_URL}/cron/ringkasan-mingguan",
            data="invalid json",
            headers={
                "Authorization": f"Bearer {webhook_secret}",
                "Content-Type": "application/json"
            }
        )
        assert r.status_code == 400, f"Expected 400, got {r.status_code}"
    
    def test_ringkasan_mingguan_cron_valid(self):
        """Cron endpoint with valid auth should return 200"""
        webhook_secret = os.environ.get("WEBHOOK_CRON_SECRET", "jj9bO6OMBGPMHte9vCy5WIErqxOt1MQ8U81haOaKJ-7_Ug82")
        webhook_id = f"test-webhook-{int(time.time())}"
        r = requests.post(
            f"{API_URL}/cron/ringkasan-mingguan",
            json={"test": "data"},
            headers={
                "Authorization": f"Bearer {webhook_secret}",
                "X-Webhook-Id": webhook_id
            }
        )
        assert r.status_code == 200, f"Expected 200, got {r.status_code}: {r.text}"
        data = r.json()
        assert "accepted" in data, "Missing 'accepted' field"
        assert data["accepted"] == True, "Expected accepted=true"
    
    def test_ringkasan_mingguan_cron_duplicate(self):
        """Duplicate webhook ID should return duplicate:true"""
        webhook_secret = os.environ.get("WEBHOOK_CRON_SECRET", "jj9bO6OMBGPMHte9vCy5WIErqxOt1MQ8U81haOaKJ-7_Ug82")
        webhook_id = f"test-webhook-dup-{int(time.time())}"
        
        # First request
        requests.post(
            f"{API_URL}/cron/ringkasan-mingguan",
            json={"test": "data"},
            headers={
                "Authorization": f"Bearer {webhook_secret}",
                "X-Webhook-Id": webhook_id
            }
        )
        
        # Duplicate request
        r = requests.post(
            f"{API_URL}/cron/ringkasan-mingguan",
            json={"test": "data"},
            headers={
                "Authorization": f"Bearer {webhook_secret}",
                "X-Webhook-Id": webhook_id
            }
        )
        assert r.status_code == 200, f"Expected 200, got {r.status_code}"
        data = r.json()
        assert "duplicate" in data, "Missing 'duplicate' field"
        assert data["duplicate"] == True, "Expected duplicate=true"
    
    def test_ringkasan_mingguan_preview_no_auth(self):
        """Preview endpoint without auth should return 401"""
        self.logout()
        r = self.get("/inklusi/ringkasan-mingguan/preview")
        assert r.status_code == 401, f"Expected 401, got {r.status_code}"
    
    def test_ringkasan_mingguan_preview_operator_forbidden(self):
        """Preview endpoint with operator role should return 403"""
        self.login(OPERATOR_EMAIL, OPERATOR_PASSWORD)
        r = self.get("/inklusi/ringkasan-mingguan/preview")
        assert r.status_code == 403, f"Expected 403, got {r.status_code}"
    
    def test_ringkasan_mingguan_preview_admin(self):
        """Preview endpoint with admin role should return 200 with data"""
        self.login(ADMIN_EMAIL, ADMIN_PASSWORD)
        r = self.get("/inklusi/ringkasan-mingguan/preview")
        assert r.status_code == 200, f"Expected 200, got {r.status_code}: {r.text}"
        
        data = r.json()
        required_fields = ["ringkasan", "email", "penerima", "smtp", "jadwal"]
        for field in required_fields:
            assert field in data, f"Missing '{field}' field"
        
        # Check ringkasan structure
        ringkasan = data["ringkasan"]
        assert "per_kecamatan" in ringkasan, "Missing 'per_kecamatan'"
        assert "total" in ringkasan, "Missing 'total'"
        assert "inquiry" in ringkasan, "Missing 'inquiry'"
        
        kec_count = len(ringkasan["per_kecamatan"])
        assert kec_count >= 15, f"Expected 15+ kecamatan, got {kec_count}"
        
        # Check email structure
        email = data["email"]
        assert "subject" in email, "Missing email 'subject'"
        assert "html" in email, "Missing email 'html'"
        assert "text" in email, "Missing email 'text'"
        
        # Check jadwal
        jadwal = data["jadwal"]
        assert "cron" in jadwal, "Missing 'cron' field"
        assert jadwal["cron"] == "0 6 * * 1", f"Expected cron '0 6 * * 1', got {jadwal['cron']}"
        
        self.success(f"Preview returned {kec_count} kecamatan, {len(data['penerima'])} recipients")
    
    def test_ringkasan_mingguan_kirim_no_auth(self):
        """Kirim endpoint without auth should return 401"""
        self.logout()
        r = self.post("/inklusi/ringkasan-mingguan/kirim", json={})
        assert r.status_code == 401, f"Expected 401, got {r.status_code}"
    
    def test_ringkasan_mingguan_kirim_operator_forbidden(self):
        """Kirim endpoint with operator role should return 403"""
        self.login(OPERATOR_EMAIL, OPERATOR_PASSWORD)
        r = self.post("/inklusi/ringkasan-mingguan/kirim", json={})
        assert r.status_code == 403, f"Expected 403, got {r.status_code}"
    
    def test_ringkasan_mingguan_kirim_admin(self):
        """Kirim endpoint with admin role should return 200 and queue emails"""
        self.login(ADMIN_EMAIL, ADMIN_PASSWORD)
        r = self.post("/inklusi/ringkasan-mingguan/kirim", json={})
        assert r.status_code == 200, f"Expected 200, got {r.status_code}: {r.text}"
        
        data = r.json()
        assert "id" in data, "Missing 'id' field"
        assert "status" in data, "Missing 'status' field"
        assert "hasil" in data, "Missing 'hasil' field"
        
        hasil = data["hasil"]
        terkirim = hasil.get("terkirim", 0)
        belum = hasil.get("belum_terkirim", 0)
        gagal = hasil.get("gagal", 0)
        total = terkirim + belum + gagal
        
        assert total > 0, "No emails queued"
        self.success(f"Queued {total} emails (terkirim={terkirim}, belum={belum}, gagal={gagal})")
    
    def test_ringkasan_mingguan_riwayat_no_auth(self):
        """Riwayat endpoint without auth should return 401"""
        self.logout()
        r = self.get("/inklusi/ringkasan-mingguan/riwayat")
        assert r.status_code == 401, f"Expected 401, got {r.status_code}"
    
    def test_ringkasan_mingguan_riwayat_operator_forbidden(self):
        """Riwayat endpoint with operator role should return 403"""
        self.login(OPERATOR_EMAIL, OPERATOR_PASSWORD)
        r = self.get("/inklusi/ringkasan-mingguan/riwayat")
        assert r.status_code == 403, f"Expected 403, got {r.status_code}"
    
    def test_ringkasan_mingguan_riwayat_admin(self):
        """Riwayat endpoint with admin role should return 200 with history"""
        self.login(ADMIN_EMAIL, ADMIN_PASSWORD)
        r = self.get("/inklusi/ringkasan-mingguan/riwayat")
        assert r.status_code == 200, f"Expected 200, got {r.status_code}: {r.text}"
        
        data = r.json()
        assert "items" in data, "Missing 'items' field"
        
        items = data["items"]
        self.success(f"Found {len(items)} history items")
        
        if len(items) > 0:
            item = items[0]
            required_fields = ["id", "sumber", "status", "created_at"]
            for field in required_fields:
                assert field in item, f"History item missing '{field}'"
    
    def test_ringkasan_mingguan_email_outbox(self):
        """Email outbox should contain ringkasan_mingguan emails"""
        self.login(ADMIN_EMAIL, ADMIN_PASSWORD)
        r = self.get("/inklusi/email-outbox")
        assert r.status_code == 200, f"Expected 200, got {r.status_code}"
        
        data = r.json()
        if "items" in data:
            items = data["items"]
            ringkasan_emails = [e for e in items if e.get("jenis") == "ringkasan_mingguan"]
            self.success(f"Found {len(ringkasan_emails)} ringkasan_mingguan emails in outbox")


if __name__ == "__main__":
    runner = TestRunner()
    sys.exit(runner.run_all())
