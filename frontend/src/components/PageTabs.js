import React, { useRef } from "react";
import { FR } from "@/features/a11y/ui";

/**
 * Tab tingkat halaman dengan pola WAI-ARIA (roving tabindex + panah kiri/kanan).
 * Dipakai untuk menggabungkan beberapa fungsi lama ke satu pintu masuk tanpa
 * mengubah hak akses tiap fungsi.
 */
export function PageTabs({ tabs, value, onChange, label = "Bagian halaman" }) {
  const refs = useRef([]);
  const idx = tabs.findIndex((t) => t.id === value);

  const pindah = (d) => {
    const n = tabs.length;
    if (!n) return;
    const next = (idx + d + n) % n;
    onChange(tabs[next].id);
    refs.current[next]?.focus();
  };

  if (tabs.length < 2) return null;

  return (
    <div role="tablist" aria-label={label} className="mb-4 flex flex-wrap gap-2 border-b border-slate-200 pb-2">
      {tabs.map((t, i) => {
        const aktif = t.id === value;
        const Ic = t.icon;
        return (
          <button
            key={t.id}
            ref={(el) => { refs.current[i] = el; }}
            type="button"
            role="tab"
            id={`tab-${t.id}`}
            aria-selected={aktif}
            aria-controls={`panel-${t.id}`}
            tabIndex={aktif ? 0 : -1}
            data-testid={`page-tab-${t.id}`}
            onClick={() => onChange(t.id)}
            onKeyDown={(e) => {
              if (e.key === "ArrowRight") { e.preventDefault(); pindah(1); }
              else if (e.key === "ArrowLeft") { e.preventDefault(); pindah(-1); }
              else if (e.key === "Home") { e.preventDefault(); onChange(tabs[0].id); refs.current[0]?.focus(); }
              else if (e.key === "End") {
                e.preventDefault();
                const last = tabs.length - 1;
                onChange(tabs[last].id);
                refs.current[last]?.focus();
              }
            }}
            className={`inline-flex min-h-11 items-center gap-2 rounded-full px-4 text-sm font-semibold transition-colors ${FR} ${
              aktif
                ? "bg-[#117A69] text-white shadow-sm"
                : "bg-white text-slate-700 ring-1 ring-slate-200 hover:ring-slate-300"
            }`}
          >
            {Ic ? <Ic className="h-4 w-4" aria-hidden="true" /> : null}
            {t.label}
          </button>
        );
      })}
    </div>
  );
}

/** Panel isi tab — dipasangkan dengan `PageTabs`. */
export function TabPanel({ id, children }) {
  return (
    <div role="tabpanel" id={`panel-${id}`} aria-labelledby={`tab-${id}`} tabIndex={0} className="focus:outline-none">
      {children}
    </div>
  );
}
