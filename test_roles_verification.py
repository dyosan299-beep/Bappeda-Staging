#!/usr/bin/env python3
import os
"""
Role System + Data Verification Workflow Test Suite
Tests the new role system (superadmin, operator, petugas, verifikator) and data verification workflow
"""

import requests
import json
import time
import sys
from typing import Dict, Optional

# Configuration
BASE_URL = "https://backend-recovery-16.preview.emergentagent.com/api"

# Test credentials from test_credentials.md
SUPERADMIN_EMAIL = "admin@bappeda.makassarkota.go.id"
SUPERADMIN_PASSWORD = os.environ.get("TEST_ADMIN_PASSWORD", "")

OPERATOR_EMAIL = "operator.rappocini@makassarkota.go.id"
OPERATOR_PASSWORD = os.environ.get("TEST_OPERATOR_PASSWORD", "")

PETUGAS_EMAIL = "petugas.tallo@makassarkota.go.id"
PETUGAS_PASSWORD = os.environ.get("TEST_PETUGAS_PASSWORD", "")

VERIFIKATOR_EMAIL = "verifikator@bappeda.makassarkota.go.id"
VERIFIKATOR_PASSWORD = os.environ.get("TEST_VERIFIKATOR_PASSWORD", "")

# Test results tracking
test_results = []


def log_test(name: str, passed: bool, details: str = ""):
    """Log test result"""
    status = "✅ PASS" if passed else "❌ FAIL"
    test_results.append({"name": name, "passed": passed, "details": details})
    print(f"{status}: {name}")
    if details:
        print(f"  Details: {details}")


def login(email: str, password: str) -> Optional[requests.Session]:
    """Login and return session with cookies"""
    session = requests.Session()
    try:
        resp = session.post(
            f"{BASE_URL}/auth/login",
            json={"email": email, "password": password},
            timeout=10
        )
        if resp.status_code == 200:
            return session
        else:
            print(f"Login failed for {email}: {resp.status_code} - {resp.text}")
            return None
    except Exception as e:
        print(f"Login exception for {email}: {e}")
        return None


def test_role_migration():
    """Test 1: Role migration - superadmin login and verify role"""
    print("\n=== Test 1: Role Migration ===")
    
    # Login as superadmin
    superadmin_session = login(SUPERADMIN_EMAIL, SUPERADMIN_PASSWORD)
    if not superadmin_session:
        log_test("Role migration - superadmin login", False, "Could not login as superadmin")
        return None
    
    log_test("Role migration - superadmin login", True, "Superadmin logged in successfully")
    
    # GET /api/auth/me to verify role
    try:
        resp = superadmin_session.get(f"{BASE_URL}/auth/me", timeout=10)
        
        if resp.status_code != 200:
            log_test("Role migration - GET /auth/me", False, f"Status {resp.status_code}")
            return superadmin_session
        
        data = resp.json()
        role = data.get("role")
        
        if role == "superadmin":
            log_test("Role migration - role is superadmin", True, f"Role: {role}")
        else:
            log_test("Role migration - role is superadmin", False, f"Expected 'superadmin', got '{role}'")
    
    except Exception as e:
        log_test("Role migration - GET /auth/me", False, f"Exception: {e}")
    
    return superadmin_session


def test_user_management(superadmin_session):
    """Test 2: User management (superadmin only)"""
    print("\n=== Test 2: User Management ===")
    
    if not superadmin_session:
        log_test("User management - skipped", False, "No superadmin session")
        return None
    
    # Test 2a: Create user with role "verifikator" (no wilayah needed)
    verifikator_email = f"verifikator.test.{int(time.time())}@bappeda.go.id"
    verifikator_password = "TestVerif2025"
    created_user_id = None
    
    try:
        resp = superadmin_session.post(
            f"{BASE_URL}/admin/users",
            json={
                "email": verifikator_email,
                "password": verifikator_password,
                "name": "Test Verifikator",
                "wilayah": "",  # No wilayah for verifikator
                "role": "verifikator"
            },
            timeout=10
        )
        
        if resp.status_code not in [200, 201]:
            log_test("User management - create verifikator", False, f"Status {resp.status_code}: {resp.text}")
        else:
            data = resp.json()
            created_user_id = data.get("id")
            
            if data.get("role") != "verifikator":
                log_test("User management - create verifikator", False, f"Wrong role: {data.get('role')}")
            elif data.get("status") != "active":
                log_test("User management - create verifikator", False, f"Wrong status: {data.get('status')}")
            else:
                log_test("User management - create verifikator", True, f"Created verifikator user (ID: {created_user_id})")
    
    except Exception as e:
        log_test("User management - create verifikator", False, f"Exception: {e}")
    
    # Test 2b: PATCH user to change name and wilayah
    if created_user_id:
        try:
            resp = superadmin_session.patch(
                f"{BASE_URL}/admin/users/{created_user_id}",
                json={
                    "name": "Test Verifikator Updated",
                    "wilayah": "Kota Makassar"
                },
                timeout=10
            )
            
            if resp.status_code != 200:
                log_test("User management - PATCH user", False, f"Status {resp.status_code}: {resp.text}")
            else:
                data = resp.json()
                if data.get("name") != "Test Verifikator Updated":
                    log_test("User management - PATCH user", False, f"Name not updated: {data.get('name')}")
                elif data.get("wilayah") != "Kota Makassar":
                    log_test("User management - PATCH user", False, f"Wilayah not updated: {data.get('wilayah')}")
                else:
                    log_test("User management - PATCH user", True, "Name and wilayah updated successfully")
        
        except Exception as e:
            log_test("User management - PATCH user", False, f"Exception: {e}")
    
    # Test 2c: Reset password and verify new password works
    if created_user_id:
        new_password = "NewPassword2025"
        
        try:
            # Reset password
            resp = superadmin_session.post(
                f"{BASE_URL}/admin/users/{created_user_id}/reset-password",
                json={"password": new_password},
                timeout=10
            )
            
            if resp.status_code != 200:
                log_test("User management - reset password", False, f"Status {resp.status_code}: {resp.text}")
            else:
                log_test("User management - reset password", True, "Password reset successful")
                
                # Try to login with new password
                new_session = login(verifikator_email, new_password)
                if new_session:
                    log_test("User management - login with new password", True, "Login successful with new password")
                else:
                    log_test("User management - login with new password", False, "Could not login with new password")
        
        except Exception as e:
            log_test("User management - reset password", False, f"Exception: {e}")
    
    # Test 2d: Negative test - operator trying to access admin endpoints should get 403
    operator_session = login(OPERATOR_EMAIL, OPERATOR_PASSWORD)
    if operator_session:
        # Try POST /api/admin/users
        try:
            resp = operator_session.post(
                f"{BASE_URL}/admin/users",
                json={
                    "email": "test@test.com",
                    "password": "test123",
                    "name": "Test",
                    "role": "petugas"
                },
                timeout=10
            )
            
            if resp.status_code == 403:
                log_test("User management - operator POST /admin/users (should fail)", True, "Correctly rejected with 403")
            else:
                log_test("User management - operator POST /admin/users (should fail)", False, f"Expected 403, got {resp.status_code}")
        
        except Exception as e:
            log_test("User management - operator POST /admin/users (should fail)", False, f"Exception: {e}")
        
        # Try PATCH /api/admin/users/{id}
        if created_user_id:
            try:
                resp = operator_session.patch(
                    f"{BASE_URL}/admin/users/{created_user_id}",
                    json={"name": "Hacked"},
                    timeout=10
                )
                
                if resp.status_code == 403:
                    log_test("User management - operator PATCH /admin/users (should fail)", True, "Correctly rejected with 403")
                else:
                    log_test("User management - operator PATCH /admin/users (should fail)", False, f"Expected 403, got {resp.status_code}")
            
            except Exception as e:
                log_test("User management - operator PATCH /admin/users (should fail)", False, f"Exception: {e}")
        
        # Try POST /api/admin/users/{id}/reset-password
        if created_user_id:
            try:
                resp = operator_session.post(
                    f"{BASE_URL}/admin/users/{created_user_id}/reset-password",
                    json={"password": "hacked123"},
                    timeout=10
                )
                
                if resp.status_code == 403:
                    log_test("User management - operator reset-password (should fail)", True, "Correctly rejected with 403")
                else:
                    log_test("User management - operator reset-password (should fail)", False, f"Expected 403, got {resp.status_code}")
            
            except Exception as e:
                log_test("User management - operator reset-password (should fail)", False, f"Exception: {e}")
    
    # Test 2e: Superadmin trying to downgrade own role should get 400
    try:
        # Get superadmin user ID
        resp = superadmin_session.get(f"{BASE_URL}/auth/me", timeout=10)
        if resp.status_code == 200:
            superadmin_id = resp.json().get("id")
            
            # Try to change own role to non-superadmin
            resp = superadmin_session.patch(
                f"{BASE_URL}/admin/users/{superadmin_id}",
                json={"role": "petugas"},
                timeout=10
            )
            
            if resp.status_code == 400:
                log_test("User management - superadmin downgrade own role (should fail)", True, "Correctly rejected with 400")
            else:
                log_test("User management - superadmin downgrade own role (should fail)", False, f"Expected 400, got {resp.status_code}")
    
    except Exception as e:
        log_test("User management - superadmin downgrade own role (should fail)", False, f"Exception: {e}")
    
    return created_user_id


def test_data_verification_workflow():
    """Test 3: Data verification workflow"""
    print("\n=== Test 3: Data Verification Workflow ===")
    
    # Get Rappocini region id
    rappocini_id = None
    rappocini_original_value = None
    
    try:
        resp = requests.get(f"{BASE_URL}/regions", timeout=10)
        if resp.status_code == 200:
            regions = resp.json()
            for region in regions:
                if region.get("nama", "").lower() == "rappocini":
                    rappocini_id = region.get("id")
                    rappocini_original_value = region.get("stunting_anak")
                    log_test("Data verification - get Rappocini region", True, f"Found Rappocini (ID: {rappocini_id}, stunting_anak: {rappocini_original_value})")
                    break
            
            if not rappocini_id:
                log_test("Data verification - get Rappocini region", False, "Rappocini region not found")
                return None, None
        else:
            log_test("Data verification - get Rappocini region", False, f"Status {resp.status_code}")
            return None, None
    
    except Exception as e:
        log_test("Data verification - get Rappocini region", False, f"Exception: {e}")
        return None, None
    
    # Test 3a: Operator PUT /api/regions/{rappocini_id} -> status "pending", data NOT changed yet
    operator_session = login(OPERATOR_EMAIL, OPERATOR_PASSWORD)
    operator_change_id = None
    
    if operator_session and rappocini_id:
        try:
            resp = operator_session.put(
                f"{BASE_URL}/regions/{rappocini_id}",
                json={"stunting_anak": 123},
                timeout=10
            )
            
            if resp.status_code != 200:
                log_test("Data verification - operator PUT region", False, f"Status {resp.status_code}: {resp.text}")
            else:
                data = resp.json()
                status = data.get("status")
                operator_change_id = data.get("change_id")
                
                if status != "pending":
                    log_test("Data verification - operator PUT region", False, f"Expected status 'pending', got '{status}'")
                else:
                    log_test("Data verification - operator PUT region", True, f"Status: pending, change_id: {operator_change_id}")
                    
                    # Verify data NOT changed yet
                    check_resp = requests.get(f"{BASE_URL}/regions/{rappocini_id}", timeout=10)
                    if check_resp.status_code == 200:
                        current_value = check_resp.json().get("stunting_anak")
                        if current_value == 123:
                            log_test("Data verification - operator PUT region (data unchanged)", False, f"Data changed immediately (value: {current_value})")
                        else:
                            log_test("Data verification - operator PUT region (data unchanged)", True, f"Data NOT changed yet (still: {current_value})")
        
        except Exception as e:
            log_test("Data verification - operator PUT region", False, f"Exception: {e}")
    
    # Test 3b: Petugas PUT /api/kelurahan/{tallo_kel_id} -> status "pending"
    petugas_session = login(PETUGAS_EMAIL, PETUGAS_PASSWORD)
    petugas_change_id = None
    tallo_kel_id = None
    
    if petugas_session:
        # Get Tallo region id first
        try:
            resp = requests.get(f"{BASE_URL}/regions", timeout=10)
            if resp.status_code == 200:
                regions = resp.json()
                tallo_region_id = None
                for region in regions:
                    if region.get("nama", "").lower() == "tallo":
                        tallo_region_id = region.get("id")
                        break
                
                if tallo_region_id:
                    # Get kelurahan in Tallo
                    resp = requests.get(f"{BASE_URL}/regions/{tallo_region_id}/kelurahan", timeout=10)
                    if resp.status_code == 200:
                        kelurahans = resp.json()
                        if kelurahans:
                            tallo_kel_id = kelurahans[0].get("id")
                            log_test("Data verification - get Tallo kelurahan", True, f"Found Tallo kelurahan (ID: {tallo_kel_id})")
        
        except Exception as e:
            log_test("Data verification - get Tallo kelurahan", False, f"Exception: {e}")
        
        # PUT kelurahan
        if tallo_kel_id:
            try:
                resp = petugas_session.put(
                    f"{BASE_URL}/kelurahan/{tallo_kel_id}",
                    json={"stunting_anak": 7},
                    timeout=10
                )
                
                if resp.status_code != 200:
                    log_test("Data verification - petugas PUT kelurahan", False, f"Status {resp.status_code}: {resp.text}")
                else:
                    data = resp.json()
                    status = data.get("status")
                    petugas_change_id = data.get("change_id")
                    
                    if status != "pending":
                        log_test("Data verification - petugas PUT kelurahan", False, f"Expected status 'pending', got '{status}'")
                    else:
                        log_test("Data verification - petugas PUT kelurahan", True, f"Status: pending, change_id: {petugas_change_id}")
            
            except Exception as e:
                log_test("Data verification - petugas PUT kelurahan", False, f"Exception: {e}")
    
    # Test 3c: Verifikator PUT -> 403 (verifikator cannot input)
    verifikator_session = login(VERIFIKATOR_EMAIL, VERIFIKATOR_PASSWORD)
    
    if verifikator_session and rappocini_id:
        try:
            resp = verifikator_session.put(
                f"{BASE_URL}/regions/{rappocini_id}",
                json={"stunting_anak": 5},
                timeout=10
            )
            
            if resp.status_code == 403:
                log_test("Data verification - verifikator PUT region (should fail)", True, "Correctly rejected with 403")
            else:
                log_test("Data verification - verifikator PUT region (should fail)", False, f"Expected 403, got {resp.status_code}")
        
        except Exception as e:
            log_test("Data verification - verifikator PUT region (should fail)", False, f"Exception: {e}")
    
    # Test 3d: Superadmin PUT -> status "applied", data changes immediately
    superadmin_session = login(SUPERADMIN_EMAIL, SUPERADMIN_PASSWORD)
    
    if superadmin_session and rappocini_id:
        try:
            # Get a different region for superadmin test (not Rappocini, to avoid conflict)
            resp = requests.get(f"{BASE_URL}/regions", timeout=10)
            if resp.status_code == 200:
                regions = resp.json()
                test_region_id = None
                test_region_original = None
                
                for region in regions:
                    if region.get("nama", "").lower() not in ["rappocini", "tallo"]:
                        test_region_id = region.get("id")
                        test_region_original = region.get("anak_jalanan", 0)
                        break
                
                if test_region_id:
                    resp = superadmin_session.put(
                        f"{BASE_URL}/regions/{test_region_id}",
                        json={"anak_jalanan": 3},
                        timeout=10
                    )
                    
                    if resp.status_code != 200:
                        log_test("Data verification - superadmin PUT region", False, f"Status {resp.status_code}: {resp.text}")
                    else:
                        data = resp.json()
                        status = data.get("status")
                        
                        if status != "applied":
                            log_test("Data verification - superadmin PUT region", False, f"Expected status 'applied', got '{status}'")
                        else:
                            log_test("Data verification - superadmin PUT region", True, f"Status: applied")
                            
                            # Verify data changed immediately
                            check_resp = requests.get(f"{BASE_URL}/regions/{test_region_id}", timeout=10)
                            if check_resp.status_code == 200:
                                current_value = check_resp.json().get("anak_jalanan")
                                if current_value == 3:
                                    log_test("Data verification - superadmin PUT region (data changed)", True, f"Data changed immediately (value: {current_value})")
                                else:
                                    log_test("Data verification - superadmin PUT region (data changed)", False, f"Data NOT changed (value: {current_value})")
        
        except Exception as e:
            log_test("Data verification - superadmin PUT region", False, f"Exception: {e}")
    
    return operator_change_id, petugas_change_id


def test_verifikator_review(operator_change_id, petugas_change_id):
    """Test 4: Verifikator review"""
    print("\n=== Test 4: Verifikator Review ===")
    
    verifikator_session = login(VERIFIKATOR_EMAIL, VERIFIKATOR_PASSWORD)
    
    if not verifikator_session:
        log_test("Verifikator review - login", False, "Could not login as verifikator")
        return
    
    log_test("Verifikator review - login", True, "Verifikator logged in successfully")
    
    # Test 4a: GET /api/verifikasi/count -> {pending: N>=2}
    try:
        resp = verifikator_session.get(f"{BASE_URL}/verifikasi/count", timeout=10)
        
        if resp.status_code != 200:
            log_test("Verifikator review - GET /verifikasi/count", False, f"Status {resp.status_code}: {resp.text}")
        else:
            data = resp.json()
            pending_count = data.get("pending")
            
            if pending_count is None:
                log_test("Verifikator review - GET /verifikasi/count", False, "Missing 'pending' field")
            elif pending_count < 2:
                log_test("Verifikator review - GET /verifikasi/count", False, f"Expected pending >= 2, got {pending_count}")
            else:
                log_test("Verifikator review - GET /verifikasi/count", True, f"Pending count: {pending_count}")
    
    except Exception as e:
        log_test("Verifikator review - GET /verifikasi/count", False, f"Exception: {e}")
    
    # Test 4b: GET /api/verifikasi?status=pending -> array with required fields
    try:
        resp = verifikator_session.get(f"{BASE_URL}/verifikasi?status=pending", timeout=10)
        
        if resp.status_code != 200:
            log_test("Verifikator review - GET /verifikasi?status=pending", False, f"Status {resp.status_code}: {resp.text}")
        else:
            data = resp.json()
            
            if not isinstance(data, list):
                log_test("Verifikator review - GET /verifikasi?status=pending", False, "Response is not a list")
            elif len(data) == 0:
                log_test("Verifikator review - GET /verifikasi?status=pending", False, "Empty list (expected at least 2 items)")
            else:
                # Check required fields
                required_fields = ["id", "target_type", "target_nama", "changes", "before", "submitted_by", "status"]
                item = data[0]
                missing = [f for f in required_fields if f not in item]
                
                if missing:
                    log_test("Verifikator review - GET /verifikasi?status=pending", False, f"Missing fields: {missing}")
                elif item.get("status") != "pending":
                    log_test("Verifikator review - GET /verifikasi?status=pending", False, f"Item status is not 'pending': {item.get('status')}")
                else:
                    log_test("Verifikator review - GET /verifikasi?status=pending", True, f"Found {len(data)} pending items with all required fields")
    
    except Exception as e:
        log_test("Verifikator review - GET /verifikasi?status=pending", False, f"Exception: {e}")
    
    # Test 4c: POST /api/verifikasi/{operator_change_id}/approve -> 200, data applied
    if operator_change_id:
        try:
            resp = verifikator_session.post(
                f"{BASE_URL}/verifikasi/{operator_change_id}/approve",
                timeout=10
            )
            
            if resp.status_code != 200:
                log_test("Verifikator review - approve operator change", False, f"Status {resp.status_code}: {resp.text}")
            else:
                log_test("Verifikator review - approve operator change", True, "Change approved")
                
                # Verify Rappocini stunting_anak == 123 (applied)
                time.sleep(1)  # Wait for DB update
                resp = requests.get(f"{BASE_URL}/regions", timeout=10)
                if resp.status_code == 200:
                    regions = resp.json()
                    for region in regions:
                        if region.get("nama", "").lower() == "rappocini":
                            current_value = region.get("stunting_anak")
                            if current_value == 123:
                                log_test("Verifikator review - approve operator change (data applied)", True, f"Rappocini stunting_anak: {current_value}")
                            else:
                                log_test("Verifikator review - approve operator change (data applied)", False, f"Expected 123, got {current_value}")
                            break
        
        except Exception as e:
            log_test("Verifikator review - approve operator change", False, f"Exception: {e}")
    
    # Test 4d: POST /api/verifikasi/{petugas_change_id}/reject -> 200, data NOT changed
    if petugas_change_id:
        # Get current kelurahan value before reject
        try:
            resp = requests.get(f"{BASE_URL}/kelurahan?kecamatan=Tallo", timeout=10)
            if resp.status_code == 200:
                kelurahans = resp.json()
                if kelurahans:
                    kel_id = kelurahans[0].get("id")
                    original_value = kelurahans[0].get("stunting_anak")
                    
                    # Reject the change
                    resp = verifikator_session.post(
                        f"{BASE_URL}/verifikasi/{petugas_change_id}/reject",
                        json={"note": "tidak sesuai"},
                        timeout=10
                    )
                    
                    if resp.status_code != 200:
                        log_test("Verifikator review - reject petugas change", False, f"Status {resp.status_code}: {resp.text}")
                    else:
                        log_test("Verifikator review - reject petugas change", True, "Change rejected")
                        
                        # Verify kelurahan value NOT changed
                        time.sleep(1)  # Wait for DB update
                        resp = requests.get(f"{BASE_URL}/kelurahan/{kel_id}", timeout=10)
                        if resp.status_code == 200:
                            current_value = resp.json().get("stunting_anak")
                            if current_value == 7:
                                log_test("Verifikator review - reject petugas change (data unchanged)", False, f"Data changed to 7 (should remain {original_value})")
                            else:
                                log_test("Verifikator review - reject petugas change (data unchanged)", True, f"Data unchanged (still: {current_value})")
        
        except Exception as e:
            log_test("Verifikator review - reject petugas change", False, f"Exception: {e}")
    
    # Test 4e: Negative test - operator trying to access /api/verifikasi -> 403
    operator_session = login(OPERATOR_EMAIL, OPERATOR_PASSWORD)
    
    if operator_session:
        # Try GET /api/verifikasi
        try:
            resp = operator_session.get(f"{BASE_URL}/verifikasi", timeout=10)
            
            if resp.status_code == 403:
                log_test("Verifikator review - operator GET /verifikasi (should fail)", True, "Correctly rejected with 403")
            else:
                log_test("Verifikator review - operator GET /verifikasi (should fail)", False, f"Expected 403, got {resp.status_code}")
        
        except Exception as e:
            log_test("Verifikator review - operator GET /verifikasi (should fail)", False, f"Exception: {e}")
        
        # Try GET /api/verifikasi/count
        try:
            resp = operator_session.get(f"{BASE_URL}/verifikasi/count", timeout=10)
            
            if resp.status_code == 403:
                log_test("Verifikator review - operator GET /verifikasi/count (should fail)", True, "Correctly rejected with 403")
            else:
                log_test("Verifikator review - operator GET /verifikasi/count (should fail)", False, f"Expected 403, got {resp.status_code}")
        
        except Exception as e:
            log_test("Verifikator review - operator GET /verifikasi/count (should fail)", False, f"Exception: {e}")


def test_regression():
    """Test 5: Regression tests"""
    print("\n=== Test 5: Regression Tests ===")
    
    # Test 5a: POST /api/ai/analyze SSE
    try:
        resp = requests.post(
            f"{BASE_URL}/ai/analyze",
            json={"kategori": "stunting"},
            stream=True,
            timeout=60
        )
        
        if resp.status_code != 200:
            log_test("Regression - AI analyze SSE", False, f"Status {resp.status_code}")
        else:
            deltas = []
            done_received = False
            
            for line in resp.iter_lines(decode_unicode=True):
                if line.startswith("data: "):
                    data_str = line[6:]
                    try:
                        data = json.loads(data_str)
                        if "delta" in data:
                            deltas.append(data["delta"])
                        elif "done" in data and data["done"]:
                            done_received = True
                    except json.JSONDecodeError:
                        pass
            
            if done_received and len(deltas) > 0:
                log_test("Regression - AI analyze SSE", True, f"Received {len(deltas)} deltas with done signal")
            else:
                log_test("Regression - AI analyze SSE", False, f"Done: {done_received}, Deltas: {len(deltas)}")
    
    except Exception as e:
        log_test("Regression - AI analyze SSE", False, f"Exception: {e}")
    
    # Test 5b: GET /api/export/excel
    try:
        resp = requests.get(f"{BASE_URL}/export/excel", timeout=30)
        
        if resp.status_code != 200:
            log_test("Regression - Excel export", False, f"Status {resp.status_code}")
        else:
            content_type = resp.headers.get("content-type", "")
            expected_ct = "application/vnd.openxmlformats-officedocument.spreadsheetml.sheet"
            
            if content_type != expected_ct:
                log_test("Regression - Excel export", False, f"Wrong content-type: {content_type}")
            elif len(resp.content) == 0:
                log_test("Regression - Excel export", False, "Empty body")
            else:
                log_test("Regression - Excel export", True, f"Valid xlsx ({len(resp.content)} bytes)")
    
    except Exception as e:
        log_test("Regression - Excel export", False, f"Exception: {e}")


def print_summary():
    """Print test summary"""
    print("\n" + "="*60)
    print("TEST SUMMARY")
    print("="*60)
    
    passed = sum(1 for t in test_results if t["passed"])
    failed = sum(1 for t in test_results if not t["passed"])
    total = len(test_results)
    
    print(f"\nTotal: {total} tests")
    print(f"Passed: {passed} ✅")
    print(f"Failed: {failed} ❌")
    
    if failed > 0:
        print("\nFailed tests:")
        for t in test_results:
            if not t["passed"]:
                print(f"  ❌ {t['name']}")
                if t["details"]:
                    print(f"     {t['details']}")
    
    print("\n" + "="*60)
    
    return failed == 0


if __name__ == "__main__":
    print("SIDATA Bappeda - Role System + Data Verification Workflow Test Suite")
    print(f"Testing: {BASE_URL}")
    print("="*60)
    
    # Run all tests
    superadmin_session = test_role_migration()
    created_user_id = test_user_management(superadmin_session)
    operator_change_id, petugas_change_id = test_data_verification_workflow()
    test_verifikator_review(operator_change_id, petugas_change_id)
    test_regression()
    
    # Print summary
    success = print_summary()
    
    sys.exit(0 if success else 1)
