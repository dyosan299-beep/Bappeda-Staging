/* Hook pengelola layer PETA DASAR agar dapat dipakai bersama oleh halaman
   Peta Rumah (memakai MapEngine) maupun Peta Sosial (Leaflet langsung). */
import { useCallback, useEffect, useMemo, useRef, useState } from "react";
import { toast } from "sonner";
import { fetchBasemapLayer, fetchBasemapLayers } from "./basemapApi";
import { BasemapFeatureCollection, BasemapLayerMeta } from "./basemapTypes";

export type LayerStatus = "kosong" | "memuat" | "tampil" | "perlu_zoom" | "gagal";

export interface BasemapRenderer {
  ready: boolean;
  viewTick: number;
  /** Aktifkan layer bawaan (batas kelurahan) saat pertama kali dibuka. */
  autoDefault?: boolean;
  getZoom: () => number;
  getBounds: () => number[] | null;
  setOverlay: (id: string, fc: BasemapFeatureCollection, meta: BasemapLayerMeta) => void;
  removeOverlay: (id: string) => void;
}

function padBox(b: number[], pad = 0.3): number[] {
  const w = (b[2] - b[0]) * pad;
  const h = (b[3] - b[1]) * pad;
  return [b[0] - w, b[1] - h, b[2] + w, b[3] + h];
}

function contains(outer: number[], inner: number[]): boolean {
  return (
    outer[0] <= inner[0] && outer[1] <= inner[1] && outer[2] >= inner[2] && outer[3] >= inner[3]
  );
}

function bboxString(b: number[]): string {
  return b.map((v) => v.toFixed(6)).join(",");
}

export function useBasemapLayers(renderer: BasemapRenderer) {
  const { ready, viewTick, autoDefault = true, getZoom, getBounds, setOverlay, removeOverlay } =
    renderer;

  const [layers, setLayers] = useState<BasemapLayerMeta[]>([]);
  const [sumber, setSumber] = useState("");
  const [aktif, setAktif] = useState<string[]>([]);
  const [status, setStatus] = useState<Record<string, LayerStatus>>({});
  const [jumlahTampil, setJumlahTampil] = useState<Record<string, number>>({});

  const cache = useRef<Record<string, BasemapFeatureCollection>>({});
  const lastBbox = useRef<Record<string, string>>({});
  const rendered = useRef<Record<string, string>>({});
  const inflight = useRef<Record<string, boolean>>({});

  /* muat manifest layer */
  useEffect(() => {
    let alive = true;
    (async () => {
      try {
        const res = await fetchBasemapLayers();
        if (!alive) return;
        setLayers(res.layers || []);
        setSumber(res.sumber || "");
        if (autoDefault) {
          const def = (res.layers || []).filter((l) => l.aktif_default).map((l) => l.id);
          if (def.length) setAktif(def);
        }
      } catch {
        if (alive) toast.error("Gagal memuat daftar layer peta dasar");
      }
    })();
    return () => {
      alive = false;
    };
  }, [autoDefault]);

  const metaById = useMemo(() => {
    const m: Record<string, BasemapLayerMeta> = {};
    layers.forEach((l) => {
      m[l.id] = l;
    });
    return m;
  }, [layers]);

  const grup = useMemo(() => {
    const out: { grup: string; items: BasemapLayerMeta[] }[] = [];
    layers.forEach((l) => {
      const found = out.find((g) => g.grup === l.grup);
      if (found) found.items.push(l);
      else out.push({ grup: l.grup, items: [l] });
    });
    return out;
  }, [layers]);

  const muatLayer = useCallback(
    async (id: string) => {
      const meta = metaById[id];
      if (!meta || inflight.current[id]) return;
      const zoom = getZoom();
      if (zoom < (meta.min_zoom || 0)) {
        removeOverlay(id);
        delete rendered.current[id];
        setStatus((s) => ({ ...s, [id]: "perlu_zoom" }));
        return;
      }
      const bbox: string | undefined = (() => {
        if (!meta.bbox_required) return undefined;
        const cur = getBounds();
        if (!cur || cur.length !== 4) return undefined;
        const prev = lastBbox.current[id];
        // area yang sudah diambil masih mencakup tampilan sekarang -> pakai lagi
        if (prev && rendered.current[id] && contains(prev.split(",").map(Number), cur)) {
          return prev;
        }
        return bboxString(padBox(cur, 0.3));
      })();
      if (meta.bbox_required && !bbox) return;
      const key = bbox || "full";
      // sudah tergambar untuk kunci yang sama -> tidak perlu apa-apa
      if (rendered.current[id] === key) {
        setStatus((s) => (s[id] === "tampil" ? s : { ...s, [id]: "tampil" }));
        return;
      }
      if (!meta.bbox_required && cache.current[id]) {
        setOverlay(id, cache.current[id], meta);
        rendered.current[id] = key;
        setStatus((s) => ({ ...s, [id]: "tampil" }));
        setJumlahTampil((s) => ({ ...s, [id]: cache.current[id].count || 0 }));
        return;
      }
      inflight.current[id] = true;
      setStatus((s) => ({ ...s, [id]: "memuat" }));
      try {
        const fc = await fetchBasemapLayer(id, bbox ? { bbox } : {});
        cache.current[id] = fc;
        if (bbox) lastBbox.current[id] = bbox;
        setOverlay(id, fc, meta);
        rendered.current[id] = key;
        setStatus((s) => ({ ...s, [id]: "tampil" }));
        setJumlahTampil((s) => ({ ...s, [id]: fc.count || 0 }));
      } catch {
        setStatus((s) => ({ ...s, [id]: "gagal" }));
        toast.error(`Gagal memuat layer ${meta.label}`);
      } finally {
        inflight.current[id] = false;
      }
    },
    [metaById, getBounds, getZoom, removeOverlay, setOverlay],
  );

  /* mesin peta dibuat ulang -> semua overlay hilang, tandai perlu digambar lagi */
  useEffect(() => {
    rendered.current = {};
  }, [ready]);

  /* muat / perbarui layer aktif setiap perubahan tampilan peta */
  useEffect(() => {
    if (!ready) return;
    const t = setTimeout(() => {
      aktif.forEach((id) => muatLayer(id));
    }, 250);
    return () => clearTimeout(t);
  }, [ready, aktif, viewTick, muatLayer]);

  const toggle = useCallback(
    (id: string) => {
      setAktif((cur) => {
        if (cur.includes(id)) {
          removeOverlay(id);
          delete rendered.current[id];
          setStatus((s) => ({ ...s, [id]: "kosong" }));
          return cur.filter((x) => x !== id);
        }
        return [...cur, id];
      });
    },
    [removeOverlay],
  );

  const matikanSemua = useCallback(() => {
    aktif.forEach((id) => {
      removeOverlay(id);
      delete rendered.current[id];
    });
    setAktif([]);
    setStatus({});
  }, [aktif, removeOverlay]);

  return { layers, grup, metaById, aktif, status, jumlahTampil, sumber, toggle, matikanSemua };
}
