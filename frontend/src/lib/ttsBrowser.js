/**
 * Text-to-Speech lewat Web Speech API (`speechSynthesis`) dengan penanganan
 * khusus untuk iOS/iPadOS Safari dan Chrome Android.
 *
 * Alasan modul ini dipisah dari context:
 * 1. iOS hanya mengizinkan ucapan *pertama* bila `speak()` dipanggil di dalam
 *    gestur pengguna. Rantai `await fetch(...)` sebelum `speak()` membuat gestur
 *    kedaluwarsa sehingga suara tidak keluar sama sekali.
 * 2. iOS membuang antrean bila beberapa utterance dimasukkan sekaligus, jadi
 *    ucapan dirangkai satu per satu lewat `onend`.
 * 3. Sebagian mesin TTS Android memotong utterance yang panjang (> ~200 huruf).
 * 4. Bila perangkat tidak punya suara Bahasa Indonesia, `speak()` dapat tidak
 *    pernah memicu `onstart`; tanpa watchdog status UI menggantung di
 *    "Membacakan…" padahal tidak ada suara.
 */

/** Panjang maksimum satu utterance. iOS/Android memotong teks yang lebih panjang. */
export const MAKS_UTTERANCE = 160;

/** Batas waktu tunggu `onstart` sebelum dianggap terblokir (ms). */
const BATAS_MULAI = 3000;

const normalLang = (v) => String(v || "").toLowerCase().replace(/_/g, "-");

/** Apakah browser ini punya mesin Text-to-Speech. */
export function dukungSuara() {
  try {
    return !!(window.speechSynthesis && typeof window.SpeechSynthesisUtterance === "function");
  } catch {
    return false;
  }
}

/** Daftar suara yang terpasang di perangkat (bisa kosong sebelum `voiceschanged`). */
export function daftarSuara() {
  try {
    return (window.speechSynthesis?.getVoices() || []).slice();
  } catch {
    return [];
  }
}

/**
 * Suara Bahasa Indonesia bila tersedia.
 * iOS memakai kode `id-ID`, sebagian mesin lama memakai `in-ID`.
 */
export function suaraIndonesia(daftar = daftarSuara()) {
  return (
    daftar.find((v) => normalLang(v.lang).startsWith("id")) ||
    daftar.find((v) => normalLang(v.lang).startsWith("in")) ||
    daftar.find((v) => /indonesia/i.test(v.name || "")) ||
    undefined
  );
}

/** Ringkasan kemampuan suara perangkat — dipakai untuk diagnosa di panel. */
export function infoSuara() {
  const didukung = dukungSuara();
  const daftar = didukung ? daftarSuara() : [];
  const indo = didukung ? suaraIndonesia(daftar) : undefined;
  return {
    didukung,
    jumlah: daftar.length,
    indonesia: !!indo,
    nama: indo ? indo.name : "",
    lang: indo ? indo.lang : (daftar[0]?.lang || ""),
  };
}

/** Ikuti perubahan daftar suara (iOS/Android mengisinya secara asinkron). */
export function pantauSuara(cb) {
  const synth = window.speechSynthesis;
  if (!synth) return () => {};
  const h = () => cb(infoSuara());
  const dukungEvent = typeof synth.addEventListener === "function";
  if (dukungEvent) synth.addEventListener("voiceschanged", h);
  else synth.onvoiceschanged = h;
  // Isi awal: sebagian browser butuh satu kali getVoices() untuk memicu pemuatan.
  daftarSuara();
  h();
  return () => {
    if (dukungEvent) synth.removeEventListener("voiceschanged", h);
    else if (synth.onvoiceschanged === h) synth.onvoiceschanged = null;
  };
}

let sudahDibuka = false;
/**
 * Buka kunci sesi audio pada gestur pengguna pertama.
 * iOS tidak mau memutar suara yang dipicu kode (mis. "bacakan saat disorot")
 * sebelum ada satu ucapan yang dijalankan dari gestur.
 */
export function bukaKunciSuara() {
  if (sudahDibuka || !dukungSuara()) return;
  const synth = window.speechSynthesis;
  sudahDibuka = true;
  try {
    const u = new window.SpeechSynthesisUtterance("\u00A0");
    u.volume = 0;
    u.rate = 1;
    u.lang = "id-ID";
    synth.speak(u);
  } catch { /* noop */ }
}

/**
 * Pecah teks menjadi potongan pendek siap-ucap, mengutamakan batas kalimat.
 */
export function potongTeks(text, maks = MAKS_UTTERANCE) {
  const kalimat = String(text || "")
    .replace(/\s+/g, " ")
    .trim()
    .split(/(?<=[.!?;:])\s+/)
    .map((s) => s.trim())
    .filter(Boolean);

  const hasil = [];
  let cur = "";
  const dorong = () => {
    const t = cur.trim();
    if (t) hasil.push(t);
    cur = "";
  };

  for (const k of kalimat) {
    if (k.length > maks) {
      dorong();
      let buf = "";
      for (const kata of k.split(" ")) {
        if (!buf) buf = kata;
        else if (`${buf} ${kata}`.length > maks) { hasil.push(buf); buf = kata; }
        else buf = `${buf} ${kata}`;
      }
      if (buf) hasil.push(buf);
      continue;
    }
    if (`${cur} ${k}`.trim().length > maks) dorong();
    cur = `${cur} ${k}`;
  }
  dorong();
  return hasil;
}

/**
 * Bacakan teks dengan suara perangkat.
 *
 * @returns {{ stop: () => void, pause: () => void, resume: () => void } | null}
 */
export function bacakanTeks({
  text, rate = 1, tunda = 0,
  onPotongan, onSelesai, onTerblokir, onGagal,
}) {
  if (!dukungSuara()) {
    onGagal?.("tidak-didukung");
    return null;
  }
  const synth = window.speechSynthesis;
  const potongan = potongTeks(text);
  if (!potongan.length) {
    onSelesai?.();
    return null;
  }

  let token = 0;
  let idx = 0;
  let berhenti = false;
  let jeda = false;
  let watchdog = null;
  let timer = null;
  let voice = suaraIndonesia();

  const bersihkan = () => {
    clearTimeout(watchdog);
    clearTimeout(timer);
    watchdog = null;
    timer = null;
  };

  const ucapkan = (i) => {
    if (berhenti || jeda) return;
    if (i >= potongan.length) {
      onSelesai?.();
      return;
    }
    idx = i;
    // Suara bisa baru terpasang setelah pemutaran pertama (iOS/Android).
    if (!voice) voice = suaraIndonesia();
    const teks = potongan[i];
    const u = new window.SpeechSynthesisUtterance(teks);
    u.lang = "id-ID";
    if (voice) u.voice = voice;
    u.rate = Math.min(2, Math.max(0.5, rate));
    u.pitch = 1;
    u.volume = 1;

    const tokenKini = token;
    let mulai = false;

    u.onstart = () => {
      if (tokenKini !== token) return;
      mulai = true;
      clearTimeout(watchdog);
      onPotongan?.(teks, i);
    };
    u.onend = () => {
      if (tokenKini !== token) return;
      clearTimeout(watchdog);
      if (berhenti || jeda) return;
      // Jeda kecil antar ucapan: Chrome Android kadang mengabaikan speak() yang
      // dipanggil langsung dari dalam onend.
      timer = setTimeout(() => ucapkan(i + 1), 40);
    };
    u.onerror = (e) => {
      if (tokenKini !== token) return;
      clearTimeout(watchdog);
      const kode = (e && e.error) || "error";
      if (kode === "interrupted" || kode === "canceled") return;
      if (kode === "not-allowed") {
        berhenti = true;
        onTerblokir?.("not-allowed");
        return;
      }
      if (berhenti || jeda) return;
      // language-unavailable / voice-unavailable / synthesis-failed:
      // laporkan sekali, lalu lanjut agar tidak berhenti total tanpa suara.
      onGagal?.(kode);
      timer = setTimeout(() => ucapkan(i + 1), 80);
    };

    watchdog = setTimeout(() => {
      if (tokenKini !== token || mulai || berhenti || jeda) return;
      berhenti = true;
      onTerblokir?.("tanpa-respons");
    }, BATAS_MULAI);

    try {
      if (synth.paused) synth.resume();
      synth.speak(u);
    } catch {
      onGagal?.("gagal-panggil");
      timer = setTimeout(() => ucapkan(i + 1), 80);
    }
  };

  const jalankan = () => { if (!berhenti && !jeda) ucapkan(0); };
  // tunda > 0 dipakai setelah cancel(): Chrome Android butuh tenggang singkat,
  // sedangkan tunda = 0 menjaga gestur pengguna tetap sah di iOS.
  if (tunda > 0) timer = setTimeout(jalankan, tunda);
  else jalankan();

  return {
    stop() {
      berhenti = true;
      token += 1;
      bersihkan();
      try { synth.cancel(); } catch { /* noop */ }
    },
    /** Android Chrome tidak mendukung pause() dengan benar, jadi jeda = hentikan
     *  lalu lanjutkan dari potongan terakhir saat resume. */
    pause() {
      if (berhenti || jeda) return;
      jeda = true;
      token += 1;
      bersihkan();
      try { synth.cancel(); } catch { /* noop */ }
    },
    resume() {
      if (!jeda || berhenti) return;
      jeda = false;
      token += 1;
      timer = setTimeout(() => ucapkan(idx), 120);
    },
  };
}
