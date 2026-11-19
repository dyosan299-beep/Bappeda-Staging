import React, { useEffect, useRef, useState } from "react";
import { marked } from "marked";
import { toast } from "sonner";
import api, { API } from "@/lib/api";
import { Speak } from "@/components/Speak";
import {
  Sparkles, Loader2, Send, Database, FileDown, Plus, Trash2,
  MessageSquare, AlertTriangle, ChevronDown, ChevronUp,
} from "lucide-react";

/** Bersihkan markdown untuk dibacakan TTS */
const toPlain = (s) => (s || "").replace(/[#*`|>_-]/g, " ").replace(/\s+/g, " ").trim();

function RefsPanel({ refs }) {
  const [open, setOpen] = useState(false);
  if (!refs || refs.length === 0) return null;
  return (
    <div className="mt-4 rounded-md border-2 border-dashed border-slate-300 bg-slate-50 p-3">
      <button
        type="button"
        data-testid="refs-toggle"
        onClick={() => setOpen((o) => !o)}
        className="flex w-full items-center gap-2 text-left text-sm font-bold text-slate-700 focus:outline-none"
      >
        <Database className="h-4 w-4 shrink-0" />
        <span className="flex-1">Referensi Data Internal ({refs.length} sumber)</span>
        {open ? <ChevronUp className="h-4 w-4" /> : <ChevronDown className="h-4 w-4" />}
      </button>
      {open && (
        <ul className="mt-2 space-y-1.5 text-xs text-slate-600">
          {refs.map((r, i) => (
            <li key={i} className="flex flex-wrap items-center gap-2">
              <span className="rounded bg-slate-200 px-1.5 py-0.5 font-mono font-semibold text-slate-800">
                {r.sumber}
              </span>
              <span className="flex-1">{r.label}</span>
              <span className="font-semibold">{r.jumlah} baris</span>
              <span className="font-mono text-[11px] text-slate-500">{r.endpoint}</span>
            </li>
          ))}
        </ul>
      )}
    </div>
  );
}

export default function AIAssistant() {
  const [models, setModels] = useState([]);
  const [model, setModel] = useState("gpt-5.2");
  const [regions, setRegions] = useState([]);
  const [wilayah, setWilayah] = useState("");
  const [suggestions, setSuggestions] = useState([]);
  const [sessions, setSessions] = useState([]);
  const [sessionId, setSessionId] = useState(null);
  const [messages, setMessages] = useState([]);
  const [question, setQuestion] = useState("");
  const [loading, setLoading] = useState(false);
  const [error, setError] = useState("");
  const bottomRef = useRef(null);

  const loadSessions = () => {
    api.get("/ai/chat-sessions?limit=30")
      .then((r) => setSessions(r.data.items || []))
      .catch(() => {});
  };

  useEffect(() => {
    api.get("/ai/models").then((r) => {
      setModels(r.data.items || []);
      setModel(r.data.default || "gpt-5.2");
    }).catch(() => {});
    api.get("/ai/suggestions").then((r) => setSuggestions(r.data.items || [])).catch(() => {});
    api.get("/regions").then((r) => setRegions(r.data || [])).catch(() => {});
    loadSessions();
  }, []);

  useEffect(() => {
    bottomRef.current?.scrollIntoView({ behavior: "smooth", block: "end" });
  }, [messages, loading]);

  const openSession = async (id) => {
    try {
      const r = await api.get(`/ai/chat/${id}`);
      const items = (r.data.items || []).map((m) => ({
        role: m.role, content: m.content, refs: m.refs || [], model: m.model,
      }));
      setMessages(items);
      setSessionId(id);
      setError("");
    } catch {
      toast.error("Gagal membuka percakapan");
    }
  };

  const deleteSession = async (id) => {
    try {
      await api.delete(`/ai/chat/${id}`);
      if (id === sessionId) { setSessionId(null); setMessages([]); }
      loadSessions();
      toast.success("Percakapan dihapus");
    } catch {
      toast.error("Gagal menghapus percakapan");
    }
  };

  const newSession = () => {
    setSessionId(null);
    setMessages([]);
    setError("");
    setQuestion("");
  };

  const ask = async (text) => {
    const q = (text ?? question).trim();
    if (q.length < 3 || loading) return;
    setQuestion("");
    setError("");
    setLoading(true);
    setMessages((m) => [...m, { role: "user", content: q },
                        { role: "assistant", content: "", refs: [], model }]);
    try {
      const res = await fetch(`${API}/ai/ask`, {
        method: "POST",
        headers: { "Content-Type": "application/json" },
        credentials: "include",
        body: JSON.stringify({
          question: q, model,
          session_id: sessionId || null,
          wilayah: wilayah || null,
        }),
      });
      if (!res.ok || !res.body) {
        const detail = await res.json().catch(() => ({}));
        throw new Error(detail.detail || "gagal");
      }
      const reader = res.body.getReader();
      const decoder = new TextDecoder();
      let buffer = "";
      let acc = "";
      let sid = sessionId;
      while (true) {
        const { done, value } = await reader.read();
        if (done) break;
        buffer += decoder.decode(value, { stream: true });
        const parts = buffer.split("\n\n");
        buffer = parts.pop();
        for (const part of parts) {
          const line = part.trim();
          if (!line.startsWith("data:")) continue;
          let payload;
          try { payload = JSON.parse(line.slice(5).trim()); } catch { continue; }
          if (payload.session_id) {
            sid = payload.session_id;
            setSessionId(payload.session_id);
            setMessages((m) => {
              const c = [...m];
              c[c.length - 1] = { ...c[c.length - 1], refs: payload.refs || [] };
              return c;
            });
          } else if (payload.delta) {
            acc += payload.delta;
            setMessages((m) => {
              const c = [...m];
              c[c.length - 1] = { ...c[c.length - 1], content: acc };
              return c;
            });
          } else if (payload.error) {
            throw new Error(payload.error);
          }
        }
      }
      if (!acc) throw new Error("Jawaban kosong");
      if (sid) loadSessions();
    } catch (e) {
      setError(String(e.message || e));
      setMessages((m) => m.filter((x, i) => !(i === m.length - 1 && !x.content)));
    } finally {
      setLoading(false);
    }
  };

  const downloadPdf = async (content) => {
    try {
      toast.loading("Menyiapkan laporan PDF…", { id: "ai-pdf" });
      const res = await fetch(`${API}/report/ai`, {
        method: "POST",
        headers: { "Content-Type": "application/json" },
        credentials: "include",
        body: JSON.stringify({ kategori: "assistant", wilayah: wilayah || null, hasil: content }),
      });
      if (!res.ok) throw new Error();
      const blob = await res.blob();
      const url = URL.createObjectURL(blob);
      const a = document.createElement("a");
      a.href = url;
      a.download = `Analisis_AI_SIDATA_${wilayah || "Kota_Makassar"}.pdf`;
      document.body.appendChild(a);
      a.click();
      a.remove();
      URL.revokeObjectURL(url);
      toast.success("Laporan PDF berhasil diunduh", { id: "ai-pdf" });
    } catch {
      toast.error("Gagal mengunduh laporan", { id: "ai-pdf" });
    }
  };

  return (
    <div className="space-y-5" data-testid="ai-assistant-page">
      <div>
        <p className="font-head text-2xl font-extrabold md:text-3xl">AI Assistant (Tanya Data)</p>
        <p className="mt-1 max-w-4xl text-sm text-muted-foreground">
          Ajukan pertanyaan bebas; jawaban disusun langsung dari basis data SIDATA
          (wilayah prioritas, faktor penyebab, anggaran stunting 2025 vs 2026, OPD terkait)
          dengan struktur Ringkasan Analisis, Data Pendukung, Faktor Utama, Program Terkait,
          Rekomendasi, dan Tingkat Prioritas.
        </p>
      </div>

      <div className="grid grid-cols-1 gap-5 lg:grid-cols-[1fr_280px]">
        {/* ---------------- kolom chat ---------------- */}
        <div className="flex flex-col rounded-lg border-2 border-border bg-card">
          {/* kontrol */}
          <div className="flex flex-wrap items-end gap-3 border-b-2 border-border p-4">
            <div className="min-w-[190px] flex-1">
              <label className="mb-1 block text-xs font-bold uppercase text-slate-500">Model AI</label>
              <select
                data-testid="ai-model-select"
                value={model}
                onChange={(e) => setModel(e.target.value)}
                className="w-full rounded-md border-2 border-border bg-background px-3 py-2 text-sm focus:border-primary focus:outline-none"
              >
                {models.map((m) => (
                  <option key={m.id} value={m.id}>{m.label}</option>
                ))}
              </select>
            </div>
            <div className="min-w-[190px] flex-1">
              <label className="mb-1 block text-xs font-bold uppercase text-slate-500">Fokus Wilayah</label>
              <select
                data-testid="ai-wilayah-select"
                value={wilayah}
                onChange={(e) => setWilayah(e.target.value)}
                className="w-full rounded-md border-2 border-border bg-background px-3 py-2 text-sm focus:border-primary focus:outline-none"
              >
                <option value="">Seluruh Kota Makassar</option>
                {regions.map((r) => (
                  <option key={r.id} value={r.nama}>Kecamatan {r.nama}</option>
                ))}
              </select>
            </div>
            <button
              type="button"
              data-testid="ai-new-chat"
              onClick={newSession}
              className="inline-flex items-center gap-2 rounded-md border-2 border-border px-3 py-2 text-sm font-semibold hover:bg-slate-100 focus:outline-none"
            >
              <Plus className="h-4 w-4" /> Percakapan Baru
            </button>
          </div>

          {/* pesan */}
          <div className="min-h-[320px] flex-1 space-y-4 overflow-y-auto p-4 md:max-h-[58vh]">
            {messages.length === 0 && !loading && (
              <div className="space-y-3">
                <p className="text-sm font-semibold text-slate-600">Contoh pertanyaan:</p>
                <div className="flex flex-wrap gap-2">
                  {suggestions.map((s, i) => (
                    <button
                      key={i}
                      type="button"
                      data-testid={`ai-suggestion-${i}`}
                      onClick={() => ask(s)}
                      className="rounded-full border-2 border-border bg-slate-50 px-3 py-1.5 text-left text-xs font-semibold text-slate-700 hover:border-primary hover:text-primary focus:outline-none"
                    >
                      {s}
                    </button>
                  ))}
                </div>
              </div>
            )}

            {messages.map((m, i) =>
              m.role === "user" ? (
                <div key={i} className="flex justify-end" data-testid="ai-msg-user">
                  <div className="max-w-[85%] rounded-lg rounded-br-none bg-accent px-4 py-2.5 text-sm font-semibold text-accent-foreground">
                    {m.content}
                  </div>
                </div>
              ) : (
                <div key={i} className="rounded-lg border-2 border-accent/40 bg-slate-50/60 p-4" data-testid="ai-msg-assistant">
                  <div className="mb-2 flex flex-wrap items-center justify-between gap-2">
                    <span className="inline-flex items-center gap-2 rounded-full bg-primary/10 px-3 py-1 text-xs font-bold text-primary">
                      {loading && i === messages.length - 1
                        ? <Loader2 className="h-3.5 w-3.5 animate-spin" />
                        : <Sparkles className="h-3.5 w-3.5" />}
                      {loading && i === messages.length - 1 ? "Menganalisis data…" : `Analisis AI · ${m.model || model}`}
                    </span>
                    {m.content && !(loading && i === messages.length - 1) && (
                      <span className="flex items-center gap-2">
                        <button
                          type="button"
                          data-testid="ai-pdf-btn"
                          onClick={() => downloadPdf(m.content)}
                          className="inline-flex items-center gap-1.5 rounded-full bg-accent px-3 py-1.5 text-xs font-semibold text-accent-foreground hover:opacity-90 focus:outline-none"
                        >
                          <FileDown className="h-3.5 w-3.5" /> PDF
                        </button>
                        <Speak text={toPlain(m.content)} label="Bacakan" testid="ai-speak" />
                      </span>
                    )}
                  </div>
                  {m.content ? (
                    <div className="prose-gov max-w-none text-sm"
                         dangerouslySetInnerHTML={{ __html: marked.parse(m.content) }} />
                  ) : (
                    <p className="text-sm text-muted-foreground">Membaca basis data SIDATA…</p>
                  )}
                  <RefsPanel refs={m.refs} />
                </div>
              )
            )}
            {error && (
              <div className="flex items-center gap-2 rounded-md border-2 border-destructive bg-destructive/5 p-3 text-sm font-semibold text-destructive" data-testid="ai-error">
                <AlertTriangle className="h-4 w-4" /> {error}
              </div>
            )}
            <div ref={bottomRef} />
          </div>

          {/* input */}
          <div className="border-t-2 border-border p-3 sm:p-4">
            <div className="flex items-end gap-2">
              <textarea
                data-testid="ai-question-input"
                rows={2}
                value={question}
                onChange={(e) => setQuestion(e.target.value)}
                onKeyDown={(e) => {
                  if (e.key === "Enter" && !e.shiftKey) { e.preventDefault(); ask(); }
                }}
                placeholder="Contoh: Kelurahan mana paling prioritas dan apa faktor penyebabnya?"
                className="min-w-0 flex-1 resize-none rounded-md border-2 border-border bg-background px-3 py-2 text-sm focus:border-primary focus:outline-none"
              />
              <button
                type="button"
                data-testid="ai-send-btn"
                onClick={() => ask()}
                disabled={loading || question.trim().length < 3}
                className="inline-flex shrink-0 items-center gap-1.5 rounded-md bg-primary px-3.5 py-2.5 text-sm font-bold text-primary-foreground hover:bg-[#0E6456] focus:outline-none disabled:opacity-60 sm:gap-2 sm:px-5 sm:py-3"
              >
                {loading ? <Loader2 className="h-4 w-4 animate-spin" /> : <Send className="h-4 w-4" />}
                Tanya
              </button>
            </div>
            <p className="mt-2 text-[11px] text-slate-500">
              Jawaban hanya memakai angka yang tersedia pada basis data. Bila data belum diimpor,
              AI akan menyatakannya secara eksplisit.
            </p>
          </div>
        </div>

        {/* ---------------- riwayat percakapan ---------------- */}
        <div className="rounded-lg border-2 border-border bg-card p-4" data-testid="ai-session-list">
          <h2 className="mb-3 flex items-center gap-2 text-sm font-bold uppercase text-slate-500">
            <MessageSquare className="h-4 w-4" /> Riwayat Percakapan
          </h2>
          {sessions.length === 0 ? (
            <p className="text-xs text-muted-foreground">Belum ada percakapan.</p>
          ) : (
            <ul className="space-y-2">
              {sessions.map((s) => (
                <li key={s.id} className={`rounded-md border-2 p-2 text-xs ${
                  s.id === sessionId ? "border-primary bg-primary/5" : "border-border"}`}>
                  <button
                    type="button"
                    onClick={() => openSession(s.id)}
                    className="block w-full text-left font-semibold text-slate-800 focus:outline-none"
                  >
                    {s.judul || "(tanpa judul)"}
                  </button>
                  <div className="mt-1 flex items-center justify-between text-[11px] text-slate-500">
                    <span>{(s.updated_at || "").slice(0, 16).replace("T", " ")}</span>
                    <button
                      type="button"
                      onClick={() => deleteSession(s.id)}
                      className="inline-flex items-center gap-1 text-red-600 hover:underline focus:outline-none"
                    >
                      <Trash2 className="h-3 w-3" /> Hapus
                    </button>
                  </div>
                </li>
              ))}
            </ul>
          )}
        </div>
      </div>
    </div>
  );
}
