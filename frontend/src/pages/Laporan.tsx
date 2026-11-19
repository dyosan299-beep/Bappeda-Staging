import React, { useMemo, useState } from "react";
import { ClipboardList, FileDown } from "lucide-react";
import { useAuth } from "@/context/AuthContext";
import Rekap from "@/pages/Rekap";
import { LaporanWilayah } from "@/features/inklusi/InklusiExtra";
import { PageTabs, TabPanel } from "@/components/PageTabs";

/** Peran yang boleh melihat rekap lintas kategori (sama dengan penjaga rute /rekap). */
const REKAP_ROLES = ["superadmin", "admin", "pimpinan"];

/**
 * Pusat laporan: satu pintu masuk untuk rekap data dan laporan wilayah (PDF).
 * Setiap tab memakai halaman lama apa adanya, sehingga isi, filter, dan hak
 * aksesnya tidak berubah. Rute lama /rekap dan /laporan-wilayah tetap hidup.
 */
export default function Laporan() {
  const { user } = useAuth();
  const bolehRekap = REKAP_ROLES.includes(user?.role);

  const tabs = useMemo(() => {
    const t = [];
    if (bolehRekap) t.push({ id: "rekap", label: "Rekap Data", icon: ClipboardList });
    t.push({ id: "wilayah", label: "Laporan Wilayah", icon: FileDown });
    return t;
  }, [bolehRekap]);

  const [pilih, setPilih] = useState("");
  const aktif = tabs.some((t) => t.id === pilih) ? pilih : tabs[0]?.id;

  return (
    <div data-testid="laporan-hub">
      <PageTabs tabs={tabs} value={aktif} onChange={setPilih} label="Jenis laporan" />
      <TabPanel id={aktif}>
        {aktif === "rekap" ? <Rekap /> : <LaporanWilayah />}
      </TabPanel>
    </div>
  );
}
