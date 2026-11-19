import React, { useState } from "react";
import InklusiMap from "@/features/inklusi/InklusiMap";
import PetaGIS from "@/pages/PetaGIS";

export const KEMISKINAN_METRICS = [
  { id: "value", label: "KK desil 1-2 (DTSEN)" },
  { id: "persen_desil_1_2", label: "% KK desil 1-2" },
  { id: "total_households", label: "Jumlah rumah tangga" },
  { id: "total_individu", label: "Jumlah jiwa" },
  { id: "pbi_nas", label: "Penerima PBI Nasional" },
  { id: "pbi_pemda", label: "Penerima PBI Pemda" },
  { id: "rumah_rentan", label: "Rumah kondisi rentan" },
  { id: "sanitasi_tidak_layak", label: "Sanitasi tidak layak" },
  { id: "air_rentan", label: "Air minum rentan" },
  { id: "hunian_rentan", label: "Hunian sempit" },
  { id: "avg_risk", label: "Skor kerentanan rata-rata" },
  { id: "skor_prioritas", label: "Skor prioritas intervensi" },
];

/** Peta Kemiskinan (sebelumnya "Peta Rumah (Bangunan)").
 *  Tab 1: distribusi kemiskinan kecamatan → kelurahan. Tab 2: peta bangunan sebagai indikator pendukung. */
export default function PetaKemiskinan() {
  const [tab, setTab] = useState<"wilayah" | "bangunan">("wilayah");
  return (
    <div className="flex h-full w-full flex-col" data-testid="page-peta-kemiskinan">
      <div className="flex shrink-0 gap-1 overflow-x-auto border-b border-slate-200 bg-white px-2 py-2 sm:px-3" role="tablist" aria-label="Tampilan Peta Kemiskinan">
        {[["wilayah", "Distribusi Kemiskinan per Wilayah", "Per Wilayah"], ["bangunan", "Peta Bangunan (indikator pendukung)", "Peta Bangunan"]].map(([id, label, short]) => (
          <button key={id} role="tab" aria-selected={tab === id} type="button" data-testid={`kemiskinan-tab-${id}`} onClick={() => setTab(id as any)}
            aria-label={label} className={`min-h-10 shrink-0 whitespace-nowrap rounded-md px-3 py-1.5 text-xs font-bold ${tab === id ? "bg-[#232F3E] text-white" : "bg-slate-100 text-slate-700 hover:bg-slate-200"}`}><span className="sm:hidden">{short}</span><span className="hidden sm:inline">{label}</span></button>
        ))}
      </div>
      <div className="relative min-h-0 flex-1">
        {tab === "wilayah" ? <InklusiMap kategoriList={["kemiskinan"]} title="Peta Kemiskinan" metricOptions={KEMISKINAN_METRICS} /> : <PetaGIS />}
      </div>
    </div>
  );
}
