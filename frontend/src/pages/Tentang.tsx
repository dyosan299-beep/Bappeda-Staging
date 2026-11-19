import React from "react";
import { Link } from "react-router-dom";
import PublicLayout from "@/components/PublicLayout";
import InklusiMap from "@/features/inklusi/InklusiMap";
import { MapDataTable } from "@/features/a11y/components";
import { usePublicA11yData } from "@/features/a11y/data";
import { BTN_PRIMARY } from "@/features/a11y/ui";

export function Tentang() {
  return (
    <PublicLayout>
      <div className="mx-auto max-w-4xl space-y-6 px-4 py-10">
        <h1 className="font-head text-3xl font-extrabold text-[#232F3E]">Tentang PETA INKLUSI</h1>
        <p className="text-slate-700">PETA INKLUSI adalah platform Bappeda Kota Makassar yang menyajikan data sosial secara terintegrasi untuk mendukung analisis dan perencanaan program pada empat kategori utama: <b>Disabilitas, Stunting, Anak Tidak Sekolah (ATS), dan Kemiskinan</b>. Seluruh kategori memakai master wilayah yang sama: Kota Makassar → Kecamatan → Kelurahan.</p>
        <section><h2 className="font-head text-xl font-bold text-[#117A69]">Siapa yang dapat menggunakan?</h2>
          <ul className="mt-2 list-disc space-y-1 pl-6 text-slate-700">
            <li><b>Publik</b> — melihat dashboard, peta, dan flow sistem berisi data agregat tanpa login.</li>
            <li><b>NGO</b> — mendaftar, lalu setelah diverifikasi dapat mengajukan dan memantau inquiry program.</li>
            <li><b>Operator</b> — mengelola data wilayah sesuai kewenangan (data pribadi tersamarkan).</li>
            <li><b>Admin & Super Admin</b> — memverifikasi data, memproses inquiry, mengelola pengguna dan audit.</li>
          </ul></section>
        <section><h2 className="font-head text-xl font-bold text-[#117A69]">Perlindungan data pribadi</h2>
          <p className="mt-2 text-slate-700">NIK, nama, alamat, email, dan nomor telepon dimasking di sisi server (contoh NIK: 7371********1234, email: gu****@gmail.com, telepon: 0812******89). API publik hanya mengembalikan agregat. Akses data individu dibatasi peran (RBAC) dan setiap akses data sensitif, login, impor, maupun perubahan status inquiry tercatat di audit log.</p></section>
        <section><h2 className="font-head text-xl font-bold text-[#117A69]">Sumber data</h2>
          <p className="mt-2 text-slate-700">Matriks Bappeda (rekap per kecamatan), DTSEN (rumah tangga Kec. Makassar & Tallo), data balita stunting 2026 (Kec. Makassar & Tallo), rekap disabilitas per kelurahan, Matriks ATS, dan batas wilayah PETA_DASAR. Data yang belum tersedia ditandai jelas sebagai “belum ada data”.</p></section>
        <Link to="/login?mode=ngo" className={BTN_PRIMARY} data-testid="tentang-daftar-ngo">Daftar sebagai NGO</Link>
      </div>
    </PublicLayout>
  );
}

function PetaA11y({ jenis, judul, children }: { jenis: "sosial" | "kemiskinan"; judul: string; children: React.ReactNode }) {
  const { s } = usePublicA11yData();
  return (
    <>
      <a href="#a11y-peta-tabel" className="sr-only focus:not-sr-only focus:absolute focus:left-2 focus:top-2 focus:z-[999] focus:rounded focus:bg-white focus:px-3 focus:py-2" data-testid="skip-map">
        Lewati peta, langsung ke tabel data
      </a>
      <section id="a11y-peta" tabIndex={-1} aria-label={`${judul}. Peta interaktif; data yang sama tersedia sebagai tabel di bawah peta.`} className="focus:outline-none">
        <div className="h-[calc(100dvh-4rem)] min-h-[380px]">{children}</div>
      </section>
      <MapDataTable s={s} jenis={jenis} />
    </>
  );
}

export function PublicPetaSosial() {
  return <PublicLayout fullBleed><PetaA11y jenis="sosial" judul="Peta Sosial"><InklusiMap publicMode kategoriList={["disabilitas", "stunting", "ats"]} title="Peta Sosial — data agregat" /></PetaA11y></PublicLayout>;
}

export function PublicPetaKemiskinan() {
  return <PublicLayout fullBleed><PetaA11y jenis="kemiskinan" judul="Peta Kemiskinan"><InklusiMap publicMode kategoriList={["kemiskinan"]} title="Peta Kemiskinan — data agregat"
    metricOptions={[{ id: "value", label: "KK desil 1-2" }, { id: "persen_desil_1_2", label: "% KK desil 1-2" }, { id: "total_households", label: "Jumlah rumah tangga" }, { id: "pbi_nas", label: "Penerima PBI Nasional" }, { id: "pbi_pemda", label: "Penerima PBI Pemda" }, { id: "rumah_rentan", label: "Rumah rentan" }]} /></PetaA11y></PublicLayout>;
}

export default Tentang;
