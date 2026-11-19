#!/usr/bin/env python3
"""
Backend testing for IMPORT WIZARD module (/api/import/*)
CRITICAL: households must remain 29,213 and individu 106,863 after all tests
Use mode "skip" for DTSEN imports, gis_koordinat for write/rollback tests
"""
import io
import json
import os
import time
from pathlib import Path

import requests

# Backend URL from environment
BACKEND_URL = os.environ.get("REACT_APP_BACKEND_URL", "https://backend-recovery-16.preview.emergentagent.com")
BASE_URL = f"{BACKEND_URL}/api"

# Test credentials
SUPERADMIN_EMAIL = "admin@bappeda.makassarkota.go.id"
SUPERADMIN_PASSWORD = os.environ.get("TEST_ADMIN_PASSWORD", "")
PETUGAS_EMAIL = "petugas.tallo@makassarkota.go.id"
PETUGAS_PASSWORD = os.environ.get("TEST_PETUGAS_PASSWORD", "")
PIMPINAN_EMAIL = None  # Will create if needed

# Test files
LARIANG_BANGI_PATH = "/app/data_upload/Bahan Website Ibu Kabid/PILAH DTSEN KEC. MAKASSAR/LARIANG BANGI.xlsx"
TALLO_PATH = "/app/data_upload/Bahan Website Ibu Kabid/Pilah DTSEN KEC TALLO.xlsx"

# Reference numbers - MUST NOT CHANGE
EXPECTED_HOUSEHOLDS = 29213
EXPECTED_INDIVIDU = 106863

# Test results
test_results = []
session = requests.Session()


def log_test(name, passed, details=""):
    """Log test result"""
    status = "✅ PASS" if passed else "❌ FAIL"
    test_results.append({"name": name, "passed": passed, "details": details})
    print(f"{status}: {name}")
    if details:
        print(f"  {details}")


def login(email, password):
    """Login and return session with cookie"""
    resp = session.post(f"{BASE_URL}/auth/login", json={"email": email, "password": password})
    if resp.status_code == 200:
        print(f"✓ Logged in as {email}")
        return True
    else:
        print(f"✗ Login failed for {email}: {resp.status_code}")
        return False


def logout():
    """Logout"""
    session.cookies.clear()


def test_1_datasets():
    """Test 1: GET /api/import/datasets"""
    print("\n=== TEST 1: GET /api/import/datasets ===")
    resp = session.get(f"{BASE_URL}/import/datasets")
    
    if resp.status_code != 200:
        log_test("GET /import/datasets", False, f"Status {resp.status_code}")
        return
    
    data = resp.json()
    datasets = data.get("datasets", [])
    
    # Check 4 types
    types = [d.get("jenis") or d.get("id") for d in datasets]
    expected_types = ["dtsen", "disabilitas", "rad", "gis_koordinat"]
    
    if set(types) == set(expected_types):
        log_test("GET /import/datasets - 4 types", True, f"Types: {types}")
    else:
        log_test("GET /import/datasets - 4 types", False, f"Expected {expected_types}, got {types}")
    
    # Check each has fields
    for ds in datasets:
        ds_id = ds.get("jenis") or ds.get("id", "unknown")
        if "fields" in ds and len(ds["fields"]) > 0:
            log_test(f"Dataset {ds_id} has fields", True, f"{len(ds['fields'])} fields")
        else:
            log_test(f"Dataset {ds_id} has fields", False, "No fields found")


def test_2_template():
    """Test 2: GET /api/import/template"""
    print("\n=== TEST 2: GET /api/import/template ===")
    resp = session.get(f"{BASE_URL}/import/template")
    
    if resp.status_code != 200:
        log_test("GET /import/template", False, f"Status {resp.status_code}")
        return
    
    # Check content type
    ct = resp.headers.get("content-type", "")
    if "spreadsheet" in ct or "excel" in ct:
        log_test("GET /import/template - content-type", True, ct)
    else:
        log_test("GET /import/template - content-type", False, f"Unexpected: {ct}")
    
    # Check size > 5KB
    size = len(resp.content)
    if size > 5000:
        log_test("GET /import/template - size", True, f"{size} bytes")
    else:
        log_test("GET /import/template - size", False, f"Only {size} bytes")


def test_3_upload():
    """Test 3: POST /api/import/upload"""
    print("\n=== TEST 3: POST /api/import/upload ===")
    
    # Test 3a: Upload LARIANG BANGI.xlsx (multi-sheet)
    if not Path(LARIANG_BANGI_PATH).exists():
        log_test("Upload LARIANG BANGI.xlsx", False, f"File not found: {LARIANG_BANGI_PATH}")
        return None
    
    with open(LARIANG_BANGI_PATH, "rb") as f:
        files = {"file": ("LARIANG BANGI.xlsx", f, "application/vnd.openxmlformats-officedocument.spreadsheetml.sheet")}
        resp = session.post(f"{BASE_URL}/import/upload", files=files)
    
    if resp.status_code != 200:
        log_test("Upload LARIANG BANGI.xlsx", False, f"Status {resp.status_code}: {resp.text[:200]}")
        return None
    
    data = resp.json()
    session_id = data.get("session_id")
    sheets = data.get("sheets", [])
    
    # Check sheets
    if len(sheets) >= 1:
        sheet = sheets[0]
        rows = sheet.get("rows", 0)
        cols = sheet.get("cols", 0)
        
        # Expected: 1 sheet, 225 rows, 28 cols
        if rows == 225 and cols == 28:
            log_test("Upload LARIANG BANGI.xlsx - rows/cols", True, f"1 sheet, {rows} rows, {cols} cols")
        else:
            log_test("Upload LARIANG BANGI.xlsx - rows/cols", False, f"Expected 225 rows, 28 cols; got {rows} rows, {cols} cols")
        
        # Check preview
        if "preview" in sheet and len(sheet["preview"]) > 0:
            log_test("Upload LARIANG BANGI.xlsx - preview", True, f"{len(sheet['preview'])} preview rows")
        else:
            log_test("Upload LARIANG BANGI.xlsx - preview", False, "No preview data")
    else:
        log_test("Upload LARIANG BANGI.xlsx - sheets", False, f"Expected 1+ sheets, got {len(sheets)}")
        session_id = None
    
    # Test 3b: Upload CSV
    csv_content = """kelurahan,latitude,longitude,keterangan
Kaluku Bodoa,-5.1478,119.4328,Test Point 1
Rappokalling,-5.1485,119.4335,Test Point 2"""
    
    files = {"file": ("test_gis.csv", io.BytesIO(csv_content.encode()), "text/csv")}
    resp = session.post(f"{BASE_URL}/import/upload", files=files)
    
    if resp.status_code == 200:
        data = resp.json()
        if len(data.get("sheets", [])) == 1:
            csv_rows = data['sheets'][0].get('rows', 0)
            log_test("Upload CSV", True, f"CSV uploaded, {csv_rows} rows")
        else:
            log_test("Upload CSV", False, "CSV upload succeeded but unexpected structure")
    else:
        log_test("Upload CSV", False, f"Status {resp.status_code}")
    
    # Test 3c: Invalid format (.txt)
    files = {"file": ("test.txt", io.BytesIO(b"invalid content"), "text/plain")}
    resp = session.post(f"{BASE_URL}/import/upload", files=files)
    
    if resp.status_code == 422:
        log_test("Upload invalid format (.txt) - 422", True, "Correctly rejected")
    else:
        log_test("Upload invalid format (.txt) - 422", False, f"Expected 422, got {resp.status_code}")
    
    # Test 3d: Corrupted file
    files = {"file": ("corrupted.xlsx", io.BytesIO(b"not a real xlsx file"), "application/vnd.openxmlformats-officedocument.spreadsheetml.sheet")}
    resp = session.post(f"{BASE_URL}/import/upload", files=files)
    
    if resp.status_code == 422:
        error_msg = resp.json().get("detail", "")
        # Check for friendly message (not traceback)
        if "traceback" not in error_msg.lower() and "exception" not in error_msg.lower():
            log_test("Upload corrupted file - friendly error", True, f"Error: {error_msg[:100]}")
        else:
            log_test("Upload corrupted file - friendly error", False, "Error message contains traceback")
    else:
        log_test("Upload corrupted file - 422", False, f"Expected 422, got {resp.status_code}")
    
    return session_id


def test_4_analyze(session_id):
    """Test 4: POST /api/import/analyze"""
    print("\n=== TEST 4: POST /api/import/analyze ===")
    
    if not session_id:
        print("Skipping analyze tests - no session_id")
        return None
    
    # Test 4a: Auto-detect DTSEN
    payload = {"session_id": session_id}
    resp = session.post(f"{BASE_URL}/import/analyze", json=payload)
    
    if resp.status_code != 200:
        log_test("Analyze - auto-detect", False, f"Status {resp.status_code}: {resp.text[:200]}")
        return None
    
    data = resp.json()
    detected_type = data.get("jenis")
    sheets = data.get("sheets", [])
    
    if detected_type == "dtsen":
        log_test("Analyze - detect dtsen", True, f"Detected: {detected_type}")
    else:
        log_test("Analyze - detect dtsen", False, f"Expected dtsen, got {detected_type}")
    
    # Check first sheet mapping
    if len(sheets) > 0:
        first_sheet = sheets[0]
        mappings = first_sheet.get("mapping", {})
        unmapped = first_sheet.get("wajib_belum_terpetakan", [])
        
        # Check auto-mapping (should map 28 columns)
        mapped_count = len([m for m in mappings.values() if m])
        if mapped_count >= 28:
            log_test("Analyze - auto-mapping 28 cols", True, f"{mapped_count} columns mapped")
        else:
            log_test("Analyze - auto-mapping 28 cols", False, f"Only {mapped_count} columns mapped")
        
        # Check no unmapped required fields
        if len(unmapped) == 0:
            log_test("Analyze - no unmapped required", True, "All required fields mapped")
        else:
            log_test("Analyze - no unmapped required", False, f"Unmapped: {unmapped}")
    else:
        log_test("Analyze - sheets", False, "No sheets returned")
    
    # Test 4b: Manual type change
    payload = {"session_id": session_id, "jenis": "disabilitas"}
    resp = session.post(f"{BASE_URL}/import/analyze", json=payload)
    
    if resp.status_code == 200:
        log_test("Analyze - manual type change", True, "Accepted disabilitas type")
    else:
        log_test("Analyze - manual type change", False, f"Status {resp.status_code}")
    
    # Test 4c: Invalid type
    payload = {"session_id": session_id, "jenis": "invalid_type"}
    resp = session.post(f"{BASE_URL}/import/analyze", json=payload)
    
    if resp.status_code == 422:
        log_test("Analyze - invalid type - 422", True, "Correctly rejected")
    else:
        log_test("Analyze - invalid type - 422", False, f"Expected 422, got {resp.status_code}")
    
    return data


def test_5_validate(session_id):
    """Test 5: POST /api/import/validate"""
    print("\n=== TEST 5: POST /api/import/validate ===")
    
    if not session_id:
        print("Skipping validate tests - no session_id")
        return None
    
    # Test 5a: Valid LARIANG BANGI data
    # First re-analyze to get proper mapping
    payload = {"session_id": session_id}
    resp = session.post(f"{BASE_URL}/import/analyze", json=payload)
    if resp.status_code != 200:
        log_test("Validate - re-analyze", False, f"Status {resp.status_code}")
        return None
    
    analyze_data = resp.json()
    sheets = analyze_data.get("sheets", [])
    if len(sheets) == 0:
        log_test("Validate - get mapping", False, "No sheets in analyze response")
        return None
    
    mapping = sheets[0].get("mapping", {})
    
    # Validate
    payload = {
        "session_id": session_id,
        "jenis": "dtsen",
        "mapping": mapping
    }
    resp = session.post(f"{BASE_URL}/import/validate", json=payload)
    
    if resp.status_code != 200:
        log_test("Validate LARIANG BANGI", False, f"Status {resp.status_code}: {resp.text[:200]}")
        return None
    
    data = resp.json()
    total = data.get("total", 0)
    valid = data.get("valid", 0)
    errors = data.get("errors", 0)
    duplikat_db = data.get("duplikat_db", 0)
    
    # Expected: 225 total, 225 valid, 0 errors, 225 duplikat_db
    if total == 225:
        log_test("Validate - total 225", True, f"Total: {total}")
    else:
        log_test("Validate - total 225", False, f"Expected 225, got {total}")
    
    if valid == 225 and errors == 0:
        log_test("Validate - 225 valid, 0 errors", True, f"Valid: {valid}, Errors: {errors}")
    else:
        log_test("Validate - 225 valid, 0 errors", False, f"Valid: {valid}, Errors: {errors}")
    
    if duplikat_db == 225:
        log_test("Validate - 225 duplikat_db", True, f"Duplikat DB: {duplikat_db}")
    else:
        log_test("Validate - 225 duplikat_db", False, f"Expected 225, got {duplikat_db}")
    
    # Test 5b: Negative validation - create CSV with errors
    csv_bad = """nomor_kartu_keluarga,kelurahan_desa,desil_nasional,pbi_nas,jumlah_anggota_keluarga
7371010101010001,,99,5,abc"""
    
    files = {"file": ("bad_dtsen.csv", io.BytesIO(csv_bad.encode()), "text/csv")}
    resp = session.post(f"{BASE_URL}/import/upload", files=files)
    
    if resp.status_code != 200:
        log_test("Validate - upload bad CSV", False, f"Status {resp.status_code}")
        return data
    
    bad_session_id = resp.json().get("session_id")
    
    # Analyze
    payload = {"session_id": bad_session_id, "jenis": "dtsen"}
    resp = session.post(f"{BASE_URL}/import/analyze", json=payload)
    if resp.status_code != 200:
        log_test("Validate - analyze bad CSV", False, f"Status {resp.status_code}")
        return data
    
    bad_sheets = resp.json().get("sheets", [])
    if len(bad_sheets) == 0:
        log_test("Validate - get bad mapping", False, "No sheets")
        return data
    
    bad_mapping = bad_sheets[0].get("mapping", {})
    
    # Validate bad data
    payload = {
        "session_id": bad_session_id,
        "jenis": "dtsen",
        "mapping": bad_mapping
    }
    resp = session.post(f"{BASE_URL}/import/validate", json=payload)
    
    if resp.status_code == 200:
        bad_data = resp.json()
        issues = bad_data.get("issues", [])
        
        # Check for expected errors
        error_types = [issue.get("jenis") for issue in issues]
        
        has_desil_error = any("desil" in str(issue).lower() for issue in issues)
        has_pbi_error = any("pbi" in str(issue).lower() for issue in issues)
        has_kelurahan_error = any("kelurahan" in str(issue).lower() or "kosong" in str(issue).lower() for issue in issues)
        has_numeric_error = any("jumlah" in str(issue).lower() or "angka" in str(issue).lower() for issue in issues)
        
        if has_desil_error:
            log_test("Validate - desil=99 error", True, "Desil validation error found")
        else:
            log_test("Validate - desil=99 error", False, "No desil validation error")
        
        if has_pbi_error:
            log_test("Validate - pbi=5 error", True, "PBI validation error found")
        else:
            log_test("Validate - pbi=5 error", False, "No PBI validation error")
        
        if has_kelurahan_error:
            log_test("Validate - empty kelurahan error", True, "Kelurahan validation error found")
        else:
            log_test("Validate - empty kelurahan error", False, "No kelurahan validation error")
        
        if has_numeric_error:
            log_test("Validate - non-numeric jumlah_anggota error", True, "Numeric validation error found")
        else:
            log_test("Validate - non-numeric jumlah_anggota error", False, "No numeric validation error")
    else:
        log_test("Validate - bad data", False, f"Status {resp.status_code}")
    
    return data


def test_6_errors(session_id):
    """Test 6: GET /api/import/errors/{session_id}"""
    print("\n=== TEST 6: GET /api/import/errors/{session_id} ===")
    
    if not session_id:
        print("Skipping errors tests - no session_id")
        return
    
    # Test 6a: Download XLSX
    resp = session.get(f"{BASE_URL}/import/errors/{session_id}?format=xlsx")
    
    if resp.status_code == 200:
        ct = resp.headers.get("content-type", "")
        if "spreadsheet" in ct or "excel" in ct:
            log_test("GET /import/errors - xlsx", True, f"Downloaded {len(resp.content)} bytes")
        else:
            log_test("GET /import/errors - xlsx", False, f"Wrong content-type: {ct}")
    else:
        log_test("GET /import/errors - xlsx", False, f"Status {resp.status_code}")
    
    # Test 6b: Download CSV
    resp = session.get(f"{BASE_URL}/import/errors/{session_id}?format=csv")
    
    if resp.status_code == 200:
        ct = resp.headers.get("content-type", "")
        if "csv" in ct or "text" in ct:
            log_test("GET /import/errors - csv", True, f"Downloaded {len(resp.content)} bytes")
        else:
            log_test("GET /import/errors - csv", False, f"Wrong content-type: {ct}")
    else:
        log_test("GET /import/errors - csv", False, f"Status {resp.status_code}")


def test_7_execute_skip(session_id):
    """Test 7: POST /api/import/execute with mode=skip"""
    print("\n=== TEST 7: POST /api/import/execute (mode=skip) ===")
    
    if not session_id:
        print("Skipping execute tests - no session_id")
        return None
    
    # Get current households count
    resp = session.get(f"{BASE_URL}/sosial/overview")
    if resp.status_code == 200:
        before_count = resp.json().get("total_households", 0)
        print(f"  Households before: {before_count}")
    else:
        before_count = EXPECTED_HOUSEHOLDS
    
    # Re-analyze and validate first
    payload = {"session_id": session_id}
    resp = session.post(f"{BASE_URL}/import/analyze", json=payload)
    if resp.status_code != 200:
        log_test("Execute - re-analyze", False, f"Status {resp.status_code}")
        return None
    
    sheets = resp.json().get("sheets", [])
    if len(sheets) == 0:
        log_test("Execute - get sheets", False, "No sheets")
        return None
    
    mapping = sheets[0].get("mapping", {})
    
    payload = {
        "session_id": session_id,
        "jenis": "dtsen",
        "mapping": mapping
    }
    resp = session.post(f"{BASE_URL}/import/validate", json=payload)
    if resp.status_code != 200:
        log_test("Execute - re-validate", False, f"Status {resp.status_code}")
        return None
    
    # Execute with mode=skip
    payload = {
        "session_id": session_id,
        "jenis": "dtsen",
        "mapping": mapping,
        "mode": "skip"
    }
    resp = session.post(f"{BASE_URL}/import/execute", json=payload)
    
    if resp.status_code != 200:
        log_test("Execute - mode=skip", False, f"Status {resp.status_code}: {resp.text[:200]}")
        return None
    
    data = resp.json()
    job_id = data.get("job_id")
    
    if not job_id:
        log_test("Execute - job_id", False, "No job_id returned")
        return None
    
    log_test("Execute - job_id", True, f"Job ID: {job_id}")
    
    # Poll job status
    max_wait = 60
    start = time.time()
    job_data = None
    
    while time.time() - start < max_wait:
        resp = session.get(f"{BASE_URL}/import/job/{job_id}")
        if resp.status_code == 200:
            job_data = resp.json()
            status = job_data.get("status")
            progress = job_data.get("persen", 0)
            
            print(f"  Job status: {status}, progress: {progress}%")
            
            if status in ["selesai", "gagal", "completed", "failed"]:
                break
        
        time.sleep(2)
    
    if not job_data:
        log_test("Execute - job polling", False, "Failed to get job status")
        return None
    
    # Check job results
    if job_data.get("status") in ["selesai", "completed"]:
        log_test("Execute - job completed", True, "Job completed successfully")
        
        skipped = job_data.get("skipped", 0)
        inserted = job_data.get("inserted", 0)
        
        if skipped == 225 and inserted == 0:
            log_test("Execute - 225 skipped, 0 inserted", True, f"Skipped: {skipped}, Inserted: {inserted}")
        else:
            log_test("Execute - 225 skipped, 0 inserted", False, f"Skipped: {skipped}, Inserted: {inserted}")
    else:
        log_test("Execute - job completed", False, f"Job status: {job_data.get('status')}")
    
    # Verify households count unchanged
    resp = session.get(f"{BASE_URL}/sosial/overview")
    if resp.status_code == 200:
        after_count = resp.json().get("total_households", 0)
        print(f"  Households after: {after_count}")
        
        if after_count == before_count:
            log_test("Execute - households unchanged", True, f"Still {after_count}")
        else:
            log_test("Execute - households unchanged", False, f"Changed from {before_count} to {after_count}")
    
    return job_id


def test_8_execute_gis():
    """Test 8: Import gis_koordinat CSV with insert and update"""
    print("\n=== TEST 8: Import gis_koordinat (insert + update) ===")
    
    # Create CSV with 2 rows
    csv_content = """kelurahan,latitude,longitude,keterangan
Kaluku Bodoa,-5.1478,119.4328,Test Point 1
Rappokalling,-5.1485,119.4335,Test Point 2"""
    
    # Upload
    files = {"file": ("test_gis.csv", io.BytesIO(csv_content.encode()), "text/csv")}
    resp = session.post(f"{BASE_URL}/import/upload", files=files)
    
    if resp.status_code != 200:
        log_test("GIS - upload CSV", False, f"Status {resp.status_code}")
        return None
    
    session_id = resp.json().get("session_id")
    
    # Analyze
    payload = {"session_id": session_id, "jenis": "gis_koordinat"}
    resp = session.post(f"{BASE_URL}/import/analyze", json=payload)
    
    if resp.status_code != 200:
        log_test("GIS - analyze", False, f"Status {resp.status_code}")
        return None
    
    sheets = resp.json().get("sheets", [])
    if len(sheets) == 0:
        log_test("GIS - get sheets", False, "No sheets")
        return None
    
    mapping = sheets[0].get("mapping", {})
    
    # Validate
    payload = {
        "session_id": session_id,
        "jenis": "gis_koordinat",
        "mapping": mapping
    }
    resp = session.post(f"{BASE_URL}/import/validate", json=payload)
    
    if resp.status_code != 200:
        log_test("GIS - validate", False, f"Status {resp.status_code}")
        return None
    
    # Execute with mode=insert (or update since gis_koordinat doesn't have strict mode requirements)
    payload = {
        "session_id": session_id,
        "jenis": "gis_koordinat",
        "mapping": mapping,
        "mode": "update"  # Use update mode which will insert if not exists
    }
    resp = session.post(f"{BASE_URL}/import/execute", json=payload)
    
    if resp.status_code != 200:
        log_test("GIS - execute insert", False, f"Status {resp.status_code}")
        return None
    
    job_id = resp.json().get("job_id")
    
    # Wait for completion
    max_wait = 30
    start = time.time()
    job_data = None
    
    while time.time() - start < max_wait:
        resp = session.get(f"{BASE_URL}/import/job/{job_id}")
        if resp.status_code == 200:
            job_data = resp.json()
            if job_data.get("status") in ["selesai", "gagal", "completed", "failed"]:
                break
        time.sleep(1)
    
    if job_data and job_data.get("status") in ["selesai", "completed"]:
        inserted = job_data.get("inserted", 0)
        updated = job_data.get("updated", 0)
        total_changed = inserted + updated
        
        if total_changed == 2:
            log_test("GIS - inserted/updated 2", True, f"Inserted: {inserted}, Updated: {updated}")
        else:
            log_test("GIS - inserted/updated 2", False, f"Expected 2 total, got {total_changed}")
    else:
        log_test("GIS - insert completed", False, f"Status: {job_data.get('status') if job_data else 'unknown'}")
        return None
    
    # Now test update mode - upload same CSV again
    files = {"file": ("test_gis_update.csv", io.BytesIO(csv_content.encode()), "text/csv")}
    resp = session.post(f"{BASE_URL}/import/upload", files=files)
    
    if resp.status_code != 200:
        log_test("GIS - upload for update", False, f"Status {resp.status_code}")
        return job_id
    
    session_id2 = resp.json().get("session_id")
    
    # Analyze
    payload = {"session_id": session_id2, "jenis": "gis_koordinat"}
    resp = session.post(f"{BASE_URL}/import/analyze", json=payload)
    sheets2 = resp.json().get("sheets", [])
    if len(sheets2) == 0:
        log_test("GIS - get sheets for update", False, "No sheets")
        return job_id
    
    mapping2 = sheets2[0].get("mapping", {})
    
    # Validate
    payload = {
        "session_id": session_id2,
        "jenis": "gis_koordinat",
        "mapping": mapping2
    }
    resp = session.post(f"{BASE_URL}/import/validate", json=payload)
    
    # Execute with mode=update
    payload = {
        "session_id": session_id2,
        "jenis": "gis_koordinat",
        "mapping": mapping2,
        "mode": "update"
    }
    resp = session.post(f"{BASE_URL}/import/execute", json=payload)
    
    if resp.status_code != 200:
        log_test("GIS - execute update", False, f"Status {resp.status_code}")
        return job_id
    
    job_id2 = resp.json().get("job_id")
    
    # Wait for completion
    start = time.time()
    job_data2 = None
    
    while time.time() - start < max_wait:
        resp = session.get(f"{BASE_URL}/import/job/{job_id2}")
        if resp.status_code == 200:
            job_data2 = resp.json()
            if job_data2.get("status") in ["selesai", "gagal", "completed", "failed"]:
                break
        time.sleep(1)
    
    if job_data2 and job_data2.get("status") in ["selesai", "completed"]:
        updated = job_data2.get("updated", 0)
        skipped = job_data2.get("skipped", 0)
        
        # Should update or skip the 2 existing records
        if updated + skipped >= 2:
            log_test("GIS - updated/skipped 2", True, f"Updated: {updated}, Skipped: {skipped}")
        else:
            log_test("GIS - updated/skipped 2", False, f"Expected 2 total, got {updated + skipped}")
    else:
        log_test("GIS - update completed", False, f"Status: {job_data2.get('status') if job_data2 else 'unknown'}")
    
    return job_id


def test_9_history():
    """Test 9: GET /api/import/history"""
    print("\n=== TEST 9: GET /api/import/history ===")
    
    resp = session.get(f"{BASE_URL}/import/history")
    
    if resp.status_code != 200:
        log_test("GET /import/history", False, f"Status {resp.status_code}")
        return
    
    data = resp.json()
    items = data.get("items", [])
    
    if len(items) > 0:
        log_test("GET /import/history - has items", True, f"{len(items)} batches")
        
        # Check latest batch
        latest = items[0]
        if latest.get("status") == "success":
            log_test("GET /import/history - latest success", True, f"Batch: {latest.get('batch_id')}")
        else:
            log_test("GET /import/history - latest success", False, f"Status: {latest.get('status')}")
    else:
        log_test("GET /import/history - has items", False, "No batches found")


def test_10_rollback(gis_job_id):
    """Test 10: DELETE /api/import/batch/{id}"""
    print("\n=== TEST 10: DELETE /api/import/batch/{id} ===")
    
    if not gis_job_id:
        print("Skipping rollback tests - no gis job_id")
        return
    
    # Get batch_id from job
    resp = session.get(f"{BASE_URL}/import/job/{gis_job_id}")
    if resp.status_code != 200:
        log_test("Rollback - get batch_id", False, f"Status {resp.status_code}")
        return
    
    batch_id = resp.json().get("batch_id")
    if not batch_id:
        log_test("Rollback - get batch_id", False, "No batch_id in job")
        return
    
    # Test 10a: Rollback as superadmin
    resp = session.delete(f"{BASE_URL}/import/batch/{batch_id}")
    
    if resp.status_code == 200:
        log_test("Rollback - superadmin success", True, f"Batch {batch_id} rolled back")
        
        # Verify batch status changed
        resp = session.get(f"{BASE_URL}/import/history")
        if resp.status_code == 200:
            items = resp.json().get("items", [])
            batch = next((b for b in items if b.get("batch_id") == batch_id), None)
            if batch and batch.get("status") == "dibatalkan":
                log_test("Rollback - status dibatalkan", True, "Batch status updated")
            else:
                log_test("Rollback - status dibatalkan", False, f"Status: {batch.get('status') if batch else 'not found'}")
    else:
        log_test("Rollback - superadmin success", False, f"Status {resp.status_code}")
    
    # Test 10b: Try to rollback old ETL batch (should be 422)
    # Get an old batch from history
    resp = session.get(f"{BASE_URL}/import/history")
    if resp.status_code == 200:
        items = resp.json().get("items", [])
        old_batch = next((b for b in items if b.get("sumber") == "etl"), None)
        
        if old_batch:
            old_batch_id = old_batch.get("batch_id")
            resp = session.delete(f"{BASE_URL}/import/batch/{old_batch_id}")
            
            if resp.status_code == 422:
                log_test("Rollback - ETL batch 422", True, "Correctly rejected ETL batch")
            else:
                log_test("Rollback - ETL batch 422", False, f"Expected 422, got {resp.status_code}")
        else:
            print("  No old ETL batch found to test")
    
    # Test 10c: Rollback as non-superadmin (403)
    logout()
    login(PETUGAS_EMAIL, PETUGAS_PASSWORD)
    
    # Create a new GIS batch to test
    csv_content = """kelurahan,latitude,longitude,keterangan
Kaluku Bodoa,-5.1479,119.4329,Test Point 3"""
    
    files = {"file": ("test_rollback.csv", io.BytesIO(csv_content.encode()), "text/csv")}
    resp = session.post(f"{BASE_URL}/import/upload", files=files)
    
    if resp.status_code == 200:
        session_id = resp.json().get("session_id")
        
        # Quick execute
        payload = {"session_id": session_id, "jenis": "gis_koordinat"}
        resp = session.post(f"{BASE_URL}/import/analyze", json=payload)
        sheets = resp.json().get("sheets", [])
        if len(sheets) > 0:
            mapping = sheets[0].get("mapping", {})
            
            payload = {
                "session_id": session_id,
                "jenis": "gis_koordinat",
                "mapping": mapping,
                "mode": "update"
            }
            resp = session.post(f"{BASE_URL}/import/execute", json=payload)
            
            if resp.status_code == 200:
                test_job_id = resp.json().get("job_id")
                
                # Wait for completion
                time.sleep(5)
                
                resp = session.get(f"{BASE_URL}/import/job/{test_job_id}")
                if resp.status_code == 200:
                    test_batch_id = resp.json().get("batch_id")
                    
                    # Try to delete as petugas
                    resp = session.delete(f"{BASE_URL}/import/batch/{test_batch_id}")
                    
                    if resp.status_code == 403:
                        log_test("Rollback - petugas 403", True, "Correctly rejected non-superadmin")
                    else:
                        log_test("Rollback - petugas 403", False, f"Expected 403, got {resp.status_code}")
    
    # Login back as superadmin
    logout()
    login(SUPERADMIN_EMAIL, SUPERADMIN_PASSWORD)


def test_11_authorization():
    """Test 11: Authorization checks"""
    print("\n=== TEST 11: Authorization ===")
    
    # Test 11a: Upload without login
    logout()
    
    csv_content = """test,data
1,2"""
    files = {"file": ("test.csv", io.BytesIO(csv_content.encode()), "text/csv")}
    resp = session.post(f"{BASE_URL}/import/upload", files=files)
    
    if resp.status_code in [401, 403]:
        log_test("Authorization - upload without login", True, f"Correctly rejected with {resp.status_code}")
    else:
        log_test("Authorization - upload without login", False, f"Expected 401/403, got {resp.status_code}")
    
    # Test 11b: Execute without login
    payload = {
        "session_id": "fake",
        "sheet_index": 0,
        "jenis": "dtsen",
        "mapping": {},
        "mode": "skip"
    }
    resp = session.post(f"{BASE_URL}/import/execute", json=payload)
    
    if resp.status_code in [401, 403]:
        log_test("Authorization - execute without login", True, f"Correctly rejected with {resp.status_code}")
    else:
        log_test("Authorization - execute without login", False, f"Expected 401/403, got {resp.status_code}")
    
    # Login back as superadmin for remaining tests
    login(SUPERADMIN_EMAIL, SUPERADMIN_PASSWORD)


def test_12_regression():
    """Test 12: Regression tests"""
    print("\n=== TEST 12: Regression ===")
    
    # Test health
    resp = session.get(f"{BASE_URL}/health")
    if resp.status_code == 200:
        log_test("Regression - /health", True, "200 OK")
    else:
        log_test("Regression - /health", False, f"Status {resp.status_code}")
    
    # Test sosial/overview
    resp = session.get(f"{BASE_URL}/sosial/overview")
    if resp.status_code == 200:
        data = resp.json()
        households = data.get("total_households", 0)
        individu = data.get("total_individu", 0)
        
        if households == EXPECTED_HOUSEHOLDS:
            log_test("Regression - households count", True, f"Still {households}")
        else:
            log_test("Regression - households count", False, f"Expected {EXPECTED_HOUSEHOLDS}, got {households}")
        
        if individu == EXPECTED_INDIVIDU:
            log_test("Regression - individu count", True, f"Still {individu}")
        else:
            log_test("Regression - individu count", False, f"Expected {EXPECTED_INDIVIDU}, got {individu}")
    else:
        log_test("Regression - /sosial/overview", False, f"Status {resp.status_code}")
    
    # Test wilayah/summary
    resp = session.get(f"{BASE_URL}/wilayah/summary")
    if resp.status_code == 200:
        data = resp.json()
        kelurahan_count = len(data.get("kelurahan", []))
        kecamatan_count = len(data.get("kecamatan", []))
        
        if kelurahan_count == 29 and kecamatan_count == 2:
            log_test("Regression - wilayah (29 kel, 2 kec)", True, f"{kelurahan_count} kel, {kecamatan_count} kec")
        else:
            log_test("Regression - wilayah (29 kel, 2 kec)", False, f"{kelurahan_count} kel, {kecamatan_count} kec")
    else:
        log_test("Regression - /wilayah/summary", False, f"Status {resp.status_code}")
    
    # Test analisis/prioritas
    resp = session.get(f"{BASE_URL}/analisis/prioritas")
    if resp.status_code == 200:
        log_test("Regression - /analisis/prioritas", True, "200 OK")
    else:
        log_test("Regression - /analisis/prioritas", False, f"Status {resp.status_code}")
    
    # Test rad/overview
    resp = session.get(f"{BASE_URL}/rad/overview")
    if resp.status_code == 200:
        data = resp.json()
        rad_count = data.get("jumlah_item", 0)
        if rad_count == 77:
            log_test("Regression - RAD (77 items)", True, f"{rad_count} items")
        else:
            log_test("Regression - RAD (77 items)", False, f"Expected 77, got {rad_count}")
    else:
        log_test("Regression - /rad/overview", False, f"Status {resp.status_code}")
    
    # Test peta-dasar/layers
    resp = session.get(f"{BASE_URL}/peta-dasar/layers")
    if resp.status_code == 200:
        data = resp.json()
        layer_count = data.get("total_layer", 0)
        if layer_count == 13:
            log_test("Regression - peta-dasar (13 layers)", True, f"{layer_count} layers")
        else:
            log_test("Regression - peta-dasar (13 layers)", False, f"Expected 13, got {layer_count}")
    else:
        log_test("Regression - /peta-dasar/layers", False, f"Status {resp.status_code}")


def main():
    """Run all tests"""
    print("=" * 80)
    print("IMPORT WIZARD MODULE BACKEND TESTING")
    print("=" * 80)
    print(f"Backend URL: {BASE_URL}")
    print(f"Expected households: {EXPECTED_HOUSEHOLDS}")
    print(f"Expected individu: {EXPECTED_INDIVIDU}")
    print("=" * 80)
    
    # Login as superadmin
    if not login(SUPERADMIN_EMAIL, SUPERADMIN_PASSWORD):
        print("FATAL: Cannot login as superadmin")
        return
    
    # Run tests
    test_1_datasets()
    test_2_template()
    session_id = test_3_upload()
    analyze_data = test_4_analyze(session_id)
    validate_data = test_5_validate(session_id)
    test_6_errors(session_id)
    dtsen_job_id = test_7_execute_skip(session_id)
    gis_job_id = test_8_execute_gis()
    test_9_history()
    test_10_rollback(gis_job_id)
    test_11_authorization()
    test_12_regression()
    
    # Summary
    print("\n" + "=" * 80)
    print("TEST SUMMARY")
    print("=" * 80)
    
    passed = sum(1 for t in test_results if t["passed"])
    total = len(test_results)
    
    print(f"Total tests: {total}")
    print(f"Passed: {passed}")
    print(f"Failed: {total - passed}")
    print(f"Pass rate: {passed / total * 100:.1f}%")
    
    print("\n" + "=" * 80)
    print("FAILED TESTS:")
    print("=" * 80)
    
    failed_tests = [t for t in test_results if not t["passed"]]
    if failed_tests:
        for t in failed_tests:
            print(f"❌ {t['name']}")
            if t["details"]:
                print(f"   {t['details']}")
    else:
        print("None - all tests passed!")
    
    print("\n" + "=" * 80)
    print("CRITICAL VERIFICATION:")
    print("=" * 80)
    
    # Final verification
    resp = session.get(f"{BASE_URL}/sosial/overview")
    if resp.status_code == 200:
        data = resp.json()
        final_households = data.get("total_households", 0)
        final_individu = data.get("total_individu", 0)
        
        print(f"Final households: {final_households} (expected: {EXPECTED_HOUSEHOLDS})")
        print(f"Final individu: {final_individu} (expected: {EXPECTED_INDIVIDU})")
        
        if final_households == EXPECTED_HOUSEHOLDS and final_individu == EXPECTED_INDIVIDU:
            print("✅ DATA INTEGRITY VERIFIED - No changes to DTSEN data")
        else:
            print("❌ DATA INTEGRITY VIOLATION - DTSEN data was modified!")
    
    print("=" * 80)


if __name__ == "__main__":
    main()
