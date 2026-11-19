import L from "leaflet";

let patched = false;

/**
 * Guard untuk bug bawaan Leaflet 1.9.x saat komponen React di-unmount ketika
 * animasi zoom/pan masih berlangsung: setTimeout(250ms) di `_animateZoom` tetap
 * memanggil `_onZoomTransitionEnd` setelah `map.remove()` menghapus `_mapPane`,
 * sehingga `getPosition(this._mapPane)` melempar `reading '_leaflet_pos'`.
 */
export function ensureLeafletSafe(): void {
  if (patched) return;
  patched = true;

  const proto = L.Map.prototype as any;

  const origZoomEnd = proto._onZoomTransitionEnd;
  if (typeof origZoomEnd === "function") {
    proto._onZoomTransitionEnd = function (this: any) {
      if (!this._animatingZoom) return;
      if (!this._mapPane || !this._container || !this._loaded) {
        this._animatingZoom = false;
        delete this._tempFireZoomEvent;
        return;
      }
      return origZoomEnd.call(this);
    };
  }

  const origAnimMoveEnd = proto._animMoveEnd;
  if (typeof origAnimMoveEnd === "function") {
    proto._animMoveEnd = function (this: any) {
      if (!this._proxy || !this._mapPane || !this._loaded) return;
      return origAnimMoveEnd.call(this);
    };
  }

  const origGetMapPanePos = proto._getMapPanePos;
  if (typeof origGetMapPanePos === "function") {
    proto._getMapPanePos = function (this: any) {
      if (!this._mapPane) return new L.Point(0, 0);
      return origGetMapPanePos.call(this);
    };
  }
}

/** Periksa apakah instance Leaflet Map masih terpasang ke DOM dan belum dihapus. */
export function isMapAlive(map: L.Map | null | undefined): map is L.Map {
  if (!map) return false;
  const m = map as any;
  return Boolean(m._mapPane && m._container && m._container._leaflet_id);
}

/** Hentikan animasi yang berjalan lalu hapus instance Leaflet Map dengan aman. */
export function safeRemoveMap(map: L.Map | null | undefined): void {
  if (!map) return;
  const m = map as any;
  try {
    m._animatingZoom = false;
    delete m._tempFireZoomEvent;
    map.stop();
  } catch {
    /* abaikan bila animasi sudah berhenti */
  }
  try {
    map.off();
  } catch {
    /* abaikan */
  }
  try {
    if (m._container && m._container._leaflet_id) {
      map.remove();
    }
  } catch {
    /* abaikan bila kontainer sudah dibersihkan */
  }
}
