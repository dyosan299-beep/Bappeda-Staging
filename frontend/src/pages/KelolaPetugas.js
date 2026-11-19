import { useEffect, useMemo, useState } from "react";
import { useLocation, useSearchParams } from "react-router-dom";
import { toast } from "sonner";
import api, { formatApiErrorDetail } from "@/lib/api";
import { useAuth } from "@/context/AuthContext";
import {
  UserPlus, CheckCircle2, Ban, Play, Trash2, Users, ShieldCheck, Clock, Pencil, KeyRound, MapPin, Info,
} from "lucide-react";
import {
  Dialog, DialogContent, DialogHeader, DialogTitle, DialogDescription, DialogFooter, DialogClose,
} from "@/components/ui/dialog";
import {
  AlertDialog, AlertDialogContent, AlertDialogHeader, AlertDialogTitle, AlertDialogDescription,
  AlertDialogFooter, AlertDialogCancel, AlertDialogAction,
} from "@/components/ui/alert-dialog";

const REGIONS = [
  "Mariso", "Mamajang", "Tamalate", "Rappocini", "Makassar", "Ujung Pandang",
  "Wajo", "Bontoala", "Ujung Tanah", "Kepulauan Sangkarrang", "Tallo",
  "Panakkukang", "Manggala", "Biringkanaya", "Tamalanrea",
];

const STATUS = {
  active: { label: "Aktif", cls: "bg-[hsl(160_84%_27%)] text-white", icon: ShieldCheck },
  pending: { label: "Menunggu", cls: "bg-[hsl(32_90%_44%)] text-white", icon: Clock },
  inactive: { label: "Nonaktif", cls: "bg-muted text-muted-foreground", icon: Ban },
};

const ROLE_LABEL = {
  superadmin: "Superadmin", admin: "Superadmin", operator: "Kecamatan",
  operator_kecamatan: "Kecamatan", operator_kelurahan: "Kelurahan", verifikator: "Verifikator",
  pimpinan: "Pimpinan", petugas: "Petugas RT/RW", operator_rt_rw: "Operator RT/RW", ngo: "NGO",
  admin_bappeda: "Admin Bappeda", admin_opd: "Admin OPD", viewer: "Viewer",
};

/** Peran yang dapat dibuat SUPERADMIN (petugas RT/RW dibuat oleh akun Kecamatan). */
const SUPERADMIN_ROLE_OPTIONS = [
  ["operator", "Kecamatan (kelola RT/RW, Kelurahan, penugasan & persetujuan akhir Verval)"],
  ["operator_kelurahan", "Kelurahan (periksa Verval tahap 1 kelurahan)"],
  ["admin_bappeda", "Admin Bappeda (semua wilayah kota & persetujuan akhir)"],
  ["verifikator", "Verifikator (periksa data/Verval wilayah)"],
  ["pimpinan", "Pimpinan (lihat hasil & unduh laporan)"],
  ["superadmin", "Superadmin (akses penuh)"],
];
const KECAMATAN_ROLE_OPTIONS = [
  ["petugas", "Petugas RT/RW (Verval & GeoTag lapangan)"],
  ["operator_kelurahan", "Kelurahan (pemeriksa Verval tahap 1)"],
];
const NEEDS_KECAMATAN = (role) => ["operator", "operator_kecamatan", "operator_kelurahan", "verifikator", "petugas"].includes(role);
const CITY = "Kota Makassar";

const inputCls = "w-full rounded-md border-2 border-border bg-background px-4 py-2.5 focus:border-primary focus:outline-none disabled:opacity-50";

export default function KelolaPetugas() {
  const { user } = useAuth();
  const { pathname } = useLocation();
  const [params, setParams] = useSearchParams();
  const isKecamatan = ["operator", "operator_kecamatan"].includes(user?.role);
  const myKecamatan = user?.wilayah || "";
  // Rute /validasi-akun memakai halaman yang sama, tetapi fokus pada antrean pendaftar.
  const modeValidasi = pathname.startsWith("/validasi-akun");
  const statusFilter = params.get("status") || (modeValidasi ? "pending" : "semua");
  const setStatusFilter = (v) => {
    const next = new URLSearchParams(params);
    if (v === "semua" || (modeValidasi && v === "pending")) next.delete("status");
    else next.set("status", v);
    setParams(next, { replace: true });
  };

  const [users, setUsers] = useState([]);
  const [kelurahanOpts, setKelurahanOpts] = useState([]); // [{kecamatan, nama}]
  const [showForm, setShowForm] = useState(false);
  const emptyForm = {
    email: "", password: "", name: "", role: isKecamatan ? "petugas" : "operator",
    wilayah: isKecamatan ? myKecamatan : "", kelurahan: "", rw: "", rt: "",
  };
  const [form, setForm] = useState(emptyForm);
  const [busy, setBusy] = useState(false);
  const [loadErr, setLoadErr] = useState("");
  // Aksi destruktif selalu lewat konfirmasi dulu (WCAG 3.3.4)
  const [confirm, setConfirm] = useState(null); // { kind: "delete"|"deactivate", user }

  const load = async () => {
    try {
      const { data } = await api.get("/admin/users");
      setUsers(data);
      setLoadErr("");
    } catch (e) {
      setLoadErr(formatApiErrorDetail(e.response?.data?.detail) || "Gagal memuat pengguna");
    }
  };
  useEffect(() => {
    load();
    api.get("/admin/users/kelurahan").then((r) => setKelurahanOpts(r.data || [])).catch(() => {});
    // eslint-disable-next-line react-hooks/exhaustive-deps
  }, []);

  const kelurahanFor = (kec) => kelurahanOpts.filter((k) => !kec || k.kecamatan === kec).map((k) => k.nama);

  const setStatus = async (id, status) => {
    try {
      await api.patch(`/admin/users/${id}/status`, { status });
      toast.success("Status diperbarui");
      load();
    } catch (e) {
      toast.error(formatApiErrorDetail(e.response?.data?.detail));
    }
  };

  const remove = async (id) => {
    try {
      await api.delete(`/admin/users/${id}`);
      toast.success("Pengguna dihapus");
      load();
    } catch (e) {
      toast.error(formatApiErrorDetail(e.response?.data?.detail));
    }
  };

  const rtArray = (s) => String(s || "").split(/[,\s;/]+/).map((x) => x.trim()).filter(Boolean);

  const create = async (e) => {
    e.preventDefault();
    setBusy(true);
    try {
      const payload = {
        email: form.email, password: form.password, name: form.name, role: form.role,
        wilayah: isKecamatan ? myKecamatan : (NEEDS_KECAMATAN(form.role) ? form.wilayah : CITY),
      };
      if (form.role === "petugas" || form.role === "operator_kelurahan") {
        payload.kelurahan = form.kelurahan;
      }
      if (form.role === "petugas") {
        payload.rw = form.rw;
        payload.rt = rtArray(form.rt);
      }
      await api.post("/admin/users", payload);
      toast.success(form.role === "petugas" ? "Akun petugas berhasil dibuat" : "Akun baru ditambahkan");
      setForm(emptyForm);
      setShowForm(false);
      load();
    } catch (e) {
      toast.error(formatApiErrorDetail(e.response?.data?.detail));
    } finally {
      setBusy(false);
    }
  };

  // Edit user
  const [editUser, setEditUser] = useState(null);
  const [resetUser, setResetUser] = useState(null);
  const [newPass, setNewPass] = useState("");

  const saveEdit = async () => {
    try {
      const payload = { name: editUser.name, email: editUser.email };
      if (!isKecamatan) {
        payload.role = editUser.role;
        payload.wilayah = NEEDS_KECAMATAN(editUser.role) ? editUser.wilayah : CITY;
      } else {
        payload.role = editUser.role;
      }
      if (editUser.role === "petugas" || editUser.role === "operator_kelurahan") {
        payload.kelurahan = editUser.kelurahan;
      }
      if (editUser.role === "petugas") {
        payload.rw = editUser.rw;
        payload.rt = rtArray(editUser.rt);
      }
      await api.patch(`/admin/users/${editUser.id}`, payload);
      toast.success("Data pengguna diperbarui");
      setEditUser(null);
      load();
    } catch (e) {
      toast.error(formatApiErrorDetail(e.response?.data?.detail));
    }
  };

  const saveReset = async () => {
    if (!newPass || newPass.length < 10) { toast.error("Kata sandi minimal 10 karakter, kombinasi huruf dan angka"); return; }
    if (!/[A-Za-z]/.test(newPass) || !/\d/.test(newPass)) { toast.error("Kata sandi harus memuat huruf dan angka"); return; }
    try {
      await api.post(`/admin/users/${resetUser.id}/reset-password`, { password: newPass });
      toast.success(`Kata sandi ${resetUser.name} berhasil diatur ulang`);
      setResetUser(null);
      setNewPass("");
    } catch (e) {
      toast.error(formatApiErrorDetail(e.response?.data?.detail));
    }
  };

  const pendingCount = users.filter((u) => u.status === "pending").length;
  const shown = statusFilter === "semua" ? users : users.filter((u) => u.status === statusFilter);
  const title = modeValidasi ? "Validasi Akun Petugas" : isKecamatan ? "Kelola Petugas & Kelurahan" : "Kelola User";
  const wilayahText = (u) => {
    if (u.role === "petugas") {
      const rt = Array.isArray(u.rt) && u.rt.length ? ` / RT ${u.rt.join(", ")}` : " (Semua RT)";
      return `${u.wilayah || "-"} · ${u.kelurahan || "-"} · RW ${u.rw || "-"}${rt}`;
    }
    if (u.role === "operator_kelurahan") {
      return `${u.wilayah || "-"} · Kel. ${u.kelurahan || "-"}`;
    }
    return u.wilayah || "–";
  };

  const editKelurahanList = useMemo(() => kelurahanFor(editUser?.wilayah || myKecamatan), [editUser?.wilayah, kelurahanOpts]); // eslint-disable-line react-hooks/exhaustive-deps

  return (
    <div className="space-y-6" data-testid="kelola-petugas-page">
      <div className="flex flex-wrap items-end justify-between gap-4">
        <div className="min-w-0">
          <p className="font-head text-3xl font-extrabold md:text-4xl">{title}</p>
          <p className="mt-1 flex flex-wrap items-center gap-2 text-sm text-muted-foreground">
            <Users className="h-4 w-4" /> {users.length} akun
            {modeValidasi && <span className="text-xs">· periksa identitas dan wilayah, lalu aktifkan akun</span>}
            {isKecamatan && (
              <span className="inline-flex items-center gap-1 rounded-full bg-[#117A69]/10 px-2 py-0.5 text-xs font-bold text-[#0f5f52]" data-testid="operator-scope-label">
                <MapPin className="h-3 w-3" /> Kecamatan {myKecamatan}
              </span>
            )}
            {pendingCount > 0 && (
              <span className="ml-1 rounded-full bg-[hsl(32_90%_44%)] px-2 py-0.5 text-xs font-bold text-white">
                {pendingCount} menunggu persetujuan
              </span>
            )}
          </p>
        </div>
        <button
          data-testid="add-user-btn"
          onClick={() => setShowForm((s) => !s)}
          className="inline-flex min-h-11 items-center gap-2 rounded-md bg-primary px-4 py-2 text-sm font-semibold text-primary-foreground transition-colors hover:bg-[#0E6456] focus:outline-none"
        >
          <UserPlus className="h-4 w-4" /> {isKecamatan ? "Tambah Petugas / Kelurahan" : "Tambah Akun"}
        </button>
      </div>

      <div className="flex items-start gap-2 rounded-lg border border-border bg-secondary/50 p-3 text-xs text-muted-foreground" data-testid="kelola-user-info">
        <Info className="mt-0.5 h-4 w-4 shrink-0 text-[#117A69]" />
        {isKecamatan ? (
          <p>
            Anda mengelola akun <b>Petugas RT/RW</b> dan <b>Kelurahan</b> di Kecamatan <b>{myKecamatan}</b>. Petugas RT/RW
            melakukan Verval &amp; GeoTag lapangan, Kelurahan memeriksa tahap 1, dan Kecamatan memberikan persetujuan akhir.
          </p>
        ) : (
          <p>
            Superadmin membuat akun <b>Kecamatan</b>, <b>Kelurahan</b>, <b>Admin Bappeda</b>, <b>Verifikator</b>, dan <b>Pimpinan</b>.
            Akun Kecamatan dapat membuat &amp; mengelola akun <b>Petugas RT/RW</b> dan <b>Kelurahan</b> di kecamatannya sekaligus
            memberikan persetujuan akhir Verval.
          </p>
        )}
      </div>

      {showForm && (
        <form onSubmit={create} className="rounded-lg border-2 border-primary bg-card p-4 sm:p-6" data-testid="add-user-form">
          <h3 className="mb-4 font-head text-lg font-bold">{isKecamatan ? "Tambah Akun Wilayah Kecamatan" : "Tambah Akun Baru"}</h3>
          <div className="grid grid-cols-1 gap-4 md:grid-cols-2">
            <div>
              <label htmlFor="new-user-role" className="mb-1.5 block text-sm font-semibold">Peran Akun</label>
              <select id="new-user-role" data-testid="new-user-role" value={form.role}
                onChange={(e) => setForm({ ...form, role: e.target.value })} className={inputCls}>
                {(isKecamatan ? KECAMATAN_ROLE_OPTIONS : SUPERADMIN_ROLE_OPTIONS).map(([v, l]) => (
                  <option key={v} value={v}>{l}</option>
                ))}
              </select>
            </div>
            <div>
              <label htmlFor="new-user-name" className="mb-1.5 block text-sm font-semibold">Nama Lengkap</label>
              <input id="new-user-name" data-testid="new-user-name" required autoComplete="name" value={form.name}
                onChange={(e) => setForm({ ...form, name: e.target.value })} className={inputCls} />
            </div>
            <div>
              <label htmlFor="new-user-email" className="mb-1.5 block text-sm font-semibold">Email</label>
              <input id="new-user-email" data-testid="new-user-email" type="email" required autoComplete="email" value={form.email}
                onChange={(e) => setForm({ ...form, email: e.target.value })} className={inputCls} />
            </div>
            <div>
              <label htmlFor="new-user-password" className="mb-1.5 block text-sm font-semibold">Kata Sandi</label>
              <input id="new-user-password" data-testid="new-user-password" type="text" required minLength={10}
                autoComplete="new-password" value={form.password}
                onChange={(e) => setForm({ ...form, password: e.target.value })} className={inputCls} />
            </div>
            <div>
              <label htmlFor="new-user-wilayah" className="mb-1.5 block text-sm font-semibold">
                Wilayah (Kecamatan){NEEDS_KECAMATAN(form.role) ? "" : " — tidak diperlukan"}
              </label>
              <select id="new-user-wilayah" data-testid="new-user-wilayah" required={NEEDS_KECAMATAN(form.role)}
                disabled={isKecamatan || !NEEDS_KECAMATAN(form.role)} value={form.wilayah}
                onChange={(e) => setForm({ ...form, wilayah: e.target.value, kelurahan: "" })} className={inputCls}>
                <option value="">{NEEDS_KECAMATAN(form.role) ? "Pilih kecamatan…" : "Seluruh Kota Makassar"}</option>
                {REGIONS.map((r) => <option key={r} value={r}>{r}</option>)}
              </select>
            </div>
            {(form.role === "petugas" || form.role === "operator_kelurahan") && (
              <div>
                <label htmlFor="new-user-kelurahan" className="mb-1.5 block text-sm font-semibold">Kelurahan</label>
                <select id="new-user-kelurahan" data-testid="new-user-kelurahan" required value={form.kelurahan}
                  onChange={(e) => setForm({ ...form, kelurahan: e.target.value })} className={inputCls}>
                  <option value="">Pilih kelurahan…</option>
                  {kelurahanFor(form.wilayah).map((k) => <option key={k} value={k}>{k}</option>)}
                </select>
              </div>
            )}
            {form.role === "petugas" && (
              <>
                <div>
                  <label htmlFor="new-user-rw" className="mb-1.5 block text-sm font-semibold">RW</label>
                  <input id="new-user-rw" data-testid="new-user-rw" required inputMode="numeric" placeholder="mis. 01" value={form.rw}
                    onChange={(e) => setForm({ ...form, rw: e.target.value })} className={inputCls} />
                </div>
                <div>
                  <label htmlFor="new-user-rt" className="mb-1.5 block text-sm font-semibold">RT <span className="font-normal text-muted-foreground">(kosongkan untuk akun Ketua RW)</span></label>
                  <input id="new-user-rt" data-testid="new-user-rt" placeholder="mis. 01, 02, 03" value={form.rt}
                    onChange={(e) => setForm({ ...form, rt: e.target.value })} className={inputCls} />
                </div>
              </>
            )}
          </div>
          <button data-testid="submit-new-user" type="submit" disabled={busy}
            className="mt-5 inline-flex min-h-11 items-center gap-2 rounded-md bg-primary px-6 py-2.5 font-semibold text-primary-foreground hover:bg-[#0E6456] focus:outline-none disabled:opacity-60">
            <UserPlus className="h-5 w-5" /> {busy ? "Menyimpan…" : "Tambahkan"}
          </button>
        </form>
      )}

      {loadErr && (
        <div className="rounded-lg border-2 border-destructive/40 bg-destructive/5 p-4 text-sm text-destructive" data-testid="users-error">
          {loadErr} <button onClick={load} className="ml-2 font-bold underline">Coba lagi</button>
        </div>
      )}

      <div className="flex flex-wrap items-center gap-3" data-testid="user-filter">
        <label htmlFor="filter-status" className="text-sm font-semibold">Tampilkan status</label>
        <select id="filter-status" value={statusFilter} onChange={(e) => setStatusFilter(e.target.value)}
          className="min-h-11 rounded-md border-2 border-border bg-background px-3 py-2 text-sm focus:border-primary focus:outline-none">
          <option value="semua">Semua ({users.length})</option>
          <option value="pending">Menunggu persetujuan ({pendingCount})</option>
          <option value="active">Aktif</option>
          <option value="inactive">Nonaktif</option>
        </select>
      </div>

      <div className="table-scroll overflow-x-auto rounded-lg max-md:border-0 max-md:bg-transparent md:border-2 md:border-border md:bg-card">
        <table className="table-cards w-full text-sm md:min-w-[780px]" role="table" data-testid="users-table">
          <caption className="sr-only">
            Daftar akun petugas beserta email, peran, wilayah, status, dan aksi yang tersedia
          </caption>
          <thead>
            <tr className="border-b-2 border-border bg-secondary text-left" role="row">
              <th scope="col" role="columnheader" className="px-4 py-3 font-bold">Nama</th>
              <th scope="col" role="columnheader" className="px-4 py-3 font-bold">Email</th>
              <th scope="col" role="columnheader" className="px-4 py-3 font-bold">Peran</th>
              <th scope="col" role="columnheader" className="px-4 py-3 font-bold">Wilayah</th>
              <th scope="col" role="columnheader" className="px-4 py-3 font-bold">Status</th>
              <th scope="col" role="columnheader" className="px-4 py-3 text-right font-bold">Aksi</th>
            </tr>
          </thead>
          <tbody>
            {shown.length === 0 && !loadErr && (
              <tr role="row"><td role="cell" colSpan={6} className="px-4 py-8 text-center text-muted-foreground" data-testid="users-empty">
                {users.length > 0
                  ? "Tidak ada akun dengan status ini."
                  : isKecamatan ? "Belum ada akun petugas / kelurahan di kecamatan Anda." : "Belum ada akun."}
              </td></tr>
            )}
            {shown.map((u) => {
              const st = STATUS[u.status] || STATUS.active;
              const isSelf = u.id === user?.id;
              return (
                <tr key={u.id} role="row" className="border-b border-border" data-testid={`user-row-${u.email}`}>
                  <td role="cell" data-label="Nama" className="px-4 py-3 font-medium">{u.name}</td>
                  <td role="cell" data-label="Email" className="px-4 py-3 text-muted-foreground max-md:[overflow-wrap:anywhere] md:whitespace-nowrap">{u.email}</td>
                  <td role="cell" data-label="Peran" className="px-4 py-3">
                    {ROLE_LABEL[u.role] || u.role}
                    {u.role === "ngo" && u.organisasi && (
                      <span className="block text-xs text-muted-foreground" data-testid={`user-org-${u.email}`}>{u.organisasi}</span>
                    )}
                  </td>
                  <td role="cell" data-label="Wilayah" className="px-4 py-3" data-testid={`user-wilayah-${u.email}`}>{wilayahText(u)}</td>
                  <td role="cell" data-label="Status" className="px-4 py-3">
                    <span className={`inline-flex items-center gap-1 rounded-full px-2.5 py-1 text-xs font-bold ${st.cls}`}>
                      <st.icon className="h-3 w-3" aria-hidden="true" /> {st.label}
                    </span>
                  </td>
                  <td role="cell" data-label="" className="px-4 py-3">
                    <div className="flex flex-wrap items-center justify-end gap-2 md:flex-nowrap">
                      {u.status === "pending" && (
                        <button data-testid={`approve-${u.email}`} onClick={() => setStatus(u.id, "active")}
                          className="inline-flex min-h-11 items-center gap-1 rounded-md bg-[hsl(160_84%_27%)] px-2.5 py-1.5 text-xs font-semibold text-white hover:opacity-90 sm:min-h-9">
                          <CheckCircle2 className="h-4 w-4" aria-hidden="true" /> Setujui<span className="sr-only"> {u.name}</span>
                        </button>
                      )}
                      {u.status === "active" && !isSelf && (
                        <button data-testid={`deactivate-${u.email}`} onClick={() => setConfirm({ kind: "deactivate", user: u })}
                          className="inline-flex min-h-11 items-center gap-1 rounded-md border-2 border-border px-2.5 py-1.5 text-xs font-semibold hover:bg-secondary sm:min-h-9">
                          <Ban className="h-4 w-4" aria-hidden="true" /> Nonaktifkan<span className="sr-only"> {u.name}</span>
                        </button>
                      )}
                      {u.status === "inactive" && (
                        <button data-testid={`activate-${u.email}`} onClick={() => setStatus(u.id, "active")}
                          className="inline-flex min-h-11 items-center gap-1 rounded-md bg-[hsl(160_84%_27%)] px-2.5 py-1.5 text-xs font-semibold text-white hover:opacity-90 sm:min-h-9">
                          <Play className="h-4 w-4" aria-hidden="true" /> Aktifkan<span className="sr-only"> {u.name}</span>
                        </button>
                      )}
                      {!isSelf && (
                        <button data-testid={`delete-${u.email}`} onClick={() => setConfirm({ kind: "delete", user: u })}
                          aria-label={`Hapus petugas ${u.name}`}
                          className="inline-flex h-11 w-11 items-center justify-center rounded-md border-2 border-primary text-primary hover:bg-primary hover:text-primary-foreground sm:h-9 sm:w-9">
                          <Trash2 className="h-4 w-4" aria-hidden="true" />
                        </button>
                      )}
                      <button data-testid={`edit-${u.email}`}
                        aria-label={`Edit petugas ${u.name}`}
                        onClick={() => setEditUser({
                          id: u.id, name: u.name, email: u.email, wilayah: u.wilayah || "", role: u.role,
                          kelurahan: u.kelurahan || "", rw: u.rw || "", rt: Array.isArray(u.rt) ? u.rt.join(", ") : "",
                        })}
                        className="inline-flex h-11 w-11 items-center justify-center rounded-md border-2 border-accent text-accent hover:bg-accent hover:text-accent-foreground sm:h-9 sm:w-9">
                        <Pencil className="h-4 w-4" aria-hidden="true" />
                      </button>
                      <button data-testid={`reset-${u.email}`}
                        aria-label={`Reset kata sandi ${u.name}`}
                        onClick={() => { setResetUser({ id: u.id, name: u.name }); setNewPass(""); }}
                        className="inline-flex h-11 w-11 items-center justify-center rounded-md border-2 border-border hover:bg-secondary sm:h-9 sm:w-9">
                        <KeyRound className="h-4 w-4" aria-hidden="true" />
                      </button>
                      {isSelf && <span className="text-xs text-muted-foreground">Akun Anda</span>}
                    </div>
                  </td>
                </tr>
              );
            })}
          </tbody>
        </table>
      </div>

      {/* Modal Edit User */}
      {editUser && (
        <Dialog open onOpenChange={(o) => { if (!o) setEditUser(null); }}>
          <DialogContent className="max-w-lg" data-testid="edit-user-modal">
            <DialogHeader>
              <DialogTitle className="inline-flex items-center gap-2 font-head text-lg font-bold">
                <Pencil className="h-5 w-5 text-accent" aria-hidden="true" /> Edit Pengguna
              </DialogTitle>
              <DialogDescription className="sr-only">
                Ubah nama, email, peran, dan wilayah akun petugas.
              </DialogDescription>
            </DialogHeader>
            <div className="grid grid-cols-1 gap-4">
              <div>
                <label htmlFor="edit-user-name" className="mb-1.5 block text-sm font-semibold">Nama Lengkap</label>
                <input id="edit-user-name" data-testid="edit-user-name" autoComplete="name" value={editUser.name}
                  onChange={(e) => setEditUser({ ...editUser, name: e.target.value })} className={inputCls} />
              </div>
              <div>
                <label htmlFor="edit-user-email" className="mb-1.5 block text-sm font-semibold">Email</label>
                <input id="edit-user-email" data-testid="edit-user-email" type="email" autoComplete="email" value={editUser.email}
                  onChange={(e) => setEditUser({ ...editUser, email: e.target.value })} className={inputCls} />
              </div>
              <div>
                <label htmlFor="edit-user-role" className="mb-1.5 block text-sm font-semibold">Peran</label>
                {isKecamatan && ["petugas", "operator_kelurahan"].includes(editUser.role) ? (
                  <select id="edit-user-role" data-testid="edit-user-role" value={editUser.role}
                    onChange={(e) => setEditUser({ ...editUser, role: e.target.value })} className={inputCls}>
                    {KECAMATAN_ROLE_OPTIONS.map(([v, l]) => <option key={v} value={v}>{l}</option>)}
                  </select>
                ) : !isKecamatan && editUser.role !== "petugas" ? (
                  <select id="edit-user-role" data-testid="edit-user-role" value={editUser.role}
                    onChange={(e) => setEditUser({ ...editUser, role: e.target.value })} className={inputCls}>
                    {SUPERADMIN_ROLE_OPTIONS.map(([v, l]) => <option key={v} value={v}>{l}</option>)}
                    {!SUPERADMIN_ROLE_OPTIONS.some(([v]) => v === editUser.role) && (
                      <option value={editUser.role}>{ROLE_LABEL[editUser.role] || editUser.role}</option>
                    )}
                  </select>
                ) : (
                  <input id="edit-user-role" data-testid="edit-user-role" value={ROLE_LABEL[editUser.role] || editUser.role} disabled className={inputCls} />
                )}
              </div>
              <div>
                <label htmlFor="edit-user-wilayah" className="mb-1.5 block text-sm font-semibold">
                  Wilayah (Kecamatan){NEEDS_KECAMATAN(editUser.role) ? "" : " — tidak diperlukan"}
                </label>
                <select id="edit-user-wilayah" data-testid="edit-user-wilayah" disabled={isKecamatan || !NEEDS_KECAMATAN(editUser.role)}
                  value={editUser.wilayah}
                  onChange={(e) => setEditUser({ ...editUser, wilayah: e.target.value, kelurahan: "" })} className={inputCls}>
                  <option value="">{NEEDS_KECAMATAN(editUser.role) ? "Pilih kecamatan…" : "Seluruh Kota Makassar"}</option>
                  {REGIONS.map((r) => <option key={r} value={r}>{r}</option>)}
                </select>
              </div>
              {(editUser.role === "petugas" || editUser.role === "operator_kelurahan") && (
                <div>
                  <label htmlFor="edit-user-kelurahan" className="mb-1.5 block text-sm font-semibold">Kelurahan</label>
                  <select id="edit-user-kelurahan" data-testid="edit-user-kelurahan" value={editUser.kelurahan}
                    onChange={(e) => setEditUser({ ...editUser, kelurahan: e.target.value })} className={inputCls}>
                    <option value="">Pilih kelurahan…</option>
                    {editKelurahanList.map((k) => <option key={k} value={k}>{k}</option>)}
                    {editUser.kelurahan && !editKelurahanList.includes(editUser.kelurahan) && (
                      <option value={editUser.kelurahan}>{editUser.kelurahan}</option>
                    )}
                  </select>
                </div>
              )}
              {editUser.role === "petugas" && (
                <div className="grid grid-cols-2 gap-3">
                  <div>
                    <label htmlFor="edit-user-rw" className="mb-1.5 block text-sm font-semibold">RW</label>
                    <input id="edit-user-rw" data-testid="edit-user-rw" inputMode="numeric" value={editUser.rw}
                      onChange={(e) => setEditUser({ ...editUser, rw: e.target.value })} className={inputCls} />
                  </div>
                  <div>
                    <label htmlFor="edit-user-rt" className="mb-1.5 block text-sm font-semibold">RT (koma)</label>
                    <input id="edit-user-rt" data-testid="edit-user-rt" value={editUser.rt}
                      onChange={(e) => setEditUser({ ...editUser, rt: e.target.value })} className={inputCls} />
                  </div>
                </div>
              )}
            </div>
            <DialogFooter className="mt-5 flex-row justify-end gap-2">
              <DialogClose asChild>
                <button className="min-h-11 rounded-md border-2 border-border px-4 py-2 text-sm font-semibold hover:bg-secondary">
                  Batal
                </button>
              </DialogClose>
              <button data-testid="save-edit-user" onClick={saveEdit}
                className="min-h-11 rounded-md bg-primary px-5 py-2 text-sm font-semibold text-primary-foreground hover:bg-[#0E6456]">
                Simpan
              </button>
            </DialogFooter>
          </DialogContent>
        </Dialog>
      )}

      {/* Modal Reset Password */}
      {resetUser && (
        <Dialog open onOpenChange={(o) => { if (!o) setResetUser(null); }}>
          <DialogContent className="max-w-md" data-testid="reset-pw-modal">
            <DialogHeader>
              <DialogTitle className="inline-flex items-center gap-2 font-head text-lg font-bold">
                <KeyRound className="h-5 w-5 text-primary" aria-hidden="true" /> Reset Kata Sandi
              </DialogTitle>
              <DialogDescription>
                Atur kata sandi baru untuk <b>{resetUser.name}</b>.
              </DialogDescription>
            </DialogHeader>
            <div>
              <label htmlFor="reset-pw-input" className="mb-1.5 block text-sm font-semibold">Kata sandi baru</label>
              <input id="reset-pw-input" data-testid="reset-pw-input" type="text" value={newPass} minLength={10}
                placeholder="Minimal 10 karakter, huruf + angka" autoComplete="new-password"
                onChange={(e) => setNewPass(e.target.value)} className={inputCls} />
            </div>
            <DialogFooter className="mt-5 flex-row justify-end gap-2">
              <DialogClose asChild>
                <button className="min-h-11 rounded-md border-2 border-border px-4 py-2 text-sm font-semibold hover:bg-secondary">
                  Batal
                </button>
              </DialogClose>
              <button data-testid="save-reset-pw" onClick={saveReset}
                className="min-h-11 rounded-md bg-primary px-5 py-2 text-sm font-semibold text-primary-foreground hover:bg-[hsl(0_72%_43%)]">
                Simpan Kata Sandi
              </button>
            </DialogFooter>
          </DialogContent>
        </Dialog>
      )}

      {/* Konfirmasi aksi destruktif (WCAG 3.3.4) */}
      <AlertDialog open={!!confirm} onOpenChange={(o) => { if (!o) setConfirm(null); }}>
        <AlertDialogContent data-testid="confirm-dialog">
          <AlertDialogHeader>
            <AlertDialogTitle>
              {confirm?.kind === "delete"
                ? `Hapus akun ${confirm?.user?.name}?`
                : `Nonaktifkan akun ${confirm?.user?.name}?`}
            </AlertDialogTitle>
            <AlertDialogDescription>
              {confirm?.kind === "delete"
                ? "Akun akan dihapus permanen dan tidak dapat dipulihkan."
                : "Akun tidak akan bisa masuk sampai diaktifkan kembali oleh admin."}
            </AlertDialogDescription>
          </AlertDialogHeader>
          <AlertDialogFooter>
            <AlertDialogCancel className="min-h-11">Batal</AlertDialogCancel>
            <AlertDialogAction
              data-testid="confirm-dialog-action"
              className="min-h-11 bg-destructive text-destructive-foreground hover:bg-destructive/90"
              onClick={() => {
                if (!confirm) return;
                if (confirm.kind === "delete") remove(confirm.user.id);
                else setStatus(confirm.user.id, "inactive");
                setConfirm(null);
              }}
            >
              {confirm?.kind === "delete" ? "Hapus" : "Nonaktifkan"}
            </AlertDialogAction>
          </AlertDialogFooter>
        </AlertDialogContent>
      </AlertDialog>
    </div>
  );
}
