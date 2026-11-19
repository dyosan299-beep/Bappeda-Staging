import { useEffect, useState } from "react";
import api from "@/lib/api";
import { Speak } from "@/components/Speak";
import { useA11y } from "@/context/AccessibilityContext";
import {
  Eye, Ear, Type, Contrast, Volume2, Hand, Info,
} from "lucide-react";
import { ResponsiveContainer, BarChart, Bar, XAxis, YAxis, CartesianGrid, Tooltip } from "recharts";

const fmt = (n) => (n ?? 0).toLocaleString("id-ID");

// Data kategori tersimpan di basis data masih memakai istilah lama (mis. "(Tunanetra)").
// Tampilkan dengan istilah terkini tanpa mengubah data sumber.
const labelRagam = (k) => k
  .replace(/tunanetra/i, "Disabilitas Buta")
  .replace(/tunarungu/i, "Disabilitas Tuli");

export default function Disabilitas() {
  const [data, setData] = useState(null);
  const { setTextSize, setContrast, contrast } = useA11y();

  useEffect(() => {
    api.get("/disability").then((r) => setData(r.data));
  }, []);

  if (!data) return <div className="p-10 text-center text-muted-foreground">Memuat…</div>;

  const buta = data.ragam.find((r) => r.kategori.toLowerCase().includes("penglihatan"));
  const tuli = data.ragam.find((r) => r.kategori.toLowerCase().includes("pendengaran"));
  const total2025 = data.total_per_tahun.find((t) => t.tahun === 2025)?.jumlah;

  const ragamText = `Data ragam disabilitas Kota Makassar tahun 2025. Total ${fmt(total2025)} orang. ${data.ragam.map((r) => `${labelRagam(r.kategori)} sebanyak ${fmt(r.jumlah)} orang`).join(". ")}.`;
  const ragamChart = data.ragam.map((r) => ({ ...r, kategori: labelRagam(r.kategori) }));

  return (
    <div className="space-y-8" data-testid="disabilitas-page">
      <div>
        <p className="font-head text-3xl font-extrabold md:text-4xl">Aksesibilitas & Disabilitas</p>
        <p className="mt-1 max-w-3xl text-sm text-muted-foreground">
          Fitur inklusif untuk disabilitas buta dan disabilitas tuli, sekaligus data
          disabilitas Kota Makassar.
        </p>
      </div>

      {/* Two accessibility mode cards */}
      <div className="grid grid-cols-1 gap-6 lg:grid-cols-2">
        {/* Disabilitas buta */}
        <div className="rounded-lg border-2 border-primary bg-card p-6" data-testid="mode-tunanetra">
          <div className="flex items-center gap-3">
            <div className="flex h-12 w-12 shrink-0 items-center justify-center rounded-md bg-primary text-primary-foreground">
              <Eye className="h-6 w-6" />
            </div>
            <div className="min-w-0">
              <h2 className="font-head text-xl font-extrabold">Mode Disabilitas Buta</h2>
              <p className="text-sm text-muted-foreground">Buta total / low vision</p>
            </div>
          </div>
          <p className="mt-4 text-sm leading-relaxed">
            Seluruh data dapat <b>dibacakan dengan suara</b> (text-to-speech), didukung teks
            berukuran besar dan mode kontras tinggi untuk memudahkan pengguna dengan gangguan
            penglihatan.
          </p>
          <div className="mt-4 flex flex-wrap gap-2">
            <Speak text={ragamText} label="Bacakan Data Disabilitas" testid="tunanetra-speak" />
            <button
              data-testid="tunanetra-bigtext"
              onClick={() => setTextSize("xlarge")}
              className="inline-flex items-center gap-2 rounded-full border-2 border-accent px-4 py-2 text-sm font-semibold transition-colors hover:bg-accent hover:text-accent-foreground focus:outline-none"
            >
              <Type className="h-4 w-4" /> Perbesar Teks
            </button>
            <button
              data-testid="tunanetra-contrast"
              onClick={() => setContrast(!contrast)}
              className="inline-flex items-center gap-2 rounded-full border-2 border-accent px-4 py-2 text-sm font-semibold transition-colors hover:bg-accent hover:text-accent-foreground focus:outline-none"
            >
              <Contrast className="h-4 w-4" /> Kontras Tinggi
            </button>
          </div>
          <div className="mt-4 flex items-center gap-2 rounded-md bg-secondary p-3 text-xs text-muted-foreground">
            <Volume2 className="h-4 w-4 shrink-0" />
            Tip: setiap tombol "Bacakan" akan melafalkan informasi secara lisan.
          </div>
        </div>

        {/* Disabilitas tuli */}
        <div className="rounded-lg border-2 border-accent bg-card p-6" data-testid="mode-tunarungu">
          <div className="flex items-center gap-3">
            <div className="flex h-12 w-12 shrink-0 items-center justify-center rounded-md bg-accent text-accent-foreground">
              <Ear className="h-6 w-6" />
            </div>
            <div className="min-w-0">
              <h2 className="font-head text-xl font-extrabold">Mode Disabilitas Tuli</h2>
              <p className="text-sm text-muted-foreground">Tuli / kurang dengar</p>
            </div>
          </div>
          <p className="mt-4 text-sm leading-relaxed">
            Informasi disajikan sepenuhnya secara <b>visual dan teks</b> — grafik, ikon, dan angka
            besar — tanpa bergantung pada audio. Cocok bagi pengguna dengan gangguan pendengaran.
          </p>
          <div className="mt-4 grid grid-cols-1 gap-3 sm:grid-cols-2">
            <div className="rounded-md border-2 border-border p-4 text-center">
              <Eye className="mx-auto h-6 w-6 text-primary" />
              <p className="mt-2 font-head text-2xl font-extrabold text-primary">{fmt(buta?.jumlah)}</p>
              <p className="mt-1 text-xs leading-snug text-muted-foreground">Disabilitas Buta (penglihatan)</p>
            </div>
            <div className="rounded-md border-2 border-border p-4 text-center">
              <Ear className="mx-auto h-6 w-6 text-[hsl(160_84%_27%)]" />
              <p className="mt-2 font-head text-2xl font-extrabold text-[hsl(160_84%_27%)]">{fmt(tuli?.jumlah)}</p>
              <p className="mt-1 text-xs leading-snug text-muted-foreground">Disabilitas Tuli (pendengaran)</p>
            </div>
          </div>
          <div className="mt-4 flex items-center gap-2 rounded-md bg-secondary p-3 text-xs text-muted-foreground">
            <Hand className="h-4 w-4 shrink-0" />
            Semua konten memiliki padanan teks; tidak ada informasi penting yang hanya berupa suara.
          </div>
        </div>
      </div>

      {/* Data disabilitas */}
      <div className="rounded-lg border-2 border-border bg-card p-6">
        <div className="mb-4 flex items-center justify-between">
          <h3 className="font-head text-lg font-bold">Ragam Disabilitas Kota Makassar 2025 · Total {fmt(total2025)} orang</h3>
          <Speak text={ragamText} label="Bacakan" testid="ragam-speak" />
        </div>
        <ResponsiveContainer width="100%" height={320}>
          <BarChart data={ragamChart} layout="vertical" margin={{ top: 0, right: 30, left: 40, bottom: 0 }}>
            <CartesianGrid strokeDasharray="3 3" stroke="#e2e8f0" />
            <XAxis type="number" tick={{ fontSize: 12 }} />
            <YAxis type="category" dataKey="kategori" tick={{ fontSize: 11 }} width={200} />
            <Tooltip />
            <Bar dataKey="jumlah" fill="#047857" radius={[0, 4, 4, 0]} />
          </BarChart>
        </ResponsiveContainer>
      </div>

      {/* Breakdown tables */}
      <div className="grid grid-cols-1 gap-6 md:grid-cols-3">
        {[
          { title: "Jenis Kelamin", rows: data.jenis_kelamin },
          { title: "Tingkat Pendidikan", rows: data.pendidikan },
          { title: "Status NIK", rows: data.nik },
        ].map((b) => (
          <div key={b.title} className="rounded-lg border-2 border-border bg-card p-6">
            <h4 className="mb-3 font-head text-base font-bold">{b.title}</h4>
            <ul className="space-y-1.5 text-sm">
              {b.rows.map((r) => (
                <li key={r.kategori} className="flex items-center justify-between border-b border-border py-1.5">
                  <span>{r.kategori}</span>
                  <span className="font-bold tabular-nums">{fmt(r.jumlah)}</span>
                </li>
              ))}
            </ul>
          </div>
        ))}
      </div>

      <div className="flex items-start gap-3 rounded-md border border-border bg-secondary p-4 text-sm text-muted-foreground">
        <Info className="mt-0.5 h-4 w-4 shrink-0" />
        Pengaturan aksesibilitas (ukuran teks, kontras, animasi) tersedia di bilah atas setiap
        halaman dan tersimpan otomatis di peramban Anda.
      </div>
    </div>
  );
}
