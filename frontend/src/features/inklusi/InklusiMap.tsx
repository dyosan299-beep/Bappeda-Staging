import React, { useCallback, useEffect, useMemo, useRef, useState } from "react";
import L from "leaflet";
import "leaflet/dist/leaflet.css";
import { useNavigate } from "react-router-dom";
import { Search, RotateCcw, Loader2, MapPin, Send, Info, FileDown, SlidersHorizontal, ChevronUp } from "lucide-react";
import { downloadLaporanKelurahan } from "./download";
import api from "@/lib/api";
import { KATEGORI_META, Kategori, normWil, fmt } from "./theme";
import { BTN_OUTLINE_NAVY, BTN_OUTLINE_TEAL, BTN_SM, BTN_SM_PRIMARY, FR, SEG } from "@/features/a11y/ui";
import VervalMapLayer from "@/features/verval/VervalMapLayer";
import { ensureLeafletSafe, isMapAlive, safeRemoveMap } from "@/lib/leafletSafe";

ensureLeafletSafe();

type Level = "kecamatan" | "kelurahan";
interface Props {
  kategoriList: Kategori[];
  initial?: Kategori;
  publicMode?: boolean;
  title?: string;
  metricOptions?: { id: string; label: string }[]; // untuk kemiskinan (indikator detail kelurahan)
}

const MAKASSAR: [number, number] = [-5.147, 119.44];

export default function InklusiMap({ kategoriList, initial, publicMode = false, title, metricOptions }: Props) {
  const navigate = useNavigate();
  const divRef = useRef<HTMLDivElement | null>(null);
  const mapRef = useRef<L.Map | null>(null);
  const polyRef = useRef<L.GeoJSON | null>(null);
  const markRef = useRef<L.LayerGroup | null>(null);
  const searchTimerRef = useRef<number | null>(null);
  const [kategori, setKategori] = useState<Kategori>(initial || kategoriList[0]);
  const [level, setLevel] = useState<Level>("kecamatan");
  const [kec, setKec] = useState("");
  const [metric, setMetric] = useState("value");
  const [geo, setGeo] = useState<any>(null);
  const [data, setData] = useState<any>(null);
  const [loading, setLoading] = useState(true);
  const [selected, setSelected] = useState<any>(null);
  const [showMarker, setShowMarker] = useState(true);
  const [q, setQ] = useState("");
  const [mapReady, setMapReady] = useState(false);
  // Panel filter/legenda: selalu tampil di >=768px; di HP dapat diciutkan agar peta terlihat.
  const [panelOpen, setPanelOpen] = useState<boolean>(() =>
    typeof window === "undefined" || !window.matchMedia ? true : window.matchMedia("(min-width: 768px)").matches);
  const meta = KATEGORI_META[kategori];

  useEffect(() => {
    if (!divRef.current || mapRef.current) return;
    const map = L.map(divRef.current, { center: MAKASSAR, zoom: 12 });
    // Panel filter menempati kiri-atas: pindahkan kontrol zoom ke kanan-atas agar tidak tertutup
    map.zoomControl.setPosition("topright");
    // Leaflet memberi label bahasa Inggris pada tombol zoom; lokalkan agar konsisten
    // dengan antarmuka dan jelas bagi pembaca layar (WCAG 3.2.4, 2.5.3).
    const zoomBox = map.zoomControl.getContainer();
    if (zoomBox) {
      const tombol = zoomBox.querySelectorAll("a");
      const labelZoom = ["Perbesar peta", "Perkecil peta"];
      tombol.forEach((a, i) => {
        const teks = labelZoom[i] || "Perbesar atau perkecil peta";
        a.setAttribute("aria-label", teks);
        a.setAttribute("title", teks);
      });
    }
    const osm = L.tileLayer("https://tile.openstreetmap.org/{z}/{x}/{y}.png", { maxZoom: 19, attribution: "&copy; OpenStreetMap" });
    osm.addTo(map);
    mapRef.current = map;
    setMapReady(true);
    // Hitung ulang ukuran peta saat kontainer berubah (sidebar, rotasi layar, resize jendela)
    let ro: ResizeObserver | null = null;
    if (typeof ResizeObserver !== "undefined" && divRef.current) {
      ro = new ResizeObserver(() => {
        if (!isMapAlive(map)) return;
        try { map.invalidateSize({ pan: false }); } catch { /* noop */ }
      });
      ro.observe(divRef.current);
    }
    // Google basemap: tambahkan jika API key tersedia (via /api/map/config).
    const baseLayers: Record<string, L.TileLayer> = { "OpenStreetMap": osm };
    let cancelled = false;
    let layersCtrl: L.Control.Layers | null = null;
    const addCtrl = () => {
      if (cancelled || !isMapAlive(mapRef.current)) return;
      layersCtrl = L.control.layers(baseLayers).addTo(mapRef.current);
    };
    api.get("/map/config").then((r) => {
      if (cancelled || !isMapAlive(mapRef.current)) return;
      const key = (r.data?.google_maps_api_key || "").trim();
      if (key) {
        // Tile URL Google (lyrs: m=road, s=satellite, y=hybrid). Key dilewatkan untuk billing/kuota.
        const gOpts = (lyrs: string) => L.tileLayer(
          `https://mt{s}.google.com/vt/lyrs=${lyrs}&x={x}&y={y}&z={z}&key=${encodeURIComponent(key)}`,
          { subdomains: ["0", "1", "2", "3"], maxZoom: 20, attribution: "&copy; Google Maps" },
        );
        baseLayers["Google Road"] = gOpts("m");
        baseLayers["Google Satellite"] = gOpts("s");
        baseLayers["Google Hybrid"] = gOpts("y");
      }
      addCtrl();
    }).catch(() => { addCtrl(); });
    return () => {
      cancelled = true;
      if (searchTimerRef.current !== null) {
        window.clearTimeout(searchTimerRef.current);
        searchTimerRef.current = null;
      }
      try { ro?.disconnect(); } catch { /* noop */ }
      try { layersCtrl?.remove(); } catch { /* noop */ }
      safeRemoveMap(map);
      mapRef.current = null;
      setMapReady(false);
    };
  }, []);

  useEffect(() => {
    api.get("/geo/kelurahan", { params: { metric: "total_households" } }).then((r) => setGeo(r.data)).catch(() => setGeo({ features: [] }));
  }, []);

  const load = useCallback(async () => {
    setLoading(true);
    try {
      const url = publicMode ? `/public/map/${kategori}` : `/inklusi/map/${kategori}`;
      const r = await api.get(url, { params: { level } });
      setData(r.data);
    } catch { setData({ items: [], total: 0 }); } finally { setLoading(false); }
  }, [kategori, level, publicMode]);
  useEffect(() => { load(); setSelected(null); }, [load]);
  useEffect(() => { setMetric("value"); }, [kategori]);

  const index = useMemo(() => {
    const m: Record<string, any> = {};
    (data?.items || []).forEach((i: any) => { m[level === "kecamatan" ? normWil(i.kecamatan) : normWil(i.kelurahan)] = i; });
    return m;
  }, [data, level]);

  const kecList = useMemo(() => {
    const s = new Set<string>();
    (geo?.features || []).forEach((f: any) => s.add(f.properties.kecamatan));
    return Array.from(s).filter(Boolean).sort();
  }, [geo]);

  const valueOf = useCallback((item: any) => {
    if (!item) return 0;
    if (metric === "value") return Number(item.value || 0);
    return Number(item.detail?.[metric] || 0);
  }, [metric]);

  const features = useMemo(() => (geo?.features || []).filter((f: any) => !kec || f.properties.kecamatan === kec), [geo, kec]);
  const itemFor = useCallback((f: any) => index[level === "kecamatan" ? normWil(f.properties.kecamatan) : normWil(f.properties.kelurahan)], [index, level]);
  const max = useMemo(() => Math.max(1, ...features.map((f: any) => valueOf(itemFor(f)))), [features, itemFor, valueOf]);
  const color = useCallback((v: number) => {
    if (!v) return "#E2E8F0";
    return meta.ramp[Math.min(meta.ramp.length - 1, Math.floor((v / max) * meta.ramp.length))];
  }, [max, meta]);

  // render polygon + marker
  useEffect(() => {
    const map = mapRef.current;
    if (!isMapAlive(map) || !geo) return;
    polyRef.current?.remove();
    markRef.current?.remove();
    const layer = L.geoJSON({ type: "FeatureCollection", features } as any, {
      style: (f: any) => {
        const v = valueOf(itemFor(f));
        return { fillColor: color(v), fillOpacity: v ? 0.78 : 0.3, color: level === "kecamatan" ? "#475569" : "#64748B", weight: level === "kecamatan" ? 0.6 : 1 };
      },
      onEachFeature: (f: any, lyr: any) => {
        const it = itemFor(f);
        const nama = level === "kecamatan" ? `Kec. ${f.properties.kecamatan}` : `${f.properties.kelurahan} (Kec. ${f.properties.kecamatan})`;
        lyr.bindTooltip(`<b>${nama}</b><br/>${meta.label}: <b>${it ? fmt(valueOf(it)) : "belum ada data"}</b>`, { sticky: true });
        lyr.on("click", () => {
          setSelected({ nama, kecamatan: f.properties.kecamatan, kelurahan: level === "kelurahan" ? f.properties.kelurahan : "", item: it });
        });
      },
    }).addTo(map);
    polyRef.current = layer;
    if (showMarker) {
      const g = L.layerGroup();
      const done = new Set<string>();
      features.forEach((f: any) => {
        const key = level === "kecamatan" ? f.properties.kecamatan : f.properties.kelurahan;
        const v = valueOf(itemFor(f));
        if (!v || done.has(key)) return;
        done.add(key);
        let c: L.LatLng;
        if (level === "kecamatan") {
          const fs = features.filter((x: any) => x.properties.kecamatan === key);
          c = L.geoJSON({ type: "FeatureCollection", features: fs } as any).getBounds().getCenter();
        } else c = L.geoJSON(f).getBounds().getCenter();
        L.circleMarker(c, { radius: 5 + 14 * Math.sqrt(v / max), color: "#fff", weight: 1.5, fillColor: meta.warna, fillOpacity: 0.85 })
          .bindTooltip(`${key}: <b>${fmt(v)}</b>`).addTo(g);
      });
      g.addTo(map);
      markRef.current = g;
    }
    try {
      if (features.length && isMapAlive(map)) {
        // Tanpa filter kecamatan: fokus ke daratan kota (pulau-pulau Sangkarrang membuat zoom terlalu jauh)
        const main = kec ? features : features.filter((f: any) => L.geoJSON(f).getBounds().getCenter().lng > 119.38);
        const b = L.geoJSON({ type: "FeatureCollection", features: main.length ? main : features } as any).getBounds();
        const isWide = typeof window !== "undefined" && window.matchMedia && window.matchMedia("(min-width: 768px)").matches;
        map.fitBounds(b, {
          paddingTopLeft: isWide ? [316, 20] : [20, 60],
          paddingBottomRight: [20, 20],
          animate: false,
        });
      }
    } catch { /* */ }
    // eslint-disable-next-line react-hooks/exhaustive-deps
  }, [geo, features, index, metric, showMarker, kategori]);

  const drillDown = (kecamatan: string) => { setKec(kecamatan); setLevel("kelurahan"); setSelected(null); };
  const reset = () => { setKec(""); setLevel("kecamatan"); setQ(""); setSelected(null); setMetric("value"); };

  const cari = (e: React.FormEvent) => {
    e.preventDefault();
    const n = normWil(q);
    if (!n) return;
    const f = (geo?.features || []).find((x: any) => normWil(x.properties.kelurahan) === n) ||
      (geo?.features || []).find((x: any) => normWil(x.properties.kelurahan).includes(n));
    const kc = kecList.find((k) => normWil(k) === n || normWil(k).includes(n));
    if (f && (!kc || normWil(f.properties.kelurahan) === n)) {
      setLevel("kelurahan"); setKec(f.properties.kecamatan);
      if (searchTimerRef.current !== null) window.clearTimeout(searchTimerRef.current);
      searchTimerRef.current = window.setTimeout(() => {
        searchTimerRef.current = null;
        if (isMapAlive(mapRef.current)) {
          mapRef.current.fitBounds(L.geoJSON(f).getBounds(), { maxZoom: 15, animate: false });
        }
        const it = (data?.items || []).find((i: any) => normWil(i.kelurahan) === normWil(f.properties.kelurahan));
        setSelected({ nama: `${f.properties.kelurahan} (Kec. ${f.properties.kecamatan})`, kecamatan: f.properties.kecamatan, kelurahan: f.properties.kelurahan, item: it });
      }, 400);
    } else if (kc) { drillDown(kc); }
  };

  const ajukan = () => {
    const p = new URLSearchParams({ kategori: meta.inquiry, kecamatan: selected?.kecamatan || "", kelurahan: selected?.kelurahan || "",
      nilai: String(valueOf(selected?.item) || ""), indikator: metric === "value" ? meta.label : metric });
    const target = `/ngo/inquiry/baru?${p.toString()}`;
    navigate(publicMode ? `/login?mode=ngo&next=${encodeURIComponent(target)}` : target);
  };

  const [pdfBusy, setPdfBusy] = useState(false);
  const unduhPdf = async () => {
    if (!selected?.kelurahan) return;
    setPdfBusy(true);
    await downloadLaporanKelurahan(selected.kecamatan, selected.kelurahan);
    setPdfBusy(false);
  };

  const ranking = (data?.items || []).filter((i: any) => !kec || i.kecamatan === kec).slice(0, 8);
  // Di HP: setelah memilih wilayah dari ranking, ciutkan panel agar hasil terlihat di peta
  const autoCollapse = () => { if (window.matchMedia && !window.matchMedia("(min-width: 768px)").matches) setPanelOpen(false); };
  const semuaNama = useMemo(() => Array.from(new Set<string>([...kecList, ...(geo?.features || []).map((f: any) => f.properties.kelurahan)].filter(Boolean))), [kecList, geo]);

  return (
    <div className={`relative w-full ${publicMode ? "h-full min-h-[380px]" : "h-full min-h-[320px] sm:min-h-[480px] lg:min-h-[560px]"}`} data-testid="inklusi-map">
      <p id="peta-panduan-keyboard" className="sr-only">
        Peta dapat dioperasikan tanpa tetikus: fokuskan peta lalu gunakan tombol panah untuk menggeser,
        tombol plus dan minus untuk memperbesar atau memperkecil, dan tombol Esc untuk berhenti menggeser.
        Daftar wilayah dan tabel data tersedia pada panel di samping peta.
      </p>
      <div ref={divRef} className="absolute inset-0 z-0" role="application" aria-describedby="peta-panduan-keyboard" aria-label={`Peta ${meta.label} Kota Makassar`} data-testid="inklusi-map-canvas" />
      {mapReady && !publicMode && <VervalMapLayer map={mapRef.current} />}

      {/* Tombol buka panel (khusus HP) */}
      {!panelOpen && (
        <button type="button" onClick={() => setPanelOpen(true)} data-testid="map-panel-open"
          aria-controls="map-panel" aria-expanded={false}
          className={`absolute left-3 top-3 z-[500] inline-flex min-h-11 max-w-[calc(100%-5rem)] items-center gap-2 rounded-full bg-white px-4 py-2 text-xs font-bold text-[#232F3E] shadow-[0_10px_30px_rgba(35,47,62,.22)] ring-1 ring-slate-200 md:hidden ${FR}`}>
          <SlidersHorizontal className="h-4 w-4 shrink-0 text-[#117A69]" aria-hidden="true" />
          <span className="truncate">Filter & Legenda · {meta.label}</span>
          <span className="shrink-0 rounded-full bg-slate-100 px-2 py-0.5 text-[10px]">{fmt(data?.total)}</span>
        </button>
      )}

      <div id="map-panel" className={`absolute inset-x-2 top-2 z-[500] max-h-[calc(100%-1rem)] flex-col gap-2 overflow-y-auto overscroll-contain sm:inset-x-auto sm:left-3 sm:top-3 sm:max-h-[calc(100%-1.5rem)] sm:w-[300px] sm:max-w-[calc(100%-1.5rem)] md:flex ${panelOpen ? "flex" : "hidden"}`}>
        <div className="rounded-[16px] bg-white/95 p-3.5 shadow-[0_18px_50px_rgba(35,47,62,.18)] ring-1 ring-slate-200 backdrop-blur">
          <div className="mb-2 flex items-center justify-between gap-2">
            {title ? <h2 className="min-w-0 font-head text-sm font-extrabold text-[#232F3E]">{title}</h2> : <span />}
            <button type="button" onClick={() => setPanelOpen(false)} data-testid="map-panel-close"
              aria-label="Ciutkan panel filter untuk melihat peta" aria-controls="map-panel" aria-expanded={true}
              className={`inline-flex h-10 shrink-0 items-center gap-1 rounded-full bg-slate-100 px-3 text-[11px] font-bold text-slate-700 hover:bg-slate-200 md:hidden ${FR}`}>
              <ChevronUp className="h-4 w-4" aria-hidden="true" /> Lihat peta
            </button>
          </div>
          {kategoriList.length > 1 && (
            <div role="tablist" aria-label="Kategori data" className="mb-2 grid grid-cols-3 gap-1 rounded-full bg-slate-100 p-1 ring-1 ring-slate-200">
              {kategoriList.map((k) => (
                <button key={k} role="tab" aria-selected={kategori === k} type="button" data-testid={`map-tab-${k}`}
                  onClick={() => setKategori(k)}
                  className={`min-h-9 rounded-full px-1.5 py-1.5 text-[11px] font-bold transition-colors ${FR} ${kategori === k ? "text-white shadow-sm" : "text-slate-600 hover:bg-white hover:text-slate-900"}`}
                  style={kategori === k ? { backgroundColor: KATEGORI_META[k].warna } : undefined}>
                  {k === "ats" ? "ATS" : KATEGORI_META[k].label}
                </button>
              ))}
            </div>
          )}
          <div className={`${SEG} grid-cols-2`} role="group" aria-label="Tingkat wilayah">
            {(["kecamatan", "kelurahan"] as Level[]).map((lv) => (
              <button key={lv} type="button" data-testid={`map-level-${lv}`} aria-pressed={level === lv}
                onClick={() => { setLevel(lv); setSelected(null); }}
                className={`min-h-9 rounded-full px-2 py-1.5 text-xs font-semibold transition-colors ${FR} ${level === lv ? "bg-[#232F3E] text-white shadow-sm" : "text-slate-600 hover:bg-white hover:text-slate-900"}`}>
                {lv === "kecamatan" ? "Kecamatan" : "Kelurahan"}
              </button>
            ))}
          </div>
          <label className="sr-only" htmlFor="filter-kec">Filter kecamatan</label>
          <select id="filter-kec" data-testid="map-filter-kecamatan" value={kec} onChange={(e) => { setKec(e.target.value); setSelected(null); }}
            className={`mt-2 h-10 w-full rounded-[10px] border border-slate-200 bg-white px-2.5 text-xs font-medium transition-colors hover:border-slate-300 ${FR}`}>
            <option value="">Semua Kecamatan</option>
            {kecList.map((k) => <option key={k} value={k}>{k}</option>)}
          </select>
          {metricOptions && level === "kelurahan" && (
            <>
              <label className="sr-only" htmlFor="filter-metric">Indikator</label>
              <select id="filter-metric" data-testid="map-metric" value={metric} onChange={(e) => setMetric(e.target.value)}
                className={`mt-2 h-10 w-full rounded-[10px] border border-slate-200 bg-white px-2.5 text-xs font-medium transition-colors hover:border-slate-300 ${FR}`}>
                {metricOptions.map((m) => <option key={m.id} value={m.id}>{m.label}</option>)}
              </select>
            </>
          )}
          <form onSubmit={cari} className="mt-2 flex gap-1" role="search">
            <label htmlFor="cari-wil" className="sr-only">Cari kecamatan atau kelurahan</label>
            <input id="cari-wil" list="daftar-wilayah" value={q} onChange={(e) => setQ(e.target.value)} placeholder="Cari kecamatan/kelurahan…"
              data-testid="map-search-input" className={`h-10 min-w-0 flex-1 rounded-[10px] border border-slate-200 px-2.5 text-xs transition-colors hover:border-slate-300 ${FR}`} />
            <datalist id="daftar-wilayah">{semuaNama.map((n: string) => <option key={n} value={n} />)}</datalist>
            <button type="submit" aria-label="Cari wilayah" data-testid="map-search-btn" className={`inline-flex h-10 w-10 shrink-0 items-center justify-center rounded-[10px] bg-[#117A69] text-white transition-colors hover:bg-[#0B4F45] ${FR}`}><Search className="h-4 w-4" /></button>
            <button type="button" aria-label="Reset filter" onClick={reset} data-testid="map-reset-btn" className={`inline-flex h-10 w-10 shrink-0 items-center justify-center rounded-[10px] bg-white text-slate-700 ring-1 ring-slate-200 transition-colors hover:bg-slate-50 ${FR}`}><RotateCcw className="h-4 w-4" /></button>
          </form>
          <label className="mt-2 flex items-center gap-2 text-xs text-slate-700">
            <input type="checkbox" checked={showMarker} onChange={(e) => setShowMarker(e.target.checked)} data-testid="map-marker-toggle" /> Tampilkan marker proporsional
          </label>
          <div className="mt-3" aria-label="Legenda">
            <p className="text-[10px] font-bold uppercase tracking-wide text-slate-600">Legenda — {meta.label} ({data?.satuan || meta.satuan})</p>
            <div className="mt-1 flex overflow-hidden rounded">{meta.ramp.map((c) => <span key={c} className="h-3 flex-1" style={{ backgroundColor: c }} />)}</div>
            <div className="flex justify-between text-[10px] text-slate-600"><span>rendah</span><span>{fmt(Math.round(max))}</span></div>
            <p className="mt-1 flex items-center gap-1 text-[10px] text-slate-600"><span className="inline-block h-2.5 w-2.5 rounded-sm bg-slate-200" /> abu-abu = belum ada data</p>
          </div>
          <p className="mt-2 rounded bg-slate-50 p-2 text-[10.5px] leading-snug text-slate-600" data-testid="map-source">
            {loading ? <Loader2 className="inline h-3 w-3 animate-spin" /> : <Info className="inline h-3 w-3" />} Sumber: {data?.sumber || "-"}
          </p>
          {data?.catatan && <p className="mt-1 rounded bg-amber-50 p-2 text-[10.5px] text-amber-900" data-testid="map-note">{data.catatan}</p>}
        </div>

        <div className="rounded-[16px] bg-white/95 p-3.5 shadow-[0_18px_50px_rgba(35,47,62,.18)] ring-1 ring-slate-200 backdrop-blur">
          <p className="text-[10px] font-bold uppercase tracking-wide text-slate-600">
            Total {level === "kecamatan" ? "kota" : "terdata"}: <span className="text-sm text-slate-900">{fmt(data?.total)}</span>
          </p>
          <ol className="mt-2 space-y-1" data-testid="map-ranking">
            {ranking.map((r: any, i: number) => (
              <li key={i}>
                <button type="button" onClick={() => { if (level === "kecamatan") { drillDown(r.kecamatan); } else { setSelected({ nama: `${r.kelurahan} (Kec. ${r.kecamatan})`, kecamatan: r.kecamatan, kelurahan: r.kelurahan, item: r }); autoCollapse(); } }}
                  className={`flex min-h-10 w-full gap-2 items-center justify-between rounded-[8px] px-2 py-1 text-left text-xs transition-colors hover:bg-slate-100 ${FR}`}>
                  <span className="truncate">{i + 1}. {level === "kecamatan" ? r.kecamatan : r.kelurahan}</span>
                  <span className="font-bold" style={{ color: meta.warna }}>{fmt(valueOf(r))}</span>
                </button>
              </li>
            ))}
            {!ranking.length && <li className="text-xs text-slate-500">Belum ada data untuk pilihan ini.</li>}
          </ol>
          {level === "kecamatan" && ranking.length > 0 && <p className="mt-1 text-[10px] text-slate-500">Klik kecamatan untuk drill-down ke kelurahan.</p>}
        </div>
      </div>

      {selected && (
        <aside className="absolute inset-x-2 bottom-2 z-[600] max-h-[60%] overflow-y-auto overscroll-contain rounded-[16px] bg-white p-4 sm:inset-x-auto sm:bottom-3 sm:right-3 sm:w-[340px] sm:max-w-[calc(100%-1.5rem)] md:max-h-[calc(100%-1.5rem)] shadow-[0_24px_60px_rgba(35,47,62,.22)] ring-1 ring-slate-200 md:bottom-auto md:top-3"
          data-testid="map-detail" aria-live="polite">
          <div className="flex items-start justify-between gap-2">
            <div>
              <p className="text-[10px] font-bold uppercase tracking-wide" style={{ color: meta.warna }}>{meta.label}</p>
              <h3 className="font-head text-base font-extrabold text-slate-900"><MapPin className="mr-1 inline h-4 w-4" />{selected.nama}</h3>
            </div>
            <button type="button" onClick={() => setSelected(null)} className={BTN_SM} data-testid="map-detail-close">Tutup</button>
          </div>
          {selected.item ? (
            <dl className="mt-2 space-y-1 text-xs">
              <div className="flex justify-between border-b border-dashed py-1"><dt className="text-slate-600">Jumlah ({data?.satuan})</dt><dd className="font-bold">{fmt(selected.item.value)}</dd></div>
              {Object.entries(selected.item.detail || {}).filter(([, v]) => v !== null && v !== undefined && v !== "").map(([k, v]) => (
                <div key={k} className="flex justify-between border-b border-dashed py-1"><dt className="capitalize text-slate-600">{k.replace(/_/g, " ")}</dt><dd className="font-semibold">{typeof v === "number" && k !== "tahun" ? fmt(v) : String(v)}</dd></div>
              ))}
            </dl>
          ) : (
            <p className="mt-2 rounded bg-amber-50 p-2 text-xs text-amber-900">Belum ada data {meta.label.toLowerCase()} untuk wilayah ini pada tingkat {level}.</p>
          )}
          <div className="mt-4 flex flex-wrap gap-2 border-t border-slate-100 pt-3">
            {level === "kecamatan" && (
              <button type="button" onClick={() => drillDown(selected.kecamatan)} data-testid="map-drilldown-btn"
                className={BTN_OUTLINE_NAVY}>Lihat kelurahan</button>
            )}
            <button type="button" onClick={ajukan} data-testid="map-ajukan-btn"
              className={BTN_SM_PRIMARY}>
              <Send className="h-3.5 w-3.5" /> Ajukan Program Intervensi {kategori === "ats" ? "ATS" : meta.label}
            </button>
            {!publicMode && selected.kelurahan && (
              <button type="button" onClick={unduhPdf} disabled={pdfBusy} data-testid="map-pdf-btn"
                className={BTN_OUTLINE_TEAL}>
                {pdfBusy ? <Loader2 className="h-3.5 w-3.5 animate-spin" /> : <FileDown className="h-3.5 w-3.5" />} Laporan PDF Kelurahan
              </button>
            )}
          </div>
        </aside>
      )}
    </div>
  );
}
