import React, { useMemo, useState } from "react";
import { Database, Upload } from "lucide-react";
import { useAuth } from "@/context/AuthContext";
import { WRITERS } from "@/constants/roles";
import ImportWizard from "@/pages/ImportWizard";
import Administrasi from "@/pages/Administrasi";
import { PageTabs, TabPanel } from "@/components/PageTabs";

/**
 * Satu pintu masuk untuk impor dan kualitas data (SOP 05–06).
 * Wizard impor menempati tab pertama bila peran pengguna memang boleh mengimpor;
 * riwayat, pratinjau batch, dan temuan kualitas tetap seperti halaman lama.
 * Rute lama /impor dan /administrasi tetap hidup.
 */
export default function ImporKualitas() {
  const { user } = useAuth();
  const bolehImpor = WRITERS.includes(user?.role);

  const tabs = useMemo(() => {
    const t = [];
    if (bolehImpor) t.push({ id: "impor", label: "Impor Baru", icon: Upload });
    t.push({ id: "kualitas", label: "Riwayat & Kualitas", icon: Database });
    return t;
  }, [bolehImpor]);

  const [pilih, setPilih] = useState("");
  const aktif = tabs.some((t) => t.id === pilih) ? pilih : tabs[0]?.id;

  return (
    <div data-testid="impor-kualitas-hub">
      <PageTabs tabs={tabs} value={aktif} onChange={setPilih} label="Bagian impor dan kualitas data" />
      <TabPanel id={aktif}>
        {aktif === "impor" ? <ImportWizard /> : <Administrasi />}
      </TabPanel>
    </div>
  );
}
