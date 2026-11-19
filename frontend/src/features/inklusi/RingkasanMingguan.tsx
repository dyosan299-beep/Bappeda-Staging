import React, { useEffect, useState } from "react";
import { Link } from "react-router-dom";
import { toast } from "sonner";
import { CalendarClock, Mail, Send, RefreshCw, Users, Baby, GraduationCap, Accessibility, Inbox, AlertTriangle } from "lucide-react";
import api, { formatApiErrorDetail } from "@/lib/api";
import { useAuth } from "@/context/AuthContext";
import * as ButtonUI from "@/components/ui/button";
import * as BadgeUI from "@/components/ui/badge";
import * as SkeletonUI from "@/components/ui/skeleton";
import * as TabsUI from "@/components/ui/tabs";
import { fmt } from "./theme";

// Komponen shadcn (JSX) diberi tipe longgar agar kompatibel dengan TSX
const Button: any = (ButtonUI as any).Button;
const Badge: any = (BadgeUI as any).Badge;
const Skeleton: any = (SkeletonUI as any).Skeleton;
const { Tabs, TabsContent, TabsList, TabsTrigger }: any = TabsUI as any;

const SEND_ROLES = ["superadmin", "admin", "admin_bappeda", "verifikator"];
const th = "p-2 text-left text-[11px] font-bold uppercase text-slate-600";
const ROLE_LABEL: Record<string, string> = {
  pimpinan: "Pimpinan", superadmin: "Super Admin", admin: "Admin", admin_bappeda: "Admin Bappeda", tambahan: "Tambahan",
};
const RUN_STATUS: Record<string, string> = {
  selesai: "bg-[#E6FAF6] text-[#117A69]", berjalan: "bg-slate-100 text-slate-700", gagal: "bg-red-50 text-red-700",
};

function Stat({ icon: Icon, label, nilai, baru, warna, testid }: any) {
  return (
    <div className="rounded-xl border border-slate-200 bg-white p-4" style={{ borderTop: `4px solid ${warna}` }} data-testid={testid}>
      <p className="flex items-center gap-2 text-[11px] font-bold uppercase text-slate-600"><Icon className="h-4 w-4" style={{ color: warna }} />{label}</p>
      <p className="mt-1 font-head text-3xl font-extrabold text-[#232F3E]">{fmt(nilai)}</p>
      <p className={`text-xs font-bold ${baru ? "text-[#117A69]" : "text-slate-400"}`}>{baru ? `+${fmt(baru)} minggu ini` : "tidak ada data baru"}</p>
    </div>
  );
}

export default function RingkasanMingguan() {
  const { user } = useAuth() as any;
  const [d, setD] = useState<any>(null);
  const [runs, setRuns] = useState<any[]>([]);
  const [busy, setBusy] = useState(false);
  const canSend = SEND_ROLES.includes(user?.role);

  const load = () => {
    setD(null);
    api.get("/inklusi/ringkasan-mingguan/preview").then((r) => setD(r.data)).catch(() => setD(false));
    api.get("/inklusi/ringkasan-mingguan/riwayat").then((r) => setRuns(r.data.items || [])).catch(() => setRuns([]));
  };
  useEffect(() => { load(); }, []);

  const kirim = async () => {
    setBusy(true);
    try {
      const r = await api.post("/inklusi/ringkasan-mingguan/kirim", {});
      const h = r.data.hasil || {};
      if (r.data.status === "gagal") toast.error(`Gagal membuat ringkasan: ${r.data.error || ""}`);
      else if (h.terkirim) toast.success(`Ringkasan terkirim ke ${h.terkirim} penerima`);
      else toast.warning(`${h.belum_terkirim || 0} email masuk antrean (SMTP belum aktif), ${h.gagal || 0} gagal`);
      load();
    } catch (er: any) { toast.error(formatApiErrorDetail(er.response?.data?.detail)); } finally { setBusy(false); }
  };

  if (d === false) return (
    <div className="rounded-xl border border-red-200 bg-red-50 p-5" data-testid="ringkasan-error">
      <p className="font-bold text-red-700">Gagal memuat ringkasan mingguan.</p>
      <Button variant="outline" className="mt-3" onClick={load} data-testid="ringkasan-retry-btn"><RefreshCw className="mr-2 h-4 w-4" />Coba lagi</Button>
    </div>
  );
  if (!d) return (
    <div className="space-y-4" aria-live="polite" data-testid="ringkasan-loading">
      <Skeleton className="h-10 w-80 max-w-full" /><div className="grid gap-3 sm:grid-cols-3">{[0, 1, 2].map((i) => <Skeleton key={i} className="h-28" />)}</div><Skeleton className="h-96" />
    </div>
  );

  const s = d.ringkasan; const t = s.total; const iq = s.inquiry;
  return (
    <div className="space-y-5" data-testid="ringkasan-mingguan-page">
      <div className="flex flex-wrap items-start justify-between gap-3">
        <div>
          <p className="font-head text-2xl font-extrabold text-[#232F3E]">Ringkasan Mingguan Pimpinan</p>
          <p className="text-sm text-slate-600">Email ringkasan otomatis per kecamatan dan pembaruan inquiry NGO untuk Pimpinan & Admin.</p>
          <p className="mt-1 text-xs font-bold text-slate-500" data-testid="ringkasan-periode">Periode pratinjau: {s.periode.label}</p>
        </div>
        <div className="flex flex-wrap gap-2">
          <Button variant="outline" onClick={load} data-testid="ringkasan-refresh-btn"><RefreshCw className="mr-2 h-4 w-4" />Muat ulang</Button>
          {canSend && <Button onClick={kirim} disabled={busy} className="bg-[#117A69] hover:bg-[#0E6456]" data-testid="ringkasan-send-btn">
            <Send className={`mr-2 h-4 w-4 ${busy ? "animate-pulse" : ""}`} />{busy ? "Mengirim…" : "Kirim sekarang"}</Button>}
        </div>
      </div>

      <div className="grid gap-3 lg:grid-cols-2">
        <section className="rounded-xl border-2 border-[#117A69] bg-[#E6FAF6] p-4" data-testid="ringkasan-jadwal">
          <p className="flex items-center gap-2 font-head font-extrabold text-[#232F3E]"><CalendarClock className="h-5 w-5 text-[#117A69]" />Jadwal otomatis aktif</p>
          <p className="text-sm text-slate-700">{d.jadwal.label} · dikirim terpisah ke setiap penerima.</p>
        </section>
        <section className={`rounded-xl border-2 p-4 ${d.smtp.configured ? "border-[#117A69] bg-[#E6FAF6]" : "border-[#F4B63A] bg-[#FEF6E4]"}`} data-testid="ringkasan-smtp-status">
          <p className="flex items-center gap-2 font-head font-extrabold text-[#232F3E]">
            {d.smtp.configured ? <Mail className="h-5 w-5 text-[#117A69]" /> : <AlertTriangle className="h-5 w-5 text-[#B7791F]" />}
            {d.smtp.configured ? "SMTP kantor aktif" : "SMTP belum dikonfigurasi"}</p>
          <p className="text-sm text-slate-700">{d.smtp.configured ? `${d.smtp.host}:${d.smtp.port} · pengirim ${d.smtp.from}`
            : <>Email disimpan di antrean dan terkirim otomatis setelah SMTP diisi. Lihat <Link to="/notifikasi-email" className="font-bold text-[#117A69] underline" data-testid="ringkasan-outbox-link">Notifikasi Email</Link>.</>}</p>
        </section>
      </div>

      <div className="grid gap-3 sm:grid-cols-2 lg:grid-cols-4">
        <Stat icon={Baby} label="Anak stunting" nilai={t.stunting} baru={t.stunting_baru} warna="#117A69" testid="ringkasan-stat-stunting" />
        <Stat icon={GraduationCap} label={`ATS${s.tahun_ats ? " " + s.tahun_ats : ""}`} nilai={t.ats} baru={t.ats_baru} warna="#F4B63A" testid="ringkasan-stat-ats" />
        <Stat icon={Accessibility} label={`Disabilitas${s.tahun_disabilitas ? " " + s.tahun_disabilitas : ""}`} nilai={t.disabilitas} baru={t.disabilitas_baru} warna="#232F3E" testid="ringkasan-stat-disabilitas" />
        <div className="rounded-xl border border-slate-200 bg-white p-4" style={{ borderTop: "4px solid #6FE3CF" }} data-testid="ringkasan-stat-inquiry">
          <p className="flex items-center gap-2 text-[11px] font-bold uppercase text-slate-600"><Inbox className="h-4 w-4 text-[#117A69]" />Inquiry NGO</p>
          <p className="mt-1 font-head text-3xl font-extrabold text-[#232F3E]">{fmt(iq.total)}</p>
          <p className="text-xs font-bold text-slate-600">{iq.baru.length} baru · {iq.jumlah_perubahan} perubahan status</p>
        </div>
      </div>

      <Tabs defaultValue="preview" className="w-full">
        <TabsList data-testid="ringkasan-tabs" className="h-auto w-full flex-wrap justify-start">
          <TabsTrigger value="preview" data-testid="ringkasan-tab-preview">Pratinjau email</TabsTrigger>
          <TabsTrigger value="kecamatan" data-testid="ringkasan-tab-kecamatan">Per kecamatan</TabsTrigger>
          <TabsTrigger value="penerima" data-testid="ringkasan-tab-penerima">Penerima ({d.penerima.length})</TabsTrigger>
          <TabsTrigger value="riwayat" data-testid="ringkasan-tab-riwayat">Riwayat pengiriman</TabsTrigger>
        </TabsList>

        <TabsContent value="preview">
          <div className="rounded-xl border border-slate-200 bg-slate-50 p-3">
            <p className="mb-2 text-xs text-slate-600"><b>Subjek:</b> <span data-testid="ringkasan-subject">{d.email.subject}</span></p>
            <iframe title="Pratinjau email ringkasan mingguan" srcDoc={d.email.html} sandbox=""
              className="h-[min(640px,75dvh)] w-full rounded-lg border border-slate-200 bg-white" data-testid="ringkasan-email-preview" />
          </div>
        </TabsContent>

        <TabsContent value="kecamatan">
          <div className="overflow-x-auto rounded-xl border border-slate-200 bg-white">
            <table className="w-full text-sm" data-testid="ringkasan-kecamatan-table">
              <thead className="bg-slate-50"><tr>{["Kecamatan", "Stunting", "ATS", "Disabilitas"].map((h) => <th key={h} className={th}>{h}</th>)}</tr></thead>
              <tbody>
                {s.per_kecamatan.map((k: any) => (
                  <tr key={k.kecamatan} className="border-t" data-testid="ringkasan-kecamatan-row">
                    <td className="p-2 font-semibold">{k.kecamatan}</td>
                    {[["stunting", "stunting_baru"], ["ats", "ats_baru"], ["disabilitas", "disabilitas_baru"]].map(([a, b]) => (
                      <td key={a} className="p-2">{fmt(k[a])}{k[b] > 0 && <span className="ml-1 text-xs font-bold text-[#117A69]">+{fmt(k[b])}</span>}</td>
                    ))}
                  </tr>
                ))}
              </tbody>
            </table>
          </div>
        </TabsContent>

        <TabsContent value="penerima">
          <div className="rounded-xl border border-slate-200 bg-white p-4" data-testid="ringkasan-penerima-list">
            {d.penerima.length ? (
              <ul className="divide-y">
                {d.penerima.map((p: any) => (
                  <li key={p.email} className="flex flex-wrap items-center justify-between gap-2 py-2 text-sm">
                    <span className="flex min-w-0 flex-wrap items-center gap-x-2 gap-y-0.5"><Users className="h-4 w-4 shrink-0 text-slate-500" /><b>{p.name || p.email}</b>{p.name && <span className="break-all text-slate-500">{p.email}</span>}</span>
                    <Badge variant="outline" className="border-[#117A69] text-[#117A69]">{ROLE_LABEL[p.role] || p.role}</Badge>
                  </li>
                ))}
              </ul>
            ) : <p className="text-sm text-slate-500">Belum ada akun Pimpinan/Admin aktif. Tambahkan lewat <Link to="/kelola-petugas" className="font-bold text-[#117A69] underline">User Management</Link>.</p>}
            <p className="mt-3 text-xs text-slate-500">Penerima otomatis: semua akun aktif dengan peran Pimpinan, Super Admin, Admin, dan Admin Bappeda.</p>
          </div>
        </TabsContent>

        <TabsContent value="riwayat">
          <div className="overflow-x-auto rounded-xl border border-slate-200 bg-white">
            <table className="w-full text-sm" data-testid="ringkasan-riwayat-table">
              <thead className="bg-slate-50"><tr>{["Waktu", "Sumber", "Periode", "Penerima", "Hasil", "Status"].map((h) => <th key={h} className={th}>{h}</th>)}</tr></thead>
              <tbody>
                {runs.map((r) => (
                  <tr key={r.id} className="border-t align-top" data-testid="ringkasan-riwayat-row">
                    <td className="whitespace-nowrap p-2 text-xs">{new Date(r.created_at).toLocaleString("id-ID")}</td>
                    <td className="p-2 text-xs">{r.sumber === "cron" ? "Jadwal otomatis" : `Manual (${r.oleh})`}</td>
                    <td className="p-2 text-xs">{r.periode?.label || "-"}</td>
                    <td className="p-2 text-xs">{(r.penerima || []).length}</td>
                    <td className="p-2 text-xs">{r.hasil ? `${r.hasil.terkirim || 0} terkirim · ${r.hasil.belum_terkirim || 0} antre · ${r.hasil.gagal || 0} gagal` : r.error || "-"}</td>
                    <td className="p-2"><span className={`rounded-full px-2 py-0.5 text-[11px] font-bold ${RUN_STATUS[r.status] || "bg-slate-100"}`}>{r.status}</span></td>
                  </tr>
                ))}
                {!runs.length && <tr><td colSpan={6} className="p-6 text-center text-slate-500" data-testid="ringkasan-riwayat-empty">Belum ada pengiriman. Ringkasan pertama dikirim otomatis Senin pukul 06.00 WITA.</td></tr>}
              </tbody>
            </table>
          </div>
        </TabsContent>
      </Tabs>
    </div>
  );
}
