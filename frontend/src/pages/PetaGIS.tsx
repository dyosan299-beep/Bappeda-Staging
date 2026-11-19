import React, { useCallback, useEffect, useMemo, useRef, useState } from "react";
import { createPortal } from "react-dom";
import {
  Layers,
  Loader2,
  Maximize2,
  Minus,
  Plus,
  RefreshCw,
  Home,
  Info,
} from "lucide-react";
import { toast } from "sonner";
import { BASEMAPS, fallbackBasemap, isGoogleBasemap, STATUS_COLORS, STATUS_LABEL } from "@/features/peta/basemaps";
import { fetchFilters, fetchGeoJSON, fetchMapConfig, fetchStats } from "@/features/peta/api";
import { createLeafletEngine } from "@/features/peta/leafletEngine";
import { createGoogleEngine } from "@/features/peta/googleEngine";
import RumahPopup from "@/features/peta/RumahPopup";
import BasemapLayerPanel from "@/features/peta/BasemapLayerPanel";
import { useBasemapLayers } from "@/features/peta/useBasemapLayers";
import { useVervalPeta } from "@/features/verval/VervalMapLayer";
import { STATUS_COLOR as VERVAL_STATUS_COLOR } from "@/features/verval/api";
import {
  BasemapId,
  MapConfig,
  MapEngine,
  Pixel,
  RumahFeatureCollection,
  RumahFilters,
  RumahProps,
  RumahStats,
} from "@/features/peta/types";

const SEMUA = "semua";

export default function PetaGIS() {
  const wrapperRef = useRef<HTMLDivElement | null>(null);
  const mapDivRef = useRef<HTMLDivElement | null>(null);
  const engineRef = useRef<MapEngine | null>(null);
  // Setelah Google gagal dimuat sekali (mis. kunci dibatasi domain), jangan dicoba lagi
  // pada halaman ini agar peta tidak berkedip gagal berulang kali.
  const googleGagalRef = useRef(false);

  const [config, setConfig] = useState<MapConfig | null>(null);
  const [filters, setFilters] = useState<RumahFilters | null>(null);
  const [pendingKel, setPendingKel] = useState<string>(SEMUA);
  const [pendingRw, setPendingRw] = useState<string>(SEMUA);
  const [applied, setApplied] = useState<{ kelurahan: string; rw: string }>({
    kelurahan: SEMUA,
    rw: SEMUA,
  });
  const [statusFilter, setStatusFilter] = useState<string>(SEMUA);
  const [basemap, setBasemap] = useState<BasemapId>("esri_hybrid");
  const [fc, setFc] = useState<RumahFeatureCollection | null>(null);
  const [stats, setStats] = useState<RumahStats | null>(null);
  const [selected, setSelected] = useState<RumahProps | null>(null);
  const [pixel, setPixel] = useState<Pixel | null>(null);
  const [engineReady, setEngineReady] = useState(0);
  const [googleGagal, setGoogleGagal] = useState(false);
  const [loadingData, setLoadingData] = useState(true);
  const [containerSize, setContainerSize] = useState({ width: 800, height: 600 });
  const [headerSlot, setHeaderSlot] = useState<HTMLElement | null>(null);
  const [viewTick, setViewTick] = useState(0);

  const googleEnabled = !!config?.google_maps_enabled;
  const googleAktif = googleEnabled && !googleGagal;

  /* ---------------- muat konfigurasi & daftar filter ---------------- */
  useEffect(() => {
    let alive = true;
    (async () => {
      try {
        const [cfg, flt] = await Promise.all([fetchMapConfig(), fetchFilters()]);
        if (!alive) return;
        setConfig(cfg);
        setFilters(flt);
        const initial = (cfg.basemap || "google_hybrid") as BasemapId;
        setBasemap(cfg.google_maps_enabled ? initial : fallbackBasemap(initial));
      } catch (e) {
        toast.error("Gagal memuat konfigurasi peta");
      }
    })();
    return () => {
      alive = false;
    };
  }, []);

  // Panel legenda & alat peta: terbuka di >=768px, ringkas (dapat dibuka) di HP
  const [legendOpen, setLegendOpen] = useState<boolean>(() => !window.matchMedia || window.matchMedia("(min-width: 768px)").matches);
  const [toolsOpen, setToolsOpen] = useState<boolean>(() => !window.matchMedia || window.matchMedia("(min-width: 768px)").matches);

  useEffect(() => {
    // Filter dipindah ke header layout hanya bila header cukup lebar (>=1024px)
    const mq = window.matchMedia ? window.matchMedia("(min-width: 1024px)") : null;
    const apply = () => setHeaderSlot(!mq || mq.matches ? document.getElementById("layout-header-slot") : null);
    apply();
    mq?.addEventListener?.("change", apply);
    return () => mq?.removeEventListener?.("change", apply);
  }, []);

  /* ---------------- buat mesin peta ---------------- */
  useEffect(() => {
    if (!config || !mapDivRef.current) return;
    let cancelled = false;
    let created: MapEngine | null = null;

    (async () => {
      const div = mapDivRef.current as HTMLElement;
      const dasar = (config.basemap || "google_hybrid") as BasemapId;
      const mauGoogle = config.google_maps_enabled && !googleGagalRef.current;
      const opts = {
        center: config.center,
        zoom: config.zoom || 18,
        basemap: mauGoogle ? dasar : fallbackBasemap(dasar),
        apiKey: config.google_maps_api_key,
      };
      try {
        created = mauGoogle
          ? await createGoogleEngine(div, opts)
          : await createLeafletEngine(div, opts);
      } catch (e) {
        console.error(e);
        if (!mauGoogle) {
          toast.error("Peta gagal dimuat. Coba muat ulang halaman.");
          return;
        }
        // Kunci API tidak berlaku untuk domain ini (RefererNotAllowedMapError),
        // Maps JavaScript API belum diaktifkan, atau kuota habis.
        googleGagalRef.current = true;
        setGoogleGagal(true);
        try {
          created = await createLeafletEngine(div, { ...opts, basemap: fallbackBasemap(dasar) });
          setBasemap(fallbackBasemap(dasar));
          toast.error("Google Maps tidak dapat dimuat. Peta memakai basemap alternatif.");
        } catch (e2) {
          console.error(e2);
          toast.error("Peta gagal dimuat. Coba muat ulang halaman.");
          return;
        }
      }
      if (cancelled) {
        created.destroy();
        return;
      }
      created.onSelect((props) => setSelected(props));
      created.onViewChange(() => setViewTick((t) => t + 1));
      engineRef.current = created;
      setEngineReady((n) => n + 1);
    })();

    return () => {
      cancelled = true;
      if (engineRef.current) {
        engineRef.current.destroy();
        engineRef.current = null;
      }
    };
    // dibuat ulang bila konfigurasi/mesin peta berubah (google <-> leaflet)
  }, [config, googleEnabled]);

  /* ---------------- ambil data GeoJSON sesuai filter ---------------- */
  const loadData = useCallback(async () => {
    setLoadingData(true);
    try {
      const query = {
        kelurahan: applied.kelurahan,
        rw: applied.rw,
        status: statusFilter,
      };
      const [geo, st] = await Promise.all([fetchGeoJSON(query), fetchStats(query)]);
      setFc(geo);
      setStats(st);
      setSelected(null);
    } catch (e) {
      toast.error("Gagal memuat data rumah");
    } finally {
      setLoadingData(false);
    }
  }, [applied, statusFilter]);

  useEffect(() => {
    loadData();
  }, [loadData]);

  /* ---------------- kirim data ke mesin peta ---------------- */
  useEffect(() => {
    const engine = engineRef.current;
    if (!engine || !fc) return;
    engine.setData(fc);
    // Tampilan awal memakai center & zoom dari konfigurasi (database).
    // Auto-zoom ke sebaran data hanya dilakukan saat filter diterapkan.
    const adaFilter = applied.kelurahan !== SEMUA || applied.rw !== SEMUA;
    if (fc.bbox && adaFilter) engine.fitBounds(fc.bbox);
  }, [fc, engineReady, applied]);

  /* ---------------- ganti basemap ---------------- */
  useEffect(() => {
    engineRef.current?.setBasemap(googleAktif ? basemap : fallbackBasemap(basemap));
  }, [basemap, engineReady, googleAktif]);

  /* ---------------- ukuran kontainer & posisi popup ---------------- */
  useEffect(() => {
    const el = mapDivRef.current;
    if (!el) return;
    const update = () => {
      setContainerSize({ width: el.clientWidth, height: el.clientHeight });
      engineRef.current?.resize?.();
    };
    update();
    const ro = new ResizeObserver(update);
    ro.observe(el);
    return () => ro.disconnect();
  }, [engineReady]);

  useEffect(() => {
    const engine = engineRef.current;
    if (!engine || !selected || selected.lat == null || selected.lng == null) {
      setPixel(null);
      return;
    }
    setPixel(engine.project(Number(selected.lat), Number(selected.lng)));
  }, [selected, viewTick, engineReady]);

  useEffect(() => {
    engineRef.current?.setSelected(selected ? String(selected.id) : null);
  }, [selected, engineReady]);

  /* ---------------- layer PETA DASAR ---------------- */
  const getZoomEngine = useCallback(() => engineRef.current?.getZoom() ?? 12, []);
  const getBoundsEngine = useCallback(() => engineRef.current?.getBounds() ?? null, []);
  const setOverlayEngine = useCallback((id: string, fc: any, meta: any) => {
    engineRef.current?.setOverlay(id, fc, meta);
  }, []);
  const removeOverlayEngine = useCallback((id: string) => {
    engineRef.current?.removeOverlay(id);
  }, []);

  /* ---------------- lapisan GeoTag Verval (sinkron dari modul Verval) ---------------- */
  const { data: vervalPeta } = useVervalPeta();
  const [vervalShow, setVervalShow] = useState(true);
  useEffect(() => {
    if (!engineReady) return;
    const fc = vervalPeta && vervalPeta.mode === "titik" ? vervalPeta.geojson : null;
    if (fc && vervalShow && fc.features?.length) {
      setOverlayEngine("verval-geotag", fc, {
        id: "verval-geotag", label: "GeoTag Verval DTSEN", tipe: "point", warna: "#117A69",
        kategori_field: "status_verval", kategori_warna: VERVAL_STATUS_COLOR, weight: 2,
      });
    } else {
      removeOverlayEngine("verval-geotag");
    }
  }, [vervalPeta, vervalShow, engineReady, setOverlayEngine, removeOverlayEngine]);

  const petaDasar = useBasemapLayers({
    ready: engineReady > 0,
    viewTick,
    getZoom: getZoomEngine,
    getBounds: getBoundsEngine,
    setOverlay: setOverlayEngine,
    removeOverlay: removeOverlayEngine,
  });

  /* ---------------- aksi ---------------- */
  const rwOptions = useMemo(() => {
    if (!filters) return [];
    if (pendingKel === SEMUA) return filters.rw_all || [];
    return filters.rw_by_kelurahan?.[pendingKel] || [];
  }, [filters, pendingKel]);

  const terapkan = () => {
    setApplied({ kelurahan: pendingKel, rw: pendingRw });
  };

  const resetView = () => {
    if (!config) return;
    if (fc?.bbox) engineRef.current?.fitBounds(fc.bbox);
    else engineRef.current?.setView(config.center, config.zoom || 18);
  };

  const toggleFullscreen = () => {
    const el = wrapperRef.current;
    if (!el) return;
    if (document.fullscreenElement) document.exitFullscreen();
    else el.requestFullscreen?.();
  };

  const onPickBasemap = (id: BasemapId) => {
    if (isGoogleBasemap(id) && !googleAktif) {
      toast.info(
        googleEnabled
          ? "Google Maps tidak dapat dimuat untuk alamat ini (periksa pembatasan kunci API)."
          : "Google Maps belum aktif: isi GOOGLE_MAPS_API_KEY pada backend/.env lalu muat ulang.",
      );
      return;
    }
    setBasemap(id);
  };

  /* ---------------- kontrol filter (dipasang di header) ---------------- */
  const filterControls = (
    <div className="flex min-w-0 flex-wrap items-center gap-2" data-testid="peta-filter-bar">
      <select
        data-testid="filter-kelurahan"
        aria-label="Filter kelurahan"
        value={pendingKel}
        onChange={(e) => {
          setPendingKel(e.target.value);
          setPendingRw(SEMUA);
        }}
        className="h-10 min-w-[120px] flex-1 rounded-md border border-slate-300 bg-white px-2 text-sm font-medium text-slate-700 focus:border-slate-500 focus:outline-none sm:flex-none lg:h-9"
      >
        <option value={SEMUA}>Semua Kelurahan</option>
        {filters?.kelurahan?.map((k) => (
          <option key={k} value={k}>
            {k}
          </option>
        ))}
      </select>

      <select
        data-testid="filter-rw"
        aria-label="Filter RW"
        value={pendingRw}
        onChange={(e) => setPendingRw(e.target.value)}
        className="h-10 min-w-[100px] flex-1 rounded-md border border-slate-300 bg-white px-2 text-sm font-medium text-slate-700 focus:border-slate-500 focus:outline-none sm:flex-none lg:h-9"
      >
        <option value={SEMUA}>Semua RW</option>
        {rwOptions.map((r) => (
          <option key={r} value={r}>
            RW {r}
          </option>
        ))}
      </select>

      <button
        type="button"
        data-testid="btn-terapkan"
        onClick={terapkan}
        className="inline-flex h-10 items-center justify-center gap-1.5 rounded-md bg-primary px-3 text-sm font-semibold text-primary-foreground transition-colors hover:opacity-90 lg:h-9"
      >
        {loadingData ? <Loader2 className="h-4 w-4 animate-spin" /> : <RefreshCw className="h-4 w-4" />}
        Terapkan
      </button>
    </div>
  );

  const legend = config?.legend?.length
    ? config.legend
    : Object.keys(STATUS_COLORS).map((s) => ({
        status: s,
        label: STATUS_LABEL[s],
        color: STATUS_COLORS[s],
      }));

  return (
    <div ref={wrapperRef} className="relative flex h-full min-h-[320px] w-full flex-col bg-slate-900" data-testid="peta-gis">
      {headerSlot ? createPortal(filterControls, headerSlot) : (
        <div className="relative z-[600] shrink-0 border-b border-slate-200 bg-white px-2 py-2 sm:px-3">
          {filterControls}
        </div>
      )}
      <div className="relative min-h-0 flex-1">

      {/* Kanvas peta */}
      <div ref={mapDivRef} className="absolute inset-0 h-full w-full" data-testid="map-canvas" />

      {/* Legenda + ringkasan */}
      {!legendOpen && (
        <button type="button" onClick={() => setLegendOpen(true)} data-testid="btn-legend-open" aria-expanded={false} aria-controls="gis-legend"
          className="absolute left-2 top-2 z-[400] inline-flex min-h-10 items-center gap-1.5 rounded-full bg-white px-3 text-xs font-bold text-slate-700 shadow-lg ring-1 ring-slate-200 md:hidden">
          <Home className="h-3.5 w-3.5" /> Legenda <span className="rounded bg-slate-100 px-1.5 text-[10px]">{stats?.total ?? fc?.count ?? 0}</span>
        </button>
      )}
      <div id="gis-legend" className={`pointer-events-auto absolute left-2 top-2 z-[400] max-h-[calc(100%-1rem)] w-56 max-w-[calc(100%-4.5rem)] overflow-y-auto rounded-lg border border-slate-200 bg-white/95 p-3 shadow-lg backdrop-blur sm:left-3 sm:top-3 md:block ${legendOpen ? "block" : "hidden"}`}>
        <div className="mb-2 flex items-center justify-between gap-2">
          <p className="flex items-center gap-1.5 text-xs font-bold uppercase tracking-wide text-slate-700">
            <Home className="h-3.5 w-3.5" /> Status Rumah
          </p>
          <span
            className="rounded bg-slate-100 px-1.5 py-0.5 text-[11px] font-bold text-slate-600"
            data-testid="total-rumah"
          >
            {stats?.total ?? fc?.count ?? 0}
          </span>
          <button type="button" onClick={() => setLegendOpen(false)} aria-label="Ciutkan legenda" data-testid="btn-legend-close"
            className="ml-auto inline-flex h-8 w-8 items-center justify-center rounded-md text-slate-500 hover:bg-slate-100 md:hidden">
            <Minus className="h-4 w-4" />
          </button>
        </div>
        <ul className="space-y-1">
          <li>
            <button
              type="button"
              onClick={() => setStatusFilter(SEMUA)}
              className={`flex w-full items-center gap-2 rounded px-1.5 py-1 text-left text-[11.5px] transition-colors hover:bg-slate-100 ${
                statusFilter === SEMUA ? "bg-slate-100 font-bold" : ""
              }`}
            >
              <span className="inline-block h-3 w-3 rounded-sm border border-slate-400 bg-gradient-to-br from-[#00C853] via-[#FFC107] to-[#FF5252]" />
              Semua status
            </button>
          </li>
          {legend.map((l) => (
            <li key={l.status}>
              <button
                type="button"
                data-testid={`legend-${l.status}`}
                onClick={() => setStatusFilter(statusFilter === l.status ? SEMUA : l.status)}
                className={`flex w-full items-center gap-2 rounded px-1.5 py-1 text-left text-[11.5px] transition-colors hover:bg-slate-100 ${
                  statusFilter === l.status ? "bg-slate-100 font-bold" : ""
                }`}
              >
                <span
                  className="inline-block h-3 w-3 shrink-0 rounded-sm"
                  style={{ backgroundColor: l.color, opacity: 0.85 }}
                />
                <span className="flex-1">{l.label}</span>
                <span className="text-[10px] font-semibold text-slate-500">
                  {stats?.per_status?.[l.status] ?? 0}
                </span>
              </button>
            </li>
          ))}
        </ul>
        {vervalPeta && vervalPeta.mode === "titik" && (
          <div className="mt-2 border-t border-slate-200 pt-2" data-testid="gis-verval-layer">
            <label className="flex cursor-pointer items-center gap-2 text-[11.5px] font-bold text-slate-700">
              <input type="checkbox" checked={vervalShow} onChange={(e) => setVervalShow(e.target.checked)} data-testid="gis-verval-toggle" />
              <span className="inline-block h-3 w-3 shrink-0 rounded-full border-2 border-white bg-[#117A69] ring-1 ring-slate-300" />
              GeoTag Verval
              <span className="ml-auto rounded bg-slate-100 px-1.5 text-[10px] text-slate-600" data-testid="gis-verval-count">{vervalPeta.total}</span>
            </label>
            <p className="mt-1 text-[10px] text-slate-500">Titik foto & koordinat hasil Verval petugas (klik titik untuk rincian).</p>
          </div>
        )}
        <div className="mt-2 border-t border-slate-200 pt-2 text-[11px] text-slate-600">
          <p>
            Jiwa terdata: <b>{stats?.total_jiwa ?? 0}</b>
          </p>
          <p>
            Total luas: <b>{(stats?.total_luas ?? 0).toLocaleString("id-ID")} m²</b>
          </p>
        </div>
      </div>

      {/* Pemilih basemap + kontrol peta */}
      <div className="absolute right-2 top-2 z-[400] flex max-h-[calc(100%-1rem)] max-w-[calc(100%-1rem)] flex-col items-end gap-2 overflow-y-auto sm:right-3 sm:top-3">
        <button type="button" onClick={() => setToolsOpen((v) => !v)} data-testid="btn-tools-toggle" aria-expanded={toolsOpen} aria-controls="gis-tools"
          aria-label={toolsOpen ? "Sembunyikan pengaturan basemap & layer" : "Tampilkan pengaturan basemap & layer"}
          className="inline-flex h-10 w-10 items-center justify-center rounded-lg border border-slate-200 bg-white text-slate-700 shadow-lg md:hidden">
          <Layers className="h-4 w-4" />
        </button>
        <div id="gis-tools" className={`flex-col items-end gap-2 md:flex ${toolsOpen ? "flex" : "hidden"}`}>
        <div className="rounded-lg border border-slate-200 bg-white/95 p-2 shadow-lg backdrop-blur">
          <label className="mb-1 flex items-center gap-1.5 text-[11px] font-bold uppercase tracking-wide text-slate-600">
            <Layers className="h-3.5 w-3.5" /> Basemap
          </label>
          <select
            data-testid="basemap-select"
            value={basemap}
            onChange={(e) => onPickBasemap(e.target.value as BasemapId)}
            className="h-9 w-52 max-w-full rounded-md border border-slate-300 bg-white px-2 text-xs font-medium text-slate-700 focus:outline-none"
          >
            {["Google Maps", "Alternatif (tanpa API key)"].map((group) => (
              <optgroup key={group} label={group}>
                {BASEMAPS.filter((b) => b.group === group).map((b) => (
                  <option key={b.id} value={b.id} disabled={b.requiresGoogle && !googleAktif}>
                    {b.label}
                    {b.requiresGoogle && !googleAktif ? (googleEnabled ? " (tidak aktif)" : " (perlu API key)") : ""}
                  </option>
                ))}
              </optgroup>
            ))}
          </select>
        </div>

        <BasemapLayerPanel
          grup={petaDasar.grup}
          aktif={petaDasar.aktif}
          status={petaDasar.status}
          jumlahTampil={petaDasar.jumlahTampil}
          sumber={petaDasar.sumber}
          onToggle={petaDasar.toggle}
          onReset={petaDasar.matikanSemua}
        />
        </div>

        <div className="flex flex-col overflow-hidden rounded-lg border border-slate-200 bg-white shadow-lg">
          <button
            type="button"
            data-testid="btn-zoom-in"
            onClick={() => engineRef.current?.zoomIn()}
            aria-label="Perbesar peta"
            className="flex h-9 w-9 items-center justify-center border-b border-slate-200 text-slate-700 hover:bg-slate-100"
          >
            <Plus className="h-4 w-4" />
          </button>
          <button
            type="button"
            data-testid="btn-zoom-out"
            onClick={() => engineRef.current?.zoomOut()}
            aria-label="Perkecil peta"
            className="flex h-9 w-9 items-center justify-center border-b border-slate-200 text-slate-700 hover:bg-slate-100"
          >
            <Minus className="h-4 w-4" />
          </button>
          <button
            type="button"
            data-testid="btn-reset-view"
            onClick={resetView}
            aria-label="Kembalikan tampilan awal"
            className="flex h-9 w-9 items-center justify-center border-b border-slate-200 text-slate-700 hover:bg-slate-100"
          >
            <RefreshCw className="h-4 w-4" />
          </button>
          <button
            type="button"
            data-testid="btn-fullscreen"
            onClick={toggleFullscreen}
            aria-label="Layar penuh"
            className="flex h-9 w-9 items-center justify-center text-slate-700 hover:bg-slate-100"
          >
            <Maximize2 className="h-4 w-4" />
          </button>
        </div>
      </div>

      {/* Catatan basemap */}
      {config && !googleAktif && (
        <div className="absolute bottom-2 left-2 right-16 z-[400] max-w-md rounded-lg border border-amber-300 bg-amber-50/95 px-3 py-2 text-[11px] text-amber-900 shadow sm:bottom-3 sm:left-3 sm:right-auto" data-testid="google-notice">
          <p className="flex items-start gap-1.5">
            <Info className="mt-[1px] h-3.5 w-3.5 shrink-0" />
            <span>
              {googleEnabled ? (
                <>
                  Google Maps tidak dapat dimuat untuk alamat ini. Peta memakai basemap
                  alternatif (ESRI/OSM) — periksa pembatasan <b>HTTP referrer</b> dan
                  <b> API restrictions</b> pada kunci Google Maps.
                </>
              ) : (
                <>
                  Basemap ESRI Imagery dipakai sementara. Tambahkan
                  <b> GOOGLE_MAPS_API_KEY</b> pada <b>backend/.env</b> untuk mengaktifkan Google
                  Satellite / Hybrid — struktur peta sudah siap.
                </>
              )}
            </span>
          </p>
        </div>
      )}

      {/* Popup informasi rumah */}
      {selected && (
        <RumahPopup
          data={selected}
          pixel={pixel}
          containerSize={containerSize}
          onClose={() => setSelected(null)}
        />
      )}

      {loadingData && (
        <div className="absolute bottom-3 right-3 z-[400] inline-flex items-center gap-2 rounded-md bg-white/95 px-3 py-1.5 text-xs font-semibold text-slate-700 shadow">
          <Loader2 className="h-4 w-4 animate-spin" /> Memuat polygon rumah…
        </div>
      )}
      </div>
    </div>
  );
}
