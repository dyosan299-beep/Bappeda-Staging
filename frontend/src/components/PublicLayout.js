import React, { useEffect, useRef, useState } from "react";
import { NavLink, Link, useLocation, useNavigate } from "react-router-dom";
import { Menu, X, LogIn, LayoutDashboard } from "lucide-react";
import BrandLogo from "@/components/BrandLogo";
import { useAuth } from "@/context/AuthContext";
import { usePageTitle } from "@/hooks/usePageTitle";
import A11yAssistant from "@/features/a11y/Assistant";
import EasyReadAuto from "@/features/a11y/EasyReadAuto";
import { FR } from "@/features/a11y/ui";

const NAV = [
  { to: "/", label: "Beranda", end: true },
  { to: "/publik", label: "Dashboard Informasi Umum", end: true },
  { to: "/publik/peta-sosial", label: "Peta Sosial" },
  { to: "/publik/peta-kemiskinan", label: "Peta Kemiskinan" },
  { to: "/flow-sistem", label: "Flow Sistem" },
  { to: "/tentang", label: "Tentang" },
];

export default function PublicLayout({ children, fullBleed = false }) {
  const [open, setOpen] = useState(false);
  const { user } = useAuth();
  const navigate = useNavigate();
  const location = useLocation();
  const toggleRef = useRef(null);
  const mobileNavRef = useRef(null);

  // Judul dokumen unik per halaman (WCAG 2.4.2)
  const navTitle = NAV.find((n) => n.to === location.pathname)?.label;
  usePageTitle(navTitle || "Beranda");

  // Menu seluler: fokus masuk saat terbuka, Esc menutup dan mengembalikan fokus
  useEffect(() => {
    if (!open) return undefined;
    mobileNavRef.current?.querySelector("a")?.focus();
    const onKey = (e) => {
      if (e.key === "Escape") {
        setOpen(false);
        toggleRef.current?.focus();
      }
    };
    window.addEventListener("keydown", onKey);
    return () => window.removeEventListener("keydown", onKey);
  }, [open]);
  return (
    <div className="flex min-h-screen min-h-[100dvh] flex-col bg-slate-50">
      <a href="#konten" className="sr-only focus:not-sr-only focus:absolute focus:left-2 focus:top-2 focus:z-[999] focus:rounded focus:bg-white focus:px-3 focus:py-2">
        Lewati ke konten utama
      </a>
      <a href="#a11y-panel" onClick={(e) => { e.preventDefault(); document.querySelector('[data-testid="a11y-assistant-btn"]')?.click(); }}
        className="sr-only focus:not-sr-only focus:absolute focus:left-48 focus:top-2 focus:z-[999] focus:rounded focus:bg-white focus:px-3 focus:py-2">
        Buka Asisten Aksesibilitas (Alt + A)
      </a>
      <header className="sticky top-0 z-[600] bg-[#232F3E] pt-[env(safe-area-inset-top)] text-white shadow" data-testid="public-header">
        <div className="mx-auto flex min-h-16 max-w-7xl flex-nowrap items-center gap-1.5 px-3 py-1 sm:gap-3 sm:px-4 xl:gap-4">
          <Link to="/" aria-label="Beranda PETA INKLUSI" data-testid="public-logo" className="min-w-0 shrink overflow-hidden">
            <BrandLogo className="h-8 w-8 sm:h-10 sm:w-10" withText />
          </Link>
          <nav className="ml-auto hidden flex-nowrap items-center gap-0.5 lg:flex xl:gap-1" aria-label="Navigasi publik">
            {NAV.map((n) => (
              <NavLink key={n.to} to={n.to} end={n.end}
                data-testid={`pubnav-${n.to.replace(/\W+/g, "-") || "home"}`}
                className={({ isActive }) => `inline-flex min-h-10 items-center whitespace-nowrap rounded-full px-2 py-2 text-xs font-semibold transition-colors xl:px-3.5 xl:text-sm ${FR} ${
                  isActive ? "bg-[#6FE3CF] text-[#232F3E] shadow-[0_6px_16px_rgba(111,227,207,.25)]" : "text-slate-200 hover:bg-white/10 hover:text-white"}`}>
                {n.label}
              </NavLink>
            ))}
          </nav>
          <button type="button" data-testid="public-login-btn"
            onClick={() => navigate(user ? "/dashboard" : "/login")}
            className={`ml-auto inline-flex min-h-11 shrink-0 items-center gap-1.5 whitespace-nowrap rounded-full bg-white px-2.5 py-2 text-xs font-bold text-[#232F3E] ring-1 ring-white/20 transition-colors hover:bg-[#E6FAF6] active:bg-[#D2F4EC] sm:gap-2 sm:px-4 sm:text-sm lg:ml-2 lg:px-3 lg:text-xs xl:ml-3 xl:px-4 xl:text-sm ${FR}`}>
            {user ? <LayoutDashboard className="h-4 w-4 shrink-0" aria-hidden="true" /> : <LogIn className="h-4 w-4 shrink-0" aria-hidden="true" />}
            <span className="max-[379px]:sr-only">{user ? "Dashboard" : "Masuk"}</span>
          </button>
          <button type="button" ref={toggleRef} className={`inline-flex h-11 w-11 shrink-0 items-center justify-center rounded-full bg-white/10 ring-1 ring-white/15 transition-colors hover:bg-white/20 lg:hidden ${FR}`} onClick={() => setOpen(!open)} aria-label={open ? "Tutup menu" : "Buka menu"}
            aria-expanded={open} aria-controls="public-mobile-nav" data-testid="public-menu-toggle">
            {open ? <X className="h-5 w-5" /> : <Menu className="h-5 w-5" />}
          </button>
        </div>
        {open && (
          <nav id="public-mobile-nav" ref={mobileNavRef} className="max-h-[calc(100dvh-4rem)] space-y-1 overflow-y-auto border-t border-white/10 px-4 pb-4 pt-2 lg:hidden" aria-label="Navigasi publik (seluler)">
            {NAV.map((n) => (
              <NavLink key={n.to} to={n.to} end={n.end} onClick={() => setOpen(false)}
                className={({ isActive }) => `flex min-h-11 items-center rounded-[12px] px-3 py-2 text-sm font-semibold transition-colors ${FR} ${isActive ? "bg-[#6FE3CF] text-[#232F3E]" : "text-slate-200 hover:bg-white/10"}`}>
                {n.label}
              </NavLink>
            ))}
          </nav>
        )}
      </header>
      <main id="konten" tabIndex={-1} className={fullBleed ? "relative flex-1 focus:outline-none" : "flex-1 focus:outline-none"}>
        <EasyReadAuto />
        {children}
      </main>
      <A11yAssistant />
      {!fullBleed && (
        <footer className="bg-[#1A2330] pb-[calc(4.5rem+env(safe-area-inset-bottom))] text-slate-300" data-testid="public-footer">
          <div className="mx-auto grid max-w-7xl gap-6 px-4 py-8 sm:grid-cols-2 md:grid-cols-3">
            <div>
              <BrandLogo className="h-12 w-12" withText />
              <p className="mt-3 text-sm text-slate-400">
                Platform data sosial terintegrasi untuk perencanaan program inklusif Kota Makassar:
                Disabilitas, Stunting, Anak Tidak Sekolah, dan Kemiskinan.
              </p>
            </div>
            <div>
              <h2 className="font-head text-sm font-bold uppercase tracking-wider text-[#6FE3CF]">Tautan</h2>
              <ul className="mt-2 space-y-1 text-sm">
                {NAV.slice(1).map((n) => <li key={n.to}><Link className={`inline-flex min-h-8 items-center rounded transition-colors hover:text-[#6FE3CF] ${FR}`} to={n.to}>{n.label}</Link></li>)}
              </ul>
            </div>
            <div>
              <h2 className="font-head text-sm font-bold uppercase tracking-wider text-[#6FE3CF]">Privasi Data</h2>
              <p className="mt-2 text-sm text-slate-400">
                Halaman publik hanya menampilkan data agregat per wilayah. NIK, nama, alamat, email, dan
                nomor telepon tidak pernah ditampilkan kepada publik.
              </p>
              <p className="mt-3 text-xs text-slate-400">© {new Date().getFullYear()} Bappeda Kota Makassar</p>
            </div>
          </div>
        </footer>
      )}
    </div>
  );
}
