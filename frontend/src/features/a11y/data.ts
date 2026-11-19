import { useEffect, useState } from "react";
import api from "@/lib/api";

/** Cache tingkat modul: data publik agregat untuk narasi aksesibilitas (sekali ambil per kunjungan). */
const cache: Record<string, Promise<any> | undefined> = {};
const ambil = (url: string) => {
  if (!cache[url]) cache[url] = api.get(url).then((r) => r.data).catch(() => { cache[url] = undefined; return null; });
  return cache[url] as Promise<any>;
};

export function resetBisindoCache() { cache["/public/a11y/bisindo"] = undefined; }

export function usePublicA11yData() {
  const [d, setD] = useState<{ s: any; st: any; bisindo: any }>({ s: null, st: null, bisindo: null });
  useEffect(() => {
    let aktif = true;
    Promise.all([ambil("/public/summary"), ambil("/public/stunting/breakdown"), ambil("/public/a11y/bisindo")])
      .then(([s, st, bisindo]) => { if (aktif) setD({ s, st, bisindo }); });
    return () => { aktif = false; };
  }, []);
  return d;
}

export type HalamanKey = "beranda" | "publik" | "peta_sosial" | "peta_kemiskinan";

export function halamanDariPath(path: string): HalamanKey | null {
  const p = path.replace(/\/+$/, "") || "/";
  if (p === "/") return "beranda";
  if (p === "/publik") return "publik";
  if (p === "/publik/peta-sosial") return "peta_sosial";
  if (p === "/publik/peta-kemiskinan") return "peta_kemiskinan";
  return null;
}
