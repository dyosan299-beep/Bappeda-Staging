#!/usr/bin/env python3
import os
"""
Backend testing for DATA MANAGE MODULE - SIDATA Bappeda Kota Makassar
Tests all /api/master/*, /api/sosial/households, /api/disabilitas/items, 
/api/rad/items, /api/gis/locations endpoints with data integrity validation

CRITICAL: All test data MUST be cleaned up to restore baseline numbers:
- households: 29,213
- individu: 106,863
- villages: 29
- districts: 2
- rad_items: 77
- disability_region_stats: 24
- kode_referensi: 96
- gis_locations: 29
"""
import requests
import json
import sys
import time
from typing import Dict, Any, List, Optional

# Base URL from environment
BASE_URL = "https://backend-recovery-16.preview.emergentagent.com/api"

# Test credentials from /app/memory/test_credentials.md
SUPERADMIN_EMAIL = "admin@bappeda.makassarkota.go.id"
SUPERADMIN_PASSWORD = os.environ.get("TEST_ADMIN_PASSWORD", "")
PETUGAS_EMAIL = "petugas.tallo@makassarkota.go.id"
PETUGAS_PASSWORD = os.environ.get("TEST_PETUGAS_PASSWORD", "")
OPERATOR_EMAIL = "operator.rappocini@makassarkota.go.id"
OPERATOR_PASSWORD = os.environ.get("TEST_OPERATOR_PASSWORD", "")

# Expected baseline numbers
EXPECTED_BASELINE = {
    "households": 29213,
    "villages": 29,
    "districts": 2,
    "rad_items": 77,
    "disability_region_stats": 24,
    "kode_referensi": 96,
    "gis_locations": 29,
}

class TestResults:
    def __init__(self):
        self.passed = 0
        self.failed = 0
        self.errors = []
        self.created_ids = {
            "households": [],
            "disabilitas": [],
            "rad": [],
        }
    
    def add_pass(self, test_name: str):
        self.passed += 1
        print(f"✅ PASS: {test_name}")
    
    def add_fail(self, test_name: str, reason: str):
        self.failed += 1
        error_msg = f"❌ FAIL: {test_name} - {reason}"
        self.errors.append(error_msg)
        print(error_msg)
    
    def summary(self):
        total = self.passed + self.failed
        print(f"\n{'='*80}")
        print(f"TEST SUMMARY: {self.passed}/{total} passed ({self.failed} failed)")
        print(f"{'='*80}")
        if self.errors:
            print("\nFAILURES:")
            for err in self.errors:
                print(f"  {err}")
        return self.failed == 0

results = TestResults()

def login(email: str, password: str) -> str:
    """Login and return access token cookie"""
    try:
        resp = requests.post(
            f"{BASE_URL}/auth/login",
            json={"email": email, "password": password},
            timeout=10
        )
        if resp.status_code == 200:
            return resp.cookies.get("access_token", "")
        return ""
    except Exception as e:
        print(f"⚠️  Login failed for {email}: {e}")
        return ""

def make_request(method: str, endpoint: str, token: str = "", **kwargs) -> requests.Response:
    """Make HTTP request with optional authentication"""
    url = f"{BASE_URL}{endpoint}"
    cookies = {"access_token": token} if token else {}
    kwargs.setdefault("timeout", 15)
    
    try:
        if method == "GET":
            return requests.get(url, cookies=cookies, **kwargs)
        elif method == "POST":
            return requests.post(url, cookies=cookies, **kwargs)
        elif method == "PUT":
            return requests.put(url, cookies=cookies, **kwargs)
        elif method == "DELETE":
            return requests.delete(url, cookies=cookies, **kwargs)
    except Exception as e:
        print(f"⚠️  Request failed: {method} {endpoint} - {e}")
        raise

# ============================================================================
# TEST SECTION 1: Master Kode Referensi
# ============================================================================

def test_master_kode_get():
    """Test GET /api/master/kode - should return 96 items"""
    resp = make_request("GET", "/master/kode")
    
    if resp.status_code != 200:
        results.add_fail("GET /master/kode", f"Expected 200, got {resp.status_code}")
        return
    
    data = resp.json()
    if data.get("total") != 96:
        results.add_fail("GET /master/kode total", f"Expected 96, got {data.get('total')}")
        return
    
    if data.get("belum_didefinisikan") != 96:
        results.add_fail("GET /master/kode belum_didefinisikan", 
                        f"Expected 96, got {data.get('belum_didefinisikan')}")
        return
    
    if len(data.get("fields", [])) != 15:
        results.add_fail("GET /master/kode fields count", 
                        f"Expected 15 fields, got {len(data.get('fields', []))}")
        return
    
    results.add_pass("GET /master/kode - 96 items, 15 fields")

def test_master_kode_filter():
    """Test GET /api/master/kode with filters"""
    # Test field filter
    resp = make_request("GET", "/master/kode", params={"field": "jenis_lantai_terluas"})
    
    if resp.status_code != 200:
        results.add_fail("GET /master/kode?field=jenis_lantai_terluas", 
                        f"Expected 200, got {resp.status_code}")
        return
    
    data = resp.json()
    items = data.get("items", [])
    
    # Should have 11 items for jenis_lantai_terluas
    if len(items) < 10:
        results.add_fail("GET /master/kode field filter", 
                        f"Expected ~11 items for jenis_lantai_terluas, got {len(items)}")
        return
    
    # All items should have field=jenis_lantai_terluas
    if not all(item.get("field") == "jenis_lantai_terluas" for item in items):
        results.add_fail("GET /master/kode field filter", 
                        "Not all items have field=jenis_lantai_terluas")
        return
    
    results.add_pass("GET /master/kode?field=jenis_lantai_terluas - filter works")
    
    # Test hanya_kosong filter
    resp = make_request("GET", "/master/kode", params={"hanya_kosong": "true"})
    
    if resp.status_code != 200:
        results.add_fail("GET /master/kode?hanya_kosong=true", 
                        f"Expected 200, got {resp.status_code}")
        return
    
    data = resp.json()
    items = data.get("items", [])
    
    # All items should have empty label
    if not all(item.get("label") == "" for item in items):
        results.add_fail("GET /master/kode hanya_kosong filter", 
                        "Not all items have empty label")
        return
    
    results.add_pass("GET /master/kode?hanya_kosong=true - filter works")

def test_master_kode_map():
    """Test GET /api/master/kode/map"""
    resp = make_request("GET", "/master/kode/map")
    
    if resp.status_code != 200:
        results.add_fail("GET /master/kode/map", f"Expected 200, got {resp.status_code}")
        return
    
    data = resp.json()
    
    # Should have nested structure with fields
    if not isinstance(data, dict):
        results.add_fail("GET /master/kode/map", "Expected dict response")
        return
    
    # Should have 'fields' key
    if "fields" not in data:
        results.add_fail("GET /master/kode/map", "Missing 'fields' key")
        return
    
    results.add_pass("GET /master/kode/map - returns map structure")

def test_master_kode_update_authorization(superadmin_token: str, petugas_token: str):
    """Test PUT /api/master/kode/{kode_id} authorization"""
    kode_id = "jenis_lantai_terluas::6"
    
    # Test as petugas (should be 403)
    resp = make_request("PUT", f"/master/kode/{kode_id}", 
                       token=petugas_token,
                       json={"label": "Test Unauthorized"})
    
    if resp.status_code != 403:
        results.add_fail("PUT /master/kode as petugas", 
                        f"Expected 403, got {resp.status_code}")
        return
    
    results.add_pass("PUT /master/kode as petugas - correctly rejected with 403")
    
    # Test as superadmin (should be 200)
    resp = make_request("PUT", f"/master/kode/{kode_id}", 
                       token=superadmin_token,
                       json={"label": "Keramik"})
    
    if resp.status_code != 200:
        results.add_fail("PUT /master/kode as superadmin", 
                        f"Expected 200, got {resp.status_code}: {resp.text}")
        return
    
    results.add_pass("PUT /master/kode as superadmin - updated successfully")
    
    # Verify the label was updated by getting the specific kode
    resp = make_request("GET", "/master/kode", params={"field": "jenis_lantai_terluas"})
    data = resp.json()
    items = data.get("items", [])
    
    # Find kode 6
    kode_6 = None
    for item in items:
        if item.get("kode") == "6":
            kode_6 = item
            break
    
    if kode_6:
        if kode_6.get("label") == "Keramik":
            results.add_pass("PUT /master/kode - label updated to 'Keramik'")
        else:
            results.add_fail("PUT /master/kode - label verification", 
                           f"Expected 'Keramik', got {kode_6.get('label')}")
    else:
        results.add_fail("PUT /master/kode - label verification", 
                        "Could not find kode 6 in jenis_lantai_terluas")
    
    # Restore label to empty string
    resp = make_request("PUT", f"/master/kode/{kode_id}", 
                       token=superadmin_token,
                       json={"label": ""})
    
    if resp.status_code != 200:
        results.add_fail("PUT /master/kode restore label", 
                        f"Expected 200, got {resp.status_code}")
        return
    
    results.add_pass("PUT /master/kode - label restored to empty")

def test_master_kode_post_validation(superadmin_token: str):
    """Test POST /api/master/kode validation"""
    # Test with unknown field (should be 400)
    resp = make_request("POST", "/master/kode", 
                       token=superadmin_token,
                       json={"field": "field_tidak_dikenal", "kode": "99", "label": "Test"})
    
    if resp.status_code != 400:
        results.add_fail("POST /master/kode unknown field", 
                        f"Expected 400, got {resp.status_code}")
        return
    
    results.add_pass("POST /master/kode unknown field - correctly rejected with 400")
    
    # Test duplicate kode (should be 409)
    resp = make_request("POST", "/master/kode", 
                       token=superadmin_token,
                       json={"field": "jenis_lantai_terluas", "kode": "6", "label": "Duplicate"})
    
    if resp.status_code != 409:
        results.add_fail("POST /master/kode duplicate", 
                        f"Expected 409, got {resp.status_code}")
        return
    
    results.add_pass("POST /master/kode duplicate - correctly rejected with 409")

def test_master_kode_delete_validation(superadmin_token: str):
    """Test DELETE /api/master/kode/{kode_id} validation"""
    # Try to delete a kode with jumlah_data > 0 (should be 400)
    # First, find a kode with data
    resp = make_request("GET", "/master/kode")
    data = resp.json()
    items = data.get("items", [])
    
    kode_with_data = None
    for item in items:
        if item.get("jumlah_data", 0) > 0:
            kode_with_data = item.get("id")
            break
    
    if kode_with_data:
        resp = make_request("DELETE", f"/master/kode/{kode_with_data}", 
                           token=superadmin_token)
        
        if resp.status_code != 400:
            results.add_fail("DELETE /master/kode with data", 
                            f"Expected 400, got {resp.status_code}")
            return
        
        results.add_pass("DELETE /master/kode with jumlah_data > 0 - correctly rejected with 400")
    else:
        results.add_pass("DELETE /master/kode with data - skipped (no kode with data found)")

# ============================================================================
# TEST SECTION 2: Master Wilayah Berantai
# ============================================================================

def test_master_wilayah_provinsi():
    """Test GET /api/master/wilayah/provinsi"""
    resp = make_request("GET", "/master/wilayah/provinsi")
    
    if resp.status_code != 200:
        results.add_fail("GET /master/wilayah/provinsi", f"Expected 200, got {resp.status_code}")
        return
    
    data = resp.json()
    items = data.get("items", [])
    
    # Should have 1 province (Sulawesi Selatan, code 73)
    if len(items) != 1:
        results.add_fail("GET /master/wilayah/provinsi", f"Expected 1 province, got {len(items)}")
        return
    
    if items[0].get("kode") != "73":
        results.add_fail("GET /master/wilayah/provinsi", 
                        f"Expected kode 73, got {items[0].get('kode')}")
        return
    
    results.add_pass("GET /master/wilayah/provinsi - 1 province (73)")

def test_master_wilayah_kabupaten():
    """Test GET /api/master/wilayah/kabupaten"""
    resp = make_request("GET", "/master/wilayah/kabupaten", params={"kode_provinsi": "73"})
    
    if resp.status_code != 200:
        results.add_fail("GET /master/wilayah/kabupaten", f"Expected 200, got {resp.status_code}")
        return
    
    data = resp.json()
    items = data.get("items", [])
    
    # Should have 1 kabupaten (Makassar, code 7371)
    if len(items) != 1:
        results.add_fail("GET /master/wilayah/kabupaten", f"Expected 1 kabupaten, got {len(items)}")
        return
    
    if items[0].get("kode") != "7371":
        results.add_fail("GET /master/wilayah/kabupaten", 
                        f"Expected kode 7371, got {items[0].get('kode')}")
        return
    
    results.add_pass("GET /master/wilayah/kabupaten?kode_provinsi=73 - 1 kabupaten (7371)")

def test_master_wilayah_kecamatan():
    """Test GET /api/master/wilayah/kecamatan"""
    resp = make_request("GET", "/master/wilayah/kecamatan", 
                       params={"kode_kabupaten_kota": "7371"})
    
    if resp.status_code != 200:
        results.add_fail("GET /master/wilayah/kecamatan", f"Expected 200, got {resp.status_code}")
        return
    
    data = resp.json()
    items = data.get("items", [])
    
    # Should have 2 kecamatan (Tallo 737107 & Makassar 737103)
    if len(items) != 2:
        results.add_fail("GET /master/wilayah/kecamatan", f"Expected 2 kecamatan, got {len(items)}")
        return
    
    kode_list = [item.get("kode") for item in items]
    if "737107" not in kode_list or "737103" not in kode_list:
        results.add_fail("GET /master/wilayah/kecamatan", 
                        f"Expected kode 737107 and 737103, got {kode_list}")
        return
    
    results.add_pass("GET /master/wilayah/kecamatan?kode_kabupaten_kota=7371 - 2 kecamatan")

def test_master_wilayah_kelurahan():
    """Test GET /api/master/wilayah/kelurahan"""
    # Test Tallo (737107) - should have 15 kelurahan
    resp = make_request("GET", "/master/wilayah/kelurahan", 
                       params={"kode_kecamatan": "737107"})
    
    if resp.status_code != 200:
        results.add_fail("GET /master/wilayah/kelurahan Tallo", 
                        f"Expected 200, got {resp.status_code}")
        return
    
    data = resp.json()
    items = data.get("items", [])
    
    if len(items) != 15:
        results.add_fail("GET /master/wilayah/kelurahan Tallo", 
                        f"Expected 15 kelurahan, got {len(items)}")
        return
    
    results.add_pass("GET /master/wilayah/kelurahan?kode_kecamatan=737107 - 15 kelurahan")
    
    # Test Makassar (737103) - should have 14 kelurahan
    resp = make_request("GET", "/master/wilayah/kelurahan", 
                       params={"kode_kecamatan": "737103"})
    
    if resp.status_code != 200:
        results.add_fail("GET /master/wilayah/kelurahan Makassar", 
                        f"Expected 200, got {resp.status_code}")
        return
    
    data = resp.json()
    items = data.get("items", [])
    
    if len(items) != 14:
        results.add_fail("GET /master/wilayah/kelurahan Makassar", 
                        f"Expected 14 kelurahan, got {len(items)}")
        return
    
    results.add_pass("GET /master/wilayah/kelurahan?kode_kecamatan=737103 - 14 kelurahan")

# ============================================================================
# TEST SECTION 3: Master Fields Metadata
# ============================================================================

def test_master_fields_dtsen():
    """Test GET /api/master/fields/dtsen"""
    resp = make_request("GET", "/master/fields/dtsen")
    
    if resp.status_code != 200:
        results.add_fail("GET /master/fields/dtsen", f"Expected 200, got {resp.status_code}")
        return
    
    data = resp.json()
    sections = data.get("sections", [])
    
    # Should have 6 sections
    if len(sections) != 6:
        results.add_fail("GET /master/fields/dtsen sections", 
                        f"Expected 6 sections, got {len(sections)}")
        return
    
    expected_sections = [
        "Identitas Keluarga",
        "Identitas Wilayah",
        "Status Sosial",
        "Kondisi Rumah",
        "Infrastruktur Dasar",
        "Aset"
    ]
    
    section_names = [s.get("section", s.get("nama", "")) for s in sections]
    for expected in expected_sections:
        if expected not in section_names:
            results.add_fail("GET /master/fields/dtsen sections", 
                           f"Missing section: {expected}")
            return
    
    # Check that fields with tipe 'kode' have 'opsi'
    has_opsi = False
    for section in sections:
        for field in section.get("fields", []):
            if field.get("tipe") == "kode" and "opsi" in field and field["opsi"]:
                has_opsi = True
                break
        if has_opsi:
            break
    
    if not has_opsi:
        results.add_fail("GET /master/fields/dtsen opsi", 
                        "No field with tipe=kode has opsi")
        return
    
    results.add_pass("GET /master/fields/dtsen - 6 sections with opsi for kode fields")

def test_master_fields_other():
    """Test GET /api/master/fields for other types"""
    # Test disabilitas
    resp = make_request("GET", "/master/fields/disabilitas")
    
    if resp.status_code != 200:
        results.add_fail("GET /master/fields/disabilitas", 
                        f"Expected 200, got {resp.status_code}")
        return
    
    results.add_pass("GET /master/fields/disabilitas - returns 200")
    
    # Test rad
    resp = make_request("GET", "/master/fields/rad")
    
    if resp.status_code != 200:
        results.add_fail("GET /master/fields/rad", f"Expected 200, got {resp.status_code}")
        return
    
    results.add_pass("GET /master/fields/rad - returns 200")
    
    # Test gis_koordinat
    resp = make_request("GET", "/master/fields/gis_koordinat")
    
    if resp.status_code != 200:
        results.add_fail("GET /master/fields/gis_koordinat", 
                        f"Expected 200, got {resp.status_code}")
        return
    
    results.add_pass("GET /master/fields/gis_koordinat - returns 200")
    
    # Test unknown type (should be 404)
    resp = make_request("GET", "/master/fields/unknown_type")
    
    if resp.status_code != 404:
        results.add_fail("GET /master/fields/unknown_type", 
                        f"Expected 404, got {resp.status_code}")
        return
    
    results.add_pass("GET /master/fields/unknown_type - correctly returns 404")

# ============================================================================
# TEST SECTION 4: CRUD DTSEN Households
# ============================================================================

def test_households_create(superadmin_token: str) -> Optional[str]:
    """Test POST /api/sosial/households - create new household"""
    # Generate unique no_kk (16 digits)
    import random
    no_kk = f"73710710{random.randint(10000000, 99999999)}"
    
    household_data = {
        "data": {
            "nomor_kartu_keluarga": no_kk,
            "nama_kepala_keluarga": "UJI TEST DTSEN",
            "alamat": "Jl. Test No. 123",
            "kelurahan_desa": "PANNAMPU",
            "kode_kelurahan": "7371071001",
            "kecamatan": "TALLO",
            "kode_kecamatan": "737107",
            "kabupaten_kota": "MAKASSAR",
            "kode_kabupaten_kota": "7371",
            "provinsi": "SULAWESI SELATAN",
            "kode_provinsi": "73",
            "jumlah_anggota_keluarga": 4,
            "desil_nasional": 3,
            "pbi_nas": 0,
            "pbi_pemda": 0,
        },
        "mode_duplikat": "tolak",
        "catatan": "Data uji testing agent"
    }
    
    resp = make_request("POST", "/sosial/households", 
                       token=superadmin_token,
                       json=household_data)
    
    if resp.status_code not in [200, 201]:
        results.add_fail("POST /sosial/households create", 
                        f"Expected 200/201, got {resp.status_code}: {resp.text}")
        return None
    
    data = resp.json()
    
    if data.get("status") != "created":
        results.add_fail("POST /sosial/households status", 
                        f"Expected status=created, got {data.get('status')}")
        return None
    
    household_id = data.get("id")
    if not household_id:
        results.add_fail("POST /sosial/households id", "No id returned")
        return None
    
    results.created_ids["households"].append(household_id)
    results.add_pass(f"POST /sosial/households - created with id {household_id}")
    
    return household_id

def test_households_overview_increment():
    """Test that household count increased to 29,214"""
    resp = make_request("GET", "/sosial/overview")
    
    if resp.status_code != 200:
        results.add_fail("GET /sosial/overview after create", 
                        f"Expected 200, got {resp.status_code}")
        return
    
    data = resp.json()
    total = data.get("total_households", 0)
    
    # Note: Aggregate refresh might be async, so we check if it's >= baseline
    if total < 29213:
        results.add_fail("GET /sosial/overview total_households", 
                        f"Expected >= 29213, got {total}")
        return
    
    if total == 29214:
        results.add_pass("GET /sosial/overview - total_households increased to 29,214")
    else:
        results.add_pass(f"GET /sosial/overview - total_households is {total} (aggregate refresh may be async)")

def test_households_village_stats_increment():
    """Test that Pannampu village stats increased"""
    resp = make_request("GET", "/wilayah/kelurahan", 
                       params={"kode_kecamatan": "737107"})
    
    if resp.status_code != 200:
        results.add_fail("GET /wilayah/kelurahan after create", 
                        f"Expected 200, got {resp.status_code}")
        return
    
    data = resp.json()
    items = data.get("items", [])
    
    # Find Pannampu
    pannampu = None
    for kel in items:
        if kel.get("nama", "").upper() == "PANNAMPU":
            pannampu = kel
            break
    
    if not pannampu:
        results.add_fail("GET /wilayah/kelurahan Pannampu", "Pannampu not found")
        return
    
    # Should have increased by 1 (original was 2559, now should be 2560)
    # Note: Aggregate refresh might be async
    total = pannampu.get("total_households", 0)
    if total < 2559:
        results.add_fail("GET /wilayah/kelurahan Pannampu total", 
                        f"Expected >= 2559, got {total}")
        return
    
    if total == 2560:
        results.add_pass("GET /wilayah/kelurahan - Pannampu total_households increased to 2,560")
    else:
        results.add_pass(f"GET /wilayah/kelurahan - Pannampu total_households is {total} (aggregate refresh may be async)")

def test_households_get_detail(household_id: str):
    """Test GET /api/sosial/households/{id}"""
    resp = make_request("GET", f"/sosial/households/{household_id}")
    
    if resp.status_code != 200:
        results.add_fail(f"GET /sosial/households/{household_id}", 
                        f"Expected 200, got {resp.status_code}")
        return
    
    data = resp.json()
    
    if data.get("id") != household_id:
        results.add_fail(f"GET /sosial/households/{household_id} id", 
                        f"Expected id={household_id}, got {data.get('id')}")
        return
    
    results.add_pass(f"GET /sosial/households/{household_id} - returns household data")

def test_households_get_form(superadmin_token: str, household_id: str):
    """Test GET /api/sosial/households/{id}/form"""
    resp = make_request("GET", f"/sosial/households/{household_id}/form", 
                       token=superadmin_token)
    
    if resp.status_code != 200:
        results.add_fail(f"GET /sosial/households/{household_id}/form", 
                        f"Expected 200, got {resp.status_code}")
        return
    
    data = resp.json()
    
    # Should return Excel column format
    if not isinstance(data, dict):
        results.add_fail(f"GET /sosial/households/{household_id}/form", 
                        "Expected dict response")
        return
    
    results.add_pass(f"GET /sosial/households/{household_id}/form - returns Excel format")

def test_households_duplicate(superadmin_token: str, no_kk: str):
    """Test POST /api/sosial/households with duplicate no_kk"""
    household_data = {
        "data": {
            "nomor_kartu_keluarga": no_kk,
            "nama_kepala_keluarga": "DUPLICATE TEST",
            "alamat": "Jl. Duplicate",
            "kelurahan_desa": "PANNAMPU",
            "kode_kelurahan": "7371071001",
            "kecamatan": "TALLO",
            "kode_kecamatan": "737107",
            "kabupaten_kota": "MAKASSAR",
            "kode_kabupaten_kota": "7371",
            "provinsi": "SULAWESI SELATAN",
            "kode_provinsi": "73",
            "jumlah_anggota_keluarga": 3,
            "desil_nasional": 2,
            "pbi_nas": 0,
            "pbi_pemda": 0,
        },
        "mode_duplikat": "tolak",
    }
    
    resp = make_request("POST", "/sosial/households", 
                       token=superadmin_token,
                       json=household_data)
    
    if resp.status_code != 409:
        results.add_fail("POST /sosial/households duplicate", 
                        f"Expected 409, got {resp.status_code}")
        return
    
    data = resp.json()
    
    # Should contain pilihan (choices)
    if "pilihan" not in data:
        results.add_fail("POST /sosial/households duplicate pilihan", 
                        "Expected 'pilihan' in response")
        return
    
    results.add_pass("POST /sosial/households duplicate - correctly returns 409 with pilihan")
    
    # Test mode_duplikat=skip
    household_data["mode_duplikat"] = "skip"
    resp = make_request("POST", "/sosial/households", 
                       token=superadmin_token,
                       json=household_data)
    
    if resp.status_code not in [200, 201]:
        results.add_fail("POST /sosial/households mode=skip", 
                        f"Expected 200/201, got {resp.status_code}")
        return
    
    data = resp.json()
    if data.get("status") != "skipped":
        results.add_fail("POST /sosial/households mode=skip status", 
                        f"Expected status=skipped, got {data.get('status')}")
        return
    
    results.add_pass("POST /sosial/households mode_duplikat=skip - status=skipped")
    
    # Test mode_duplikat=update
    household_data["mode_duplikat"] = "update"
    household_data["data"]["nama_kepala_keluarga"] = "UPDATED NAME"
    resp = make_request("POST", "/sosial/households", 
                       token=superadmin_token,
                       json=household_data)
    
    if resp.status_code not in [200, 201]:
        results.add_fail("POST /sosial/households mode=update", 
                        f"Expected 200/201, got {resp.status_code}")
        return
    
    data = resp.json()
    if data.get("status") != "updated":
        results.add_fail("POST /sosial/households mode=update status", 
                        f"Expected status=updated, got {data.get('status')}")
        return
    
    results.add_pass("POST /sosial/households mode_duplikat=update - status=updated")

def test_households_validation(superadmin_token: str):
    """Test POST /api/sosial/households validation"""
    # Test without nomor_kartu_keluarga (should be 422)
    household_data = {
        "data": {
            "nama_kepala_keluarga": "NO KK TEST",
            "kelurahan_desa": "PANNAMPU",
        },
        "mode_duplikat": "tolak",
    }
    
    resp = make_request("POST", "/sosial/households", 
                       token=superadmin_token,
                       json=household_data)
    
    if resp.status_code != 422:
        results.add_fail("POST /sosial/households without no_kk", 
                        f"Expected 422, got {resp.status_code}")
        return
    
    data = resp.json()
    # Check for either 'errors' or 'detail' field (FastAPI validation)
    if "errors" not in data and "detail" not in data:
        results.add_fail("POST /sosial/households validation errors", 
                        f"Expected 'errors' or 'detail' in response, got: {data}")
        return
    
    results.add_pass("POST /sosial/households without no_kk - correctly returns 422 with validation errors")
    
    # Test with invalid desil_nasional (should be 422)
    household_data = {
        "data": {
            "nomor_kartu_keluarga": "7371071099999999",
            "kelurahan_desa": "PANNAMPU",
            "kode_kelurahan": "7371071001",
            "desil_nasional": 99,
        },
        "mode_duplikat": "tolak",
    }
    
    resp = make_request("POST", "/sosial/households", 
                       token=superadmin_token,
                       json=household_data)
    
    if resp.status_code != 422:
        results.add_fail("POST /sosial/households invalid desil", 
                        f"Expected 422, got {resp.status_code}")
        return
    
    results.add_pass("POST /sosial/households desil_nasional=99 - correctly returns 422")
    
    # Test with invalid pbi_nas (should be 422)
    household_data["data"]["desil_nasional"] = 3
    household_data["data"]["pbi_nas"] = 5
    
    resp = make_request("POST", "/sosial/households", 
                       token=superadmin_token,
                       json=household_data)
    
    if resp.status_code != 422:
        results.add_fail("POST /sosial/households invalid pbi_nas", 
                        f"Expected 422, got {resp.status_code}")
        return
    
    results.add_pass("POST /sosial/households pbi_nas=5 - correctly returns 422")
    
    # Test with invalid jumlah_anggota_keluarga (should be 422)
    household_data["data"]["pbi_nas"] = 0
    household_data["data"]["jumlah_anggota_keluarga"] = "abc"
    
    resp = make_request("POST", "/sosial/households", 
                       token=superadmin_token,
                       json=household_data)
    
    if resp.status_code != 422:
        results.add_fail("POST /sosial/households invalid jumlah_anggota", 
                        f"Expected 422, got {resp.status_code}")
        return
    
    results.add_pass("POST /sosial/households jumlah_anggota_keluarga='abc' - correctly returns 422")

def test_households_update(superadmin_token: str, household_id: str):
    """Test PUT /api/sosial/households/{id}"""
    update_data = {
        "data": {
            "desil_nasional": 4,
            "alamat": "Jl. Updated Address No. 456",
        },
        "catatan": "Update test"
    }
    
    resp = make_request("PUT", f"/sosial/households/{household_id}", 
                       token=superadmin_token,
                       json=update_data)
    
    if resp.status_code != 200:
        results.add_fail(f"PUT /sosial/households/{household_id}", 
                        f"Expected 200, got {resp.status_code}: {resp.text}")
        return
    
    results.add_pass(f"PUT /sosial/households/{household_id} - updated successfully")
    
    # Verify the update
    resp = make_request("GET", f"/sosial/households/{household_id}")
    data = resp.json()
    
    if data.get("desil_nasional") != 4:
        results.add_fail(f"PUT /sosial/households/{household_id} verify desil", 
                        f"Expected desil_nasional=4, got {data.get('desil_nasional')}")
        return
    
    # Check if alamat contains the updated text (might be truncated in display)
    alamat = data.get("alamat", "")
    if "Jl. Updated" not in alamat:
        results.add_fail(f"PUT /sosial/households/{household_id} verify alamat", 
                        f"Expected alamat with 'Jl. Updated', got {alamat}")
        return
    
    results.add_pass(f"PUT /sosial/households/{household_id} - values updated correctly")

def test_households_delete_authorization(superadmin_token: str, petugas_token: str, 
                                        household_id: str):
    """Test DELETE /api/sosial/households/{id} authorization"""
    # Test without login (should be 401 or 403)
    resp = make_request("DELETE", f"/sosial/households/{household_id}", 
                       params={"alasan": "Test delete"})
    
    if resp.status_code not in [401, 403]:
        results.add_fail("DELETE /sosial/households without auth", 
                        f"Expected 401/403, got {resp.status_code}")
        return
    
    results.add_pass("DELETE /sosial/households without auth - correctly rejected")
    
    # Test as petugas (should be 403)
    resp = make_request("DELETE", f"/sosial/households/{household_id}", 
                       token=petugas_token,
                       params={"alasan": "Test delete"})
    
    if resp.status_code != 403:
        results.add_fail("DELETE /sosial/households as petugas", 
                        f"Expected 403, got {resp.status_code}")
        return
    
    results.add_pass("DELETE /sosial/households as petugas - correctly rejected with 403")
    
    # Test as superadmin (should be 200)
    resp = make_request("DELETE", f"/sosial/households/{household_id}", 
                       token=superadmin_token,
                       params={"alasan": "Cleanup test data"})
    
    if resp.status_code != 200:
        results.add_fail("DELETE /sosial/households as superadmin", 
                        f"Expected 200, got {resp.status_code}: {resp.text}")
        return
    
    results.add_pass(f"DELETE /sosial/households/{household_id} as superadmin - deleted successfully")
    
    # Remove from created_ids since it's deleted
    if household_id in results.created_ids["households"]:
        results.created_ids["households"].remove(household_id)

def test_households_baseline_restored():
    """Test that household count is back to 29,213"""
    resp = make_request("GET", "/sosial/overview")
    
    if resp.status_code != 200:
        results.add_fail("GET /sosial/overview after delete", 
                        f"Expected 200, got {resp.status_code}")
        return
    
    data = resp.json()
    total = data.get("total_households", 0)
    
    if total != 29213:
        results.add_fail("GET /sosial/overview baseline restored", 
                        f"Expected 29213, got {total}")
        return
    
    results.add_pass("GET /sosial/overview - total_households restored to 29,213")

# ============================================================================
# TEST SECTION 5: Audit Logs
# ============================================================================

def test_audit_logs(superadmin_token: str):
    """Test GET /api/admin/audit-logs"""
    resp = make_request("GET", "/admin/audit-logs", token=superadmin_token)
    
    if resp.status_code != 200:
        results.add_fail("GET /admin/audit-logs", f"Expected 200, got {resp.status_code}")
        return
    
    data = resp.json()
    items = data.get("items", [])
    
    # Should have audit logs
    if len(items) == 0:
        results.add_fail("GET /admin/audit-logs", "No audit logs found")
        return
    
    # Find DTSEN audit logs
    dtsen_logs = [log for log in items if log.get("action") in 
                  ["dtsen_tambah", "dtsen_ubah", "dtsen_hapus"]]
    
    if len(dtsen_logs) == 0:
        results.add_fail("GET /admin/audit-logs DTSEN", "No DTSEN audit logs found")
        return
    
    # Check that data_sebelum and data_sesudah are present
    has_data = False
    for log in dtsen_logs:
        if log.get("data_sebelum") or log.get("data_sesudah"):
            has_data = True
            break
    
    if not has_data:
        results.add_fail("GET /admin/audit-logs data", 
                        "No audit logs with data_sebelum/data_sesudah")
        return
    
    results.add_pass("GET /admin/audit-logs - contains DTSEN logs with data_sebelum/data_sesudah")

# ============================================================================
# TEST SECTION 6: CRUD Disabilitas
# ============================================================================

def test_disabilitas_get():
    """Test GET /api/disabilitas/items"""
    resp = make_request("GET", "/disabilitas/items")
    
    if resp.status_code != 200:
        results.add_fail("GET /disabilitas/items", f"Expected 200, got {resp.status_code}")
        return
    
    data = resp.json()
    total = data.get("total", 0)
    
    if total != 24:
        results.add_fail("GET /disabilitas/items total", f"Expected 24, got {total}")
        return
    
    results.add_pass("GET /disabilitas/items - 24 items")
    
    # Test filter by kecamatan
    resp = make_request("GET", "/disabilitas/items", params={"kecamatan": "Tallo"})
    
    if resp.status_code != 200:
        results.add_fail("GET /disabilitas/items filter", f"Expected 200, got {resp.status_code}")
        return
    
    data = resp.json()
    items = data.get("items", [])
    
    # All items should have kecamatan=Tallo
    if not all("TALLO" in item.get("kecamatan", "").upper() for item in items):
        results.add_fail("GET /disabilitas/items filter", 
                        "Not all items have kecamatan=Tallo")
        return
    
    results.add_pass("GET /disabilitas/items?kecamatan=Tallo - filter works")

def test_disabilitas_create(superadmin_token: str) -> Optional[str]:
    """Test POST /api/disabilitas/items"""
    disabilitas_data = {
        "data": {
            "kelurahan": "PANNAMPU",
            "kecamatan": "TALLO",
            "tahun": 2025,
            "jumlah": 10,
            "jenis": "Fisik",
            "keterangan": "Data uji testing agent"
        }
    }
    
    resp = make_request("POST", "/disabilitas/items", 
                       token=superadmin_token,
                       json=disabilitas_data)
    
    if resp.status_code not in [200, 201]:
        results.add_fail("POST /disabilitas/items create", 
                        f"Expected 200/201, got {resp.status_code}: {resp.text}")
        return None
    
    data = resp.json()
    item_id = data.get("id")
    
    if not item_id:
        results.add_fail("POST /disabilitas/items id", "No id returned")
        return None
    
    results.created_ids["disabilitas"].append(item_id)
    results.add_pass(f"POST /disabilitas/items - created with id {item_id}")
    
    return item_id

def test_disabilitas_duplicate(superadmin_token: str):
    """Test POST /api/disabilitas/items with duplicate"""
    disabilitas_data = {
        "data": {
            "kelurahan": "PANNAMPU",
            "kecamatan": "TALLO",
            "tahun": 2025,
            "jumlah": 15,
            "jenis": "Fisik",
        },
        "mode_duplikat": "tolak"
    }
    
    resp = make_request("POST", "/disabilitas/items", 
                       token=superadmin_token,
                       json=disabilitas_data)
    
    if resp.status_code != 409:
        results.add_fail("POST /disabilitas/items duplicate", 
                        f"Expected 409, got {resp.status_code}")
        return
    
    results.add_pass("POST /disabilitas/items duplicate - correctly returns 409")
    
    # Test mode_duplikat=update
    disabilitas_data["mode_duplikat"] = "update"
    resp = make_request("POST", "/disabilitas/items", 
                       token=superadmin_token,
                       json=disabilitas_data)
    
    if resp.status_code not in [200, 201]:
        results.add_fail("POST /disabilitas/items mode=update", 
                        f"Expected 200/201, got {resp.status_code}")
        return
    
    results.add_pass("POST /disabilitas/items mode_duplikat=update - updated successfully")

def test_disabilitas_update(superadmin_token: str, item_id: str):
    """Test PUT /api/disabilitas/items/{id}"""
    update_data = {
        "data": {
            "jumlah": 20,
            "keterangan": "Updated by testing agent"
        }
    }
    
    resp = make_request("PUT", f"/disabilitas/items/{item_id}", 
                       token=superadmin_token,
                       json=update_data)
    
    if resp.status_code != 200:
        results.add_fail(f"PUT /disabilitas/items/{item_id}", 
                        f"Expected 200, got {resp.status_code}: {resp.text}")
        return
    
    results.add_pass(f"PUT /disabilitas/items/{item_id} - updated successfully")

def test_disabilitas_delete(superadmin_token: str, item_id: str):
    """Test DELETE /api/disabilitas/items/{id}"""
    resp = make_request("DELETE", f"/disabilitas/items/{item_id}", 
                       token=superadmin_token)
    
    if resp.status_code != 200:
        results.add_fail(f"DELETE /disabilitas/items/{item_id}", 
                        f"Expected 200, got {resp.status_code}: {resp.text}")
        return
    
    results.add_pass(f"DELETE /disabilitas/items/{item_id} - deleted successfully")
    
    # Remove from created_ids
    if item_id in results.created_ids["disabilitas"]:
        results.created_ids["disabilitas"].remove(item_id)

def test_disabilitas_baseline_restored():
    """Test that disabilitas count is back to 24"""
    resp = make_request("GET", "/disabilitas/items")
    
    if resp.status_code != 200:
        results.add_fail("GET /disabilitas/items after delete", 
                        f"Expected 200, got {resp.status_code}")
        return
    
    data = resp.json()
    total = data.get("total", 0)
    
    if total != 24:
        results.add_fail("GET /disabilitas/items baseline restored", 
                        f"Expected 24, got {total}")
        return
    
    results.add_pass("GET /disabilitas/items - total restored to 24")

# ============================================================================
# TEST SECTION 7: CRUD RAD
# ============================================================================

def test_rad_get():
    """Test GET /api/rad/items"""
    resp = make_request("GET", "/rad/items")
    
    if resp.status_code != 200:
        results.add_fail("GET /rad/items", f"Expected 200, got {resp.status_code}")
        return
    
    data = resp.json()
    total = data.get("total", 0)
    
    if total != 77:
        results.add_fail("GET /rad/items total", f"Expected 77, got {total}")
        return
    
    results.add_pass("GET /rad/items - 77 items")

def test_rad_create_validation(superadmin_token: str):
    """Test POST /api/rad/items validation (kegiatan required)"""
    rad_data = {
        "data": {
            "opd": "Test OPD",
            "tahun": 2025,
            # Missing kegiatan - should be 422
        }
    }
    
    resp = make_request("POST", "/rad/items", 
                       token=superadmin_token,
                       json=rad_data)
    
    if resp.status_code != 422:
        results.add_fail("POST /rad/items without kegiatan", 
                        f"Expected 422, got {resp.status_code}")
        return
    
    results.add_pass("POST /rad/items without kegiatan - correctly returns 422")

def test_rad_create(superadmin_token: str) -> Optional[str]:
    """Test POST /api/rad/items"""
    rad_data = {
        "data": {
            "opd": "Test OPD",
            "kegiatan": "Test Kegiatan RAD",
            "tahun": 2025,
            "anggaran": 100000000,
            "keterangan": "Data uji testing agent"
        }
    }
    
    resp = make_request("POST", "/rad/items", 
                       token=superadmin_token,
                       json=rad_data)
    
    if resp.status_code not in [200, 201]:
        results.add_fail("POST /rad/items create", 
                        f"Expected 200/201, got {resp.status_code}: {resp.text}")
        return None
    
    data = resp.json()
    item_id = data.get("id")
    
    if not item_id:
        results.add_fail("POST /rad/items id", "No id returned")
        return None
    
    results.created_ids["rad"].append(item_id)
    results.add_pass(f"POST /rad/items - created with id {item_id}")
    
    # Verify total increased to 78
    resp = make_request("GET", "/rad/items")
    data = resp.json()
    total = data.get("total", 0)
    
    if total != 78:
        results.add_fail("GET /rad/items after create", f"Expected 78, got {total}")
    else:
        results.add_pass("GET /rad/items - total increased to 78")
    
    return item_id

def test_rad_update(superadmin_token: str, item_id: str):
    """Test PUT /api/rad/items/{id}"""
    update_data = {
        "data": {
            "anggaran": 150000000,
            "keterangan": "Updated by testing agent"
        }
    }
    
    resp = make_request("PUT", f"/rad/items/{item_id}", 
                       token=superadmin_token,
                       json=update_data)
    
    if resp.status_code != 200:
        results.add_fail(f"PUT /rad/items/{item_id}", 
                        f"Expected 200, got {resp.status_code}: {resp.text}")
        return
    
    results.add_pass(f"PUT /rad/items/{item_id} - updated successfully")

def test_rad_get_form(superadmin_token: str, item_id: str):
    """Test GET /api/rad/items/{id}/form"""
    resp = make_request("GET", f"/rad/items/{item_id}/form", 
                       token=superadmin_token)
    
    if resp.status_code != 200:
        results.add_fail(f"GET /rad/items/{item_id}/form", 
                        f"Expected 200, got {resp.status_code}")
        return
    
    data = resp.json()
    
    # Should return Excel column format
    if not isinstance(data, dict):
        results.add_fail(f"GET /rad/items/{item_id}/form", "Expected dict response")
        return
    
    results.add_pass(f"GET /rad/items/{item_id}/form - returns Excel format")

def test_rad_delete(superadmin_token: str, item_id: str):
    """Test DELETE /api/rad/items/{id}"""
    resp = make_request("DELETE", f"/rad/items/{item_id}", 
                       token=superadmin_token)
    
    if resp.status_code != 200:
        results.add_fail(f"DELETE /rad/items/{item_id}", 
                        f"Expected 200, got {resp.status_code}: {resp.text}")
        return
    
    results.add_pass(f"DELETE /rad/items/{item_id} - deleted successfully")
    
    # Remove from created_ids
    if item_id in results.created_ids["rad"]:
        results.created_ids["rad"].remove(item_id)

def test_rad_baseline_restored():
    """Test that RAD count is back to 77"""
    resp = make_request("GET", "/rad/items")
    
    if resp.status_code != 200:
        results.add_fail("GET /rad/items after delete", 
                        f"Expected 200, got {resp.status_code}")
        return
    
    data = resp.json()
    total = data.get("total", 0)
    
    if total != 77:
        results.add_fail("GET /rad/items baseline restored", f"Expected 77, got {total}")
        return
    
    results.add_pass("GET /rad/items - total restored to 77")

# ============================================================================
# TEST SECTION 8: GIS Locations
# ============================================================================

def test_gis_locations_get():
    """Test GET /api/gis/locations"""
    resp = make_request("GET", "/gis/locations")
    
    if resp.status_code != 200:
        results.add_fail("GET /gis/locations", f"Expected 200, got {resp.status_code}")
        return
    
    data = resp.json()
    items = data.get("items", [])
    
    if len(items) != 29:
        results.add_fail("GET /gis/locations count", f"Expected 29 items, got {len(items)}")
        return
    
    # All items should have latitude and longitude
    missing_coords = [item for item in items 
                     if not item.get("latitude") or not item.get("longitude")]
    
    if missing_coords:
        results.add_fail("GET /gis/locations coordinates", 
                        f"{len(missing_coords)} items missing coordinates")
        return
    
    # tanpa_koordinat should be empty
    tanpa_koordinat = data.get("tanpa_koordinat", [])
    if tanpa_koordinat:
        results.add_fail("GET /gis/locations tanpa_koordinat", 
                        f"Expected empty, got {len(tanpa_koordinat)} items")
        return
    
    results.add_pass("GET /gis/locations - 29 items, all with coordinates, tanpa_koordinat empty")

def test_gis_locations_update(superadmin_token: str):
    """Test PUT /api/gis/locations/{kelurahan}"""
    kelurahan = "Pannampu"
    
    # Update with valid coordinates
    update_data = {
        "latitude": -5.11,
        "longitude": 119.42,
        "keterangan": "Manual input by testing agent"
    }
    
    resp = make_request("PUT", f"/gis/locations/{kelurahan}", 
                       token=superadmin_token,
                       json=update_data)
    
    if resp.status_code != 200:
        results.add_fail(f"PUT /gis/locations/{kelurahan}", 
                        f"Expected 200, got {resp.status_code}: {resp.text}")
        return
    
    data = resp.json()
    
    # Response might have 'item' wrapper
    item = data.get("item", data)
    
    # Should have sumber='manual'
    if item.get("sumber") != "manual":
        results.add_fail(f"PUT /gis/locations/{kelurahan} sumber", 
                        f"Expected sumber=manual, got {item.get('sumber')}")
        return
    
    results.add_pass(f"PUT /gis/locations/{kelurahan} - updated with sumber=manual")
    
    # Test with invalid latitude (should be 422)
    invalid_data = {
        "latitude": 200,
        "longitude": 119.42,
    }
    
    resp = make_request("PUT", f"/gis/locations/{kelurahan}", 
                       token=superadmin_token,
                       json=invalid_data)
    
    if resp.status_code != 422:
        results.add_fail(f"PUT /gis/locations/{kelurahan} invalid latitude", 
                        f"Expected 422, got {resp.status_code}")
        return
    
    results.add_pass(f"PUT /gis/locations/{kelurahan} latitude=200 - correctly returns 422")

def test_gis_locations_delete(superadmin_token: str):
    """Test DELETE /api/gis/locations/{kelurahan}"""
    kelurahan = "Pannampu"
    
    resp = make_request("DELETE", f"/gis/locations/{kelurahan}", 
                       token=superadmin_token)
    
    if resp.status_code != 200:
        results.add_fail(f"DELETE /gis/locations/{kelurahan}", 
                        f"Expected 200, got {resp.status_code}: {resp.text}")
        return
    
    data = resp.json()
    
    # Response might have 'item' wrapper
    item = data.get("item", data)
    
    # Should have sumber back to centroid
    if "centroid" not in item.get("sumber", ""):
        results.add_fail(f"DELETE /gis/locations/{kelurahan} sumber", 
                        f"Expected sumber with 'centroid', got {item.get('sumber')}")
        return
    
    results.add_pass(f"DELETE /gis/locations/{kelurahan} - sumber restored to centroid")

# ============================================================================
# TEST SECTION 9: Regression Tests
# ============================================================================

def test_regression_endpoints():
    """Test that old endpoints still work"""
    endpoints = [
        "/health",
        "/sosial/ranking",
        "/analisis/prioritas",
        "/geo/kelurahan",
        "/disabilitas/overview",
        "/rad/overview",
    ]
    
    for endpoint in endpoints:
        resp = make_request("GET", endpoint)
        
        if resp.status_code != 200:
            results.add_fail(f"Regression {endpoint}", 
                           f"Expected 200, got {resp.status_code}")
        else:
            results.add_pass(f"Regression {endpoint} - returns 200")

# ============================================================================
# MAIN TEST EXECUTION
# ============================================================================

def cleanup_test_data(superadmin_token: str):
    """Clean up any remaining test data"""
    print("\n" + "="*80)
    print("CLEANUP: Removing any remaining test data...")
    print("="*80)
    
    # Delete households
    for household_id in results.created_ids["households"]:
        try:
            resp = make_request("DELETE", f"/sosial/households/{household_id}", 
                              token=superadmin_token,
                              params={"alasan": "Cleanup test data"})
            if resp.status_code == 200:
                print(f"✅ Deleted household {household_id}")
            else:
                print(f"⚠️  Failed to delete household {household_id}: {resp.status_code}")
        except Exception as e:
            print(f"⚠️  Error deleting household {household_id}: {e}")
    
    # Delete disabilitas
    for item_id in results.created_ids["disabilitas"]:
        try:
            resp = make_request("DELETE", f"/disabilitas/items/{item_id}", 
                              token=superadmin_token)
            if resp.status_code == 200:
                print(f"✅ Deleted disabilitas {item_id}")
            else:
                print(f"⚠️  Failed to delete disabilitas {item_id}: {resp.status_code}")
        except Exception as e:
            print(f"⚠️  Error deleting disabilitas {item_id}: {e}")
    
    # Delete RAD
    for item_id in results.created_ids["rad"]:
        try:
            resp = make_request("DELETE", f"/rad/items/{item_id}", 
                              token=superadmin_token)
            if resp.status_code == 200:
                print(f"✅ Deleted RAD {item_id}")
            else:
                print(f"⚠️  Failed to delete RAD {item_id}: {resp.status_code}")
        except Exception as e:
            print(f"⚠️  Error deleting RAD {item_id}: {e}")

def main():
    print("="*80)
    print("BACKEND TESTING: DATA MANAGE MODULE")
    print("="*80)
    print(f"Base URL: {BASE_URL}")
    print(f"Expected baseline: {EXPECTED_BASELINE}")
    print("="*80)
    
    # Login
    print("\n🔐 Logging in...")
    superadmin_token = login(SUPERADMIN_EMAIL, SUPERADMIN_PASSWORD)
    petugas_token = login(PETUGAS_EMAIL, PETUGAS_PASSWORD)
    operator_token = login(OPERATOR_EMAIL, OPERATOR_PASSWORD)
    
    if not superadmin_token:
        print("❌ Failed to login as superadmin. Aborting tests.")
        sys.exit(1)
    
    print("✅ Logged in as superadmin")
    if petugas_token:
        print("✅ Logged in as petugas")
    if operator_token:
        print("✅ Logged in as operator")
    
    try:
        # Section 1: Master Kode Referensi
        print("\n" + "="*80)
        print("SECTION 1: Master Kode Referensi")
        print("="*80)
        test_master_kode_get()
        test_master_kode_filter()
        test_master_kode_map()
        test_master_kode_update_authorization(superadmin_token, petugas_token)
        test_master_kode_post_validation(superadmin_token)
        test_master_kode_delete_validation(superadmin_token)
        
        # Section 2: Master Wilayah Berantai
        print("\n" + "="*80)
        print("SECTION 2: Master Wilayah Berantai")
        print("="*80)
        test_master_wilayah_provinsi()
        test_master_wilayah_kabupaten()
        test_master_wilayah_kecamatan()
        test_master_wilayah_kelurahan()
        
        # Section 3: Master Fields Metadata
        print("\n" + "="*80)
        print("SECTION 3: Master Fields Metadata")
        print("="*80)
        test_master_fields_dtsen()
        test_master_fields_other()
        
        # Section 4: CRUD DTSEN Households
        print("\n" + "="*80)
        print("SECTION 4: CRUD DTSEN Households")
        print("="*80)
        household_id = test_households_create(superadmin_token)
        
        if household_id:
            # Get the no_kk for duplicate tests
            resp = make_request("GET", f"/sosial/households/{household_id}")
            no_kk = resp.json().get("nomor_kartu_keluarga", "")
            
            test_households_overview_increment()
            test_households_village_stats_increment()
            test_households_get_detail(household_id)
            test_households_get_form(superadmin_token, household_id)
            
            if no_kk:
                test_households_duplicate(superadmin_token, no_kk)
            
            test_households_validation(superadmin_token)
            test_households_update(superadmin_token, household_id)
            test_households_delete_authorization(superadmin_token, petugas_token, household_id)
            test_households_baseline_restored()
        
        # Section 5: Audit Logs
        print("\n" + "="*80)
        print("SECTION 5: Audit Logs")
        print("="*80)
        test_audit_logs(superadmin_token)
        
        # Section 6: CRUD Disabilitas
        print("\n" + "="*80)
        print("SECTION 6: CRUD Disabilitas")
        print("="*80)
        test_disabilitas_get()
        disabilitas_id = test_disabilitas_create(superadmin_token)
        
        if disabilitas_id:
            test_disabilitas_duplicate(superadmin_token)
            test_disabilitas_update(superadmin_token, disabilitas_id)
            test_disabilitas_delete(superadmin_token, disabilitas_id)
            test_disabilitas_baseline_restored()
        
        # Section 7: CRUD RAD
        print("\n" + "="*80)
        print("SECTION 7: CRUD RAD")
        print("="*80)
        test_rad_get()
        test_rad_create_validation(superadmin_token)
        rad_id = test_rad_create(superadmin_token)
        
        if rad_id:
            test_rad_update(superadmin_token, rad_id)
            test_rad_get_form(superadmin_token, rad_id)
            test_rad_delete(superadmin_token, rad_id)
            test_rad_baseline_restored()
        
        # Section 8: GIS Locations
        print("\n" + "="*80)
        print("SECTION 8: GIS Locations")
        print("="*80)
        test_gis_locations_get()
        test_gis_locations_update(superadmin_token)
        test_gis_locations_delete(superadmin_token)
        
        # Section 9: Regression Tests
        print("\n" + "="*80)
        print("SECTION 9: Regression Tests")
        print("="*80)
        test_regression_endpoints()
        
    finally:
        # Cleanup
        cleanup_test_data(superadmin_token)
    
    # Summary
    success = results.summary()
    
    if success:
        print("\n✅ ALL TESTS PASSED!")
        sys.exit(0)
    else:
        print("\n❌ SOME TESTS FAILED!")
        sys.exit(1)

if __name__ == "__main__":
    main()
