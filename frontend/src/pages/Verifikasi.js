import { useCallback, useEffect, useState } from "react";
import { toast } from "sonner";
import api, { formatApiErrorDetail } from "@/lib/api";
import { ClipboardCheck, Check, X, Clock, MapPin, Building, ArrowRight } from "lucide-react";

const FIELD_LABEL = {
  kemiskinan_ekstrim_kk: "Kemiskinan Ekstrim (KK)",
  stunting_anak: "Stunting (anak)",
  anak_jalanan: "Anak Jalanan (jiwa)",
  ats: "Anak Tidak Sekolah",
  disabilitas: "Disabilitas (orang)",
  kemiskinan_persen: "Tingkat Kemiskinan (%)",
};

const fmt = (v) => (v === null || v === undefined || v === "" ? "–" : Number(v).toLocaleString("id-ID"));

const fmtDate = (iso) => {
  try {
    return new Date(iso).toLocaleString("id-ID", {
      day: "2-digit", month: "short", year: "numeric", hour: "2-digit", minute: "2-digit",
    });
  } catch { return iso || ""; }
};

const TABS = [
  { key: "pending", label: "Menunggu" },
  { key: "approved", label: "Disetujui" },
  { key: "rejected", label: "Ditolak" },
];

export default function Verifikasi() {
  const [tab, setTab] = useState("pending");
  const [items, setItems] = useState([]);
  const [loading, setLoading] = useState(false);

  const load = useCallback(async () => {
    setLoading(true);
    try {
      const { data } = await api.get(`/verifikasi?status=${tab}`);
      setItems(data);
    } catch {
      // ignore
    } finally {
      setLoading(false);
    }
  }, [tab]);

  useEffect(() => { load(); }, [load]);

  const approve = async (id) => {
    try {
      await api.post(`/verifikasi/${id}/approve`);
      toast.success("Perubahan disetujui & diterapkan");
      load();
    } catch (e) {
      toast.error(formatApiErrorDetail(e.response?.data?.detail));
    }
  };

  const reject = async (id) => {
    const note = window.prompt("Alasan penolakan (opsional):", "");
    if (note === null) return;
    try {
      await api.post(`/verifikasi/${id}/reject`, { note });
      toast.success("Perubahan ditolak");
      load();
    } catch (e) {
      toast.error(formatApiErrorDetail(e.response?.data?.detail));
    }
  };

  return (
    <div className="space-y-6" data-testid="verifikasi-page">
      <div>
        <p className="inline-flex items-center gap-2 font-head text-3xl font-extrabold md:text-4xl">
          <ClipboardCheck className="h-8 w-8 text-primary" /> Verifikasi Data
        </p>
        <p className="mt-1 max-w-3xl text-sm text-muted-foreground">
          Tinjau usulan perubahan data yang dikirim petugas/operator. Setujui untuk menerapkan ke
          data resmi, atau tolak dengan alasan.
        </p>
      </div>

      <div className="flex flex-wrap gap-2" data-testid="verifikasi-tabs">
        {TABS.map((t) => (
          <button
            key={t.key}
            data-testid={`verif-tab-${t.key}`}
            onClick={() => setTab(t.key)}
            className={`rounded-full border-2 px-4 py-1.5 text-sm font-semibold transition-colors focus:outline-none ${
              tab === t.key ? "border-transparent bg-primary text-primary-foreground" : "border-border bg-card hover:border-accent"
            }`}
          >
            {t.label}
          </button>
        ))}
      </div>

      {loading ? (
        <p className="py-10 text-center text-sm text-muted-foreground">Memuat…</p>
      ) : items.length === 0 ? (
        <div className="rounded-lg border-2 border-dashed border-border p-10 text-center text-sm text-muted-foreground">
          Tidak ada usulan pada kategori ini.
        </div>
      ) : (
        <ul className="space-y-4" data-testid="verifikasi-list">
          {items.map((it) => (
            <li key={it.id} className="rounded-lg border-2 border-border bg-card p-5" data-testid="verifikasi-item">
              <div className="flex flex-wrap items-start justify-between gap-3">
                <div>
                  <div className="flex items-center gap-2 font-head text-lg font-bold">
                    {it.target_type === "region" ? <MapPin className="h-4 w-4 text-primary" /> : <Building className="h-4 w-4 text-accent" />}
                    {it.target_type === "region" ? `Kecamatan ${it.target_nama}` : `Kelurahan ${it.target_nama}`}
                    {it.target_type === "kelurahan" && (
                      <span className="text-sm font-normal text-muted-foreground">· Kec. {it.kecamatan}</span>
                    )}
                  </div>
                  <p className="mt-1 inline-flex items-center gap-1 text-xs text-muted-foreground">
                    <Clock className="h-3 w-3" /> {fmtDate(it.submitted_at)} · oleh {it.submitted_by}
                  </p>
                </div>
                {it.status === "pending" && (
                  <div className="flex items-center gap-2">
                    <button
                      data-testid={`approve-change-${it.id}`}
                      onClick={() => approve(it.id)}
                      className="inline-flex items-center gap-1.5 rounded-md bg-[hsl(160_84%_27%)] px-4 py-2 text-sm font-semibold text-white hover:opacity-90 focus:outline-none"
                    >
                      <Check className="h-4 w-4" /> Setujui
                    </button>
                    <button
                      data-testid={`reject-change-${it.id}`}
                      onClick={() => reject(it.id)}
                      className="inline-flex items-center gap-1.5 rounded-md border-2 border-destructive px-4 py-2 text-sm font-semibold text-destructive hover:bg-destructive hover:text-destructive-foreground focus:outline-none"
                    >
                      <X className="h-4 w-4" /> Tolak
                    </button>
                  </div>
                )}
                {it.status !== "pending" && (
                  <span className={`rounded-full px-3 py-1 text-xs font-bold ${it.status === "approved" ? "bg-primary text-primary-foreground" : "bg-destructive text-destructive-foreground"}`}>
                    {it.status === "approved" ? "Disetujui" : "Ditolak"} oleh {it.reviewed_by || "-"}
                  </span>
                )}
              </div>

              <div className="mt-4 overflow-x-auto">
                <table className="w-full text-sm">
                  <thead>
                    <tr className="border-b border-border text-left text-xs uppercase tracking-wide text-muted-foreground">
                      <th className="py-2 pr-4 font-bold">Indikator</th>
                      <th className="py-2 pr-4 font-bold">Sebelumnya</th>
                      <th className="py-2 font-bold">Usulan Baru</th>
                    </tr>
                  </thead>
                  <tbody>
                    {Object.keys(it.changes || {}).map((k) => (
                      <tr key={k} className="border-b border-border/60">
                        <td className="py-2 pr-4 font-medium">{FIELD_LABEL[k] || k}</td>
                        <td className="py-2 pr-4 tabular-nums text-muted-foreground">{fmt(it.before?.[k])}</td>
                        <td className="py-2 tabular-nums font-bold text-primary">
                          <span className="inline-flex items-center gap-1">
                            <ArrowRight className="h-3 w-3" /> {fmt(it.changes[k])}
                          </span>
                        </td>
                      </tr>
                    ))}
                  </tbody>
                </table>
              </div>

              {it.note && (
                <p className="mt-3 rounded-md bg-primary/5 px-3 py-2 text-xs text-primary">
                  Catatan: {it.note}
                </p>
              )}
            </li>
          ))}
        </ul>
      )}
    </div>
  );
}
