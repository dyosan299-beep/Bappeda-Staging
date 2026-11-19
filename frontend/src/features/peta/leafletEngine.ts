/* Mesin peta berbasis Leaflet — dipakai bila Google Maps API key belum tersedia.
   Basemap: ESRI World Imagery (satellite), ESRI Imagery + label (hybrid), OSM. */
import L from "leaflet";
import "leaflet/dist/leaflet.css";
import { fallbackBasemap, STATUS_COLORS, TILE_SPECS } from "./basemaps";
import { createOverlayController } from "./leafletOverlay";
import { ensureLeafletSafe, isMapAlive, safeRemoveMap } from "@/lib/leafletSafe";

ensureLeafletSafe();
import {
  BasemapId,
  EngineOptions,
  MapEngine,
  Pixel,
  RumahFeatureCollection,
  RumahProps,
} from "./types";

export async function createLeafletEngine(
  container: HTMLElement,
  opts: EngineOptions,
): Promise<MapEngine> {
  const map = L.map(container, {
    center: [opts.center.lat, opts.center.lng],
    zoom: opts.zoom,
    zoomControl: false,
    attributionControl: true,
    preferCanvas: false,
    minZoom: 3,
    maxZoom: 21,
  });

  let tileLayers: L.TileLayer[] = [];
  let dataLayer: L.GeoJSON | null = null;
  let selectedId: string | null = null;
  let selectCb: (p: RumahProps | null) => void = () => {};
  let viewCb: () => void = () => {};

  function applyBasemap(basemap: BasemapId) {
    const id = fallbackBasemap(basemap);
    const spec = TILE_SPECS[id] || TILE_SPECS.esri_hybrid;
    tileLayers.forEach((l) => map.removeLayer(l));
    tileLayers = spec.urls.map((url, idx) =>
      L.tileLayer(url, {
        maxZoom: 21,
        maxNativeZoom: spec.maxNativeZoom,
        attribution: idx === 0 ? spec.attribution : undefined,
        crossOrigin: true,
      }).addTo(map),
    );
    // basemap selalu di bawah polygon
    tileLayers.forEach((l) => l.bringToBack());
  }

  function styleFor(feature: any) {
    const props = (feature && feature.properties) || {};
    const color = STATUS_COLORS[String(props.status)] || STATUS_COLORS.kuning;
    const isSelected = selectedId && props.id === selectedId;
    return {
      color: isSelected ? "#0b1220" : color,
      weight: isSelected ? 3.5 : 1.4,
      fillColor: isSelected ? "#ffffff" : color,
      fillOpacity: isSelected ? 0.85 : 0.55,
      opacity: 1,
    } as L.PathOptions;
  }

  applyBasemap(opts.basemap);
  const overlays = createOverlayController(map);
  map.on("move zoom moveend zoomend resize", () => viewCb());
  map.on("click", () => {
    selectedId = null;
    if (dataLayer) dataLayer.setStyle(styleFor as any);
    selectCb(null);
  });

  const engine: MapEngine = {
    kind: "leaflet",

    setBasemap(basemap: BasemapId) {
      applyBasemap(basemap);
    },

    setData(fc: RumahFeatureCollection) {
      if (dataLayer) {
        map.removeLayer(dataLayer);
        dataLayer = null;
      }
      dataLayer = L.geoJSON(fc as any, {
        style: styleFor as any,
        onEachFeature: (feature: any, layer: L.Layer) => {
          layer.on("click", (ev: L.LeafletMouseEvent) => {
            L.DomEvent.stopPropagation(ev);
            selectedId = feature?.properties?.id ?? null;
            if (dataLayer) dataLayer.setStyle(styleFor as any);
            if ((layer as L.Path).bringToFront) (layer as L.Path).bringToFront();
            selectCb(feature?.properties ?? null);
          });
        },
      }).addTo(map);
    },

    setSelected(id: string | null) {
      selectedId = id;
      if (dataLayer) dataLayer.setStyle(styleFor as any);
    },

    setOverlay(id: string, fc: any, meta: any) {
      overlays.setOverlay(id, fc, meta);
    },

    removeOverlay(id: string) {
      overlays.removeOverlay(id);
    },

    getBounds(): number[] | null {
      try {
        const b = map.getBounds();
        return [b.getWest(), b.getSouth(), b.getEast(), b.getNorth()];
      } catch {
        return null;
      }
    },

    fitBounds(bbox?: number[] | null) {
      if (!bbox || bbox.length !== 4 || !isMapAlive(map)) return;
      const [minLng, minLat, maxLng, maxLat] = bbox;
      map.fitBounds(
        L.latLngBounds(L.latLng(minLat, minLng), L.latLng(maxLat, maxLng)),
        { padding: [40, 40], maxZoom: 19, animate: false },
      );
    },

    setView(center, zoom) {
      if (!isMapAlive(map)) return;
      map.setView([center.lat, center.lng], zoom);
    },

    resize() {
      if (!isMapAlive(map)) return;
      try { map.invalidateSize({ pan: false }); } catch { /* noop */ }
    },
    zoomIn() {
      if (!isMapAlive(map)) return;
      map.zoomIn();
    },

    zoomOut() {
      if (!isMapAlive(map)) return;
      map.zoomOut();
    },

    getZoom() {
      return isMapAlive(map) ? map.getZoom() : opts.zoom;
    },

    project(lat: number, lng: number): Pixel | null {
      if (!isMapAlive(map)) return null;
      try {
        const p = map.latLngToContainerPoint(L.latLng(lat, lng));
        return { x: p.x, y: p.y };
      } catch {
        return null;
      }
    },

    onSelect(cb) {
      selectCb = cb;
    },

    onViewChange(cb) {
      viewCb = cb;
    },

    destroy() {
      safeRemoveMap(map);
    },
  };

  return engine;
}
