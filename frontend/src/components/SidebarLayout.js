import React, { useEffect, useMemo, useRef, useState } from "react";
import { NavLink, useLocation, useNavigate } from "react-router-dom";
import A11yAssistant from "@/features/a11y/Assistant";
import { useAuth } from "@/context/AuthContext";
import { usePageTitle } from "@/hooks/usePageTitle";
import api from "@/lib/api";
import {
  Accessibility, Baby, BarChart3, Bell, CalendarClock, Camera, ClipboardCheck, ClipboardList, Database,
  FileEdit, Globe, GraduationCap, Hand, HandHeart, Home, KeyRound, Layers3, LayoutDashboard, ListTree,
  LogIn, LogOut, Mail, Map, MapPin, Menu, ScrollText, Search, Send, ShieldCheck, Sparkles, Target,
  User, UserCheck, Users, X,
} from "lucide-react";
import BrandLogo from "@/components/BrandLogo";
import { MENU, UTILITY_ITEMS, grupHalaman, judulHalaman, menuDatar } from "@/constants/menu";
import { SCOPED, SUPER, USER_MANAGERS } from "@/constants/roles";

/** Pemetaan nama ikon pada menu terpusat ke komponen lucide. */
const IKON = {
  accessibility: Accessibility, baby: Baby, calendar: CalendarClock, camera: Camera, chart: BarChart3,
  check: ClipboardCheck, clipboard: ClipboardList, dashboard: LayoutDashboard, database: Database,
  edit: FileEdit, globe: Globe, graduation: GraduationCap, hand: Hand, handHeart: HandHeart, home: Home,
  key: KeyRound, layers: Layers3, listTree: ListTree, mail: Mail, map: Map, mapPin: MapPin, scroll: ScrollText,
  send: Send, shield: ShieldCheck, sparkles: Sparkles, target: Target, userCheck: UserCheck, users: Users,
};

/** Halaman yang memakai seluruh area (tanpa padding & scroll) */
const FULL_BLEED = ["/peta-kemiskinan", "/peta-sosial", "/ngo/peta-sosial", "/ngo/peta-kemiskinan"];

function NavItem({ item, badge, onNavigate }) {
  const Ic = IKON[item.icon] || LayoutDashboard;
  return (
    <NavLink
      to={item.to}
      end={!!item.end}
      data-testid={item.testid}
      onClick={onNavigate}
      className={({ isActive }) =>
        `group flex min-h-10 items-center gap-3 rounded-md border-l-4 py-2 pl-2 pr-3 text-sm font-semibold transition-colors focus:outline-none ${
          isActive
            ? "border-white/80 bg-[#117A69] text-white shadow-sm"
            : "border-transparent text-slate-600 hover:bg-slate-100 hover:text-slate-900"
        }`
      }
    >
      <Ic className="h-[18px] w-[18px] shrink-0" />
      <span className="flex-1">{item.label}</span>
      {badge > 0 && (
        <span
          aria-hidden="true"
          className="inline-flex h-5 min-w-[1.25rem] items-center justify-center rounded-full bg-red-600 px-1 text-[11px] font-bold text-white"
        >
          {badge > 99 ? "99+" : badge}
        </span>
      )}
    </NavLink>
  );
}

export function SidebarLayout({ children }) {
  const { user, logout } = useAuth();
  const navigate = useNavigate();
  const location = useLocation();
  const [pending, setPending] = useState(0);
  const [pendingVerif, setPendingVerif] = useState(0);
  const [sidebarOpen, setSidebarOpen] = useState(false);
  const [query, setQuery] = useState("");
  const menuButtonRef = useRef(null);
  const sidebarCloseRef = useRef(null);

  const isSuper = SUPER.includes(user?.role);
  const canManageUsers = USER_MANAGERS.includes(user?.role);
  const canVerify = isSuper || user?.role === "verifikator";
  const scopeLabel = useMemo(() => {
    if (!user || !SCOPED.includes(user.role)) return "";
    const wil = (user.wilayah || "").trim();
    if (!wil || wil.toLowerCase() === "kota makassar") return "";
    if (user.role === "petugas" && user.kelurahan) {
      const rt = Array.isArray(user.rt) && user.rt.length ? ` / RT ${user.rt.join(",")}` : "";
      return `${user.kelurahan} · RW ${user.rw || "-"}${rt}`;
    }
    return `Kec. ${wil}`;
  }, [user]);
  const fullBleed = FULL_BLEED.includes(location.pathname);

  const visible = (items) =>
    items.filter((n) => !n.roles || (user && n.roles.includes(user.role)));

  // Daftar datar untuk pencarian menu — alternatif kedua menemukan halaman (WCAG 2.4.5)
  const flatMenu = useMemo(() => menuDatar(user), [user]);

  const q = query.trim().toLowerCase();
  const results = useMemo(
    () => (q ? flatMenu.filter((n) => n.label.toLowerCase().includes(q)) : []),
    [q, flatMenu]
  );

  // Grup halaman aktif — dipakai sebagai penanda lokasi di header
  const currentGroup = useMemo(() => grupHalaman(location.pathname, user), [location.pathname, user]);

  const pageTitle = useMemo(() => judulHalaman(location.pathname, user), [location.pathname, user]);

  // Judul dokumen unik per halaman (WCAG 2.4.2).
  // WAJIB dipanggil SETELAH pageTitle dideklarasikan: memakainya lebih awal
  // memicu ReferenceError "Cannot access 'pageTitle' before initialization".
  usePageTitle(pageTitle);

  useEffect(() => {
    if (!canManageUsers) { setPending(0); return; }
    let alive = true;
    const fetchPending = () =>
      api.get("/admin/pending-count")
        .then((r) => { if (alive) setPending(r.data.pending || 0); })
        .catch(() => {});
    fetchPending();
    const t = setInterval(fetchPending, 30000);
    return () => { alive = false; clearInterval(t); };
  }, [user, canManageUsers]);

  useEffect(() => {
    if (!canVerify) { setPendingVerif(0); return; }
    let alive = true;
    const fetchVerif = () =>
      api.get("/verifikasi/count")
        .then((r) => { if (alive) setPendingVerif(r.data.pending || 0); })
        .catch(() => {});
    fetchVerif();
    const t = setInterval(fetchVerif, 30000);
    return () => { alive = false; clearInterval(t); };
  }, [user, canVerify]);

  useEffect(() => { setSidebarOpen(false); }, [location.pathname]);

  // Drawer seluler: tutup dengan Escape, pindahkan fokus ke dalam saat terbuka,
  // dan kembalikan fokus ke tombol pemicu saat ditutup (WCAG 2.4.3).
  useEffect(() => {
    if (!sidebarOpen) return undefined;
    sidebarCloseRef.current?.focus();
    const onKey = (e) => {
      if (e.key === "Escape") {
        setSidebarOpen(false);
        menuButtonRef.current?.focus();
      }
    };
    window.addEventListener("keydown", onKey);
    return () => window.removeEventListener("keydown", onKey);
  }, [sidebarOpen]);

  // Beri tahu peta (Leaflet/Google) agar menghitung ulang ukuran saat layout berubah
  useEffect(() => {
    const t = setTimeout(() => window.dispatchEvent(new Event("resize")), 250);
    return () => clearTimeout(t);
  }, [sidebarOpen]);

  return (
    <div className="flex h-screen h-[100dvh] overflow-hidden bg-slate-50">
      {/* Elemen fokus pertama: lewati navigasi (WCAG 2.4.1) */}
      <a
        href="#konten-utama"
        className="sr-only focus:not-sr-only focus:absolute focus:left-2 focus:top-2 focus:z-[999] focus:rounded focus:bg-white focus:px-3 focus:py-2 focus:text-slate-900"
        data-testid="skip-link"
      >
        Lewati ke konten utama
      </a>

      {/* ---------------- Sidebar ---------------- */}
      <aside
        data-testid="sidebar"
        id="app-sidebar"
        className={`fixed inset-y-0 left-0 z-50 flex w-[min(280px,85vw)] shrink-0 flex-col border-r border-slate-200 bg-white shadow-xl transition-transform duration-200 lg:static lg:w-[240px] lg:translate-x-0 lg:shadow-none ${
          sidebarOpen ? "translate-x-0" : "-translate-x-full invisible lg:visible"
        }`}
      >
        <div className="flex h-14 items-center gap-2 border-b border-white/10 bg-[#232F3E] px-4">
          <NavLink to="/" aria-label="Beranda PETA INKLUSI" data-testid="sidebar-logo">
            <BrandLogo className="h-9 w-9" withText dark />
          </NavLink>
          <button
            type="button"
            ref={sidebarCloseRef}
            className="ml-auto inline-flex h-11 w-11 items-center justify-center rounded-md text-slate-300 hover:bg-white/10 hover:text-white lg:hidden"
            data-testid="sidebar-close"
            onClick={() => { setSidebarOpen(false); menuButtonRef.current?.focus(); }}
            aria-label="Tutup menu"
          >
            <X className="h-5 w-5" />
          </button>
        </div>

        <nav className="flex min-h-0 flex-1 flex-col" data-testid="sidebar-nav" aria-label="Navigasi utama">
          <div className="border-b border-slate-200 p-3">
            <label htmlFor="nav-search" className="sr-only">Cari menu</label>
            <div className="relative">
              <Search className="pointer-events-none absolute left-2.5 top-1/2 h-4 w-4 -translate-y-1/2 text-slate-500" aria-hidden="true" />
              <input
                id="nav-search"
                type="search"
                value={query}
                onChange={(e) => setQuery(e.target.value)}
                onKeyDown={(e) => { if (e.key === "Escape") setQuery(""); }}
                placeholder="Cari menu…"
                className="h-10 w-full rounded-md border border-slate-300 bg-white pl-8 pr-2 text-sm"
                data-testid="nav-search"
              />
            </div>
          </div>

          <div className="flex-1 space-y-3 overflow-y-auto p-3">
            {q ? (
              <div className="space-y-1">
                <p className="px-3 text-[11px] font-semibold text-slate-600" role="status" aria-live="polite">
                  {results.length} menu ditemukan
                </p>
                {results.length === 0 && (
                  <p className="px-3 text-sm text-slate-600">Tidak ada menu yang cocok. Coba kata lain.</p>
                )}
                {results.map((item) => (
                  <NavItem
                    key={`${item.grup}-${item.to}`}
                    item={item}
                    badge={item.to === "/verifikasi" ? pendingVerif : 0}
                    onNavigate={() => { setQuery(""); setSidebarOpen(false); }}
                  />
                ))}
              </div>
            ) : (
              MENU.map((group, gi) => {
                const items = visible(group.items);
                if (!items.length) return null;
                return (
                  <div key={group.id || `g${gi}`} className="space-y-1">
                    {group.label && (
                      <p className="px-3 pt-1 text-[10px] font-bold uppercase tracking-wider text-slate-600">
                        {group.label}
                      </p>
                    )}
                    {items.map((item) => (
                      <NavItem
                        key={item.to}
                        item={item}
                        badge={item.to === "/verifikasi" ? pendingVerif : 0}
                      />
                    ))}
                  </div>
                );
              })
            )}
          </div>
        </nav>

        <div className="border-t border-slate-200 p-3">
          <div className="mb-2 space-y-1">
            {UTILITY_ITEMS.map((item) => <NavItem key={item.to} item={item} />)}
          </div>
          {user ? (
            <>
              <div className="mb-2 flex items-center gap-2" data-testid="sidebar-user">
                <div className="flex h-8 w-8 items-center justify-center rounded-full bg-slate-200 text-slate-600">
                  <User className="h-4 w-4" />
                </div>
                <div className="min-w-0 leading-tight">
                  <p className="truncate text-xs font-bold text-slate-800">{user.name}</p>
                  <p className="truncate text-[10px] capitalize text-slate-500">
                    {user.role === "ngo" ? `NGO · ${user.organisasi || ""}` : `${user.role}${user.wilayah ? ` · ${user.wilayah}` : ""}`}
                  </p>
                </div>
              </div>
              <button
                type="button"
                data-testid="logout-btn"
                onClick={async () => { await logout(); navigate("/"); }}
                className="flex w-full items-center gap-3 rounded-md px-3 py-2 text-sm font-semibold text-slate-600 transition-colors hover:bg-red-50 hover:text-red-700"
              >
                <LogOut className="h-[18px] w-[18px]" aria-hidden="true" /> Keluar
              </button>
            </>
          ) : (
            <button
              type="button"
              data-testid="header-login-btn"
              onClick={() => navigate("/login")}
              className="flex w-full items-center gap-3 rounded-md bg-primary px-3 py-2 text-sm font-semibold text-primary-foreground"
            >
              <LogIn className="h-[18px] w-[18px]" /> Masuk
            </button>
          )}
        </div>
      </aside>

      {sidebarOpen && (
        <div
          className="fixed inset-0 z-40 bg-black/40 lg:hidden"
          data-testid="sidebar-backdrop"
          aria-hidden="true"
          onClick={() => setSidebarOpen(false)}
        />
      )}

      {/* ---------------- Konten ---------------- */}
      <div className="flex min-w-0 flex-1 flex-col">

        <header className="flex min-h-14 shrink-0 flex-wrap items-center gap-2 border-b border-slate-200 bg-white px-2 py-1 sm:gap-3 sm:px-3 lg:px-5">
          <button
            type="button"
            ref={menuButtonRef}
            onClick={() => setSidebarOpen(true)}
            className="inline-flex h-11 w-11 shrink-0 items-center justify-center rounded-md text-slate-600 hover:bg-slate-100 lg:hidden"
            aria-label="Buka menu navigasi"
            aria-controls="app-sidebar"
            aria-expanded={sidebarOpen}
            data-testid="sidebar-open"
          >
            <Menu className="h-5 w-5" />
          </button>

          <div className="min-w-0 flex-1 sm:flex-none">
            <h1 className="truncate font-head text-sm font-extrabold uppercase tracking-tight text-slate-900 md:text-base">
              {pageTitle}
            </h1>
            <p className="hidden text-[10px] text-slate-500 sm:block">{currentGroup || "Kota Makassar"}</p>
          </div>

          {/* Slot filter halaman (mis. Kelurahan / RW / Terapkan pada Peta) */}
          <div id="layout-header-slot" className="ml-auto flex min-w-0 items-center gap-2" />

          {scopeLabel && (
            <span
              data-testid="wilayah-scope-badge"
              title="Data yang ditampilkan dibatasi pada wilayah ini"
              className="hidden max-w-[220px] shrink-0 items-center gap-1 truncate rounded-full border border-[#117A69]/30 bg-[#117A69]/10 px-2.5 py-1 text-[11px] font-bold text-[#0f5f52] sm:inline-flex"
            >
              <MapPin className="h-3 w-3 shrink-0" /> <span className="truncate">{scopeLabel}</span>
            </span>
          )}

          {canManageUsers && (
            <button
              type="button"
              data-testid="notif-bell"
              onClick={() => navigate("/kelola-petugas")}
              aria-label={
                pending > 0
                  ? `Kelola petugas — ${pending} akun menunggu persetujuan`
                  : "Kelola petugas — tidak ada akun menunggu persetujuan"
              }
              className="relative inline-flex h-11 w-11 shrink-0 items-center justify-center rounded-md border border-slate-300 text-slate-600 hover:bg-slate-100 lg:h-9 lg:w-9"
            >
              <Bell className="h-4 w-4" aria-hidden="true" />
              {pending > 0 && (
                <span
                  data-testid="notif-badge"
                  aria-hidden="true"
                  className="absolute -right-1.5 -top-1.5 inline-flex h-5 min-w-[1.25rem] items-center justify-center rounded-full bg-red-600 px-1 text-[11px] font-bold text-white"
                >
                  {pending > 99 ? "99+" : pending}
                </span>
              )}
            </button>
          )}
          {/* Perubahan jumlah antrean diumumkan ke pembaca layar (WCAG 4.1.3) */}
          <span className="sr-only" role="status" aria-live="polite">
            {pending > 0 ? `${pending} akun menunggu persetujuan` : ""}
          </span>
        </header>

        <main
          id="konten-utama"
          tabIndex={-1}
          data-testid="main-content"
          className={fullBleed ? "relative min-h-0 flex-1 overflow-hidden" : "min-h-0 flex-1 overflow-y-auto px-3 pb-[calc(6rem+env(safe-area-inset-bottom))] pt-4 sm:px-4 sm:pt-6 lg:px-6 lg:pb-20"}
        >
          {fullBleed ? children : <div className="mx-auto w-full max-w-7xl min-[1920px]:max-w-[1680px]">{children}</div>}
        </main>
      </div>
      <A11yAssistant />
    </div>
  );
}

export default SidebarLayout;
