import { useEffect, useState } from "react";
import { useNavigate, Link, useSearchParams } from "react-router-dom";
import { toast } from "sonner";
import { useAuth } from "@/context/AuthContext";
import { usePageTitle } from "@/hooks/usePageTitle";
import api, { formatApiErrorDetail } from "@/lib/api";
import BrandLogo from "@/components/BrandLogo";
import A11yAssistant from "@/features/a11y/Assistant";
import { LogIn, ArrowLeft, Building2, UserPlus, ShieldCheck } from "lucide-react";

const inputCls =
  "w-full rounded-md border-2 border-slate-300 bg-white px-4 py-2.5 text-base focus:border-[#117A69] focus:outline-none focus-visible:ring-2 focus-visible:ring-[#6FE3CF]";

function Field({ label, id, children, error, hint }) {
  return (
    <div>
      <label htmlFor={id} className="mb-1.5 block text-sm font-semibold text-slate-800">{label}</label>
      {children}
      {hint && !error && (
        <p id={`${id}-hint`} className="mt-1 text-xs text-slate-600">{hint}</p>
      )}
      {error && (
        <p id={`${id}-error`} className="mt-1 text-xs font-semibold text-[#B3261E]">
          {error}
        </p>
      )}
    </div>
  );
}

/** Atribut ARIA untuk input yang mungkin sedang error (WCAG 3.3.1, 3.3.3). */
const fieldA11y = (id, errors) => ({
  "aria-invalid": errors[id] ? true : undefined,
  "aria-describedby": errors[id] ? `${id}-error` : undefined,
});

const TITLES = {
  login: ["Masuk", "Gunakan akun PETA INKLUSI Anda (Admin, Operator, atau NGO)."],
  register: ["Daftar Petugas", "Ajukan akun petugas. Akun aktif setelah disetujui admin Bappeda."],
  ngo: ["Daftar sebagai NGO", "Setelah diverifikasi admin, NGO dapat mengajukan dan memantau inquiry program intervensi."],
};

export default function Login() {
  const { login, register, user } = useAuth();
  const navigate = useNavigate();
  const [sp] = useSearchParams();
  const next = sp.get("next") || "";
  const [mode, setMode] = useState(sp.get("mode") === "ngo" ? "ngo" : "login");
  const [f, setF] = useState({ email: "", password: "", name: "", wilayah: "", organisasi: "", telepon: "", alamat_organisasi: "" });
  const [loading, setLoading] = useState(false);
  const [errors, setErrors] = useState({});
  const [formErr, setFormErr] = useState("");
  // Nilai yang sudah diisi TIDAK dihapus saat berganti mode (WCAG 3.3.7).
  const set = (k) => (e) => {
    const value = e.target.value;
    setF((prev) => ({ ...prev, [k]: value }));
    setErrors((prev) => (prev[k] ? { ...prev, [k]: "" } : prev));
  };

  /** Validasi klien: pesan menyebut kolom + saran perbaikan (WCAG 3.3.1, 3.3.3). */
  const validate = () => {
    const err = {};
    const email = f.email.trim();
    if (!email) err.email = "Email wajib diisi. Contoh: nama@organisasi.org";
    else if (!/^[^\s@]+@[^\s@]+\.[^\s@]+$/.test(email)) err.email = "Format email belum benar. Contoh: nama@organisasi.org";

    const minPass = 10;
    if (!f.password) err.password = "Kata sandi wajib diisi.";
    else if (mode !== "login" && f.password.length < minPass) {
      err.password = `Kata sandi minimal ${minPass} karakter, kombinasi huruf dan angka.`;
    } else if (mode !== "login" && (!/[A-Za-z]/.test(f.password) || !/\d/.test(f.password))) {
      err.password = "Kata sandi harus memuat huruf dan angka.";
    }

    if (mode !== "login") {
      if (!f.name.trim()) err.name = mode === "ngo" ? "Nama PIC wajib diisi." : "Nama lengkap wajib diisi.";
      else if (f.name.trim().length < 2) err.name = "Nama minimal 2 karakter.";
    }
    if (mode === "register" && !f.wilayah.trim()) {
      err.wilayah = "Kecamatan wajib diisi. Contoh: Tallo";
    }
    if (mode === "ngo") {
      if (!f.organisasi.trim()) err.organisasi = "Nama organisasi wajib diisi.";
      else if (f.organisasi.trim().length < 2) err.organisasi = "Nama organisasi minimal 2 karakter.";
      const tel = f.telepon.trim();
      if (!tel) err.telepon = "Nomor telepon wajib diisi. Contoh: 0812xxxxxxxx";
      else if (tel.length < 6) err.telepon = "Nomor telepon minimal 6 digit.";
    }
    return err;
  };

  useEffect(() => {
    if (user) {
      const home = user.role === "ngo" ? "/ngo/inquiry"
        : ["petugas", "operator_rt_rw"].includes(user.role) ? "/verval" : "/dashboard";
      navigate(next || home, { replace: true });
    }
    // eslint-disable-next-line react-hooks/exhaustive-deps
  }, [user]);

  const submit = async (e) => {
    e.preventDefault();
    setFormErr("");
    const found = validate();
    setErrors(found);
    const invalid = Object.keys(found);
    if (invalid.length) {
      setFormErr(`Periksa ${invalid.length} kolom yang ditandai, lalu coba lagi.`);
      document.getElementById(invalid[0])?.focus();
      return;
    }
    setLoading(true);
    try {
      if (mode === "login") {
        const res = await login(f.email, f.password);
        if (res.ok) toast.success("Berhasil masuk");
        else toast.error(res.error);
      } else if (mode === "register") {
        const res = await register({ email: f.email, password: f.password, name: f.name, wilayah: f.wilayah });
        if (res.ok) { toast.success(res.message || "Registrasi berhasil, menunggu persetujuan admin."); setMode("login"); }
        else toast.error(res.error);
      } else {
        const { data } = await api.post("/auth/register-ngo", {
          email: f.email, password: f.password, name: f.name, organisasi: f.organisasi,
          telepon: f.telepon, alamat_organisasi: f.alamat_organisasi,
        });
        toast.success(data.message || "Pendaftaran NGO berhasil, menunggu verifikasi admin.");
        setMode("login");
      }
    } catch (er) {
      const msg = formatApiErrorDetail(er.response?.data?.detail) || er.message;
      setFormErr(msg);
      toast.error(msg);
    } finally {
      setLoading(false);
    }
  };

  const [title, sub] = TITLES[mode];
  usePageTitle(title);
  return (
    <div className="relative grid min-h-screen min-h-[100dvh] grid-cols-1 lg:grid-cols-2">
      <a
        href="#konten"
        className="sr-only focus:not-sr-only focus:absolute focus:left-2 focus:top-2 focus:z-[999] focus:rounded focus:bg-white focus:px-3 focus:py-2 focus:text-slate-900"
      >
        Lewati ke konten utama
      </a>
      <aside aria-label="Tentang PETA INKLUSI" className="relative hidden overflow-hidden bg-[#232F3E] text-white lg:block">
        <div className="relative flex h-full flex-col justify-between p-12">
          <BrandLogo className="h-12 w-12" withText />
          <div>
            <img src="/logo-peta-inklusi.png" alt="Logo PETA INKLUSI" className="mb-8 w-64 max-w-full rounded-2xl" />
            <h2 className="max-w-xl font-head text-[clamp(1.5rem,1rem+1.1vw,2rem)] font-extrabold leading-tight">
              Penguatan Perencanaan Pembangunan Inklusi melalui Pemetaan Data Tematik dan Evaluasi Program pada Kelompok Rentan.
            </h2>
            <p className="mt-4 max-w-lg leading-relaxed text-slate-300">
              Satu platform untuk membaca kondisi Disabilitas, Stunting, Anak Tidak Sekolah, dan Kemiskinan hingga tingkat kelurahan — dari data, analisis, sampai usulan program intervensi.
            </p>
            <p className="mt-6 inline-flex items-center gap-2 rounded-full bg-white/10 px-3 py-1.5 text-xs text-[#6FE3CF]">
              <ShieldCheck className="h-4 w-4" /> NIK, email, dan telepon dimasking sesuai peran
            </p>
          </div>
        </div>
      </aside>

      <main id="konten" tabIndex={-1} className="flex items-center justify-center bg-slate-50 px-4 py-12 pb-[calc(3rem+env(safe-area-inset-bottom))] sm:px-6">
        <div className="w-full max-w-md">
          <Link to="/" className="mb-8 inline-flex items-center gap-2 text-sm font-semibold text-slate-600 hover:text-[#117A69]" data-testid="back-home-link">
            <ArrowLeft className="h-4 w-4" /> Kembali ke Beranda
          </Link>
          <div className="mb-2 lg:hidden"><BrandLogo className="h-10 w-10" withText dark={false} /></div>

          <div className="mb-6 grid grid-cols-3 gap-1 rounded-lg bg-slate-200 p-1" role="group" aria-label="Pilih mode akun">
            {[["login", "Masuk", LogIn], ["ngo", "Daftar NGO", Building2], ["register", "Daftar Petugas", UserPlus]].map(([id, label, Icon]) => (
              <button key={id} type="button" aria-pressed={mode === id} data-testid={`auth-tab-${id}`}
                onClick={() => { setMode(id); setErrors({}); setFormErr(""); }}
                className={`inline-flex min-h-11 items-center justify-center gap-1 rounded-md px-1.5 py-2 text-[11px] font-bold transition-colors sm:gap-1.5 sm:px-2 sm:text-xs ${
                  mode === id ? "bg-white text-[#117A69] shadow-sm ring-2 ring-[#117A69]" : "text-slate-700 hover:text-slate-900"}`}>
                <Icon className="h-3.5 w-3.5 shrink-0" aria-hidden="true" /> <span className="truncate">{label}</span>
              </button>
            ))}
          </div>

          <h1 className="font-head text-3xl font-extrabold text-[#232F3E]" data-testid="auth-title">{title}</h1>
          <p className="mt-2 text-sm text-slate-600">{sub}</p>

          <form onSubmit={submit} noValidate className="mt-6 space-y-4" data-testid="login-form">
            {formErr && (
              <div role="alert" data-testid="login-error-summary"
                className="rounded-md border-2 border-[#B3261E] bg-[#FDF2F2] p-3 text-sm font-semibold text-[#B3261E]">
                {formErr}
              </div>
            )}
            {mode !== "login" && (
              <Field label={mode === "ngo" ? "Nama PIC (penanggung jawab)" : "Nama Lengkap"} id="name" error={errors.name}>
                <input id="name" data-testid="register-name" required minLength={2} autoComplete="name"
                  value={f.name} onChange={set("name")} className={inputCls} {...fieldA11y("name", errors)} />
              </Field>
            )}
            {mode === "register" && (
              <Field label="Wilayah (Kecamatan)" id="wilayah" error={errors.wilayah} hint="Contoh: Tallo">
                <input id="wilayah" data-testid="register-wilayah" required autoComplete="address-level2"
                  value={f.wilayah} onChange={set("wilayah")} placeholder="cth: Tallo" className={inputCls} {...fieldA11y("wilayah", errors)} />
              </Field>
            )}
            {mode === "ngo" && (
              <>
                <Field label="Nama organisasi / NGO" id="organisasi" error={errors.organisasi}>
                  <input id="organisasi" data-testid="ngo-organisasi" required minLength={2} autoComplete="organization"
                    value={f.organisasi} onChange={set("organisasi")} className={inputCls} {...fieldA11y("organisasi", errors)} />
                </Field>
                <Field label="Nomor telepon" id="telepon" error={errors.telepon} hint="Contoh: 0812xxxxxxxx">
                  <input id="telepon" data-testid="ngo-telepon" required inputMode="tel" minLength={6} maxLength={20}
                    autoComplete="tel" value={f.telepon} onChange={set("telepon")} placeholder="0812xxxxxxxx"
                    className={inputCls} {...fieldA11y("telepon", errors)} />
                </Field>
                <Field label="Alamat organisasi (opsional)" id="alamat_organisasi">
                  <input id="alamat_organisasi" data-testid="ngo-alamat" autoComplete="street-address"
                    value={f.alamat_organisasi} onChange={set("alamat_organisasi")} className={inputCls} />
                </Field>
              </>
            )}
            <Field label="Email" id="email" error={errors.email}>
              <input id="email" data-testid="login-email" type="email" required
                autoComplete={mode === "login" ? "username" : "email"}
                value={f.email} onChange={set("email")} placeholder="nama@organisasi.org"
                className={inputCls} {...fieldA11y("email", errors)} />
            </Field>
            <Field
              label="Kata Sandi"
              id="password"
              error={errors.password}
              hint={mode === "login" ? undefined : "Minimal 10 karakter, kombinasi huruf dan angka"}
            >
              <input id="password" data-testid="login-password" type="password" required minLength={mode === "login" ? undefined : 10}
                autoComplete={mode === "login" ? "current-password" : "new-password"}
                value={f.password} onChange={set("password")} placeholder="••••••••"
                className={inputCls} {...fieldA11y("password", errors)} />
            </Field>
            <button data-testid="login-submit" type="submit" disabled={loading}
              className="inline-flex min-h-12 w-full items-center justify-center gap-2 rounded-md bg-[#117A69] px-6 py-3 font-semibold text-white transition-colors hover:bg-[#0E6456] focus:outline-none focus-visible:ring-2 focus-visible:ring-[#6FE3CF] disabled:opacity-60">
              <LogIn className="h-5 w-5" aria-hidden="true" />
              {loading ? "Memproses…" : mode === "login" ? "Masuk" : mode === "ngo" ? "Daftar NGO" : "Ajukan Pendaftaran"}
            </button>
          </form>


        </div>
      </main>
      <A11yAssistant />
    </div>
  );
}
