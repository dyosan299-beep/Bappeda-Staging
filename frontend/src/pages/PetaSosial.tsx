import React from "react";
import InklusiMap from "@/features/inklusi/InklusiMap";

/** Peta Sosial: pusat visualisasi Disabilitas | Stunting | ATS (drill-down kecamatan → kelurahan). */
export default function PetaSosial() {
  return (
    <div className="h-full w-full" data-testid="page-peta-sosial">
      <InklusiMap kategoriList={["disabilitas", "stunting", "ats"]} title="Peta Sosial" />
    </div>
  );
}
