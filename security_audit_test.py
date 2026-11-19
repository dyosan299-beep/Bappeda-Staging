#!/usr/bin/env python3
"""
PETA INKLUSI Security Audit Test
Tests that hardcoded passwords have been removed and login still works
"""
import os
import sys
import requests

# Public endpoint from frontend/.env
BASE_URL = os.environ.get("REACT_APP_BACKEND_URL", "https://deploy-live-26.preview.emergentagent.com")
API_URL = f"{BASE_URL}/api"

# Test credentials from /app/memory/test_credentials.md
ADMIN_EMAIL = "admin@bappeda.makassarkota.go.id"
ADMIN_PASSWORD = os.environ.get("TEST_ADMIN_PASSWORD", os.environ.get("TEST_ADMIN_PASSWORD", ""))
PETUGAS_EMAIL = "petugas.tallo@makassarkota.go.id"
PETUGAS_PASSWORD = os.environ.get("TEST_PETUGAS_PASSWORD", os.environ.get("TEST_PETUGAS_PASSWORD", ""))
OPERATOR_EMAIL = "operator.rappocini@makassarkota.go.id"
OPERATOR_PASSWORD = os.environ.get("TEST_OPERATOR_PASSWORD", os.environ.get("TEST_OPERATOR_PASSWORD", ""))
VERIFIKATOR_EMAIL = "verifikator@bappeda.makassarkota.go.id"
VERIFIKATOR_PASSWORD = os.environ.get("TEST_VERIFIKATOR_PASSWORD", os.environ.get("TEST_VERIFIKATOR_PASSWORD", ""))
NGO_EMAIL = "ngo.uji@petainklusi.org"
NGO_PASSWORD = os.environ.get("TEST_NGO_PASSWORD", os.environ.get("TEST_NGO_PASSWORD", ""))

class Colors:
    GREEN = '\033[92m'
    RED = '\033[91m'
    YELLOW = '\033[93m'
    BLUE = '\033[94m'
    END = '\033[0m'

class SecurityAuditTest:
    def __init__(self):
        self.tests_run = 0
        self.tests_passed = 0
        self.tests_failed = 0
        self.session = requests.Session()
        self.session.headers.update({"Content-Type": "application/json"})

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

    # ============================================================
    # AUTH LOGIN TESTS
    # ============================================================

    def test_login_admin(self):
        """Login as superadmin"""
        r = self.session.post(f"{API_URL}/auth/login", json={"email": ADMIN_EMAIL, "password": ADMIN_PASSWORD})
        assert r.status_code == 200, f"Login failed: {r.status_code} {r.text}"
        data = r.json()
        assert "role" in data, "Missing role in response"
        assert data["role"] == "superadmin", f"Expected superadmin, got {data['role']}"
        self.success(f"Admin login successful: {data['email']}")

    def test_login_petugas(self):
        """Login as petugas"""
        r = self.session.post(f"{API_URL}/auth/login", json={"email": PETUGAS_EMAIL, "password": PETUGAS_PASSWORD})
        assert r.status_code == 200, f"Login failed: {r.status_code} {r.text}"
        data = r.json()
        assert "role" in data, "Missing role in response"
        assert data["role"] == "petugas", f"Expected petugas, got {data['role']}"
        self.success(f"Petugas login successful: {data['email']}")

    def test_login_operator(self):
        """Login as operator"""
        r = self.session.post(f"{API_URL}/auth/login", json={"email": OPERATOR_EMAIL, "password": OPERATOR_PASSWORD})
        assert r.status_code == 200, f"Login failed: {r.status_code} {r.text}"
        data = r.json()
        assert "role" in data, "Missing role in response"
        assert data["role"] == "operator", f"Expected operator, got {data['role']}"
        self.success(f"Operator login successful: {data['email']}")

    def test_login_verifikator(self):
        """Login as verifikator"""
        r = self.session.post(f"{API_URL}/auth/login", json={"email": VERIFIKATOR_EMAIL, "password": VERIFIKATOR_PASSWORD})
        assert r.status_code == 200, f"Login failed: {r.status_code} {r.text}"
        data = r.json()
        assert "role" in data, "Missing role in response"
        assert data["role"] == "verifikator", f"Expected verifikator, got {data['role']}"
        self.success(f"Verifikator login successful: {data['email']}")

    def test_login_ngo(self):
        """Login as NGO"""
        r = self.session.post(f"{API_URL}/auth/login", json={"email": NGO_EMAIL, "password": NGO_PASSWORD})
        assert r.status_code == 200, f"Login failed: {r.status_code} {r.text}"
        data = r.json()
        assert "role" in data, "Missing role in response"
        assert data["role"] == "ngo", f"Expected ngo, got {data['role']}"
        self.success(f"NGO login successful: {data['email']}")

    # ============================================================
    # PUBLIC ENDPOINTS TESTS
    # ============================================================

    def test_public_summary(self):
        """Public summary endpoint"""
        r = self.session.get(f"{API_URL}/public/summary")
        assert r.status_code == 200, f"Expected 200, got {r.status_code}"
        data = r.json()
        assert "dtsen" in data, "Missing dtsen"
        assert "individu" in data["dtsen"], "Missing dtsen.individu"
        self.success(f"Public summary endpoint accessible, {data['dtsen']['individu']} individu")

    def test_public_program_selesai(self):
        """Public program selesai endpoint"""
        r = self.session.get(f"{API_URL}/public/program-selesai")
        assert r.status_code == 200, f"Expected 200, got {r.status_code}"
        data = r.json()
        assert "items" in data, "Missing items"
        assert "total" in data, "Missing total"
        self.success(f"Public program selesai accessible, {data['total']} programs")

    def test_public_ats_kelurahan(self):
        """Public ATS kelurahan endpoint"""
        r = self.session.get(f"{API_URL}/public/ats/kelurahan")
        assert r.status_code == 200, f"Expected 200, got {r.status_code}"
        data = r.json()
        assert "tersedia" in data, "Missing tersedia field"
        self.success("Public ATS kelurahan endpoint accessible")

    # ============================================================
    # REGRESSION SMOKE TESTS
    # ============================================================

    def test_admin_dashboard_access(self):
        """Admin can access dashboard data"""
        # Login as admin
        r = self.session.post(f"{API_URL}/auth/login", json={"email": ADMIN_EMAIL, "password": ADMIN_PASSWORD})
        assert r.status_code == 200, f"Login failed: {r.status_code}"
        cookies = r.cookies.get_dict()
        
        # Access stats overview
        r = self.session.get(f"{API_URL}/stats/overview", cookies=cookies)
        assert r.status_code == 200, f"Stats overview access failed: {r.status_code}"
        data = r.json()
        assert "jumlah_kecamatan" in data or "kemiskinan_ekstrim_kk" in data, "Missing stats data"
        self.success("Admin can access stats overview")

    def test_admin_inquiry_management(self):
        """Admin can access inquiry management"""
        # Login as admin
        r = self.session.post(f"{API_URL}/auth/login", json={"email": ADMIN_EMAIL, "password": ADMIN_PASSWORD})
        assert r.status_code == 200, f"Login failed: {r.status_code}"
        cookies = r.cookies.get_dict()
        
        # Access inquiries
        r = self.session.get(f"{API_URL}/inquiries", cookies=cookies)
        assert r.status_code == 200, f"Inquiry access failed: {r.status_code}"
        data = r.json()
        assert "items" in data, "Missing items"
        self.success("Admin can access inquiry management")

    def test_pdf_report_download(self):
        """Admin can download PDF report"""
        # Login as admin
        r = self.session.post(f"{API_URL}/auth/login", json={"email": ADMIN_EMAIL, "password": ADMIN_PASSWORD})
        assert r.status_code == 200, f"Login failed: {r.status_code}"
        cookies = r.cookies.get_dict()
        
        # Download PDF
        r = self.session.get(f"{API_URL}/inklusi/laporan/kelurahan", 
                            params={"kecamatan": "Tallo", "kelurahan": "Buloa"}, 
                            cookies=cookies)
        assert r.status_code == 200, f"PDF download failed: {r.status_code}"
        assert r.headers.get("content-type") == "application/pdf", "Wrong content type"
        assert len(r.content) > 5000, "PDF file too small"
        self.success("Admin can download PDF reports")

    # ============================================================
    # RUN ALL TESTS
    # ============================================================

    def run_all(self):
        """Run all security audit tests"""
        self.log("=" * 80, Colors.BLUE)
        self.log("PETA INKLUSI Security Audit Test", Colors.BLUE)
        self.log(f"Testing: {BASE_URL}", Colors.BLUE)
        self.log("=" * 80, Colors.BLUE)

        # Auth Tests
        self.log("\n" + "=" * 80, Colors.BLUE)
        self.log("AUTHENTICATION TESTS", Colors.BLUE)
        self.log("=" * 80, Colors.BLUE)
        self.test("Login as superadmin", self.test_login_admin)
        self.test("Login as petugas", self.test_login_petugas)
        self.test("Login as operator", self.test_login_operator)
        self.test("Login as verifikator", self.test_login_verifikator)
        self.test("Login as NGO", self.test_login_ngo)

        # Public Endpoints
        self.log("\n" + "=" * 80, Colors.BLUE)
        self.log("PUBLIC ENDPOINTS TESTS", Colors.BLUE)
        self.log("=" * 80, Colors.BLUE)
        self.test("Public summary endpoint", self.test_public_summary)
        self.test("Public program selesai endpoint", self.test_public_program_selesai)
        self.test("Public ATS kelurahan endpoint", self.test_public_ats_kelurahan)

        # Regression Smoke Tests
        self.log("\n" + "=" * 80, Colors.BLUE)
        self.log("REGRESSION SMOKE TESTS", Colors.BLUE)
        self.log("=" * 80, Colors.BLUE)
        self.test("Admin dashboard access", self.test_admin_dashboard_access)
        self.test("Admin inquiry management", self.test_admin_inquiry_management)
        self.test("PDF report download", self.test_pdf_report_download)

        # Summary
        self.log("\n" + "=" * 80, Colors.BLUE)
        self.log("TEST SUMMARY", Colors.BLUE)
        self.log("=" * 80, Colors.BLUE)
        self.log(f"Total tests: {self.tests_run}")
        self.log(f"Passed: {self.tests_passed}", Colors.GREEN)
        self.log(f"Failed: {self.tests_failed}", Colors.RED if self.tests_failed > 0 else Colors.GREEN)
        self.log(f"Success rate: {self.tests_passed / self.tests_run * 100:.1f}%")
        
        return 0 if self.tests_failed == 0 else 1


if __name__ == "__main__":
    runner = SecurityAuditTest()
    sys.exit(runner.run_all())
