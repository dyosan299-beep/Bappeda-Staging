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
      <div className="mx-auto max-w-4xl space-y-6 px-4 py-10 sm:px-6">
        <h1 className="font-head text-3xl font-extrabold text-[#232F3E]">Tentang PETA INKLUSI</h1>
        <p className="leading-relaxed text-slate-700">
          PETA INKLUSI menyajikan data sosial Bappeda Kota Makassar untuk analisis dan perencanaan program pada empat kategori utama: <b>Disabilitas, Stunting, Anak Tidak Sekolah (ATS), dan Kemiskinan</b>. Seluruh kategori memakai master wilayah yang sama mulai dari Kota Makassar, kecamatan, sampai kelurahan.
        </p>
        <section>
          <h2 className="font-head text-xl font-bold text-[#117A69]">Pengguna portal</h2>
          <ul className="mt-2 list-disc space-y-1.5 pl-6 text-slate-700">
            <li><b>Publik</b> dapat melihat dashboard, peta tematik, dan flow sistem berisi data agregat tanpa masuk akun.</li>
            <li><b>NGO</b> dapat mendaftar akun, lalu mengajukan dan memantau inquiry program setelah akun diverifikasi.</li>
            <li><b>Operator</b> mengelola data wilayah sesuai kewenangan dengan data pribadi yang disamarkan.</li>
            <li><b>Admin dan Super Admin</b> memverifikasi data, memproses inquiry, mengelola pengguna, dan memeriksa log audit.</li>
          </ul>
        </section>
        <section>
          <h2 className="font-head text-xl font-bold text-[#117A69]">Perlindungan data pribadi</h2>
          <p className="mt-2 leading-relaxed text-slate-700">
            Server menyamarkan NIK, nama, alamat, email, dan nomor telepon (contoh NIK menjadi 7371********1234, email menjadi gu****@gmail.com, telepon menjadi 0812******89). Endpoint publik hanya mengembalikan data agregat. Server membatasi akses data individu berdasarkan peran dan mencatat setiap akses data sensitif, proses masuk akun, impor data, dan perubahan status inquiry di log audit.
          </p>
        </section>
        <section>
          <h2 className="font-head text-xl font-bold text-[#117A69]">Sumber data</h2>
          <p className="mt-2 leading-relaxed text-slate-700">
            Sumber data meliputi Matriks Bappeda per kecamatan, DTSEN rumah tangga Kecamatan Makassar dan Tallo, data balita stunting tahun 2026 Kecamatan Makassar dan Tallo, rekap disabilitas per kelurahan, Matriks ATS, serta peta batas wilayah PETA_DASAR. Wilayah yang belum memiliki data ditandai dengan label "belum ada data".
          </p>
        </section>
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
