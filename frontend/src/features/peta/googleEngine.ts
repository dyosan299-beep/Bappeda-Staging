/* global google */
/* Mesin peta Google Maps JavaScript API (dipakai bila API key tersedia).
   Basemap: roadmap / satellite / hybrid + ESRI Imagery sebagai custom ImageMapType. */
import { importLibrary, setOptions } from "@googlemaps/js-api-loader";
import { STATUS_COLORS, TILE_SPECS } from "./basemaps";
import { popupHtml } from "./leafletOverlay";
import {
  BasemapId,
  EngineOptions,
  MapEngine,
  Pixel,
  RumahFeatureCollection,
  RumahProps,
} from "./types";

const ESRI_TYPE_ID = "esri_imagery";
const ESRI_HYBRID_TYPE_ID = "esri_hybrid";

function esriTileUrl(template: string, coord: google.maps.Point, zoom: number) {
  return template
    .replace("{z}", String(zoom))
    .replace("{x}", String(coord.x))
    .replace("{y}", String(coord.y));
}

export async function createGoogleEngine(
  container: HTMLElement,
  opts: EngineOptions,
): Promise<MapEngine> {
  // @googlemaps/js-api-loader v2: setOptions() + importLibrary()
  // language/region: label peta (nama tempat) mengikuti Bahasa Indonesia.
  setOptions({ key: opts.apiKey || "", v: "weekly", language: "id", region: "ID" });
  await importLibrary("maps");
  await importLibrary("core");
  const g: any = (window as any).google;

  const mapTypeIdFor = (basemap: BasemapId): string => {
    switch (basemap) {
      case "google_roadmap":
        return g.maps.MapTypeId.ROADMAP;
      case "google_satellite":
        return g.maps.MapTypeId.SATELLITE;
      case "google_hybrid":
        return g.maps.MapTypeId.HYBRID;
      case "esri_imagery":
        return ESRI_TYPE_ID;
      case "esri_hybrid":
        return ESRI_HYBRID_TYPE_ID;
      default:
        return g.maps.MapTypeId.HYBRID;
    }
  };

  const map = new g.maps.Map(container, {
    center: opts.center,
    zoom: opts.zoom,
    mapTypeId: mapTypeIdFor(opts.basemap),
    tilt: 0,
    gestureHandling: "greedy",
    mapTypeControl: false,
    fullscreenControl: false,
    streetViewControl: false,
    zoomControl: false,
    clickableIcons: false,
  });

  // Basemap ESRI sebagai tipe peta kustom
  const esriSpec = TILE_SPECS.esri_imagery;
  const esriLayer = new g.maps.ImageMapType({
    name: "ESRI Imagery",
    maxZoom: 21,
    minZoom: 3,
    tileSize: new g.maps.Size(256, 256),
    getTileUrl: (coord, zoom) =>
      esriTileUrl(esriSpec.urls[0], coord, Math.min(zoom, esriSpec.maxNativeZoom)),
  });
  map.mapTypes.set(ESRI_TYPE_ID, esriLayer);
  map.mapTypes.set(ESRI_HYBRID_TYPE_ID, esriLayer);

  const esriLabelOverlay = new g.maps.ImageMapType({
    name: "ESRI Label",
    maxZoom: 21,
    minZoom: 3,
    tileSize: new g.maps.Size(256, 256),
    getTileUrl: (coord, zoom) =>
      esriTileUrl(TILE_SPECS.esri_hybrid.urls[2], coord, Math.min(zoom, 19)),
  });

  let selectedId: string | null = null;
  let selectCb: (p: RumahProps | null) => void = () => {};
  let viewCb: () => void = () => {};

  const styleFor = (feature: google.maps.Data.Feature): google.maps.Data.StyleOptions => {
    const status = String(feature.getProperty("status") || "kuning");
    const id = String(feature.getProperty("id") || "");
    const color = STATUS_COLORS[status] || STATUS_COLORS.kuning;
    const isSelected = selectedId !== null && id === selectedId;
    return {
      fillColor: isSelected ? "#ffffff" : color,
      fillOpacity: isSelected ? 0.85 : 0.55,
      strokeColor: isSelected ? "#0b1220" : color,
      strokeWeight: isSelected ? 3.5 : 1.4,
      clickable: true,
      zIndex: isSelected ? 20 : 1,
    };
  };

  map.data.setStyle(styleFor);
  map.data.addListener("click", (ev: any) => {
    const feature = ev.feature as google.maps.Data.Feature;
    const props: Record<string, unknown> = {};
    feature.forEachProperty((value, name) => {
      props[name] = value;
    });
    selectedId = String(props.id || "");
    map.data.setStyle(styleFor);
    selectCb(props as RumahProps);
  });
  map.addListener("click", () => {
    selectedId = null;
    map.data.setStyle(styleFor);
    selectCb(null);
  });
  map.addListener("bounds_changed", () => viewCb());
  map.addListener("idle", () => viewCb());

  // Overlay bantu untuk konversi latlng -> pixel kontainer
  class ProjectionHelper extends g.maps.OverlayView {
    draw() {}
  }
  const helper = new ProjectionHelper();
  helper.setMap(map);

  function applyBasemap(basemap: BasemapId) {
    map.setMapTypeId(mapTypeIdFor(basemap));
    // overlay label hanya untuk mode esri_hybrid
    const idx = map.overlayMapTypes.getArray().indexOf(esriLabelOverlay as any);
    if (basemap === "esri_hybrid") {
      if (idx < 0) map.overlayMapTypes.push(esriLabelOverlay);
    } else if (idx >= 0) {
      map.overlayMapTypes.removeAt(idx);
    }
  }
  applyBasemap(opts.basemap);

  const overlayLayers: Record<string, google.maps.Data> = {};
  const overlayInfo = new g.maps.InfoWindow();

  const overlayColor = (meta: any, feature: google.maps.Data.Feature): string => {
    const field = meta?.kategori_field;
    if (!field) return meta?.warna || "#334155";
    const kat = String(feature.getProperty(field) ?? "");
    return (meta?.kategori_warna || {})[kat] || meta?.warna || "#334155";
  };

  const engine: MapEngine = {
    kind: "google",

    setBasemap(basemap: BasemapId) {
      applyBasemap(basemap);
    },

    setData(fc: RumahFeatureCollection) {
      map.data.forEach((f) => map.data.remove(f));
      map.data.addGeoJson(fc as any, { idPropertyName: "id" });
      map.data.setStyle(styleFor);
    },

    setSelected(id: string | null) {
      selectedId = id;
      map.data.setStyle(styleFor);
    },

    setOverlay(id: string, fc: any, meta: any) {
      if (overlayLayers[id]) {
        overlayLayers[id].setMap(null);
        delete overlayLayers[id];
      }
      const layer = new g.maps.Data({ map });
      layer.addGeoJson(fc as any);
      layer.setStyle((feature: google.maps.Data.Feature) => {
        const color = overlayColor(meta, feature);
        const isPolygon = meta?.tipe === "polygon";
        return {
          strokeColor: color,
          strokeWeight: meta?.weight ?? (isPolygon ? 0.8 : 1.6),
          strokeOpacity: 0.95,
          fillColor: color,
          fillOpacity: isPolygon ? meta?.fill_opacity ?? 0.35 : 0,
          clickable: true,
          zIndex: 0,
          icon: meta?.tipe === "point"
            ? {
                path: g.maps.SymbolPath.CIRCLE,
                scale: 4,
                fillColor: color,
                fillOpacity: 0.95,
                strokeColor: "#ffffff",
                strokeWeight: 1,
              }
            : undefined,
        } as google.maps.Data.StyleOptions;
      });
      layer.addListener("click", (ev: any) => {
        const props: Record<string, unknown> = {};
        ev.feature.forEachProperty((value: unknown, name: string) => {
          props[name] = value;
        });
        overlayInfo.setContent(popupHtml(meta, props));
        overlayInfo.setPosition(ev.latLng);
        overlayInfo.open({ map });
      });
      overlayLayers[id] = layer;
    },

    removeOverlay(id: string) {
      if (overlayLayers[id]) {
        overlayLayers[id].setMap(null);
        delete overlayLayers[id];
      }
    },

    getBounds(): number[] | null {
      const b = map.getBounds();
      if (!b) return null;
      const sw = b.getSouthWest();
      const ne = b.getNorthEast();
      return [sw.lng(), sw.lat(), ne.lng(), ne.lat()];
    },

    fitBounds(bbox?: number[] | null) {
      if (!bbox || bbox.length !== 4) return;
      const [minLng, minLat, maxLng, maxLat] = bbox;
      const bounds = new g.maps.LatLngBounds(
        new g.maps.LatLng(minLat, minLng),
        new g.maps.LatLng(maxLat, maxLng),
      );
      map.fitBounds(bounds, 40);
    },

    setView(center, zoom) {
      map.setCenter(center);
      map.setZoom(zoom);
    },

    zoomIn() {
      map.setZoom((map.getZoom() || opts.zoom) + 1);
    },

    zoomOut() {
      map.setZoom((map.getZoom() || opts.zoom) - 1);
    },

    getZoom() {
      return map.getZoom() || opts.zoom;
    },

    project(lat: number, lng: number): Pixel | null {
      try {
        const projection = helper.getProjection();
        if (!projection) return null;
        const point = projection.fromLatLngToContainerPixel(new g.maps.LatLng(lat, lng));
        return point ? { x: point.x, y: point.y } : null;
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
      try {
        helper.setMap(null);
        g.maps.event.clearInstanceListeners(map);
        container.innerHTML = "";
      } catch {
        /* ignore */
      }
    },
  };

  return engine;
}
