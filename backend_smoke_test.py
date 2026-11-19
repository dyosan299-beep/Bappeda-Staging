#!/usr/bin/env python3
"""
PETA INKLUSI / SIDATA Bappeda - Smoke Test
Tests basic functionality after importing repo to new workspace
"""
import os
import sys
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
    return "https://bappeda-live-demo.preview.emergentagent.com"

BASE_URL = get_backend_url()
API_URL = f"{BASE_URL}/api"

# Credentials via env vars. Set them before running the smoke test:
#   export ADMIN_PASSWORD=... DEMO_PETUGAS_PASSWORD=... DEMO_OPERATOR_PASSWORD=... DEMO_VERIFIKATOR_PASSWORD=...
# No fallbacks are provided here — the file must not contain real passwords.
_required = ("ADMIN_PASSWORD", "DEMO_PETUGAS_PASSWORD", "DEMO_OPERATOR_PASSWORD", "DEMO_VERIFIKATOR_PASSWORD")
_missing = [k for k in _required if not os.environ.get(k)]
if _missing:
    sys.stderr.write(f"[smoke-test] Variabel lingkungan belum di-set: {', '.join(_missing)}\n")
    sys.exit(2)

CREDENTIALS = {
    "superadmin": {
        "email": "admin@bappeda.makassarkota.go.id",
        "password": os.environ["ADMIN_PASSWORD"],
    },
    "petugas": {
        "email": "petugas.tallo@makassarkota.go.id",
        "password": os.environ["DEMO_PETUGAS_PASSWORD"],
    },
    "operator": {
        "email": "operator.rappocini@makassarkota.go.id",
        "password": os.environ["DEMO_OPERATOR_PASSWORD"],
    },
    "verifikator": {
        "email": "verifikator@bappeda.makassarkota.go.id",
        "password": os.environ["DEMO_VERIFIKATOR_PASSWORD"],
    },
}

class Colors:
    GREEN = '\033[92m'
    RED = '\033[91m'
    YELLOW = '\033[93m'
    BLUE = '\033[94m'
    END = '\033[0m'

class SmokeTest:
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

    def test_health(self):
        """GET /api/health returns {status: ok, database: mariadb}"""
        r = self.session.get(f"{API_URL}/health")
        assert r.status_code == 200, f"Expected 200, got {r.status_code}: {r.text}"
        data = r.json()
        assert data.get("status") == "ok", f"Expected status=ok, got {data.get('status')}"
        assert data.get("database") == "mariadb", f"Expected database=mariadb, got {data.get('database')}"
        self.success(f"Health check OK: {data}")

    def test_login_superadmin(self):
        """POST /api/auth/login works for superadmin"""
        creds = CREDENTIALS["superadmin"]
        r = self.session.post(f"{API_URL}/auth/login", json=creds)
        assert r.status_code == 200, f"Login failed: {r.status_code} {r.text}"
        data = r.json()
        assert "email" in data, "Missing email in response"
        assert data["email"] == creds["email"], f"Email mismatch: {data['email']}"
        assert "role" in data, "Missing role in response"
        self.cookies_superadmin = r.cookies.get_dict()
        self.success(f"Logged in as superadmin: {data['email']} (role: {data['role']})")

    def test_login_petugas(self):
        """POST /api/auth/login works for petugas"""
        creds = CREDENTIALS["petugas"]
        r = self.session.post(f"{API_URL}/auth/login", json=creds)
        assert r.status_code == 200, f"Login failed: {r.status_code} {r.text}"
        data = r.json()
        assert data["email"] == creds["email"], f"Email mismatch: {data['email']}"
        self.cookies_petugas = r.cookies.get_dict()
        self.success(f"Logged in as petugas: {data['email']} (role: {data['role']})")

    def test_login_operator(self):
        """POST /api/auth/login works for operator"""
        creds = CREDENTIALS["operator"]
        r = self.session.post(f"{API_URL}/auth/login", json=creds)
        assert r.status_code == 200, f"Login failed: {r.status_code} {r.text}"
        data = r.json()
        assert data["email"] == creds["email"], f"Email mismatch: {data['email']}"
        self.cookies_operator = r.cookies.get_dict()
        self.success(f"Logged in as operator: {data['email']} (role: {data['role']})")

    def test_login_verifikator(self):
        """POST /api/auth/login works for verifikator"""
        creds = CREDENTIALS["verifikator"]
        r = self.session.post(f"{API_URL}/auth/login", json=creds)
        assert r.status_code == 200, f"Login failed: {r.status_code} {r.text}"
        data = r.json()
        assert data["email"] == creds["email"], f"Email mismatch: {data['email']}"
        self.cookies_verifikator = r.cookies.get_dict()
        self.success(f"Logged in as verifikator: {data['email']} (role: {data['role']})")

    def test_auth_me_superadmin(self):
        """GET /api/auth/me after login (superadmin)"""
        r = self.session.get(f"{API_URL}/auth/me", cookies=self.cookies_superadmin)
        assert r.status_code == 200, f"Expected 200, got {r.status_code}: {r.text}"
        data = r.json()
        assert "email" in data, "Missing email"
        assert "role" in data, "Missing role"
        assert data["role"] in ["superadmin", "admin"], f"Unexpected role: {data['role']}"
        self.success(f"Auth me OK: {data['email']} (role: {data['role']})")

    def test_auth_me_petugas(self):
        """GET /api/auth/me after login (petugas)"""
        r = self.session.get(f"{API_URL}/auth/me", cookies=self.cookies_petugas)
        assert r.status_code == 200, f"Expected 200, got {r.status_code}: {r.text}"
        data = r.json()
        assert data["role"] == "petugas", f"Unexpected role: {data['role']}"
        self.success(f"Auth me OK: {data['email']} (role: {data['role']})")

    def test_auth_me_verifikator(self):
        """GET /api/auth/me after login (verifikator)"""
        r = self.session.get(f"{API_URL}/auth/me", cookies=self.cookies_verifikator)
        assert r.status_code == 200, f"Expected 200, got {r.status_code}: {r.text}"
        data = r.json()
        assert data["role"] == "verifikator", f"Unexpected role: {data['role']}"
        self.success(f"Auth me OK: {data['email']} (role: {data['role']})")

    def test_ringkasan_mingguan_preview_admin(self):
        """GET /api/inklusi/ringkasan-mingguan/preview (admin)"""
        r = self.session.get(f"{API_URL}/inklusi/ringkasan-mingguan/preview", cookies=self.cookies_superadmin)
        assert r.status_code == 200, f"Expected 200, got {r.status_code}: {r.text}"
        data = r.json()
        assert "ringkasan" in data, "Missing ringkasan"
        assert "email" in data, "Missing email"
        assert "penerima" in data, "Missing penerima"
        self.success(f"Ringkasan mingguan preview OK: {len(data.get('penerima', []))} recipients")

    def test_logout(self):
        """POST /api/auth/logout works"""
        r = self.session.post(f"{API_URL}/auth/logout", cookies=self.cookies_superadmin)
        assert r.status_code == 200, f"Expected 200, got {r.status_code}: {r.text}"
        data = r.json()
        assert "message" in data, "Missing message"
        self.success("Logout OK")

    def run_all(self):
        """Run all smoke tests"""
        self.log("=" * 80, Colors.BLUE)
        self.log("PETA INKLUSI / SIDATA Bappeda - Smoke Test", Colors.BLUE)
        self.log(f"Testing: {BASE_URL}", Colors.BLUE)
        self.log("=" * 80, Colors.BLUE)

        # Health check
        self.test("Health check", self.test_health)

        # Login tests
        self.test("Login as superadmin", self.test_login_superadmin)
        self.test("Login as petugas", self.test_login_petugas)
        self.test("Login as operator", self.test_login_operator)
        self.test("Login as verifikator", self.test_login_verifikator)

        # Auth me tests
        self.test("Auth me (superadmin)", self.test_auth_me_superadmin)
        self.test("Auth me (petugas)", self.test_auth_me_petugas)
        self.test("Auth me (verifikator)", self.test_auth_me_verifikator)

        # Latest features
        self.test("Ringkasan mingguan preview (admin)", self.test_ringkasan_mingguan_preview_admin)

        # Logout
        self.test("Logout", self.test_logout)

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
    tester = SmokeTest()
    sys.exit(tester.run_all())
