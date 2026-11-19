import React, { useCallback, useEffect, useMemo, useRef, useState } from "react";
import { useLocation, useNavigate } from "react-router-dom";
import {
  Accessibility, Captions, ChevronsDown, Ear, Eye, FileText, Hand, Keyboard, Maximize2, Mic, MicOff, Minimize2,
  Pause, Play, Square, Volume2, X, Type, Contrast, Zap, Gauge, RotateCcw,
} from "lucide-react";
import { useA11y } from "@/context/AccessibilityContext";
import { halamanDariPath, usePublicA11yData } from "./data";
import { buatNarasi, teksHalamanPenuh, type Bagian, type Narasi } from "./narasi";
import { BTN_ICON_DARK, BTN_PRIMARY, BTN_SECONDARY, FR, KBD, SEG, segItem } from "./ui";

const SR: any = typeof window !== "undefined" ? (window as any).SpeechRecognition || (window as any).webkitSpeechRecognition : null;

const PINTASAN: [string, string][] = [
  ["Alt + B", "Bacakan seluruh halaman"],
  ["Alt + P", "Jeda / lanjutkan suara"],
  ["Alt + S", "Hentikan suara"],
  ["Alt + 1 … 9", "Lompat ke bagian 1–9 (Alt + Shift + angka bila Alt + angka dipakai browser)"],
  ["Alt + A", "Buka / tutup Asisten Aksesibilitas"],
  ["Alt + M", "Nyalakan / matikan perintah suara (mikrofon)"],
  ["Alt + T", "Subtitle (teks suara) nyala / mati"],
  ["Alt + E", "Mode Bahasa Mudah nyala / mati"],
  ["?", "Buka bantuan pintasan ini"],
  ["Esc", "Tutup jendela / bantuan"],
];
const PERINTAH: [string, string][] = [
  ["\"bacakan halaman\"", "Membacakan seluruh halaman"],
  ["\"bacakan stunting\" / \"bacakan kemiskinan\" …", "Membacakan bagian yang disebut"],
  ["\"jeda\" · \"lanjut\" · \"berhenti\"", "Mengatur suara"],
  ["\"buka beranda\" / \"buka dashboard\" / \"buka peta sosial\" / \"buka peta kemiskinan\"", "Pindah halaman"],
  ["\"perbesar teks\" · \"kontras\" · \"bahasa mudah\" · \"subtitle\" · \"bahasa isyarat\"", "Mengatur tampilan"],
  ["\"bantuan\"", "Membacakan daftar perintah"],
];

function teksElemen(el: HTMLElement | null): string {
  if (!el) return "";
  const a = el.getAttribute("aria-label") || el.getAttribute("data-speak") || el.getAttribute("alt") || el.getAttribute("title");
  if (a) return a;
  const lbl = el.id ? document.querySelector(`label[for="${el.id}"]`)?.textContent : "";
  const t = (el.innerText || el.textContent || "").replace(/\s+/g, " ").trim();
  const peran = el.tagName === "A" ? "Tautan" : el.tagName === "BUTTON" ? "Tombol" : el.tagName === "INPUT" ? "Kolom isian" : "";
  return [peran, lbl, t || (el as HTMLInputElement).placeholder].filter(Boolean).join(": ").slice(0, 300);
}

function Toggle({ on, onChange, icon: Ic, label, ket, testid, disabled }: any) {
  return (
    <button type="button" role="switch" aria-checked={on} onClick={() => onChange(!on)} disabled={disabled} data-testid={testid}
      className={`flex min-h-11 w-full items-center gap-3 rounded-[12px] bg-slate-50 px-3 py-3 text-left ring-1 ring-slate-200 transition-colors hover:bg-white disabled:cursor-not-allowed disabled:opacity-55 ${FR}`}>
      <span className={`grid h-9 w-9 shrink-0 place-items-center rounded-full ${on ? "bg-[#117A69] text-white" : "bg-white text-[#117A69] ring-1 ring-slate-200"}`} aria-hidden="true"><Ic className="h-[18px] w-[18px]" /></span>
      <span className="min-w-0 flex-1">
        <span className="block text-sm font-semibold text-slate-900">{label}</span>
        {ket && <span className="mt-0.5 block text-xs leading-5 text-slate-600">{ket}</span>}
      </span>
      <span aria-hidden="true" className={`inline-flex h-6 w-11 shrink-0 items-center rounded-full p-0.5 transition-colors ${on ? "bg-[#117A69]" : "bg-slate-300"}`}>
        <span className={`h-5 w-5 rounded-full bg-white shadow-sm ${on ? "translate-x-5" : ""}`} />
      </span>
    </button>
  );
}

function LinkRow({ icon: Ic, label, hint, onClick, testid, disabled }: any) {
  return (
    <button type="button" onClick={onClick} disabled={disabled} data-testid={testid}
      className={`flex min-h-11 w-full items-center gap-3 rounded-[12px] bg-white px-3 py-3 text-left ring-1 ring-slate-200 transition-colors hover:bg-slate-50 disabled:cursor-not-allowed disabled:opacity-55 ${FR}`}>
      <span className="grid h-9 w-9 shrink-0 place-items-center rounded-full bg-slate-100 text-[#117A69]" aria-hidden="true"><Ic className="h-[18px] w-[18px]" /></span>
      <span className="flex-1 text-sm font-semibold text-slate-900">{label}</span>
      {hint && <span className="text-xs font-semibold text-[#117A69]">{hint}</span>}
    </button>
  );
}

function Kartu({ judul, icon: Ic, children, aksi }: any) {
  return (
    <div className="rounded-[14px] bg-white p-3 shadow-[0_10px_24px_rgba(35,47,62,.08)] ring-1 ring-slate-200">
      <div className="mb-2.5 flex items-center justify-between gap-2">
        <p className="flex items-center gap-2 text-xs font-semibold uppercase tracking-wide text-slate-700"><Ic className="h-4 w-4 text-[#117A69]" aria-hidden="true" /> {judul}</p>
        {aksi}
      </div>
      {children}
    </div>
  );
}


export default function A11yAssistant() {
  const a = useA11y();
  const loc = useLocation();
  const nav = useNavigate();
  const halaman = halamanDariPath(loc.pathname);
  const { s, st, bisindo } = usePublicA11yData();
  const [buka, setBuka] = useState(false);
  const [bantuan, setBantuan] = useState(false);
  const [transkrip, setTranskrip] = useState(false);
  const [mic, setMic] = useState(false);
  const [dengar, setDengar] = useState("");
  const [vidBesar, setVidBesar] = useState(false);
  const [tab, setTab] = useState<"tampilan" | "netra" | "rungu">(halaman ? "netra" : "tampilan");
  const recRef = useRef<any>(null);
  const micRef = useRef(false);

  // Narasi: halaman terdaftar memakai data nyata; halaman lain memakai judul h2 dari konten.
  const narasi: Narasi | null = useMemo(() => {
    const nr = buatNarasi(halaman, s, st);
    if (nr) return nr;
    const main = typeof document !== "undefined" ? (document.getElementById("konten") || document.querySelector("main")) : null;
    if (!main) return null;
    const h = Array.from(main.querySelectorAll("h1, h2")).slice(0, 9) as HTMLElement[];
    return {
      judul: document.title, pembuka: `Anda berada di halaman ${h[0]?.innerText || document.title}.`, mudah: [],
      bagian: h.map((el, i) => {
        if (!el.id) el.id = `a11y-h-${i}`;
        const sec = (el.closest("section") as HTMLElement) || el.parentElement;
        return { id: el.id, label: el.innerText, teks: (sec?.innerText || el.innerText).replace(/\s+/g, " ").slice(0, 900), target: el.id, kata: [el.innerText.toLowerCase()] };
      }),
    };
    // eslint-disable-next-line react-hooks/exhaustive-deps
  }, [halaman, s, st, loc.pathname, buka]);

  const video = halaman ? bisindo?.videos?.[halaman] : null;

  const bacaHalaman = useCallback(() => { if (narasi) { a.speak(teksHalamanPenuh(narasi), undefined, "halaman"); a.announce("Membacakan seluruh halaman"); } }, [a, narasi]);
  const bacaBagian = useCallback((b: Bagian) => a.speak(`${b.label}. ${b.teks}`, undefined, `bagian:${b.id}`), [a]);
  const lompat = useCallback((b: Bagian) => {
    const el = document.getElementById(b.target) || document.getElementById(b.id);
    if (el) {
      if (!el.hasAttribute("tabindex")) el.setAttribute("tabindex", "-1");
      el.scrollIntoView({ behavior: a.reduceMotion ? "auto" : "smooth", block: "start" });
      (el as HTMLElement).focus({ preventScroll: true });
    }
    a.announce(`Bagian: ${b.label}`);
  }, [a]);
  const togglePlay = useCallback(() => {
    if (a.status === "playing") a.pause();
    else if (a.status === "paused") a.resume();
    else bacaHalaman();
  }, [a, bacaHalaman]);

  // ---------------------------------------------------------------- Perintah suara (fitur E)
  const jalankanPerintah = useCallback((raw: string) => {
    const t = raw.toLowerCase().replace(/[.,!?]/g, "").trim();
    const ada = (...k: string[]) => k.some((x) => t.includes(x));
    if (ada("berhenti", "stop", "diam")) { a.stop(); a.announce("Suara dihentikan"); return; }
    if (a.status === "playing") return; // abaikan suara sendiri saat membacakan
    if (ada("jeda")) { a.pause(); return; }
    if (ada("lanjut")) { a.resume(); return; }
    if (ada("bantuan", "tolong")) { setBantuan(true); a.speak("Perintah yang tersedia: " + PERINTAH.map(([p, k]) => `${p.replace(/"/g, "")}, ${k}`).join(". "), undefined, "bantuan"); return; }
    const rute: [string[], string][] = [[["peta sosial"], "/publik/peta-sosial"], [["peta kemiskinan"], "/publik/peta-kemiskinan"],
      [["dashboard", "informasi umum"], "/publik"], [["beranda", "halaman utama"], "/"]];
    if (ada("buka", "pergi", "pindah", "ke ")) {
      for (const [k, to] of rute) if (k.some((x) => t.includes(x))) { nav(to); a.announce(`Membuka ${k[0]}`); return; }
    }
    if (ada("perbesar", "besarkan")) { a.setTextSize(a.textSize === "normal" ? "large" : "xlarge"); a.announce("Teks diperbesar"); return; }
    if (ada("perkecil", "teks normal")) { a.setTextSize("normal"); a.announce("Ukuran teks normal"); return; }
    if (ada("kontras")) { a.setContrast(!a.contrast); a.announce(a.contrast ? "Kontras tinggi dimatikan" : "Kontras tinggi dinyalakan"); return; }
    if (ada("bahasa mudah")) { a.setEasyMode(!a.easyMode); a.announce("Mode bahasa mudah diubah"); return; }
    if (ada("subtitle", "teks suara")) { a.setCaptionsOn(!a.captionsOn); a.announce("Subtitle diubah"); return; }
    if (ada("isyarat", "bisindo")) { a.setBisindoOn(!a.bisindoOn); a.announce("Video bahasa isyarat diubah"); return; }
    if (narasi) {
      if (ada("bacakan halaman", "bacakan semua", "baca semua", "baca halaman")) { bacaHalaman(); return; }
      const cocok = narasi.bagian.find((b) => b.kata.some((k) => t.includes(k)) || t.includes(b.label.toLowerCase()));
      if (cocok) { if (ada("lompat", "ke bagian")) lompat(cocok); else { lompat(cocok); bacaBagian(cocok); } return; }
      if (ada("bacakan", "baca")) { bacaHalaman(); return; }
    }
    a.speak(`Maaf, perintah "${raw}" tidak dikenali. Ucapkan bantuan untuk daftar perintah.`, undefined, "perintah");
  }, [a, nav, narasi, bacaHalaman, bacaBagian, lompat]);
  const perintahRef = useRef(jalankanPerintah);
  perintahRef.current = jalankanPerintah;

  const setMicOn = useCallback((on: boolean) => {
    if (!SR) { a.announce("Perintah suara tidak didukung browser ini. Gunakan Chrome atau Edge."); return; }
    micRef.current = on;
    setMic(on);
    if (!on) { try { recRef.current?.stop(); } catch { /* noop */ } setDengar(""); a.announce("Perintah suara dimatikan"); return; }
    const rec = new SR();
    rec.lang = "id-ID";
    rec.continuous = true;
    rec.interimResults = true;
    rec.onresult = (e: any) => {
      for (let i = e.resultIndex; i < e.results.length; i += 1) {
        const txt = e.results[i][0].transcript;
        setDengar(txt);
        if (e.results[i].isFinal) perintahRef.current(txt);
      }
    };
    rec.onerror = (e: any) => {
      if (e.error === "not-allowed" || e.error === "service-not-allowed") {
        micRef.current = false; setMic(false);
        a.announce("Izin mikrofon ditolak. Izinkan mikrofon di pengaturan browser.");
      }
    };
    rec.onend = () => { if (micRef.current) { try { rec.start(); } catch { /* noop */ } } };
    recRef.current = rec;
    try { rec.start(); a.announce("Perintah suara aktif. Ucapkan bantuan untuk daftar perintah."); } catch { /* noop */ }
  }, [a]);
  useEffect(() => () => { micRef.current = false; try { recRef.current?.stop(); } catch { /* noop */ } }, []);

  // ---------------------------------------------------------------- Pintasan keyboard (fitur D)
  useEffect(() => {
    const onKey = (e: KeyboardEvent) => {
      const tg = e.target as HTMLElement;
      const ketik = tg && (tg.tagName === "INPUT" || tg.tagName === "TEXTAREA" || tg.tagName === "SELECT" || tg.isContentEditable);
      if (e.key === "Escape") { setBantuan(false); setTranskrip(false); return; }
      if (!ketik && !e.altKey && !e.ctrlKey && !e.metaKey && e.key === "?") { e.preventDefault(); setBantuan(true); return; }
      if (!e.altKey || e.ctrlKey || e.metaKey) return;
      const c = e.code;
      const aksi: Record<string, () => void> = {
        KeyB: bacaHalaman, KeyS: () => a.stop(), KeyP: togglePlay, KeyA: () => setBuka((x) => !x),
        KeyM: () => setMicOn(!micRef.current), KeyT: () => a.setCaptionsOn(!a.captionsOn), KeyE: () => a.setEasyMode(!a.easyMode),
      };
      if (aksi[c]) { e.preventDefault(); aksi[c](); return; }
      const m = /^Digit([1-9])$/.exec(c);
      if (m && narasi?.bagian[Number(m[1]) - 1]) { e.preventDefault(); const b = narasi.bagian[Number(m[1]) - 1]; lompat(b); if (a.autoRead) bacaBagian(b); }
    };
    window.addEventListener("keydown", onKey);
    return () => window.removeEventListener("keydown", onKey);
  }, [a, narasi, bacaHalaman, togglePlay, setMicOn, lompat, bacaBagian]);

  // ---------------------------------------------------------------- Bacakan saat disorot (fitur F)
  useEffect(() => {
    if (!a.autoRead) return undefined;
    let t: any;
    const onFocus = (e: FocusEvent) => {
      const el = e.target as HTMLElement;
      if (!el || el === document.body || el.closest("[data-a11y-no-read]")) return;
      clearTimeout(t);
      t = setTimeout(() => a.speakQuick(teksElemen(el)), 220);
    };
    document.addEventListener("focusin", onFocus);
    return () => { clearTimeout(t); document.removeEventListener("focusin", onFocus); };
  }, [a, a.autoRead]);

  // Umumkan halaman baru untuk pembaca layar
  const judulHalaman = narasi?.judul;
  const announce = a.announce;
  useEffect(() => { if (judulHalaman) announce(`Halaman ${judulHalaman}`); }, [halaman, judulHalaman, announce]);

  const statusTeks = a.status === "loading" ? "Menyiapkan suara…" : a.status === "playing" ? `Membacakan${a.progress.n > 1 ? ` (bagian ${a.progress.i} dari ${a.progress.n})` : ""}…`
    : a.status === "paused" ? "Dijeda" : "Siap";

  return (
    <>
      {/* ---------------- Tombol melayang (ikon saja agar ringkas, Alt+A tetap aktif) */}
      <button type="button" onClick={() => setBuka(!buka)} aria-expanded={buka} aria-controls="a11y-panel" data-testid="a11y-assistant-btn"
        title="Asisten Aksesibilitas (Alt + A)"
        aria-label="Asisten Aksesibilitas: pengaturan tampilan, bantuan suara untuk disabilitas buta, dan subtitle untuk disabilitas tuli (Alt + A)" data-a11y-no-read
        className={`fixed bottom-[max(1rem,env(safe-area-inset-bottom))] right-[max(1rem,env(safe-area-inset-right))] z-[900] grid h-12 w-12 place-items-center rounded-2xl shadow-[0_10px_30px_rgba(35,47,62,0.18)] ring-1 transition-all ${buka ? "bg-[#117A69] text-white ring-[#0E6456]" : "bg-white text-[#117A69] ring-slate-200 hover:bg-[#E6FAF6] hover:ring-[#117A69]/35"} ${FR}`}>
        <span className="relative grid place-items-center" aria-hidden="true">
          {buka ? <X className="h-5 w-5" /> : <Accessibility className="h-6 w-6" />}
          {a.status !== "idle" && <span className={`absolute -right-2 -top-2 h-2.5 w-2.5 rounded-full bg-[#F4B63A] ring-2 ${buka ? "ring-[#117A69]" : "ring-white"}`} />}
        </span>
      </button>

      {/* ---------------- Panel */}
      {buka && (
        <div id="a11y-panel" role="dialog" aria-label="Asisten Aksesibilitas" data-testid="a11y-panel"
          className="fixed bottom-[4.75rem] right-4 z-[900] flex max-h-[min(80vh,740px)] w-[min(420px,calc(100vw-2rem))] flex-col overflow-hidden rounded-[16px] bg-white text-slate-900 shadow-[0_18px_60px_rgba(35,47,62,.22)] ring-1 ring-slate-200">
          <div className="bg-[#232F3E] px-4 pb-3 pt-4 text-white">
            <div className="flex items-start justify-between gap-3">
              <div className="flex items-start gap-3">
                <span className="grid h-10 w-10 shrink-0 place-items-center rounded-[12px] bg-white/10 ring-1 ring-white/15" aria-hidden="true"><Accessibility className="h-5 w-5 text-[#6FE3CF]" /></span>
                <div>
                  <h2 className="font-head text-base font-bold leading-6">Asisten Aksesibilitas</h2>
                  <p className="mt-0.5 text-xs leading-5 text-white/75">Atur tampilan, dengarkan isi halaman, atau baca subtitle.</p>
                </div>
              </div>
              <button type="button" onClick={() => setBuka(false)} aria-label="Tutup asisten" data-testid="a11y-panel-close"
                className={`inline-flex h-10 w-10 shrink-0 items-center justify-center rounded-full bg-white/10 ring-1 ring-white/15 transition-colors hover:bg-white/15 ${FR}`}><X className="h-5 w-5" /></button>
            </div>
          </div>
          <div className="border-b border-slate-100 bg-white px-4 pb-3 pt-3">
            <div role="tablist" aria-label="Kategori aksesibilitas" className={`${SEG} grid-cols-3 items-stretch`}>
              {([["tampilan", "Tampilan", Type], ["netra", "Disabilitas Buta", Eye], ["rungu", "Disabilitas Tuli", Ear]] as const).map(([id, lbl, Ic]) => (
                <button key={id} type="button" role="tab" aria-selected={tab === id} aria-controls={`a11y-tab-${id}`} id={`a11y-tabbtn-${id}`}
                  onClick={() => setTab(id)} data-testid={`a11y-tab-${id}`}
                  className={`inline-flex min-h-12 flex-col items-center justify-center gap-1 rounded-[12px] px-1.5 py-1.5 text-center text-[11px] font-semibold leading-[1.2] transition-colors ${FR} ${tab === id ? "bg-white text-slate-900 shadow-sm ring-1 ring-slate-200" : "text-slate-600 hover:text-slate-900"}`}>
                  <Ic className={`h-4 w-4 shrink-0 ${tab === id ? "text-[#117A69]" : ""}`} aria-hidden="true" />
                  <span className="text-balance">{lbl}</span>
                </button>
              ))}
            </div>
          </div>

          <div className="flex-1 overflow-y-auto bg-slate-50/60 p-4">
            {/* Peringatan suara tampil di semua tab: aksi "Bacakan" ada di tab
                Disabilitas Buta, jadi pesan tidak boleh tersembunyi di tab Tampilan. */}
            {(a.suaraTerblokir || a.masalahSuara) && (
              <div role="alert" data-testid="a11y-voice-alert" className="mb-3 rounded-[12px] bg-[#FFF4DF] p-3 text-xs leading-5 text-[#6B4A00] ring-1 ring-[#F4B63A]">
                <p className="font-semibold">Suara belum berbunyi.</p>
                <p className="mt-0.5">
                  {a.suaraTerblokir === "not-allowed"
                    ? "Perangkat memblokir pemutaran otomatis. Ketuk tombol di bawah ini sekali lagi."
                    : a.masalahSuara === "language-unavailable" || a.masalahSuara === "voice-unavailable"
                      ? "Bahasa Indonesia belum tersedia di mesin suara perangkat. Pasang data suara Bahasa Indonesia pada pengaturan perangkat."
                      : "Pastikan volume perangkat menyala dan tidak dalam mode senyap, lalu coba lagi."}
                </p>
                <button type="button" onClick={a.ulangiSuara} data-testid="a11y-voice-retry"
                  className={`mt-2 inline-flex min-h-9 items-center gap-1.5 rounded-full bg-white px-3 text-xs font-semibold text-[#6B4A00] ring-1 ring-[#F4B63A] transition-colors hover:bg-[#FFF9EE] ${FR}`}>
                  <Play className="h-3.5 w-3.5" aria-hidden="true" /> Coba bacakan lagi
                </button>
              </div>
            )}
            {tab === "tampilan" && (
              <div id="a11y-tab-tampilan" role="tabpanel" aria-labelledby="a11y-tabbtn-tampilan" className="space-y-3">
                <Kartu judul="Ukuran teks" icon={Type}>
                  <div className="grid grid-cols-3 gap-2" role="group" aria-label="Ukuran teks">
                    {([["normal", "Normal", "text-sm"], ["large", "Besar", "text-lg"], ["xlarge", "Sangat besar", "text-2xl"]] as const).map(([v, l, cls]) => (
                      <button key={v} type="button" aria-pressed={a.textSize === v} onClick={() => a.setTextSize(v)} data-testid={`a11y-text-${v}`}
                        className={`flex min-h-[64px] flex-col items-center justify-center gap-1 rounded-[12px] bg-white px-2 py-2.5 transition-colors ${FR} ${a.textSize === v ? "text-[#0B4F45] ring-2 ring-[#117A69]" : "text-slate-700 ring-1 ring-slate-200 hover:ring-slate-300"}`}>
                        <span className={`font-head font-bold leading-none ${cls}`} aria-hidden="true">Aa</span>
                        <span className="text-[11px] font-semibold">{l}</span>
                      </button>
                    ))}
                  </div>
                </Kartu>
                <div className="grid grid-cols-2 gap-2">
                  {([[a.contrast, a.setContrast, Contrast, "Kontras tinggi", "Warna lebih tegas", "a11y-contrast"],
                    [a.reduceMotion, a.setReduceMotion, Zap, "Kurangi animasi", "Gerakan diminimalkan", "a11y-motion"]] as const).map(([on, set, Ic, l, k, tid]) => (
                    <button key={tid} type="button" role="switch" aria-checked={on} onClick={() => (set as any)(!on)} data-testid={tid}
                      className={`flex flex-col items-start gap-2.5 rounded-[14px] p-3 text-left transition-colors ${FR} ${on ? "bg-white ring-2 ring-[#117A69]" : "bg-white ring-1 ring-slate-200 hover:ring-slate-300"}`}>
                      <span className="flex w-full items-start justify-between gap-2">
                        <span className={`grid h-9 w-9 place-items-center rounded-full ${on ? "bg-[#117A69] text-white" : "bg-slate-100 text-[#117A69]"}`} aria-hidden="true"><Ic className="h-[18px] w-[18px]" /></span>
                        <span className={`inline-flex items-center rounded-full px-2 py-0.5 text-[11px] font-semibold ring-1 ${on ? "bg-[#117A69]/10 text-[#0B4F45] ring-[#117A69]/20" : "bg-slate-200/70 text-slate-700 ring-slate-300"}`}>{on ? "AKTIF" : "MATI"}</span>
                      </span>
                      <span><span className="block text-sm font-semibold text-slate-900">{l}</span><span className="mt-0.5 block text-xs leading-5 text-slate-600">{k}</span></span>
                    </button>
                  ))}
                </div>
                <Kartu judul="Kecepatan suara" icon={Gauge}
                  aksi={<button type="button" onClick={() => a.speak("Halo, ini contoh suara asisten aksesibilitas PETA INKLUSI.", undefined, "contoh")} data-testid="a11y-try-voice"
                    className={`inline-flex items-center gap-1 rounded text-xs font-semibold text-[#117A69] underline underline-offset-4 hover:text-[#0B4F45] ${FR}`}><Volume2 className="h-3.5 w-3.5" aria-hidden="true" /> Coba suara</button>}>
                  <div className={`${SEG} grid-cols-3`} role="group" aria-label="Kecepatan suara">
                    {([["normal", "Normal"], ["slow", "Pelan"], ["slower", "Sangat pelan"]] as const).map(([v, l]) => (
                      <button key={v} type="button" aria-pressed={a.speechRate === v} onClick={() => a.setSpeechRate(v)} data-testid={`a11y-rate-${v}`} className={segItem(a.speechRate === v)}>{l}</button>
                    ))}
                  </div>
                  <p className="mt-2 text-xs leading-5 text-slate-600" data-testid="a11y-rate-hint">
                    {a.speechRate === "normal" ? "Tempo bicara biasa (disarankan). Suara dibuat jernih dengan lafal Bahasa Indonesia yang jelas." : a.speechRate === "slow" ? "Sedikit lebih pelan dari tempo normal." : "Pelan dengan jeda lebih panjang antar kalimat."}
                  </p>
                  <p className="mt-2 border-t border-slate-200 pt-2 text-xs leading-5 text-slate-600" data-testid="a11y-voice-info">
                    {!a.suara?.didukung
                      ? "Browser ini tidak mendukung suara. Isi halaman tetap bisa dibaca lewat subtitle."
                      : a.suara.indonesia
                        ? <>Suara perangkat: <b className="text-slate-800">{a.suara.nama}</b> ({a.suara.lang})</>
                        : <>Perangkat ini belum punya suara Bahasa Indonesia. Pasang di Pengaturan → Bahasa & masukan → Output teks-ke-ucapan, lalu muat ulang halaman.</>}
                  </p>
                </Kartu>
                <button type="button" data-testid="a11y-reset"
                  onClick={() => { a.setTextSize("normal"); a.setContrast(false); a.setReduceMotion(false); a.setSpeechRate("normal"); a.announce("Pengaturan tampilan dikembalikan"); }}
                  className={`inline-flex min-h-11 w-full items-center justify-center gap-2 rounded-[12px] bg-white px-4 py-3 text-sm font-semibold text-slate-900 ring-1 ring-slate-200 transition-colors hover:bg-slate-50 ${FR}`}>
                  <RotateCcw className="h-4 w-4" aria-hidden="true" /> Kembalikan pengaturan awal
                </button>
              </div>
            )}

            {tab === "netra" && (
              <div id="a11y-tab-netra" role="tabpanel" aria-labelledby="a11y-tabbtn-netra" className="space-y-3">
                <Kartu judul="Bacakan halaman" icon={Volume2}>
                  <div className="grid grid-cols-[1fr_auto] gap-2">
                    <button type="button" onClick={togglePlay} disabled={!narasi} data-testid="a11y-read-page"
                      className={`inline-flex min-h-11 items-center justify-center gap-2 rounded-[12px] bg-[#117A69] px-4 py-3 text-sm font-semibold text-white shadow-[0_12px_30px_rgba(17,122,105,.22)] transition-colors hover:bg-[#0B4F45] disabled:opacity-50 ${FR}`}>
                      {a.status === "playing" ? <Pause className="h-4 w-4" /> : <Play className="h-4 w-4" />}
                      {a.status === "playing" ? "Jeda" : a.status === "paused" ? "Lanjutkan" : "Bacakan Halaman"}
                    </button>
                    <button type="button" onClick={() => a.stop()} disabled={a.status === "idle"} data-testid="a11y-stop"
                      className={`inline-flex min-h-11 items-center justify-center gap-2 rounded-[12px] bg-white px-4 py-3 text-sm font-semibold text-slate-900 ring-1 ring-slate-200 transition-colors hover:bg-slate-50 disabled:opacity-40 ${FR}`}><Square className="h-4 w-4" /> Berhenti</button>
                  </div>
                  <p className="mt-2.5 flex items-center gap-2 text-xs text-slate-700" data-testid="a11y-status">
                    <span className={`h-2.5 w-2.5 rounded-full ${a.status === "idle" ? "bg-slate-300" : a.status === "paused" ? "bg-[#F4B63A]" : "bg-[#117A69] ring-2 ring-[#6FE3CF]/40"}`} aria-hidden="true" />
                    Status: <b>{statusTeks}</b></p>
                </Kartu>
                {narasi && narasi.bagian.length > 0 && (
                  <Kartu judul={`Bagian halaman (${narasi.bagian.length})`} icon={ChevronsDown}>
                    <ol className="space-y-1.5" aria-label="Bagian halaman">
                      {narasi.bagian.map((b, i) => (
                        <li key={b.id} className="flex items-center gap-2 rounded-[12px] bg-white py-1 pl-2 pr-1 ring-1 ring-slate-200 transition-colors hover:ring-slate-300" data-testid="a11y-section-item">
                          <span className="inline-flex min-w-[2.75rem] items-center justify-center rounded-full bg-slate-100 px-2 py-0.5 font-mono text-[11px] font-semibold text-slate-700 ring-1 ring-slate-200" aria-hidden="true">Alt+{i + 1}</span>
                          <button type="button" onClick={() => lompat(b)} className={`min-h-9 min-w-0 flex-1 truncate rounded text-left text-sm font-semibold text-slate-900 hover:text-[#117A69] ${FR}`} data-testid={`a11y-jump-${i + 1}`}
                            aria-label={`Lompat ke bagian ${i + 1}: ${b.label}`}>{b.label}</button>
                          <button type="button" onClick={() => bacaBagian(b)} aria-label={`Bacakan bagian ${b.label}`} data-testid={`a11y-read-${i + 1}`}
                            className={`inline-flex h-10 w-10 shrink-0 items-center justify-center rounded-full bg-white text-[#117A69] ring-1 ring-slate-200 transition-colors hover:bg-slate-50 hover:text-[#0B4F45] ${FR}`}><Volume2 className="h-4 w-4" /></button>
                        </li>
                      ))}
                    </ol>
                  </Kartu>
                )}
                <div className="space-y-2">
                  <Toggle on={a.autoRead} onChange={a.setAutoRead} icon={ChevronsDown} label="Bacakan saat disorot" ket="Teks dibacakan otomatis saat berpindah dengan tombol Tab" testid="a11y-toggle-focusread" />
                  <Toggle on={mic} onChange={setMicOn} icon={mic ? Mic : MicOff} label="Perintah suara (mikrofon)" testid="a11y-toggle-voice" disabled={!SR}
                    ket={SR ? "Ucapkan mis. \"bacakan stunting\", \"buka peta\", \"berhenti\"" : "Tidak didukung di browser ini — gunakan Chrome atau Edge"} />
                  <LinkRow icon={Keyboard} label="Pintasan keyboard & perintah suara" hint="Tekan ?" onClick={() => setBantuan(true)} testid="a11y-open-help" />
                </div>
              </div>
            )}

            {tab === "rungu" && (
              <div id="a11y-tab-rungu" role="tabpanel" aria-labelledby="a11y-tabbtn-rungu" className="space-y-2">
                <Toggle on={a.captionsOn} onChange={a.setCaptionsOn} icon={Captions} label="Subtitle (teks suara)" ket="Semua suara yang diputar ditampilkan sebagai tulisan" testid="a11y-toggle-captions" />
                {halaman && <Toggle on={a.easyMode} onChange={a.setEasyMode} icon={FileText} label="Bahasa Mudah" ket="Kalimat pendek dengan ikon besar di atas halaman" testid="a11y-toggle-easy" />}
                {halaman && <Toggle on={a.bisindoOn && !!video} onChange={a.setBisindoOn} icon={Hand} label="Video Juru Bahasa Isyarat (BISINDO)" testid="a11y-toggle-bisindo" disabled={!video}
                  ket={video ? "Jendela video melayang di kiri bawah" : "Video BISINDO untuk halaman ini belum tersedia"} />}
                <LinkRow icon={FileText} label="Transkrip suara terakhir" hint={a.transcript ? "Buka" : ""} onClick={() => setTranskrip(true)} disabled={!a.transcript} testid="a11y-open-transcript" />
                <div className="mt-1 rounded-[12px] bg-slate-900 px-3 py-3 text-sm leading-6 text-white shadow-[0_12px_30px_rgba(35,47,62,.18)]">
                  <p className="flex items-center gap-1.5 text-xs text-white/70"><Captions className="h-4 w-4" aria-hidden="true" /> Contoh tampilan subtitle</p>
                  <p className="mt-1 font-medium">Setiap suara akan tampil sebagai tulisan seperti ini.</p>
                  <button type="button" onClick={() => a.speak("Ini contoh subtitle. Setiap suara yang diputar akan muncul sebagai tulisan di bagian bawah layar.", undefined, "contoh")} data-testid="a11y-try-caption"
                    className={`mt-2 inline-flex min-h-9 items-center gap-1.5 rounded-full bg-white/10 px-3 text-xs font-semibold ring-1 ring-white/15 transition-colors hover:bg-white/15 ${FR}`}><Play className="h-3.5 w-3.5" aria-hidden="true" /> Tampilkan contoh subtitle</button>
                </div>
              </div>
            )}
          </div>
          <div className="flex flex-wrap items-center gap-x-2 gap-y-1.5 border-t border-slate-200 bg-slate-50 px-4 py-2.5 text-xs text-slate-600" data-testid="a11y-panel-footer">
            <kbd className={KBD}>Alt + A</kbd> buka/tutup
            <span className="text-slate-300" aria-hidden="true">•</span>
            <kbd className={KBD}>?</kbd> bantuan
            <span className="text-slate-300" aria-hidden="true">•</span>
            <kbd className={KBD}>Esc</kbd> tutup jendela
          </div>
        </div>
      )}

      {/* ---------------- Subtitle (fitur G) — visual; pembaca layar sudah mendengar suaranya */}
      {a.captionsOn && (a.caption || (mic && dengar)) && (
        <div className="pointer-events-none fixed bottom-[4.75rem] left-1/2 z-[890] w-[min(720px,calc(100vw-2rem))] -translate-x-1/2" aria-hidden="true" data-testid="a11y-caption-bar">
          {a.caption && a.status !== "idle" && (
            <div className="rounded-[14px] bg-slate-950/95 px-5 py-3 text-white shadow-[0_18px_60px_rgba(0,0,0,.35)] ring-1 ring-white/10">
              <span className="mb-1 flex items-center gap-1.5 text-[11px] font-semibold uppercase tracking-wider text-[#6FE3CF]">
                <Captions className="h-3.5 w-3.5" /> {a.status === "loading" ? "Menyiapkan suara" : a.status === "paused" ? "Dijeda" : "Sedang dibacakan"}
              </span>
              <span className="block text-base font-semibold leading-7 sm:text-lg" data-testid="a11y-caption-text">{a.caption}</span>
            </div>
          )}
          {mic && dengar && (
            <div className="mt-2 rounded-[12px] bg-[#232F3E] px-4 py-2 text-center text-sm font-semibold text-white ring-1 ring-white/10" data-testid="a11y-heard">
              <Mic className="mr-1 inline h-4 w-4 text-[#6FE3CF]" /> Anda: “{dengar}”
            </div>
          )}
        </div>
      )}

      {/* ---------------- Jendela BISINDO (fitur I) */}
      {video && a.bisindoOn && (
        <aside aria-label="Video juru bahasa isyarat BISINDO" data-testid="a11y-bisindo-window"
          className={`fixed bottom-4 left-4 z-[880] overflow-hidden rounded-[16px] bg-white shadow-[0_18px_60px_rgba(35,47,62,.22)] ring-1 ring-slate-200 ${vidBesar ? "w-[min(560px,calc(100vw-2rem))]" : "w-[min(360px,calc(100vw-2rem))]"}`}>
          <div className="flex items-center justify-between gap-2 bg-[#232F3E] px-3 py-2 text-white">
            <span className="flex min-w-0 items-center gap-2 text-sm font-semibold"><Hand className="h-4 w-4 shrink-0 text-[#6FE3CF]" aria-hidden="true" /> <span className="truncate">{video.judul || "Juru Bahasa Isyarat (BISINDO)"}</span></span>
            <span className="flex shrink-0 items-center gap-1">
              <button type="button" onClick={() => setVidBesar(!vidBesar)} aria-label={vidBesar ? "Perkecil video" : "Perbesar video"} data-testid="a11y-bisindo-size"
                className={`inline-flex h-9 w-9 items-center justify-center rounded-full bg-white/10 ring-1 ring-white/15 transition-colors hover:bg-white/15 ${FR}`}>
                {vidBesar ? <Minimize2 className="h-4 w-4" /> : <Maximize2 className="h-4 w-4" />}</button>
              <button type="button" onClick={() => a.setBisindoOn(false)} aria-label="Tutup video bahasa isyarat" data-testid="a11y-bisindo-close"
                className={`inline-flex h-9 w-9 items-center justify-center rounded-full bg-white/10 ring-1 ring-white/15 transition-colors hover:bg-white/15 ${FR}`}><X className="h-4 w-4" /></button>
            </span>
          </div>
          <div className="aspect-video bg-black">
            {video.jenis === "video"
              ? <video src={video.embed} controls className="h-full w-full" title="Video bahasa isyarat" />
              : <iframe src={video.embed} title={video.judul || "Video juru bahasa isyarat BISINDO"} className="h-full w-full" allow="encrypted-media; picture-in-picture; fullscreen" />}
          </div>
        </aside>
      )}

      {/* ---------------- Bantuan pintasan (fitur D) */}
      {bantuan && (
        <div className="fixed inset-0 z-[960] flex items-center justify-center bg-[#0F172A]/60 p-4 backdrop-blur-sm" onMouseDown={(e) => { if (e.target === e.currentTarget) setBantuan(false); }}>
          <div role="dialog" aria-modal="true" aria-labelledby="a11y-help-title" className="flex max-h-[85vh] w-full max-w-2xl flex-col overflow-hidden rounded-[18px] bg-white shadow-[0_24px_70px_rgba(15,23,42,.35)] ring-1 ring-slate-200" data-testid="a11y-help-dialog">
            <div className="flex items-start justify-between gap-3 bg-[#232F3E] px-5 py-4 text-white">
              <div className="flex items-start gap-3">
                <span className="grid h-10 w-10 shrink-0 place-items-center rounded-[12px] bg-white/10 ring-1 ring-white/15" aria-hidden="true"><Keyboard className="h-5 w-5 text-[#6FE3CF]" /></span>
                <div>
                  <h2 id="a11y-help-title" className="font-head text-lg font-bold leading-6">Pintasan keyboard & perintah suara</h2>
                  <p className="mt-0.5 text-xs text-white/75">Gunakan tanpa mouse — semua fitur dapat diakses dari keyboard atau suara.</p>
                </div>
              </div>
              <button type="button" autoFocus onClick={() => setBantuan(false)} aria-label="Tutup bantuan" className={BTN_ICON_DARK} data-testid="a11y-help-close"><X className="h-5 w-5" /></button>
            </div>
            <div className="flex-1 overflow-y-auto bg-slate-50/60 p-5">
              <h3 className="flex items-center gap-2 text-xs font-semibold uppercase tracking-wider text-slate-600"><Keyboard className="h-4 w-4 text-[#117A69]" aria-hidden="true" /> Pintasan keyboard</h3>
              <div className="mt-2 overflow-hidden rounded-[14px] bg-white ring-1 ring-slate-200">
                <table className="w-full text-sm"><caption className="sr-only">Pintasan keyboard</caption>
                  <tbody>{PINTASAN.map(([k, d], i) => <tr key={k} className={i ? "border-t border-slate-100" : ""}><th scope="row" className="w-36 whitespace-nowrap px-4 py-2.5 text-left align-top"><kbd className={KBD}>{k}</kbd></th><td className="px-4 py-2.5 text-slate-700">{d}</td></tr>)}</tbody></table>
              </div>
              <h3 className="mt-5 flex items-center gap-2 text-xs font-semibold uppercase tracking-wider text-slate-600"><Mic className="h-4 w-4 text-[#117A69]" aria-hidden="true" /> Perintah suara {SR ? "" : "(tidak didukung di browser ini)"}</h3>
              <div className="mt-2 overflow-hidden rounded-[14px] bg-white ring-1 ring-slate-200">
                <table className="w-full text-sm"><caption className="sr-only">Perintah suara</caption>
                  <tbody>{PERINTAH.map(([k, d], i) => <tr key={k} className={i ? "border-t border-slate-100" : ""}><th scope="row" className="px-4 py-2.5 text-left align-top font-semibold text-slate-900">{k}</th><td className="px-4 py-2.5 text-slate-700">{d}</td></tr>)}</tbody></table>
              </div>
            </div>
            <div className="flex flex-wrap items-center justify-end gap-2 border-t border-slate-200 bg-white px-5 py-3">
              <button type="button" onClick={() => setBantuan(false)} className={BTN_SECONDARY} data-testid="a11y-help-done">Tutup</button>
              <button type="button" onClick={() => a.speak("Pintasan keyboard. " + PINTASAN.map(([k, d]) => `${k.replace(/\+/g, "plus").replace("…", "sampai")}: ${d}`).join(". ") + ". Perintah suara. " + PERINTAH.map(([k, d]) => `${k.replace(/"/g, "")}: ${d}`).join(". "), undefined, "bantuan")}
                className={BTN_PRIMARY} data-testid="a11y-help-speak"><Volume2 className="h-4 w-4" aria-hidden="true" /> Bacakan bantuan</button>
            </div>
          </div>
        </div>
      )}

      {/* ---------------- Transkrip (fitur G) */}
      {transkrip && (
        <div className="fixed inset-0 z-[960] flex items-center justify-center bg-[#0F172A]/60 p-4 backdrop-blur-sm" onMouseDown={(e) => { if (e.target === e.currentTarget) setTranskrip(false); }}>
          <div role="dialog" aria-modal="true" aria-labelledby="a11y-tr-title" className="flex max-h-[85vh] w-full max-w-2xl flex-col overflow-hidden rounded-[18px] bg-white shadow-[0_24px_70px_rgba(15,23,42,.35)] ring-1 ring-slate-200" data-testid="a11y-transcript-dialog">
            <div className="flex items-start justify-between gap-3 bg-[#232F3E] px-5 py-4 text-white">
              <div className="flex items-start gap-3">
                <span className="grid h-10 w-10 shrink-0 place-items-center rounded-[12px] bg-white/10 ring-1 ring-white/15" aria-hidden="true"><FileText className="h-5 w-5 text-[#6FE3CF]" /></span>
                <div>
                  <h2 id="a11y-tr-title" className="font-head text-lg font-bold leading-6">Transkrip suara</h2>
                  <p className="mt-0.5 text-xs text-white/75">Teks lengkap dari suara terakhir yang diputar.</p>
                </div>
              </div>
              <button type="button" autoFocus onClick={() => setTranskrip(false)} aria-label="Tutup transkrip" className={BTN_ICON_DARK} data-testid="a11y-transcript-close"><X className="h-5 w-5" /></button>
            </div>
            <div className="flex-1 overflow-y-auto p-5">
              <p className="whitespace-pre-line rounded-[14px] bg-slate-50 p-4 text-base leading-relaxed text-slate-800 ring-1 ring-slate-200" data-testid="a11y-transcript-text">{a.transcript}</p>
            </div>
          </div>
        </div>
      )}
    </>
  );
}
