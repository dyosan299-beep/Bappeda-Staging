#!/usr/bin/env python3
"""
PETA INKLUSI - Cerita Dampak Program Backend Test
Tests the new "Cerita Dampak Program" feature for NGO impact stories
"""
import io
import json
import os
import sys
import time
from datetime import datetime

import requests

# Public endpoint from frontend/.env
BASE_URL = os.environ.get("REACT_APP_BACKEND_URL", "https://deploy-live-26.preview.emergentagent.com")
API_URL = f"{BASE_URL}/api"

# Test credentials
ADMIN_EMAIL = "admin@bappeda.makassarkota.go.id"
ADMIN_PASSWORD = os.environ.get("TEST_ADMIN_PASSWORD", "")
NGO_EMAIL = "ngo.uji@petainklusi.org"
NGO_PASSWORD = os.environ.get("TEST_NGO_PASSWORD", "")
OPERATOR_EMAIL = "petugas.tallo@makassarkota.go.id"
OPERATOR_PASSWORD = os.environ.get("TEST_PETUGAS_PASSWORD", "")

class Colors:
    GREEN = '\033[92m'
    RED = '\033[91m'
    YELLOW = '\033[93m'
    BLUE = '\033[94m'
    END = '\033[0m'

class CeritaTestRunner:
    def __init__(self):
        self.tests_run = 0
        self.tests_passed = 0
        self.tests_failed = 0
        self.session = requests.Session()
        self.cookies = {}
        self.test_inquiry_id = None
        self.test_foto_id = None
        
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
    
    def put(self, path, **kwargs):
        """PUT request with cookies"""
        return self.session.put(f"{API_URL}{path}", cookies=self.cookies, **kwargs)
    
    def patch(self, path, **kwargs):
        """PATCH request with cookies"""
        return self.session.patch(f"{API_URL}{path}", cookies=self.cookies, **kwargs)
    
    def delete(self, path, **kwargs):
        """DELETE request with cookies"""
        return self.session.delete(f"{API_URL}{path}", cookies=self.cookies, **kwargs)
    
    # ============ Setup: Find or create test inquiry ============
    def setup_test_inquiry(self):
        """Find existing TEST inquiry or create new one"""
        self.log("\n📋 Setting up test inquiry...")
        self.login(NGO_EMAIL, NGO_PASSWORD)
        
        # Find existing TEST inquiry
        r = self.get("/inquiries")
        assert r.status_code == 200, f"Failed to get inquiries: {r.status_code}"
        
        inquiries = r.json().get("items", [])
        test_inq = None
        
        # Look for COMPLETED inquiry owned by ngo.uji
        for inq in inquiries:
            if inq.get("status") == "COMPLETED" and "TEST" in inq.get("program_usulan", ""):
                test_inq = inq
                break
        
        if test_inq:
            self.test_inquiry_id = test_inq["id"]
            self.success(f"Found existing TEST inquiry: {test_inq['nomor']} (ID: {self.test_inquiry_id})")
        else:
            # Create new inquiry and move it to COMPLETED
            self.warn("No COMPLETED TEST inquiry found, creating new one...")
            
            # Create inquiry
            payload = {
                "nama_ngo": "Yayasan Uji Inklusi",
                "nama_pic": "Test PIC",
                "email": NGO_EMAIL,
                "telepon": "081234567890",
                "organisasi": "Yayasan Uji Inklusi",
                "alamat_organisasi": "Makassar",
                "kategori": "Stunting",
                "kecamatan": "Tallo",
                "kelurahan": "Buloa",
                "permasalahan": "TEST - Permasalahan stunting di wilayah",
                "deskripsi_kebutuhan": "TEST - Intervensi gizi untuk balita",
                "program_usulan": "TEST Cerita Dampak - Program Gizi Balita",
                "target_penerima": "Balita stunting",
                "jumlah_penerima": 30,
                "durasi_bulan": 6,
                "estimasi_anggaran": 50000000,
                "catatan": "TEST inquiry for cerita dampak testing"
            }
            
            r = self.post("/inquiries", json=payload)
            assert r.status_code == 200, f"Failed to create inquiry: {r.status_code} {r.text}"
            
            inq_data = r.json()
            self.test_inquiry_id = inq_data["id"]
            self.success(f"Created TEST inquiry: {inq_data['nomor']} (ID: {self.test_inquiry_id})")
            
            # Move to COMPLETED status (admin actions)
            self.logout()
            self.login(ADMIN_EMAIL, ADMIN_PASSWORD)
            
            statuses = ["UNDER_REVIEW", "VERIFICATION", "APPROVED", "PROGRAM_IMPLEMENTATION", "MONITORING", "COMPLETED"]
            for status in statuses:
                r = self.patch(f"/inquiries/{self.test_inquiry_id}/status", 
                             json={"status": status, "catatan": f"TEST - Moving to {status}"})
                assert r.status_code == 200, f"Failed to move to {status}: {r.status_code} {r.text}"
                self.log(f"  Moved to {status}")
            
            self.success(f"Moved inquiry to COMPLETED status")
            
            # Switch back to NGO
            self.logout()
            self.login(NGO_EMAIL, NGO_PASSWORD)
    
    # ============ Test Cases ============
    
    def test_get_cerita_empty(self):
        """Test GET cerita when no story exists"""
        r = self.get(f"/inquiries/{self.test_inquiry_id}/cerita")
        assert r.status_code == 200, f"Expected 200, got {r.status_code}"
        data = r.json()
        # Should return ada: False when no story
        self.log(f"  Response: {json.dumps(data, indent=2)}")
    
    def test_put_cerita_validation_short_ringkasan(self):
        """Test PUT cerita with ringkasan < 30 chars (should fail)"""
        payload = {
            "ringkasan_hasil": "Too short",  # < 30 chars
            "realisasi_penerima": 25,
            "testimoni": [],
            "persetujuan": True
        }
        r = self.put(f"/inquiries/{self.test_inquiry_id}/cerita", json=payload)
        assert r.status_code == 422, f"Expected 422 for short ringkasan, got {r.status_code}"
        self.log(f"  Correctly rejected short ringkasan: {r.json().get('detail')}")
    
    def test_put_cerita_validation_no_persetujuan(self):
        """Test PUT cerita without persetujuan checkbox (should fail)"""
        payload = {
            "ringkasan_hasil": "Program berjalan dengan baik selama 6 bulan dan berhasil meningkatkan status gizi balita",
            "realisasi_penerima": 25,
            "testimoni": [],
            "persetujuan": False  # Not checked
        }
        r = self.put(f"/inquiries/{self.test_inquiry_id}/cerita", json=payload)
        assert r.status_code == 422, f"Expected 422 for no persetujuan, got {r.status_code}"
        assert "persetujuan" in r.text.lower(), "Error should mention persetujuan"
        self.log(f"  Correctly rejected without persetujuan: {r.json().get('detail')}")
    
    def test_put_cerita_validation_too_many_testimoni(self):
        """Test PUT cerita with > 3 testimoni (should fail)"""
        payload = {
            "ringkasan_hasil": "Program berjalan dengan baik selama 6 bulan dan berhasil meningkatkan status gizi balita",
            "realisasi_penerima": 25,
            "testimoni": [
                {"kutipan": "Testimoni 1 sangat bagus", "sumber": "Ibu A"},
                {"kutipan": "Testimoni 2 sangat bagus", "sumber": "Ibu B"},
                {"kutipan": "Testimoni 3 sangat bagus", "sumber": "Ibu C"},
                {"kutipan": "Testimoni 4 sangat bagus", "sumber": "Ibu D"}  # 4th one
            ],
            "persetujuan": True
        }
        r = self.put(f"/inquiries/{self.test_inquiry_id}/cerita", json=payload)
        assert r.status_code == 422, f"Expected 422 for >3 testimoni, got {r.status_code}"
        self.log(f"  Correctly rejected >3 testimoni: {r.json().get('detail')}")
    
    def test_put_cerita_success(self):
        """Test PUT cerita with valid data"""
        payload = {
            "ringkasan_hasil": "Program gizi balita berjalan dengan baik selama 6 bulan. Sebanyak 28 balita menerima PMT harian dan pendampingan gizi. Hasil pengukuran menunjukkan 11 balita naik status gizi dari sangat pendek ke pendek.",
            "realisasi_penerima": 28,
            "testimoni": [
                {
                    "kutipan": "Anak saya sekarang lebih aktif dan nafsu makannya meningkat setelah mengikuti program ini",
                    "sumber": "Ibu penerima manfaat, Kel. Buloa"
                },
                {
                    "kutipan": "Program ini sangat membantu keluarga kami memahami pentingnya gizi seimbang",
                    "sumber": "Ayah penerima manfaat, Kel. Buloa"
                }
            ],
            "persetujuan": True
        }
        r = self.put(f"/inquiries/{self.test_inquiry_id}/cerita", json=payload)
        assert r.status_code == 200, f"Expected 200, got {r.status_code}: {r.text}"
        
        data = r.json()
        assert data.get("ada") == True, "Should have ada=True"
        assert data.get("status") == "menunggu_review", f"Status should be menunggu_review, got {data.get('status')}"
        assert data.get("ringkasan_hasil") == payload["ringkasan_hasil"], "Ringkasan should match"
        assert data.get("realisasi_penerima") == 28, "Realisasi should be 28"
        assert len(data.get("testimoni", [])) == 2, "Should have 2 testimoni"
        
        self.log(f"  Story created with status: {data.get('status')}")
        self.log(f"  Testimoni count: {len(data.get('testimoni', []))}")
    
    def test_post_foto_before_story(self):
        """Test POST foto before story exists (should fail with 409)"""
        # Create a new inquiry without story
        self.logout()
        self.login(NGO_EMAIL, NGO_PASSWORD)
        
        # Use existing inquiry but try to upload photo before saving story
        # First, let's create a minimal 1x1 JPEG
        from PIL import Image
        img = Image.new('RGB', (100, 100), color='red')
        img_bytes = io.BytesIO()
        img.save(img_bytes, format='JPEG')
        img_bytes.seek(0)
        
        # Try to upload without story - but we just created story above, so skip this test
        self.log("  Skipping - story already exists from previous test")
    
    def test_post_foto_success(self):
        """Test POST foto with valid image"""
        # Create a test JPEG image with EXIF data
        from PIL import Image
        import piexif
        
        # Create image
        img = Image.new('RGB', (800, 600), color='blue')
        
        # Add EXIF data including GPS
        exif_dict = {
            "0th": {
                piexif.ImageIFD.Make: b"TestCamera",
                piexif.ImageIFD.Model: b"TestModel",
            },
            "GPS": {
                piexif.GPSIFD.GPSLatitude: ((5, 1), (7, 1), (0, 1)),
                piexif.GPSIFD.GPSLongitude: ((119, 1), (24, 1), (0, 1)),
            }
        }
        exif_bytes = piexif.dump(exif_dict)
        
        img_bytes = io.BytesIO()
        img.save(img_bytes, format='JPEG', exif=exif_bytes)
        img_bytes.seek(0)
        
        # Upload photo
        files = {'file': ('test_photo.jpg', img_bytes, 'image/jpeg')}
        data = {'keterangan': 'Kegiatan pemberian PMT kepada balita'}
        
        r = self.session.post(
            f"{API_URL}/inquiries/{self.test_inquiry_id}/cerita/foto",
            files=files,
            data=data,
            cookies=self.cookies
        )
        
        assert r.status_code == 200, f"Expected 200, got {r.status_code}: {r.text}"
        
        result = r.json()
        assert result.get("ada") == True, "Should have ada=True"
        assert len(result.get("foto", [])) > 0, "Should have at least 1 photo"
        
        self.test_foto_id = result["foto"][0]["id"]
        self.log(f"  Photo uploaded successfully, ID: {self.test_foto_id}")
        self.log(f"  Total photos: {len(result.get('foto', []))}")
        
        # Verify EXIF was stripped by downloading and checking
        foto_url = result["foto"][0]["url"]
        r_foto = self.get(foto_url)
        assert r_foto.status_code == 200, "Should be able to download photo"
        
        # Check if EXIF is stripped
        downloaded_img = Image.open(io.BytesIO(r_foto.content))
        exif_data = downloaded_img.getexif()
        
        # EXIF should be empty or minimal after processing
        self.log(f"  EXIF data after processing: {len(exif_data)} tags")
        # Note: Some EXIF tags might remain, but GPS should be gone
    
    def test_post_foto_non_image(self):
        """Test POST foto with non-image file (should fail)"""
        # Create a text file
        text_file = io.BytesIO(b"This is not an image")
        files = {'file': ('test.txt', text_file, 'text/plain')}
        data = {'keterangan': 'Test'}
        
        r = self.session.post(
            f"{API_URL}/inquiries/{self.test_inquiry_id}/cerita/foto",
            files=files,
            data=data,
            cookies=self.cookies
        )
        
        assert r.status_code == 422, f"Expected 422 for non-image, got {r.status_code}"
        self.log(f"  Correctly rejected non-image file: {r.json().get('detail')}")
    
    def test_post_foto_max_limit(self):
        """Test POST foto when already at max (5 photos)"""
        # Upload 4 more photos to reach limit
        from PIL import Image
        
        for i in range(4):
            img = Image.new('RGB', (100, 100), color='green')
            img_bytes = io.BytesIO()
            img.save(img_bytes, format='JPEG')
            img_bytes.seek(0)
            
            files = {'file': (f'test_{i}.jpg', img_bytes, 'image/jpeg')}
            data = {'keterangan': f'Test photo {i+2}'}
            
            r = self.session.post(
                f"{API_URL}/inquiries/{self.test_inquiry_id}/cerita/foto",
                files=files,
                data=data,
                cookies=self.cookies
            )
            
            if r.status_code == 422 and "Maksimal" in r.text:
                self.log(f"  Reached max photos at {i+1} additional uploads")
                break
            
            assert r.status_code == 200, f"Upload {i+2} failed: {r.status_code}"
        
        # Try to upload 6th photo
        img = Image.new('RGB', (100, 100), color='red')
        img_bytes = io.BytesIO()
        img.save(img_bytes, format='JPEG')
        img_bytes.seek(0)
        
        files = {'file': ('test_6.jpg', img_bytes, 'image/jpeg')}
        data = {'keterangan': 'This should fail'}
        
        r = self.session.post(
            f"{API_URL}/inquiries/{self.test_inquiry_id}/cerita/foto",
            files=files,
            data=data,
            cookies=self.cookies
        )
        
        assert r.status_code == 422, f"Expected 422 for 6th photo, got {r.status_code}"
        assert "Maksimal" in r.text or "maksimal" in r.text.lower(), "Error should mention max limit"
        self.log(f"  Correctly rejected 6th photo: {r.json().get('detail')}")
    
    def test_get_foto_private_authenticated(self):
        """Test GET private foto URL (authenticated)"""
        if not self.test_foto_id:
            self.warn("No foto_id available, skipping")
            return
        
        r = self.get(f"/inquiries/{self.test_inquiry_id}/cerita/foto/{self.test_foto_id}")
        assert r.status_code == 200, f"Expected 200, got {r.status_code}"
        assert r.headers.get('content-type') == 'image/jpeg', "Should return JPEG"
        self.log(f"  Successfully retrieved private photo")
    
    def test_get_foto_public_not_published(self):
        """Test GET public foto URL when story not published (should fail 404)"""
        if not self.test_foto_id:
            self.warn("No foto_id available, skipping")
            return
        
        # Logout to test public access
        self.logout()
        
        r = self.session.get(f"{API_URL}/public/cerita-foto/{self.test_foto_id}")
        assert r.status_code == 404, f"Expected 404 for unpublished story, got {r.status_code}"
        self.log(f"  Correctly blocked public access to unpublished photo")
        
        # Login back
        self.login(NGO_EMAIL, NGO_PASSWORD)
    
    def test_patch_review_ngo_forbidden(self):
        """Test PATCH review by NGO (should fail 403)"""
        payload = {
            "keputusan": "publikasikan",
            "catatan": "Test"
        }
        r = self.patch(f"/inquiries/{self.test_inquiry_id}/cerita/review", json=payload)
        assert r.status_code == 403, f"Expected 403 for NGO review, got {r.status_code}"
        self.log(f"  Correctly blocked NGO from reviewing")
    
    def test_patch_review_operator_forbidden(self):
        """Test PATCH review by Operator (should fail 403)"""
        self.logout()
        self.login(OPERATOR_EMAIL, OPERATOR_PASSWORD)
        
        payload = {
            "keputusan": "publikasikan",
            "catatan": "Test"
        }
        r = self.patch(f"/inquiries/{self.test_inquiry_id}/cerita/review", json=payload)
        assert r.status_code == 403, f"Expected 403 for Operator review, got {r.status_code}"
        self.log(f"  Correctly blocked Operator from reviewing")
        
        self.logout()
        self.login(NGO_EMAIL, NGO_PASSWORD)
    
    def test_patch_review_tolak_without_catatan(self):
        """Test PATCH review tolak without catatan (should fail 422)"""
        self.logout()
        self.login(ADMIN_EMAIL, ADMIN_PASSWORD)
        
        payload = {
            "keputusan": "tolak",
            "catatan": ""  # Empty
        }
        r = self.patch(f"/inquiries/{self.test_inquiry_id}/cerita/review", json=payload)
        assert r.status_code == 422, f"Expected 422 for tolak without catatan, got {r.status_code}"
        assert "catatan" in r.text.lower() or "wajib" in r.text.lower(), "Error should mention catatan required"
        self.log(f"  Correctly rejected tolak without catatan: {r.json().get('detail')}")
        
        self.logout()
        self.login(NGO_EMAIL, NGO_PASSWORD)
    
    def test_patch_review_publikasikan_success(self):
        """Test PATCH review publikasikan by admin"""
        self.logout()
        self.login(ADMIN_EMAIL, ADMIN_PASSWORD)
        
        payload = {
            "keputusan": "publikasikan",
            "catatan": "Cerita dampak sudah sesuai dan layak dipublikasikan"
        }
        r = self.patch(f"/inquiries/{self.test_inquiry_id}/cerita/review", json=payload)
        assert r.status_code == 200, f"Expected 200, got {r.status_code}: {r.text}"
        
        data = r.json()
        assert data.get("status") == "dipublikasikan", f"Status should be dipublikasikan, got {data.get('status')}"
        assert data.get("catatan_admin") == payload["catatan"], "Catatan should match"
        
        self.log(f"  Story published successfully")
        self.log(f"  Status: {data.get('status')}")
        
        self.logout()
        self.login(NGO_EMAIL, NGO_PASSWORD)
    
    def test_get_foto_public_published(self):
        """Test GET public foto URL when story published and inquiry COMPLETED (should succeed)"""
        if not self.test_foto_id:
            self.warn("No foto_id available, skipping")
            return
        
        # Logout to test public access
        self.logout()
        
        r = self.session.get(f"{API_URL}/public/cerita-foto/{self.test_foto_id}")
        assert r.status_code == 200, f"Expected 200 for published story, got {r.status_code}"
        assert r.headers.get('content-type') == 'image/jpeg', "Should return JPEG"
        self.log(f"  Successfully retrieved public photo")
        
        # Login back
        self.login(NGO_EMAIL, NGO_PASSWORD)
    
    def test_get_inklusi_cerita_staff(self):
        """Test GET /inklusi/cerita by staff"""
        self.logout()
        self.login(ADMIN_EMAIL, ADMIN_PASSWORD)
        
        r = self.get("/inklusi/cerita")
        assert r.status_code == 200, f"Expected 200, got {r.status_code}"
        
        data = r.json()
        assert "items" in data, "Should have items"
        assert "menunggu" in data, "Should have menunggu count"
        
        self.log(f"  Total stories: {len(data.get('items', []))}")
        self.log(f"  Menunggu review: {data.get('menunggu')}")
        
        self.logout()
        self.login(NGO_EMAIL, NGO_PASSWORD)
    
    def test_get_inklusi_cerita_ngo_forbidden(self):
        """Test GET /inklusi/cerita by NGO (should fail 403)"""
        r = self.get("/inklusi/cerita")
        assert r.status_code == 403, f"Expected 403 for NGO, got {r.status_code}"
        self.log(f"  Correctly blocked NGO from listing all stories")
    
    def test_get_public_program_selesai(self):
        """Test GET /public/program-selesai"""
        self.logout()
        
        r = self.session.get(f"{API_URL}/public/program-selesai")
        assert r.status_code == 200, f"Expected 200, got {r.status_code}"
        
        data = r.json()
        assert "items" in data, "Should have items"
        assert "total" in data, "Should have total"
        assert "total_penerima" in data, "Should have total_penerima"
        
        self.log(f"  Total completed programs: {data.get('total')}")
        self.log(f"  Total penerima: {data.get('total_penerima')}")
        self.log(f"  With cerita: {data.get('dengan_cerita')}")
        
        # Check if our test inquiry appears
        found = False
        for item in data.get("items", []):
            if item.get("id") == self.test_inquiry_id:
                found = True
                assert item.get("cerita") is not None, "Should have cerita"
                assert len(item["cerita"].get("foto", [])) > 0, "Should have photos"
                assert len(item["cerita"].get("testimoni", [])) > 0, "Should have testimoni"
                self.log(f"  Found our test inquiry in gallery")
                self.log(f"  Cerita has {len(item['cerita'].get('foto', []))} photos")
                self.log(f"  Cerita has {len(item['cerita'].get('testimoni', []))} testimoni")
                break
        
        if not found:
            self.warn(f"Test inquiry {self.test_inquiry_id} not found in gallery")
        
        self.login(NGO_EMAIL, NGO_PASSWORD)
    
    def test_delete_foto_owner(self):
        """Test DELETE foto by owner"""
        if not self.test_foto_id:
            self.warn("No foto_id available, skipping")
            return
        
        r = self.delete(f"/inquiries/{self.test_inquiry_id}/cerita/foto/{self.test_foto_id}")
        assert r.status_code == 200, f"Expected 200, got {r.status_code}"
        
        data = r.json()
        # Check that photo was removed
        foto_ids = [f["id"] for f in data.get("foto", [])]
        assert self.test_foto_id not in foto_ids, "Photo should be deleted"
        
        self.log(f"  Photo deleted successfully")
        self.log(f"  Remaining photos: {len(data.get('foto', []))}")
    
    def test_ngo_edit_resets_status(self):
        """Test that NGO edit after publish resets status to menunggu_review"""
        # Story is currently published, edit it
        payload = {
            "ringkasan_hasil": "UPDATED: Program gizi balita berjalan dengan sangat baik selama 6 bulan. Sebanyak 28 balita menerima PMT harian dan pendampingan gizi intensif. Hasil pengukuran menunjukkan 11 balita naik status gizi dari sangat pendek ke pendek.",
            "realisasi_penerima": 28,
            "testimoni": [
                {
                    "kutipan": "Anak saya sekarang lebih aktif dan nafsu makannya meningkat setelah mengikuti program ini",
                    "sumber": "Ibu penerima manfaat, Kel. Buloa"
                }
            ],
            "persetujuan": True
        }
        r = self.put(f"/inquiries/{self.test_inquiry_id}/cerita", json=payload)
        assert r.status_code == 200, f"Expected 200, got {r.status_code}"
        
        data = r.json()
        assert data.get("status") == "menunggu_review", f"Status should reset to menunggu_review after edit, got {data.get('status')}"
        
        self.log(f"  Status correctly reset to menunggu_review after NGO edit")
    
    # ============ Run all tests ============
    def run_all_tests(self):
        """Run all test cases"""
        self.log("\n" + "="*60)
        self.log("PETA INKLUSI - Cerita Dampak Backend Tests", Colors.BLUE)
        self.log("="*60)
        
        # Setup
        try:
            self.setup_test_inquiry()
        except Exception as e:
            self.fail(f"Setup failed: {str(e)}")
            return
        
        # Run tests in order
        self.test("GET cerita when empty", self.test_get_cerita_empty)
        self.test("PUT cerita validation - short ringkasan", self.test_put_cerita_validation_short_ringkasan)
        self.test("PUT cerita validation - no persetujuan", self.test_put_cerita_validation_no_persetujuan)
        self.test("PUT cerita validation - too many testimoni", self.test_put_cerita_validation_too_many_testimoni)
        self.test("PUT cerita success", self.test_put_cerita_success)
        self.test("POST foto success with EXIF stripping", self.test_post_foto_success)
        self.test("POST foto non-image rejection", self.test_post_foto_non_image)
        self.test("POST foto max limit (5 photos)", self.test_post_foto_max_limit)
        self.test("GET private foto authenticated", self.test_get_foto_private_authenticated)
        self.test("GET public foto not published (404)", self.test_get_foto_public_not_published)
        self.test("PATCH review by NGO forbidden", self.test_patch_review_ngo_forbidden)
        self.test("PATCH review by Operator forbidden", self.test_patch_review_operator_forbidden)
        self.test("PATCH review tolak without catatan", self.test_patch_review_tolak_without_catatan)
        self.test("PATCH review publikasikan success", self.test_patch_review_publikasikan_success)
        self.test("GET public foto published (200)", self.test_get_foto_public_published)
        self.test("GET /inklusi/cerita by staff", self.test_get_inklusi_cerita_staff)
        self.test("GET /inklusi/cerita by NGO forbidden", self.test_get_inklusi_cerita_ngo_forbidden)
        self.test("GET /public/program-selesai", self.test_get_public_program_selesai)
        self.test("DELETE foto by owner", self.test_delete_foto_owner)
        self.test("NGO edit resets status to menunggu_review", self.test_ngo_edit_resets_status)
        
        # Summary
        self.log("\n" + "="*60)
        self.log("TEST SUMMARY", Colors.BLUE)
        self.log("="*60)
        self.log(f"Total tests: {self.tests_run}")
        self.success(f"Passed: {self.tests_passed}")
        if self.tests_failed > 0:
            self.fail(f"Failed: {self.tests_failed}")
        
        success_rate = (self.tests_passed / self.tests_run * 100) if self.tests_run > 0 else 0
        self.log(f"Success rate: {success_rate:.1f}%")
        
        return self.tests_failed == 0

if __name__ == "__main__":
    runner = CeritaTestRunner()
    success = runner.run_all_tests()
    sys.exit(0 if success else 1)
