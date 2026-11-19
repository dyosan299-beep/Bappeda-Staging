import React, { useCallback, useEffect, useRef, useState } from "react";
import L from "leaflet";
import "leaflet/dist/leaflet.css";
import { toast } from "sonner";
import { Crosshair, MapPin, RotateCcw, Save } from "lucide-react";
import { KpiCard, PageHeader, Panel } from "@/features/data/ui";
import { fmtNum, getWilayahSummary } from "@/features/data/api";
import {
  getGisLocations, pesanGalat, putGisLocation, resetGisLocation,
} from "@/features/data/manageApi";
import { useAuth } from "@/context/AuthContext";
import VervalMapLayer from "@/features/verval/VervalMapLayer";
import { bolehTulis as cekTulis } from "@/features/data/roles";
import { ensureLeafletSafe, isMapAlive, safeRemoveMap } from "@/lib/leafletSafe";

ensureLeafletSafe();

const SEMUA = "semua";

export default function KoordinatGIS() {
  const { user } = useAuth() as { user: any };
  const bolehTulis = cekTulis(user?.role);
  const [data, setData] = useState<any>(null);
  const [wilayah, setWilayah] = useState<any>(null);
  const [kec, setKec] = useState(SEMUA);
  const [edit, setEdit] = useState<any>(null);
  const mapRef = useRef<any>(null);
  const [mapReady, setMapReady] = useState(false);
  const layerRef = useRef<any>(null);
  const pinRef = useRef<any>(null);
  const editRef = useRef<any>(null);

  editRef.current = edit;

  const muat = useCallback(() => {
    getGisLocations(kec === SEMUA ? undefined : kec)
      .then(setData)
      .catch(() => toast.error("Gagal memuat titik koordinat"));
  }, [kec]);

  useEffect(() => { muat(); }, [muat]);
  useEffect(() => { getWilayahSummary().then(setWilayah).catch(() => {}); }, []);

  // inisialisasi peta
  useEffect(() => {
    if (mapRef.current) return;
    const map = L.map("map-koordinat", { center: [-5.135, 119.44], zoom: 12 });
    L.tileLayer("https://{s}.tile.openstreetmap.org/{z}/{x}/{y}.png", {
      attribution: "© OpenStreetMap", maxZoom: 19,
    }).addTo(map);
    map.on("click", (e: any) => {
      if (!editRef.current) return;
      const { lat, lng } = e.latlng;
      setEdit((v: any) => (v ? { ...v, latitude: lat.toFixed(6), longitude: lng.toFixed(6) } : v));
      if (pinRef.current) map.removeLayer(pinRef.current);
      pinRef.current = L.circleMarker([lat, lng], {
        radius: 8, color: "#b91c1c", weight: 3, fillColor: "#fecaca", fillOpacity: 0.9,
      }).addTo(map);
    });
    mapRef.current = map;
    setMapReady(true);
    const t = window.setTimeout(() => {
      if (isMapAlive(map)) map.invalidateSize({ pan: false });
    }, 200);
    return () => {
      window.clearTimeout(t);
      layerRef.current = null;
      pinRef.current = null;
      safeRemoveMap(map);
      mapRef.current = null;
      setMapReady(false);
    };
  }, []);

  // gambar marker
  useEffect(() => {
    const map = mapRef.current;
    if (!isMapAlive(map) || !data) return;
    if (layerRef.current) map.removeLayer(layerRef.current);
    const grup = L.layerGroup();
    const maks = Math.max(1, ...(data.items || []).map((i: any) => Number(i.total_households) || 0));
    (data.items || []).forEach((i: any) => {
      if (i.latitude == null || i.longitude == null) return;
      const r = 6 + 18 * Math.sqrt((Number(i.total_households) || 0) / maks);
      L.circleMarker([Number(i.latitude), Number(i.longitude)], {
        radius: r,
        color: i.sumber === "manual" ? "#0f766e" : "#1d4ed8",
        weight: 2, fillOpacity: 0.35,
      }).bindPopup(
        `<b>${i.kelurahan}</b><br/>Kecamatan ${i.kecamatan}<br/>`
        + `Keluarga: ${fmtNum(i.total_households)}<br/>`
        + `Anggota: ${fmtNum(i.total_individu)}<br/>`
        + `Desil dominan: ${i.desil_dominan}<br/>`
        + `PBI Nasional: ${fmtNum(i.pbi_nas)} · PBI Pemda: ${fmtNum(i.pbi_pemda)}<br/>`
        + `Rumah rentan: ${fmtNum(i.rumah_rentan)}<br/>`
        + `<i>Sumber titik: ${i.sumber}</i>`,
      ).addTo(grup);
    });
    grup.addTo(map);
    layerRef.current = grup;
  }, [data]);

  const simpan = async () => {
    if (!edit) return;
    try {
      await putGisLocation(edit.kelurahan, {
        latitude: Number(edit.latitude),
        longitude: Number(edit.longitude),
        keterangan: edit.keterangan || "",
      });
      toast.success(`Koordinat ${edit.kelurahan} disimpan`);
      setEdit(null);
      if (pinRef.current && mapRef.current) mapRef.current.removeLayer(pinRef.current);
      muat();
    } catch (e) {
      toast.error(pesanGalat(e).pesan);
    }
  };

  const manual = (data?.items || []).filter((i: any) => i.sumber === "manual").length;

  return (
    <div data-testid="page-koordinat-gis">
      <PageHeader title="Titik Koordinat Kelurahan (GIS)"
        subtitle="Titik berasal dari pusat polygon batas wilayah resmi (BIG 2021) — dapat diperbarui manual" />

      <div className="grid grid-cols-2 gap-3 md:grid-cols-4">
        <KpiCard testid="kg-total" label="Kelurahan bertitik" value={fmtNum(data?.total)} />
        <KpiCard label="Titik input manual" value={fmtNum(manual)} color="#0f766e" />
        <KpiCard label="Belum bertitik" value={fmtNum(data?.tanpa_koordinat?.length)} color="#b91c1c" />
        <KpiCard label="Total keluarga terpeta"
          value={fmtNum((data?.items || []).reduce((a: number, i: any) => a + (Number(i.total_households) || 0), 0))}
          color="#4f46e5" />
      </div>

      <div className="mt-3 flex flex-wrap items-center gap-2 rounded-lg border border-slate-200 bg-white p-3">
        <select value={kec} onChange={(e) => setKec(e.target.value)} data-testid="kg-kecamatan"
          className="h-10 w-full rounded-md border border-slate-300 px-2 text-sm sm:h-9 sm:w-auto">
          <option value={SEMUA}>Semua Kecamatan</option>
          {wilayah?.kecamatan?.map((k: any) => <option key={k.kode} value={k.kode}>{k.nama}</option>)}
        </select>
        <span className="text-[11px] text-slate-500">{data?.catatan}</span>
      </div>

      <div className="mt-3 grid gap-3 xl:grid-cols-5">
        <Panel title="Peta Titik Kelurahan" className="xl:col-span-3" testid="kg-peta">
          <div className="relative">
            <div id="map-koordinat" className="h-[clamp(280px,55vh,480px)] w-full rounded-md" />
            {mapReady && <VervalMapLayer map={mapRef.current} compact />}
          </div>
          <p className="mt-2 text-[11px] text-slate-500">
            <MapPin className="mr-1 inline h-3 w-3" />
            Ukuran bulatan mengikuti jumlah keluarga. Titik hijau = koordinat input manual,
            biru = titik pusat batas wilayah resmi. Data pribadi tidak ditampilkan pada popup.
          </p>
        </Panel>

        <Panel title="Daftar Titik" className="xl:col-span-2" testid="kg-tabel">
          <div className="table-scroll max-h-[420px] overflow-y-auto">
            <table className="w-full min-w-[460px] text-sm">
              <thead className="sticky top-0 bg-slate-50 text-left text-[11px] uppercase tracking-wide text-slate-500">
                <tr>
                  <th className="px-2 py-2">Kelurahan</th>
                  <th className="whitespace-nowrap px-2 py-2">Latitude</th>
                  <th className="whitespace-nowrap px-2 py-2">Longitude</th>
                  <th className="whitespace-nowrap px-2 py-2 text-right">Keluarga</th>
                  {bolehTulis && <th className="whitespace-nowrap px-2 py-2">Aksi</th>}
                </tr>
              </thead>
              <tbody>
                {(data?.items || []).map((i: any) => (
                  <tr key={i.id} className="border-t border-slate-100 hover:bg-slate-50">
                    <td className="px-2 py-2">
                      <b className="block text-slate-800">{i.kelurahan}</b>
                      <span className="text-[10px] text-slate-500">
                        {i.kecamatan} · {i.sumber === "manual" ? "manual" : "centroid BIG"}
                      </span>
                    </td>
                    <td className="whitespace-nowrap px-2 py-2 font-mono text-[11px] tabular-nums">{i.latitude}</td>
                    <td className="whitespace-nowrap px-2 py-2 font-mono text-[11px] tabular-nums">{i.longitude}</td>
                    <td className="whitespace-nowrap px-2 py-2 text-right tabular-nums">{fmtNum(i.total_households)}</td>
                    {bolehTulis && (
                      <td className="whitespace-nowrap px-2 py-2">
                        <div className="flex gap-1">
                          <button type="button" data-testid={`kg-edit-${i.kelurahan_norm}`}
                            title="Ubah koordinat"
                            aria-label={`Ubah koordinat ${i.kelurahan}`}
                            onClick={() => {
                              setEdit({
                                kelurahan: i.kelurahan, latitude: i.latitude,
                                longitude: i.longitude, keterangan: "",
                              });
                              if (mapRef.current && i.latitude != null) {
                                mapRef.current.setView([Number(i.latitude), Number(i.longitude)], 15);
                              }
                            }}
                            className="inline-flex h-9 w-9 items-center justify-center rounded text-slate-500 hover:bg-amber-100 hover:text-amber-700 sm:h-8 sm:w-8">
                            <Crosshair className="h-4 w-4" />
                          </button>
                          {i.sumber === "manual" && (
                            <button type="button" data-testid={`kg-reset-${i.kelurahan_norm}`}
                              title="Kembalikan ke titik pusat batas wilayah resmi"
                              aria-label={`Reset koordinat ${i.kelurahan}`}
                              onClick={async () => {
                                try {
                                  await resetGisLocation(i.kelurahan);
                                  toast.success("Titik dikembalikan ke centroid resmi");
                                  muat();
                                } catch (e) { toast.error(pesanGalat(e).pesan); }
                              }}
                              className="inline-flex h-9 w-9 items-center justify-center rounded text-slate-500 hover:bg-slate-200 sm:h-8 sm:w-8">
                              <RotateCcw className="h-4 w-4" />
                            </button>
                          )}
                        </div>
                      </td>
                    )}
                  </tr>
                ))}
              </tbody>
            </table>
          </div>
        </Panel>
      </div>

      {(data?.tanpa_koordinat || []).length > 0 && (
        <Panel title="Kelurahan Belum Memiliki Titik" className="mt-3" testid="kg-tanpa">
          <p className="text-xs text-slate-600">{(data.tanpa_koordinat || []).join(", ")}</p>
        </Panel>
      )}

      {edit && (
        <div className="fixed bottom-4 left-1/2 z-[900] w-[min(560px,94vw)] -translate-x-1/2 rounded-lg border border-slate-300 bg-white p-3 shadow-2xl"
          data-testid="kg-form">
          <p className="text-xs font-bold text-slate-800">
            Ubah koordinat — {edit.kelurahan}
          </p>
          <p className="text-[11px] text-slate-500">
            Klik pada peta untuk mengambil koordinat, atau isi manual di bawah.
          </p>
          <div className="mt-2 grid grid-cols-2 gap-2 md:grid-cols-4">
            <input value={edit.latitude ?? ""} data-testid="kg-lat" placeholder="Latitude"
              onChange={(e) => setEdit({ ...edit, latitude: e.target.value })}
              className="h-9 rounded-md border border-slate-300 px-2 text-sm" />
            <input value={edit.longitude ?? ""} data-testid="kg-lng" placeholder="Longitude"
              onChange={(e) => setEdit({ ...edit, longitude: e.target.value })}
              className="h-9 rounded-md border border-slate-300 px-2 text-sm" />
            <input value={edit.keterangan ?? ""} data-testid="kg-ket" placeholder="Keterangan (opsional)"
              onChange={(e) => setEdit({ ...edit, keterangan: e.target.value })}
              className="h-9 rounded-md border border-slate-300 px-2 text-sm md:col-span-2" />
          </div>
          <div className="mt-2 flex justify-end gap-2">
            <button type="button" onClick={() => setEdit(null)}
              className="h-9 rounded-md border border-slate-300 px-3 text-xs font-semibold">Batal</button>
            <button type="button" onClick={simpan} data-testid="kg-simpan"
              className="inline-flex h-9 items-center gap-2 rounded-md bg-slate-900 px-4 text-xs font-semibold text-white">
              <Save className="h-4 w-4" /> Simpan Koordinat
            </button>
          </div>
        </div>
      )}
    </div>
  );
}
