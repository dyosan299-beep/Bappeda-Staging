import React from "react";
import { useLocation } from "react-router-dom";
import { useA11y } from "@/context/AccessibilityContext";
import { EasyRead } from "./components";
import { halamanDariPath, usePublicA11yData } from "./data";
import { buatNarasi } from "./narasi";

/** Menampilkan panel Bahasa Mudah di atas konten bila mode aktif (fitur H). */
export default function EasyReadAuto() {
  const { easyMode } = useA11y();
  const loc = useLocation();
  const { s, st } = usePublicA11yData();
  if (!easyMode) return null;
  const nr = buatNarasi(halamanDariPath(loc.pathname), s, st);
  if (!nr || !nr.mudah.length) return null;
  return <EasyRead items={nr.mudah} judul={nr.judul} />;
}
