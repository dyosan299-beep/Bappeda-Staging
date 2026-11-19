/* Design system PETA INKLUSI — diturunkan dari warna logo. */
export const BRAND = {
  navy: "#232F3E",
  navy2: "#1A2330",
  mint: "#6FE3CF",
  teal: "#117A69", // primer (kontras AA dengan teks putih)
  magenta: "#C8375B",
  amber: "#F4B63A",
  amberText: "#8A5A00",
};

export type Kategori = "disabilitas" | "stunting" | "ats" | "kemiskinan";

export const KATEGORI_META: Record<Kategori, { label: string; warna: string; ramp: string[]; ikon: string; satuan: string; inquiry: string }> = {
  disabilitas: { label: "Disabilitas", warna: "#117A69", ikon: "♿", satuan: "orang", inquiry: "Disabilitas",
    ramp: ["#E6FAF6", "#B5EFE3", "#6FE3CF", "#2FB9A2", "#117A69", "#0B4F45"] },
  stunting: { label: "Stunting", warna: "#C8375B", ikon: "👶", satuan: "anak", inquiry: "Stunting",
    ramp: ["#FCE8ED", "#F5BFCC", "#EA8AA2", "#DB5B7B", "#C8375B", "#8E2240"] },
  ats: { label: "Anak Tidak Sekolah", warna: "#9A6416", ikon: "🎓", satuan: "anak", inquiry: "ATS",
    ramp: ["#FEF6E4", "#FCE3AE", "#F8CD72", "#F4B63A", "#D18F16", "#8A5A00"] },
  kemiskinan: { label: "Kemiskinan", warna: "#3B4F6B", ikon: "🏠", satuan: "KK", inquiry: "Kemiskinan",
    ramp: ["#EEF1F6", "#CBD4E1", "#98A9C2", "#667E9F", "#3B4F6B", "#232F3E"] },
};

export const normWil = (s: any) =>
  String(s || "")
    .toUpperCase()
    .replace(/-/g, " ")
    .normalize("NFKD")
    .replace(/[^A-Z0-9' ]/g, " ")
    .replace(/\s+/g, " ")
    .trim();

export const fmt = (n: any) => (n === null || n === undefined || n === "" ? "-" : Number(n).toLocaleString("id-ID"));
