import "@/App.css";
import { BrowserRouter, Routes, Route, Navigate } from "react-router-dom";
import { Toaster } from "sonner";
import { AuthProvider, useAuth } from "@/context/AuthContext";
import { AccessibilityProvider } from "@/context/AccessibilityContext";
import { SidebarLayout } from "@/components/SidebarLayout";
import Landing from "@/pages/Landing";
import Login from "@/pages/Login";
import Dashboard from "@/pages/Dashboard";
import PetaGIS from "@/pages/PetaGIS";
import DataRumah from "@/pages/DataRumah";
import Bantuan from "@/pages/Bantuan";
import SosialDashboard from "@/pages/SosialDashboard";
import RumahTangga from "@/pages/RumahTangga";
import PetaSosial from "@/pages/PetaSosial";
import PetaDasar from "@/pages/PetaDasar";
import ImportWizard from "@/pages/ImportWizard";
import MasterKode from "@/pages/MasterKode";
import KoordinatGIS from "@/pages/KoordinatGIS";
import PrioritasIntervensi from "@/pages/PrioritasIntervensi";
import DisabilitasDashboard from "@/pages/DisabilitasDashboard";
import StuntingDashboard from "@/pages/StuntingDashboard";
import RadDisabilitas from "@/pages/RadDisabilitas";
import Administrasi from "@/pages/Administrasi";
import AIAnalysis from "@/pages/AIAnalysis";
import AIAssistant from "@/pages/AIAssistant";
import Disabilitas from "@/pages/Disabilitas";
import DataEntry from "@/pages/DataEntry";
import KelolaPetugas from "@/pages/KelolaPetugas";
import Rekap from "@/pages/Rekap";
import Verifikasi from "@/pages/Verifikasi";
import PublicDashboard from "@/pages/PublicDashboard";
import FlowSistem, { FlowSistemContent } from "@/pages/FlowSistem";
import Laporan from "@/pages/Laporan";
import Matriks from "@/pages/Matriks";
import Musrenbang from "@/pages/Musrenbang";
import ImporKualitas from "@/pages/ImporKualitas";
import Tentang, { PublicPetaSosial, PublicPetaKemiskinan } from "@/pages/Tentang";
import PetaKemiskinan from "@/pages/PetaKemiskinan";
import { PublicDashboardContent } from "@/pages/PublicDashboard";
import InklusiMap from "@/features/inklusi/InklusiMap";
import AdminOverview from "@/pages/AdminOverview";
import { DataStunting, DataATS, ProgramManajemen, RolePermission, AuditLog } from "@/pages/InklusiPages";
import { InquiryForm, InquiryList, InquiryDetail } from "@/features/inklusi/Inquiry";
import { LaporanWilayah, EmailOutbox } from "@/features/inklusi/InklusiExtra";
import RingkasanMingguan from "@/features/inklusi/RingkasanMingguan";
import BisindoSettings from "@/features/a11y/BisindoSettings";
import { VervalBeranda, VervalForm } from "@/pages/VervalOperator";
import VervalReview from "@/pages/VervalReview";
import VervalPenugasan from "@/pages/VervalPenugasan";
import {
  ADMINS, INTERNAL, USER_MANAGERS as USER_MANAGER_ROLES,
  VERVAL_OPERATOR as VERVAL_OPERATOR_ROLES, VERVAL_PENUGASAN as VERVAL_PENUGASAN_ROLES,
  VERVAL_REVIEWER as VERVAL_REVIEWER_ROLES,
} from "@/constants/roles";

/** Halaman awal sesuai peran (dipakai untuk pengalihan). */
export function homeFor(role) {
  if (role === "ngo") return "/ngo/inquiry";
  if (VERVAL_OPERATOR_ROLES.includes(role)) return "/verval";
  return "/dashboard";
}

function ProtectedRoute({ children, roles }) {
  const { user, loading } = useAuth();
  if (loading) return <div className="p-10 text-center text-muted-foreground">Memuat…</div>;
  if (!user) return <Navigate to="/login" replace />;
  if (roles && !roles.includes(user.role)) return <Navigate to={homeFor(user.role)} replace />;
  return children;
}

/** Dashboard sesuai peran: NGO -> daftar inquiry, Admin -> ringkasan PETA INKLUSI, lainnya -> dashboard lama. */
function RoleDashboard() {
  const { user, loading } = useAuth();
  if (loading) return <div className="p-10 text-center text-muted-foreground">Memuat…</div>;
  if (!user) return <Navigate to="/login" replace />;
  if (user.role === "ngo") return <Navigate to="/ngo/inquiry" replace />;
  if (VERVAL_OPERATOR_ROLES.includes(user.role)) return <Navigate to="/verval" replace />;
  if (["superadmin", "admin"].includes(user.role)) return <AppShell><AdminOverview /></AppShell>;
  return <AppShell><Dashboard /></AppShell>;
}

/** Halaman internal: wajib login & bukan NGO. */
function Internal({ children, roles = INTERNAL }) {
  return <AppShell><ProtectedRoute roles={roles}>{children}</ProtectedRoute></AppShell>;
}

function AdminRoute({ children, roles = ["superadmin", "admin"] }) {
  const { user, loading } = useAuth();
  if (loading) return <div className="p-10 text-center text-muted-foreground">Memuat…</div>;
  if (!user) return <Navigate to="/login" replace />;
  if (!roles.includes(user.role)) return <Navigate to={homeFor(user.role)} replace />;
  return children;
}

/** NGO: peta kemiskinan agregat (tanpa peta bangunan/data rumah individu). */
function PetaKemiskinanNgo() {
  return (
    <div className="h-full w-full" data-testid="page-peta-kemiskinan-ngo">
      <InklusiMap kategoriList={["kemiskinan"]} title="Peta Kemiskinan" />
    </div>
  );
}

function AppShell({ children }) {
  return <SidebarLayout>{children}</SidebarLayout>;
}

function App() {
  return (
    <div className="App">
      <AccessibilityProvider>
        <AuthProvider>
          <BrowserRouter>
            <Toaster position="bottom-right" richColors containerAriaLabel="Notifikasi" />
            <Routes>
              <Route path="/" element={<Landing />} />
              <Route path="/login" element={<Login />} />
              {/* ---------- Publik (tanpa login, data agregat) ---------- */}
              <Route path="/publik" element={<PublicDashboard />} />
              <Route path="/publik/peta-sosial" element={<PublicPetaSosial />} />
              <Route path="/publik/peta-kemiskinan" element={<PublicPetaKemiskinan />} />
              <Route path="/dashboard-publik" element={<Navigate to="/publik" replace />} />
              <Route path="/flow-sistem" element={<FlowSistem />} />
              <Route path="/tentang" element={<Tentang />} />

              {/* ---------- Dashboard sesuai peran ---------- */}
              <Route path="/dashboard" element={<RoleDashboard />} />
              <Route path="/dashboard-lama" element={<Internal><Dashboard /></Internal>} />

              {/* ---------- NGO Inquiry ---------- */}
              <Route path="/ngo/inquiry" element={<AppShell><ProtectedRoute><InquiryList /></ProtectedRoute></AppShell>} />
              <Route path="/ngo/inquiry/baru" element={<AppShell><ProtectedRoute roles={["ngo", "superadmin", "admin"]}><InquiryForm /></ProtectedRoute></AppShell>} />
              <Route path="/ngo/inquiry/:id/revisi" element={<AppShell><ProtectedRoute roles={["ngo", "superadmin", "admin"]}><InquiryForm /></ProtectedRoute></AppShell>} />
              <Route path="/ngo/inquiry/:id" element={<AppShell><ProtectedRoute><InquiryDetail /></ProtectedRoute></AppShell>} />
              <Route path="/ngo/peta-sosial" element={<AppShell><ProtectedRoute roles={["ngo"]}><PetaSosial /></ProtectedRoute></AppShell>} />
              <Route path="/ngo/peta-kemiskinan" element={<AppShell><ProtectedRoute roles={["ngo"]}><PetaKemiskinanNgo /></ProtectedRoute></AppShell>} />
              <Route path="/ngo/statistik" element={<AppShell><ProtectedRoute roles={["ngo"]}><PublicDashboardContent headingTag="p" /></ProtectedRoute></AppShell>} />

              {/* ---------- Internal ---------- */}
              <Route path="/peta-kemiskinan" element={<Internal><PetaKemiskinan /></Internal>} />
              <Route path="/peta" element={<Navigate to="/peta-kemiskinan" replace />} />
              <Route path="/peta-rumah" element={<Internal><DataRumah /></Internal>} />
              <Route path="/bantuan" element={<Internal><Bantuan /></Internal>} />
              <Route path="/sosial" element={<Internal><SosialDashboard /></Internal>} />
              <Route path="/rumah-tangga" element={<Internal><RumahTangga /></Internal>} />
              <Route path="/peta-sosial" element={<Internal><PetaSosial /></Internal>} />
              <Route path="/peta-dasar" element={<Internal><PetaDasar /></Internal>} />
              <Route path="/prioritas" element={<Internal><PrioritasIntervensi /></Internal>} />
              <Route path="/disabilitas" element={<Internal><DisabilitasDashboard /></Internal>} />
              <Route path="/stunting" element={<Internal><StuntingDashboard /></Internal>} />
              <Route path="/data-stunting" element={<Internal><DataStunting /></Internal>} />
              <Route path="/data-ats" element={<Internal><DataATS /></Internal>} />
              <Route path="/program" element={<Internal><ProgramManajemen /></Internal>} />
              <Route path="/role-permission" element={<Internal roles={ADMINS}><RolePermission /></Internal>} />
              <Route path="/audit-log" element={<Internal roles={ADMINS}><AuditLog /></Internal>} />
              <Route path="/ringkasan-mingguan" element={<Internal roles={[...ADMINS, "pimpinan"]}><RingkasanMingguan /></Internal>} />
              <Route path="/notifikasi-email" element={<Internal roles={ADMINS}><EmailOutbox /></Internal>} />
              <Route path="/aksesibilitas-bisindo" element={<Internal roles={ADMINS}><BisindoSettings /></Internal>} />
              <Route path="/laporan-wilayah" element={<Internal roles={[...INTERNAL, "ngo"]}><LaporanWilayah /></Internal>} />
              <Route path="/rad" element={<Internal><RadDisabilitas /></Internal>} />
              <Route path="/administrasi" element={<Internal><Administrasi /></Internal>} />
              {/* Pusat laporan & pusat impor: rute lama /rekap, /laporan-wilayah, /impor,
                  /administrasi tetap hidup agar tautan lama tidak rusak. */}
              <Route path="/laporan" element={<Internal roles={[...INTERNAL, "ngo"]}><Laporan /></Internal>} />
              <Route path="/matriks" element={<Internal><Matriks /></Internal>} />
              <Route path="/musrenbang" element={<Internal><Musrenbang /></Internal>} />
              <Route path="/impor-kualitas" element={<Internal><ImporKualitas /></Internal>} />
              <Route
                path="/impor"
                element={
                  <AppShell>
                    <ProtectedRoute roles={["superadmin", "admin", "operator", "verifikator"]}>
                      <ImportWizard />
                    </ProtectedRoute>
                  </AppShell>
                }
              />
              <Route
                path="/master-kode"
                element={
                  <AppShell>
                    <AdminRoute><MasterKode /></AdminRoute>
                  </AppShell>
                }
              />
              <Route
                path="/gis-koordinat"
                element={
                  <AppShell>
                    <ProtectedRoute roles={["superadmin", "admin", "verifikator", "operator", "pimpinan"]}>
                      <KoordinatGIS />
                    </ProtectedRoute>
                  </AppShell>
                }
              />
              <Route path="/analisa-ai" element={<Internal><AIAnalysis /></Internal>} />
              <Route path="/ai-assistant" element={<Internal><AIAssistant /></Internal>} />
              <Route path="/panduan-alur" element={<Internal><FlowSistemContent /></Internal>} />
              <Route path="/aksesibilitas" element={<AppShell><Disabilitas /></AppShell>} />
              <Route
                path="/input-data"
                element={
                  <ProtectedRoute roles={["superadmin", "admin", "operator", "operator_kecamatan"]}>
                    <AppShell><DataEntry /></AppShell>
                  </ProtectedRoute>
                }
              />
              <Route
                path="/verifikasi"
                element={
                  <ProtectedRoute roles={["superadmin", "admin", "verifikator"]}>
                    <AppShell><Verifikasi /></AppShell>
                  </ProtectedRoute>
                }
              />
              <Route
                path="/rekap"
                element={
                  <ProtectedRoute roles={["superadmin", "admin", "pimpinan"]}>
                    <AppShell><Rekap /></AppShell>
                  </ProtectedRoute>
                }
              />
              <Route
                path="/kelola-petugas"
                element={
                  <AdminRoute roles={USER_MANAGER_ROLES}>
                    <AppShell><KelolaPetugas /></AppShell>
                  </AdminRoute>
                }
              />
              {/* Antrean pendaftar memakai halaman yang sama dengan filter status awal "pending". */}
              <Route
                path="/validasi-akun"
                element={
                  <AdminRoute roles={USER_MANAGER_ROLES}>
                    <AppShell><KelolaPetugas /></AppShell>
                  </AdminRoute>
                }
              />
              {/* ---------- GeoTag Verval DTSEN ---------- */}
              <Route path="/verval" element={<AppShell><ProtectedRoute roles={VERVAL_OPERATOR_ROLES}><VervalBeranda /></ProtectedRoute></AppShell>} />
              <Route path="/verval/sasaran/:ref" element={<AppShell><ProtectedRoute roles={VERVAL_OPERATOR_ROLES}><VervalForm /></ProtectedRoute></AppShell>} />
              <Route path="/verval/review" element={<Internal roles={VERVAL_REVIEWER_ROLES}><VervalReview /></Internal>} />
              <Route path="/verval/penugasan" element={<Internal roles={VERVAL_PENUGASAN_ROLES}><VervalPenugasan /></Internal>} />
              <Route path="*" element={<Navigate to="/" replace />} />
            </Routes>
          </BrowserRouter>
        </AuthProvider>
      </AccessibilityProvider>
    </div>
  );
}

export default App;
