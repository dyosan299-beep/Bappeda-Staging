import { createContext, useCallback, useContext, useEffect, useRef, useState } from "react";
import { API } from "@/lib/api";
import {
  bacakanTeks, bukaKunciSuara, dukungSuara, infoSuara, pantauSuara, potongTeks,
} from "@/lib/ttsBrowser";

const AccessibilityContext = createContext(null);

/** Satu suara untuk seluruh sistem — sama dengan tombol "Bacakan" di halaman /aksesibilitas. */
export const SUARA = "alloy";

/**
 * Suara AI dari server (`POST /api/tts`) hanya dipakai bila memang tersedia.
 * Endpoint itu sekarang menjawab 503, sehingga permintaan jaringan di depan
 * `speechSynthesis.speak()` membuat gestur pengguna kedaluwarsa dan suara tidak
 * berbunyi di iOS/Android. Aktifkan lewat REACT_APP_TTS_SERVER=1 bila server TTS
 * sudah hidup kembali.
 */
const SERVER_TTS = String(process.env.REACT_APP_TTS_SERVER || "") === "1";

const load = (k, d) => {
  try {
    const v = localStorage.getItem(k);
    return v === null ? d : JSON.parse(v);
  } catch {
    return d;
  }
};

/** Pecah teks menjadi kalimat, lalu gabungkan menjadi potongan <= max karakter (agar suara cepat mulai). */
export function potongKalimat(text) {
  return String(text || "")
    .replace(/\s+/g, " ")
    .split(/(?<=[.!?;:])\s+/)
    .map((s) => s.trim())
    .filter(Boolean);
}

/** Potongan pertama dibuat pendek agar suara cepat mulai; potongan berikutnya diambil sambil diputar. */
function buatPotongan(text, max = 380, maxPertama = 160) {
  const out = [];
  let cur = [];
  let len = 0;
  for (const s of potongKalimat(text)) {
    const batas = out.length ? max : maxPertama;
    if (len + s.length > batas && cur.length) {
      out.push(cur);
      cur = [];
      len = 0;
    }
    cur.push(s);
    len += s.length + 1;
  }
  if (cur.length) out.push(cur);
  return out; // array of array-of-sentences
}

export function AccessibilityProvider({ children }) {
  const [textSize, setTextSize] = useState(() => load("a11y_text", "normal")); // normal|large|xlarge
  const [contrast, setContrast] = useState(() => load("a11y_contrast", false));
  const [reduceMotion, setReduceMotion] = useState(() => load("a11y_reduce", false));
  const [autoRead, setAutoRead] = useState(() => load("a11y_autoread", false)); // bacakan saat disorot
  // Tempo bawaan = normal. Kunci v2 agar pengguna lama (bawaan lama "slow") ikut kembali ke tempo normal.
  const [speechRate, setSpeechRate] = useState(() => load("a11y_rate_v2", "normal")); // normal|slow|slower
  const [captionsOn, setCaptionsOn] = useState(() => load("a11y_captions", true)); // subtitle (disabilitas tuli)
  const [easyMode, setEasyMode] = useState(() => load("a11y_easy", false)); // bahasa mudah
  const [bisindoOn, setBisindoOn] = useState(() => load("a11y_bisindo", true)); // jendela juru bahasa isyarat
  const [status, setStatus] = useState("idle"); // idle|loading|playing|paused
  const [caption, setCaption] = useState("");
  const [transcript, setTranscript] = useState("");
  const [progress, setProgress] = useState({ i: 0, n: 0 });
  const [currentKey, setCurrentKey] = useState("");
  const [liveMsg, setLiveMsg] = useState("");
  // Diagnosa suara perangkat (dipakai panel aksesibilitas).
  const [suara, setSuara] = useState(() => infoSuara());
  const [suaraTerblokir, setSuaraTerblokir] = useState("");
  const [masalahSuara, setMasalahSuara] = useState("");

  const audioRef = useRef(null);
  const tokenRef = useRef(0);
  const modeRef = useRef("browser"); // audio|browser
  const ctlRef = useRef(null); // pengendali mesin suara browser
  const aktifRef = useRef(false); // ada suara yang sedang dimuat/diputar/dijeda
  const statusRef = useRef("idle");
  const lastRef = useRef(null); // teks terakhir, untuk "coba lagi"

  statusRef.current = status;

  // Tempo diatur di server (instruksi model suara) agar suara tetap jernih — audio diputar pada kecepatan asli 1.0.
  // RATE_MAP dipakai untuk suara browser.
  const RATE_MAP = { normal: 1.0, slow: 0.88, slower: 0.75 };
  const rateRef = useRef(RATE_MAP[speechRate] ?? 1.0);
  rateRef.current = RATE_MAP[speechRate] ?? 1.0;
  const tempoRef = useRef(speechRate);
  tempoRef.current = speechRate;

  useEffect(() => {
    const el = document.documentElement;
    el.classList.toggle("a11y-large", textSize === "large");
    el.classList.toggle("a11y-xlarge", textSize === "xlarge");
    el.classList.toggle("a11y-contrast", contrast);
    el.classList.toggle("a11y-reduce-motion", reduceMotion);
    el.classList.toggle("a11y-easy", easyMode);
    const simpan = { a11y_text: textSize, a11y_contrast: contrast, a11y_reduce: reduceMotion, a11y_autoread: autoRead,
      a11y_rate_v2: speechRate, a11y_captions: captionsOn, a11y_easy: easyMode, a11y_bisindo: bisindoOn };
    Object.entries(simpan).forEach(([k, v]) => localStorage.setItem(k, JSON.stringify(v)));
  }, [textSize, contrast, reduceMotion, autoRead, speechRate, captionsOn, easyMode, bisindoOn]);

  // iOS/Android mengisi daftar suara secara asinkron; denah suara ikut diperbarui.
  useEffect(() => pantauSuara(setSuara), []);

  // iOS hanya mengizinkan suara yang dipicu kode setelah ada satu ucapan dari gestur.
  useEffect(() => {
    const buka = () => bukaKunciSuara();
    const opt = { once: true, passive: true };
    window.addEventListener("pointerdown", buka, opt);
    window.addEventListener("touchstart", buka, opt);
    window.addEventListener("keydown", buka, opt);
    return () => {
      window.removeEventListener("pointerdown", buka);
      window.removeEventListener("touchstart", buka);
      window.removeEventListener("keydown", buka);
    };
  }, []);

  /** Pesan untuk pembaca layar (aria-live) — juga dipakai sebagai umpan balik visual. */
  const announce = useCallback((msg) => {
    setLiveMsg("");
    setTimeout(() => setLiveMsg(msg), 30);
  }, []);

  const stop = useCallback(() => {
    const aktif = aktifRef.current;
    aktifRef.current = false;
    tokenRef.current += 1;
    if (audioRef.current) {
      audioRef.current.pause();
      audioRef.current = null;
    }
    if (ctlRef.current) {
      ctlRef.current.stop();
      ctlRef.current = null;
    }
    // Jangan panggil cancel() saat tidak ada yang diputar: Chrome Android
    // mengabaikan speak() yang dipanggil tepat setelah cancel().
    if (aktif) { try { window.speechSynthesis?.cancel(); } catch { /* noop */ } }
    setStatus("idle");
    setCaption("");
    setProgress({ i: 0, n: 0 });
    setCurrentKey("");
  }, []);

  const selesai = useCallback(() => {
    aktifRef.current = false;
    ctlRef.current = null;
    setStatus("idle");
    setCaption("");
    setProgress({ i: 0, n: 0 });
    setCurrentKey("");
  }, []);

  /** Suara perangkat (Web Speech API) — jalur utama, dipanggil sinkron dari gestur. */
  const mulaiBrowser = useCallback((text, tunda, token) => {
    modeRef.current = "browser";
    aktifRef.current = true;
    const jumlah = potongTeks(text).length;
    const ctl = bacakanTeks({
      text,
      rate: rateRef.current,
      tunda,
      onPotongan: (s, i) => {
        if (token !== tokenRef.current) return;
        setCaption(s);
        setStatus("playing");
        setProgress({ i: i + 1, n: jumlah });
      },
      onSelesai: () => { if (token === tokenRef.current) selesai(); },
      onTerblokir: (sebab) => {
        if (token !== tokenRef.current) return;
        aktifRef.current = false;
        ctlRef.current = null;
        setStatus("idle");
        setCaption("");
        setSuaraTerblokir(sebab);
        announce(sebab === "not-allowed"
          ? "Perangkat memblokir suara. Ketuk tombol Bacakan sekali lagi untuk mengizinkan."
          : "Suara belum berbunyi. Pastikan volume perangkat aktif, lalu ketuk Bacakan lagi.");
      },
      onGagal: (kode) => {
        if (token !== tokenRef.current) return;
        if (kode === "tidak-didukung") {
          aktifRef.current = false;
          setStatus("idle");
          announce("Perangkat ini tidak mendukung suara. Silakan baca teks subtitle.");
        } else {
          setMasalahSuara(kode);
        }
      },
    });
    ctlRef.current = ctl;
    if (!ctl) {
      aktifRef.current = false;
      setStatus("idle");
    }
  }, [announce, selesai]);

  /**
   * Bacakan teks. Jalur browser dipanggil tanpa `await` apa pun agar gestur
   * pengguna masih sah (syarat iOS). Jalur audio server hanya bila diaktifkan.
   */
  const speak = useCallback((text, voice = SUARA, key = "") => {
    if (!text) return;
    const sebelumnyaAktif = aktifRef.current;
    stop();
    const token = tokenRef.current;
    setTranscript(potongKalimat(text).join(" "));
    setCurrentKey(key);
    setSuaraTerblokir("");
    setMasalahSuara("");
    lastRef.current = { text, voice, key };

    if (!SERVER_TTS) {
      setStatus("loading");
      // Setelah cancel() Chrome Android butuh tenggang; dari keadaan diam tidak,
      // supaya gestur pengguna tetap terpakai di iOS.
      mulaiBrowser(text, sebelumnyaAktif ? 140 : 0, token);
      return;
    }

    const potongan = buatPotongan(text);
    setStatus("loading");
    setCaption(potongan[0]?.[0] || "");
    modeRef.current = "audio";
    aktifRef.current = true;
    const cache = {};
    const ambil = (i) => {
      if (!cache[i]) {
        cache[i] = fetch(`${API}/tts`, {
          method: "POST",
          headers: { "Content-Type": "application/json" },
          body: JSON.stringify({ text: potongan[i].join(" ").slice(0, 3800), voice, kecepatan: tempoRef.current }),
        }).then((r) => { if (!r.ok) throw new Error("tts"); return r.blob(); }).then((b) => URL.createObjectURL(b));
      }
      return cache[i];
    };
    const putar = async (i) => {
      if (token !== tokenRef.current) return;
      if (i >= potongan.length) { selesai(); return; }
      let url;
      try {
        url = await ambil(i);
      } catch {
        if (token === tokenRef.current) {
          // Server TTS tidak tersedia: lanjutkan sisa teks dengan suara perangkat.
          aktifRef.current = false;
          mulaiBrowser(potongan.slice(i).flat().join(" "), 0, token);
        }
        return;
      }
      if (token !== tokenRef.current) return;
      if (i + 1 < potongan.length) ambil(i + 1).catch(() => {});
      const kal = potongan[i];
      const bobot = kal.map((s) => s.length);
      const total = bobot.reduce((a, b) => a + b, 0) || 1;
      const audio = new Audio(url);
      audio.playbackRate = 1.0;
      audioRef.current = audio;
      audio.ontimeupdate = () => {
        if (!audio.duration || token !== tokenRef.current) return;
        const target = (audio.currentTime / audio.duration) * total;
        let acc = 0;
        for (let k = 0; k < kal.length; k += 1) {
          acc += bobot[k];
          if (target <= acc) { setCaption(kal[k]); break; }
        }
      };
      audio.onended = () => putar(i + 1);
      audio.onerror = () => putar(i + 1);
      setProgress({ i: i + 1, n: potongan.length });
      setCaption(kal[0]);
      try {
        await audio.play();
        if (token === tokenRef.current) setStatus("playing");
      } catch {
        if (token === tokenRef.current) {
          aktifRef.current = false;
          mulaiBrowser(potongan.slice(i).flat().join(" "), 0, token);
        }
      }
    };
    putar(0);
  }, [mulaiBrowser, selesai, stop]);

  /** Bacaan singkat (mode "bacakan saat disorot") — memakai jalur suara yang sama. */
  const speakQuick = useCallback((text, key = "fokus") => {
    const t = String(text || "").replace(/\s+/g, " ").trim().slice(0, 300);
    if (t) speak(t, SUARA, key);
  }, [speak]);

  /** Ulangi bacaan terakhir (dipakai tombol "Coba lagi" saat suara diblokir). */
  const ulangiSuara = useCallback(() => {
    const l = lastRef.current;
    if (l) speak(l.text, l.voice, l.key);
  }, [speak]);

  const pause = useCallback(() => {
    if (modeRef.current === "audio" && audioRef.current) audioRef.current.pause();
    else ctlRef.current?.pause();
    setStatus("paused");
  }, []);

  const resume = useCallback(() => {
    if (modeRef.current === "audio" && audioRef.current) audioRef.current.play().catch(() => {});
    else ctlRef.current?.resume();
    setStatus("playing");
  }, []);

  // Suara dihentikan sistem saat aplikasi ke latar belakang (kebanyakan iOS):
  // jangan biarkan status tertahan di "Membacakan…".
  useEffect(() => {
    const onVis = () => {
      if (document.visibilityState !== "visible" || !aktifRef.current) return;
      if (modeRef.current !== "browser" || statusRef.current !== "playing") return;
      if (dukungSuara() && window.speechSynthesis.speaking) return;
      aktifRef.current = false;
      ctlRef.current = null;
      setStatus("idle");
      setCaption("");
    };
    document.addEventListener("visibilitychange", onVis);
    return () => document.removeEventListener("visibilitychange", onVis);
  }, []);

  // Bersihkan suara saat provider dilepas (mis. halaman di-reload).
  useEffect(() => () => {
    aktifRef.current = false;
    ctlRef.current?.stop();
    ctlRef.current = null;
    try { window.speechSynthesis?.cancel(); } catch { /* noop */ }
  }, []);

  const speaking = status !== "idle";

  return (
    <AccessibilityContext.Provider
      value={{
        textSize, setTextSize,
        contrast, setContrast,
        reduceMotion, setReduceMotion,
        autoRead, setAutoRead,
        speechRate, setSpeechRate,
        captionsOn, setCaptionsOn,
        easyMode, setEasyMode,
        bisindoOn, setBisindoOn,
        speak, speakQuick, stop, pause, resume, speaking, status, caption, transcript, progress, currentKey,
        suara, suaraTerblokir, masalahSuara, ulangiSuara,
        announce, liveMsg,
      }}
    >
      {children}
      <div className="sr-only" role="status" aria-live="polite" aria-atomic="true" data-testid="a11y-live">{liveMsg}</div>
    </AccessibilityContext.Provider>
  );
}

export const useA11y = () => useContext(AccessibilityContext);
