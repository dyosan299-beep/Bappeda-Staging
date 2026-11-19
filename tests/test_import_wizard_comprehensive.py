#!/usr/bin/env python3
"""Comprehensive Import Wizard Test - DB Storage + Permissions
Tests all Import Wizard endpoints after migration to MariaDB storage.
"""
import io
import os
import sys
import time
import requests
from openpyxl import Workbook

BASE = os.environ.get("TEST_BASE_URL", "https://deploy-live-26.preview.emergentagent.com") + "/api"

# Test credentials
USERS = {
    "superadmin": {"email": "admin@bappeda.makassarkota.go.id", "password": os.environ.get("TEST_ADMIN_PASSWORD", "")},
    "petugas": {"email": "petugas.tallo@makassarkota.go.id", "password": os.environ.get("TEST_PETUGAS_PASSWORD", "")},
    "operator": {"email": "operator.rappocini@makassarkota.go.id", "password": os.environ.get("TEST_OPERATOR_PASSWORD", "")},
    "verifikator": {"email": "verifikator@bappeda.makassarkota.go.id", "password": os.environ.get("TEST_VERIFIKATOR_PASSWORD", "")},
}

class TestRunner:
    def __init__(self):
        self.passed = 0
        self.failed = 0
        self.results = []
        
    def log(self, test_name: str, passed: bool, details: str = ""):
        status = "✅ PASS" if passed else "❌ FAIL"
        msg = f"{status} - {test_name}"
        if details:
            msg += f" — {details}"
        print(msg)
        self.results.append(msg)
        if passed:
            self.passed += 1
        else:
            self.failed += 1
            
    def login(self, role: str) -> requests.Session:
        """Login and return session with auth"""
        s = requests.Session()
        creds = USERS[role]
        r = s.post(f"{BASE}/auth/login", json=creds, timeout=10)
        if r.status_code != 200:
            self.log(f"Login {role}", False, f"Status {r.status_code}")
            return None
        # Set cookie from response
        for cookie in r.cookies:
            s.cookies.set_cookie(cookie)
        return s
        
    def test_permissions(self):
        """Test that editor roles can access import endpoints"""
        print("\n=== Testing Permissions ===")
        
        # Test that petugas can access import endpoints
        s = self.login("petugas")
        if s:
            r = s.get(f"{BASE}/import/datasets", timeout=10)
            self.log("Petugas can access /import/datasets", r.status_code == 200, 
                    f"Status {r.status_code}")
        
        # Test that operator can access import endpoints
        s = self.login("operator")
        if s:
            r = s.get(f"{BASE}/import/datasets", timeout=10)
            self.log("Operator can access /import/datasets", r.status_code == 200,
                    f"Status {r.status_code}")
                    
    def test_full_workflow(self):
        """Test complete import workflow with gis_koordinat"""
        print("\n=== Testing Full Import Workflow ===")
        
        s = self.login("superadmin")
        if not s:
            return
            
        # 1. Create test file
        wb = Workbook()
        ws = wb.active
        ws.title = "Test"
        ws.append(["kelurahan", "kecamatan", "latitude", "longitude", "keterangan"])
        ws.append(["Kelurahan Test 1", "Kecamatan Test", -5.1400, 119.4230, "test data"])
        ws.append(["Kelurahan Test 2", "Kecamatan Test", -5.1450, 119.4250, "test data"])
        buf = io.BytesIO()
        wb.save(buf)
        
        # 2. Upload
        r = s.post(f"{BASE}/import/upload",
                  files={"file": ("test.xlsx", buf.getvalue(),
                                "application/vnd.openxmlformats-officedocument.spreadsheetml.sheet")},
                  timeout=30)
        self.log("Upload file", r.status_code == 200, 
                f"Status {r.status_code}, {r.text[:100] if r.status_code != 200 else ''}")
        if r.status_code != 200:
            return
            
        data = r.json()
        session_id = data["id"]
        
        # Verify no 'path' or 'storage' in response
        self.log("Response has no 'path' field", "path" not in data)
        self.log("Response has no 'storage' field", "storage" not in data)
        self.log("Response has 'storage'='db' removed", data.get("storage") != "db")
        
        # 3. Analyze
        r = s.post(f"{BASE}/import/analyze", 
                  json={"session_id": session_id, "jenis": "gis_koordinat"},
                  timeout=10)
        self.log("Analyze mapping", r.status_code == 200,
                f"Status {r.status_code}")
        if r.status_code != 200:
            return
        mapping = r.json()["sheets"][0]["mapping"]
        
        # 4. Validate (reads from DB)
        r = s.post(f"{BASE}/import/validate",
                  json={"session_id": session_id, "jenis": "gis_koordinat", 
                       "mapping": mapping},
                  timeout=10)
        self.log("Validate (reads from DB)", r.status_code == 200,
                f"Status {r.status_code}, total={r.json().get('total') if r.status_code == 200 else 'N/A'}")
        
        # 5. Get error report
        r = s.get(f"{BASE}/import/errors/{session_id}?format=xlsx", timeout=10)
        self.log("Download error report (xlsx)", r.status_code == 200,
                f"Status {r.status_code}")
                
        r = s.get(f"{BASE}/import/errors/{session_id}?format=csv", timeout=10)
        self.log("Download error report (csv)", r.status_code == 200,
                f"Status {r.status_code}")
        
        # 6. Execute
        r = s.post(f"{BASE}/import/execute",
                  json={"session_id": session_id, "jenis": "gis_koordinat",
                       "mapping": mapping, "mode": "update"},
                  timeout=10)
        self.log("Execute import", r.status_code == 200,
                f"Status {r.status_code}")
        if r.status_code != 200:
            return
        job_id = r.json()["job_id"]
        
        # 7. Poll job status
        for _ in range(30):
            r = s.get(f"{BASE}/import/job/{job_id}", timeout=10)
            if r.status_code == 200:
                job = r.json()
                if job.get("status") in ("selesai", "gagal"):
                    self.log("Job completed", job.get("status") == "selesai",
                            f"Status: {job.get('status')}, {job.get('pesan', '')}")
                    batch_id = job.get("batch_id")
                    break
            time.sleep(1)
        
        # 8. Check history
        r = s.get(f"{BASE}/import/history", timeout=10)
        self.log("Get import history", r.status_code == 200,
                f"Status {r.status_code}")
        
        # 9. Rollback
        if batch_id:
            r = s.delete(f"{BASE}/import/batch/{batch_id}", timeout=10)
            self.log("Rollback batch", r.status_code == 200,
                    f"Status {r.status_code}")
                    
    def test_negative_cases(self):
        """Test error handling"""
        print("\n=== Testing Negative Cases ===")
        
        s = self.login("superadmin")
        if not s:
            return
            
        # 1. Wrong file type
        r = s.post(f"{BASE}/import/upload",
                  files={"file": ("test.txt", b"not an excel file", "text/plain")},
                  timeout=10)
        self.log("Reject .txt file (422)", r.status_code == 422,
                f"Status {r.status_code}")
        
        # 2. Corrupt Excel
        r = s.post(f"{BASE}/import/upload",
                  files={"file": ("corrupt.xlsx", b"not valid excel data", 
                                "application/vnd.openxmlformats-officedocument.spreadsheetml.sheet")},
                  timeout=10)
        self.log("Reject corrupt xlsx (422)", r.status_code == 422,
                f"Status {r.status_code}")
        
        # 3. Empty file
        r = s.post(f"{BASE}/import/upload",
                  files={"file": ("empty.xlsx", b"", 
                                "application/vnd.openxmlformats-officedocument.spreadsheetml.sheet")},
                  timeout=10)
        self.log("Reject empty file (422)", r.status_code == 422,
                f"Status {r.status_code}")
        
        # 4. Unknown session
        r = s.post(f"{BASE}/import/validate",
                  json={"session_id": "unknown-session-id", "jenis": "gis_koordinat",
                       "mapping": {}},
                  timeout=10)
        self.log("Unknown session returns 404", r.status_code == 404,
                f"Status {r.status_code}")
                
    def test_large_file(self):
        """Test large file >2MB (multi-chunk storage)"""
        print("\n=== Testing Large File (>2MB) ===")
        
        s = self.login("superadmin")
        if not s:
            return
            
        # Create CSV >2MB
        lines = ["kelurahan,kecamatan,latitude,longitude,keterangan"]
        pad = "x" * 180
        for i in range(15000):
            lines.append(f"Kel {i},Kec {i % 15},-5.1,119.4,{pad}")
        data = "\n".join(lines).encode()
        
        self.log("CSV file size >2MB", len(data) > 2 * 1024 * 1024,
                f"Size: {len(data) / 1e6:.1f} MB")
        
        # Upload
        r = s.post(f"{BASE}/import/upload",
                  files={"file": ("large.csv", data, "text/csv")},
                  timeout=60)
        self.log("Upload large CSV", r.status_code == 200,
                f"Status {r.status_code}")
        if r.status_code != 200:
            return
            
        session_id = r.json()["id"]
        total_rows = r.json().get("total_rows", 0)
        self.log("Large CSV row count correct", total_rows == 15000,
                f"Rows: {total_rows}")
        
        # Validate (tests multi-chunk reassembly)
        r = s.post(f"{BASE}/import/analyze",
                  json={"session_id": session_id, "jenis": "gis_koordinat"},
                  timeout=10)
        if r.status_code == 200:
            mapping = r.json()["sheets"][0]["mapping"]
            r = s.post(f"{BASE}/import/validate",
                      json={"session_id": session_id, "jenis": "gis_koordinat",
                           "mapping": mapping},
                      timeout=30)
            self.log("Validate large file (multi-chunk reassembly)", 
                    r.status_code == 200 and r.json().get("total") == 15000,
                    f"Status {r.status_code}, total={r.json().get('total') if r.status_code == 200 else 'N/A'}")
                    
    def run_all(self):
        """Run all tests"""
        print("=" * 80)
        print("Import Wizard Comprehensive Test - DB Storage + Permissions")
        print("=" * 80)
        
        self.test_permissions()
        self.test_full_workflow()
        self.test_negative_cases()
        self.test_large_file()
        
        print("\n" + "=" * 80)
        print("TEST SUMMARY")
        print("=" * 80)
        print(f"Total: {self.passed + self.failed} tests")
        print(f"✅ Passed: {self.passed}")
        print(f"❌ Failed: {self.failed}")
        print("=" * 80)
        
        return self.failed == 0

if __name__ == "__main__":
    runner = TestRunner()
    success = runner.run_all()
    sys.exit(0 if success else 1)
